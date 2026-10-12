#!/usr/bin/env python3
"""
Audiobook Factory - Pillar 3.4: Dedicated Key Quarantine & Isolation Engine.
Guarantees physical segregation of permanently invalid, banned, revoked, or suspended keys.
Prevents zombie key resurrection during daily date rollovers, admin resets, or environment rescans.
"""

from __future__ import annotations
import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from audiobook_factory.core.models.db import get_db_connection, DEFAULT_DB_PATH
from audiobook_factory.logger import logger


@dataclass(frozen=True)
class QuarantinedKeyRecord:
    key_hash: str
    key_alias: str
    encrypted_key: str
    provider: str
    quarantine_reason: str
    error_code: int
    error_body_snippet: str
    quarantined_by: str
    quarantined_at: str
    is_permanent: bool


class KeyQuarantineManager:
    """
    Dedicated Control Plane for Key Quarantine & Isolation.
    Physically removes permanently disabled keys from active inventory tables into 'key_quarantine'.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH).resolve()
        self._lock = threading.RLock()
        self._init_schema()

    def _init_schema(self) -> None:
        """Initializes quarantine schema and performance indexes."""
        with self._lock, get_db_connection(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS key_quarantine (
                    key_hash TEXT PRIMARY KEY,
                    key_alias TEXT NOT NULL UNIQUE,
                    encrypted_key TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT 'gemini',
                    quarantine_reason TEXT NOT NULL,
                    error_code INTEGER NOT NULL,
                    error_body_snippet TEXT,
                    quarantined_by TEXT NOT NULL,
                    quarantined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_permanent INTEGER NOT NULL DEFAULT 1
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_quarantine_provider ON key_quarantine(provider);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_quarantine_timestamp ON key_quarantine(quarantined_at);")
            conn.commit()

    def is_quarantined(self, key_or_hash: str) -> bool:
        """Checks if a key, hash, or alias resides in the quarantine vault."""
        if not key_or_hash or not isinstance(key_or_hash, str) or not key_or_hash.strip():
            return False
        clean = key_or_hash.strip()
        from audiobook_factory.core.models.lease_manager import _hash_key
        kh = _hash_key(clean)
        with self._lock, get_db_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM key_quarantine WHERE key_hash = ? OR key_hash = ? OR key_alias = ? OR encrypted_key = ? LIMIT 1;",
                (clean, kh, clean, clean),
            ).fetchone()
            return bool(row)

    def quarantine_key(
        self,
        api_key_or_hash: str,
        reason: str,
        error_code: int = 403,
        error_body: str = "",
        quarantined_by: str = "AUTO_CLASSIFIER",
        provider: str = "gemini",
    ) -> bool:
        """
        Atomically transfers an API key from active inventory/quota ledgers into the quarantine vault.
        Terminates active leases and logs structured audit entry.
        """
        if not api_key_or_hash or not isinstance(api_key_or_hash, str) or not api_key_or_hash.strip():
            return False

        clean_input = api_key_or_hash.strip()
        from audiobook_factory.core.models.lease_manager import _hash_key, _alias_key

        with self._lock, get_db_connection(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE;")

            # 1. Deterministic multi-field lookup across key_hash, key_alias, and encrypted_key
            row = conn.execute("""
                SELECT key_hash, key_alias, encrypted_key, provider
                FROM key_inventory
                WHERE key_hash = ? OR key_alias = ? OR encrypted_key = ?
                LIMIT 1;
            """, (clean_input, clean_input, clean_input)).fetchone()

            if not row:
                # Check legacy table
                try:
                    row_legacy = conn.execute("""
                        SELECT key_hash, key_preview, api_key, provider
                        FROM key_quota_ledger
                        WHERE key_hash = ? OR api_key = ?
                        LIMIT 1;
                    """, (clean_input, clean_input)).fetchone()
                    if row_legacy:
                        kh = row_legacy["key_hash"]
                        raw_k = row_legacy["api_key"]
                        ka = _alias_key(raw_k)
                        prov = row_legacy["provider"] or provider
                    else:
                        kh = _hash_key(clean_input)
                        ka = _alias_key(clean_input)
                        raw_k = clean_input
                        prov = provider
                except sqlite3.OperationalError:
                    kh = _hash_key(clean_input)
                    ka = _alias_key(clean_input)
                    raw_k = clean_input
                    prov = provider
            else:
                kh = row["key_hash"]
                ka = row["key_alias"]
                raw_k = row["encrypted_key"]
                prov = row["provider"]

            # 2. Insert into quarantine vault
            conn.execute("""
                INSERT INTO key_quarantine (
                    key_hash, key_alias, encrypted_key, provider, quarantine_reason,
                    error_code, error_body_snippet, quarantined_by, is_permanent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(key_hash) DO UPDATE SET
                    quarantine_reason = excluded.quarantine_reason,
                    error_code = excluded.error_code,
                    error_body_snippet = excluded.error_body_snippet,
                    quarantined_by = excluded.quarantined_by,
                    quarantined_at = CURRENT_TIMESTAMP;
            """, (kh, ka, raw_k, prov, reason[:100], int(error_code), str(error_body)[:500], quarantined_by))

            # 3. Clean up associated leases and quota ledger rows to satisfy foreign key constraints
            conn.execute("DELETE FROM key_leases WHERE key_hash = ?;", (kh,))
            conn.execute("DELETE FROM model_quota_ledger WHERE key_hash = ?;", (kh,))
            if len(kh) == 16:
                conn.execute("DELETE FROM model_quota_ledger WHERE key_hash = ?;", (kh[:12],))

            # 4. Physically delete from active inventory table
            conn.execute("DELETE FROM key_inventory WHERE key_hash = ?;", (kh,))

            # 5. Invalidate legacy quota ledger if exists
            try:
                conn.execute("UPDATE key_quota_ledger SET status = 'INVALID' WHERE key_hash = ?;", (kh,))
                if len(kh) == 16:
                    conn.execute("UPDATE key_quota_ledger SET status = 'INVALID' WHERE key_hash = ?;", (kh[:12],))
            except sqlite3.OperationalError:
                pass

            # 6. Structured audit log
            conn.execute("""
                INSERT INTO key_audit_log (
                    event_type, lease_id, key_alias, user_id, process_id, provider, status_code, error_summary
                ) VALUES ('QUARANTINE', 'NONE', ?, 'SYSTEM', 0, ?, ?, ?);
            """, (ka, prov, int(error_code), f"[{error_code}] {reason[:80]}"))

            conn.commit()
            logger.critical(f"  [QUARANTINE ENFORCED] Key {ka} physically segregated: {reason} (Code: {error_code})")
            return True

    def list_quarantined(self, provider: Optional[str] = None) -> List[QuarantinedKeyRecord]:
        """Returns all quarantined keys sorted by most recently quarantined."""
        with self._lock, get_db_connection(self.db_path) as conn:
            if provider:
                rows = conn.execute(
                    "SELECT * FROM key_quarantine WHERE provider = ? ORDER BY quarantined_at DESC;",
                    (provider,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM key_quarantine ORDER BY quarantined_at DESC;"
                ).fetchall()
            return [QuarantinedKeyRecord(**dict(r)) for r in rows]

    def get_quarantined(self, key_alias_or_hash: str) -> Optional[QuarantinedKeyRecord]:
        """Fetches details for a single quarantined key by alias or hash."""
        with self._lock, get_db_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM key_quarantine WHERE key_alias = ? OR key_hash = ? LIMIT 1;",
                (key_alias_or_hash, key_alias_or_hash),
            ).fetchone()
            if row:
                return QuarantinedKeyRecord(**dict(row))
            return None

    def purge_keys(
        self,
        key_aliases_or_hashes: Optional[List[str]] = None,
        purge_all: bool = False,
        provider: Optional[str] = None,
    ) -> int:
        """
        Permanently purges specified or all keys from the quarantine vault and active databases.
        This operation is irreversible.
        """
        with self._lock, get_db_connection(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE;")
            if purge_all:
                if provider:
                    cur = conn.execute("DELETE FROM key_quarantine WHERE provider = ?;", (provider,))
                else:
                    cur = conn.execute("DELETE FROM key_quarantine;")
                reaped = cur.rowcount
            elif key_aliases_or_hashes:
                reaped = 0
                for item in key_aliases_or_hashes:
                    cur = conn.execute(
                        "DELETE FROM key_quarantine WHERE key_alias = ? OR key_hash = ?;",
                        (item, item),
                    )
                    reaped += cur.rowcount
            else:
                conn.commit()
                return 0

            conn.commit()
            logger.info(f"  [QUARANTINE PURGE] Permanently deleted {reaped} keys from quarantine vault.")
            return reaped

    def export_quarantined(self, output_path: Path, include_plaintext: bool = False) -> int:
        """Exports quarantine manifest to a JSON file for secret rotation or compliance reports."""
        records = self.list_quarantined()
        data = []
        for r in records:
            item: Dict[str, Any] = {
                "key_alias": r.key_alias,
                "key_hash": r.key_hash,
                "provider": r.provider,
                "quarantine_reason": r.quarantine_reason,
                "error_code": r.error_code,
                "error_body_snippet": r.error_body_snippet,
                "quarantined_by": r.quarantined_by,
                "quarantined_at": r.quarantined_at,
            }
            if include_plaintext:
                item["api_key"] = r.encrypted_key
            data.append(item)

        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return len(data)

    def restore_key(self, key_alias_or_hash: str) -> bool:
        """
        Explicit admin recovery: Restores a false-positive key from quarantine back to active inventory.
        """
        with self._lock, get_db_connection(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE;")
            row = conn.execute(
                "SELECT * FROM key_quarantine WHERE key_alias = ? OR key_hash = ? LIMIT 1;",
                (key_alias_or_hash, key_alias_or_hash),
            ).fetchone()
            if not row:
                conn.commit()
                return False

            # 1. Re-insert into active key_inventory
            conn.execute("""
                INSERT INTO key_inventory (
                    key_hash, key_alias, encrypted_key, provider, status
                ) VALUES (?, ?, ?, ?, 'ACTIVE')
                ON CONFLICT(key_hash) DO UPDATE SET
                    status = 'ACTIVE',
                    exhausted_date = NULL,
                    backoff_until = NULL,
                    failed_calls_today = 0;
            """, (row["key_hash"], row["key_alias"], row["encrypted_key"], row["provider"]))

            # 2. Sync to legacy table if exists
            try:
                conn.execute("""
                    UPDATE key_quota_ledger
                    SET status = 'ACTIVE', exhausted_date = NULL, backoff_until = NULL
                    WHERE key_hash = ?;
                """, (row["key_hash"],))
                if len(row["key_hash"]) == 16:
                    conn.execute("""
                        UPDATE key_quota_ledger
                        SET status = 'ACTIVE', exhausted_date = NULL, backoff_until = NULL
                        WHERE key_hash = ?;
                    """, (row["key_hash"][:12],))
            except sqlite3.OperationalError:
                pass

            # 3. Remove from quarantine vault
            conn.execute("DELETE FROM key_quarantine WHERE key_hash = ?;", (row["key_hash"],))

            # 4. Audit event
            conn.execute("""
                INSERT INTO key_audit_log (
                    event_type, lease_id, key_alias, user_id, process_id, provider, error_summary
                ) VALUES ('RESTORE', 'NONE', ?, 'ADMIN', 0, ?, 'Restored from quarantine');
            """, (row["key_alias"], row["provider"]))

            conn.commit()
            logger.info(f"  [QUARANTINE RESTORED] Key {row['key_alias']} restored to active inventory.")
            return True


# Module-level singleton
_QUARANTINE_MANAGER_INSTANCE: Optional[KeyQuarantineManager] = None
_QUARANTINE_LOCK = threading.Lock()


def get_key_quarantine_manager(db_path: Optional[Path] = None) -> KeyQuarantineManager:
    """Returns process-wide singleton for KeyQuarantineManager."""
    global _QUARANTINE_MANAGER_INSTANCE
    if db_path is not None:
        target_path = Path(db_path).resolve()
        if _QUARANTINE_MANAGER_INSTANCE is None or _QUARANTINE_MANAGER_INSTANCE.db_path != target_path:
            return KeyQuarantineManager(db_path=target_path)
    if _QUARANTINE_MANAGER_INSTANCE is None:
        with _QUARANTINE_LOCK:
            if _QUARANTINE_MANAGER_INSTANCE is None:
                _QUARANTINE_MANAGER_INSTANCE = KeyQuarantineManager(db_path=db_path)
    return _QUARANTINE_MANAGER_INSTANCE
