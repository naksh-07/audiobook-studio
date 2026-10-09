#!/usr/bin/env python3
"""
Audiobook Factory - Pillar 3.2: Concurrent TTS Package.
Exports TTSDispatcher, rate limiting, audio slicing, and provider synthesis backends.
"""

from __future__ import annotations

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
    global_key_pool,
    UnregisteredSpeakerError,
)
from audiobook_factory.tts.rate_limiter import TokenBucketRateLimiter
try:
    from audiobook_factory.tts.providers.winrt import (
        _synthesize_local_winrt_fallback,
        _synthesize_local_batch_winrt,
    )
except (ImportError, ModuleNotFoundError):
    _synthesize_local_winrt_fallback = None
    _synthesize_local_batch_winrt = None
try:
    from audiobook_factory.tts.providers.gemini import (
        resolve_speech_metadata_style,
        synthesize_gemini_tts,
        synthesize_gemini_multispeaker_batch,
    )
    from audiobook_factory.tts.audio_slicer import (
        compute_canonical_segment_filename,
        slice_and_declick_batch,
    )
    from audiobook_factory.tts.dispatcher import (
        TTSDispatcher,
        synthesize_segment_audio,
    )
except (ImportError, ModuleNotFoundError):
    resolve_speech_metadata_style = None
    synthesize_gemini_tts = None
    synthesize_gemini_multispeaker_batch = None
    compute_canonical_segment_filename = None
    slice_and_declick_batch = None
    TTSDispatcher = None
    synthesize_segment_audio = None

__all__ = [
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
