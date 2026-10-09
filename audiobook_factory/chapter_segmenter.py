#!/usr/bin/env python3
"""
Audiobook Studio - Legacy Facade for Chapter Segmenter.
Maintains 100% backward compatibility by re-exporting canonical symbols
from the standalone audiobook_factory.extraction.segmenter module.
"""

from __future__ import annotations

from audiobook_factory.extraction.segmenter import (
    CHAPTER_PATTERNS,
    COMBINED_CHAPTER_REGEX,
    is_valid_heading_candidate,
    segment_chapters_from_text,
    split_large_chapter_on_semantic_boundary,
    ChapterSegmenter,
)

__all__ = [
    "CHAPTER_PATTERNS",
    "COMBINED_CHAPTER_REGEX",
    "is_valid_heading_candidate",
    "segment_chapters_from_text",
    "split_large_chapter_on_semantic_boundary",
    "ChapterSegmenter",
]
