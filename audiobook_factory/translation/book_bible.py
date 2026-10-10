#!/usr/bin/env python3
"""
Audiobook Factory - Translation Book Bible Backward Compatibility Layer.
Re-exports canonical BookBible, BookEntity, NovelEntity, and provenance models
from the neutral audiobook_factory.metadata.book_bible package.
Guarantees 100% backward compatibility for all translation modules and test suites.
"""

from audiobook_factory.metadata.book_bible import (
    EpistemicProvenance,
    BookEntity,
    CharacterEntry,
    NovelEntity,
    DynamicRelationship,
    WorldRule,
    FlaggedConflict,
    BookBible,
)

__all__ = [
    "EpistemicProvenance",
    "BookEntity",
    "CharacterEntry",
    "NovelEntity",
    "DynamicRelationship",
    "WorldRule",
    "FlaggedConflict",
    "BookBible",
]
