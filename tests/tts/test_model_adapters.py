#!/usr/bin/env python3
"""
Unit tests for TTS Model Adapters and ModelAdapterRegistry.
Verifies BaseTTSModelAdapter contract, GeminiTTSAdapter configuration & payload invariants,
QwenTTSAdapter validation, and runtime registry lookups.
"""

from unittest.mock import patch, MagicMock
import pytest

from audiobook_factory.tts.contracts import CanonicalTTSRequest, DeliveryIntent
from audiobook_factory.tts.providers.base import BaseTTSModelAdapter
from audiobook_factory.tts.providers.gemini_adapter import GeminiTTSAdapter, GEMINI_PERMISSIVE_SAFETY
from audiobook_factory.tts.providers.qwen_adapter import QwenTTSAdapter
from audiobook_factory.tts.providers.registry import ModelAdapterRegistry, get_adapter_registry


def test_model_adapter_registry_resolution():
    registry = ModelAdapterRegistry()
    gemini_ad = GeminiTTSAdapter("gemini-3.8-flash")
    qwen_ad = QwenTTSAdapter("qwen3-tts")

    registry.register("gemini-3.8-flash", gemini_ad)
    registry.register("qwen3-tts", qwen_ad)

    # Exact match
    assert registry.get_adapter("gemini-3.8-flash") is gemini_ad
    assert registry.get_adapter("qwen3-tts") is qwen_ad

    # Prefix match
    assert registry.get_adapter("gemini-3.8-flash-preview") is gemini_ad
    assert registry.get_adapter("qwen3-tts-large") is qwen_ad

    # Fallback to default
    assert registry.get_adapter("unknown-model-xyz") is gemini_ad


def test_gemini_adapter_metadata_and_validation():
    adapter = GeminiTTSAdapter("gemini-3.8-flash")
    meta = adapter.get_model_metadata()

    assert meta["model_name"] == "gemini-3.8-flash"
    assert meta["native_sample_rate"] == 24000
    assert "Puck" in meta["supported_voices"]
    assert meta["supports_speech_metadata"] is True

    # Validate permissive safety settings invariant
    for s in GEMINI_PERMISSIVE_SAFETY:
        assert s["threshold"] == "BLOCK_NONE"

    # Compatibility check
    req = CanonicalTTSRequest(
        segment_uid="seg_01",
        literary_text="नमस्ते",
        spoken_text="नमस्ते",
        voice_id="Puck",
        temperature=0.38,
    )
    compat, warnings = adapter.validate_request_compatibility(req)
    assert compat is True
    assert len(warnings) == 0


def test_qwen_adapter_metadata_and_mock_synthesis():
    adapter = QwenTTSAdapter("qwen3-tts")
    meta = adapter.get_model_metadata()

    assert meta["model_name"] == "qwen3-tts"
    assert meta["supports_reference_audio"] is True

    req = CanonicalTTSRequest(
        segment_uid="seg_02",
        literary_text="यह एक परीक्षण है।",
        spoken_text="यह एक परीक्षण है।",
        voice_id="CustomVoice_01",
        delivery_intent=DeliveryIntent(emotion="whisper", delivery_style="whisper"),
    )

    # Test synthesis in simulation mode when endpoint is not live
    chunk = adapter.synthesize_chunk(req)
    assert chunk.segment_uid == "seg_02"
    assert chunk.sample_rate == 24000
    assert chunk.duration_sec > 0
    assert len(chunk.pcm_bytes) > 0
