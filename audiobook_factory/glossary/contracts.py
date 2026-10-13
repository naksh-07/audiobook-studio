#!/usr/bin/env python3
"""
Audiobook Factory - Room 1.5: Standalone Glossary & Chapter Metadata Contracts.
==============================================================================
Defines strongly-typed Pydantic v2 schemas for per-chapter lexical analysis,
Tri-Partite entity classification, alias unification, and multi-consumer
data projections (Translation, Dramaturgy, Scripting, and Voice Casting).
"""

from __future__ import annotations
import json
import uuid
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


EntityCategory = Literal[
    "PROPER_NAME",
    "HERALDIC_MONIKER",
    "OCCUPATIONAL_ROLE",
    "LOCATION",
    "LORE_TERM",
]


class ChapterEntity(BaseModel):
    """
    Standardized entity record discovered in chapter text.
    """
    model_config = ConfigDict(extra="ignore")

    canonical_id: str = Field(..., description="Unique snake_case identifier (e.g. 'lord_corwin')")
    english_name: str = Field(..., description="Canonical English name or moniker")
    hindi_name: str = Field(..., description="Phonetic Devanagari transliteration or evocative Hindustani translation")
    category: EntityCategory = Field(default="PROPER_NAME", description="Tri-Partite entity classification")
    aliases: List[str] = Field(default_factory=list, description="All situational nicknames, aliases, and titles")
    gender: Literal["male", "female"] = Field(default="male")
    voice_style: str = Field(default="", description="Descriptive vocal acting hint or acoustic demeanor")
    sociolect_archetype: str = Field(default="NEUTRAL", description="Hindustani dialect/social register archetype")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    first_appearance_chapter: int = Field(default=1, ge=1)
    is_canonical: bool = Field(default=True)


class ChapterGlossary(BaseModel):
    """
    Immutable, self-contained glossary snapshot for a single chapter.
    Serves as the single source of truth for:
    - Room 2 (Translation): dynamic_glossary (en -> hi dictionary)
    - Room 3 (Dramaturgy): scene characters & known entity list
    - Room 3 (Scripting): character_roster.json with unified aliases
    - Room 4 (Voice Casting): cast_lock sync candidates
    """
    model_config = ConfigDict(extra="ignore")

    chapter_num: int = Field(..., ge=0, description="1-indexed chapter number (0 for front matter)")
    chapter_id: str = Field(default="", description="Chapter identifier slug (e.g. 'chapter_004')")
    entities: Dict[str, ChapterEntity] = Field(default_factory=dict, description="Active character and person entities")
    locations: Dict[str, str] = Field(default_factory=dict, description="English location name -> Devanagari translation")
    terminology: Dict[str, str] = Field(default_factory=dict, description="English fantasy/lore term -> Devanagari translation")
    version_hash: str = Field(default="", description="Deterministic SHA-256 fingerprint of glossary content")
    total_entities: int = Field(default=0)

    def model_post_init(self, __context: Any) -> None:
        if not self.total_entities:
            self.total_entities = len(self.entities) + len(self.locations) + len(self.terminology)
        if not self.version_hash:
            self.version_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Computes a deterministic 16-char SHA-256 fingerprint of the glossary content."""
        data = {
            "chapter_num": self.chapter_num,
            "entities": {k: v.model_dump() for k, v in sorted(self.entities.items())},
            "locations": dict(sorted(self.locations.items())),
            "terminology": dict(sorted(self.terminology.items())),
        }
        raw_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()[:16]

    def to_translation_glossary(self) -> Dict[str, str]:
        """
        Projects glossary into a clean English -> Hindi mapping
        for TranslationRequest.dynamic_glossary.
        """
        glossary: Dict[str, str] = {}
        # 1. Locations
        glossary.update(self.locations)
        # 2. Terminology
        glossary.update(self.terminology)
        # 3. Characters & Heraldic Monikers
        import unicodedata
        for c_name, c_ent in self.entities.items():
            if c_ent.hindi_name:
                glossary[c_name] = c_ent.hindi_name
                norm_c = "".join(c for c in unicodedata.normalize("NFD", c_name) if unicodedata.category(c) != "Mn")
                if norm_c and norm_c not in glossary:
                    glossary[norm_c] = c_ent.hindi_name
                # Also map aliases if they have clean mappings
                for a in c_ent.aliases:
                    if a and a not in glossary:
                        glossary[a] = c_ent.hindi_name
                        norm_a = "".join(c for c in unicodedata.normalize("NFD", a) if unicodedata.category(c) != "Mn")
                        if norm_a and norm_a not in glossary:
                            glossary[norm_a] = c_ent.hindi_name
        return glossary

    def to_scripting_roster(self, use_hindi: bool = True) -> Dict[str, Any]:
        """
        Projects glossary into standard character_roster schema
        consumed by DialogueAttributionAuditor and dialogue_parser.
        Ensures unified alias maps prevent false speaker flips.
        """
        roster_chars: Dict[str, Any] = {}
        for c_name, c_ent in self.entities.items():
            primary_key = c_ent.hindi_name if (use_hindi and c_ent.hindi_name) else c_name
            alias_list = set(c_ent.aliases)
            alias_list.add(c_name)
            if c_ent.hindi_name:
                alias_list.add(c_ent.hindi_name)

            roster_chars[primary_key] = {
                "aliases": sorted(list(alias_list)),
                "gender": c_ent.gender,
                "voice_style": c_ent.voice_style,
                "sociolect_archetype": c_ent.sociolect_archetype,
                "category": c_ent.category,
            }
        return {"characters": roster_chars}

    def to_dramaturgy_characters(self) -> List[str]:
        """Returns list of all active character names for scene segmentation."""
        names = set(self.entities.keys())
        for c_ent in self.entities.values():
            if c_ent.hindi_name:
                names.add(c_ent.hindi_name)
            names.update(c_ent.aliases)
        return sorted(list(names))

    def save_to_file(self, path: Path | str) -> None:
        """Atomically persists glossary to JSON on disk."""
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(f".tmp_glo_{uuid.uuid4().hex[:8]}")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(self.model_dump_json(indent=2))
            tmp.replace(p)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    @classmethod
    def load_from_file(cls, path: Path | str) -> ChapterGlossary:
        """Loads glossary from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)
