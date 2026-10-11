#!/usr/bin/env python3
"""
Audiobook Factory - Pillar 3: Request Router & Execution Planner.
=================================================================
Resolves incoming requests by matching:
Task Requirements -> Eligible Models -> Circuit Breaker State -> Key Inventory -> Provider Adapter.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from audiobook_factory.logger import logger
from audiobook_factory.core.models.registry import (
    ModelRegistry,
    ModelCapability,
    ModelTier,
    Modality,
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
from audiobook_factory.core.models.policy_engine import (
    CircuitBreaker,
    get_circuit_breaker,
)
from audiobook_factory.core.models.adapters.base import BaseProviderAdapter
from audiobook_factory.core.models.adapters.gemini import GeminiProviderAdapter
from audiobook_factory.core.models.adapters.openai_compat import OpenAICompatibleAdapter
from audiobook_factory.core.models.adapters.local_gpu import LocalGpuAdapter


@dataclass
class ExecutionPlan:
    """Complete execution blueprint for an API request."""
    model_capability: ModelCapability
    provider: str
    adapter: BaseProviderAdapter
    lease: KeyLease
    key_alias: str
    api_key: str
    model_id: str


class RequestRouter:
    """
    Intelligent Request Router matching task requirements to eligible healthy resources.
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        lease_manager: Optional[KeyLeaseManager] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.registry = registry or get_model_registry()
        self.lease_manager = lease_manager or get_key_lease_manager()
        self.circuit_breaker = circuit_breaker or get_circuit_breaker()

        # Cache of provider adapters
        self._gemini_adapter = GeminiProviderAdapter()
        self._openai_adapters: Dict[str, OpenAICompatibleAdapter] = {}
        self._local_adapter = LocalGpuAdapter()

    def _get_adapter(self, provider: str) -> BaseProviderAdapter:
        """Resolves or instantiates provider adapter."""
        prov = provider.lower().strip()
        if prov == "gemini":
            return self._gemini_adapter
        elif prov in ("cerebras", "groq", "openai", "openrouter"):
            if prov not in self._openai_adapters:
                self._openai_adapters[prov] = OpenAICompatibleAdapter(provider=prov)
            return self._openai_adapters[prov]
        elif prov == "local":
            return self._local_adapter
        else:
            if prov not in self._openai_adapters:
                self._openai_adapters[prov] = OpenAICompatibleAdapter(provider=prov)
            return self._openai_adapters[prov]

    def resolve_plan(
        self,
        task: str,
        preferred_provider: str = "gemini",
        min_tier: Optional[ModelTier] = None,
        modality: Modality = Modality.TEXT,
        identity: Optional[CallerIdentity] = None,
        model_override: Optional[str] = None,
        preferred_key_alias: Optional[str] = None,
    ) -> ExecutionPlan:
        """
        Builds an ExecutionPlan:
        1. Selects healthy candidate model matching constraints.
        2. Bypasses models whose Circuit Breaker is OPEN.
        3. Acquires an exclusive ACID lease on a matching key (prioritizing preferred_key_alias if valid).
        4. Links the correct polymorphic provider adapter.
        """
        # Determine candidate models
        candidate_models: List[ModelCapability] = []

        if model_override:
            override_cap = self.registry.get_model(model_override)
            if override_cap:
                candidate_models.append(override_cap)

        # Query registry for primary and fallbacks
        primary = self.registry.resolve_best_model(
            task=task,
            preferred_provider=preferred_provider,
            min_tier=min_tier,
            modality=modality,
        )
        if primary and primary.model_id not in [c.model_id for c in candidate_models]:
            candidate_models.append(primary)

        # Add remaining fallbacks of matching tier and modality
        all_matching = self.registry.filter_models(
            min_tier=min_tier,
            modality=modality,
        )
        existing_ids = {c.model_id for c in candidate_models}
        for m in all_matching:
            if m.model_id not in existing_ids:
                candidate_models.append(m)

        # Iterate through candidates checking circuit breaker health
        last_error = None
        for candidate in candidate_models:
            if not self.circuit_breaker.is_available(candidate.provider, candidate.model_id):
                logger.warning(
                    f"  [ROUTER] Skipping {candidate.provider}/{candidate.model_id} (Circuit Breaker is OPEN)."
                )
                continue

            # Determine workload type: 'tts' for audio models, 'text' for text models
            workload_type = "tts" if modality == Modality.AUDIO or "tts" in candidate.model_id.lower() else "text"

            try:
                lease = self.lease_manager.acquire_lease(
                    workload_type=workload_type,
                    provider=candidate.provider,
                    model=candidate.model_id,
                    identity=identity,
                    preferred_key_alias=preferred_key_alias,
                )
            except (NoAvailableKeyError, AllKeysExhaustedTodayError) as e:
                last_error = e
                logger.debug(f"  [ROUTER] Key unavailable for {candidate.provider}/{candidate.model_id}: {e}")
                continue

            adapter = self._get_adapter(candidate.provider)

            return ExecutionPlan(
                model_capability=candidate,
                provider=candidate.provider,
                adapter=adapter,
                lease=lease,
                key_alias=lease.key_alias,
                api_key=lease.api_key,
                model_id=candidate.model_id,
            )

        if last_error:
            raise last_error
        raise NoAvailableKeyError(f"No available healthy models and keys for task '{task}'.")
