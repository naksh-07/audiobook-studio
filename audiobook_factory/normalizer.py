#!/usr/bin/env python3
"""
Audiobook Studio - Legacy Facade for Literary Normalizer.
Maintains 100% backward compatibility by re-exporting canonical symbols
from the standalone audiobook_factory.extraction.normalizer module.
"""

from __future__ import annotations

from audiobook_factory.extraction.normalizer import (
    ZERO_WIDTH_CHARS,
    CONTROL_CHARS_RE,
    UNICODE_SPACES,
    PUNCTUATION_REPLACEMENTS,
    clean_book_text,
    normalize_block_text,
    TextNormalizer,
)

__all__ = [
    "ZERO_WIDTH_CHARS",
    "CONTROL_CHARS_RE",
    "UNICODE_SPACES",
    "PUNCTUATION_REPLACEMENTS",
    "clean_book_text",
    "normalize_block_text",
    "TextNormalizer",
]
