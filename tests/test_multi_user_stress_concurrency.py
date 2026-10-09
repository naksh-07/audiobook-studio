#!/usr/bin/env python3
"""
Multi-User & Multi-Worker Concurrency Stress Test Suite.
========================================================
Validates Phase 5 Concurrency & Safety Contracts:
1. Multi-User Mutual Exclusion: Two users (Alice & Bob) accessing the shared workstation simultaneously.
2. Zero Key Dogpiling: 0% duplicate active leases across concurrent threads.
3. 'One User = One Key per Workload': Enforces mutual exclusion per user.
4. Thundering Herd Under Contention: 20 workers competing for 3 keys.
5. Zero Orphaned Leases: All leases cleaned up or recovered after execution.
"""

import sys
import os
import time
import unittest
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from audiobook_factory.core.models.db import get_db_connection
from audiobook_factory.core.models.lease_manager import (
    KeyLeaseManager,
    CallerIdentity,
    KeyLease,
    KeyLeaseQuotaExceededError,
    NoAvailableKeyError,
)
from audiobook_factory.core.models.gateway import ModelGateway
from audiobook_factory.core.models.registry import get_model_registry
from audiobook_factory.core.models.anti_ban_guard import get_anti_ban_guard
from audiobook_factory.core.models.policy_engine import get_circuit_breaker
from audiobook_factory.core.models.router import RequestRouter
from audiobook_factory.core.models.adapters.base import GenerationResult


class TestMultiUserStressConcurrency(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(WORKSPACE_DIR) / "scratch" / "test_stress"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.tmp_dir / f"test_stress_{int(time.time() * 1000)}_{os.getpid()}.db"

        # 3 distinct keys in the pool
        self.keys = [
            "AIzaSyStressKeyOne11111111",
            "AIzaSyStressKeyTwo22222222",
            "AIzaSyStressKeyThree33333333",
        ]
        self.lease_mgr = KeyLeaseManager(db_path=self.db_path, keys=self.keys)

    def tearDown(self):
        try:
            if self.db_path.exists():
                self.db_path.unlink()
        except OSError:
            pass

    # =========================================================================
    # 1. Multi-User Separation & No Concurrent Collision
    # =========================================================================
    def test_01_two_users_concurrent_leasing(self):
        """Verifies User Alice and User Bob acquire distinct keys simultaneously."""
        ident_alice = CallerIdentity(user_id="user_alice", workload_type="text")
        ident_bob = CallerIdentity(user_id="user_bob", workload_type="text")

        lease_alice = self.lease_mgr.acquire_lease(workload_type="text", provider="gemini", identity=ident_alice)
        lease_bob = self.lease_mgr.acquire_lease(workload_type="text", provider="gemini", identity=ident_bob)

        # Keys must be completely distinct
        self.assertNotEqual(lease_alice.key_hash, lease_bob.key_hash)
        self.assertNotEqual(lease_alice.key_alias, lease_bob.key_alias)
        self.assertNotEqual(lease_alice.api_key, lease_bob.api_key)

        # Release both
        self.lease_mgr.release_lease(lease_alice.lease_id)
        self.lease_mgr.release_lease(lease_bob.lease_id)

        summary = self.lease_mgr.get_status_summary("gemini")
        self.assertEqual(summary["active_leases_count"], 0)

    # =========================================================================
    # 2. Thundering Herd Under Extreme Contention (20 Workers on 3 Keys)
    # =========================================================================
    def test_02_thundering_herd_zero_double_leasing(self):
        """
        20 concurrent workers (each with a unique user_id) attempt to acquire a key.
        At no point in time should the same key have > 1 active lease.
        """
        active_key_hashes = set()
        active_lock = threading.Lock()
        double_lease_violations = []
        successful_leases = []

        def worker_task(worker_idx: int):
            user_id = f"worker_user_{worker_idx}"
            ident = CallerIdentity(user_id=user_id, workload_type="text")

            # Try acquiring lease (timeout 2.5s for 20 threads on mobile)
            start_t = time.time()
            while time.time() - start_t < 2.5:
                try:
                    lease = self.lease_mgr.acquire_lease(
                        workload_type="text",
                        provider="gemini",
                        identity=ident,
                    )

                    with active_lock:
                        if lease.key_hash in active_key_hashes:
                            double_lease_violations.append(lease.key_hash)
                        active_key_hashes.add(lease.key_hash)

                    # Simulate work
                    time.sleep(0.01)

                    with active_lock:
                        active_key_hashes.remove(lease.key_hash)

                    self.lease_mgr.release_lease(lease.lease_id)
                    successful_leases.append(lease.lease_id)
                    return True
                except NoAvailableKeyError:
                    time.sleep(0.005)
                except Exception as e:
                    return False
            return False

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker_task, i) for i in range(20)]
            results = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(double_lease_violations), 0, "Double leasing detected under stress!")
        self.assertGreaterEqual(len(successful_leases), 10, "At least half of workers should have acquired lease.")


        # Assert zero orphaned leases in database
        summary = self.lease_mgr.get_status_summary("gemini")
        self.assertEqual(summary["active_leases_count"], 0)

    # =========================================================================
    # 3. User Concurrency Lock (1 Key per Workload Violation)
    # =========================================================================
    def test_03_same_user_second_concurrent_lease_rejected(self):
        """A single user cannot hold 2 keys concurrently for the same workload without releasing."""
        ident_alice = CallerIdentity(user_id="user_alice", workload_type="text")

        lease1 = self.lease_mgr.acquire_lease(workload_type="text", provider="gemini", identity=ident_alice)
        self.assertIsNotNone(lease1)

        # Second attempt without releasing lease1 must raise KeyLeaseQuotaExceededError
        with self.assertRaises(KeyLeaseQuotaExceededError):
            self.lease_mgr.acquire_lease(workload_type="text", provider="gemini", identity=ident_alice)

        self.lease_mgr.release_lease(lease1.lease_id)

        # After releasing lease1, second attempt succeeds
        lease2 = self.lease_mgr.acquire_lease(workload_type="text", provider="gemini", identity=ident_alice)
        self.assertIsNotNone(lease2)
        self.lease_mgr.release_lease(lease2.lease_id)


if __name__ == "__main__":
    unittest.main()
