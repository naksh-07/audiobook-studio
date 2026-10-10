#!/usr/bin/env python3
"""
Deep Unit Tests for TakeBank Auditioning Manager.
Tests multi-take candidate allocation, variant generation, take scoring, and selection.
"""

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
from audiobook_factory.tts.take_bank_manager import TakeBankManager, CandidateTake


class TakeMockAdapter(BaseTTSModelAdapter):
    """Generates synthetic tone audio for multi-take synthesis."""

    def synthesize_chunk(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk:
        words = max(1, len(request.spoken_text.split()))
        dur = max(0.4, min(words * 0.25, 4.0))
        num_samples = int(request.sample_rate * dur)
        samples = [13000 if (i // 40) % 2 == 0 else -13000 for i in range(num_samples)]
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
def take_orchestrator():
    reg = ModelAdapterRegistry()
    adapter = TakeMockAdapter("test-mock-model")
    reg.register("test-mock-model", adapter)
    return TTSCoreOrchestrator(registry=reg, max_workers=4)


def test_take_bank_candidate_generation_climactic(take_orchestrator):
    mgr = TakeBankManager(orchestrator=take_orchestrator)

    base_req = CanonicalTTSRequest(
        literary_text="I will never forgive you!",
        spoken_text="मैं तुम्हें कभी माफ़ नहीं करूँगा!",
        voice_id="Fenrir",
        segment_uid="seg_climax_01",
        speaker="Villain",
        delivery_intent=DeliveryIntent(emotion="furious"),
        sample_rate=24000,
        pipeline_mode=TTSPipelineMode.MULTI_CAST,
    )

    takes = mgr.generate_candidate_takes(base_req, priority="climactic", model="test-mock-model")

    # Climactic must generate 4 variants: standard, restraint, vulnerable, exposed
    assert len(takes) == 4
    variant_types = [t.variant_type for t in takes]
    assert variant_types == ["standard", "restraint", "vulnerable", "exposed"]

    # Exactly one take must be marked selected
    selected_takes = [t for t in takes if t.is_selected]
    assert len(selected_takes) == 1
    assert selected_takes[0].score > 0.0


def test_take_bank_candidate_generation_focused_and_high(take_orchestrator):
    mgr = TakeBankManager(orchestrator=take_orchestrator)

    base_req = CanonicalTTSRequest(
        literary_text="Stay back.",
        spoken_text="पीछे रहो।",
        voice_id="Charon",
        segment_uid="seg_focus_01",
        speaker="Hero",
        delivery_intent=DeliveryIntent(emotion="stern"),
        sample_rate=24000,
        pipeline_mode=TTSPipelineMode.MULTI_CAST,
    )

    # Focused -> 2 takes: standard, restraint
    takes_focused = mgr.generate_candidate_takes(base_req, priority="focused", model="test-mock-model")
    assert len(takes_focused) == 2
    assert [t.variant_type for t in takes_focused] == ["standard", "restraint"]

    # High -> 3 takes: standard, restraint, vulnerable
    takes_high = mgr.generate_candidate_takes(base_req, priority="high", model="test-mock-model")
    assert len(takes_high) == 3
    assert [t.variant_type for t in takes_high] == ["standard", "restraint", "vulnerable"]


def test_take_bank_select_best_take(take_orchestrator):
    mgr = TakeBankManager(orchestrator=take_orchestrator)

    base_req = CanonicalTTSRequest(
        literary_text="Listen to me carefully.",
        spoken_text="मेरी बात ध्यान से सुनो।",
        voice_id="Puck",
        segment_uid="seg_dialogue_01",
        speaker="Mentor",
        delivery_intent=DeliveryIntent(emotion="serious"),
        sample_rate=24000,
        pipeline_mode=TTSPipelineMode.MULTI_CAST,
    )

    chunk, validation, all_takes = mgr.select_best_take(base_req, priority="standard", model="test-mock-model")

    assert chunk is not None
    assert validation is not None
    assert validation.passed is True
    assert len(all_takes) == 1
    assert all_takes[0].is_selected is True
