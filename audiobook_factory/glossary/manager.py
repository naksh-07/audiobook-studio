#!/usr/bin/env python3
"""
Audiobook Factory - Room 1.5: Unified Glossary Manager.
=======================================================
The primary production facade for Room 1.5:
1. Performs single-pass chapter pre-scanning and Tri-Partite taxonomy classification.
2. Synchronizes newly discovered entities with BookBible (book_bible.json) and
   NovelStateMaintainer voice casting (cast_lock.json, voice_registry.json).
3. Produces deterministic, durable ChapterGlossary artifacts (chapter_XXX_glossary.json).
4. Exports tailor-made metadata slices for Room 2 Translation, Room 3 Dramaturgy,
   and Room 3 Screenplay Attribution.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union

from audiobook_factory.logger import logger
from audiobook_factory.metadata.book_bible import BookBible, BookEntity, EpistemicProvenance
from audiobook_factory.metadata.state_maintainer import NovelStateMaintainer
from audiobook_factory.glossary.contracts import ChapterGlossary, ChapterEntity
from audiobook_factory.glossary.scanner import ChapterLexicalScanner, CandidateEntity
from audiobook_factory.glossary.classifier import GlossaryClassifier


class GlossaryManager:
    """
    Central Coordinator for Chapter-Level Glossary, Metadata & Entity Synchronization.
    """

    @classmethod
    def scan_and_sync_chapter(
        cls,
        chapter_text: str,
        project_dir: Optional[Union[Path, str]] = None,
        chapter_num: int = 1,
        chapter_id: Optional[str] = None,
        book_bible: Optional[BookBible] = None,
        call_llm_fn: Optional[Callable[..., Any]] = None,
        min_frequency: int = 2,
        force_classification: bool = False,
    ) -> ChapterGlossary:
        """
        Executes single-pass chapter lexical analysis:
        1. Fast zero-token regex scan against known lexicon in BookBible.
        2. Dispatches uncataloged candidates to GlossaryClassifier via ModelGateway.
        3. Updates BookBible, dynamic voice allocation (cast_lock.json), and persists state.
        4. Writes durable chapter glossary artifact: glossary/chapter_XXX_glossary.json.
        """
        p_dir = Path(project_dir).resolve() if project_dir else None
        active_bible = book_bible

        # Load BookBible if not provided
        if active_bible is None and p_dir:
            try:
                active_bible = BookBible.load_from_project(p_dir)
            except Exception as e:
                logger.warning(f"  [!] Notice loading BookBible in GlossaryManager: {e}")

        if active_bible is None:
            active_bible = BookBible(book_title=p_dir.name if p_dir else "Untitled")

        # 1. Zero-Token Regex Sweep
        candidates = ChapterLexicalScanner.scan_chapter_text(
            text=chapter_text,
            book_bible=active_bible,
            min_frequency=min_frequency,
        )

        discovered_entities: List[ChapterEntity] = []
        new_locations: Dict[str, str] = {}
        new_terminology: Dict[str, str] = {}

        # 2. LLM Classification (Bypassed if 0 unknown candidates and not forced)
        if candidates or force_classification:
            known_chars = list(active_bible.characters.keys())
            discovered_entities, new_locations, new_terminology = GlossaryClassifier.classify_candidates(
                candidates=candidates,
                chapter_text=chapter_text,
                chapter_num=chapter_num,
                known_characters=known_chars,
                call_llm_fn=call_llm_fn,
            )

        # 3. Synchronize with BookBible and Alias Unification
        for d_ent in discovered_entities:
            eng_name = d_ent.english_name
            hin_name = d_ent.hindi_name

            # Check if this name matches an existing character or alias (accent-insensitive)
            import unicodedata
            def _strip(s: str) -> str:
                return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()

            matched_key: Optional[str] = None
            clean_eng = _strip(eng_name)
            for ex_name, ex_ent in active_bible.characters.items():
                ex_clean = _strip(ex_name)
                ex_aliases_clean = [_strip(a) for a in ex_ent.aliases]
                if clean_eng == ex_clean or clean_eng in ex_aliases_clean:
                    matched_key = ex_name
                    break
                for alias in d_ent.aliases:
                    al_clean = _strip(alias)
                    if al_clean == ex_clean or al_clean in ex_aliases_clean:
                        matched_key = ex_name
                        break
                if matched_key:
                    break

            if matched_key:
                # Character already known: authoritative BookBible takes precedence over candidate classification
                target_ent = active_bible.characters[matched_key]
                if target_ent.hindi_name:
                    d_ent.hindi_name = target_ent.hindi_name
                d_ent.english_name = target_ent.english_name
                d_ent.canonical_id = target_ent.canonical_id
                current_aliases = set(target_ent.aliases)
                for a in d_ent.aliases:
                    current_aliases.add(a)
                if eng_name != matched_key:
                    current_aliases.add(eng_name)
                target_ent.aliases = sorted(list(current_aliases))
                # Update ChapterEntity with unified aliases
                d_ent.aliases = target_ent.aliases
            else:
                # Brand new character discovered: register in BookBible
                new_book_ent = BookEntity(
                    canonical_id=d_ent.canonical_id,
                    english_name=eng_name,
                    hindi_name=hin_name,
                    aliases=d_ent.aliases,
                    category="character",
                    gender=d_ent.gender,
                    description=d_ent.voice_style,
                    sociolect_archetype=d_ent.sociolect_archetype,
                    first_appearance_chapter=chapter_num,
                    confidence=d_ent.confidence,
                    provenance=EpistemicProvenance(
                        origin="CORPUS_EXTRACTED",
                        evidence_quote=f"Discovered in Chapter {chapter_num}",
                    ),
                    is_canonical=True,
                )
                active_bible.characters[eng_name] = new_book_ent

        # Update locations and terminology
        active_bible.locations.update(new_locations)
        active_bible.terminology.update(new_terminology)

        # 4. Synchronize Dynamic Voice Allocation (Room 4 Cast Lock)
        if p_dir:
            try:
                for c_name, c_ent in active_bible.characters.items():
                    NovelStateMaintainer.discover_and_lock_character(
                        project_dir=p_dir,
                        speaker_name=c_name,
                        gender=c_ent.gender,
                        book_bible=active_bible,
                    )
                    # Also lock Hindi moniker if distinct
                    h_name = c_ent.hindi_name or c_name
                    if h_name != c_name:
                        NovelStateMaintainer.discover_and_lock_character(
                            project_dir=p_dir,
                            speaker_name=h_name,
                            gender=c_ent.gender,
                            book_bible=active_bible,
                        )
            except Exception as e:
                logger.warning(f"  [!] Notice during cast_lock voice allocation in GlossaryManager: {e}")

            # Atomically save updated BookBible
            try:
                active_bible.save(p_dir)
            except Exception as e:
                logger.warning(f"  [!] Notice saving BookBible in GlossaryManager: {e}")

        # 5. Build ChapterGlossary model
        # Collect active characters present in this chapter
        chapter_entities_map: Dict[str, ChapterEntity] = {}

        # Include newly discovered entities
        for d_ent in discovered_entities:
            chapter_entities_map[d_ent.english_name] = d_ent

        # Also include previously known characters mentioned in this chapter text
        for c_name, c_ent in active_bible.characters.items():
            if c_name not in chapter_entities_map:
                # Check if mentioned in chapter text
                name_found = c_name in chapter_text or (c_ent.hindi_name and c_ent.hindi_name in chapter_text)
                if not name_found and c_ent.aliases:
                    name_found = any(a in chapter_text for a in c_ent.aliases)
                if name_found:
                    chapter_entities_map[c_name] = ChapterEntity(
                        canonical_id=c_ent.canonical_id,
                        english_name=c_name,
                        hindi_name=c_ent.hindi_name or c_name,
                        aliases=c_ent.aliases,
                        gender=c_ent.gender,  # type: ignore
                        voice_style=c_ent.description or "",
                        sociolect_archetype=c_ent.sociolect_archetype or "NEUTRAL",
                        confidence=c_ent.confidence,
                        first_appearance_chapter=c_ent.first_appearance_chapter,
                    )

        chap_slug = chapter_id or f"chapter_{chapter_num:03d}"
        chapter_glossary = ChapterGlossary(
            chapter_num=chapter_num,
            chapter_id=chap_slug,
            entities=chapter_entities_map,
            locations=dict(active_bible.locations),
            terminology=dict(active_bible.terminology),
        )

        # 6. Save chapter glossary artifact
        if p_dir:
            glossary_dir = p_dir / "glossary"
            glossary_dir.mkdir(parents=True, exist_ok=True)
            art_file = glossary_dir / f"{chap_slug}_glossary.json"
            chapter_glossary.save_to_file(art_file)
            logger.info(f"  [+] Chapter glossary persisted -> {art_file.name} ({chapter_glossary.total_entities} terms)")

        return chapter_glossary

    @classmethod
    def get_chapter_glossary(
        cls,
        chapter_num: int,
        project_dir: Union[Path, str],
    ) -> Optional[ChapterGlossary]:
        """Loads existing chapter glossary artifact from disk if present."""
        p_dir = Path(project_dir).resolve()
        glossary_file = p_dir / "glossary" / f"chapter_{chapter_num:03d}_glossary.json"
        if glossary_file.exists():
            try:
                return ChapterGlossary.load_from_file(glossary_file)
            except Exception as e:
                logger.warning(f"Notice reading {glossary_file.name}: {e}")
        return None

    @classmethod
    def export_for_translation(
        cls,
        chapter_num: int,
        project_dir: Union[Path, str],
        chapter_text: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Exports a flat English -> Hindi translation glossary for
        TranslationRequest.dynamic_glossary.
        """
        cg = cls.get_chapter_glossary(chapter_num, project_dir)
        if cg is not None:
            return cg.to_translation_glossary()

        # Fallback to scanning on-the-fly if chapter_text provided
        if chapter_text:
            cg = cls.scan_and_sync_chapter(
                chapter_text=chapter_text,
                project_dir=project_dir,
                chapter_num=chapter_num,
            )
            return cg.to_translation_glossary()

        # Fallback to project BookBible
        p_dir = Path(project_dir).resolve()
        try:
            bible = BookBible.load_from_project(p_dir)
            return bible.export_legacy_glossary().get("locations_and_terms", {})
        except Exception:
            return {}

    @classmethod
    def export_for_scripting(
        cls,
        chapter_num: int,
        project_dir: Union[Path, str],
        use_hindi: bool = True,
    ) -> Dict[str, Any]:
        """
        Exports structured character_roster schema consumed by
        DialogueAttributionAuditor and dialogue_parser.
        """
        cg = cls.get_chapter_glossary(chapter_num, project_dir)
        if cg is not None:
            return cg.to_scripting_roster(use_hindi=use_hindi)

        # Fallback to character_roster.json on project root
        p_dir = Path(project_dir).resolve()
        roster_file = p_dir / "character_roster.json"
        if roster_file.exists():
            try:
                return json.loads(roster_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"characters": {}}
