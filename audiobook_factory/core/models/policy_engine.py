#!/usr/bin/env python3
"""
Audiobook Factory - Pillar 3.4: Universal Policy Engine & Error Resilience Matrix.
Provides:
1. Universal error classification differentiating daily quota, RPM bursts, TPM ceilings,
   concurrency limits, server hiccups (5xx), context overflow, safety blocks, and invalid keys.
2. HTTP Retry-After and rate-limit header parsing.
3. Resilient per-(provider, model) Circuit Breaker with CLOSED -> OPEN -> HALF_OPEN state transitions.
4. Timezone-aware daily quota rollover calculator (Pacific Midnight PT for Google, UTC for others).
"""

from __future__ import annotations
import re
import time
import email.utils
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, NamedTuple
import threading
from zoneinfo import ZoneInfo

from audiobook_factory.logger import logger


def get_provider_date_str(provider: str = "gemini") -> str:
    """
    Returns the effective quota date string (YYYY-MM-DD) for the given provider.
    - Google AI Studio resets daily quotas at Midnight US Pacific Time (PT).
      Uses IANA 'America/Los_Angeles' for automatic PDT/PST DST transitions,
      with a graceful fallback for environments lacking tzdata (e.g. Windows).
    - Other providers (OpenAI, Anthropic, Cerebras, Groq) reset at UTC Midnight.
    """
    if provider == "gemini":
        try:
            pacific_tz = ZoneInfo("America/Los_Angeles")
            return datetime.now(pacific_tz).strftime("%Y-%m-%d")
        except Exception:
            # Fallback for Windows without tzdata package (approximate Pacific Time: UTC-7 PDT / UTC-8 PST)
            pacific_tz = timezone(timedelta(hours=-7))
            return datetime.now(pacific_tz).strftime("%Y-%m-%d")
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class NormalizedApiError(NamedTuple):
    """Categorized result from universal error classifier."""
    category: str              # DAILY_QUOTA_EXHAUSTED, RPM_RATE_LIMIT, TPM_RATE_LIMIT, CONCURRENCY_LIMIT, etc.
    wait_sec: float            # Recommended backoff in seconds
    message: str               # Diagnostic description
    is_retryable: bool         # Whether retrying could succeed (on same or next key/model)
    suggested_action: str      # "ROTATE_KEY", "ROTATE_MODEL", "COOL_DOWN", "ABORT_PAYLOAD", "HALT_POOL"


def parse_retry_after(headers: Optional[Dict[str, str]]) -> Optional[float]:
    """Extracts wait seconds from standard HTTP Retry-After and rate-limit headers."""
    if not headers:
        return None
    val = headers.get("retry-after") or headers.get("Retry-After")
    if not val:
        # Check alternative provider ratelimit headers
        for k in ("x-ratelimit-reset-requests", "x-ratelimit-reset-tokens", "ratelimit-reset"):
            alt = headers.get(k) or headers.get(k.lower())
            if alt:
                try:
                    return float(alt)
                except ValueError:
                    pass
        return None

    val_str = str(val).strip()
    # Can be integer or float seconds
    try:
        return float(val_str)
    except ValueError:
        pass

    # Can be HTTP Date string (RFC 2822 / RFC 7231)
    try:
        parsed_dt = email.utils.parsedate_to_datetime(val_str)
        now_dt = datetime.now(timezone.utc)
        diff = (parsed_dt - now_dt).total_seconds()
        return max(1.0, diff)
    except Exception:
        return None


def classify_universal_api_error(
    status_code: int,
    error_body: str,
    headers: Optional[Dict[str, str]] = None,
    provider: str = "gemini",
    model: str = "",
) -> NormalizedApiError:
    """
    Universal Error Classifier across Google Gemini, OpenAI, Anthropic, Cerebras, Groq.
    Differentiates:
    - 401/403/400 Invalid Keys -> ROTATE_KEY
    - 400 Context Length Exceeded -> ABORT_PAYLOAD
    - 400 Safety / Content Block -> ROTATE_MODEL
    - 429 Daily Quota (per day / per project) -> ROTATE_KEY
    - 429 RPM Rate Limit / Burst -> COOL_DOWN
    - 429 TPM Rate Limit -> COOL_DOWN
    - 429 Concurrency Limit -> COOL_DOWN
    - 5xx Server Errors -> ROTATE_MODEL
    """
    body_lower = error_body.lower()
    header_wait = parse_retry_after(headers)

    # 1. Temporary Geo / Location restriction (do not burn key on VPN drop)
    if status_code == 403 and any(
        x in body_lower for x in ["user_location_not_supported", "location is not supported", "georestricted", "country"]
    ):
        return NormalizedApiError(
            category="LOCATION_UNSUPPORTED",
            wait_sec=30.0,
            message=f"User location/VPN not supported for {provider}. Check network routing.",
            is_retryable=True,
            suggested_action="COOL_DOWN",
        )

    # 2. Authentication / Key Validity (HTTP 401/403/400)
    is_400_key_error = (
        status_code == 400 and any(
            x in body_lower for x in [
                "api_key_invalid", "api key not valid", "invalid api key",
                "apikey invalid", "api_key_expired", "consumer_suspended"
            ]
        )
    )
    is_403_key_error = (
        status_code == 403 and not any(
            x in body_lower for x in [
                "user_location_not_supported", "location is not supported",
                "quota exceeded", "resource_exhausted"
            ]
        )
    )

    if status_code == 401 or is_400_key_error or is_403_key_error:
        return NormalizedApiError(
            category="INVALID_KEY",
            wait_sec=0.0,
            message=f"API key is invalid, revoked, or lacks permission for {provider}.",
            is_retryable=False,
            suggested_action="ROTATE_KEY"
        )

    # 2. Context Length Exceeded (HTTP 400 / 413)
    if status_code in (400, 413) and any(
        x in body_lower for x in [
            "context_length_exceeded", "maximum context length", "too many tokens",
            "prompt is too long", "token count exceeds", "max_tokens"
        ]
    ):
        return NormalizedApiError(
            category="CONTEXT_LENGTH_EXCEEDED",
            wait_sec=0.0,
            message="Payload exceeds model maximum context window.",
            is_retryable=False,
            suggested_action="ABORT_PAYLOAD"
        )

    # 3. Content Moderation / Safety Block (HTTP 400 or payload flag)
    if any(x in body_lower for x in ["blocked", "prohibited_content", "safety", "harm_category", "moderation"]):
        return NormalizedApiError(
            category="CONTENT_SAFETY_BLOCKED",
            wait_sec=0.5,
            message="Model safety filter blocked the prompt. Requires dramatic framing or model rotation.",
            is_retryable=True,
            suggested_action="ROTATE_MODEL"
        )

    # 4. HTTP 429 Resource Exhausted / Rate Limits
    if status_code == 429:
        # Check genuine Daily Quota Exhaustion (per project / per day)
        # Google: "GenerateRequestsPerDayPerProjectPerModel", "perday", "daily"
        # OpenAI/Cerebras: "insufficient_quota", "daily limit"
        is_daily = any(
            x in body_lower for x in [
                "generaterequestsperday", "perday", "daily", "insufficient_quota",
                "quota_exceeded", "billing_hard_limit_reached"
            ]
        )
        if is_daily:
            return NormalizedApiError(
                category="DAILY_QUOTA_EXHAUSTED",
                wait_sec=0.0,
                message=f"Daily quota reached for model '{model}' on provider '{provider}'.",
                is_retryable=True,
                suggested_action="ROTATE_KEY"
            )

        # Check TPM (Tokens Per Minute) limit
        if any(x in body_lower for x in ["tpm", "tokens per minute", "token limit"]):
            wait = header_wait if header_wait is not None else 20.0
            return NormalizedApiError(
                category="TPM_RATE_LIMIT",
                wait_sec=wait,
                message=f"Tokens-per-minute (TPM) limit reached. Backing off {wait:.1f}s.",
                is_retryable=True,
                suggested_action="COOL_DOWN"
            )

        # Check Concurrency Limit
        if any(x in body_lower for x in ["concurrency", "simultaneous", "concurrent_requests"]):
            wait = header_wait if header_wait is not None else 6.0
            return NormalizedApiError(
                category="CONCURRENCY_LIMIT",
                wait_sec=wait,
                message=f"Concurrent request limit reached. Cooling off {wait:.1f}s.",
                is_retryable=True,
                suggested_action="COOL_DOWN"
            )

        # Standard RPM Rate Limit
        if header_wait is not None:
            wait = header_wait + 1.0
        else:
            delay_match = re.search(r"retry in (\d+\.?\d*)s", error_body, re.IGNORECASE)
            wait = float(delay_match.group(1)) + 2.0 if delay_match else 15.0

        return NormalizedApiError(
            category="RPM_RATE_LIMIT",
            wait_sec=wait,
            message=f"Temporary RPM rate limit hit on '{model}'. Cooling off {wait:.1f}s.",
            is_retryable=True,
            suggested_action="COOL_DOWN"
        )

    # 5. Transient 5xx Server Errors (500, 502, 503, 504)
    if status_code in (500, 502, 503, 504):
        if header_wait is not None:
            wait = header_wait + 1.0
        else:
            delay_match = re.search(r"retry in (\d+\.?\d*)s", error_body, re.IGNORECASE)
            wait = float(delay_match.group(1)) + 2.0 if delay_match else 8.0

        return NormalizedApiError(
            category="TRANSIENT_SERVER_ERROR",
            wait_sec=wait,
            message=f"Transient provider server error HTTP {status_code} ({provider}).",
            is_retryable=True,
            suggested_action="ROTATE_MODEL"
        )

    # 6. HTTP 400 Bad Request
    if status_code == 400:
        return NormalizedApiError(
            category="PAYLOAD_INVALID",
            wait_sec=0.0,
            message=f"HTTP 400 Bad Request: {error_body[:140]}",
            is_retryable=False,
            suggested_action="ABORT_PAYLOAD"
        )

    # 7. Unclassified error
    return NormalizedApiError(
        category="UNKNOWN_ERROR",
        wait_sec=5.0,
        message=f"HTTP {status_code}: {error_body[:120]}",
        is_retryable=True,
        suggested_action="ROTATE_KEY"
    )


class CircuitBreaker:
    """
    Per-(Provider, Model) Thread-Safe Circuit Breaker.
    States:
    - CLOSED: Normal operation. Requests flow freely.
    - OPEN: Tripped due to consecutive server failures (503/500/timeout). Requests blocked.
    - HALF_OPEN: Cooldown expired. Allows a single canary request to test recovery.
    """

    def __init__(self, failure_threshold: int = 5, cooldown_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._lock = threading.Lock()
        # Key: (provider, model) -> state dict
        self._circuits: Dict[str, Dict[str, Any]] = {}

    def _key(self, provider: str, model: str) -> str:
        return f"{provider.lower()}/{model.lower()}"

    def is_available(self, provider: str, model: str) -> bool:
        """Returns True if the circuit breaker allows a request to proceed."""
        k = self._key(provider, model)
        now = time.time()
        with self._lock:
            state = self._circuits.get(k)
            if not state:
                return True
            status = state.get("status", "CLOSED")
            if status == "CLOSED":
                return True
            if status == "OPEN":
                tripped_at = state.get("tripped_at", 0.0)
                if now - tripped_at >= self.cooldown_seconds:
                    state["status"] = "HALF_OPEN"
                    logger.info(f"  [CIRCUIT BREAKER] {provider}/{model} entered HALF_OPEN state. Testing canary request...")
                    return True
                return False
            if status == "HALF_OPEN":
                # Only 1 canary at a time
                return False
        return True

    def record_success(self, provider: str, model: str) -> None:
        """Records a successful API call. Resets failure count and closes circuit."""
        k = self._key(provider, model)
        with self._lock:
            state = self._circuits.get(k)
            if state:
                if state.get("status") in ("HALF_OPEN", "OPEN"):
                    logger.info(f"  [CIRCUIT BREAKER] {provider}/{model} recovered to CLOSED state.")
                state["status"] = "CLOSED"
                state["consecutive_failures"] = 0
                state["tripped_at"] = 0.0

    def record_failure(self, provider: str, model: str, error_msg: str = "") -> None:
        """Records a server-side failure. Trips circuit to OPEN if threshold exceeded."""
        k = self._key(provider, model)
        now = time.time()
        with self._lock:
            state = self._circuits.setdefault(k, {
                "status": "CLOSED",
                "consecutive_failures": 0,
                "tripped_at": 0.0,
                "last_error": "",
            })
            state["consecutive_failures"] += 1
            state["last_error"] = error_msg[:120]

            if state["consecutive_failures"] >= self.failure_threshold:
                state["status"] = "OPEN"
                state["tripped_at"] = now
                logger.warning(
                    f"  [CIRCUIT BREAKER TRIPPED] {provider}/{model} tripped to OPEN for {self.cooldown_seconds:.0f}s! "
                    f"Consecutive failures: {state['consecutive_failures']}. ({error_msg[:60]})"
                )

    def force_reset(self) -> None:
        """Resets all circuit breaker states back to CLOSED."""
        with self._lock:
            self._circuits.clear()


# Module-level singleton
_CIRCUIT_BREAKER_INSTANCE: Optional[CircuitBreaker] = None
_CB_LOCK = threading.Lock()


def get_circuit_breaker() -> CircuitBreaker:
    """Returns process-wide CircuitBreaker singleton."""
    global _CIRCUIT_BREAKER_INSTANCE
    if _CIRCUIT_BREAKER_INSTANCE is None:
        with _CB_LOCK:
            if _CIRCUIT_BREAKER_INSTANCE is None:
                _CIRCUIT_BREAKER_INSTANCE = CircuitBreaker()
    return _CIRCUIT_BREAKER_INSTANCE
