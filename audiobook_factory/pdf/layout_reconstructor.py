from __future__ import annotations

"""
Compatibility shim for legacy imports.
Re-exports PDFLayoutReconstructor from audiobook_factory.extraction.parsers.pdf.layout_reconstructor.
"""

from audiobook_factory.extraction.parsers.pdf.layout_reconstructor import (
    PDFLayoutReconstructor,
)

__all__ = ["PDFLayoutReconstructor"]
