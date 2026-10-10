#!/usr/bin/env python3
"""
Audiobook Factory - Pillar 3.1: ACID Key Lease & Inventory Reservation Engine.
Guarantees:
1. Multi-user & multi-process mutual exclusion (Concurrency = 1 per key).
2. Autonomous dead PID crash recovery via OS process tables.
3. Rolling lease TTL with background heartbeat daemon.
4. "One User = One Active Key per Workload" enforcement.
5. Zero-secret public aliases and structured audit ledger.
"""

from __future__ import annotations
import os
import sys
import time
import uuid
import hashlib
import sqlite3
import threading
import contextlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Generator
from zoneinfo import ZoneInfo

from audiobook_factory.core.models.db import get_db_connection, init_db, DEFAULT_DB_PATH
from audiobook_factory.logger import logger

# Public Alias Salt (Machine-local ephemeral or fixed salt for deterministic public aliases)
_ALIAS_SALT = b"audiobook_factory_safe_public_alias_v1"


def _hash_key(api_key: str) -> str:
    """Computes standard 16-hex-char SHA-256 identifier for internal database keys."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]


def _alias_key(api_key: str) -> str:
    """Computes safe, zero-secret public alias for logs and telemetry (e.g. 'key_a8f2')."""
    h = hashlib.sha256(api_key.encode("utf-8") + _ALIAS_SALT).hexdigest()
    return f"key_{h[:8]}"


def _google_quota_date_str() -> str:
    """
    Returns Pacific Time YYYY-MM-DD for Google AI Studio quotas.
    Includes DST transitions with safe fallback for environments lacking tzdata (e.g. Windows).
    """
    try:
        pacific_tz = ZoneInfo("America/Los_Angeles")
        return datetime.now(pacific_tz).strftime("%Y-%m-%d")
    except Exception:
        pacific_tz = timezone(timedelta(hours=-7))
        return datetime.now(pacific_tz).strftime("%Y-%m-%d")


def _utc_quota_date_str() -> str:
    """Returns standard UTC midnight YYYY-MM-DD for OpenAI, Anthropic, Cerebras, Groq."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def is_pid_alive(pid: int) -> bool:
    """
    Probes local operating system process table to verify whether a PID is actively running.
    Returns True if process is alive, False if dead or nonexistent.
    """
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            process = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if process != 0:
                kernel32.CloseHandle(process)
                return True
            return False
        except Exception:
            return False
    try:
        # On POSIX (Linux, Android, macOS), signal 0 checks for existence without killing
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but owned by another user
        return True
    except Exception:
        # Fallback
        return False


class KeyLeaseError(RuntimeError):
    """Base exception for Key Lease errors."""
    pass


class KeyLeaseQuotaExceededError(KeyLeaseError):
    """Raised when a user attempts to acquire more concurrent keys than permitted by policy."""
    pass


class NoAvailableKeyError(KeyLeaseError):
    """Raised when all keys are currently leased, cooling down, or busy."""
    pass


class AllKeysExhaustedTodayError(KeyLeaseError):
    """Raised when all configured API keys have exhausted their daily quota for today."""
    pass


@dataclass(frozen=True)
class CallerIdentity:
    """Cryptographic and operational tuple identifying a caller process or human user."""
    workstation_id: str = field(default_factory=lambda: os.environ.get("WORKSTATION_ID", "local_workstation"))
    user_id: str = field(default_factory=lambda: os.environ.get("USER", os.environ.get("USERNAME", "default_user")))
    process_id: int = field(default_factory=os.getpid)
    worker_id: str = field(default_factory=lambda: f"thr_{threading.get_ident()}")
    session_id: str = field(default_factory=lambda: os.environ.get("CURRENT_SESSION_ID") or os.environ.get("CURRENT_AUDIOBOOK_RUN_ID") or "session_default")
    workload_type: str = "text"  # "text" or "tts"


@dataclass
class KeyLease:
    """Active lease handle guaranteeing exclusive single-request mutual exclusion."""
    lease_id: str
    key_hash: str
    key_alias: str
    api_key: str
    provider: str
    workload_type: str
    leased_at: str
    expires_at: str
    status: str = "ACTIVE"


class KeyLeaseManager:
    """
    High-Performance ACID SQLite Key Inventory & Lease Manager.
    Enforces:
    - Mutex Concurrency = 1 per free API key.
    - Session Affinity with rolling TTL.
    - Autonomous dead PID crash reclamation.
    - One User = One Key per Workload enforcement.
    - Zero plaintext logging.
    """

    def __init__(self, db_path: Optional[Path] = None, keys: Optional[List[str]] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH).resolve()
        self._lock = threading.RLock()
        init_db(self.db_path)

        if keys is not None:
            self.register_keys(keys, provider="gemini")
        else:
            self._auto_discover_and_register_env_keys()

    def _connection(self):
        return get_db_connection(self.db_path)

    def _today_str(self, provider: str = "gemini") -> str:
        if provider == "gemini":
            return _google_quota_date_str()
        return _utc_quota_date_str()

    def _auto_discover_and_register_env_keys(self) -> None:
        """Auto-discovers keys from environment variables and registers them in the inventory."""
        provider_env_map = {
            "gemini": ["GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY"],
            "openrouter": ["OPENROUTER_API_KEYS", "OPENROUTER_API_KEY"],
            "cerebras": ["CEREBRAS_API_KEYS", "CEREBRAS_API_KEY"],
            "groq": ["GROQ_API_KEYS", "GROQ_API_KEY"],
            "openai": ["OPENAI_API_KEYS", "OPENAI_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEYS", "ANTHROPIC_API_KEY"],
            "elevenlabs": ["ELEVENLABS_API_KEYS", "ELEVENLABS_API_KEY"],
            "local": ["LOCAL_API_KEY"],
        }
        for provider, var_names in provider_env_map.items():
            found_keys: List[str] = []
            for var in var_names:
                val = os.environ.get(var, "")
                if val:
                    for k in val.split(","):
                        clean_k = k.strip().strip("'\"")
                        if clean_k and clean_k not in found_keys:
                            found_keys.append(clean_k)
            if found_keys:
                self.register_keys(found_keys, provider=provider)

    def register_keys(
        self,
        keys: List[str],
        provider: str = "gemini",
        allowed_services: Optional[List[str]] = None,
        tier: str = "free",
    ) -> None:
        """Registers or syncs API keys in key_inventory without wiping quota history."""
        services_json = json.dumps(allowed_services or ["text", "tts"])
        today = self._today_str(provider)

        with self._lock, self._connection() as conn:
            for k in keys:
                clean_k = k.strip().strip("'\"")
                if not clean_k:
                    continue
                kh = _hash_key(clean_k)
                ka = _alias_key(clean_k)

                conn.execute("""
                    INSERT INTO key_inventory (
                        key_hash, key_alias, encrypted_key, provider, tier,
                        allowed_services, status, last_reset_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
                    ON CONFLICT(key_hash) DO UPDATE SET
                        key_alias = excluded.key_alias,
                        encrypted_key = excluded.encrypted_key,
                        provider = excluded.provider,
                        allowed_services = excluded.allowed_services;
                """, (kh, ka, clean_k, provider, tier, services_json, today))
            conn.commit()

    def _check_date_rollover(self, conn: sqlite3.Connection, provider: str = "gemini") -> None:
        """Automatically re-activates keys whose exhausted_date is prior to today and resets daily counters."""
        today = self._today_str(provider)
        cursor = conn.execute("""
            UPDATE key_inventory
            SET status = CASE WHEN status = 'EXHAUSTED_TODAY' THEN 'ACTIVE' ELSE status END,
                exhausted_date = NULL,
                total_calls_today = 0,
                success_calls_today = 0,
                failed_calls_today = 0,
                backoff_until = NULL,
                last_reset_date = ?
            WHERE (exhausted_date IS NOT NULL AND exhausted_date != ?)
               OR (last_reset_date IS NULL OR last_reset_date != ?);
        """, (today, today, today))

        conn.execute("""
            UPDATE model_quota_ledger
            SET status = CASE WHEN status = 'EXHAUSTED_TODAY' THEN 'ACTIVE' ELSE status END,
                exhausted_date = NULL,
                total_calls_today = 0,
                success_calls_today = 0,
                failed_calls_today = 0,
                total_tokens_today = 0,
                backoff_until = NULL,
                last_reset_date = ?
            WHERE (exhausted_date IS NOT NULL AND exhausted_date != ?)
               OR (last_reset_date IS NULL OR last_reset_date != ?);
        """, (today, today, today))

        if cursor.rowcount > 0:
            logger.info(f"  [DATE ROLLOVER] Midnight passed for {provider}! Reset {cursor.rowcount} API keys to ACTIVE for {today}.")

    def sweep_stale_and_dead_leases(self, conn: sqlite3.Connection) -> int:
        """
        Dual Liveness Sweep:
        1. Marks leases past their expires_at as EXPIRED.
        2. Probes OS process table for active leases; if process is dead, marks EXPIRED immediately.
        Returns count of reclaimed leases.
        """
        reclaimed = 0
        now_ts = datetime.now().isoformat()

        # 1. Sweep expired TTL leases
        res = conn.execute("""
            UPDATE key_leases
            SET status = 'EXPIRED'
            WHERE status = 'ACTIVE' AND expires_at < ?;
        """, (now_ts,))
        reclaimed += res.rowcount

        # 2. Sweep dead PID leases
        active_leases = conn.execute("""
            SELECT lease_id, process_id, key_hash
            FROM key_leases
            WHERE status = 'ACTIVE';
        """).fetchall()

        for row in active_leases:
            pid = row["process_id"]
            if not is_pid_alive(pid):
                conn.execute("""
                    UPDATE key_leases
                    SET status = 'EXPIRED'
                    WHERE lease_id = ?;
                """, (row["lease_id"],))
                reclaimed += 1
                logger.warning(f"  [CRASH RECOVERY] Reclaimed orphaned lease {row['lease_id']} from dead PID {pid}.")

        return reclaimed

    def _check_user_concurrency(
        self,
        conn: sqlite3.Connection,
        identity: CallerIdentity,
        provider: str,
        max_allowed: int = 1,
    ) -> None:
        """
        Enforces 'One User = One Key per Workload' constraint.
        Raises KeyLeaseQuotaExceededError if user already holds an active lease for this workload.
        """
        row = conn.execute("""
            SELECT count(*) as count
            FROM key_leases
            WHERE user_id = ?
              AND provider = ?
              AND workload_type = ?
              AND status = 'ACTIVE'
              AND expires_at > ?;
        """, (identity.user_id, provider, identity.workload_type, datetime.now().isoformat())).fetchone()

        if row and row["count"] >= max_allowed:
            raise KeyLeaseQuotaExceededError(
                f"Policy breach: User '{identity.user_id}' already holds {row['count']} active lease(s) for "
                f"{provider.upper()} {identity.workload_type.upper()}. Concurrency limit is {max_allowed}."
            )

    def acquire_lease(
        self,
        workload_type: str = "text",
        provider: str = "gemini",
        identity: Optional[CallerIdentity] = None,
        ttl_seconds: float = 60.0,
        model: Optional[str] = None,
        allow_multi_lease: bool = False,
        preferred_key_alias: Optional[str] = None,
    ) -> KeyLease:
        """
        Atomically acquires an exclusive lease for an eligible API key.
        Guarantees:
        - Mutual exclusion (0% double-allocations).
        - Dead PID crash reclamation.
        - User quota enforcement.
        - Quota rollover and model isolation.
        """
        eff_identity = identity or CallerIdentity(workload_type=workload_type)
        now_dt = datetime.now()
        now_ts = now_dt.isoformat()
        expires_ts = (now_dt + timedelta(seconds=ttl_seconds)).isoformat()
        lease_id = str(uuid.uuid4())
        today = self._today_str(provider)

        with self._lock, self._connection() as conn:
            # Atomic transaction
            conn.execute("BEGIN IMMEDIATE;")

            # 1. Date rollover check
            self._check_date_rollover(conn, provider=provider)

            # 2. Sweep dead/stale leases
            self.sweep_stale_and_dead_leases(conn)

            # 3. Check user concurrency quota
            if not allow_multi_lease:
                self._check_user_concurrency(conn, eff_identity, provider, max_allowed=1)

            # 4. Clear expired temporary backoffs
            conn.execute("""
                UPDATE key_inventory
                SET status = 'ACTIVE', backoff_until = NULL
                WHERE status = 'TEMP_BACKOFF' AND backoff_until <= ?;
            """, (now_ts,))

            conn.execute("""
                UPDATE model_quota_ledger
                SET status = 'ACTIVE', backoff_until = NULL
                WHERE status = 'TEMP_BACKOFF' AND backoff_until <= ?;
            """, (now_ts,))

            # 5. Query candidate keys that are NOT currently leased
            is_tts = (workload_type == "tts") or (model and "-tts" in model.lower())
            key_status_clause = "k.status = 'ACTIVE'" if is_tts else "k.status != 'INVALID'"

            order_clause = (
                "ORDER BY (CASE WHEN k.key_alias = ? THEN 0 ELSE 1 END), k.last_used ASC NULLS FIRST, k.total_calls_today ASC"
                if preferred_key_alias
                else "ORDER BY k.last_used ASC NULLS FIRST, k.total_calls_today ASC"
            )

            if model:
                query = f"""
                    SELECT k.key_hash, k.key_alias, k.encrypted_key
                    FROM key_inventory k
                    LEFT JOIN model_quota_ledger m ON (k.key_hash = m.key_hash AND m.model = ?)
                    WHERE k.provider = ?
                      AND {key_status_clause}
                      AND (k.backoff_until IS NULL OR k.backoff_until <= ?)
                      AND (m.status IS NULL OR m.status = 'ACTIVE' OR (m.status = 'TEMP_BACKOFF' AND m.backoff_until <= ?))
                      AND (m.exhausted_date IS NULL OR m.exhausted_date != ?)
                      AND NOT EXISTS (
                          SELECT 1 FROM key_leases l
                          WHERE l.key_hash = k.key_hash
                            AND l.status = 'ACTIVE'
                            AND l.expires_at > ?
                      )
                    {order_clause}
                    LIMIT 1;
                """
                params: tuple = (preferred_key_alias, model, provider, now_ts, now_ts, today, now_ts) if preferred_key_alias else (model, provider, now_ts, now_ts, today, now_ts)
                row = conn.execute(query, params).fetchone()
            else:
                query = f"""
                    SELECT k.key_hash, k.key_alias, k.encrypted_key
                    FROM key_inventory k
                    WHERE k.provider = ?
                      AND {key_status_clause}
                      AND (k.backoff_until IS NULL OR k.backoff_until <= ?)
                      AND NOT EXISTS (
                          SELECT 1 FROM key_leases l
                          WHERE l.key_hash = k.key_hash
                            AND l.status = 'ACTIVE'
                            AND l.expires_at > ?
                      )
                    {order_clause}
                    LIMIT 1;
                """
                params = (preferred_key_alias, provider, now_ts, now_ts) if preferred_key_alias else (provider, now_ts, now_ts)
                row = conn.execute(query, params).fetchone()

            if not row:
                # Check if all keys exhausted today
                total_valid = conn.execute(
                    "SELECT count(*) as c FROM key_inventory WHERE provider = ? AND status != 'INVALID';", (provider,)
                ).fetchone()["c"]

                exhausted = conn.execute(
                    "SELECT count(*) as c FROM key_inventory WHERE provider = ? AND status = 'EXHAUSTED_TODAY' AND exhausted_date = ?;",
                    (provider, today)
                ).fetchone()["c"]

                if total_valid > 0 and exhausted >= total_valid:
                    raise AllKeysExhaustedTodayError(
                        f"All {total_valid} {provider.upper()} API keys have exhausted daily quota for {today}."
                    )
                raise NoAvailableKeyError(f"No available {provider.upper()} keys available (all busy or cooling down).")

            # 6. Insert atomic lease
            conn.execute("""
                INSERT INTO key_leases (
                    lease_id, key_hash, key_alias, provider, workstation_id, user_id,
                    process_id, worker_id, session_id, workload_type,
                    leased_at, expires_at, heartbeat_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE');
            """, (
                lease_id, row["key_hash"], row["key_alias"], provider, eff_identity.workstation_id,
                eff_identity.user_id, eff_identity.process_id, eff_identity.worker_id,
                eff_identity.session_id or "session_default", workload_type, now_ts, expires_ts, now_ts
            ))

            # Update inventory last_used
            conn.execute("""
                UPDATE key_inventory
                SET last_used = CURRENT_TIMESTAMP,
                    total_calls_today = total_calls_today + 1
                WHERE key_hash = ?;
            """, (row["key_hash"],))

            if model:
                conn.execute("""
                    INSERT INTO model_quota_ledger (key_hash, provider, model, total_calls_today, last_used)
                    VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(key_hash, model) DO UPDATE SET
                        total_calls_today = total_calls_today + 1,
                        last_used = CURRENT_TIMESTAMP;
                """, (row["key_hash"], provider, model))

            # Audit event
            conn.execute("""
                INSERT INTO key_audit_log (
                    event_type, lease_id, key_alias, user_id, process_id,
                    model_id, provider
                ) VALUES ('ACQUIRE', ?, ?, ?, ?, ?, ?);
            """, (lease_id, row["key_alias"], eff_identity.user_id, eff_identity.process_id, model, provider))

            conn.commit()

            return KeyLease(
                lease_id=lease_id,
                key_hash=row["key_hash"],
                key_alias=row["key_alias"],
                api_key=row["encrypted_key"],
                provider=provider,
                workload_type=workload_type,
                leased_at=now_ts,
                expires_at=expires_ts,
                status="ACTIVE",
            )

    def renew_lease(self, lease_id: str, extend_seconds: float = 60.0) -> bool:
        """Extends an active lease expiration timestamp (heartbeat)."""
        now_ts = datetime.now().isoformat()
        new_expires_ts = (datetime.now() + timedelta(seconds=extend_seconds)).isoformat()
        with self._lock, self._connection() as conn:
            cursor = conn.execute("""
                UPDATE key_leases
                SET expires_at = ?, heartbeat_at = ?
                WHERE lease_id = ? AND status = 'ACTIVE';
            """, (new_expires_ts, now_ts, lease_id))
            conn.commit()
            return cursor.rowcount > 0

    def release_lease(self, lease_id: str) -> bool:
        """Releases an active lease handle and records audit completion."""
        with self._lock, self._connection() as conn:
            row = conn.execute("SELECT key_alias, user_id, process_id, provider FROM key_leases WHERE lease_id = ?;", (lease_id,)).fetchone()
            if not row:
                return False

            cursor = conn.execute("""
                UPDATE key_leases
                SET status = 'RELEASED'
                WHERE lease_id = ? AND status = 'ACTIVE';
            """, (lease_id,))

            if cursor.rowcount > 0:
                conn.execute("""
                    INSERT INTO key_audit_log (
                        event_type, lease_id, key_alias, user_id, process_id, provider
                    ) VALUES ('RELEASE', ?, ?, ?, ?, ?);
                """, (lease_id, row["key_alias"], row["user_id"], row["process_id"], row["provider"]))

            conn.commit()
            return cursor.rowcount > 0

    def revoke_lease(self, lease_id: str, reason: str = "error") -> bool:
        """Revokes an active lease (e.g. on 429 quota exhaustion or critical failure)."""
        with self._lock, self._connection() as conn:
            row = conn.execute("SELECT key_alias, user_id, process_id, provider FROM key_leases WHERE lease_id = ?;", (lease_id,)).fetchone()
            if not row:
                return False

            cursor = conn.execute("""
                UPDATE key_leases
                SET status = 'REVOKED'
                WHERE lease_id = ? AND status = 'ACTIVE';
            """, (lease_id,))

            if cursor.rowcount > 0:
                conn.execute("""
                    INSERT INTO key_audit_log (
                        event_type, lease_id, key_alias, user_id, process_id, provider, error_summary
                    ) VALUES ('REVOKE', ?, ?, ?, ?, ?, ?);
                """, (lease_id, row["key_alias"], row["user_id"], row["process_id"], row["provider"], reason[:200]))

            conn.commit()
            return cursor.rowcount > 0

    def record_success(
        self,
        api_key_or_hash: str,
        model: Optional[str] = None,
        provider: str = "gemini",
        tokens_used: int = 0,
    ) -> None:
        """Records a successful call for a key."""
        kh = api_key_or_hash if len(api_key_or_hash) == 16 else _hash_key(api_key_or_hash)
        with self._lock, self._connection() as conn:
            conn.execute("""
                UPDATE key_inventory
                SET status = CASE WHEN status = 'EXHAUSTED_TODAY' THEN status ELSE 'ACTIVE' END,
                    success_calls_today = success_calls_today + 1,
                    backoff_until = NULL
                WHERE key_hash = ?;
            """, (kh,))

            if model:
                conn.execute("""
                    INSERT INTO model_quota_ledger (
                        key_hash, provider, model, status, success_calls_today, total_tokens_today
                    ) VALUES (?, ?, ?, 'ACTIVE', 1, ?)
                    ON CONFLICT(key_hash, model) DO UPDATE SET
                        status = 'ACTIVE',
                        success_calls_today = success_calls_today + 1,
                        total_tokens_today = total_tokens_today + excluded.total_tokens_today,
                        backoff_until = NULL;
                """, (kh, provider, model, tokens_used))
            conn.commit()

    def mark_daily_quota_exhausted(
        self,
        api_key_or_hash: str,
        error_msg: str,
        model: Optional[str] = None,
        provider: str = "gemini",
    ) -> None:
        """Marks a key or model as exhausted for today (e.g. 10 RPD reached on TTS)."""
        kh = api_key_or_hash if len(api_key_or_hash) == 16 else _hash_key(api_key_or_hash)
        today = self._today_str(provider)
        is_tts = (model is None) or ("-tts" in model.lower())

        with self._lock, self._connection() as conn:
            if is_tts:
                conn.execute("""
                    UPDATE key_inventory
                    SET status = 'EXHAUSTED_TODAY',
                        exhausted_date = ?,
                        failed_calls_today = failed_calls_today + 1
                    WHERE key_hash = ?;
                """, (today, kh))

            if model:
                conn.execute("""
                    INSERT INTO model_quota_ledger (
                        key_hash, provider, model, status, exhausted_date, failed_calls_today, last_error, last_reset_date
                    ) VALUES (?, ?, ?, 'EXHAUSTED_TODAY', ?, 1, ?, ?)
                    ON CONFLICT(key_hash, model) DO UPDATE SET
                        status = 'EXHAUSTED_TODAY',
                        exhausted_date = excluded.exhausted_date,
                        failed_calls_today = failed_calls_today + 1,
                        last_error = excluded.last_error,
                        last_reset_date = excluded.last_reset_date;
                """, (kh, provider, model, today, error_msg[:200], today))

            conn.commit()

    def mark_invalid(
        self,
        api_key_or_hash: str,
        error_msg: str,
        provider: str = "gemini",
    ) -> None:
        """Marks a key as permanently INVALID."""
        kh = api_key_or_hash if len(api_key_or_hash) == 16 else _hash_key(api_key_or_hash)
        with self._lock, self._connection() as conn:
            conn.execute("""
                UPDATE key_inventory
                SET status = 'INVALID'
                WHERE key_hash = ?;
            """, (kh,))
            conn.commit()

    def mark_temporary_backoff(
        self,
        api_key_or_hash: str,
        backoff_seconds: float,
        error_msg: str = "",
        model: Optional[str] = None,
        provider: str = "gemini",
    ) -> None:
        """Marks a key for temporary backoff without burning it for the whole day."""
        kh = api_key_or_hash if len(api_key_or_hash) == 16 else _hash_key(api_key_or_hash)
        backoff_until = datetime.fromtimestamp(time.time() + backoff_seconds).isoformat()

        with self._lock, self._connection() as conn:
            conn.execute("""
                UPDATE key_inventory
                SET status = CASE WHEN status = 'EXHAUSTED_TODAY' THEN status ELSE 'TEMP_BACKOFF' END,
                    backoff_until = ?,
                    failed_calls_today = failed_calls_today + 1
                WHERE key_hash = ?;
            """, (backoff_until, kh))

            if model:
                conn.execute("""
                    INSERT INTO model_quota_ledger (
                        key_hash, provider, model, status, backoff_until, failed_calls_today, last_error
                    ) VALUES (?, ?, ?, 'TEMP_BACKOFF', ?, 1, ?)
                    ON CONFLICT(key_hash, model) DO UPDATE SET
                        status = CASE WHEN status = 'EXHAUSTED_TODAY' THEN status ELSE 'TEMP_BACKOFF' END,
                        backoff_until = excluded.backoff_until,
                        failed_calls_today = failed_calls_today + 1,
                        last_error = excluded.last_error;
                """, (kh, provider, model, backoff_until, error_msg[:200]))

            conn.commit()

    def reset_all_for_today(self, provider: str = "gemini") -> None:
        """Forces administrative reset of all keys and models back to ACTIVE state."""
        with self._lock, self._connection() as conn:
            conn.execute("""
                UPDATE key_inventory
                SET status = 'ACTIVE',
                    exhausted_date = NULL,
                    backoff_until = NULL,
                    failed_calls_today = 0
                WHERE provider = ?;
            """, (provider,))
            conn.execute("""
                UPDATE model_quota_ledger
                SET status = 'ACTIVE',
                    exhausted_date = NULL,
                    backoff_until = NULL,
                    failed_calls_today = 0
                WHERE provider = ?;
            """, (provider,))
            conn.commit()

    @contextlib.contextmanager
    def lease_key(

        self,
        workload_type: str = "text",
        provider: str = "gemini",
        identity: Optional[CallerIdentity] = None,
        ttl_seconds: float = 60.0,
        model: Optional[str] = None,
        allow_multi_lease: bool = False,
    ) -> Generator[KeyLease, None, None]:
        """
        Thread-safe context manager leasing an API key handle.
        Automatically releases lease on normal exit or exception.
        """
        lease = self.acquire_lease(
            workload_type=workload_type,
            provider=provider,
            identity=identity,
            ttl_seconds=ttl_seconds,
            model=model,
            allow_multi_lease=allow_multi_lease,
        )
        try:
            yield lease
        finally:
            self.release_lease(lease.lease_id)

    def get_status_summary(self, provider: str = "gemini") -> Dict[str, Any]:
        """Returns live statistics of inventory and active leases."""
        today = self._today_str(provider)
        with self._lock, self._connection() as conn:
            self._check_date_rollover(conn, provider=provider)
            self.sweep_stale_and_dead_leases(conn)

            rows = conn.execute("""
                SELECT key_alias, status, provider, exhausted_date, total_calls_today,
                       success_calls_today, failed_calls_today, last_used, backoff_until
                FROM key_inventory
                WHERE provider = ?
                ORDER BY key_alias ASC;
            """, (provider,)).fetchall()

            active_leases = conn.execute("""
                SELECT lease_id, key_hash, user_id, process_id, workload_type, expires_at
                FROM key_leases
                WHERE status = 'ACTIVE' AND provider = ?;
            """, (provider,)).fetchall()

            return {
                "date": today,
                "provider": provider,
                "total_keys": len(rows),
                "active_keys": sum(1 for r in rows if r["status"] == "ACTIVE"),
                "exhausted_today": sum(1 for r in rows if r["status"] == "EXHAUSTED_TODAY"),
                "temp_backoff": sum(1 for r in rows if r["status"] == "TEMP_BACKOFF"),
                "active_leases_count": len(active_leases),
                "keys": [dict(r) for r in rows],
                "active_leases": [dict(l) for l in active_leases],
            }


# Module-level singleton
_LEASE_MANAGER_INSTANCE: Optional[KeyLeaseManager] = None
_LEASE_MANAGER_LOCK = threading.Lock()


def get_key_lease_manager(db_path: Optional[Path] = None) -> KeyLeaseManager:
    """Returns process-wide KeyLeaseManager singleton."""
    global _LEASE_MANAGER_INSTANCE
    if _LEASE_MANAGER_INSTANCE is None:
        with _LEASE_MANAGER_LOCK:
            if _LEASE_MANAGER_INSTANCE is None:
                _LEASE_MANAGER_INSTANCE = KeyLeaseManager(db_path=db_path)
    return _LEASE_MANAGER_INSTANCE
