#!/usr/bin/env python3
"""
Deep unit tests for GeminiTTSAdapter.
Tests key pool rotation under simulated 429 errors, BLOCK_NONE safety thresholds,
speechMetadata.style Directing NLP, and raw PCM/WAV response parsing.
"""

import json
import base64
import wave
import io
import urllib.request
import urllib.error
from unittest.mock import patch, MagicMock
import pytest

from audiobook_factory.tts.contracts import CanonicalTTSRequest, DeliveryIntent
from audiobook_factory.tts.providers.gemini_adapter import (
    GeminiTTSAdapter,
    GEMINI_PERMISSIVE_SAFETY,
)


def _generate_mock_wav_bytes(duration_sec: float = 1.0, sample_rate: int = 24000) -> bytes:
    """Generates synthetic WAV audio bytes for mock HTTP responses."""
    num_samples = int(sample_rate * duration_sec)
    samples = [10000 if (i // 50) % 2 == 0 else -10000 for i in range(num_samples)]
    import struct
    pcm = struct.pack(f"<{num_samples}h", *samples)

    with io.BytesIO() as wav_io:
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm)
        return wav_io.getvalue()


def test_gemini_permissive_safety_invariants():
    """Verifies that BLOCK_NONE is enforced on all harm categories (Zero Moral Policing)."""
    assert len(GEMINI_PERMISSIVE_SAFETY) == 5
    for s in GEMINI_PERMISSIVE_SAFETY:
        assert s["threshold"] == "BLOCK_NONE"


def test_build_style_descriptor_directing_nlp():
    """Verifies that DeliveryIntent is accurately translated into natural directing prompts."""
    # 1. Narrator delivery
    narrator_style = GeminiTTSAdapter.build_style_descriptor(DeliveryIntent(), speaker="Narrator")
    assert narrator_style == "calm, steady, articulate, measured audiobook delivery"

    # 2. Dramatic character delivery
    intent = DeliveryIntent(
        emotion="anger",
        delivery_style="harsh_tense",
        intensity="explosive",
        proximity="intimate",
        memory_vocal_constraint="hoarse voice",
        extracted_stage_cues=["heavy breathing"],
    )
    style = GeminiTTSAdapter.build_style_descriptor(intent, speaker="Geralt")
    assert "harsh tense" in style
    assert "anger" in style
    assert "extreme intensity" in style
    assert "intimate whisper proximity" in style
    assert "hoarse voice" in style
    assert "heavy breathing" in style
    assert "authentic dramatic delivery with genuine emotional conviction" in style

    # 3. Conversational character delivery
    conversational_intent = DeliveryIntent(
        emotion="neutral",
        delivery_style="grounded_dialogue",
        intensity="medium",
    )
    conv_style = GeminiTTSAdapter.build_style_descriptor(conversational_intent, speaker="Innkeeper")
    assert "understated natural dialogue (never theatrical)" in conv_style


@patch("urllib.request.urlopen")
def test_gemini_synthesis_success(mock_urlopen):
    """Tests full synthesis flow with WAV candidate parsing."""
    wav_bytes = _generate_mock_wav_bytes(duration_sec=0.8)
    b64_audio = base64.b64encode(wav_bytes).decode("utf-8")

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "candidates": [{
            "content": {
                "parts": [{
                    "inlineData": {
                        "mimeType": "audio/wav",
                        "data": b64_audio,
                    }
                }]
            }
        }]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    adapter = GeminiTTSAdapter(model_name="gemini-3.8-flash-tts")
    req = CanonicalTTSRequest(
        segment_uid="seg_gem_01",
        literary_text="यह एक परीक्षण है।",
        spoken_text="यह एक परीक्षण है।",
        voice_id="Puck",
        speaker="Vikram",
        delivery_intent=DeliveryIntent(emotion="whisper"),
    )

    chunk = adapter.synthesize_chunk(req)
    assert chunk.segment_uid == "seg_gem_01"
    assert chunk.provider_model == "gemini-3.8-flash-tts"
    assert chunk.duration_sec == pytest.approx(0.8, rel=1e-2)
    assert len(chunk.pcm_bytes) > 0


@patch("urllib.request.urlopen")
def test_gemini_synthesis_retry_on_http_429(mock_urlopen):
    """Tests automatic retry and key rotation when encountering an HTTP 429."""
    wav_bytes = _generate_mock_wav_bytes(duration_sec=0.5)
    b64_audio = base64.b64encode(wav_bytes).decode("utf-8")

    # First call: 429 error, Second call: Success
    error_response = urllib.error.HTTPError(
        url="https://generativelanguage.googleapis.com",
        code=429,
        msg="Too Many Requests",
        hdrs=None, # type: ignore
        fp=io.BytesIO(b'{"error": {"message": "Resource exhausted"}}'),
    )

    success_response = MagicMock()
    success_response.read.return_value = json.dumps({
        "candidates": [{
            "content": {
                "parts": [{
                    "inlineData": {
                        "mimeType": "audio/wav",
                        "data": b64_audio,
                    }
                }]
            }
        }]
    }).encode("utf-8")

    mock_urlopen.side_effect = [error_response, MagicMock(__enter__=MagicMock(return_value=success_response))]

    adapter = GeminiTTSAdapter(model_name="gemini-3.8-flash-tts", config={"max_retries": 2})
    req = CanonicalTTSRequest(
        segment_uid="seg_retry_01",
        literary_text="पुनः प्रयास।",
        spoken_text="पुनः प्रयास।",
        voice_id="Puck",
    )

    chunk = adapter.synthesize_chunk(req)
    assert chunk.segment_uid == "seg_retry_01"
    assert chunk.metadata["attempt"] == 2
