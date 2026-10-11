#!/usr/bin/env python3
"""
Audiobook Factory - Pillar 3: Model Gateway Control Plane Facade.
=================================================================
The Unified Entry Point for all 5 Production Rooms:
1. Room 1: Pre-Production & Extraction (gemini-3.6-flash / 3.7-flash)
2. Room 2: Hindustani Translation Collective (gemini-3.8-flash Flagship)
3. Room 3: Screenplay & Anti-Swap Attribution (gemini-3.8-flash Flagship)
4. Room 4: 4D Vocal Multi-Voice TTS (gemini-3.8-flash-tts Audio Tier)
5. Room 5: Broadcast Vocal Mastering & Verification

Integrates:
- ACID SQLite Key Inventory & Lease Manager (Phase 1)
- The 7 Iron Shields Anti-Ban Guard & Policy Engine (Phase 2)
- Canonical Model Registry & Polymorphic Adapters (Phase 3)
- Request Router with Fallback & Circuit Breakers (Phase 4)
"""

from __future__ import annotations
import os
import time
import threading
from typing import Dict, Any, Optional, List, Generator
from contextlib import contextmanager

from audiobook_factory.logger import logger
from audiobook_factory.core.models.registry import (
    ModelRegistry,
    ModelTier,
    Modality,
    ModelCapability,
    get_model_registry,
)
from audiobook_factory.core.models.lease_manager import (
    KeyLeaseManager,
    KeyLease,
    CallerIdentity,
    get_key_lease_manager,
    NoAvailableKeyError,
    AllKeysExhaustedTodayError,
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
from audiobook_factory.core.models.adapters.base import (
    GenerationResult,
    SpeechResult,
)
from audiobook_factory.core.models.adapters.gemini import ApiHttpError


class ModelGateway:
    """
    Unified Production Control Plane Facade.
    Thread-safe, multi-user, multi-provider gateway.
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        lease_manager: Optional[KeyLeaseManager] = None,
        anti_ban_guard: Optional[AntiBanGuard] = None,
        router: Optional[RequestRouter] = None,
    ):
        self.registry = registry or get_model_registry()
        self.lease_manager = lease_manager or get_key_lease_manager()
        self.anti_ban_guard = anti_ban_guard or get_anti_ban_guard()
        self.router = router or RequestRouter(
            registry=self.registry,
            lease_manager=self.lease_manager,
            circuit_breaker=get_circuit_breaker(),
        )
        self._lock = threading.RLock()

    def generate_text(
        self,
        prompt: str,
        task: str = "translation",
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        min_tier: Optional[ModelTier] = None,
        preferred_provider: str = "gemini",
        thinking_budget: Optional[int] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        response_json: bool = False,
        session_id: Optional[str] = None,
        word_count: int = 0,
        user_id: str = "user_default",
        fast_mode: bool = False,
        max_retries: int = 3,
        **kwargs,
    ) -> GenerationResult:
        """
        Executes text generation request through the control plane:
        1. Resolves execution plan & leases key.
        2. Applies Anti-Ban Gate (pacing, rate limit, anti-correlation).
        3. Dispatches request via adapter.
        4. Handles failover on 429 quota exhaustion or server error.
        5. Records metrics and safely releases lease.
        """
        identity = CallerIdentity(user_id=user_id, session_id=session_id or "session_default", workload_type="text")
        retries = 0
        last_error = None

        while retries <= max_retries:
            preferred_key = self.anti_ban_guard.affinity.get_affinity_key(session_id) if session_id else None
            plan = self.router.resolve_plan(
                task=task,
                preferred_provider=preferred_provider,
                min_tier=min_tier,
                modality=Modality.TEXT,
                identity=identity,
                model_override=model,
                preferred_key_alias=preferred_key,
            )
            if session_id:
                self.anti_ban_guard.affinity.bind_affinity(session_id, plan.key_alias)

            try:
                # Shield 1, 3, 4, 5, 7: Pre-request gate checks & pacing
                self.anti_ban_guard.pre_request_gate(
                    key_alias=plan.key_alias,
                    word_count=word_count,
                    session_id=session_id,
                    fast_mode=fast_mode,
                )

                # Execute request via chosen adapter
                result = plan.adapter.generate_text(
                    model=plan.model_id,
                    prompt=prompt,
                    api_key=plan.api_key,
                    system_instruction=system_instruction,
                    thinking_budget=thinking_budget,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    response_json=response_json,
                    **kwargs,
                )

                # Record success in SQLite and circuit breaker
                self.lease_manager.record_success(
                    api_key_or_hash=plan.lease.key_hash,
                    model=plan.model_id,
                    provider=plan.provider,
                    tokens_used=result.tokens_used,
                )
                self.anti_ban_guard.post_request_audit(
                    key_alias=plan.key_alias,
                    status_code=200,
                    model=plan.model_id,
                    session_id=session_id,
                )

                return result

            except ApiHttpError as e:
                last_error = e
                norm_err = self.anti_ban_guard.post_request_audit(
                    key_alias=plan.key_alias,
                    status_code=e.status_code,
                    error_body=e.error_body,
                    headers=e.headers,
                    provider=plan.provider,
                    model=plan.model_id,
                    session_id=session_id,
                )

                logger.warning(
                    f"  [GATEWAY ERROR] {plan.provider}/{plan.model_id} returned {norm_err.category}: {norm_err.message} "
                    f"(action: {norm_err.suggested_action})"
                )

                # Clear session affinity on any error so retries rotate to a fresh healthy key
                if session_id:
                    self.anti_ban_guard.affinity.clear_affinity(session_id)

                # Handle suggested actions
                if norm_err.suggested_action == "ROTATE_KEY":
                    if norm_err.category == "DAILY_QUOTA_EXHAUSTED":
                        self.lease_manager.mark_daily_quota_exhausted(
                            api_key_or_hash=plan.lease.key_hash,
                            error_msg=norm_err.message,
                            model=plan.model_id,
                            provider=plan.provider,
                        )
                    elif norm_err.category == "INVALID_KEY":
                        self.lease_manager.mark_invalid(
                            api_key_or_hash=plan.lease.key_hash,
                            error_msg=norm_err.message,
                            provider=plan.provider,
                        )
                    # Shield 3: Enforce anti-correlation delay before switching keys
                    self.anti_ban_guard.enforce_key_switch_cooldown(
                        prev_key_alias=plan.key_alias,
                        new_key_alias=f"{plan.key_alias}_next",
                        fast_mode=fast_mode,
                    )
                elif norm_err.suggested_action == "COOL_DOWN":
                    # Put current key on backoff (minimum 60s to allow provider sliding rate window to reset)
                    self.lease_manager.mark_temporary_backoff(
                        api_key_or_hash=plan.lease.key_hash,
                        backoff_seconds=max(norm_err.wait_sec, 60.0),
                        error_msg=norm_err.message,
                        model=plan.model_id,
                        provider=plan.provider,
                    )
                    if not fast_mode:
                        time.sleep(min(norm_err.wait_sec, 2.0))
                elif not norm_err.is_retryable:
                    raise

                retries += 1


            finally:
                # Always safely release lease back to SQLite
                self.lease_manager.release_lease(plan.lease.lease_id)

        if last_error:
            raise last_error
        raise RuntimeError("Generation failed after maximum retries.")

    def synthesize_speech(
        self,
        text: str,
        voice_name: str = "Puck",
        model: Optional[str] = None,
        preferred_provider: str = "gemini",
        session_id: Optional[str] = None,
        user_id: str = "user_default",
        fast_mode: bool = False,
        max_retries: int = 3,
        **kwargs,
    ) -> SpeechResult:
        """
        Executes speech synthesis (Room 4) adhering to strict 10 RPD daily quota ceilings:
        1. Resolves audio model (gemini-3.8-flash-tts).
        2. Leases key specifically for TTS workload.
        3. Applies cadence pacing and rate limit.
        4. Synthesizes and decodes audio into raw WAV bytes.
        """
        identity = CallerIdentity(user_id=user_id, session_id=session_id or "session_default", workload_type="tts")
        retries = 0
        last_error = None
        eff_fast_mode = fast_mode or bool(os.environ.get("PYTEST_CURRENT_TEST"))

        while retries <= max_retries:
            preferred_key = self.anti_ban_guard.affinity.get_affinity_key(session_id) if session_id else None
            plan = self.router.resolve_plan(
                task="tts",
                preferred_provider=preferred_provider,
                min_tier=ModelTier.TIER_AUDIO,
                modality=Modality.AUDIO,
                identity=identity,
                model_override=model,
                preferred_key_alias=preferred_key,
            )
            if session_id:
                self.anti_ban_guard.affinity.bind_affinity(session_id, plan.key_alias)

            try:
                self.anti_ban_guard.pre_request_gate(
                    key_alias=plan.key_alias,
                    word_count=len(text.split()),
                    session_id=session_id,
                    fast_mode=eff_fast_mode,
                )

                result = plan.adapter.synthesize_speech(
                    model=plan.model_id,
                    text=text,
                    voice_name=voice_name,
                    api_key=plan.api_key,
                    **kwargs,
                )

                self.lease_manager.record_success(
                    api_key_or_hash=plan.lease.key_hash,
                    model=plan.model_id,
                    provider=plan.provider,
                    tokens_used=result.tokens_used,
                )
                self.anti_ban_guard.post_request_audit(
                    key_alias=plan.key_alias,
                    status_code=200,
                    model=plan.model_id,
                    session_id=session_id,
                )

                result.metadata["attempt"] = retries + 1
                return result

            except ApiHttpError as e:
                last_error = e
                norm_err = self.anti_ban_guard.post_request_audit(
                    key_alias=plan.key_alias,
                    status_code=e.status_code,
                    error_body=e.error_body,
                    headers=e.headers,
                    provider=plan.provider,
                    model=plan.model_id,
                    session_id=session_id,
                )

                # Clear session affinity on any error so retries rotate to a fresh healthy key
                if session_id:
                    self.anti_ban_guard.affinity.clear_affinity(session_id)

                if norm_err.suggested_action == "ROTATE_KEY":
                    if norm_err.category == "DAILY_QUOTA_EXHAUSTED":
                        self.lease_manager.mark_daily_quota_exhausted(
                            api_key_or_hash=plan.lease.key_hash,
                            error_msg=norm_err.message,
                            model=plan.model_id,
                            provider=plan.provider,
                        )
                    elif norm_err.category == "INVALID_KEY":
                        self.lease_manager.mark_invalid(
                            api_key_or_hash=plan.lease.key_hash,
                            error_msg=norm_err.message,
                            provider=plan.provider,
                        )
                    self.anti_ban_guard.enforce_key_switch_cooldown(
                        prev_key_alias=plan.key_alias,
                        new_key_alias=f"{plan.key_alias}_next",
                        fast_mode=eff_fast_mode,
                    )
                elif norm_err.suggested_action == "COOL_DOWN":
                    # Put current key on backoff (minimum 60s to allow provider sliding rate window to reset)
                    self.lease_manager.mark_temporary_backoff(
                        api_key_or_hash=plan.lease.key_hash,
                        backoff_seconds=max(norm_err.wait_sec, 60.0),
                        error_msg=norm_err.message,
                        model=plan.model_id,
                        provider=plan.provider,
                    )
                    if not eff_fast_mode:
                        time.sleep(min(norm_err.wait_sec, 2.0))
                elif not norm_err.is_retryable:
                    raise

                retries += 1

            finally:
                self.lease_manager.release_lease(plan.lease.lease_id)

        if last_error:
            raise last_error
        raise RuntimeError("Speech synthesis failed after maximum retries.")

    @contextmanager
    def lease_session(
        self,
        session_id: str,
        task: str = "screenplay",
        user_id: str = "user_default",
        provider: str = "gemini",
    ) -> Generator[str, None, None]:
        """
        Shield 2: Context manager holding sticky session affinity across a whole scene (8-15 segments).
        """
        identity = CallerIdentity(user_id=user_id, workload_type="text")
        plan = self.router.resolve_plan(
            task=task,
            preferred_provider=provider,
            identity=identity,
        )
        self.anti_ban_guard.affinity.bind_affinity(session_id, plan.key_alias)

        try:
            yield plan.key_alias
        finally:
            self.anti_ban_guard.affinity.clear_affinity(session_id)
            self.lease_manager.release_lease(plan.lease.lease_id)

    def get_fleet_status(self) -> Dict[str, Any]:
        """Returns comprehensive diagnostic summary of keys, models, and breakers."""
        return {
            "gemini_keys": self.lease_manager.get_status_summary(provider="gemini"),
            "models_count": len(self.registry.list_models()),
            "tripwire_quarantined": self.anti_ban_guard.tripwire.is_quarantined()[0],
        }


# Module-level singleton
_MODEL_GATEWAY_INSTANCE: Optional[ModelGateway] = None
_GATEWAY_LOCK = threading.Lock()


def get_model_gateway() -> ModelGateway:
    """Returns process-wide ModelGateway singleton."""
    global _MODEL_GATEWAY_INSTANCE
    if _MODEL_GATEWAY_INSTANCE is None:
        with _GATEWAY_LOCK:
            if _MODEL_GATEWAY_INSTANCE is None:
                _MODEL_GATEWAY_INSTANCE = ModelGateway()
    return _MODEL_GATEWAY_INSTANCE
