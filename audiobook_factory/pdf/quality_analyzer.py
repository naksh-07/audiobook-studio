from __future__ import annotations

"""
Compatibility shim for legacy imports.
Re-exports PDFQualityAnalyzer from audiobook_factory.extraction.parsers.pdf.quality_analyzer.
"""

from audiobook_factory.extraction.parsers.pdf.quality_analyzer import (
    PDFQualityAnalyzer,
)

__all__ = ["PDFQualityAnalyzer"]
