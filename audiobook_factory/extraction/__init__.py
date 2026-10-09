#!/usr/bin/env python3
"""
Audiobook Studio - Pillar 1: Forensic Document Extraction Subsystem.
Transforms EPUB, PDF, Plain Text, and Markdown documents into CanonicalBook AST representations
with character-accurate forensic provenance, non-destructive normalization, chapter segmentation,
and fail-closed Quality Gate 0.1 auditing.
"""

from __future__ import annotations

from audiobook_factory.extraction.contracts import (
    BlockType,
    ConfidenceLevel,
    GateStatus,
    UnitType,
    BoundaryOrigin,
    ExtractionGateAuditError,
    SourceProvenance,
    CanonicalBlock,
    CanonicalChapter,
    ExtractionQualityReport,
    CanonicalBook,
)
from audiobook_factory.extraction.normalizer import (
    UNICODE_SPACES,
    ZERO_WIDTH_CHARS,
    CONTROL_CHARS_RE,
    PUNCTUATION_REPLACEMENTS,
    clean_book_text,
    normalize_block_text,
    TextNormalizer,
)
from audiobook_factory.extraction.segmenter import (
    CHAPTER_PATTERNS,
    COMBINED_CHAPTER_REGEX,
    is_valid_heading_candidate,
    segment_chapters_from_text,
    split_large_chapter_on_semantic_boundary,
    ChapterSegmenter,
)
from audiobook_factory.extraction.quality_gate import ExtractionQualityAuditor
from audiobook_factory.extraction.parsers.epub import (
    ForensicEPUBParser,
    EPUBStructuralHTMLParser,
    extract_epub,
)
from audiobook_factory.extraction.parsers.text import (
    PlainTextParser,
    MarkdownParser,
)
from audiobook_factory.extraction.parsers.pdf import (
    ForensicPDFEngine,
    PDFLayoutReconstructor,
    PDFQualityAnalyzer,
    GeminiVisionPDFExtractor,
    PDFEscalationEngine,
    PDFTextSpan,
    PageQualityAudit,
    ExtractionCandidateEvaluation,
)
from audiobook_factory.extraction.engine import (
    ExtractionEngine,
    process_book_file,
    extract_chapters,
    extract_gemini_pdf,
    compute_sha256,
)

__all__ = [
    # Contracts & AST
    "BlockType",
    "ConfidenceLevel",
    "GateStatus",
    "UnitType",
    "BoundaryOrigin",
    "ExtractionGateAuditError",
    "SourceProvenance",
    "CanonicalBlock",
    "CanonicalChapter",
    "ExtractionQualityReport",
    "CanonicalBook",
    # Normalizer
    "UNICODE_SPACES",
    "ZERO_WIDTH_CHARS",
    "CONTROL_CHARS_RE",
    "PUNCTUATION_REPLACEMENTS",
    "clean_book_text",
    "normalize_block_text",
    "TextNormalizer",
    # Segmenter
    "CHAPTER_PATTERNS",
    "COMBINED_CHAPTER_REGEX",
    "is_valid_heading_candidate",
    "segment_chapters_from_text",
    "split_large_chapter_on_semantic_boundary",
    "ChapterSegmenter",
    # Quality Gate
    "ExtractionQualityAuditor",
    # Parsers
    "ForensicEPUBParser",
    "EPUBStructuralHTMLParser",
    "extract_epub",
    "PlainTextParser",
    "MarkdownParser",
    "ForensicPDFEngine",
    "PDFLayoutReconstructor",
    "PDFQualityAnalyzer",
    "GeminiVisionPDFExtractor",
    "PDFEscalationEngine",
    "PDFTextSpan",
    "PageQualityAudit",
    "ExtractionCandidateEvaluation",
    # Core Engine & Entry Points
    "ExtractionEngine",
    "process_book_file",
    "extract_chapters",
    "extract_gemini_pdf",
    "compute_sha256",
]
