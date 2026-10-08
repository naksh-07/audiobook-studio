#!/usr/bin/env python3
"""
Deep Unit Tests for LongFormTTSClient Facade.
Tests 4-tier semantic chunking, concurrent batch synthesis,
Net-Silence DSP stitching, progress callbacks, and resume checkpoint caching.
"""

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
from audiobook_factory.tts.facades.long_form_client import LongFormTTSClient


class CountingMockAdapter(BaseTTSModelAdapter):
    """Tracks number of synthesize calls to verify checkpoint resume logic."""

    def __init__(self, model_name: str = "test-mock-model"):
        super().__init__(model_name)
        self.call_count = 0

    def synthesize_chunk(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk:
        self.call_count += 1
        words = max(1, len(request.spoken_text.split()))
        dur = max(0.4, min(words * 0.25, 4.0))
        num_samples = int(request.sample_rate * dur)
        samples = [12000 if (i // 50) % 2 == 0 else -12000 for i in range(num_samples)]
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
def counting_orchestrator():
    reg = ModelAdapterRegistry()
    adapter = CountingMockAdapter("test-mock-model")
    reg.register("test-mock-model", adapter)
    return TTSCoreOrchestrator(registry=reg, max_workers=2), adapter


def test_long_form_synthesize_prose(tmp_path, counting_orchestrator):
    orch, adapter = counting_orchestrator
    client = LongFormTTSClient(orchestrator=orch)
    out_file = tmp_path / "long_prose_master.wav"

    prose = (
        "सड़क पर सन्नाटा पसरा हुआ था। केवल पत्तों की सरसराहट सुनाई दे रही थी। "
        "रवि तेज़ी से कदम बढ़ा रहा था। उसे समय पर उस पुराने हवेली तक पहुँचना था।\n\n"
        "जैसे ही उसने दरवाज़ा खटखटाया, अंदर से एक भारी आवाज़ आई। "
        "कौन है इस तूफ़ानी रात में? रवि ने साहस जुटाकर उत्तर दिया।"
    )

    progress_events = []
    def on_progress(fraction, cur=0, tot=0):
        progress_events.append((fraction, cur, tot))

    master_path, duration, chunks = client.synthesize_prose(
        text=prose,
        output_path=out_file,
        voice="Puck",
        model="test-mock-model",
        target_words_per_chunk=15,
        progress_callback=on_progress,
    )

    assert master_path.exists()
    assert duration > 0.5
    assert len(chunks) >= 2
    assert adapter.call_count == len(chunks)
    assert len(progress_events) > 0

    with wave.open(str(master_path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 24000
        assert wf.getnframes() > 0


def test_long_form_synthesize_chapter_checkpoint_resume(tmp_path, counting_orchestrator):
    orch, adapter = counting_orchestrator
    client = LongFormTTSClient(orchestrator=orch)

    chapter_text = (
        "अध्याय एक। शुरुआत का दिन।\n\n"
        "सूर्य अभी निकला ही था। गाँव के लोग अपने खेतों की ओर चल पड़े थे। "
        "किशन ने अपने बैलों को बाँधा और हल संभाला।"
    )

    ckpt_dir = tmp_path / "checkpoints_ch1"
    out_file = tmp_path / "chapter_001_master.wav"

    # 1. First run: generates chunks and saves checkpoints
    res1: ChapterMasterResult = client.synthesize_chapter(
        chapter_num=1,
        text=chapter_text,
        output_file=out_file,
        checkpoint_dir=ckpt_dir,
        model="test-mock-model",
        target_words_per_chunk=10,
    )

    assert res1.chapter_num == 1
    assert res1.master_audio_path.exists()
    assert res1.qc_passed is True
    initial_calls = adapter.call_count
    assert initial_calls > 0
    assert (ckpt_dir / "checkpoint_manifest.json").exists()

    # 2. Second run with same checkpoint dir: must load cached chunks without re-synthesizing
    out_file2 = tmp_path / "chapter_001_master_reloaded.wav"
    res2 = client.synthesize_chapter(
        chapter_num=1,
        text=chapter_text,
        output_file=out_file2,
        checkpoint_dir=ckpt_dir,
        model="test-mock-model",
        target_words_per_chunk=10,
    )

    assert res2.master_audio_path.exists()
    # Call count should not increase because all chunks were cached in checkpoint
    assert adapter.call_count == initial_calls


def test_long_form_empty_prose_error(counting_orchestrator):
    orch, _ = counting_orchestrator
    client = LongFormTTSClient(orchestrator=orch)

    with pytest.raises(ValueError, match="no synthesizable text"):
        client.synthesize_prose(text="   \n\n   ", output_path=Path("dummy.wav"))
