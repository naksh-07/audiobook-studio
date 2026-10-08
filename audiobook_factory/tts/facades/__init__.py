#!/usr/bin/env python3
"""
Audiobook Factory - Specialized TTS Client Facades.
Exports GenericTTSClient, LongFormTTSClient, and MultiCastStudioClient.
"""

from audiobook_factory.tts.facades.generic_client import GenericTTSClient
from audiobook_factory.tts.facades.long_form_client import LongFormTTSClient
from audiobook_factory.tts.facades.multi_cast_client import MultiCastStudioClient

__all__ = [
    "GenericTTSClient",
    "LongFormTTSClient",
    "MultiCastStudioClient",
]
