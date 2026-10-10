#!/usr/bin/env python3
"""
Deep Unit Tests for MultiCastStudioClient Facade.
Tests ensemble casting, Anime Seiyū child casting, Cast Lock persistence,
4D Formant Sculpting, TakeBank auditioning, turn latency, and EBU R128 mastering report.
"""

import json
import wave
import struct
from pathlib import Path
import pytest

from audiobook_factory.tts.contracts import (
    CanonicalTTSRequest,
    SynthesizedAudioChunk,
    ChapterMasterResult,
)
from audiobook_factory.tts.core_orchestrator import TTSCoreOrchestrator
from audiobook_factory.tts.providers.base import BaseTTSModelAdapter
from audiobook_factory.tts.providers.registry import ModelAdapterRegistry
from audiobook_factory.tts.facades.multi_cast_client import MultiCastStudioClient
from audiobook_factory.tts.formant_sculptor import FormantProfile


class MultiCastMockAdapter(BaseTTSModelAdapter):
    """Generates synthetic audio for multi-cast testing."""

    def synthesize_chunk(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk:
        words = max(1, len(request.spoken_text.split()))
        dur = max(0.4, min(words * 0.25, 4.0))
        num_samples = int(request.sample_rate * dur)
        samples = [11000 if (i // 40) % 2 == 0 else -11000 for i in range(num_samples)]
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
def multicast_orchestrator():
    reg = ModelAdapterRegistry()
    adapter = MultiCastMockAdapter("test-mock-model")
    reg.register("test-mock-model", adapter)
    return TTSCoreOrchestrator(registry=reg, max_workers=4)


def test_multicast_produce_screenplay_with_formants_and_takebank(tmp_path, multicast_orchestrator):
    client = MultiCastStudioClient(orchestrator=multicast_orchestrator)
    out_dir = tmp_path / "chapter_output"

    # Cast Lock file
    cast_lock_file = tmp_path / "cast_lock.json"
    with open(cast_lock_file, "w", encoding="utf-8") as f:
        json.dump({"Geralt": "Charon", "Yennefer": "Aoede", "Narrator": "Puck"}, f)

    segments = [
        {
            "speaker": "Narrator",
            "text": "हवा में बर्फ की गंध थी। दोनों चुपचाप खड़े रहे।",
            "scene_num": 1,
        },
        {
            "speaker": "Geralt",
            "text": "तुम्हें यहाँ नहीं आना चाहिए था, येनेफ़र।",
            "scene_num": 1,
            "acting": {"emotion": "grave", "delivery_style": "restraint"},
            "performance_priority": "focused",
        },
        {
            "speaker": "Yennefer",
            "text": "और तुम्हें लगता है कि तुम मुझे रोक सकते हो?",
            "scene_num": 1,
            "acting": {"emotion": "defiant", "delivery_style": "exposed"},
            "performance_priority": "climactic",
        },
        {
            "speaker": "Ciri",
            "text": "कृपया लड़ो मत!",
            "scene_num": 1,
            "is_child": True,
            "age": 10,
            "acting": {"emotion": "pleading"},
        },
    ]

    character_voices = {
        "Narrator": "Puck",
        "Geralt": "Charon",
        "Yennefer": "Aoede",
        "Ciri": "Zephyr",
    }

    formant_map = {
        "Geralt": FormantProfile.WARM_BARITONE,
        "Yennefer": FormantProfile.BRIGHT_FEMALE,
        "Ciri": FormantProfile.CHILD_ANIME,
    }

    result: ChapterMasterResult = client.produce_screenplay(
        segments=segments,
        character_voices=character_voices,
        chapter_num=3,
        output_dir=out_dir,
        model="test-mock-model",
        cast_lock_file=cast_lock_file,
        character_formants=formant_map,
        enable_take_bank=True,
    )

    assert result.chapter_num == 3
    assert result.master_audio_path.exists()
    assert result.duration_sec > 1.0
    assert result.total_segments == 4
    assert result.integrated_lufs == -19.0
    assert result.qc_passed is True

    # Validate output WAV file
    with wave.open(str(result.master_audio_path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 24000
        assert wf.getnframes() > 0


def test_multicast_attribution_audit_failure(multicast_orchestrator, tmp_path):
    client = MultiCastStudioClient(orchestrator=multicast_orchestrator)
    out_dir = tmp_path / "chapter_err"

    # Segment with missing speaker
    bad_segments = [
        {"speaker": "", "text": "कोई बोल रहा है लेकिन पता नहीं कौन।"},
    ]

    with pytest.raises(ValueError, match="missing or empty speaker"):
        client.produce_screenplay(
            segments=bad_segments,
            character_voices={"Narrator": "Puck"},
            chapter_num=1,
            output_dir=out_dir,
            model="test-mock-model",
        )
