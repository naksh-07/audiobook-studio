#!/usr/bin/env python3
"""
Audiobook Factory - Room 3.5 Subsystem 3: Base Voice Adapter Interface.
========================================================================
Defines the abstract interface for translating universal character casting
assignments and calibrated formants into provider-specific speech synthesis payloads.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from audiobook_factory.casting.contracts import (
    CharacterCastAssignment,
    SpectralFormantProfile,
    ProviderCapabilities,
)


class BaseVoiceAdapter(ABC):
    """
    Abstract Provider-Specific Voice Adapter.
    Guarantees provider-neutral contracts while handling provider idiosyncrasies.
    """

    @abstractmethod
    def adapt_segment_to_provider(
        self,
        segment: Dict[str, Any],
        character_cast: Optional[CharacterCastAssignment] = None,
    ) -> Dict[str, Any]:
        """
        Translates a calibrated screenplay segment and character casting into
        a provider-native synthesis payload.
        """
        pass

    @abstractmethod
    def get_provider_capabilities(self) -> ProviderCapabilities:
        """Returns the capabilities manifest for this provider."""
        pass
