#!/usr/bin/env python3
"""
Audiobook Studio - Legacy Facade for Document Extractor.
Maintains 100% backward compatibility by re-exporting canonical symbols
from the standalone audiobook_factory.extraction.engine module.
"""

from __future__ import annotations

from audiobook_factory.extraction.engine import (
    ExtractionEngine,
    process_book_file,
    extract_chapters,
    extract_gemini_pdf,
    compute_sha256,
)
from audiobook_factory.extraction.contracts import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalBlock,
    SourceProvenance,
    ExtractionQualityReport,
    ExtractionGateAuditError,
)
from audiobook_factory.extraction.normalizer import clean_book_text, normalize_block_text
from audiobook_factory.extraction.parsers.epub import (
    ForensicEPUBParser,
    EPUBStructuralHTMLParser,
    extract_epub,
)
from audiobook_factory.extraction.parsers.pdf import (
    ForensicPDFEngine,
    GeminiVisionPDFExtractor,
    PDFQualityAnalyzer,
    PageQualityAudit,
)
from audiobook_factory.extraction.segmenter import (
    segment_chapters_from_text,
    split_large_chapter_on_semantic_boundary,
)
from audiobook_factory.extraction.quality_gate import ExtractionQualityAuditor

# Legacy alias for backward compatibility
TextHTMLParser = EPUBStructuralHTMLParser

__all__ = [
    "ExtractionEngine",
    "process_book_file",
    "extract_chapters",
    "extract_gemini_pdf",
    "compute_sha256",
    "CanonicalBook",
    "CanonicalChapter",
    "CanonicalBlock",
    "SourceProvenance",
    "ExtractionQualityReport",
    "ExtractionGateAuditError",
    "clean_book_text",
    "normalize_block_text",
    "ForensicEPUBParser",
    "EPUBStructuralHTMLParser",
    "extract_epub",
    "ForensicPDFEngine",
    "GeminiVisionPDFExtractor",
    "PDFQualityAnalyzer",
    "PageQualityAudit",
    "segment_chapters_from_text",
    "split_large_chapter_on_semantic_boundary",
    "ExtractionQualityAuditor",
    "TextHTMLParser",
]
