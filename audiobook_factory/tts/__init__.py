#!/usr/bin/env python3
"""
Audiobook Factory - Modular TTS Platform Core.
Provides strongly-typed contracts, universal input guards, model adapters,
quality gates, chunkers, editorial DSP, orchestrators, and specialized client facades,
while maintaining 100% backward compatibility for existing pipelines.
"""

# New Modular TTS Platform Core Symbols
from audiobook_factory.tts.contracts import (
    TTSPipelineMode,
    DeliveryIntent,
    CanonicalTTSRequest,
    SynthesizedAudioChunk,
    AudioValidationResult,
    ChapterMasterResult,
)
from audiobook_factory.tts.guard import (
    UniversalInputGuard,
    NumeralAndTokenExpander,
    DeliveryIntentExtractor,
    number_to_hindi_words,
)
from audiobook_factory.tts.providers import (
    BaseTTSModelAdapter,
    GeminiTTSAdapter,
    QwenTTSAdapter,
    ModelAdapterRegistry,
    get_adapter_registry,
    adapter_registry,
)
from audiobook_factory.tts.chunker import (
    SemanticProseChunker,
    SemanticChunk,
    ChunkHierarchyLevel,
)
from audiobook_factory.tts.dsp import (
    EditorialDSPEngine,
    HannFadeProcessor,
    NetSilenceProcessor,
    ZeroCrossingAligner,
)
from audiobook_factory.tts.quality_gate import TwoTierAudioQualityGate
from audiobook_factory.tts.core_orchestrator import TTSCoreOrchestrator
from audiobook_factory.tts.facades import (
    GenericTTSClient,
    LongFormTTSClient,
    MultiCastStudioClient,
)
from audiobook_factory.tts.formant_sculptor import FormantSculptor, FormantProfile
from audiobook_factory.tts.take_bank_manager import TakeBankManager, CandidateTake

# Constants & Helpers
from audiobook_factory.tts.constants import (
    DEFAULT_BACKEND,
    DEFAULT_VOICE,
    DEFAULT_MODEL,
    DEFAULT_BATCHING_ENABLED,
    DEFAULT_FORCED_ALIGNMENT_ENABLED,
    DEFAULT_DECLICK_FADE_MS,
    ENABLE_EMERGENCY_FALLBACK,
    DEFAULT_WORKERS,
    DEFAULT_RPM,
    NUMERAL_NORMALIZATION,
    get_ffmpeg,
    get_ffprobe,
    get_gemini_api_key,
    UnregisteredSpeakerError,
)
from audiobook_factory.tts.rate_limiter import TokenBucketRateLimiter
from audiobook_factory.tts.audio_slicer import (
    compute_canonical_segment_filename,
    slice_and_declick_batch,
)
from audiobook_factory.tts.providers.gemini import (
    synthesize_gemini_tts,
    synthesize_gemini_multispeaker_batch,
    resolve_speech_metadata_style,
    _synthesize_local_winrt_fallback,
    _synthesize_local_batch_winrt,
)
from audiobook_factory.key_manager import (
    get_persistent_key_pool,
)
from audiobook_factory.tts.dispatcher import (
    TTSDispatcher,
    synthesize_segment_audio,
)

global_key_pool = get_persistent_key_pool()

__all__ = [
    # New Modular Platform Core
    "TTSPipelineMode",
    "DeliveryIntent",
    "CanonicalTTSRequest",
    "SynthesizedAudioChunk",
    "AudioValidationResult",
    "ChapterMasterResult",
    "UniversalInputGuard",
    "NumeralAndTokenExpander",
    "DeliveryIntentExtractor",
    "number_to_hindi_words",
    "BaseTTSModelAdapter",
    "GeminiTTSAdapter",
    "QwenTTSAdapter",
    "ModelAdapterRegistry",
    "get_adapter_registry",
    "adapter_registry",
    "SemanticProseChunker",
    "SemanticChunk",
    "ChunkHierarchyLevel",
    "EditorialDSPEngine",
    "HannFadeProcessor",
    "NetSilenceProcessor",
    "ZeroCrossingAligner",
    "TwoTierAudioQualityGate",
    "TTSCoreOrchestrator",
    "GenericTTSClient",
    "LongFormTTSClient",
    "MultiCastStudioClient",
    "FormantSculptor",
    "FormantProfile",
    "TakeBankManager",
    "CandidateTake",
    # Legacy / Dispatcher Invariants
    "DEFAULT_BACKEND",
    "DEFAULT_VOICE",
    "DEFAULT_MODEL",
    "DEFAULT_BATCHING_ENABLED",
    "DEFAULT_FORCED_ALIGNMENT_ENABLED",
    "DEFAULT_DECLICK_FADE_MS",
    "ENABLE_EMERGENCY_FALLBACK",
    "DEFAULT_WORKERS",
    "DEFAULT_RPM",
    "NUMERAL_NORMALIZATION",
    "get_ffmpeg",
    "get_ffprobe",
    "get_gemini_api_key",
    "global_key_pool",
    "UnregisteredSpeakerError",
    "TokenBucketRateLimiter",
    "_synthesize_local_winrt_fallback",
    "_synthesize_local_batch_winrt",
    "resolve_speech_metadata_style",
    "synthesize_gemini_tts",
    "synthesize_gemini_multispeaker_batch",
    "compute_canonical_segment_filename",
    "slice_and_declick_batch",
    "TTSDispatcher",
    "synthesize_segment_audio",
]
