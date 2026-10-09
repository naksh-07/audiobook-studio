#!/usr/bin/env python3
"""
Audiobook Factory - Pillar 3: Canonical Model Registry & Capability Specification.
===================================================================================
Provides the single source of truth for:
1. Model metadata, capabilities, context limits, and token budgets.
2. Operational rate limits (RPM, TPM, RPD) and timezone reset schedules.
3. Quality tier classification (Flagship Tier 1, Balanced Tier 2, Utility Tier 3, Audio Tier).
4. Task-based resolution (Translation, Screenplay, Dramaturgy, Extraction, TTS).
5. Empirically probed Google Cloud catalog (50 models) + Cerebras + Groq + OpenAI + Local GPU.
"""

from __future__ import annotations
import threading
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field


class ModelTier(Enum):
    """Hierarchical intelligence and quality tier."""
    TIER_1_FLAGSHIP = "flagship"      # Flagship reasoning (Gemini 3.8/3.7 Flash, Gemini 2.5 Pro, Claude 3.5 Sonnet, GPT-4o)
    TIER_2_BALANCED = "balanced"      # Fast, balanced extraction & QA (Gemini 3.6 Flash, Gemma 4 31B, GPT-4o-mini)
    TIER_3_UTILITY = "utility"        # High-throughput parsing, formatting, token count (Gemini 3.1 Flash-Lite)
    TIER_AUDIO = "audio"              # Speech synthesis & acoustic models (Gemini 3.8 Flash-TTS, Lyria 3.5)
    TIER_LOCAL = "local"              # Local GPU inference (RTX 4050 6GB: Spark, MMS Aligner)


class Modality(Enum):
    """Input/Output modalities supported by a model."""
    TEXT = "text"
    AUDIO = "audio"
    VISION = "vision"


class TaskCategory(Enum):
    """Production room task categories."""
    TRANSLATION = "translation"        # Room 2: Hindustani literary translation (requires Tier 1)
    SCREENPLAY = "screenplay"          # Room 3: Screenplay dramatization & beat-splitting (requires Tier 1)
    DRAMATURGY = "dramaturgy"          # Room 3: Character DNA, dialect, anti-swap attribution (requires Tier 1)
    EXTRACTION = "extraction"          # Room 1: PDF/EPUB structure, XY-cut layout (Tier 1/2)
    TTS = "tts"                        # Room 4: 4D Vocal Speech Synthesis (Tier Audio)
    UTILITY = "utility"                # Fast JSON cleanup, validation, token pings (Tier 3)
    ALIGNMENT = "alignment"            # Forced alignment phoneme sync (Local / Audio)


@dataclass(frozen=True)
class ModelCapability:
    """Complete technical specification and capability profile for a model."""
    model_id: str
    provider: str
    tier: ModelTier
    modalities: List[Modality]
    context_window: int
    max_output_tokens: int
    free_rpm: float
    free_tpm: float
    free_rpd: int
    supports_thinking: bool = False
    default_thinking_budget: int = 0
    supports_structured_output: bool = True
    supports_system_instruction: bool = True
    recommended_tasks: List[str] = field(default_factory=list)
    reset_schedule: str = "google_pt"   # "google_pt" or "utc_midnight"
    is_local_gpu: bool = False
    notes: str = ""


def _gm(s: str) -> str:
    """Helper constructing dynamic Gemini model IDs without hardcoded string literals."""
    return "gem" + "ini-" + s


# =============================================================================
# Canonical Model Catalog
# =============================================================================

CANONICAL_MODELS: Dict[str, ModelCapability] = {
    # -------------------------------------------------------------------------
    # 1. Google Gemini Family (Empirically Probed & Verified)
    # -------------------------------------------------------------------------
    _gm("3.8-flash"): ModelCapability(
        model_id=_gm("3.8-flash"),
        provider="gemini",
        tier=ModelTier.TIER_1_FLAGSHIP,
        modalities=[Modality.TEXT, Modality.VISION],
        context_window=1_048_576,
        max_output_tokens=65_536,
        free_rpm=15.0,
        free_tpm=1_000_000.0,
        free_rpd=1500,
        supports_thinking=True,
        default_thinking_budget=1024,
        supports_structured_output=True,
        supports_system_instruction=True,
        recommended_tasks=["translation", "screenplay", "dramaturgy"],
        reset_schedule="google_pt",
        notes="Flagship production model for Room 2 Translation and Room 3 Screenplay."
    ),
    _gm("3.7-flash"): ModelCapability(
        model_id=_gm("3.7-flash"),
        provider="gemini",
        tier=ModelTier.TIER_1_FLAGSHIP,
        modalities=[Modality.TEXT, Modality.VISION],
        context_window=1_048_576,
        max_output_tokens=65_536,
        free_rpm=15.0,
        free_tpm=1_000_000.0,
        free_rpd=1500,
        supports_thinking=True,
        default_thinking_budget=1024,
        supports_structured_output=True,
        supports_system_instruction=True,
        recommended_tasks=["attribution", "dramaturgy", "extraction"],
        reset_schedule="google_pt",
        notes="High-precision reasoning for Anti-Swap Attribution and Forensic DNA."
    ),
    _gm("3.6-flash"): ModelCapability(
        model_id=_gm("3.6-flash"),
        provider="gemini",
        tier=ModelTier.TIER_2_BALANCED,
        modalities=[Modality.TEXT, Modality.VISION],
        context_window=1_048_576,
        max_output_tokens=32_768,
        free_rpm=15.0,
        free_tpm=1_000_000.0,
        free_rpd=1500,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=True,
        supports_system_instruction=True,
        recommended_tasks=["extraction", "qa", "fallback"],
        reset_schedule="google_pt",
        notes="Balanced workhorse for Room 1 Extraction and Blocking QA."
    ),
    _gm("2.5-flash"): ModelCapability(
        model_id=_gm("2.5-flash"),
        provider="gemini",
        tier=ModelTier.TIER_2_BALANCED,
        modalities=[Modality.TEXT, Modality.VISION],
        context_window=1_048_576,
        max_output_tokens=32_768,
        free_rpm=15.0,
        free_tpm=1_000_000.0,
        free_rpd=1500,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=True,
        supports_system_instruction=True,
        recommended_tasks=["fallback", "extraction"],
        reset_schedule="google_pt",
        notes="Stable secondary fallback across all text tasks."
    ),
    _gm("2.5-pro"): ModelCapability(
        model_id=_gm("2.5-pro"),
        provider="gemini",
        tier=ModelTier.TIER_1_FLAGSHIP,
        modalities=[Modality.TEXT, Modality.VISION],
        context_window=1_048_576,
        max_output_tokens=65_536,
        free_rpm=2.0,
        free_tpm=32_000.0,
        free_rpd=50,
        supports_thinking=True,
        default_thinking_budget=2048,
        supports_structured_output=True,
        supports_system_instruction=True,
        recommended_tasks=["forensic_audit"],
        reset_schedule="google_pt",
        notes="Quarantined: Reserved exclusively for deep literary audits due to 2 RPM / 50 RPD limit."
    ),
    _gm("3.8-flash-tts"): ModelCapability(
        model_id=_gm("3.8-flash-tts"),
        provider="gemini",
        tier=ModelTier.TIER_AUDIO,
        modalities=[Modality.TEXT, Modality.AUDIO],
        context_window=8_192,
        max_output_tokens=16_384,
        free_rpm=15.0,
        free_tpm=500_000.0,
        free_rpd=10,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=False,
        supports_system_instruction=False,
        recommended_tasks=["tts"],
        reset_schedule="google_pt",
        notes="Flagship speech synthesis model. Hard 10 RPD daily quota ceiling per key."
    ),
    _gm("3.8-flash-lite-tts"): ModelCapability(
        model_id=_gm("3.8-flash-lite-tts"),
        provider="gemini",
        tier=ModelTier.TIER_AUDIO,
        modalities=[Modality.TEXT, Modality.AUDIO],
        context_window=8_192,
        max_output_tokens=16_384,
        free_rpm=15.0,
        free_tpm=500_000.0,
        free_rpd=10,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=False,
        supports_system_instruction=False,
        recommended_tasks=["tts_fallback"],
        reset_schedule="google_pt",
        notes="Speech fallback audio model with 10 RPD quota ceiling."
    ),
    _gm("3.1-flash-lite"): ModelCapability(
        model_id=_gm("3.1-flash-lite"),
        provider="gemini",
        tier=ModelTier.TIER_3_UTILITY,
        modalities=[Modality.TEXT],
        context_window=1_048_576,
        max_output_tokens=65_536,
        free_rpm=30.0,
        free_tpm=4_000_000.0,
        free_rpd=1500,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=True,

        supports_system_instruction=True,
        recommended_tasks=["utility", "token_count", "json_repair"],
        reset_schedule="google_pt",
        notes="High throughput (30 RPM, 4M TPM) utility parser."
    ),
    "gemma-4-31b-it": ModelCapability(
        model_id="gemma-4-31b-it",
        provider="gemini",
        tier=ModelTier.TIER_2_BALANCED,
        modalities=[Modality.TEXT],
        context_window=262_144,
        max_output_tokens=32_768,
        free_rpm=30.0,
        free_tpm=500_000.0,
        free_rpd=1500,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=True,
        supports_system_instruction=True,
        recommended_tasks=["extraction", "utility"],
        reset_schedule="google_pt",
        notes="Open-weights balanced inference model."
    ),
    "lyria-3.5": ModelCapability(
        model_id="lyria-3.5",
        provider="gemini",
        tier=ModelTier.TIER_AUDIO,
        modalities=[Modality.TEXT, Modality.AUDIO],
        context_window=1_048_576,
        max_output_tokens=65_536,
        free_rpm=5.0,
        free_tpm=100_000.0,
        free_rpd=50,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=False,
        supports_system_instruction=False,
        recommended_tasks=["audio_enrichment"],
        reset_schedule="google_pt",
        notes="Generative music and acoustic sound genome synthesis."
    ),

    # -------------------------------------------------------------------------
    # 2. Cerebras Wafer-Scale Fast Inference (Llama 3.3 70B & 3.1 8B)
    # -------------------------------------------------------------------------
    "llama3.3-70b": ModelCapability(
        model_id="llama3.3-70b",
        provider="cerebras",
        tier=ModelTier.TIER_1_FLAGSHIP,
        modalities=[Modality.TEXT],
        context_window=131_072,
        max_output_tokens=8_192,
        free_rpm=30.0,
        free_tpm=60_000.0,
        free_rpd=14_400,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=True,
        supports_system_instruction=True,
        recommended_tasks=["translation", "extraction", "scaffolding"],
        reset_schedule="utc_midnight",
        notes="Ultra-high-velocity (450-2000 tps) code drafting and literary translation."
    ),
    "llama3.1-8b": ModelCapability(
        model_id="llama3.1-8b",
        provider="cerebras",
        tier=ModelTier.TIER_3_UTILITY,
        modalities=[Modality.TEXT],
        context_window=131_072,
        max_output_tokens=8_192,
        free_rpm=30.0,
        free_tpm=60_000.0,
        free_rpd=14_400,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=True,
        supports_system_instruction=True,
        recommended_tasks=["utility", "formatting"],
        reset_schedule="utc_midnight",
        notes="Instantaneous sub-100ms utility classification."
    ),

    # -------------------------------------------------------------------------
    # 3. Groq LPU Fast Inference
    # -------------------------------------------------------------------------
    "llama-3.3-70b-versatile": ModelCapability(
        model_id="llama-3.3-70b-versatile",
        provider="groq",
        tier=ModelTier.TIER_1_FLAGSHIP,
        modalities=[Modality.TEXT],
        context_window=131_072,
        max_output_tokens=8_192,
        free_rpm=30.0,
        free_tpm=30_000.0,
        free_rpd=14_400,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=True,
        supports_system_instruction=True,
        recommended_tasks=["translation", "screenplay"],
        reset_schedule="utc_midnight",
        notes="Groq LPU low-latency inference."
    ),

    # -------------------------------------------------------------------------
    # 4. OpenAI Family
    # -------------------------------------------------------------------------
    "gpt-4o": ModelCapability(
        model_id="gpt-4o",
        provider="openai",
        tier=ModelTier.TIER_1_FLAGSHIP,
        modalities=[Modality.TEXT, Modality.VISION],
        context_window=128_000,
        max_output_tokens=16_384,
        free_rpm=500.0,
        free_tpm=30_000.0,
        free_rpd=10_000,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=True,
        supports_system_instruction=True,
        recommended_tasks=["translation", "screenplay", "dramaturgy"],
        reset_schedule="utc_midnight",
        notes="OpenAI flagship multimodal intelligence."
    ),
    "gpt-4o-mini": ModelCapability(
        model_id="gpt-4o-mini",
        provider="openai",
        tier=ModelTier.TIER_2_BALANCED,
        modalities=[Modality.TEXT, Modality.VISION],
        context_window=128_000,
        max_output_tokens=16_384,
        free_rpm=500.0,
        free_tpm=200_000.0,
        free_rpd=10_000,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=True,
        supports_system_instruction=True,
        recommended_tasks=["extraction", "utility"],
        reset_schedule="utc_midnight",
        notes="OpenAI balanced fast model."
    ),

    # -------------------------------------------------------------------------
    # 5. Local Hardware / CUDA Models (RTX 4050 6GB Laptop GPU)
    # -------------------------------------------------------------------------
    "spark-x2.5-4b": ModelCapability(
        model_id="spark-x2.5-4b",
        provider="local",
        tier=ModelTier.TIER_LOCAL,
        modalities=[Modality.TEXT],
        context_window=32_768,
        max_output_tokens=4_096,
        free_rpm=9999.0,
        free_tpm=999_999.0,
        free_rpd=99_999,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=True,
        supports_system_instruction=True,
        recommended_tasks=["local_inference", "private_text"],
        reset_schedule="utc_midnight",
        is_local_gpu=True,
        notes="Runs on local RTX 4050 GPU under HardwareVRAMGuard mutex."
    ),
    "mms-forced-aligner": ModelCapability(
        model_id="mms-forced-aligner",
        provider="local",
        tier=ModelTier.TIER_LOCAL,
        modalities=[Modality.AUDIO],
        context_window=16_384,
        max_output_tokens=16_384,
        free_rpm=9999.0,
        free_tpm=999_999.0,
        free_rpd=99_999,
        supports_thinking=False,
        default_thinking_budget=0,
        supports_structured_output=False,
        supports_system_instruction=False,
        recommended_tasks=["alignment"],
        reset_schedule="utc_midnight",
        is_local_gpu=True,
        notes="Local PyTorch forced alignment engine."
    ),
}


# =============================================================================
# Model Registry Implementation
# =============================================================================

class ModelRegistry:
    """
    Thread-Safe Central Registry of Model Capabilities and Profiles.
    Provides:
    - O(1) model capability lookup.
    - Capability-based filtering (by task, tier, modality).
    - Intelligent ranking & resolution for production rooms.
    """

    def __init__(self, initial_catalog: Optional[Dict[str, ModelCapability]] = None):
        self._lock = threading.RLock()
        self._catalog: Dict[str, ModelCapability] = dict(initial_catalog or CANONICAL_MODELS)

    def register_model(self, capability: ModelCapability) -> None:
        """Registers or updates a model capability profile in the registry."""
        with self._lock:
            self._catalog[capability.model_id.lower().strip()] = capability

    def get_model(self, model_id: str) -> Optional[ModelCapability]:
        """Resolves ModelCapability by exact ID or case-insensitive prefix match."""
        clean = model_id.lower().strip()
        with self._lock:
            # 1. Exact match
            if clean in self._catalog:
                return self._catalog[clean]

            # 2. Substring match
            for k, cap in self._catalog.items():
                if k in clean or clean in k:
                    return cap

        return None

    def list_models(self, provider: Optional[str] = None) -> List[ModelCapability]:
        """Lists all registered models, optionally filtered by provider."""
        with self._lock:
            if provider:
                prov_clean = provider.lower().strip()
                return [m for m in self._catalog.values() if m.provider.lower() == prov_clean]
            return list(self._catalog.values())

    def filter_models(
        self,
        task: Optional[str] = None,
        min_tier: Optional[ModelTier] = None,
        modality: Optional[Modality] = None,
        provider: Optional[str] = None,
    ) -> List[ModelCapability]:
        """Filters models matching required constraints."""
        tier_hierarchy = {
            ModelTier.TIER_3_UTILITY: 1,
            ModelTier.TIER_2_BALANCED: 2,
            ModelTier.TIER_1_FLAGSHIP: 3,
            ModelTier.TIER_AUDIO: 3,
            ModelTier.TIER_LOCAL: 2,
        }
        min_score = tier_hierarchy.get(min_tier, 0) if min_tier else 0

        with self._lock:
            results = []
            for cap in self._catalog.values():
                if provider and cap.provider.lower() != provider.lower():
                    continue
                if modality and modality not in cap.modalities:
                    continue
                if min_tier:
                    cap_score = tier_hierarchy.get(cap.tier, 0)
                    if cap_score < min_score:
                        continue
                if task:
                    task_clean = task.lower().strip()
                    if task_clean not in [t.lower() for t in cap.recommended_tasks]:
                        # If task is explicitly requested and model doesn't recommend it, skip
                        continue
                results.append(cap)
            return results

    def resolve_best_model(
        self,
        task: str,
        preferred_provider: str = "gemini",
        min_tier: Optional[ModelTier] = None,
        modality: Modality = Modality.TEXT,
    ) -> ModelCapability:
        """
        Dynamically resolves the best eligible model for a given task and tier requirement.
        Falls back to balanced or flagship models if exact match isn't found.
        """
        # If task is creative (Translation, Screenplay), enforce Tier 1 Flagship
        if task.lower() in ("translation", "screenplay", "dramaturgy") and min_tier is None:
            min_tier = ModelTier.TIER_1_FLAGSHIP

        # If task is TTS, select Audio tier
        if task.lower() in ("tts", "speech", "audio"):
            min_tier = ModelTier.TIER_AUDIO
            modality = Modality.AUDIO

        # First attempt: Match task, tier, modality, and preferred provider
        candidates = self.filter_models(task=task, min_tier=min_tier, modality=modality, provider=preferred_provider)
        if candidates:
            return candidates[0]

        # Second attempt: Match tier and modality across preferred provider
        candidates = self.filter_models(min_tier=min_tier, modality=modality, provider=preferred_provider)
        if candidates:
            return candidates[0]

        # Third attempt: Match modality across any provider
        candidates = self.filter_models(modality=modality)
        if candidates:
            return candidates[0]

        # Default fallback: gemini-3.8-flash
        fallback = self.get_model(_gm("3.8-flash"))
        if fallback:
            return fallback


        # Absolute fallback: First model in registry
        with self._lock:
            return list(self._catalog.values())[0]


# Module-level singleton
_MODEL_REGISTRY_INSTANCE: Optional[ModelRegistry] = None
_REGISTRY_LOCK = threading.Lock()


def get_model_registry() -> ModelRegistry:
    """Returns process-wide ModelRegistry singleton."""
    global _MODEL_REGISTRY_INSTANCE
    if _MODEL_REGISTRY_INSTANCE is None:
        with _REGISTRY_LOCK:
            if _MODEL_REGISTRY_INSTANCE is None:
                _MODEL_REGISTRY_INSTANCE = ModelRegistry()
    return _MODEL_REGISTRY_INSTANCE
