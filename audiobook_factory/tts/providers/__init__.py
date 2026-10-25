#!/usr/bin/env python3
"""
Audiobook Factory - Pluggable TTS Model Providers.
Exports BaseTTSModelAdapter, GeminiTTSAdapter, QwenTTSAdapter, and ModelAdapterRegistry.
"""

from audiobook_factory.tts.providers.base import BaseTTSModelAdapter
from audiobook_factory.tts.providers.gemini_adapter import GeminiTTSAdapter
from audiobook_factory.tts.providers.qwen_adapter import QwenTTSAdapter
from audiobook_factory.tts.providers.registry import (
    ModelAdapterRegistry,
    get_adapter_registry,
    adapter_registry,
)

# Pre-register standard adapters into global registry
_gemini_tts_adapter = GeminiTTSAdapter(model_name="gemini-3.8-flash-tts")
_gemini_adapter = GeminiTTSAdapter(model_name="gemini-3.8-flash")
_gemini_25_adapter = GeminiTTSAdapter(model_name="gemini-2.5-flash")
_gemini_20_adapter = GeminiTTSAdapter(model_name="gemini-2.0-flash")
_qwen_adapter = QwenTTSAdapter(model_name="qwen3-tts")

adapter_registry.register("gemini-3.8-flash-tts", _gemini_tts_adapter)
adapter_registry.register("gemini-3.8-flash", _gemini_adapter)
adapter_registry.register("gemini-2.5-flash", _gemini_25_adapter)
adapter_registry.register("gemini-2.0-flash", _gemini_20_adapter)
adapter_registry.register("qwen3-tts", _qwen_adapter)
adapter_registry.register("qwen3-tts-custom", _qwen_adapter)

__all__ = [
    "BaseTTSModelAdapter",
    "GeminiTTSAdapter",
    "QwenTTSAdapter",
    "ModelAdapterRegistry",
    "get_adapter_registry",
    "adapter_registry",
]
