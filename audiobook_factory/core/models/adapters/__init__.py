#!/usr/bin/env python3
"""
Audiobook Factory - Polymorphic Provider Adapters.
==================================================
"""

from audiobook_factory.core.models.adapters.base import (
    BaseProviderAdapter,
    GenerationResult,
    SpeechResult,
)
from audiobook_factory.core.models.adapters.gemini import (
    GeminiProviderAdapter,
    ApiHttpError,
)
from audiobook_factory.core.models.adapters.openai_compat import (
    OpenAICompatibleAdapter,
)
from audiobook_factory.core.models.adapters.local_gpu import (
    LocalGpuAdapter,
    HardwareVRAMGuard,
)

__all__ = [
    "BaseProviderAdapter",
    "GenerationResult",
    "SpeechResult",
    "GeminiProviderAdapter",
    "ApiHttpError",
    "OpenAICompatibleAdapter",
    "LocalGpuAdapter",
    "HardwareVRAMGuard",
]
