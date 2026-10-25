#!/usr/bin/env python3
"""
Audiobook Factory - Advanced TTS Model Adapter Registry.
Provides thread-safe registration, capability queries, and intelligent fallback
cascades for all pluggable TTS model adapters (Gemini, Qwen, Local CUDA, WinRT).
"""

from __future__ import annotations
import threading
from typing import Dict, Any, List, Optional, Tuple, Set
from pydantic import BaseModel, ConfigDict, Field

from audiobook_factory.logger import logger
from audiobook_factory.tts.providers.base import BaseTTSModelAdapter


class ModelCapabilities(BaseModel):
    """
    Metadata describing the hardware and acoustic capabilities of a TTS model adapter.
    """
    model_config = ConfigDict(frozen=True)

    model_name: str
    provider: str
    native_sample_rate: int = 24000
    max_chars_per_request: int = 2500
    supports_speech_metadata: bool = False
    supports_voice_conditioning: bool = False
    supports_multispeaker: bool = False
    recommended_temperature_range: Tuple[float, float] = (0.65, 0.85)
    supported_voices: List[str] = Field(default_factory=list)


# Standard Fallback Cascades
DEFAULT_FALLBACK_CASCADES: Dict[str, List[str]] = {
    "gemini-3.8-flash-tts": ["gemini-2.5-flash-tts", "gemini-2.0-flash-tts"],
    "gemini-3.8-flash": ["gemini-2.5-flash", "gemini-2.0-flash"],
    "gemini-2.5-flash": ["gemini-2.0-flash", "gemini-3.8-flash"],
    "gemini-2.0-flash": ["gemini-2.5-flash", "gemini-3.8-flash"],
    "qwen3-tts": ["gemini-3.8-flash", "gemini-3.8-flash-tts", "gemini-2.5-flash"],
    "qwen3-tts-custom": ["qwen3-tts", "gemini-3.8-flash", "gemini-3.8-flash-tts"],
}


class ModelAdapterRegistry:
    """
    Central, thread-safe registry for all active TTS model adapters.
    Manages capability discovery, runtime adapter resolution, and automatic fallback chains.
    """

    def __init__(self):
        self._adapters: Dict[str, BaseTTSModelAdapter] = {}
        self._capabilities: Dict[str, ModelCapabilities] = {}
        self._fallback_chains: Dict[str, List[str]] = dict(DEFAULT_FALLBACK_CASCADES)
        self._default_model: str = "gemini-3.8-flash-tts"
        self._lock = threading.Lock()

    def register(
        self,
        model_identifier: str,
        adapter: BaseTTSModelAdapter,
        capabilities: Optional[ModelCapabilities] = None,
        fallback_models: Optional[List[str]] = None,
    ) -> None:
        """Registers a model adapter with optional capabilities and fallback chain."""
        key = model_identifier.lower().strip()
        with self._lock:
            self._adapters[key] = adapter
            if capabilities:
                self._capabilities[key] = capabilities
            else:
                meta = adapter.get_model_metadata()
                self._capabilities[key] = ModelCapabilities(
                    model_name=key,
                    provider=meta.get("provider", "custom"),
                    native_sample_rate=meta.get("native_sample_rate", 24000),
                    max_chars_per_request=meta.get("max_recommended_chars", 2500),
                    supports_speech_metadata=meta.get("supports_speech_metadata", False),
                    supports_voice_conditioning=meta.get("supports_reference_audio", False),
                    recommended_temperature_range=meta.get("temperature_bounds", (0.30, 0.52)),
                    supported_voices=meta.get("supported_voices", []),
                )

            if fallback_models:
                self._fallback_chains[key] = fallback_models

    def unregister(self, model_identifier: str) -> bool:
        """Unregisters a model adapter."""
        key = model_identifier.lower().strip()
        with self._lock:
            if key in self._adapters:
                del self._adapters[key]
                self._capabilities.pop(key, None)
                self._fallback_chains.pop(key, None)
                return True
            return False

    def get_adapter(self, model_identifier: Optional[str] = None) -> BaseTTSModelAdapter:
        """
        Resolves the appropriate model adapter for the specified model identifier.
        """
        key = (model_identifier or self._default_model).lower().strip()
        with self._lock:
            # 1. Exact match
            if key in self._adapters:
                return self._adapters[key]

            # 2. Prefix / Family match (e.g. "gemini-*" or "qwen-*")
            for reg_key, adapter in self._adapters.items():
                if key.startswith(reg_key) or reg_key.startswith(key.split("-")[0]):
                    return adapter

            # 3. Fallback to default
            if self._default_model.lower() in self._adapters:
                logger.warning(f"[!] Model '{model_identifier}' not found in registry. Falling back to default '{self._default_model}'.")
                return self._adapters[self._default_model.lower()]

            for alt_key in [self._default_model.replace("-tts", ""), f"{self._default_model}-tts"]:
                if alt_key.lower() in self._adapters:
                    logger.warning(f"[!] Model '{model_identifier}' not found. Falling back to '{alt_key}'.")
                    return self._adapters[alt_key.lower()]

            if self._adapters:
                return next(iter(self._adapters.values()))

            raise KeyError(f"No TTS model adapter registered for model '{model_identifier}' and no default available.")

    def get_fallback_chain(self, model_identifier: str) -> List[str]:
        """Returns the configured fallback chain for a model."""
        key = model_identifier.lower().strip()
        with self._lock:
            return list(self._fallback_chains.get(key, [self._default_model]))

    def get_capabilities(self, model_identifier: str) -> Optional[ModelCapabilities]:
        """Retrieves capabilities for a registered model."""
        key = model_identifier.lower().strip()
        with self._lock:
            return self._capabilities.get(key)

    def set_default_model(self, model_identifier: str) -> None:
        """Sets the fallback default model identifier."""
        with self._lock:
            self._default_model = model_identifier.strip()

    def list_registered_models(self) -> List[str]:
        """Returns list of all registered model identifiers."""
        with self._lock:
            return list(self._adapters.keys())


# Global Module Singleton
adapter_registry = ModelAdapterRegistry()


def get_adapter_registry() -> ModelAdapterRegistry:
    """Returns the global adapter registry instance."""
    return adapter_registry
