#!/usr/bin/env python3
"""
Audiobook Factory - Polymorphic Provider Adapters: Base Interface.
==================================================================
Defines common execution contracts and response structures for all model providers:
Google Gemini, OpenAI, Cerebras, Groq, Anthropic, and Local GPU.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class GenerationResult:
    """Standardized result returned by text generation models."""
    text: str
    finish_reason: str
    tokens_used: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    thoughts: str = ""
    raw_response: Dict[str, Any] = field(default_factory=dict)
    model_id: str = ""
    provider: str = ""


@dataclass
class SpeechResult:
    """Standardized result returned by speech synthesis models."""
    audio_bytes: bytes
    mime_type: str = "audio/wav"
    sample_rate: int = 24000
    duration_sec: float = 0.0
    tokens_used: int = 0
    model_id: str = ""
    provider: str = ""


class BaseProviderAdapter(ABC):
    """Abstract Base Class for all LLM and TTS Provider Adapters."""

    @abstractmethod
    def generate_text(
        self,
        model: str,
        prompt: str,
        api_key: str,
        system_instruction: Optional[str] = None,
        thinking_budget: Optional[int] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        response_json: bool = False,
        timeout: float = 60.0,
        **kwargs,
    ) -> GenerationResult:
        """Generates text from an LLM model."""
        pass

    @abstractmethod
    def synthesize_speech(
        self,
        model: str,
        text: str,
        voice_name: str,
        api_key: str,
        timeout: float = 60.0,
        **kwargs,
    ) -> SpeechResult:
        """Synthesizes speech audio from a TTS model."""
        pass

    @abstractmethod
    def format_payload(
        self,
        model: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        thinking_budget: Optional[int] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        response_json: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Constructs provider-specific HTTP request payload."""
        pass
