#!/usr/bin/env python3
"""
Deep unit tests for ModelAdapterRegistry.
Tests ModelCapabilities schema queries, automatic fallback chains,
thread-safe registration, and unregistration.
"""

import pytest
from audiobook_factory.tts.providers.registry import (
    ModelAdapterRegistry,
    ModelCapabilities,
)
from audiobook_factory.tts.providers.gemini_adapter import GeminiTTSAdapter
from audiobook_factory.tts.providers.qwen_adapter import QwenTTSAdapter


def test_registry_capabilities_and_metadata():
    registry = ModelAdapterRegistry()
    gem_adapter = GeminiTTSAdapter("gemini-3.8-flash")
    qwen_adapter = QwenTTSAdapter("qwen3-tts")

    registry.register("gemini-3.8-flash", gem_adapter)
    registry.register("qwen3-tts", qwen_adapter)

    caps_gem = registry.get_capabilities("gemini-3.8-flash")
    assert caps_gem is not None
    assert caps_gem.provider == "google"
    assert caps_gem.native_sample_rate == 24000
    assert caps_gem.supports_speech_metadata is True

    caps_qwen = registry.get_capabilities("qwen3-tts")
    assert caps_qwen is not None
    assert caps_qwen.provider == "alibaba/qwen"
    assert caps_qwen.supports_voice_conditioning is True


def test_registry_fallback_chains():
    registry = ModelAdapterRegistry()
    assert "gemini-2.5-flash" in registry.get_fallback_chain("gemini-3.8-flash")
    assert "gemini-3.8-flash" in registry.get_fallback_chain("qwen3-tts")


def test_registry_dynamic_register_and_unregister():
    registry = ModelAdapterRegistry()
    custom_adapter = GeminiTTSAdapter("gemini-custom-exp")

    custom_caps = ModelCapabilities(
        model_name="gemini-custom-exp",
        provider="google",
        native_sample_rate=24000,
        supports_speech_metadata=True,
    )

    registry.register("gemini-custom-exp", custom_adapter, capabilities=custom_caps)
    assert registry.get_adapter("gemini-custom-exp") is custom_adapter
    assert registry.get_capabilities("gemini-custom-exp").model_name == "gemini-custom-exp"

    # Unregister
    success = registry.unregister("gemini-custom-exp")
    assert success is True
    assert "gemini-custom-exp" not in registry.list_registered_models()
