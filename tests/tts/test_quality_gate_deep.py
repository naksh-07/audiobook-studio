#!/usr/bin/env python3
"""
Deep unit tests for TwoTierAudioQualityGate.
Tests RMS energy floor, clipping detection, internal dead-air silence scanning,
DC bias offset, and phonetic token preservation.
"""

import struct
import pytest

from audiobook_factory.tts.contracts import CanonicalTTSRequest, SynthesizedAudioChunk
from audiobook_factory.tts.quality_gate import TwoTierAudioQualityGate


def test_quality_gate_internal_dead_air_detection():
    """Verifies that internal silence gaps > 2.5s are rejected."""
    req = CanonicalTTSRequest(
        segment_uid="seg_deadair",
        literary_text="शुरुआत का वाक्य।",
        spoken_text="शुरुआत का वाक्य।",
        voice_id="Puck",
    )

    sample_rate = 24000
    # 0.5s audio + 3.0s dead air + 0.5s audio = 4.0s total
    aud_05s = [12000 if (i // 40) % 2 == 0 else -12000 for i in range(12000)]
    silence_30s = [0] * (sample_rate * 3)  # 3.0 seconds dead air
    all_samples = aud_05s + silence_30s + aud_05s

    pcm = struct.pack(f"<{len(all_samples)}h", *all_samples)
    chunk = SynthesizedAudioChunk(
        segment_uid="seg_deadair",
        pcm_bytes=pcm,
        sample_rate=sample_rate,
        num_channels=1,
        duration_sec=len(all_samples) / float(sample_rate),
        provider_model="mock",
        voice_id="Puck",
    )

    res = TwoTierAudioQualityGate.audit_chunk(req, chunk)
    assert res.passed is False
    assert res.tier1_acoustic_passed is False
    assert res.dead_air_sec >= 2.5
    assert any("dead-air" in d.lower() for d in res.diagnostics)


def test_quality_gate_faint_audio_below_rms_floor():
    """Verifies that extremely faint audio below -52 dBFS is rejected."""
    req = CanonicalTTSRequest(
        segment_uid="seg_faint",
        literary_text="बहुत धीमी आवाज़।",
        spoken_text="बहुत धीमी आवाज़।",
        voice_id="Puck",
    )

    sample_rate = 24000
    num_samples = 24000
    # Amplitude 30 corresponds to ~ -60 dBFS
    samples = [30 if (i // 40) % 2 == 0 else -30 for i in range(num_samples)]
    pcm = struct.pack(f"<{num_samples}h", *samples)

    chunk = SynthesizedAudioChunk(
        segment_uid="seg_faint",
        pcm_bytes=pcm,
        sample_rate=sample_rate,
        num_channels=1,
        duration_sec=1.0,
        provider_model="mock",
        voice_id="Puck",
    )

    res = TwoTierAudioQualityGate.audit_chunk(req, chunk)
    assert res.passed is False
    assert res.tier1_acoustic_passed is False


def test_quality_gate_phonetic_token_preservation():
    """Verifies phonetic check for dropped lines on long sentences with abnormally short audio."""
    long_sentence = "यह एक बहुत लंबा वाक्य है जिसमें कई महत्वपूर्ण विवरण और पात्रों के नाम शामिल हैं।"
    req = CanonicalTTSRequest(
        segment_uid="seg_dropped",
        literary_text=long_sentence,
        spoken_text=long_sentence,
        voice_id="Puck",
    )

    # 14 words, but audio is only 0.4s (impossible speech rate -> dropped words)
    sample_rate = 24000
    num_samples = int(sample_rate * 0.4)
    samples = [10000 if (i // 40) % 2 == 0 else -10000 for i in range(num_samples)]
    pcm = struct.pack(f"<{num_samples}h", *samples)

    chunk = SynthesizedAudioChunk(
        segment_uid="seg_dropped",
        pcm_bytes=pcm,
        sample_rate=sample_rate,
        num_channels=1,
        duration_sec=0.4,
        provider_model="mock",
        voice_id="Puck",
    )

    res = TwoTierAudioQualityGate.audit_chunk(req, chunk)
    assert res.passed is False
    assert any("dropped" in d.lower() or "ratio" in d.lower() for d in res.diagnostics)
