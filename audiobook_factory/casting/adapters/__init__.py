#!/usr/bin/env python3
"""
Audiobook Factory - Room 3.5: TTS Voice Adapters.
"""

from .base import BaseVoiceAdapter
from .gemini import GeminiVoiceAdapter
from .qwen import QwenVoiceAdapter

__all__ = [
    "BaseVoiceAdapter",
    "GeminiVoiceAdapter",
    "QwenVoiceAdapter",
]
