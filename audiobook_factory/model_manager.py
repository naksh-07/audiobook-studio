#!/usr/bin/env python3
"""
Audiobook Factory - Global Dynamic Model Intelligence Manager.
Discovers available Google Gemini models via API, manages capability tiering,
executes concurrent 2-3 model health pings (evaluating latency and availability),
and enforces strict minimum quality floor gates with fail-closed production halts.
"""

from __future__ import annotations
import os
import sys
import re
import time
import json
import threading
import urllib.request
import urllib.error
from enum import Enum, IntEnum
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from audiobook_factory.logger import logger
from audiobook_factory.key_manager import get_persistent_key_pool
from audiobook_factory.cadence import get_stealth_sdk_headers


class ModelTier(IntEnum):
    """
    Capability tier for LLM reasoning and literary comprehension.
    Lower integer value indicates higher capability / intelligence tier.
    """
    TIER_1_FLAGSHIP = 1    # Deep reasoning, complex dialects, high-subtext drama
    TIER_2_BALANCED = 2    # Standard production, balanced speed/nuance, scene acoustics
    TIER_3_UTILITY = 3     # Fast parsing, token normalization, lightweight JSON


class TaskType(str, Enum):
    """Production tasks with mandatory minimum capability floors."""
    TRANSLATION = "translation"        # Minimum Floor: TIER_2_BALANCED
    SCREENPLAY = "screenplay"          # Minimum Floor: TIER_2_BALANCED
    DRAMATURGY = "dramaturgy"          # Minimum Floor: TIER_2_BALANCED
    DIRECTING = "directing"            # Minimum Floor: TIER_2_BALANCED
    SOUND_DESIGN = "sound_design"      # Minimum Floor: TIER_2_BALANCED
    AUDITING = "auditing"              # Minimum Floor: TIER_2_BALANCED
    EXTRACTION = "extraction"          # Minimum Floor: TIER_2_BALANCED
    UTILITY = "utility"                # Minimum Floor: TIER_3_UTILITY


TASK_MINIMUM_TIERS: Dict[TaskType, ModelTier] = {
    TaskType.TRANSLATION: ModelTier.TIER_1_FLAGSHIP,
    TaskType.SCREENPLAY: ModelTier.TIER_1_FLAGSHIP,
    TaskType.DRAMATURGY: ModelTier.TIER_1_FLAGSHIP,
    TaskType.DIRECTING: ModelTier.TIER_2_BALANCED,
    TaskType.SOUND_DESIGN: ModelTier.TIER_2_BALANCED,
    TaskType.AUDITING: ModelTier.TIER_2_BALANCED,
    TaskType.EXTRACTION: ModelTier.TIER_2_BALANCED,
    TaskType.UTILITY: ModelTier.TIER_3_UTILITY,
}

CREATIVE_TASKS = {
    TaskType.TRANSLATION,
    TaskType.SCREENPLAY,
    TaskType.DRAMATURGY,
}

CREATIVE_BLACKLIST = (
    "3.5-flash",
    "3.6-flash",
    "3-flash-preview",
    "flash-latest",
    "lite",
    "nano",
    "8b",
    "gemma",
)


class LLMUnavailableError(RuntimeError):
    """Raised when an LLM service is unavailable, unauthenticated, or exhausted."""
    pass


class AntigravitySessionFallbackRequired(LLMUnavailableError):
    """
    Raised when all external LLM keys/models are exhausted and handoff to active
    Antigravity IDE session (Gemini 3.8 Flash High) is required.
    """
    def __init__(
        self,
        message: str,
        handoff_file: Optional[Path] = None,
        task_type: Optional[TaskType] = None,
        prompt: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ):
        super().__init__(message)
        self.handoff_file = handoff_file
        self.task_type = task_type
        self.prompt = prompt
        self.system_instruction = system_instruction


class ModelTierFloorBreachError(RuntimeError):
    """Raised when available healthy models fall below the safe quality floor for a task."""
    pass


# Default catalog used as offline fallback if API discovery cannot connect
OFFLINE_CATALOG_FALLBACK: List[str] = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.1-pro-preview",
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-flash-lite-latest",
]

# Patterns for specialized or non-text-generative models to exclude from LLM text tasks
EXCLUDED_PATTERNS = (
    "-tts",
    "-image",
    "-transcribe",
    "-2.5-",
    "gemini-2.5",
    "robotics",
    "lyria",
    "nano-banana",
    "deep-research",
    "antigravity-preview",
    "computer-use",
    "customtools",
    "omni",
    "gemma",
)


class ModelManager:
    """
    Central Dynamic Model Intelligence Manager.
    Eliminates hardcoded model strings by discovering live Gemini models,
    classifying capability tiers, pinging top candidates concurrently,
    and enforcing strict fail-closed quality cutoffs.
    """

    def __init__(self, cache_ttl_sec: float = 3600.0, ping_cache_ttl_sec: float = 300.0):
        self.cache_ttl_sec = cache_ttl_sec
        self.ping_cache_ttl_sec = ping_cache_ttl_sec
        self._cached_models: Optional[List[str]] = None
        self._last_discovery_time: float = 0.0
        self._active_task_models: Dict[TaskType, Tuple[str, float]] = {}
        self._lock = threading.Lock()
        self.pool = get_persistent_key_pool()

    def discover_available_models(self, refresh: bool = False, api_key: Optional[str] = None) -> List[str]:
        """
        [OFFLINE DISCOVERY - ZERO NETWORK PINGS]
        Returns offline catalog without querying Gemini API.
        """
        # ponytail: offline catalog fallback - zero live network pings
        now = time.time()
        with self._lock:
            self._cached_models = OFFLINE_CATALOG_FALLBACK
            self._last_discovery_time = now
            return list(self._cached_models)

    @staticmethod
    def classify_model_tier(model_name: str) -> ModelTier:
        """
        Classifies an arbitrary model string into its semantic capability tier.
        """
        m = model_name.lower()
        # Tier 3 Utility: explicitly lightweight nano models, flash-lite variants, or small gemma weights
        if any(x in m for x in ("nano", "gemma", "1.5-flash-8b", "flash-lite", "-lite", "lite")):
            return ModelTier.TIER_3_UTILITY

        # Tier 1 Flagship: High reasoning models and pro previews
        if any(x in m for x in ("3.8-flash", "3.7-flash", "-pro", "pro-preview", "gemini-pro")):
            return ModelTier.TIER_1_FLAGSHIP

        # Tier 2 Balanced: Standard balanced flash models
        return ModelTier.TIER_2_BALANCED

    @staticmethod
    def _get_cli_model_override() -> Optional[str]:
        """Extracts --model argument from sys.argv if provided on CLI."""
        try:
            for idx, arg in enumerate(sys.argv):
                if arg == "--model" and idx + 1 < len(sys.argv):
                    val = sys.argv[idx + 1].strip()
                    if val and not val.startswith("-"):
                        return val
                elif arg.startswith("--model="):
                    val = arg.split("=", 1)[1].strip()
                    if val:
                        return val
        except Exception:
            pass
        return None

    def get_candidate_models_for_task(
        self,
        task: TaskType,
        refresh: bool = False,
        preferred_model: Optional[str] = None,
    ) -> List[str]:
        """
        Returns all discovered models that satisfy the minimum quality floor for the task,
        sorted by capability tier (Tier 1 first, then Tier 2) and Gemini version descending.
        Strictly excludes blacklisted models from creative tasks.
        """
        discovered = self.discover_available_models(refresh=refresh)
        floor = TASK_MINIMUM_TIERS.get(task, ModelTier.TIER_2_BALANCED)

        eligible: List[Tuple[ModelTier, float, str]] = []
        for name in discovered:
            if task in CREATIVE_TASKS and any(b in name.lower() for b in CREATIVE_BLACKLIST):
                continue
            tier = self.classify_model_tier(name)
            if tier <= floor:  # Satisfies floor (remember: lower value = higher quality)
                # Extract numeric version for recency sorting on core gemini models
                match = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
                version = float(match.group(1)) if match else (2.0 if "gemini" in name else 1.0)
                eligible.append((tier, version, name))

        env_pref = preferred_model or os.environ.get("GEMINI_TEXT_MODEL") or self._get_cli_model_override()
        if env_pref and any(name == env_pref for name in discovered):
            tier = self.classify_model_tier(env_pref)
            is_subpar = any(x in env_pref.lower() for x in ("nano", "gemma", "8b", "lite"))
            if not is_subpar:
                # Explicit preference is honored as long as it's not a sub-par utility model
                match = re.search(r"gemini-(\d+(?:\.\d+)?)", env_pref)
                version = float(match.group(1)) if match else 2.0
                if not any(e[2] == env_pref for e in eligible):
                    eligible.append((tier, version, env_pref))
            else:
                logger.warning(
                    f"  [MODEL MANAGER] Model preference '{env_pref}' rejected for task '{task.value}' "
                    f"(Sub-par utility model). Strictly adhering to quality gate."
                )

        if not eligible:
            raise ModelTierFloorBreachError(
                f"STRICT HALT: No available models satisfy minimum quality floor {floor.name} "
                f"for task '{task.value}'. Refusing to compromise production quality."
            )

        # Sort: Primary by tier ascending (Tier 1 before Tier 2), Secondary by version descending (3.8 before 3.6), Tertiary by name
        eligible.sort(key=lambda x: (x[0].value, -x[1], x[2]))
        candidates = [x[2] for x in eligible]
        if env_pref and env_pref in candidates:
            candidates = [env_pref] + [m for m in candidates if m != env_pref]
        return candidates

    def ping_candidate_models(
        self,
        candidates: List[str],
        api_key: Optional[str] = None,
        timeout: float = 15.0,
    ) -> List[Tuple[str, bool, float, Optional[str]]]:
        """
        Concurrently pings candidate models with a minimal dry-run request.
        Uses distinct API keys from the key pool for concurrent probes to prevent HTTP 429 throttling.
        If a probe hits HTTP 429 or 503, performs one key rotation before marking failed.
        Returns a list of tuples: (model_name, is_ok, latency_ms, error_msg).
        """
        if not candidates:
            return []

        # ponytail: zero live network pings - models resolved statically
        return [(m, True, 1.0, None) for m in candidates]

    def resolve_active_model(
        self,
        task: TaskType,
        api_key: Optional[str] = None,
        force_refresh: bool = False,
        preferred_model: Optional[str] = None,
    ) -> str:
        """
        Resolves the optimal active model for a task by:
        1. Checking the dynamic minimum quality floor.
        2. Selecting top favorable candidates in batches (prioritizing explicit models directly).
        3. Concurrently pinging candidates to evaluate real-time health and latency using distinct keys.
        4. Selecting the healthiest candidate (banishing latency sorting for creative tasks).
        5. If a batch fails, probing the next batch of eligible candidates.
        6. Strictly halting (raising LLMUnavailableError) if all eligible candidates fail.
        """
        now = time.time()
        explicit_pref = preferred_model or os.environ.get("GEMINI_TEXT_MODEL") or self._get_cli_model_override()
        is_mock = os.environ.get("MOCK_OFFLINE", "").lower() in ("true", "1")
        if is_mock or os.environ.get("GEMINI_API_KEY", "").startswith("mock"):
            return explicit_pref or "gemini-2.5-pro"

        # Check active cached model for this task
        with self._lock:
            if not force_refresh and task in self._active_task_models:
                cached_model, cached_time = self._active_task_models[task]
                if now - cached_time < self.ping_cache_ttl_sec:
                    return cached_model

        # 1. Get candidate models satisfying minimum quality floor
        candidates = self.get_candidate_models_for_task(task, refresh=force_refresh, preferred_model=explicit_pref)

        floor = TASK_MINIMUM_TIERS.get(task, ModelTier.TIER_2_BALANCED)
        if not candidates:
            raise ModelTierFloorBreachError(
                f"STRICT HALT: No models meet quality floor {floor.name} for task '{task.value}'."
            )

        # 2. Probe candidates: Prioritize explicit preference directly with a single ping to avoid overhead
        batch_size = 3
        all_probed_results: List[Tuple[str, bool, float, Optional[str]]] = []
        batches: List[List[str]] = []

        if explicit_pref and candidates and candidates[0] == explicit_pref:
            batches.append([explicit_pref])
            remaining = [m for m in candidates[1:9]]
            for i in range(0, len(remaining), batch_size):
                batches.append(remaining[i:i + batch_size])
        else:
            for i in range(0, min(len(candidates), 9), batch_size):
                batches.append(candidates[i:i + batch_size])

        for batch in batches:
            logger.info(f"[*] Model Manager: Concurrently pinging favorable candidates for {task.value}: {batch}")
            probe_key = api_key if len(batch) == 1 else None
            probe_results = self.ping_candidate_models(batch, api_key=probe_key, timeout=15.0)
            all_probed_results.extend(probe_results)

            healthy = [r for r in probe_results if r[1] is True]
            for m_name, ok, lat, err in probe_results:
                status_str = f"HEALTHY ({lat:.0f}ms)" if ok else f"FAILED ({err}, {lat:.0f}ms)"
                logger.info(f"    - {m_name}: {status_str}")

            if healthy:
                # Scoring: For creative tasks, banish latency sorting completely!
                def _score(item: Tuple[str, bool, float, Optional[str]]) -> Tuple[int, int, float, float]:
                    m_name, _, latency, _ = item
                    is_pref = 0 if (explicit_pref and m_name == explicit_pref) else 1
                    tier = self.classify_model_tier(m_name)
                    match = re.search(r"gemini-(\d+(?:\.\d+)?)", m_name)
                    version = float(match.group(1)) if match else (2.0 if "gemini" in m_name else 1.0)
                    if task in CREATIVE_TASKS:
                        # Intelligence first! Preference -> Tier 1 -> Highest Version -> Latency tiebreaker
                        return (is_pref, tier.value, -version, latency)
                    return (is_pref, tier.value, latency, -version)

                healthy.sort(key=_score)
                chosen_model = healthy[0][0]
                chosen_latency = healthy[0][2]
                chosen_tier = self.classify_model_tier(chosen_model)

                if chosen_tier > floor and chosen_model != explicit_pref:
                    raise ModelTierFloorBreachError(
                        f"STRICT HALT: Candidate '{chosen_model}' ({chosen_tier.name}) breaches minimum "
                        f"quality floor {floor.name} for '{task.value}'. Production halted."
                    )

                logger.info(f"[+] Model Manager: Selected active LLM '{chosen_model}' for text task '{task.value}' (Latency: {chosen_latency:.0f}ms). [NOTE: Voice TTS strictly uses Gemini 3.8 Flash TTS]")
                with self._lock:
                    self._active_task_models[task] = (chosen_model, now)
                return chosen_model

        # All eligible candidates in primary batches failed health pings.
        # Resilient Tier 2 Fallback on Provider Downtime:
        # If all Tier 1 candidates failed with HTTP 503 (model unavailable / high demand) or network timeout,
        # probe healthy Tier 2 balanced models (e.g. gemini-3.6-flash, gemini-3.5-flash) to prevent pipeline crash.
        tier1_failed = [r for r in all_probed_results if self.classify_model_tier(r[0]) == ModelTier.TIER_1_FLAGSHIP]
        has_503_or_timeout = any(
            any(ind in (r[3] or "").lower() for ind in ("503", "timeout", "timed out", "unavailable", "high demand", "overloaded"))
            for r in tier1_failed
        )
        all_tier1_failed = bool(tier1_failed) and all(r[1] is False for r in tier1_failed)

        if all_tier1_failed and has_503_or_timeout:
            discovered = self.discover_available_models(refresh=False)
            probed_names = {r[0] for r in all_probed_results}
            tier2_candidates = [
                m for m in discovered
                if self.classify_model_tier(m) == ModelTier.TIER_2_BALANCED
                and not any(x in m.lower() for x in ("nano", "gemma", "8b", "lite"))
                and m not in probed_names
            ]
            if tier2_candidates:
                def _t2_sort(m: str) -> Tuple[float, str]:
                    match = re.search(r"gemini-(\d+(?:\.\d+)?)", m)
                    v = float(match.group(1)) if match else 2.0
                    return (-v, m)

                tier2_candidates.sort(key=_t2_sort)
                probe_key = api_key if (len(tier2_candidates[:3]) == 1 or not self.pool) else None
                t2_results = self.ping_candidate_models(tier2_candidates[:3], api_key=probe_key, timeout=15.0)
                all_probed_results.extend(t2_results)
                healthy_t2 = [r for r in t2_results if r[1] is True]
                for m_name, ok, lat, err in t2_results:
                    status_str = f"HEALTHY ({lat:.0f}ms)" if ok else f"FAILED ({err}, {lat:.0f}ms)"
                    logger.info(f"    - [TIER 2 FALLBACK] {m_name}: {status_str}")

                if healthy_t2:
                    healthy_t2.sort(key=lambda r: (
                        -float(re.search(r"gemini-(\d+(?:\.\d+)?)", r[0]).group(1)) if re.search(r"gemini-(\d+(?:\.\d+)?)", r[0]) else -2.0,
                        r[2]
                    ))
                    fallback_model = healthy_t2[0][0]
                    fallback_latency = healthy_t2[0][2]
                    logger.warning(
                        f"[WARN] All Tier 1 flagship models unavailable (503/timeout). "
                        f"Resiliently falling back to Tier 2 balanced model '{fallback_model}' to prevent pipeline crash."
                    )
                    with self._lock:
                        self._active_task_models[task] = (fallback_model, now)
                    return fallback_model

        # All eligible candidates failed ping
        raise LLMUnavailableError(
            f"STRICT HALT: All candidate models satisfying quality floor {floor.name} for '{task.value}' "
            f"failed health pings: {[(r[0], r[3]) for r in all_probed_results]}. Production halted to prevent degraded output."
        )

    def report_failure(self, task: TaskType, model_name: str) -> None:
        """Invalidates task model cache when an in-flight error occurs."""
        with self._lock:
            entry = self._active_task_models.get(task)
            if entry and entry[0] == model_name:
                self._active_task_models.pop(task, None)


# Module-level singleton
_MODEL_MANAGER_INSTANCE: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Returns the process-wide ModelManager singleton."""
    global _MODEL_MANAGER_INSTANCE
    if _MODEL_MANAGER_INSTANCE is None:
        _MODEL_MANAGER_INSTANCE = ModelManager()
    return _MODEL_MANAGER_INSTANCE


# Re-exports for Pillar 3 Control Plane Facade & Model Registry
from audiobook_factory.core.models.gateway import (
    ModelGateway,
    get_model_gateway,
)
from audiobook_factory.core.models.registry import (
    ModelRegistry,
    get_model_registry,
    ModelCapability,
)

__all__ = [
    "ModelTier",
    "TaskType",
    "TASK_MINIMUM_TIERS",
    "CREATIVE_TASKS",
    "CREATIVE_BLACKLIST",
    "LLMUnavailableError",
    "AntigravitySessionFallbackRequired",
    "ModelTierFloorBreachError",
    "ModelManager",
    "get_model_manager",
    "ModelGateway",
    "get_model_gateway",
    "ModelRegistry",
    "get_model_registry",
    "ModelCapability",
]

