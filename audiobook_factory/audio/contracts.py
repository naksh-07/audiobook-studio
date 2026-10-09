#!/usr/bin/env python3
"""
Audiobook Factory - Audio Mixing & Production Subsystem Contracts (v5.3).
Defines strongly typed, immutable Pydantic v2 schemas for audio ingestion,
segment contracts, chapter masters, and container packaging.
"""

from __future__ import annotations
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class IngestionConfig(BaseModel):
    """Configuration governing Tier A speech ingestion and acoustic normalization."""
    model_config = ConfigDict(extra="ignore")

    target_sample_rate: int = Field(default=48000, ge=16000, le=96000, description="Standard studio sample rate in Hz")
    target_channels: int = Field(default=2, ge=1, le=2, description="Output channel count (1=Mono, 2=Stereo)")
    target_bit_depth: int = Field(default=24, ge=16, le=32, description="PCM bit depth (16 or 24 bit)")
    highpass_hz: int = Field(default=30, ge=20, le=100, description="Subsonic rumble cut frequency in Hz")
    micro_taper_ms: float = Field(default=5.0, ge=1.0, le=25.0, description="Raised-cosine Hann micro-taper window in ms")


class SegmentAudioContract(BaseModel):
    """
    Immutable contract representing an ingested, acoustic-normalized speech segment.
    Emitted by Tier A Ingestion and consumed by Dialogue Editorial and Mastering engines.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    chapter_id: int = Field(..., ge=1, description="1-indexed chapter number")
    segment_index: int = Field(..., ge=1, description="1-indexed sequence order within chapter")
    segment_uid: str = Field(..., description="Deterministic sha256 identifier")

    # Audio Artifact Reference
    audio_path: Path = Field(..., description="Path to clean 48kHz uncompressed PCM WAV")
    audio_sha256: str = Field(..., description="Cryptographic SHA-256 hash of physical audio file")
    sample_rate: int = Field(default=48000, description="Exact sampling frequency in Hz")
    channels: int = Field(default=2, description="Channel count (1=Mono, 2=Stereo)")
    bit_depth: int = Field(default=24, description="PCM bit depth")
    duration_ms: int = Field(..., ge=10, description="Exact sample duration in milliseconds")

    # Dramatic & Editorial Context
    speaker: str = Field(..., description="Character name or 'Narrator'")
    voice_name: str = Field(..., description="Base synthetic voice model (e.g. 'Aoede')")
    segment_type: Literal["narration", "dialogue", "thought", "action"] = Field(
        default="narration", description="Narrative delivery classification"
    )
    intensity_level: Literal["whisper", "low", "medium", "high", "explosive"] = Field(
        default="medium", description="Dramatic intensity classification"
    )
    delivery_style: Optional[str] = Field(default=None, description="Acting style modifier")

    # Text Grounding
    literary_text: str = Field(default="", description="Canonical source text")
    spoken_text: str = Field(default="", description="Phonetically expanded text spoken by TTS")
    word_alignments: Optional[List[Dict[str, Any]]] = Field(default=None, description="Detailed word-level timestamps")

    # Telemetry
    created_at_utc: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(),
        description="ISO 8601 UTC creation timestamp"
    )


class ChapterMasterContract(BaseModel):
    """Metadata describing a certified studio chapter master deliverable."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    chapter_num: int = Field(..., ge=1, description="1-indexed chapter number")
    chapter_title: str = Field(..., description="Chapter title for TOC")
    master_wav_path: Path = Field(..., description="Uncompressed 48kHz 24-bit WAV reference master")
    deliverable_m4a_path: Path = Field(..., description="Broadcast 192k AAC deliverable")
    duration_ms: int = Field(..., ge=100, description="Total chapter duration in milliseconds")

    # EBU R128 Broadcast Metrics
    integrated_lufs: float = Field(..., ge=-25.0, le=-14.0, description="Measured integrated loudness in LUFS")
    true_peak_dbtp: float = Field(..., le=-1.4, description="Maximum True Peak in dBTP")
    loudness_range_lu: float = Field(..., ge=3.0, le=12.0, description="Loudness Range in LU")
    mean_phase_correlation: float = Field(..., ge=0.20, le=1.0, description="Stereo phase correlation coefficient")

    certified: bool = Field(default=False, description="Whether this chapter passed all quality gates")
