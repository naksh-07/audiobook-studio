#!/usr/bin/env python3
"""
Audiobook Factory - TTS Platform Core Contracts (Pydantic v2).
Defines strongly-typed, immutable schemas across all client facades,
shared orchestration core, pluggable model adapters, and audio validation.
"""

from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from pydantic import BaseModel, Field, ConfigDict


class TTSPipelineMode(str, Enum):
    """Execution mode for TTS generation."""
    GENERIC = "generic"          # Single-line, ad-hoc, or notification synthesis
    LONG_FORM = "long_form"      # Multi-page / full chapter prose streams
    MULTI_CAST = "multi_cast"    # Ensemble multi-character screenplay audio drama


class DeliveryIntent(BaseModel):
    """
    Strongly-typed emotional, dramatic, and vocal delivery directives.
    Parsed from screenplay acting instructions or neural stage direction tags.
    """
    model_config = ConfigDict(frozen=True)

    emotion: str = "neutral"
    delivery_style: str = "standard"
    intensity: str = "medium"               # low, medium, high, explosive
    proximity: str = "normal"               # intimate, close_mic, normal, distant
    pacing_multiplier: float = 1.0          # 0.75 to 1.35
    memory_vocal_constraint: Optional[str] = None
    extracted_stage_cues: List[str] = Field(default_factory=list)
    raw_style_descriptor: Optional[str] = None


class CanonicalTTSRequest(BaseModel):
    """
    Standardized request payload passed to the TTS Orchestrator and Model Adapters.
    Enforces Sacred Text vs. Spoken Text immutability invariant.
    """
    model_config = ConfigDict(frozen=True)

    segment_uid: str
    literary_text: str                       # Immutable sacred author text for display/subtitles
    spoken_text: str                         # Sanitized, expanded phonetic text for TTS voice model
    voice_id: str
    language: str = "hi-IN"
    speaker: str = "Narrator"
    delivery_intent: DeliveryIntent = Field(default_factory=DeliveryIntent)
    temperature: float = 0.40
    sample_rate: int = 24000
    pipeline_mode: TTSPipelineMode = TTSPipelineMode.GENERIC
    chapter_num: Optional[int] = None
    scene_num: Optional[int] = None
    suggested_pause_before_ms: int = 0
    suggested_pause_after_ms: int = 400
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SynthesizedAudioChunk(BaseModel):
    """
    Standardized raw audio container returned by any TTS Model Adapter.
    """
    model_config = ConfigDict(frozen=True)

    segment_uid: str
    pcm_bytes: bytes
    sample_rate: int = 24000
    num_channels: int = 1
    duration_sec: float
    provider_model: str
    voice_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AudioValidationResult(BaseModel):
    """
    Comprehensive result from the Two-Tier Audio Quality Gate.
    """
    model_config = ConfigDict(frozen=True)

    segment_uid: str
    passed: bool
    status: str = "PASS"                     # PASS, WARN, FAILED, REGENERATE
    tier1_acoustic_passed: bool
    tier2_phonetic_passed: bool
    peak_amplitude: int
    rms_dbfs: float
    dc_bias: float
    consecutive_clipped_samples: int
    dead_air_sec: float
    duration_ratio: float                    # duration_sec / word_count
    wer_score: Optional[float] = None        # Word Error Rate from MMS/ASR probe
    omitted_tokens: List[str] = Field(default_factory=list)
    hallucinated_tokens: List[str] = Field(default_factory=list)
    diagnostics: List[str] = Field(default_factory=list)


class ChapterMasterResult(BaseModel):
    """
    Master deliverable output for a synthesized chapter or dialogue stem.

    Pipeline Boundary Invariant:
    - In Room 4 (TTS Platform Core), this output represents the edited dialogue stem
      (stitched with Net-Silence DSP, contextual turn latency, and Hann micro-fades).
    - Broadcast two-pass linear EBU R128 (-19.0 LUFS, -1.5 dBTP) mastering and chaptered
      M4B container packaging are executed downstream by Room 5 (audio_master.py).
    """
    model_config = ConfigDict(frozen=True)

    chapter_num: int
    master_audio_path: Path
    duration_sec: float
    total_segments: int
    integrated_lufs: float = -19.0           # EBU R128 target (-19.0 LUFS)
    true_peak_db: float = -1.5               # Hard ceiling target (-1.5 dBTP)
    loudness_range: float = 4.5
    qc_passed: bool = True
    stage: str = "dialogue_stem"             # 'dialogue_stem' (Room 4) or 'broadcast_master' (Room 5)
    metadata: Dict[str, Any] = Field(default_factory=dict)
