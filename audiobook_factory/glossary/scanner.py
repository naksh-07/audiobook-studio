#!/usr/bin/env python3
"""
Audiobook Factory - Room 1.5: Chapter Lexical Scanner.
======================================================
High-speed, zero-token regex lexical scanner for chapter text.
Discovers emerging capitalized entities, heraldic monikers, and proper nouns
while filtering English discourse markers and sentence-starter stopwords.
Compares candidates against BookBible canonical lexicon to isolate new entities.
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Set, Optional
from pydantic import BaseModel, Field

from audiobook_factory.metadata.book_bible import BookBible


ENGLISH_NON_ENTITY_STOPWORDS: Set[str] = {
    "The", "He", "She", "They", "Then", "After", "There", "When", "What", "It", "In", "On", "At",
    "Are", "Yes", "Do", "You", "Who", "No", "That", "As", "Your", "Well", "And", "So", "Ah",
    "Greetings", "How", "History", "This", "Not", "Something", "But", "If", "To", "Become",
    "Why", "Where", "Which", "Can", "Could", "Would", "Should", "May", "Might", "Must",
    "Never", "Always", "Sometimes", "Perhaps", "Maybe", "Here", "Now", "Only", "Just",
    "All", "Some", "One", "Two", "My", "Our", "His", "Her", "Its", "Their", "We", "I",
    "Sit", "Let", "Geography", "Because", "Certainly", "Civilization", "Stories", "True",
    "Nonsense", "Instead", "Either", "Another", "Whatever", "Notice", "Nothing", "Someone",
    "Everybody", "Nobody", "Anyway", "Obviously", "Forgive", "Wait", "Look", "Listen", "Come",
    "Tonight", "Tomorrow", "Yesterday", "Suddenly", "Meanwhile", "Finally", "Soon", "Later",
    "Once", "Twice", "First", "Second", "Third", "Next", "Last", "Every", "Each", "Both",
    "Neither", "Many", "Much", "Few", "Several", "Enough", "Good", "Bad", "Great", "Little",
}


class CandidateEntity(BaseModel):
    """Raw entity candidate extracted from chapter text prior to LLM classification."""
    name: str
    frequency: int = 1
    sample_context: str = ""
    suggested_category: str = "character"
    confidence: float = 0.85
    is_multiword: bool = False
    has_mid_sentence: bool = False


class ChapterLexicalScanner:
    """
    Zero-token lexical extraction engine for chapter text.
    """

    @classmethod
    def scan_chapter_text(
        cls,
        text: str,
        known_lexicon: Optional[Set[str]] = None,
        book_bible: Optional[BookBible] = None,
        min_frequency: int = 2,
    ) -> List[CandidateEntity]:
        """
        Scans chapter text for uncataloged capitalized noun phrases and monikers.
        Filters known entities from book_bible / known_lexicon.
        Returns a list of uncataloged candidate entities.
        """
        if not text or not text.strip():
            return []

        # Build combined set of known names and terms to exclude
        active_known: Set[str] = set()
        if known_lexicon:
            active_known.update(k.lower() for k in known_lexicon)
        if book_bible:
            for c_name, c_ent in book_bible.characters.items():
                active_known.add(c_name.lower())
                active_known.update(a.lower() for a in c_ent.aliases)
            active_known.update(loc.lower() for loc in book_bible.locations.keys())
            active_known.update(term.lower() for term in book_bible.terminology.keys())

        # Regex matching 1 to 3 capitalized words, optionally with connective particles (of, de, van)
        matches = re.findall(
            r"\b[A-Z][a-z]+(?:\s+(?:of|de|the|van|[A-Z][a-z]+)){0,2}\b",
            text,
        )

        freq_map: Dict[str, int] = {}
        for m in matches:
            m_clean = m.strip()
            # Strip leading articles like 'The ' or 'A ' from multi-word candidates (e.g. 'The Night Raven' -> 'Night Raven')
            if m_clean.startswith("The ") and len(m_clean.split()) > 1:
                m_clean = m_clean[4:].strip()
            elif m_clean.startswith("A ") and len(m_clean.split()) > 1:
                m_clean = m_clean[2:].strip()

            if m_clean in ENGLISH_NON_ENTITY_STOPWORDS:
                continue
            if m_clean.lower() in active_known:
                continue
            freq_map[m_clean] = freq_map.get(m_clean, 0) + 1

        candidates: List[CandidateEntity] = []
        for name, count in freq_map.items():
            if count >= min_frequency:
                words = name.split()
                is_multi = len(words) > 1
                # Check if appearance occurs mid-sentence (not solely at line or sentence starts)
                has_mid = bool(re.search(rf"(?<![.!?\"\n\r])\s+\b{re.escape(name)}\b", text))

                # Positional confidence scoring
                if is_multi or has_mid:
                    conf = 0.85
                else:
                    conf = 0.50

                # Context snippet around first mid-sentence occurrence
                sample_ctx = ""
                m_ctx = re.search(rf"(?:[^\n.!?]+[.!?]){{0,1}}[^\n]*\b{re.escape(name)}\b[^\n]*(?:[.!?][^\n.!?]+){{0,1}}", text)
                if m_ctx:
                    sample_ctx = m_ctx.group(0).strip()[:200]

                category = "character"
                name_lower = name.lower()
                if any(w in name_lower for w in ("mountain", "valley", "city", "river", "kingdom", "tavern", "inn", "castle", "tower", "gate")):
                    category = "location"
                elif any(w in name_lower for w in ("order", "guild", "clan", "brotherhood", "empire", "guard")):
                    category = "faction"

                candidates.append(
                    CandidateEntity(
                        name=name,
                        frequency=count,
                        sample_context=sample_ctx,
                        suggested_category=category,
                        confidence=conf,
                        is_multiword=is_multi,
                        has_mid_sentence=has_mid,
                    )
                )

        return sorted(candidates, key=lambda c: (-c.frequency, c.name))
