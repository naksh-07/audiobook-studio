#!/usr/bin/env python3
"""
Audiobook Factory - Casting Subsystem & Voice Allocation Engine.
Provides character casting profiles, candidate discovery, voice auditions,
multi-dimensional evaluation, and immutable cast locking.
"""

from .contracts import (
    CharacterCastingProfile,
    VoiceCandidateScore,
    AuditionScene,
    AuditionResult,
    CastingEvaluationRecord,
    CastLock,
    CastLockManifest,
    CanonicalVoiceProfile,
    CharacterCastAssignment,
    SpectralFormantProfile,
    SceneContrastMatrix,
    ProviderCapabilities,
)
from .candidate_engine import VoiceCandidateEngine
from .audition_engine import VoiceAuditionEngine
from .casting_evaluator import CastingEvaluator
from .cast_lock import CastLockManager
from .registry import VoiceProfileRegistry
from .director import StudioCastingDirector
from .calibrator import SceneAcousticCalibrator
from .adapters import BaseVoiceAdapter, GeminiVoiceAdapter, QwenVoiceAdapter
from audiobook_factory.gates.gate28_distinction import AuditoryDistinctionGate, AuditoryDistinctionVerdict

__all__ = [
    "CharacterCastingProfile",
    "VoiceCandidateScore",
    "AuditionScene",
    "AuditionResult",
    "CastingEvaluationRecord",
    "CastLock",
    "CastLockManifest",
    "CanonicalVoiceProfile",
    "CharacterCastAssignment",
    "SpectralFormantProfile",
    "SceneContrastMatrix",
    "ProviderCapabilities",
    "VoiceCandidateEngine",
    "VoiceAuditionEngine",
    "CastingEvaluator",
    "CastLockManager",
    "VoiceProfileRegistry",
    "StudioCastingDirector",
    "SceneAcousticCalibrator",
    "BaseVoiceAdapter",
    "GeminiVoiceAdapter",
    "QwenVoiceAdapter",
    "AuditoryDistinctionGate",
    "AuditoryDistinctionVerdict",
]

