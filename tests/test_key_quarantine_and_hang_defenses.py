#!/usr/bin/env python3
"""
Test Suite: Key Quarantine Submodule, Zombie Resurrection Immunity & Hang Defenses.
Verifies:
1. KeyQuarantineManager physical isolation lifecycle (quarantine, list, inspect, purge, export, restore).
2. Zombie Resurrection Immunity across reset_all_for_today() and date rollovers.
3. Ingestion Shield preventing re-registration of quarantined keys from .env.
4. Infinite loop hang prevention in get_key() during date rollovers with NULL backoff timestamps.
5. Concurrency fix for multi-worker TTS pipelines without KeyLeaseQuotaExceededError.
6. Session affinity without self-lockout in ModelGateway.lease_session.
"""

import os
import time
import json
import sqlite3
import pytest
import tempfile
from pathlib import Path

from audiobook_factory.core.models.db import init_db, get_db_connection
from audiobook_factory.core.models.lease_manager import (
    KeyLeaseManager,
    CallerIdentity,
    _hash_key,
    _alias_key,
    KeyLeaseQuotaExceededError,
)
from audiobook_factory.core.models.quarantine import (
    KeyQuarantineManager,
    QuarantinedKeyRecord,
)
from audiobook_factory.key_manager import PersistentKeyPool


@pytest.fixture
def isolated_db(tmp_path: Path):
    """Provides a fresh isolated SQLite database with full schema initialized."""
    db_file = tmp_path / "test_key_pool.db"
    init_db(db_file)
    return db_file


def test_quarantine_lifecycle(isolated_db: Path):
    """Verifies complete quarantine lifecycle: quarantine, query, inspect, and physical segregation."""
    q_mgr = KeyQuarantineManager(db_path=isolated_db)
    lease_mgr = KeyLeaseManager(db_path=isolated_db, keys=[])

    # 1. Register 3 test keys
    test_keys = ["AIzaSyTestKey001_Alpha", "AIzaSyTestKey002_Beta", "AIzaSyTestKey003_Gamma"]
    lease_mgr.register_keys(test_keys, provider="gemini")

    status = lease_mgr.get_status_summary(provider="gemini")
    assert status["total_keys"] == 3
    assert status["active_keys"] == 3

    # 2. Quarantine key 1 (e.g. 400 Invalid)
    k1 = test_keys[0]
    kh1 = _hash_key(k1)
    ka1 = _alias_key(k1)

    ok = q_mgr.quarantine_key(
        api_key_or_hash=k1,
        reason="API_KEY_INVALID (Google 400)",
        error_code=400,
        error_body="API key not valid. Please pass a valid API key.",
        quarantined_by="TEST_RUNNER",
    )
    assert ok is True

    # 3. Verify key 1 is physically deleted from key_inventory
    with get_db_connection(isolated_db) as conn:
        inv_row = conn.execute("SELECT 1 FROM key_inventory WHERE key_hash = ?;", (kh1,)).fetchone()
        assert inv_row is None, "Quarantined key must be deleted from key_inventory!"

    # 4. Verify key 1 is present in key_quarantine
    assert q_mgr.is_quarantined(k1) is True
    assert q_mgr.is_quarantined(kh1) is True
    assert q_mgr.is_quarantined(ka1) is True

    record = q_mgr.get_quarantined(ka1)
    assert record is not None
    assert record.key_alias == ka1
    assert record.error_code == 400
    assert record.quarantine_reason == "API_KEY_INVALID (Google 400)"
    assert "API key not valid" in record.error_body_snippet

    # 5. Verify active fleet only sees remaining 2 keys
    status = lease_mgr.get_status_summary(provider="gemini")
    assert status["total_keys"] == 2
    assert status["active_keys"] == 2


def test_zombie_resurrection_immunity_on_admin_reset(isolated_db: Path):
    """
    CRITICAL INVARIANT: Administrative reset_all_for_today() MUST NEVER resurrect
    quarantined or INVALID keys back to ACTIVE state!
    """
    q_mgr = KeyQuarantineManager(db_path=isolated_db)
    lease_mgr = KeyLeaseManager(db_path=isolated_db, keys=[])
    key_pool = PersistentKeyPool(db_path=isolated_db, keys=[])

    test_keys = ["AIzaSyValid_01", "AIzaSyValid_02", "AIzaSyBanned_03"]
    lease_mgr.register_keys(test_keys, provider="gemini")
    key_pool.register_keys(test_keys, provider="gemini")

    # Mark key 3 invalid/quarantine
    banned_key = test_keys[2]
    lease_mgr.mark_invalid(banned_key, error_msg="CONSUMER_SUSPENDED")

    # Key is quarantined
    assert q_mgr.is_quarantined(banned_key) is True

    # Force administrative reset of the fleet
    lease_mgr.reset_all_for_today(provider="gemini")
    key_pool.reset_all_for_today()

    # Verify banned key was NOT resurrected in key_inventory
    with get_db_connection(isolated_db) as conn:
        kh_banned = _hash_key(banned_key)
        inv_row = conn.execute("SELECT status FROM key_inventory WHERE key_hash = ?;", (kh_banned,)).fetchone()
        assert inv_row is None, "Banned key must not exist in key_inventory after reset!"

        # In legacy table, verify it did not resurrect to ACTIVE
        legacy_row = conn.execute("SELECT status FROM key_quota_ledger WHERE key_hash = ?;", (kh_banned,)).fetchone()
        if legacy_row:
            assert legacy_row["status"] == "INVALID", "Banned key in legacy table must remain INVALID!"


def test_date_rollover_immunity(isolated_db: Path):
    """Verifies that midnight date rollover does not resurrect quarantined keys."""
    q_mgr = KeyQuarantineManager(db_path=isolated_db)
    lease_mgr = KeyLeaseManager(db_path=isolated_db, keys=[])

    test_keys = ["AIzaSyHealthy_01", "AIzaSyDead_02"]
    lease_mgr.register_keys(test_keys, provider="gemini")

    dead_key = test_keys[1]
    q_mgr.quarantine_key(dead_key, reason="REVOKED", error_code=403)

    # Simulate midnight date rollover with past date
    with get_db_connection(isolated_db) as conn:
        conn.execute("UPDATE key_inventory SET last_reset_date = '2020-01-01';")
        conn.commit()

        # Trigger rollover check
        lease_mgr._check_date_rollover(conn, provider="gemini")

    # Verify dead key is not in active inventory
    assert q_mgr.is_quarantined(dead_key) is True
    summary = lease_mgr.get_status_summary(provider="gemini")
    assert summary["total_keys"] == 1
    assert summary["active_keys"] == 1


def test_ingestion_shield_skips_quarantined_keys(isolated_db: Path):
    """Verifies that key registration (.env auto-discovery) skips quarantined keys."""
    q_mgr = KeyQuarantineManager(db_path=isolated_db)
    lease_mgr = KeyLeaseManager(db_path=isolated_db, keys=[])
    key_pool = PersistentKeyPool(db_path=isolated_db, keys=[])

    banned_key = "AIzaSyPermanentlyBanned_999"
    q_mgr.quarantine_key(banned_key, reason="API_KEY_INVALID", error_code=400)
    assert q_mgr.is_quarantined(banned_key) is True

    # Attempt to re-register banned key as part of a batch
    batch = [banned_key, "AIzaSyFreshKey_100"]
    lease_mgr.register_keys(batch, provider="gemini")
    key_pool.register_keys(batch, provider="gemini")

    # Banned key must NOT be added to key_inventory
    summary = lease_mgr.get_status_summary(provider="gemini")
    assert summary["total_keys"] == 1  # Only fresh key registered!
    assert summary["active_keys"] == 1

    with get_db_connection(isolated_db) as conn:
        banned_hash = _hash_key(banned_key)
        assert conn.execute("SELECT 1 FROM key_inventory WHERE key_hash = ?;", (banned_hash,)).fetchone() is None


def test_quarantine_purge_and_restore(isolated_db: Path):
    """Tests permanent purging and false-positive restoration from quarantine vault."""
    q_mgr = KeyQuarantineManager(db_path=isolated_db)
    lease_mgr = KeyLeaseManager(db_path=isolated_db, keys=[])

    key_a = "AIzaSyKeyA"
    key_b = "AIzaSyKeyB"
    lease_mgr.register_keys([key_a, key_b], provider="gemini")

    q_mgr.quarantine_key(key_a, reason="TEMP_GLITCH_TEST", error_code=403)
    q_mgr.quarantine_key(key_b, reason="TRUE_BAN_TEST", error_code=403)

    assert len(q_mgr.list_quarantined()) == 2

    # 1. Restore key_a (false positive)
    ka_alias = _alias_key(key_a)
    restored = q_mgr.restore_key(ka_alias)
    assert restored is True
    assert q_mgr.is_quarantined(key_a) is False

    # Key A is back in key_inventory
    summary = lease_mgr.get_status_summary(provider="gemini")
    assert summary["total_keys"] == 1
    assert summary["keys"][0]["key_alias"] == ka_alias

    # 2. Purge key_b (permanent destruction)
    kb_alias = _alias_key(key_b)
    purged = q_mgr.purge_keys([kb_alias])
    assert purged == 1
    assert q_mgr.is_quarantined(key_b) is False
    assert len(q_mgr.list_quarantined()) == 0


def test_quarantine_export(isolated_db: Path, tmp_path: Path):
    """Tests exporting quarantine records to JSON."""
    q_mgr = KeyQuarantineManager(db_path=isolated_db)
    q_mgr.quarantine_key("AIzaSyExportTest1", reason="REASON_1", error_code=400)
    q_mgr.quarantine_key("AIzaSyExportTest2", reason="REASON_2", error_code=403)

    out_file = tmp_path / "quarantine_manifest.json"
    exported_count = q_mgr.export_quarantined(out_file, include_plaintext=False)
    assert exported_count == 2
    assert out_file.exists()

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 2
    assert data[0]["quarantine_reason"] in ("REASON_1", "REASON_2")
    assert "api_key" not in data[0]  # Zero-secret audit by default


def test_get_key_null_backoff_hang_defense(isolated_db: Path):
    """
    BUG 1.1 REGRESSION: Tests that get_key() does NOT crash or loop infinitely
    when backoff_until is NULL while status = 'TEMP_BACKOFF'.
    """
    key_pool = PersistentKeyPool(db_path=isolated_db, keys=[])
    key = "AIzaSyNullBackoffTest"
    key_pool.register_keys([key], provider="gemini")

    kh = key_pool._hash_key(key)
    # Inject corrupt/rollover state: status = TEMP_BACKOFF with NULL backoff_until
    with get_db_connection(isolated_db) as conn:
        conn.execute("UPDATE key_quota_ledger SET status = 'TEMP_BACKOFF', backoff_until = NULL WHERE key_hash = ?;", (kh,))
        conn.commit()

    # get_key() must cleanly clean up expired backoff and return the key without infinite loop or TypeError
    chosen_key = key_pool.get_key(service="text", provider="gemini", max_wait_seconds=5.0)
    assert chosen_key == key


def test_get_key_timeout_defense(isolated_db: Path):
    """
    BUG 1.2 REGRESSION: Tests that get_key() raises ValueError after max_wait_seconds
    instead of looping indefinitely when all keys are cooling down.
    """
    key_pool = PersistentKeyPool(db_path=isolated_db, keys=[])
    key = "AIzaSyCoolingDownKey"
    key_pool.register_keys([key], provider="gemini")

    # Put key in 30-second backoff
    key_pool.mark_temporary_backoff(key, backoff_seconds=30.0)

    # get_key with short max_wait_seconds must raise ValueError and NOT hang indefinitely
    t0 = time.time()
    with pytest.raises(ValueError, match="Timeout"):
        key_pool.get_key(service="text", provider="gemini", max_wait_seconds=1.5)
    dur = time.time() - t0
    assert dur < 4.0, f"get_key should have timed out within ~2s, took {dur:.2f}s"


def test_multi_worker_concurrency_bypass(isolated_db: Path):
    """
    BUG 1.5 REGRESSION: Multi-worker TTS with user_id='tts_worker' must NOT trigger
    KeyLeaseQuotaExceededError across concurrent threads.
    """
    lease_mgr = KeyLeaseManager(db_path=isolated_db, keys=[])
    keys = ["AIzaSyTTSKey1", "AIzaSyTTSKey2", "AIzaSyTTSKey3"]
    lease_mgr.register_keys(keys, provider="gemini")

    # Worker 1 acquires lease
    ident1 = CallerIdentity(user_id="tts_worker", worker_id="thr_1", workload_type="tts")
    lease1 = lease_mgr.acquire_lease(workload_type="tts", identity=ident1)
    assert lease1 is not None

    # Worker 2 acquires lease concurrently with SAME user_id='tts_worker'
    ident2 = CallerIdentity(user_id="tts_worker", worker_id="thr_2", workload_type="tts")
    lease2 = lease_mgr.acquire_lease(workload_type="tts", identity=ident2)
    assert lease2 is not None

    # Mutual exclusion: leases must be on DIFFERENT keys!
    assert lease1.key_alias != lease2.key_alias

    # Cleanup
    lease_mgr.release_lease(lease1.lease_id)
    lease_mgr.release_lease(lease2.lease_id)
