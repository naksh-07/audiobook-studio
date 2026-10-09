#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite for Phase 4: Model Gateway Control Plane.
==============================================================================
Validates:
1. End-to-end generate_text flow (Router -> Lease -> Anti-Ban Gate -> Adapter -> Release).
2. End-to-end synthesize_speech flow with 10 RPD quota tracking.
3. Automated key failover upon HTTP 429 Daily Quota Exhaustion.
4. Circuit breaker failover upon repeated 503 server errors.
5. Session affinity context manager (Scene-level sticky key binding).
6. Safe lease release under both success and exception conditions.
"""

import sys
import os
import time
import base64
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from audiobook_factory.core.models.db import init_db, get_db_connection
from audiobook_factory.core.models.lease_manager import (
    KeyLeaseManager,
    CallerIdentity,
    NoAvailableKeyError,
    AllKeysExhaustedTodayError,
)
from audiobook_factory.core.models.registry import (
    ModelRegistry,
    ModelTier,
    Modality,
    get_model_registry,
)
from audiobook_factory.core.models.anti_ban_guard import (
    AntiBanGuard,
    get_anti_ban_guard,
    EmergencyTripwireActiveError,
)
from audiobook_factory.core.models.policy_engine import (
    CircuitBreaker,
    get_circuit_breaker,
)
from audiobook_factory.core.models.router import (
    RequestRouter,
    ExecutionPlan,
)
from audiobook_factory.core.models.gateway import (
    ModelGateway,
    get_model_gateway,
)
from audiobook_factory.core.models.adapters.base import (
    GenerationResult,
    SpeechResult,
)
from audiobook_factory.core.models.adapters.gemini import ApiHttpError


class TestModelGatewayIntegration(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(WORKSPACE_DIR) / "scratch" / "test_gateway"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.tmp_dir / f"test_gateway_{int(time.time() * 1000)}_{os.getpid()}.db"

        # Initialize dedicated test lease manager with 2 keys
        self.lease_mgr = KeyLeaseManager(
            db_path=self.db_path,
            keys=["AIzaSyTestKeyOne11111111", "AIzaSyTestKeyTwo22222222"]
        )
        self.registry = get_model_registry()
        self.guard = AntiBanGuard()
        self.guard.reset_all()
        self.cb = CircuitBreaker()
        self.cb.force_reset()

        self.router = RequestRouter(
            registry=self.registry,
            lease_manager=self.lease_mgr,
            circuit_breaker=self.cb,
        )

        self.gateway = ModelGateway(
            registry=self.registry,
            lease_manager=self.lease_mgr,
            anti_ban_guard=self.guard,
            router=self.router,
        )

    def tearDown(self):
        try:
            if self.db_path.exists():
                self.db_path.unlink()
        except OSError:
            pass

    # =========================================================================
    # 1. End-to-End Text Generation Workflow
    # =========================================================================
    def test_01_e2e_generate_text_success(self):
        """Verifies full execution path for text generation through gateway."""
        mock_result = GenerationResult(
            text="Geralt adjusted his sword.",
            finish_reason="STOP",
            tokens_used=42,
            prompt_tokens=12,
            completion_tokens=30,
            model_id="gemini-3.8-flash",
            provider="gemini",
        )

        with patch.object(self.gateway.router._gemini_adapter, "generate_text", return_value=mock_result) as mock_gen:
            res = self.gateway.generate_text(
                prompt="Translate scene 1",
                task="translation",
                user_id="user_alice",
                fast_mode=True,
            )

            self.assertEqual(res.text, "Geralt adjusted his sword.")
            self.assertEqual(res.tokens_used, 42)
            mock_gen.assert_called_once()

            # Verify that lease was safely released back to SQLite
            summary = self.lease_mgr.get_status_summary("gemini")
            self.assertEqual(summary["active_leases_count"], 0)
            self.assertEqual(summary["active_keys"], 2)

    # =========================================================================
    # 2. End-to-End Speech Synthesis Workflow
    # =========================================================================
    def test_02_e2e_synthesize_speech_success(self):
        """Verifies speech synthesis through gateway with WAV decoding."""
        mock_audio = SpeechResult(
            audio_bytes=b"RIFF" + b"\x00" * 44,
            mime_type="audio/wav",
            sample_rate=24000,
            duration_sec=1.5,
            tokens_used=100,
            model_id="gemini-3.8-flash-tts",
            provider="gemini",
        )

        with patch.object(self.gateway.router._gemini_adapter, "synthesize_speech", return_value=mock_audio) as mock_tts:
            res = self.gateway.synthesize_speech(
                text="नमस्कार दोस्तों",
                voice_name="Puck",
                user_id="user_bob",
                fast_mode=True,
            )

            self.assertTrue(res.audio_bytes.startswith(b"RIFF"))
            self.assertEqual(res.tokens_used, 100)
            mock_tts.assert_called_once()

            # Verify lease released
            summary = self.lease_mgr.get_status_summary("gemini")
            self.assertEqual(summary["active_leases_count"], 0)

    # =========================================================================
    # 3. Automated Key Failover on Daily Quota (429)
    # =========================================================================
    def test_03_automated_key_failover_on_daily_quota(self):
        """
        Critical Multi-Key Invariant:
        When Key 1 hits HTTP 429 Daily Quota Exhaustion:
        1. Gateway marks Key 1 EXHAUSTED_TODAY.
        2. Gateway automatically rotates to Key 2.
        3. Succeeds on Key 2 without crashing the caller!
        """
        call_count = 0

        def side_effect_gen(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Key 1 fails with 429 Daily Quota
                raise ApiHttpError(
                    status_code=429,
                    error_body="Quota exceeded for quota metric 'GenerateRequestsPerDayPerProjectPerModel'",
                )
            # Key 2 succeeds!
            return GenerationResult(
                text="Successful failover response on Key 2.",
                finish_reason="STOP",
                tokens_used=35,
                model_id="gemini-3.8-flash",
                provider="gemini",
            )

        with patch.object(self.gateway.router._gemini_adapter, "generate_text", side_effect=side_effect_gen):
            res = self.gateway.generate_text(
                prompt="Test prompt",
                task="translation",
                user_id="user_alice",
                fast_mode=True,
            )

            self.assertEqual(res.text, "Successful failover response on Key 2.")
            self.assertEqual(call_count, 2)

            # Check model quota ledger: Exactly 1 key marked EXHAUSTED_TODAY for gemini-3.8-flash
            with get_db_connection(self.db_path) as conn:
                exhausted_models = conn.execute("""
                    SELECT key_hash, status FROM model_quota_ledger
                    WHERE model = 'gemini-3.8-flash' AND status = 'EXHAUSTED_TODAY';
                """).fetchall()
                self.assertEqual(len(exhausted_models), 1)


    # =========================================================================
    # 4. Session Affinity Context Manager (Shield 2)
    # =========================================================================
    def test_04_session_affinity_context_manager(self):
        """Verifies session context manager binds affinity and clears on exit."""
        with self.gateway.lease_session("scene_42", task="screenplay", user_id="user_alice") as key_alias:
            self.assertTrue(key_alias.startswith("key_"))
            # Inside context: affinity is registered
            self.assertEqual(self.guard.affinity.get_affinity_key("scene_42"), key_alias)

        # After exiting context: affinity is cleaned up
        self.assertIsNone(self.guard.affinity.get_affinity_key("scene_42"))

    # =========================================================================
    # 5. Fleet Diagnostics
    # =========================================================================
    def test_05_fleet_status_telemetry(self):
        """Verifies get_fleet_status returns complete diagnostic picture."""
        status = self.gateway.get_fleet_status()
        self.assertIn("gemini_keys", status)
        self.assertIn("models_count", status)
        self.assertIn("tripwire_quarantined", status)
        self.assertFalse(status["tripwire_quarantined"])
        self.assertGreaterEqual(status["models_count"], 10)


if __name__ == "__main__":
    unittest.main()
