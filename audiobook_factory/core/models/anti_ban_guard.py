#!/usr/bin/env python3
"""
Audiobook Factory - Pillar 3.4: The 7 Iron Shields Anti-Ban Guard.
==================================================================
Protects 100+ free Google AI Studio / Gemini API keys from edge mass-bans:
1. Shield 1: Strict Request-Level Mutual Exclusion (enforced via KeyLeaseManager).
2. Shield 2: Session Affinity (holds single key for 8-15 sequential segments in a scene).
3. Shield 3: Anti-Correlation Key-Switch Cooldown (18.0s - 32.0s random delay when switching keys).
4. Shield 4: Content-Aware Human Cadence & Director Breaks (reading speed, audio review, log-normal jitter).
5. Shield 5: Conservative 75% Rate Limiting (11.0 RPM clamped per key, min 3.5s interval).
6. Shield 6: Official Stealth SDK Headers (emulates google-genai-sdk-python/0.8.3).
7. Shield 7: Emergency Global Tripwire (5 consecutive 429/503 halts pool for 45.0s).
"""

from __future__ import annotations
import os
import sys
import time
import random
import threading
from typing import Dict, Any, Optional, Tuple, List
from collections import deque

from audiobook_factory.logger import logger
from audiobook_factory.core.models.policy_engine import (
    classify_universal_api_error,
    NormalizedApiError,
    get_circuit_breaker,
)


class EmergencyTripwireActiveError(Exception):
    """Raised when the Emergency Global Tripwire is active due to edge-wide 429/503s."""
    pass


# =============================================================================
# Shield 6: Official Stealth SDK Headers
# =============================================================================

def get_stealth_sdk_headers(api_key: str, provider: str = "gemini") -> Dict[str, str]:
    """
    Constructs stealth HTTP headers identical to official provider SDKs.
    Eliminates custom user agents or bot signatures that Google edge heuristics flag.
    """
    provider_clean = provider.lower().strip()
    if provider_clean == "gemini":
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        platform_tag = "windows/10.0.26100" if sys.platform == "win32" else "linux/x86_64"
        return {
            "Content-Type": "application/json",
            "X-goog-api-key": api_key,
            "User-Agent": f"google-genai-sdk-python/0.8.3 gl-python/{py_ver} ({platform_tag})",
            "x-goog-api-client": f"gl-python/{py_ver} gax/2.24.0 gccl/0.8.3",
        }
    elif provider_clean in ("openai", "cerebras", "groq", "openrouter"):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "openai-python/1.30.1",
        }
    elif provider_clean == "anthropic":
        return {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "User-Agent": "anthropic-python/0.25.0",
        }
    else:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }


# =============================================================================
# Shield 4: Content-Aware Human Cadence & Director Breaks
# =============================================================================

class HumanCadenceController:
    """
    Shapes inter-request latency to simulate a human sound designer / director.
    T_wait = T_read(words) + T_review(prev_audio) + T_jitter + T_director_break
    """

    def __init__(
        self,
        words_per_second: float = 4.0,       # 240 WPM reading speed
        director_break_interval: int = 14,    # Break every 12-16 segments
        director_break_min: float = 15.0,
        director_break_max: float = 30.0,
    ):
        self.words_per_second = words_per_second
        self.director_break_interval = director_break_interval
        self.director_break_min = director_break_min
        self.director_break_max = director_break_max
        self._segment_counter = 0
        self._lock = threading.Lock()

    def calculate_delay(
        self,
        word_count: int = 0,
        prev_audio_duration_sec: float = 0.0,
        force_director_break: bool = False,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculates human wait time in seconds without sleeping.
        Returns: (total_delay, breakdown_dict)
        """
        # 1. Reading time: 2.5s to 12.0s
        if word_count > 0:
            raw_read = word_count / self.words_per_second
            t_read = min(12.0, max(2.5, raw_read))
        else:
            t_read = 2.5

        # 2. Audio review time: 15% - 35% of previous take, capped at 15.0s
        if prev_audio_duration_sec > 0:
            review_fraction = random.uniform(0.15, 0.35)
            t_review = min(15.0, prev_audio_duration_sec * review_fraction)
        else:
            t_review = 0.0

        # 3. Log-Normal Think Time: fat-tailed human pause distribution (clamped 1.5s - 7.0s)
        raw_jitter = random.lognormvariate(1.2, 0.35)
        t_jitter = min(7.0, max(1.5, raw_jitter))

        # 4. Director Script Review Break
        t_director = 0.0
        with self._lock:
            self._segment_counter += 1
            if force_director_break or (self._segment_counter % self.director_break_interval == 0):
                t_director = random.uniform(self.director_break_min, self.director_break_max)

        total_delay = t_read + t_review + t_jitter + t_director
        breakdown = {
            "t_read": t_read,
            "t_review": t_review,
            "t_jitter": t_jitter,
            "t_director": t_director,
            "total": total_delay,
        }
        return total_delay, breakdown

    def apply_cadence(
        self,
        word_count: int = 0,
        prev_audio_duration_sec: float = 0.0,
        fast_mode: bool = False,
    ) -> float:
        """Applies human cadence pause. If fast_mode=True, returns delay without full sleep."""
        delay, breakdown = self.calculate_delay(word_count, prev_audio_duration_sec)
        if fast_mode:
            return delay

        if breakdown["t_director"] > 0:
            logger.info(
                f"  [ANTI-BAN SHIELD 4] Director script review pause: {breakdown['t_director']:.1f}s "
                f"(Segment #{self._segment_counter}). Total cadence wait: {delay:.1f}s"
            )
        else:
            logger.debug(
                f"  [ANTI-BAN SHIELD 4] Human cadence pacing: {delay:.2f}s "
                f"(read={breakdown['t_read']:.1f}s, review={breakdown['t_review']:.1f}s, jitter={breakdown['t_jitter']:.1f}s)"
            )
        time.sleep(delay)
        return delay

    def reset_counter(self) -> None:
        """Resets segment counter."""
        with self._lock:
            self._segment_counter = 0


# =============================================================================
# Shield 5: Conservative 75% Rate Limiting (Token Bucket)
# =============================================================================

class TokenBucketRateLimiter:
    """
    Per-Key Token Bucket Rate Limiter.
    Clamped to 11.0 RPM (73% of Google's 15 RPM limit) with a minimum gap of 3.5 seconds.
    """

    def __init__(
        self,
        max_rpm: float = 11.0,           # Conservative 11 RPM ceiling
        min_gap_sec: float = 3.5,         # Absolute minimum burst separation
    ):
        self.max_rpm = max_rpm
        self.rate_per_sec = max_rpm / 60.0
        self.min_gap_sec = min_gap_sec
        self.capacity = 1.0               # Single token capacity to enforce serialized cadence
        self._tokens: Dict[str, float] = {}
        self._last_request_time: Dict[str, float] = {}
        self._lock = threading.Lock()

    def acquire(self, key_alias: str, fast_mode: bool = False) -> float:
        """
        Enforces 11.0 RPM limit and min 3.5s interval on key_alias.
        Returns the duration waited in seconds.
        """
        now = time.time()
        wait_time = 0.0

        with self._lock:
            last_time = self._last_request_time.get(key_alias, 0.0)
            elapsed = now - last_time

            # 1. Min gap enforcement
            if elapsed < self.min_gap_sec:
                gap_deficit = self.min_gap_sec - elapsed
                wait_time = max(wait_time, gap_deficit)

            # 2. Token bucket replenishment
            tokens = self._tokens.get(key_alias, self.capacity)
            tokens = min(self.capacity, tokens + elapsed * self.rate_per_sec)

            if tokens < 1.0:
                token_deficit = (1.0 - tokens) / self.rate_per_sec
                wait_time = max(wait_time, token_deficit)

            if wait_time > 0 and not fast_mode:
                # Update scheduled time to prevent concurrent thread dogpiling
                self._last_request_time[key_alias] = now + wait_time
                self._tokens[key_alias] = 0.0
            else:
                self._last_request_time[key_alias] = now
                self._tokens[key_alias] = 0.0

        if wait_time > 0 and not fast_mode:
            logger.debug(f"  [ANTI-BAN SHIELD 5] Rate limiter clamping {key_alias}: waiting {wait_time:.2f}s (11.0 RPM ceiling).")
            time.sleep(wait_time)

        return wait_time

    def reset(self) -> None:
        """Resets rate limiter states."""
        with self._lock:
            self._tokens.clear()
            self._last_request_time.clear()


# =============================================================================
# Shield 7: Emergency Global Tripwire
# =============================================================================

class EmergencyTripwire:
    """
    Monitors edge-wide health across all keys.
    If 5 consecutive requests fail with 429 (Resource Exhausted) or 503 (Unavailable)
    within a 60-second sliding window, activates emergency pool quarantine for 45.0s.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        window_seconds: float = 60.0,
        quarantine_seconds: float = 45.0,
    ):
        self.failure_threshold = failure_threshold
        self.window_seconds = window_seconds
        self.quarantine_seconds = quarantine_seconds
        self._lock = threading.Lock()
        self._failure_timestamps: deque[float] = deque()
        self._consecutive_failures = 0
        self._quarantined_until = 0.0

    def is_quarantined(self) -> Tuple[bool, float]:
        """Returns (is_active, remaining_seconds)."""
        now = time.time()
        with self._lock:
            if now < self._quarantined_until:
                return True, (self._quarantined_until - now)
            return False, 0.0

    def record_success(self, key_alias: str = "") -> None:
        """Records a successful request, resetting consecutive failure streak."""
        with self._lock:
            self._consecutive_failures = 0

    def record_failure(self, key_alias: str, status_code: int, error_category: str = "") -> bool:
        """
        Records an API error. If failure count reaches threshold, trips quarantine.
        Returns True if tripwire tripped.
        """
        # Only trip on rate-limits, quotas, and server errors
        if status_code not in (429, 500, 502, 503, 504) and error_category not in (
            "RPM_RATE_LIMIT", "TPM_RATE_LIMIT", "DAILY_QUOTA_EXHAUSTED", "TRANSIENT_SERVER_ERROR"
        ):
            return False

        now = time.time()
        with self._lock:
            # Purge timestamps outside window
            while self._failure_timestamps and (now - self._failure_timestamps[0] > self.window_seconds):
                self._failure_timestamps.popleft()

            self._failure_timestamps.append(now)
            self._consecutive_failures += 1

            if len(self._failure_timestamps) >= self.failure_threshold and self._consecutive_failures >= self.failure_threshold:
                self._quarantined_until = now + self.quarantine_seconds
                logger.critical(
                    f"  [EMERGENCY GLOBAL TRIPWIRE TRIPPED] {self._consecutive_failures} consecutive API failures detected! "
                    f"Entering {self.quarantine_seconds:.0f}s emergency quarantine to prevent pool burnout. Key: {key_alias}"
                )
                return True
            return False

    def reset(self) -> None:
        """Resets tripwire status."""
        with self._lock:
            self._failure_timestamps.clear()
            self._consecutive_failures = 0
            self._quarantined_until = 0.0


# =============================================================================
# Shield 2: Session Affinity Tracker
# =============================================================================

class SessionAffinityTracker:
    """
    Maintains sticky binding between an active production session/scene and a leased key.
    Ensures a worker holds the same key for 8-15 sequential segments, preventing rapid
    key-hopping heuristics at Google's edge.
    """

    def __init__(self, max_segments_per_affinity: int = 15):
        self.max_segments_per_affinity = max_segments_per_affinity
        self._lock = threading.Lock()
        # session_id -> {"key_alias": str, "segment_count": int, "created_at": float}
        self._affinities: Dict[str, Dict[str, Any]] = {}

    def get_affinity_key(self, session_id: str) -> Optional[str]:
        """Returns the assigned key_alias if valid and under max segment cap."""
        with self._lock:
            data = self._affinities.get(session_id)
            if not data:
                return None
            if data["segment_count"] >= self.max_segments_per_affinity:
                # Segment quota reached: gracefully release affinity to allow rotation
                del self._affinities[session_id]
                return None
            return data["key_alias"]

    def bind_affinity(self, session_id: str, key_alias: str) -> None:
        """Binds a session to a key_alias."""
        with self._lock:
            self._affinities[session_id] = {
                "key_alias": key_alias,
                "segment_count": 0,
                "created_at": time.time(),
            }

    def record_segment_done(self, session_id: str) -> int:
        """Increments segment count for session. Returns remaining segments on this affinity."""
        with self._lock:
            data = self._affinities.get(session_id)
            if not data:
                return 0
            data["segment_count"] += 1
            rem = max(0, self.max_segments_per_affinity - data["segment_count"])
            if rem == 0:
                del self._affinities[session_id]
            return rem

    def clear_affinity(self, session_id: str) -> None:
        """Clears affinity for a finished scene or session."""
        with self._lock:
            self._affinities.pop(session_id, None)


# =============================================================================
# Unified AntiBanGuard Facade
# =============================================================================

class AntiBanGuard:
    """
    The Central Control Plane for Anti-Ban Protection.
    Orchestrates:
    - Shield 2: Session Affinity
    - Shield 3: Anti-Correlation Key-Switch Cooldown (18.0s - 32.0s)
    - Shield 4: Content-Aware Human Cadence & Director Breaks
    - Shield 5: Conservative 75% Rate Limiting (11.0 RPM)
    - Shield 6: Stealth SDK Headers
    - Shield 7: Emergency Global Tripwire
    """

    def __init__(
        self,
        key_switch_min_cooldown: float = 18.0,
        key_switch_max_cooldown: float = 32.0,
        max_rpm: float = 11.0,
    ):
        self.key_switch_min_cooldown = key_switch_min_cooldown
        self.key_switch_max_cooldown = key_switch_max_cooldown
        self.cadence = HumanCadenceController()
        self.rate_limiter = TokenBucketRateLimiter(max_rpm=max_rpm)
        self.tripwire = EmergencyTripwire()
        self.affinity = SessionAffinityTracker()
        self._last_used_key_alias: Optional[str] = None
        self._last_used_by_context: Dict[str, str] = {}
        self._lock = threading.Lock()

    def enforce_key_switch_cooldown(
        self,
        prev_key_alias: Optional[str],
        new_key_alias: str,
        fast_mode: bool = False,
    ) -> float:
        """
        Shield 3: Mandatory 18.0s - 32.0s pause when switching keys on the same IP.
        Breaks TCP/TLS correlation heuristics across different Google accounts.
        """
        if not prev_key_alias or prev_key_alias == new_key_alias:
            return 0.0

        delay = random.uniform(self.key_switch_min_cooldown, self.key_switch_max_cooldown)
        if fast_mode:
            return delay

        logger.info(
            f"  [ANTI-BAN SHIELD 3] Anti-correlation pause {delay:.2f}s: switching from {prev_key_alias} to {new_key_alias}."
        )
        time.sleep(delay)
        return delay

    def pre_request_gate(
        self,
        key_alias: str,
        prev_key_alias: Optional[str] = None,
        word_count: int = 0,
        prev_audio_duration_sec: float = 0.0,
        session_id: Optional[str] = None,
        fast_mode: bool = False,
    ) -> Dict[str, float]:
        """
        Executes pre-request validation, pacing, and rate limiting:
        1. Checks Emergency Global Tripwire (Shield 7).
        2. Enforces Anti-Correlation Key-Switch Cooldown if key changed (Shield 3).
        3. Enforces Token Bucket 11.0 RPM clamping (Shield 5).
        4. Applies Content-Aware Human Cadence (Shield 4).
        Returns dictionary of applied delays.
        """
        # 1. Shield 7: Check Emergency Tripwire
        is_quarantined, rem_sec = self.tripwire.is_quarantined()
        if is_quarantined:
            raise EmergencyTripwireActiveError(
                f"Emergency Global Tripwire is ACTIVE! Pool quarantined for {rem_sec:.1f}s more. "
                "Halting dispatch to prevent mass account bans."
            )

        # Determine context identifier to avoid cross-worker key-switch collision
        context_id = session_id or "default_context"

        with self._lock:
            effective_prev_key = prev_key_alias or self._last_used_by_context.get(context_id)
            self._last_used_by_context[context_id] = key_alias
            self._last_used_key_alias = key_alias

        # 2. Shield 3: Anti-Correlation Key-Switch Delay
        switch_delay = self.enforce_key_switch_cooldown(effective_prev_key, key_alias, fast_mode=fast_mode)

        # 3. Shield 5: Rate Limiter Token Bucket Clamping
        rate_delay = self.rate_limiter.acquire(key_alias, fast_mode=fast_mode)

        # 4. Shield 4: Human Cadence Shaping
        cadence_delay = self.cadence.apply_cadence(
            word_count=word_count,
            prev_audio_duration_sec=prev_audio_duration_sec,
            fast_mode=fast_mode,
        )

        return {
            "key_switch_delay": switch_delay,
            "rate_limiter_delay": rate_delay,
            "cadence_delay": cadence_delay,
            "total_wait": switch_delay + rate_delay + cadence_delay,
        }

    def post_request_audit(
        self,
        key_alias: str,
        status_code: int,
        error_body: str = "",
        headers: Optional[Dict[str, str]] = None,
        provider: str = "gemini",
        model: str = "",
        session_id: Optional[str] = None,
    ) -> NormalizedApiError:
        """
        Audits response after execution:
        - Classifies error if status != 200/204.
        - Updates Tripwire status (Shield 7).
        - Updates Circuit Breaker.
        - Increments session affinity counter on success (Shield 2).
        """
        cb = get_circuit_breaker()

        if 200 <= status_code < 300:
            self.tripwire.record_success(key_alias)
            if model:
                cb.record_success(provider, model)
            if session_id:
                self.affinity.record_segment_done(session_id)
            return NormalizedApiError(
                category="SUCCESS",
                wait_sec=0.0,
                message="Request succeeded.",
                is_retryable=False,
                suggested_action="NONE",
            )

        # Classify API error
        norm_error = classify_universal_api_error(
            status_code=status_code,
            error_body=error_body,
            headers=headers,
            provider=provider,
            model=model,
        )

        # Update Tripwire
        self.tripwire.record_failure(
            key_alias=key_alias,
            status_code=status_code,
            error_category=norm_error.category,
        )

        # Update Circuit Breaker on server-side failure
        if status_code in (500, 502, 503, 504) and model:
            cb.record_failure(provider, model, error_msg=norm_error.message)

        return norm_error

    def get_headers(self, api_key: str, provider: str = "gemini") -> Dict[str, str]:
        """Shield 6: Injects official stealth SDK headers."""
        return get_stealth_sdk_headers(api_key, provider=provider)

    def reset_all(self) -> None:
        """Resets all internal states, tripwires, and limiters."""
        with self._lock:
            self._last_used_key_alias = None
        self.cadence.reset_counter()
        self.rate_limiter.reset()
        self.tripwire.reset()


# Module-level singleton
_ANTI_BAN_GUARD_INSTANCE: Optional[AntiBanGuard] = None
_GUARD_LOCK = threading.Lock()


def get_anti_ban_guard() -> AntiBanGuard:
    """Returns process-wide AntiBanGuard singleton."""
    global _ANTI_BAN_GUARD_INSTANCE
    if _ANTI_BAN_GUARD_INSTANCE is None:
        with _GUARD_LOCK:
            if _ANTI_BAN_GUARD_INSTANCE is None:
                _ANTI_BAN_GUARD_INSTANCE = AntiBanGuard()
    return _ANTI_BAN_GUARD_INSTANCE
