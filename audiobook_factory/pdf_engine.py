#!/usr/bin/env python3
"""
Audiobook Studio - Legacy Facade for PDF Engine & Quality Analyzer.
Maintains 100% backward compatibility by re-exporting modular components
from the standalone audiobook_factory.extraction package.
"""

from __future__ import annotations

from audiobook_factory.extraction.parsers.pdf import (
    PDFTextSpan,
    PDFLayoutReconstructor,
    PageQualityAudit,
    ExtractionCandidateEvaluation,
    PDFQualityAnalyzer,
    PDFEscalationEngine,
    GeminiVisionPDFExtractor,
    _PDFPageSpanRecord,
    ForensicPDFEngine,
)
from audiobook_factory.extraction.contracts import (
    CanonicalBlock,
    CanonicalChapter,
    SourceProvenance,
    ConfidenceLevel,
)
from audiobook_factory.extraction.normalizer import clean_book_text, normalize_block_text
from audiobook_factory.extraction.segmenter import (
    CHAPTER_PATTERNS,
    COMBINED_CHAPTER_REGEX,
    segment_chapters_from_text,
    split_large_chapter_on_semantic_boundary,
)

__all__ = [
    "PDFTextSpan",
    "PDFLayoutReconstructor",
    "PageQualityAudit",
    "ExtractionCandidateEvaluation",
    "PDFQualityAnalyzer",
    "PDFEscalationEngine",
    "GeminiVisionPDFExtractor",
    "_PDFPageSpanRecord",
    "ForensicPDFEngine",
    "CanonicalBlock",
    "CanonicalChapter",
    "SourceProvenance",
    "ConfidenceLevel",
    "clean_book_text",
    "normalize_block_text",
    "CHAPTER_PATTERNS",
    "COMBINED_CHAPTER_REGEX",
    "segment_chapters_from_text",
    "split_large_chapter_on_semantic_boundary",
]
