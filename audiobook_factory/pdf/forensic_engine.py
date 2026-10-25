from __future__ import annotations

"""
Compatibility shim for legacy imports.
Re-exports ForensicPDFEngine from audiobook_factory.extraction.parsers.pdf.forensic_engine.
"""

from audiobook_factory.extraction.parsers.pdf.forensic_engine import (
    ForensicPDFEngine,
)

__all__ = ["ForensicPDFEngine"]
