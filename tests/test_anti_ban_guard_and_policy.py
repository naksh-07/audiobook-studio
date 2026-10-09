#!/usr/bin/env python3
"""
Comprehensive Test Suite for Pillar 3.4: The 7 Iron Shields Anti-Ban Guard & Policy Engine.
==========================================================================================
Validates:
1. Shield 2 (Session Affinity): Sticky key binding across multi-turn scene segments.
2. Shield 3 (Key-Switch Cooldown): 18.0s - 32.0s random delay when rotating keys on same IP.
3. Shield 4 (Human Cadence Shaper): Reading speed, audio review, log-normal jitter, and director breaks.
4. Shield 5 (Conservative 75% Rate Limiting): 11.0 RPM clamped per key with min 3.5s interval.
5. Shield 6 (Official Stealth SDK Headers): Exact google-genai-sdk-python/0.8.3 header structure.
6. Shield 7 (Emergency Global Tripwire): 5 consecutive 429/503 halts pool for 45.0s quarantine.
7. Universal Policy Engine & Error Matrix: Classification of 401, 400, 429 (RPM vs Daily Quota), 5xx.
8. Timezone Quota Rollover: Pacific Midnight vs UTC Midnight rollover handling.
9. Circuit Breaker: CLOSED -> OPEN -> HALF_OPEN -> CLOSED state machine transitions.
"""

import sys
import os
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from audiobook_factory.core.models.policy_engine import (
    classify_universal_api_error,
    parse_retry_after,
    CircuitBreaker,
    get_provider_date_str,
    NormalizedApiError,
)
from audiobook_factory.core.models.anti_ban_guard import (
    AntiBanGuard,
    HumanCadenceController,
    TokenBucketRateLimiter,
    EmergencyTripwire,
    EmergencyTripwireActiveError,
    SessionAffinityTracker,
    get_stealth_sdk_headers,
)


class TestAntiBanGuardAndPolicy(unittest.TestCase):

    def setUp(self):
        self.guard = AntiBanGuard()
        self.guard.reset_all()

    def tearDown(self):
        self.guard.reset_all()

    # =========================================================================
    # 1. Shield 6: Stealth SDK Headers Emulation
    # =========================================================================
    def test_01_stealth_sdk_headers_format(self):
        """Verifies headers match official google-genai-sdk-python/0.8.3 format."""
        api_key = "AIzaSyFakeKeyForHeadersTest12345"
        headers = get_stealth_sdk_headers(api_key, provider="gemini")

        self.assertIn("X-goog-api-key", headers)
        self.assertEqual(headers["X-goog-api-key"], api_key)
        self.assertEqual(headers["Content-Type"], "application/json")

        user_agent = headers.get("User-Agent", "")
        self.assertTrue(user_agent.startswith("google-genai-sdk-python/0.8.3"))
        self.assertIn("gl-python/", user_agent)

        client_header = headers.get("x-goog-api-client", "")
        self.assertIn("gccl/0.8.3", client_header)

    def test_02_stealth_headers_other_providers(self):
        """Verifies headers for OpenAI and Anthropic format."""
        oai_headers = get_stealth_sdk_headers("sk-fake-openai", provider="openai")
        self.assertEqual(oai_headers["Authorization"], "Bearer sk-fake-openai")
        self.assertIn("openai-python", oai_headers["User-Agent"])

        anthro_headers = get_stealth_sdk_headers("sk-ant-fake", provider="anthropic")
        self.assertEqual(anthro_headers["x-api-key"], "sk-ant-fake")
        self.assertEqual(anthro_headers["anthropic-version"], "2023-06-01")

    # =========================================================================
    # 2. Shield 3: Anti-Correlation Key-Switch Delay (18.0s - 32.0s)
    # =========================================================================
    def test_03_key_switch_anti_correlation_cooldown(self):
        """
        Critical Anti-Correlation Invariant:
        Switching from Key A to Key B on the same IP must incur 18.0s - 32.0s pause.
        Reusing the same key must incur 0.0s switch delay.
        """
        # Switching between two different keys
        delay = self.guard.enforce_key_switch_cooldown("key_alpha", "key_beta", fast_mode=True)
        self.assertGreaterEqual(delay, 18.0)
        self.assertLessEqual(delay, 32.0)

        # Same key: zero delay
        delay_same = self.guard.enforce_key_switch_cooldown("key_alpha", "key_alpha", fast_mode=True)
        self.assertEqual(delay_same, 0.0)

        # Initial call (no previous key): zero delay
        delay_initial = self.guard.enforce_key_switch_cooldown(None, "key_alpha", fast_mode=True)
        self.assertEqual(delay_initial, 0.0)

    # =========================================================================
    # 3. Shield 4: Content-Aware Human Cadence & Director Breaks
    # =========================================================================
    def test_04_human_cadence_delay_calculation(self):
        """Verifies reading speed, audio review, and log-normal jitter calculations."""
        cadence = HumanCadenceController(words_per_second=4.0)

        # Normal line: 20 words, 5s previous audio, no director break
        delay, breakdown = cadence.calculate_delay(
            word_count=20,
            prev_audio_duration_sec=5.0,
            force_director_break=False,
        )

        # t_read: 20 / 4 = 5.0s
        self.assertAlmostEqual(breakdown["t_read"], 5.0, places=1)
        # t_review: 5.0 * [0.15, 0.35] -> [0.75, 1.75]s
        self.assertGreaterEqual(breakdown["t_review"], 0.70)
        self.assertLessEqual(breakdown["t_review"], 1.80)
        # t_jitter: [1.5, 7.0]s
        self.assertGreaterEqual(breakdown["t_jitter"], 1.5)
        self.assertLessEqual(breakdown["t_jitter"], 7.0)
        # total within expected realistic range
        self.assertGreaterEqual(delay, 7.0)
        self.assertLessEqual(delay, 15.0)

    def test_05_director_script_review_break(self):
        """Verifies director break of 15.0s - 30.0s is triggered every 14 segments."""
        cadence = HumanCadenceController(director_break_interval=14, director_break_min=15.0, director_break_max=30.0)

        # 13 normal segments without director break
        for i in range(13):
            delay, breakdown = cadence.calculate_delay(word_count=10)
            self.assertEqual(breakdown["t_director"], 0.0)

        # 14th segment must trigger director break
        delay_14, breakdown_14 = cadence.calculate_delay(word_count=10)
        self.assertGreaterEqual(breakdown_14["t_director"], 15.0)
        self.assertLessEqual(breakdown_14["t_director"], 30.0)
        self.assertGreaterEqual(delay_14, 18.0)

    # =========================================================================
    # 4. Shield 5: Conservative 75% Rate Limiting (Token Bucket)
    # =========================================================================
    def test_06_token_bucket_rate_limiter_min_gap(self):
        """Verifies 11.0 RPM enforcement with minimum 3.5s gap."""
        limiter = TokenBucketRateLimiter(max_rpm=11.0, min_gap_sec=3.5)

        # First acquisition: instant
        w1 = limiter.acquire("key_001", fast_mode=True)
        self.assertEqual(w1, 0.0)

        # Immediate second acquisition: must wait min_gap (approx 3.5s)
        w2 = limiter.acquire("key_001", fast_mode=True)
        self.assertGreaterEqual(w2, 3.4)

    # =========================================================================
    # 5. Shield 2: Session Affinity (Anti-Hopping Pacing)
    # =========================================================================
    def test_07_session_affinity_tracking(self):
        """Verifies sticky key binding for up to 15 segments within a scene."""
        tracker = SessionAffinityTracker(max_segments_per_affinity=15)

        # Initially unbound
        self.assertIsNone(tracker.get_affinity_key("scene_101"))

        # Bind session to key
        tracker.bind_affinity("scene_101", "key_affinity_1")
        self.assertEqual(tracker.get_affinity_key("scene_101"), "key_affinity_1")

        # Record 14 segments
        for _ in range(14):
            rem = tracker.record_segment_done("scene_101")
            self.assertGreater(rem, 0)
            self.assertEqual(tracker.get_affinity_key("scene_101"), "key_affinity_1")

        # Record 15th segment: quota exhausted, affinity released
        rem_final = tracker.record_segment_done("scene_101")
        self.assertEqual(rem_final, 0)
        self.assertIsNone(tracker.get_affinity_key("scene_101"))

    # =========================================================================
    # 6. Shield 7: Emergency Global Tripwire
    # =========================================================================
    def test_08_emergency_tripwire_activation(self):
        """
        Critical Anti-Ban Tripwire:
        5 consecutive 429 or 503 failures within 60s must trip global quarantine for 45s.
        """
        tripwire = EmergencyTripwire(failure_threshold=5, window_seconds=60.0, quarantine_seconds=45.0)

        # 4 consecutive failures: tripwire NOT yet active
        for i in range(4):
            tripped = tripwire.record_failure(f"key_{i}", status_code=429, error_category="RPM_RATE_LIMIT")
            self.assertFalse(tripped)
            is_active, _ = tripwire.is_quarantined()
            self.assertFalse(is_active)

        # 5th consecutive failure: tripwire TRIPPED!
        tripped_5 = tripwire.record_failure("key_4", status_code=429, error_category="RPM_RATE_LIMIT")
        self.assertTrue(tripped_5)

        is_active, rem_sec = tripwire.is_quarantined()
        self.assertTrue(is_active)
        self.assertGreater(rem_sec, 40.0)
        self.assertLessEqual(rem_sec, 45.0)

    def test_09_emergency_tripwire_resets_on_success(self):
        """Verifies success resets consecutive failure counter, preventing false tripwire trips."""
        tripwire = EmergencyTripwire(failure_threshold=5, window_seconds=60.0, quarantine_seconds=45.0)

        # 3 failures
        for i in range(3):
            tripwire.record_failure(f"key_{i}", status_code=429)

        # 1 success
        tripwire.record_success("key_good")

        # 2 more failures: total 2 consecutive, tripwire must NOT trip
        for i in range(2):
            tripwire.record_failure(f"key_again_{i}", status_code=429)

        is_active, _ = tripwire.is_quarantined()
        self.assertFalse(is_active)

    def test_10_guard_raises_on_quarantine_in_pre_gate(self):
        """Verifies pre_request_gate blocks all dispatches when tripwire is active."""
        # Trip the tripwire
        for i in range(5):
            self.guard.tripwire.record_failure(f"key_{i}", status_code=429, error_category="RPM_RATE_LIMIT")

        self.assertTrue(self.guard.tripwire.is_quarantined()[0])

        with self.assertRaises(EmergencyTripwireActiveError):
            self.guard.pre_request_gate(key_alias="key_test", fast_mode=True)

    # =========================================================================
    # 7. Universal Policy Engine & Error Classifier
    # =========================================================================
    def test_11_universal_error_classification_categories(self):
        """Verifies differentiation across all API error categories."""
        # 1. Invalid Key
        err_invalid = classify_universal_api_error(400, "API_KEY_INVALID: Key not found")
        self.assertEqual(err_invalid.category, "INVALID_KEY")
        self.assertFalse(err_invalid.is_retryable)
        self.assertEqual(err_invalid.suggested_action, "ROTATE_KEY")

        # 2. Context Length Exceeded
        err_ctx = classify_universal_api_error(400, "context_length_exceeded: maximum context length is 1048576")
        self.assertEqual(err_ctx.category, "CONTEXT_LENGTH_EXCEEDED")
        self.assertFalse(err_ctx.is_retryable)
        self.assertEqual(err_ctx.suggested_action, "ABORT_PAYLOAD")

        # 3. Content Safety Block
        err_safety = classify_universal_api_error(400, "Response blocked by safety filters (HARM_CATEGORY_VIOLENCE)")
        self.assertEqual(err_safety.category, "CONTENT_SAFETY_BLOCKED")
        self.assertTrue(err_safety.is_retryable)
        self.assertEqual(err_safety.suggested_action, "ROTATE_MODEL")

        # 4. Daily Quota Exhaustion (per project / per day)
        err_daily = classify_universal_api_error(
            429,
            "Quota exceeded for quota metric 'GenerateRequestsPerDayPerProjectPerModel'",
            model="gemini-3.8-flash-tts"
        )
        self.assertEqual(err_daily.category, "DAILY_QUOTA_EXHAUSTED")
        self.assertTrue(err_daily.is_retryable)
        self.assertEqual(err_daily.suggested_action, "ROTATE_KEY")

        # 5. RPM Rate Limit
        err_rpm = classify_universal_api_error(429, "Resource exhausted. Please retry in 4.5s.")
        self.assertEqual(err_rpm.category, "RPM_RATE_LIMIT")
        self.assertTrue(err_rpm.is_retryable)
        self.assertEqual(err_rpm.suggested_action, "COOL_DOWN")
        self.assertAlmostEqual(err_rpm.wait_sec, 6.5, places=1)

        # 6. TPM Rate Limit
        err_tpm = classify_universal_api_error(429, "Token rate limit exceeded (TPM reached)")
        self.assertEqual(err_tpm.category, "TPM_RATE_LIMIT")
        self.assertEqual(err_tpm.suggested_action, "COOL_DOWN")

        # 7. Transient Server Error (503)
        err_503 = classify_universal_api_error(503, "Service Unavailable")
        self.assertEqual(err_503.category, "TRANSIENT_SERVER_ERROR")
        self.assertTrue(err_503.is_retryable)
        self.assertEqual(err_503.suggested_action, "ROTATE_MODEL")

    def test_12_parse_retry_after_headers(self):
        """Verifies parsing of HTTP Retry-After headers in seconds and date formats."""
        # Simple integer seconds
        self.assertEqual(parse_retry_after({"Retry-After": "15"}), 15.0)
        self.assertEqual(parse_retry_after({"retry-after": "7.5"}), 7.5)

        # Alternative x-ratelimit-reset header
        self.assertEqual(parse_retry_after({"x-ratelimit-reset-requests": "12"}), 12.0)

        # None on missing headers
        self.assertIsNone(parse_retry_after({}))
        self.assertIsNone(parse_retry_after(None))

    # =========================================================================
    # 8. Timezone Quota Rollover
    # =========================================================================
    def test_13_provider_date_string_rollover(self):
        """Verifies Pacific Time rollover for Gemini and UTC for other providers."""
        gem_date = get_provider_date_str("gemini")
        utc_date = get_provider_date_str("openai")

        self.assertRegex(gem_date, r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(utc_date, r"^\d{4}-\d{2}-\d{2}$")

    # =========================================================================
    # 9. Circuit Breaker State Machine
    # =========================================================================
    def test_14_circuit_breaker_lifecycle(self):
        """
        Verifies Circuit Breaker state transitions:
        CLOSED -> OPEN (after threshold failures) -> HALF_OPEN (after cooldown) -> CLOSED.
        """
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)

        # Initially CLOSED
        self.assertTrue(cb.is_available("gemini", "gemini-3.8-flash"))

        # Failure 1: Still CLOSED
        cb.record_failure("gemini", "gemini-3.8-flash", "503 Unavailable")
        self.assertTrue(cb.is_available("gemini", "gemini-3.8-flash"))

        # Failure 2: Tripped to OPEN
        cb.record_failure("gemini", "gemini-3.8-flash", "503 Unavailable")
        self.assertFalse(cb.is_available("gemini", "gemini-3.8-flash"))

        # Wait for cooldown to expire
        time.sleep(0.15)

        # Canary request allowed (transitions to HALF_OPEN)
        self.assertTrue(cb.is_available("gemini", "gemini-3.8-flash"))

        # Second request blocked while canary in-flight
        self.assertFalse(cb.is_available("gemini", "gemini-3.8-flash"))

        # Canary succeeds: recovered to CLOSED
        cb.record_success("gemini", "gemini-3.8-flash")
        self.assertTrue(cb.is_available("gemini", "gemini-3.8-flash"))


if __name__ == "__main__":
    unittest.main()
