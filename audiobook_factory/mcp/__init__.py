#!/usr/bin/env python3
"""
Audiobook Factory - Antigravity MCP Suite (v5.4).
Exposes studio vocal mastering, QA auditing, neural speech enhancement,
and reference spectrum matching as native tools for AI agents.
"""

from .server import (
    apply_vocal_dsp_tool,
    audit_audio_quality_tool,
    match_reference_spectrum_tool,
    enhance_vocal_stem_tool,
    measure_ebu_r128_loudness_tool,
    audit_chapter_qa_tool,
)

__all__ = [
    "apply_vocal_dsp_tool",
    "audit_audio_quality_tool",
    "match_reference_spectrum_tool",
    "enhance_vocal_stem_tool",
    "measure_ebu_r128_loudness_tool",
    "audit_chapter_qa_tool",
]
