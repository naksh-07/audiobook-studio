#!/usr/bin/env python3
"""
Audiobook Studio - Legacy Facade for EPUB Parser.
Maintains 100% backward compatibility by re-exporting canonical symbols
from the standalone audiobook_factory.extraction.parsers.epub module.
"""

from __future__ import annotations

from audiobook_factory.extraction.parsers.epub import (
    EPUBStructuralHTMLParser,
    ForensicEPUBParser,
    extract_epub,
    _safe_xml_fromstring,
    _is_subsection_label,
    _flatten_nav_tree,
    NavItem,
    NavTarget,
)

__all__ = [
    "EPUBStructuralHTMLParser",
    "ForensicEPUBParser",
    "extract_epub",
    "_safe_xml_fromstring",
    "_is_subsection_label",
    "_flatten_nav_tree",
    "NavItem",
    "NavTarget",
]
