#!/usr/bin/env python3
"""
Unit tests for Specialized TTS Client Facades.
Tests GenericTTSClient, LongFormTTSClient (prose chunking & stitching),
and MultiCastStudioClient (screenplay casting & mastering).
"""

import wave
from pathlib import Path
import pytest

from audiobook_factory.tts.contracts import (
    CanonicalTTSRequest,
    SynthesizedAudioChunk,
    TTSPipelineMode,
)
from audiobook_factory.tts.core_orchestrator import TTSCoreOrchestrator
from audiobook_factory.tts.providers.base import BaseTTSModelAdapter
from audiobook_factory.tts.providers.registry import ModelAdapterRegistry
from audiobook_factory.tts.facades.generic_client import GenericTTSClient
from audiobook_factory.tts.facades.long_form_client import LongFormTTSClient
from audiobook_factory.tts.facades.multi_cast_client import MultiCastStudioClient


class MockToneAdapter(BaseTTSModelAdapter):
    """Generates synthetic tone audio for mock synthesis."""

    def synthesize_chunk(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk:
        words = max(1, len(request.spoken_text.split()))
        dur = max(0.4, min(words * 0.25, 4.0))
        num_samples = int(request.sample_rate * dur)
        # 16-bit PCM tone
        samples = [14000 if (i // 40) % 2 == 0 else -14000 for i in range(num_samples)]
        import struct
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
def test_orchestrator():
    reg = ModelAdapterRegistry()
    adapter = MockToneAdapter("test-mock-model")
    reg.register("test-mock-model", adapter)
    return TTSCoreOrchestrator(registry=reg, max_workers=4)


def test_generic_client(tmp_path, test_orchestrator):
    client = GenericTTSClient(orchestrator=test_orchestrator)
    out_file = tmp_path / "test_generic.wav"

    saved_path, chunk, validation = client.speak(
        text_or_request="नमस्ते दुनिया, यह पहला परीक्षण है।",
        voice="Puck",
        model="test-mock-model",
        output_path=out_file,
    )

    assert saved_path is not None
    assert saved_path.exists()
    assert chunk.duration_sec > 0
    assert validation.passed is True

    # Verify WAV file header
    with wave.open(str(saved_path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 24000
        assert wf.getnframes() > 0


def test_long_form_client_segmentation_and_synthesis(tmp_path, test_orchestrator):
    client = LongFormTTSClient(orchestrator=test_orchestrator)

    # Multi-paragraph prose
    long_prose = (
        "रात का सन्नाटा गहरा रहा था। दूर कहीं एक सायरन की आवाज़ गूँज उठी। "
        "विक्रम ने खिड़की से बाहर देखा और गहरी साँस ली।\n\n"
        "शहर सो रहा था लेकिन उसके दिमाग में विचारों का तूफ़ान चल रहा था। "
        "क्या वह कल सुबह उस रहस्य को सुलझा पाएगा? समय बहुत कम बचा था।"
    )

    # 1. Test prose segmentation
    chunks = client.segment_prose(long_prose, target_words=15)
    assert len(chunks) >= 2
    assert all(len(c.strip()) > 0 for c in chunks)

    # 2. Test continuous synthesis
    out_master = tmp_path / "long_form_master.wav"
    master_path, dur, synthesized_chunks = client.synthesize_prose(
        text=long_prose,
        output_path=out_master,
        voice="Puck",
        model="test-mock-model",
        target_words_per_chunk=15,
    )

    assert master_path.exists()
    assert dur > 0
    assert len(synthesized_chunks) == len(chunks)


def test_multi_cast_studio_client(tmp_path, test_orchestrator):
    client = MultiCastStudioClient(orchestrator=test_orchestrator)

    screenplay = [
        {
            "speaker": "Narrator",
            "text": "कमरे में भारी खामोशी छाई हुई थी।",
            "acting": {"emotion": "calm", "delivery_style": "steady_measured"},
        },
        {
            "speaker": "Vikram",
            "text": "तुमने मुझे यहाँ क्यों बुलाया?",
            "acting": {"emotion": "anger", "delivery_style": "harsh_tense"},
        },
        {
            "speaker": "Maya",
            "text": "[whispers] सच बताने के लिए।",
            "acting": {"emotion": "whisper", "delivery_style": "whisper"},
        },
    ]

    voices = {
        "Narrator": "Aoede",
        "Vikram": "Fenrir",
        "Maya": "Kore",
    }

    result = client.produce_screenplay(
        segments=screenplay,
        character_voices=voices,
        chapter_num=1,
        output_dir=tmp_path,
        model="test-mock-model",
    )

    assert result.chapter_num == 1
    assert result.total_segments == 3
    assert result.master_audio_path.exists()
    assert result.duration_sec > 0
    assert result.integrated_lufs == -19.0
    assert result.qc_passed is True
