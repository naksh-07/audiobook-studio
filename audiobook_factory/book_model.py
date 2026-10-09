#!/usr/bin/env python3
"""
Audiobook Studio - Legacy Facade for Book Model AST.
Maintains 100% backward compatibility by re-exporting canonical symbols
from the standalone audiobook_factory.extraction.contracts module.
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

__all__ = [
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
]
