#!/usr/bin/env python3
"""
Audiobook Studio - Pillar 1: Non-Destructive Literary Normalizer.
Provides high-fidelity text normalization for speech synthesis while preserving
sacred source text unmutated in the canonical layer.
"""

from __future__ import annotations
import html
import re
import unicodedata
from typing import Tuple, List, Dict


# U+200C (ZWNJ) and U+200D (ZWJ) are preserved for Indic conjuncts, eyelash-ra, and explicit halants
ZERO_WIDTH_CHARS = ("\u200b", "\ufeff", "\u2060", "\u00ad")
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

UNICODE_SPACES = (
    "\u00a0",  # Non-breaking space
    "\u1680",  # Ogham space mark
    "\u2000", "\u2001", "\u2002", "\u2003", "\u2004", "\u2005", "\u2006", "\u2007", "\u2008", "\u2009", "\u200a",  # En/Em/Thin/Hair
    "\u202f",  # Narrow no-break space
    "\u205f",  # Medium mathematical space
    "\u3000",  # Ideographic space
)

PUNCTUATION_REPLACEMENTS = {
    "\u2018": "'",   # Left single quote
    "\u2019": "'",   # Right single quote
    "\u201c": '"',   # Left double quote
    "\u201d": '"',   # Right double quote
    "\u2014": " — ", # Em dash
    "\u2013": " – ", # En dash
    "\u2026": "...", # Ellipsis
    "\r\n": "\n",
    "\r": "\n",
}


def clean_book_text(text: str, preserve_literary_quotes: bool = False) -> str:
    """
    Sanitize book text non-destructively for speech reading.
    Retains 100% backward compatibility for existing callers.
    
    Operations:
    0. Unicode NFC normalization, HTML entity unescaping & invisible zero-width/control character hygiene.
    1. Broken hyphenated linebreak healing (e.g. "impor-\\ntant" -> "important").
    2. Smart quote & dash normalization (unless preserve_literary_quotes is True).
    3. Safe footnote reference removal (e.g. "[1]", "[23]").
    4. Running headers/page number line stripping.
    5. Excessive whitespace collapsing.
    """
    if not text:
        return ""

    # 0. Unicode NFC normalization & invisible zero-width / C0-C1 control character hygiene
    text = unicodedata.normalize("NFC", text)
    for zw in ZERO_WIDTH_CHARS:
        text = text.replace(zw, "")
    text = CONTROL_CHARS_RE.sub("", text)

    # 0B. Decode unescaped HTML entities and normalize non-standard Unicode space variants
    if "&" in text:
        text = html.unescape(text)
    for sp in UNICODE_SPACES:
        text = text.replace(sp, " ")

    # 1. Fix broken hyphenated linebreaks across lines (ASCII, Accented Latin, Devanagari)
    text = re.sub(
        r"(\b[a-zA-Z\u00C0-\u024F\u1E00-\u1EFF\u0900-\u097F]{2,})-\n+([a-zA-Z\u00C0-\u024F\u1E00-\u1EFF\u0900-\u097F]{2,}\b)",
        r"\1\2",
        text,
    )

    # 2. Punctuation normalization
    if not preserve_literary_quotes:
        for orig, repl in PUNCTUATION_REPLACEMENTS.items():
            text = text.replace(orig, repl)
    else:
        text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Strip footnote reference marks (e.g. "[1]", "[23]") while preserving Sci-Fi/military coordinates (e.g. "Sector [4]", "Unit [12]")
    text = re.sub(
        r"(\b(?:sector|unit|level|grid|vault|protocol|section|gate|node|channel|sample|group|matrix|model|phase|tier|type|class|port|district|block|row|column|area|chapter|part|book)\s+)?\[\d{1,3}\]",
        lambda m: m.group(0) if m.group(1) else "",
        text,
        flags=re.IGNORECASE,
    )

    # 4. Remove common running headers/page number lines: e.g. "Page 42 of 300", "- 42 -"
    text = re.sub(r"^[\s\-\–—]*(?:page|pg\.|p\.)\s+\d+(?:\s+of\s+\d+)?[\s\-\–—]*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*[\-\–—~_]+\s*\d+\s*[\-\–—~_]+\s*$", "", text, flags=re.MULTILINE)

    # 5. Collapse excessive whitespace without wiping paragraph boundaries
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_block_text(raw_text: str, preserve_literary_quotes: bool = False) -> Tuple[str, List[str]]:
    """
    Normalizes a single literary block while recording any forensic warnings.
    Returns: (normalized_text, warnings)
    """
    if not raw_text:
        return "", []

    warnings: List[str] = []
    
    # Check for unhandled control or replacement characters
    if "\ufffd" in raw_text:
        warnings.append("Block contains Unicode replacement character (\\ufffd) indicating character decode defect.")
    if CONTROL_CHARS_RE.search(raw_text):
        warnings.append("Block contained ASCII/C1 control characters which were stripped during normalization.")

    # Check for excessive broken words
    hyphen_breaks = len(re.findall(r"\b\w+-\n+\w+\b", raw_text))
    if hyphen_breaks > 3:
        warnings.append(f"Block contained {hyphen_breaks} hyphenated line breaks healed.")

    normalized = clean_book_text(raw_text, preserve_literary_quotes=preserve_literary_quotes)
    return normalized, warnings


class TextNormalizer:
    """
    Class-based normalizer interface for pipeline components.
    """
    @classmethod
    def clean(cls, text: str, preserve_literary_quotes: bool = False) -> str:
        return clean_book_text(text, preserve_literary_quotes=preserve_literary_quotes)

    @classmethod
    def normalize_block(cls, raw_text: str, preserve_literary_quotes: bool = False) -> Tuple[str, List[str]]:
        return normalize_block_text(raw_text, preserve_literary_quotes=preserve_literary_quotes)
