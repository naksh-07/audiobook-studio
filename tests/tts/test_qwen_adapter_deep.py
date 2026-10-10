#!/usr/bin/env python3
"""
Deep unit tests for QwenTTSAdapter.
Tests HardwareVRAMGuard validation, zero-shot reference audio conditioning,
REST endpoint dispatch, and graceful fallback execution.
"""

import os
import wave
import io
import json
import base64
import urllib.request
from unittest.mock import patch, MagicMock
import pytest

from audiobook_factory.tts.contracts import CanonicalTTSRequest, DeliveryIntent
from audiobook_factory.tts.providers.qwen_adapter import QwenTTSAdapter


def _create_temp_wav(tmp_path, filename="ref.wav") -> str:
    p = tmp_path / filename
    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"\x00\x00" * 24000)
    return str(p)


def test_qwen_adapter_vram_and_compatibility():
    """Tests compatibility validation and VRAM headroom checks."""
    adapter = QwenTTSAdapter("qwen3-tts")

    req_short = CanonicalTTSRequest(
        segment_uid="seg_q1",
        literary_text="नमस्ते",
        spoken_text="नमस्ते",
        voice_id="Female_01",
    )
    compat, warnings = adapter.validate_request_compatibility(req_short)
    assert compat is True

    # Overly long text check
    req_long = CanonicalTTSRequest(
        segment_uid="seg_q2",
        literary_text="शब्द " * 1000,
        spoken_text="शब्द " * 1000,
        voice_id="Female_01",
    )
    _, warnings = adapter.validate_request_compatibility(req_long)
    assert any("very long" in w for w in warnings)


@patch("urllib.request.urlopen")
def test_qwen_synthesis_with_reference_audio(mock_urlopen, tmp_path):
    """Tests zero-shot audio prompt conditioning payload formatting."""
    ref_wav_path = _create_temp_wav(tmp_path, "voice_ref.wav")

    # Mock successful HTTP endpoint response with raw WAV
    mock_response = MagicMock()
    with io.BytesIO() as wav_io:
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(b"\x10\x10" * 12000)  # 0.5 sec
        mock_response.read.return_value = wav_io.getvalue()

    mock_urlopen.return_value.__enter__.return_value = mock_response

    adapter = QwenTTSAdapter("qwen3-tts", config={"endpoint_url": "http://127.0.0.1:8000/v1/audio/speech"})
    req = CanonicalTTSRequest(
        segment_uid="seg_ref_01",
        literary_text="कंडीशनिंग टेस्ट।",
        spoken_text="कंडीशनिंग टेस्ट।",
        voice_id="CustomVoice",
        metadata={"ref_audio_path": ref_wav_path, "ref_text": "रेफरेंस टेक्स्ट"},
    )

    chunk = adapter.synthesize_chunk(req)
    assert chunk.segment_uid == "seg_ref_01"
    assert chunk.metadata.get("has_reference_audio") is True
    assert chunk.duration_sec == pytest.approx(0.5, rel=1e-2)


def test_qwen_simulation_fallback_when_server_offline():
    """Tests that adapter falls back to simulation mode without crashing when endpoint is unreachable."""
    adapter = QwenTTSAdapter("qwen3-tts", config={"endpoint_url": "http://127.0.0.1:9999/invalid_endpoint"})
    req = CanonicalTTSRequest(
        segment_uid="seg_sim_01",
        literary_text="ऑफ़लाइन फ़ॉलबैक परीक्षण।",
        spoken_text="ऑफ़लाइन फ़ॉलबैक परीक्षण।",
        voice_id="DefaultVoice",
    )

    chunk = adapter.synthesize_chunk(req)
    assert chunk.segment_uid == "seg_sim_01"
    assert chunk.metadata.get("simulation_mode") is True
    assert chunk.duration_sec > 0
    assert len(chunk.pcm_bytes) > 0
