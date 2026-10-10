#!/usr/bin/env python3
"""
Unit tests for TwoTierAudioQualityGate and TTSCoreOrchestrator.
Verifies acoustic metric audits, clipping detection, and batch orchestration.
"""

import struct
import pytest
from unittest.mock import MagicMock

from audiobook_factory.tts.contracts import (
    CanonicalTTSRequest,
    SynthesizedAudioChunk,
    TTSPipelineMode,
)
from audiobook_factory.tts.quality_gate import TwoTierAudioQualityGate
from audiobook_factory.tts.core_orchestrator import TTSCoreOrchestrator
from audiobook_factory.tts.providers.base import BaseTTSModelAdapter
from audiobook_factory.tts.providers.registry import ModelAdapterRegistry


class MockModelAdapter(BaseTTSModelAdapter):
    """Mock adapter generating synthetic PCM sine/square waves for test verification."""

    def synthesize_chunk(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk:
        sample_rate = request.sample_rate
        # Generate 1.0 second of clean 440Hz test audio (amplitude 16000)
        num_samples = int(sample_rate * 1.0)
        samples = []
        for i in range(num_samples):
            # Square wave / tone
            val = 16000 if (i // 50) % 2 == 0 else -16000
            samples.append(val)

        pcm = struct.pack(f"<{num_samples}h", *samples)
        return SynthesizedAudioChunk(
            segment_uid=request.segment_uid,
            pcm_bytes=pcm,
            sample_rate=sample_rate,
            num_channels=1,
            duration_sec=1.0,
            provider_model=self.model_name,
            voice_id=request.voice_id,
        )

    async def synthesize_chunk_async(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk:
        return self.synthesize_chunk(request)

    def validate_request_compatibility(self, request: CanonicalTTSRequest):
        return True, []

    def get_model_metadata(self):
        return {"model_name": self.model_name}


def test_quality_gate_clean_audio():
    req = CanonicalTTSRequest(
        segment_uid="seg_clean",
        literary_text="यह एक अच्छा वाक्य है।",
        spoken_text="यह एक अच्छा वाक्य है।",
        voice_id="Puck",
    )
    # 1 second of audio for 5 words -> duration_ratio = 0.20s/word (healthy)
    num_samples = 24000
    samples = [12000 if (i // 50) % 2 == 0 else -12000 for i in range(num_samples)]
    pcm = struct.pack(f"<{num_samples}h", *samples)

    chunk = SynthesizedAudioChunk(
        segment_uid="seg_clean",
        pcm_bytes=pcm,
        sample_rate=24000,
        num_channels=1,
        duration_sec=1.0,
        provider_model="mock",
        voice_id="Puck",
    )

    res = TwoTierAudioQualityGate.audit_chunk(req, chunk)
    assert res.passed is True
    assert res.status == "PASS"
    assert res.tier1_acoustic_passed is True
    assert res.peak_amplitude == 12000
    assert res.consecutive_clipped_samples == 0


def test_quality_gate_silence_detection():
    req = CanonicalTTSRequest(
        segment_uid="seg_silent",
        literary_text="यह वाक्य बोला जाना चाहिए था।",
        spoken_text="यह वाक्य बोला जाना चाहिए था।",
        voice_id="Puck",
    )
    num_samples = 24000
    # Complete silence
    samples = [0] * num_samples
    pcm = struct.pack(f"<{num_samples}h", *samples)

    chunk = SynthesizedAudioChunk(
        segment_uid="seg_silent",
        pcm_bytes=pcm,
        sample_rate=24000,
        num_channels=1,
        duration_sec=1.0,
        provider_model="mock",
        voice_id="Puck",
    )

    res = TwoTierAudioQualityGate.audit_chunk(req, chunk)
    assert res.passed is False
    assert res.tier1_acoustic_passed is False
    assert "below minimum audible threshold" in res.diagnostics[0]


def test_quality_gate_clipping_detection():
    req = CanonicalTTSRequest(
        segment_uid="seg_clipped",
        literary_text="जोर से बोला गया वाक्य।",
        spoken_text="जोर से बोला गया वाक्य।",
        voice_id="Puck",
    )
    num_samples = 24000
    # Hard clipped max 32767
    samples = [32767] * 20 + [0] * (num_samples - 20)
    pcm = struct.pack(f"<{num_samples}h", *samples)

    chunk = SynthesizedAudioChunk(
        segment_uid="seg_clipped",
        pcm_bytes=pcm,
        sample_rate=24000,
        num_channels=1,
        duration_sec=1.0,
        provider_model="mock",
        voice_id="Puck",
    )

    res = TwoTierAudioQualityGate.audit_chunk(req, chunk)
    assert res.passed is False
    assert any("clipping" in d.lower() for d in res.diagnostics)


def test_orchestrator_single_and_batch_synthesis():
    registry = ModelAdapterRegistry()
    mock_adapter = MockModelAdapter("mock-tts")
    registry.register("mock-tts", mock_adapter)

    orchestrator = TTSCoreOrchestrator(registry=registry, max_workers=4)

    # 1. Single string synthesis
    chunk, val = orchestrator.synthesize(
        request_or_text="नमस्ते दुनिया, यह पहला वाक्य है।",
        voice_id="Puck",
        model="mock-tts",
    )
    assert chunk.duration_sec == 1.0
    assert val is not None
    assert val.passed is True

    # 2. Batch synthesis
    req1 = CanonicalTTSRequest(segment_uid="b_01", literary_text="एक", spoken_text="एक", voice_id="Puck")
    req2 = CanonicalTTSRequest(segment_uid="b_02", literary_text="दो", spoken_text="दो", voice_id="Puck")
    req3 = CanonicalTTSRequest(segment_uid="b_03", literary_text="तीन", spoken_text="तीन", voice_id="Puck")

    batch_res = orchestrator.synthesize_batch([req1, req2, req3], model="mock-tts")
    assert len(batch_res) == 3
    # Verify ordering preservation
    assert batch_res[0][0].segment_uid == "b_01"
    assert batch_res[1][0].segment_uid == "b_02"
    assert batch_res[2][0].segment_uid == "b_03"
