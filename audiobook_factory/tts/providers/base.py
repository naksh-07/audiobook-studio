#!/usr/bin/env python3
"""
Audiobook Factory - Pluggable TTS Model Adapter Base.
Defines the abstract interface and standard lifecycle for all TTS model adapters
(Gemini 3.8 Flash, Qwen3-TTS, Local Neural Models, etc.).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional

from audiobook_factory.tts.contracts import CanonicalTTSRequest, SynthesizedAudioChunk


class BaseTTSModelAdapter(ABC):
    """
    Abstract Base Class for all TTS Model Adapters.
    Every model provider (Gemini, Qwen, ElevenLabs, WinRT, etc.) must implement this interface.
    """

    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.config = config or {}

    @abstractmethod
    def synthesize_chunk(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk:
        """
        Synchronously synthesizes a canonical TTS request into raw audio PCM bytes.

        Args:
            request: Standardized CanonicalTTSRequest containing spoken text, voice, delivery intent.

        Returns:
            SynthesizedAudioChunk containing raw PCM bytes, sample rate, duration, and metadata.

        Raises:
            Exception: If API or neural synthesis fails after retries.
        """
        pass

    @abstractmethod
    async def synthesize_chunk_async(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk:
        """
        Asynchronously synthesizes a canonical TTS request into raw audio PCM bytes.
        """
        pass

    @abstractmethod
    def validate_request_compatibility(self, request: CanonicalTTSRequest) -> Tuple[bool, List[str]]:
        """
        Validates whether the incoming canonical request is compatible with this model's
        supported voices, sample rates, languages, and character limits.

        Returns:
            (is_compatible, list_of_warning_or_error_reasons)
        """
        pass

    @abstractmethod
    def get_model_metadata(self) -> Dict[str, Any]:
        """
        Returns metadata describing supported sample rates, native voices,
        max input tokens/characters, and recommended temperature bounds.
        """
        pass
