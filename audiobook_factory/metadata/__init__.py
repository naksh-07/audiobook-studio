#!/usr/bin/env python3
"""
Audiobook Factory - Neutral Metadata & Canonical State Package.
===============================================================
Single authoritative source of truth for:
- BookBible, BookEntity, NovelEntity, EpistemicProvenance
- NovelStateMaintainer (Atomic multi-file persistence & NR-GATE-06 transactions)
- MasterPreProductionState
"""

from .book_bible import (
    BookBible,
    BookEntity,
    CharacterEntry,
    NovelEntity,
    EpistemicProvenance,
    DynamicRelationship,
    WorldRule,
    FlaggedConflict,
)
from .state_maintainer import (
    NovelStateMaintainer,
    MasterPreProductionState,
)
from .doctor import (
    MetadataDoctor,
    MetadataDoctorReport,
    DiagnosticCheck,
)

__all__ = [
    "BookBible",
    "BookEntity",
    "CharacterEntry",
    "NovelEntity",
    "EpistemicProvenance",
    "DynamicRelationship",
    "WorldRule",
    "FlaggedConflict",
    "NovelStateMaintainer",
    "MasterPreProductionState",
    "MetadataDoctor",
    "MetadataDoctorReport",
    "DiagnosticCheck",
]
