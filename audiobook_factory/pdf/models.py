from __future__ import annotations

"""
Compatibility shim for legacy imports.
Re-exports PDF models from audiobook_factory.extraction.parsers.pdf.models.
"""

from audiobook_factory.extraction.parsers.pdf.models import (
    PDFTextSpan,
    PageQualityAudit,
    ExtractionCandidateEvaluation,
    _PDFPageSpanRecord,
)

__all__ = [
    "PDFTextSpan",
    "PageQualityAudit",
    "ExtractionCandidateEvaluation",
    "_PDFPageSpanRecord",
]
