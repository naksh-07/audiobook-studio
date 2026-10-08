#!/usr/bin/env python3
"""
Deep Unit Tests for GenericTTSClient Facade.
Tests single-utterance speech synthesis, memory-only WAV bytes, delivery overrides,
pre-built canonical requests, and validation pipeline.
"""

import io
import wave
import struct
from pathlib import Path
import pytest

from audiobook_factory.tts.contracts import (
    CanonicalTTSRequest,
    SynthesizedAudioChunk,
    DeliveryIntent,
    TTSPipelineMode,
)
from audiobook_factory.tts.core_orchestrator import TTSCoreOrchestrator
from audiobook_factory.tts.providers.base import BaseTTSModelAdapter
from audiobook_factory.tts.providers.registry import ModelAdapterRegistry
from audiobook_factory.tts.facades.generic_client import GenericTTSClient


class MockToneAdapter(BaseTTSModelAdapter):
    """Generates synthetic tone audio for mock synthesis."""

    def synthesize_chunk(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk:
        words = max(1, len(request.spoken_text.split()))
        dur = max(0.4, min(words * 0.25, 4.0))
        num_samples = int(request.sample_rate * dur)
        # 16-bit PCM tone
        samples = [14000 if (i // 40) % 2 == 0 else -14000 for i in range(num_samples)]
        pcm = struct.pack(f"<{num_samples}h", *samples)

        return SynthesizedAudioChunk(
            segment_uid=request.segment_uid,
            pcm_bytes=pcm,
            sample_rate=request.sample_rate,
            num_channels=1,
            duration_sec=dur,
            provider_model=self.model_name,
            voice_id=request.voice_id,
        )

    async def synthesize_chunk_async(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk:
        return self.synthesize_chunk(request)

    def validate_request_compatibility(self, request: CanonicalTTSRequest):
        return True, []

    def get_model_metadata(self):
        return {"model_name": self.model_name}


@pytest.fixture
def mock_orchestrator():
    reg = ModelAdapterRegistry()
    adapter = MockToneAdapter("test-mock-model")
    reg.register("test-mock-model", adapter)
    return TTSCoreOrchestrator(registry=reg, max_workers=2)


def test_generic_client_speak_text(tmp_path, mock_orchestrator):
    client = GenericTTSClient(orchestrator=mock_orchestrator)
    out_file = tmp_path / "sample_utterance.wav"

    saved_path, chunk, val = client.speak(
        text_or_request="नमस्ते, यह जेनेरिक क्लाइंट का टेस्ट है।",
        voice="Puck",
        model="test-mock-model",
        output_path=out_file,
    )

    assert saved_path == out_file
    assert out_file.exists()
    assert chunk.duration_sec > 0.3
    assert val is not None
    assert val.passed is True

    # Validate generated WAV header
    with wave.open(str(out_file), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 24000
        assert wf.getnframes() > 0


def test_generic_client_speak_to_bytes(mock_orchestrator):
    client = GenericTTSClient(orchestrator=mock_orchestrator)

    wav_bytes = client.speak_to_bytes(
        text_or_request="यह इन-मेमोरी ऑडियो स्ट्रीम है।",
        voice="Aoede",
        model="test-mock-model",
    )

    assert isinstance(wav_bytes, bytes)
    assert len(wav_bytes) > 44
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"

    # Read from in-memory stream
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 24000
        assert wf.getnframes() > 0


def test_generic_client_custom_delivery_intent(tmp_path, mock_orchestrator):
    client = GenericTTSClient(orchestrator=mock_orchestrator)
    out_file = tmp_path / "whisper_test.wav"

    intent = DeliveryIntent(
        emotion="whispering",
        delivery_style="restraint",
        intensity="low",
        speaking_rate=0.9,
    )

    saved_path, chunk, val = client.speak(
        text_or_request="धीरे से बोलो, कोई सुन लेगा।",
        voice="Charon",
        model="test-mock-model",
        output_path=out_file,
        delivery_intent=intent,
    )

    assert saved_path is not None
    assert saved_path.exists()
    assert chunk.voice_id == "Charon"


def test_generic_client_prebuilt_canonical_request(tmp_path, mock_orchestrator):
    client = GenericTTSClient(orchestrator=mock_orchestrator)
    out_file = tmp_path / "prebuilt_req.wav"

    req = CanonicalTTSRequest(
        literary_text="She walked in silence.",
        spoken_text="वह खामोशी से अंदर चली गई।",
        voice_id="Kore",
        segment_uid="seg_custom_001",
        speaker="Narrator",
        sample_rate=24000,
        pipeline_mode=TTSPipelineMode.GENERIC,
    )

    saved_path, chunk, val = client.speak(
        text_or_request=req,
        model="test-mock-model",
        output_path=out_file,
    )

    assert saved_path.exists()
    assert chunk.segment_uid == "seg_custom_001"
    assert chunk.voice_id == "Kore"
