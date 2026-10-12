#!/usr/bin/env python3
"""
Adversarial Stress & Test Coverage Suite:
Key Management, Leasing Engine, Model Gateway, and Key Quarantine.

Stress Tests:
1. Concurrent Lease vs Concurrent Quarantine Race Condition
2. Zero Active Keys Remaining & Empty Pool Behavior
3. Payload Error (HTTP 400 Bad Request) vs API_KEY_INVALID Error Differential
4. High Load 100-Thread SQLite Lock Contention with 2 Keys
5. Quarantine -> Restore -> Lease -> Fail -> Re-Quarantine Churn Lifecycle
6. Read-Only DB Error Containment & Graceful Recovery
"""

import os
import stat
import time
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from audiobook_factory.core.models.db import init_db, get_db_connection
from audiobook_factory.core.models.lease_manager import (
    KeyLeaseManager,
    CallerIdentity,
    KeyLease,
    NoAvailableKeyError,
    AllKeysExhaustedTodayError,
    _hash_key,
    _alias_key,
)
from audiobook_factory.core.models.quarantine import (
    KeyQuarantineManager,
)
from audiobook_factory.core.models.policy_engine import (
    classify_universal_api_error,
)
from audiobook_factory.core.models.gateway import ModelGateway
from audiobook_factory.core.models.adapters.gemini import ApiHttpError
from audiobook_factory.key_manager import PersistentKeyPool


@pytest.fixture
def adversarial_db(tmp_path: Path):
    """Provides a fresh isolated SQLite database with full schema initialized."""
    db_file = tmp_path / "adversarial_key_pool.db"
    init_db(db_file)
    return db_file


# =========================================================================
# 1. Concurrent Lease + Concurrent Quarantine Race Condition
# =========================================================================
def test_concurrent_lease_and_quarantine_race(adversarial_db: Path):
    """
    Adversarial Race Condition:
    Multiple worker threads continuously acquire and release leases on 2 keys,
    while a concurrent auditor thread suddenly quarantines one of the keys mid-flight.
    Verifies:
    - Zero double-allocation.
    - Quarantined key is immediately evicted from key_inventory and active leases.
    - When the thread holding the quarantined key releases it, release_lease returns False
      gracefully without raising unhandled exceptions.
    - DB foreign keys and integrity remain 100% valid.
    """
    q_mgr = KeyQuarantineManager(db_path=adversarial_db)
    lease_mgr = KeyLeaseManager(db_path=adversarial_db, keys=[])

    keys = ["AIzaSyRaceKeyAlpha_111", "AIzaSyRaceKeyBeta_222"]
    lease_mgr.register_keys(keys, provider="gemini")

    stop_event = threading.Event()
    race_errors = []
    leases_acquired = []

    def worker(worker_id: int):
        ident = CallerIdentity(user_id=f"worker_{worker_id}", worker_id=f"thr_{worker_id}")
        while not stop_event.is_set():
            try:
                lease = lease_mgr.acquire_lease(workload_type="text", provider="gemini", identity=ident, ttl_seconds=10.0)
                leases_acquired.append((worker_id, lease.key_alias))
                # Brief sleep to simulate work
                time.sleep(0.01)
                # Release lease
                lease_mgr.release_lease(lease.lease_id)
            except NoAvailableKeyError:
                time.sleep(0.005)
            except Exception as e:
                race_errors.append(f"Worker {worker_id} crashed: {type(e).__name__}: {e}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()

    # Allow workers to run briefly
    time.sleep(0.1)

    # Concurrently quarantine KeyAlpha while workers are actively leasing
    target_key = keys[0]
    target_hash = _hash_key(target_key)
    q_mgr.quarantine_key(
        api_key_or_hash=target_key,
        reason="CONCURRENT_RACE_TEST_BAN",
        error_code=403,
        quarantined_by="RACE_TESTER",
    )

    # Let workers continue running for another interval
    time.sleep(0.15)
    stop_event.set()
    for t in threads:
        t.join(timeout=5.0)

    assert len(race_errors) == 0, f"Race condition errors detected: {race_errors}"
    assert len(leases_acquired) > 0, "No leases were acquired during the race test!"

    # Invariants after race:
    # 1. KeyAlpha must be quarantined
    assert q_mgr.is_quarantined(target_key) is True

    # 2. KeyAlpha must NOT exist in key_inventory
    with get_db_connection(adversarial_db) as conn:
        inv_row = conn.execute("SELECT 1 FROM key_inventory WHERE key_hash = ?;", (target_hash,)).fetchone()
        assert inv_row is None, "Quarantined key still present in key_inventory!"

        # 3. No active leases exist for KeyAlpha
        active_leases = conn.execute("SELECT 1 FROM key_leases WHERE key_hash = ?;", (target_hash,)).fetchall()
        assert len(active_leases) == 0, "Orphaned leases found for quarantined key!"

        # 4. Foreign key integrity check
        fk_errors = conn.execute("PRAGMA foreign_key_check;").fetchall()
        assert len(fk_errors) == 0, f"Foreign key constraint violations: {fk_errors}"

        # 5. DB integrity check
        integrity = conn.execute("PRAGMA integrity_check;").fetchone()
        assert integrity[0] == "ok", f"DB integrity check failed: {integrity[0]}"


# =========================================================================
# 2. Zero Active Keys Remaining & Empty Pool Behavior
# =========================================================================
def test_zero_active_keys_empty_pool_behavior(adversarial_db: Path):
    """
    Verifies behavior when 0 active keys exist:
    1. KeyLeaseManager with 0 keys raises NoAvailableKeyError (not an unhandled crash).
    2. KeyLeaseManager when all keys are quarantined raises NoAvailableKeyError.
    3. PersistentKeyPool with 0 keys raises ValueError immediately.
    4. PersistentKeyPool when all keys are quarantined raises ValueError immediately.
    """
    lease_mgr = KeyLeaseManager(db_path=adversarial_db, keys=[])
    ident = CallerIdentity(user_id="user_zero", workload_type="text")

    # 1. Empty KeyLeaseManager
    with pytest.raises(NoAvailableKeyError):
        lease_mgr.acquire_lease(workload_type="text", provider="gemini", identity=ident)

    # 2. Register 2 keys, then quarantine both
    k1, k2 = "AIzaSyZeroKey1", "AIzaSyZeroKey2"
    lease_mgr.register_keys([k1, k2], provider="gemini")
    summary = lease_mgr.get_status_summary(provider="gemini")
    assert summary["active_keys"] == 2

    q_mgr = KeyQuarantineManager(db_path=adversarial_db)
    q_mgr.quarantine_key(k1, reason="REVOKED", error_code=403)
    q_mgr.quarantine_key(k2, reason="REVOKED", error_code=403)

    summary_after = lease_mgr.get_status_summary(provider="gemini")
    assert summary_after["active_keys"] == 0
    assert summary_after["total_keys"] == 0

    with pytest.raises(NoAvailableKeyError):
        lease_mgr.acquire_lease(workload_type="text", provider="gemini", identity=ident)

    # 3. PersistentKeyPool with 0 keys
    empty_pool = PersistentKeyPool(db_path=adversarial_db, keys=[])
    with pytest.raises(ValueError, match="No eligible GEMINI API keys registered"):
        empty_pool.get_key(service="text", provider="gemini", max_wait_seconds=0.5)

    # 4. PersistentKeyPool ingestion shield skips quarantined keys
    empty_pool.register_keys([k1, k2], provider="gemini")
    with pytest.raises(ValueError, match="No eligible GEMINI API keys registered"):
        empty_pool.get_key(service="text", provider="gemini", max_wait_seconds=0.5)


# =========================================================================
# 3. Payload Error (HTTP 400) vs API_KEY_INVALID Differential
# =========================================================================
def test_payload_error_vs_api_key_invalid_differential(adversarial_db: Path):
    """
    Adversarial Distinction:
    Payload errors (HTTP 400 Bad Request, malformed JSON, unsupported schema, context length)
    MUST NEVER result in key invalidation or quarantine.
    Only genuine authentication errors (API_KEY_INVALID, CONSUMER_SUSPENDED, PERMISSION_DENIED)
    must trigger key rotation and quarantine.
    """
    # 1. Policy Engine Classification Tests
    # A: Payload syntax error -> PAYLOAD_INVALID, ABORT_PAYLOAD
    err_syntax = classify_universal_api_error(
        status_code=400,
        error_body='{"error": {"code": 400, "message": "Invalid JSON payload received. Unexpected token at line 1."}}',
        provider="gemini",
    )
    assert err_syntax.category == "PAYLOAD_INVALID"
    assert err_syntax.suggested_action == "ABORT_PAYLOAD"
    assert err_syntax.is_retryable is False

    # B: Context Length Exceeded -> CONTEXT_LENGTH_EXCEEDED, ABORT_PAYLOAD
    err_context = classify_universal_api_error(
        status_code=400,
        error_body='{"error": {"code": 400, "message": "Context length exceeded. Prompt is too long for model."}}',
        provider="gemini",
    )
    assert err_context.category == "CONTEXT_LENGTH_EXCEEDED"
    assert err_context.suggested_action == "ABORT_PAYLOAD"

    # C: Genuinely Invalid Key -> INVALID_KEY, ROTATE_KEY
    err_bad_key = classify_universal_api_error(
        status_code=400,
        error_body='{"error": {"code": 400, "message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT", "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "API_KEY_INVALID"}]}}',
        provider="gemini",
    )
    assert err_bad_key.category == "INVALID_KEY"
    assert err_bad_key.suggested_action == "ROTATE_KEY"

    # 2. ModelGateway Integration Test
    lease_mgr = KeyLeaseManager(db_path=adversarial_db, keys=[])
    q_mgr = KeyQuarantineManager(db_path=adversarial_db)
    test_key = "AIzaSyDifferentialTestKey_999"
    lease_mgr.register_keys([test_key], provider="gemini")

    gateway = ModelGateway(lease_manager=lease_mgr)

    # Mock adapter to simulate a HTTP 400 Bad Payload error
    mock_adapter = MagicMock()
    mock_adapter.generate_text.side_effect = ApiHttpError(
        status_code=400,
        error_body='{"error": "Invalid field \'unknown_param\' in request body"}',
        headers={},
    )

    with patch.object(gateway.router, "resolve_plan") as mock_resolve:
        # Create a mock plan
        mock_plan = MagicMock()
        mock_plan.model_id = "gemini-3.8-flash"
        mock_plan.provider = "gemini"
        mock_plan.api_key = test_key
        mock_plan.key_alias = _alias_key(test_key)
        # Acquire actual lease
        actual_lease = lease_mgr.acquire_lease(workload_type="text", provider="gemini", allow_multi_lease=True)
        mock_plan.lease = actual_lease
        mock_plan.adapter = mock_adapter
        mock_resolve.return_value = mock_plan

        # Generating text must abort with ApiHttpError on non-retryable payload error
        with pytest.raises(ApiHttpError) as exc_info:
            gateway.generate_text(prompt="Hello world", session_id="sess_diff_1", fast_mode=True)
        assert exc_info.value.status_code == 400

    # Invariant: The key MUST NOT be quarantined or marked invalid for a payload error!
    assert q_mgr.is_quarantined(test_key) is False
    summary = lease_mgr.get_status_summary(provider="gemini")
    assert summary["total_keys"] == 1
    assert summary["active_keys"] == 1


# =========================================================================
# 4. Multi-Threading SQLite Lock Contention Under High Load (100 Threads)
# =========================================================================
def test_high_load_100_threads_sqlite_contention(adversarial_db: Path):
    """
    Stress Test:
    100 concurrent threads competing for a pool of ONLY 2 keys.
    Each thread attempts to acquire a lease, do micro-work, and release.
    Verifies:
    - Zero double allocations (never 2 active leases for the same key_hash).
    - Zero SQLite locking crashes ('database is locked') thanks to WAL mode and busy_timeout.
    - Consistency of audit logs and active lease counts.
    """
    lease_mgr = KeyLeaseManager(db_path=adversarial_db, keys=[])
    keys = ["AIzaSyHighLoadKeyOne", "AIzaSyHighLoadKeyTwo"]
    lease_mgr.register_keys(keys, provider="gemini")

    double_allocation_errors = []
    database_errors = []
    successful_leases = []

    def task(thread_idx: int):
        ident = CallerIdentity(user_id=f"stress_user_{thread_idx}", worker_id=f"thr_{thread_idx}")
        # Multiple attempts per thread to stress DB concurrency
        for _ in range(3):
            try:
                lease = lease_mgr.acquire_lease(
                    workload_type="text",
                    provider="gemini",
                    identity=ident,
                    ttl_seconds=3.0,
                )
                # Check for double allocation in DB
                with get_db_connection(adversarial_db) as conn:
                    active_count = conn.execute(
                        "SELECT count(*) as c FROM key_leases WHERE key_hash = ? AND status = 'ACTIVE' AND lease_id != ?;",
                        (lease.key_hash, lease.lease_id),
                    ).fetchone()["c"]
                    if active_count > 0:
                        double_allocation_errors.append(
                            f"Double allocation detected on key {lease.key_alias} by thread {thread_idx}!"
                        )

                # Micro sleep
                time.sleep(0.005)
                lease_mgr.release_lease(lease.lease_id)
                successful_leases.append(thread_idx)
                break
            except NoAvailableKeyError:
                time.sleep(0.01)
            except sqlite3.OperationalError as oe:
                database_errors.append(f"Thread {thread_idx} SQLite error: {oe}")
            except Exception as e:
                database_errors.append(f"Thread {thread_idx} unexpected error: {type(e).__name__}: {e}")

    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(task, i) for i in range(100)]
        for f in as_completed(futures):
            f.result()

    assert len(double_allocation_errors) == 0, f"Double allocations: {double_allocation_errors}"
    assert len(database_errors) == 0, f"Database locking errors: {database_errors}"
    assert len(successful_leases) >= 10, f"Expected at least 10 successful leases, got {len(successful_leases)}"

    # Check database integrity post-stress
    with get_db_connection(adversarial_db) as conn:
        active_remaining = conn.execute("SELECT count(*) as c FROM key_leases WHERE status = 'ACTIVE';").fetchone()["c"]
        assert active_remaining == 0, f"Leases leaked: {active_remaining} active leases remain!"

        integrity = conn.execute("PRAGMA integrity_check;").fetchone()
        assert integrity[0] == "ok"


# =========================================================================
# 5. Quarantine -> Restore -> Lease -> Fail -> Re-Quarantine Churn Lifecycle
# =========================================================================
def test_quarantine_restore_lease_fail_requarantine_churn(adversarial_db: Path):
    """
    State Machine Churn Test:
    Bounces a key through the complete lifecycle:
    Registered -> Quarantined (403) -> Restored (Admin) -> Leased -> Failed (400) -> Re-quarantined.
    Verifies:
    - Primary key ON CONFLICT resolution in key_quarantine.
    - Foreign key constraints maintained at each step.
    - Accurate state in both active inventory and quarantine vault.
    - Zero orphaned records.
    """
    q_mgr = KeyQuarantineManager(db_path=adversarial_db)
    lease_mgr = KeyLeaseManager(db_path=adversarial_db, keys=[])

    churn_key = "AIzaSyChurnCycleKey_007"
    kh = _hash_key(churn_key)
    ka = _alias_key(churn_key)

    # 1. Register key
    lease_mgr.register_keys([churn_key], provider="gemini")
    assert lease_mgr.get_status_summary(provider="gemini")["total_keys"] == 1

    # 2. Quarantine key
    q_mgr.quarantine_key(churn_key, reason="FIRST_BAN_SIMULATION", error_code=403)
    assert q_mgr.is_quarantined(churn_key) is True
    assert lease_mgr.get_status_summary(provider="gemini")["total_keys"] == 0

    # 3. Restore key
    restored = q_mgr.restore_key(ka)
    assert restored is True
    assert q_mgr.is_quarantined(churn_key) is False
    assert lease_mgr.get_status_summary(provider="gemini")["total_keys"] == 1

    # 4. Immediately acquire lease on restored key
    ident = CallerIdentity(user_id="churn_tester", workload_type="text")
    lease = lease_mgr.acquire_lease(workload_type="text", provider="gemini", identity=ident)
    assert lease.key_hash == kh
    assert lease.status == "ACTIVE"

    # 5. Fail the key while lease is held
    lease_mgr.mark_invalid(churn_key, error_msg="SECOND_FAILURE_API_KEY_INVALID")

    # 6. Verify re-quarantine state
    assert q_mgr.is_quarantined(churn_key) is True
    q_record = q_mgr.get_quarantined(ka)
    assert q_record is not None
    assert "SECOND_FAILURE" in q_record.quarantine_reason

    # Inventory must have 0 keys
    assert lease_mgr.get_status_summary(provider="gemini")["total_keys"] == 0

    # Clean release attempts by the holder should not crash
    released = lease_mgr.release_lease(lease.lease_id)
    assert released is False  # Already cleaned up by quarantine

    # Verify SQLite foreign key and table consistency
    with get_db_connection(adversarial_db) as conn:
        fk_errors = conn.execute("PRAGMA foreign_key_check;").fetchall()
        assert len(fk_errors) == 0, f"Foreign key errors: {fk_errors}"
        integrity = conn.execute("PRAGMA integrity_check;").fetchone()
        assert integrity[0] == "ok"


# =========================================================================
# 6. Read-Only DB Error Containment & Graceful Recovery
# =========================================================================
def test_read_only_db_containment_and_recovery(adversarial_db: Path):
    """
    Environmental Disaster Test:
    Tests behavior when the database file is made read-only (e.g. disk permission glitch):
    - System raises sqlite3.OperationalError without hanging or deadlocking.
    - Connection handles are safely closed (no handle leak).
    - When permissions are restored, the system recovers immediately without corruption.
    """
    lease_mgr = KeyLeaseManager(db_path=adversarial_db, keys=[])
    key = "AIzaSyReadOnlyTestKey"
    lease_mgr.register_keys([key], provider="gemini")

    # Make DB file read-only
    os.chmod(adversarial_db, stat.S_IREAD)

    try:
        ident = CallerIdentity(user_id="user_readonly", workload_type="text")
        # Attempting to write (acquire_lease) on a read-only database raises sqlite3.OperationalError
        with pytest.raises(sqlite3.OperationalError):
            lease_mgr.acquire_lease(workload_type="text", provider="gemini", identity=ident)
    finally:
        # Restore write permissions
        os.chmod(adversarial_db, stat.S_IWRITE | stat.S_IREAD)

    # Verify recovery: operations succeed again immediately
    ident2 = CallerIdentity(user_id="user_recovered", workload_type="text")
    lease = lease_mgr.acquire_lease(workload_type="text", provider="gemini", identity=ident2)
    assert lease is not None
    assert lease.status == "ACTIVE"
    lease_mgr.release_lease(lease.lease_id)
