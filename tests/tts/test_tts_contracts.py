#!/usr/bin/env python3
"""
Unit tests for TTS Platform Core Contracts.
Verifies Pydantic v2 immutability, default factories, and serialization.
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

from audiobook_factory.tts.contracts import (
    TTSPipelineMode,
    DeliveryIntent,
    CanonicalTTSRequest,
    SynthesizedAudioChunk,
    AudioValidationResult,
    ChapterMasterResult,
)


def test_delivery_intent_defaults_and_immutability():
    intent = DeliveryIntent()
    assert intent.emotion == "neutral"
    assert intent.delivery_style == "standard"
    assert intent.intensity == "medium"
    assert intent.proximity == "normal"
    assert intent.pacing_multiplier == 1.0
    assert intent.extracted_stage_cues == []

    # Verify frozen immutability
    with pytest.raises(ValidationError):
        intent.emotion = "angry"  # type: ignore


def test_canonical_tts_request_immutability():
    req = CanonicalTTSRequest(
        segment_uid="seg_001",
        literary_text="नमस्ते दुनिया!",
        spoken_text="नमस्ते दुनिया!",
        voice_id="Puck",
        language="hi-IN",
        speaker="Narrator",
    )
    assert req.segment_uid == "seg_001"
    assert req.pipeline_mode == TTSPipelineMode.GENERIC
    assert req.temperature == 0.40
    assert req.sample_rate == 24000

    # Immutability check
    with pytest.raises(ValidationError):
        req.spoken_text = "Modified"  # type: ignore


def test_synthesized_audio_chunk_schema():
    chunk = SynthesizedAudioChunk(
        segment_uid="seg_002",
        pcm_bytes=b"\x00\x00\x10\x00",
        sample_rate=24000,
        num_channels=1,
        duration_sec=0.5,
        provider_model="gemini-3.8-flash",
        voice_id="Puck",
    )
    assert chunk.duration_sec == 0.5
    assert chunk.num_channels == 1
    assert chunk.provider_model == "gemini-3.8-flash"


def test_audio_validation_result_schema():
    val = AudioValidationResult(
        segment_uid="seg_003",
        passed=True,
        status="PASS",
        tier1_acoustic_passed=True,
        tier2_phonetic_passed=True,
        peak_amplitude=16000,
        rms_dbfs=-20.5,
        dc_bias=0.001,
        consecutive_clipped_samples=0,
        dead_air_sec=0.02,
        duration_ratio=0.35,
    )
    assert val.passed is True
    assert val.status == "PASS"
    assert val.omitted_tokens == []


def test_chapter_master_result_schema():
    res = ChapterMasterResult(
        chapter_num=1,
        master_audio_path=Path("/tmp/chapter_01.m4b"),
        duration_sec=120.5,
        total_segments=15,
        integrated_lufs=-19.0,
        true_peak_db=-1.5,
        loudness_range=4.2,
        qc_passed=True,
    )
    assert res.chapter_num == 1
    assert res.integrated_lufs == -19.0
    assert res.qc_passed is True
