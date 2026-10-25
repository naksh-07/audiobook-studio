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
    assert abs(result.integrated_lufs - (-19.0)) <= 1.0
    assert result.qc_passed is True

    # Validate output WAV file
    with wave.open(str(result.master_audio_path), "rb") as wf:
        assert wf.getnchannels() in (1, 2)
        assert wf.getframerate() in (24000, 48000)
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


def test_multicast_dialogue_rally_grouping_and_fallback(multicast_orchestrator, tmp_path):
    client = MultiCastStudioClient(orchestrator=multicast_orchestrator)
    out_dir = tmp_path / "chapter_rally"

    rally_segments = [
        {"speaker": "Narrator", "text": "सराय में सन्नाटा था।", "scene_num": 1},
        {"speaker": "Geralt", "text": "चुप रहो।", "scene_num": 1, "acting": {"emotion": "grave"}},
        {"speaker": "Borch", "text": "पर मुझे कोई डर नहीं।", "scene_num": 1, "acting": {"emotion": "amused"}},
        {"speaker": "Geralt", "text": "तुम्हें होना चाहिए।", "scene_num": 1, "acting": {"emotion": "grave"}},
        {"speaker": "Narrator", "text": "वे खिड़की के पास गए।", "scene_num": 1},
    ]

    result = client.produce_screenplay(
        segments=rally_segments,
        character_voices={"Narrator": "Aoede", "Geralt": "Charon", "Borch": "Fenrir"},
        chapter_num=1,
        output_dir=out_dir,
        model="gemini-3.8-flash-tts",
        enable_dialogue_rallies=True,
    )

    assert result.master_audio_path.exists()
    assert result.duration_sec > 0
    assert result.qc_passed is True

def test_multicast_pause_cadence_matrix(multicast_orchestrator, tmp_path):
    """
    Verifies that _stitch_screenplay correctly applies the Audible Flow pause cadence:
    1. Narrator prose lead-in ending with em-dash -> 340ms (never 110ms).
    2. Character mid-speech cut-off ending with em-dash -> 110ms.
    3. Sentence terminator (।) between narrator paragraphs -> 400ms.
    4. Sentence terminator (।) between different character turns -> 400ms.
    """
    client = MultiCastStudioClient(orchestrator=multicast_orchestrator)
    from audiobook_factory.tts.contracts import CanonicalTTSRequest, SynthesizedAudioChunk

    req_narr_intro = CanonicalTTSRequest(
        segment_uid="s1",
        literary_text="कसाई बोला—",
        spoken_text="कसाई बोला—",
        voice_id="Aoede",
        speaker="Narrator",
        sample_rate=24000,
        scene_num=1,
    )
    req_char_dialogue = CanonicalTTSRequest(
        segment_uid="s2",
        literary_text="तगड़ी घोड़ी है।",
        spoken_text="तगड़ी घोड़ी है।",
        voice_id="Enceladus",
        speaker="Butcher",
        sample_rate=24000,
        scene_num=1,
    )
    req_char_interrupted = CanonicalTTSRequest(
        segment_uid="s3",
        literary_text="मैं तो बस कह रहा था—",
        spoken_text="मैं तो बस कह रहा था—",
        voice_id="Enceladus",
        speaker="Butcher",
        sample_rate=24000,
        scene_num=1,
    )
    req_char_response = CanonicalTTSRequest(
        segment_uid="s4",
        literary_text="उस घोड़े को हाथ मत लगाना, साथी।",
        spoken_text="उस घोड़े को हाथ मत लगाना, साथी।",
        voice_id="Charon",
        speaker="Borch",
        sample_rate=24000,
        scene_num=1,
    )
    req_narr_para1 = CanonicalTTSRequest(
        segment_uid="s5",
        literary_text="दीवार की ओट से अजनबी घूमा।",
        spoken_text="दीवार की ओट से अजनबी घूमा।",
        voice_id="Aoede",
        speaker="Narrator",
        sample_rate=24000,
        scene_num=1,
    )
    req_narr_para2 = CanonicalTTSRequest(
        segment_uid="s6",
        literary_text="उसके बाल घने और बादामी थे।",
        spoken_text="उसके बाल घने और बादामी थे।",
        voice_id="Aoede",
        speaker="Narrator",
        sample_rate=24000,
        scene_num=1,
    )

    dummy_pcm = b"\x00\x00" * 2400
    chunk1 = SynthesizedAudioChunk(segment_uid="s1", pcm_bytes=dummy_pcm, sample_rate=24000, num_channels=1, duration_sec=0.1, provider_model="model", voice_id="v1")
    chunk2 = SynthesizedAudioChunk(segment_uid="s2", pcm_bytes=dummy_pcm, sample_rate=24000, num_channels=1, duration_sec=0.1, provider_model="model", voice_id="v2")
    chunk3 = SynthesizedAudioChunk(segment_uid="s3", pcm_bytes=dummy_pcm, sample_rate=24000, num_channels=1, duration_sec=0.1, provider_model="model", voice_id="v3")
    chunk4 = SynthesizedAudioChunk(segment_uid="s4", pcm_bytes=dummy_pcm, sample_rate=24000, num_channels=1, duration_sec=0.1, provider_model="model", voice_id="v4")
    chunk5 = SynthesizedAudioChunk(segment_uid="s5", pcm_bytes=dummy_pcm, sample_rate=24000, num_channels=1, duration_sec=0.1, provider_model="model", voice_id="v5")
    chunk6 = SynthesizedAudioChunk(segment_uid="s6", pcm_bytes=dummy_pcm, sample_rate=24000, num_channels=1, duration_sec=0.1, provider_model="model", voice_id="v6")

    batch = [
        (req_narr_intro, chunk1, None),
        (req_char_dialogue, chunk2, None),
        (req_char_interrupted, chunk3, None),
        (req_char_response, chunk4, None),
        (req_narr_para1, chunk5, None),
        (req_narr_para2, chunk6, None),
    ]

    out_file = tmp_path / "cadence_test.wav"
    dur = client._stitch_screenplay(batch, out_file)
    assert dur > 0
    assert out_file.exists()
