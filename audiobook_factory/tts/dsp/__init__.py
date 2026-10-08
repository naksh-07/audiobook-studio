#!/usr/bin/env python3
"""
Audiobook Factory - TTS Editorial DSP Subsystem.
Exports EditorialDSPEngine, HannFadeProcessor, NetSilenceProcessor, ZeroCrossingAligner.
"""

from audiobook_factory.tts.dsp.editorial import (
    EditorialDSPEngine,
    HannFadeProcessor,
    NetSilenceProcessor,
    ZeroCrossingAligner,
)

__all__ = [
    "EditorialDSPEngine",
    "HannFadeProcessor",
    "NetSilenceProcessor",
    "ZeroCrossingAligner",
]
