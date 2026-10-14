#!/usr/bin/env python3
"""
Audiobook Factory - Core SQLite Database & Storage Engine.
Provides transactional connection management, WAL mode, busy timeout handling,
and schema initialization for key inventory, leases, and audit logs.
"""

from __future__ import annotations
import sqlite3
import os
import contextlib
import threading
from pathlib import Path
from typing import Optional, Generator

# Default persistent database path inside audiobooks directory (overridable via KEY_POOL_DB_PATH)
DEFAULT_DB_PATH = Path(
    os.environ.get("KEY_POOL_DB_PATH")
    or (Path(__file__).resolve().parent.parent.parent.parent / "audiobooks" / "key_pool_state.db")
)

_db_lock = threading.RLock()


@contextlib.contextmanager
def get_db_connection(db_path: Optional[Path] = None, timeout: float = 30.0) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager providing an ACID-safe SQLite connection configured for concurrent WAL access.
    Automatically closes the connection handle upon exit.
    """
    path = Path(db_path or DEFAULT_DB_PATH).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    """
    Initializes all core tables, indexes, and constraints for the Model & Keys control plane.
    Idempotent and safe to run on startup.
    """
    with _db_lock, get_db_connection(db_path) as conn:
        # 1. Master Key Inventory
        conn.execute("""
            CREATE TABLE IF NOT EXISTS key_inventory (
                key_hash TEXT PRIMARY KEY,
                key_alias TEXT NOT NULL UNIQUE,
                encrypted_key TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT 'gemini',
                tier TEXT NOT NULL DEFAULT 'free',
                allowed_services TEXT NOT NULL DEFAULT '["tts"]',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                exhausted_date TEXT,
                backoff_until TIMESTAMP,
                total_calls_today INTEGER DEFAULT 0,
                success_calls_today INTEGER DEFAULT 0,
                failed_calls_today INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                last_reset_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Active Leases Table (Multi-User & Multi-Process Mutual Exclusion)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS key_leases (
                lease_id TEXT PRIMARY KEY,
                key_hash TEXT NOT NULL,
                key_alias TEXT NOT NULL,
                provider TEXT NOT NULL,
                workstation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                process_id INTEGER NOT NULL,
                worker_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                workload_type TEXT NOT NULL,
                leased_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                heartbeat_at TIMESTAMP NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                FOREIGN KEY(key_hash) REFERENCES key_inventory(key_hash)
            );
        """)

        # 3. Model-Specific Quota Ledger (Per-Model Quota Isolation)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS model_quota_ledger (
                key_hash TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT 'gemini',
                model TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                exhausted_date TEXT,
                total_calls_today INTEGER DEFAULT 0,
                success_calls_today INTEGER DEFAULT 0,
                failed_calls_today INTEGER DEFAULT 0,
                total_tokens_today INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                backoff_until TIMESTAMP,
                last_error TEXT,
                last_reset_date TEXT,
                PRIMARY KEY (key_hash, model)
            );
        """)

        # 4. Zero-Secret Audit Trail (Structured Event Log)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS key_audit_log (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                lease_id TEXT NOT NULL,
                key_alias TEXT NOT NULL,
                user_id TEXT NOT NULL,
                process_id INTEGER NOT NULL,
                model_id TEXT,
                provider TEXT NOT NULL,
                duration_ms INTEGER,
                status_code INTEGER,
                error_summary TEXT
            );
        """)

        # 5. Key Quarantine Vault (Physical Segregation of Permanently Banned/Invalid Keys)
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

        # Indexes for Sub-Millisecond Reservation Lookups
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leases_active ON key_leases(key_hash, status, expires_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leases_user ON key_leases(user_id, workload_type, status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_inventory_status ON key_inventory(provider, status, backoff_until);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quarantine_provider ON key_quarantine(provider);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON key_audit_log(timestamp);")

        conn.commit()
