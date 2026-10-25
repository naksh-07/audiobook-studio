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


class DSPConfig(BaseModel):
    """Configuration governing C++ JUCE DSP vocal mastering and optional VST3 hosting."""
    model_config = ConfigDict(extra="ignore")

    enable_pedalboard: bool = Field(default=True, description="Attempt C++ Pedalboard DSP before FFmpeg fallback")
    enable_vst3: bool = Field(default=False, description="Enable headless VST3 plugin insertion")
    vst3_plugin_path: Optional[Path] = Field(default=None, description="Path to .vst3 bundle")
    subsonic_hz: float = Field(default=75.0, ge=20.0, le=120.0, description="Subsonic highpass filter cutoff in Hz")
    boxiness_cut_hz: float = Field(default=320.0, ge=150.0, le=600.0, description="Parametric notch frequency for chest resonance in Hz")
    boxiness_cut_db: float = Field(default=-1.5, ge=-6.0, le=0.0, description="Boxiness attenuation gain in dB")
    presence_lift_hz: float = Field(default=3200.0, ge=1500.0, le=6000.0, description="Speech presence clarity center frequency in Hz")
    presence_lift_db: float = Field(default=0.8, ge=0.0, le=4.0, description="Speech presence boost in dB")
    target_lufs: float = Field(default=-19.0, ge=-24.0, le=-14.0, description="EBU R128 integrated loudness target in LUFS")
    true_peak_ceiling_dbtp: float = Field(default=-1.5, ge=-3.0, le=-0.5, description="Lookahead True-Peak ceiling in dBTP")
    compressor_threshold_db: float = Field(default=-18.0, ge=-30.0, le=-6.0, description="Optical compressor threshold in dB")
    compressor_ratio: float = Field(default=2.5, ge=1.2, le=6.0, description="Optical compressor compression ratio")
    compressor_attack_ms: float = Field(default=25.0, ge=5.0, le=100.0, description="Compressor attack time in ms")
    compressor_release_ms: float = Field(default=120.0, ge=20.0, le=500.0, description="Compressor release time in ms")
    # Pro Studio 10/10 Broadcast Mastering Parameters
    enable_acx_framing: bool = Field(default=False, description="Apply 0.75s head and 3.0s tail ACX room tone framing")
    acx_head_silence_sec: float = Field(default=0.75, ge=0.5, le=1.0, description="Lead-in room tone duration in seconds")
    acx_tail_silence_sec: float = Field(default=3.0, ge=1.0, le=5.0, description="Trailing room tone duration in seconds")
    enable_dynamic_deesser: bool = Field(default=True, description="Enable split-band dynamic lookahead de-esser")
    deesser_crossover_hz: float = Field(default=5500.0, ge=4000.0, le=8000.0, description="De-esser crossover frequency in Hz")
    deesser_threshold_db: float = Field(default=-24.0, ge=-36.0, le=-12.0, description="De-esser activation threshold in dBFS")
    deesser_ratio: float = Field(default=3.0, ge=1.5, le=8.0, description="De-esser attenuation ratio")
    deesser_max_att_db: float = Field(default=-7.0, ge=-12.0, le=-2.0, description="Maximum sibilant attenuation in dB")
    enable_two_stage_compression: bool = Field(default=True, description="Enable two-stage Peak Tamer + Opto RMS leveler")
    enable_air_boost: bool = Field(default=True, description="Enable high-shelf silky air restoration")
    air_boost_hz: float = Field(default=10500.0, ge=8000.0, le=16000.0, description="High-shelf air restoration frequency in Hz")
    air_boost_db: float = Field(default=1.8, ge=0.0, le=4.0, description="High-shelf air boost in dB")
    enable_downward_expander: bool = Field(default=True, description="Enable gentle downward noise expander")


class DSPMasteringResult(BaseModel):
    """Execution telemetry emitted by VocalDSPProcessor."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    backend_used: Literal["pedalboard_juce_v2", "ffmpeg_dual_pass_linear", "fallback_linear"] = Field(
        ..., description="Mastering engine backend that rendered the artifact"
    )
    output_path: Path = Field(..., description="Rendered 48kHz 24-bit PCM master WAV")
    integrated_lufs: float = Field(..., description="Measured post-master integrated loudness in LUFS")
    true_peak_dbtp: float = Field(..., description="Measured post-master True Peak in dBTP")
    loudness_range_lu: float = Field(default=7.5, description="Measured Loudness Range in LU")
    execution_duration_sec: float = Field(default=0.0, ge=0.0, description="Processing wall-clock time in seconds")


class AudioQAConfig(BaseModel):
    """Configuration parameters governing acoustic and script quality auditing."""
    model_config = ConfigDict(extra="ignore")

    enable_vad: bool = Field(default=True, description="Enable Voice Activity Detection for boundary checks")
    enable_whisper_alignment: bool = Field(default=False, description="Enable optional Faster-Whisper script alignment")
    whisper_model_size: str = Field(default="base", description="Whisper model tier: tiny, base, small, medium")
    min_wpm: float = Field(default=75.0, description="Minimum acceptable words per minute (below indicates stalled speech)")
    max_wpm: float = Field(default=240.0, description="Maximum acceptable words per minute (above indicates rushed speech)")
    min_pause_ms: int = Field(default=120, description="Minimum natural inter-phrase pause in ms")
    max_pause_ms: int = Field(default=1800, description="Maximum natural pause before dead-air alert in ms")
    duration_tolerance_ratio: float = Field(default=0.40, description="Maximum allowable duration mismatch relative to text length")
    min_mos_threshold: float = Field(default=3.5, description="Minimum Mean Opinion Score before warning")


class SegmentQAEvaluation(BaseModel):
    """Forensic evaluation of an individual synthesized dialogue chunk."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    segment_index: int = Field(..., ge=1, description="1-indexed sequence order")
    segment_uid: str = Field(..., description="Unique segment identifier")
    speaker: str = Field(default="Narrator", description="Character or narrator name")
    status: Literal["PASS", "WARN", "FAIL"] = Field(default="PASS", description="Audit verdict")
    duration_ms: int = Field(..., ge=0, description="Physical audio duration in milliseconds")
    estimated_wpm: float = Field(default=140.0, description="Estimated speaking rate in words per minute")
    char_per_sec: float = Field(default=15.0, description="Character-to-duration speed in characters per second")
    predicted_mos: float = Field(default=4.5, ge=1.0, le=5.0, description="Predicted Speech Quality MOS")
    silence_leading_ms: int = Field(default=0, ge=0, description="Leading dead air in ms")
    silence_trailing_ms: int = Field(default=0, ge=0, description="Trailing dead air in ms")
    issues: List[str] = Field(default_factory=list, description="Detected anomalies or quality notices")
    remediation_advice: Optional[str] = Field(default=None, description="Actionable correction recommendation")


class ChapterQAReport(BaseModel):
    """Consolidated forensic QA audit report for an entire chapter."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    chapter_num: int = Field(..., ge=1, description="Chapter index")
    total_segments: int = Field(default=0, ge=0, description="Total audited speech segments")
    passed_segments: int = Field(default=0, ge=0, description="Count of passed takes")
    warned_segments: int = Field(default=0, ge=0, description="Count of takes with non-blocking warnings")
    failed_segments: int = Field(default=0, ge=0, description="Count of rejected/fatal takes")
    overall_status: Literal["PASS", "WARN", "FAIL"] = Field(default="PASS", description="Overall chapter QA status")
    mean_mos: float = Field(default=4.5, ge=1.0, le=5.0, description="Average predicted speech MOS")
    evaluations: List[SegmentQAEvaluation] = Field(default_factory=list, description="Individual segment evaluations")


class EnhancerConfig(BaseModel):
    """Configuration governing neural speech de-artifacting and enhancement."""
    model_config = ConfigDict(extra="ignore")

    enable_neural_enhancement: bool = Field(default=False, description="Enable DeepFilterNet3 neural vocal cleaning")
    snr_bypass_threshold_db: float = Field(default=45.0, description="SNR threshold above which neural filter is bypassed")
    max_energy_diff_db: float = Field(default=2.0, description="Maximum allowable RMS energy difference before rejection")
    model_type: str = Field(default="deepfilternet3", description="Neural enhancer model architecture")


class ReferenceMatcherConfig(BaseModel):
    """Configuration governing Matchering 2.0 reference spectrum matching."""
    model_config = ConfigDict(extra="ignore")

    enable_reference_matching: bool = Field(default=False, description="Enable reference spectrum matching")
    reference_track_path: Optional[Path] = Field(default=None, description="Path to golden reference WAV master")
    max_spectral_correction_db: float = Field(default=3.0, ge=0.5, le=6.0, description="Hard clamp on spectral EQ adjustment in dB")

