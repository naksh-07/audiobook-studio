from __future__ import annotations

"""
Compatibility shim for legacy imports.
Re-exports PDFEscalationEngine and GeminiVisionPDFExtractor from audiobook_factory.extraction.parsers.pdf.vision_extractor.
"""

from audiobook_factory.extraction.parsers.pdf.vision_extractor import (
    PDFEscalationEngine,
    GeminiVisionPDFExtractor,
)

__all__ = [
    "PDFEscalationEngine",
    "GeminiVisionPDFExtractor",
]
