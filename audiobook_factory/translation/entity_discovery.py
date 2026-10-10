#!/usr/bin/env python3
"""
Audiobook Factory - Translation Entity Discovery Compatibility Shim.
=====================================================================
NOTE: This module serves as a backward-compatible adapter.
The authoritative standalone implementation has moved to Room 1.5:
[`audiobook_factory.glossary`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/).

Exports:
- DiscoveredEntity
- EntityDiscoveryEngine
- ChapterEntityHarvester (delegates to GlossaryManager.scan_and_sync_chapter)
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
from pydantic import BaseModel, Field

from audiobook_factory.logger import logger
from audiobook_factory.metadata.book_bible import BookBible, BookEntity
from audiobook_factory.glossary import (
    GlossaryManager,
    ChapterLexicalScanner,
    GlossaryClassifier,
    CandidateEntity,
    ChapterEntity,
)


class DiscoveredEntity(BaseModel):
    """Legacy compatibility entity representation."""
    name: str
    category: str = "character"
    frequency: int = 1
    sample_context: str = ""
    suggested_devanagari: str = ""
    confidence: float = 0.85


class EntityDiscoveryEngine:
    """
    Backward-compatible entity discovery facade delegating to audiobook_factory.glossary.
    """

    @classmethod
    def discover_entities_from_text(
        cls,
        text: str,
        book_bible: BookBible,
        chapter_num: int = 1,
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> List[DiscoveredEntity]:
        """
        Discovers new potential entities in chapter text using ChapterLexicalScanner and GlossaryClassifier.
        """
        candidates = ChapterLexicalScanner.scan_chapter_text(
            text=text,
            book_bible=book_bible,
        )
        if not candidates:
            return []

        # Run classification
        known_chars = list(book_bible.characters.keys())
        classified_ents, locs, terms = GlossaryClassifier.classify_candidates(
            candidates=candidates,
            chapter_text=text,
            chapter_num=chapter_num,
            known_characters=known_chars,
            call_llm_fn=call_llm_fn,
        )

        results: List[DiscoveredEntity] = []
        c_map = {c.english_name: c for c in classified_ents}
        for cand in candidates:
            c_info = c_map.get(cand.name)
            suggested = c_info.hindi_name if c_info else (terms.get(cand.name) or locs.get(cand.name) or "")
            cat = c_info.category.lower() if c_info else cand.suggested_category
            conf = c_info.confidence if c_info else cand.confidence
            results.append(
                DiscoveredEntity(
                    name=cand.name,
                    category=cat,
                    frequency=cand.frequency,
                    sample_context=cand.sample_context,
                    suggested_devanagari=suggested,
                    confidence=conf,
                )
            )
        return results

    @classmethod
    def reconcile_and_commit(
        cls,
        discovered: List[DiscoveredEntity],
        book_bible: BookBible,
        chapter_num: int = 1,
    ) -> Tuple[int, int]:
        """
        Commits non-conflicting entities to BookBible.
        Returns (committed_count, flagged_count).
        """
        committed = 0
        flagged = 0

        for disc in discovered:
            entity = BookEntity(
                canonical_id=disc.name.lower().replace(" ", "_"),
                english_name=disc.name,
                hindi_name=disc.suggested_devanagari or disc.name,
                category=disc.category,
                first_appearance_chapter=chapter_num,
                confidence=disc.confidence,
                is_canonical=disc.confidence >= 0.8,
            )
            success = book_bible.propose_new_entity(entity, chapter_num)
            if success:
                committed += 1
            else:
                flagged += 1

        return committed, flagged


class ChapterEntityHarvester:
    """
    Legacy compatibility adapter delegating to GlossaryManager.
    """

    @classmethod
    def harvest_and_sync(
        cls,
        chapter_text: str,
        project_dir: Optional[Any] = None,
        chapter_num: int = 1,
        global_glossary: Optional[Dict[str, Any]] = None,
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes single-pass chapter pre-scanning via GlossaryManager.
        Synchronizes BookBible and cast_lock.json, then returns legacy glossary dictionary.
        """
        p_dir = Path(project_dir).resolve() if project_dir else None
        bible: Optional[BookBible] = None
        if p_dir:
            try:
                bible = BookBible.load_from_project(p_dir)
            except Exception as e:
                logger.warning(f"  [!] Notice loading BookBible in ChapterEntityHarvester: {e}")

        if bible is None:
            bible = BookBible()
            if global_glossary:
                bible.import_from_legacy_glossary(global_glossary)

        # Skip LLM if text is empty or offline without mock function
        is_mock_offline = os.environ.get("MOCK_OFFLINE", "").lower() in ("true", "1")
        if not chapter_text.strip() or (is_mock_offline and not call_llm_fn):
            return bible.export_legacy_glossary()

        # Delegate chapter scan and synchronization to GlossaryManager
        GlossaryManager.scan_and_sync_chapter(
            chapter_text=chapter_text,
            project_dir=p_dir,
            chapter_num=chapter_num,
            book_bible=bible,
            call_llm_fn=call_llm_fn,
            force_classification=True,
        )

        # Reload updated BookBible to export full legacy glossary
        if p_dir:
            try:
                bible = BookBible.load_from_project(p_dir)
            except Exception:
                pass

        return bible.export_legacy_glossary()
