#!/usr/bin/env python3
"""
Audiobook Factory - Room 1.5: Standalone Glossary & Chapter Metadata Package.
=============================================================================
Provides single-pass chapter pre-scanning, Tri-Partite taxonomy entity
classification, alias unification, and multi-consumer metadata delivery:
- Room 2 (Translation): dynamic_glossary (en -> hi map)
- Room 3 (Dramaturgy & Screenplay): unified character roster & alias maps
- Room 4 (Voice Casting): automated cast_lock.json dynamic sync
"""

from audiobook_factory.glossary.contracts import (
    EntityCategory,
    ChapterEntity,
    ChapterGlossary,
)
from audiobook_factory.glossary.scanner import (
    CandidateEntity,
    ChapterLexicalScanner,
    ENGLISH_NON_ENTITY_STOPWORDS,
)
from audiobook_factory.glossary.classifier import (
    GlossaryClassifier,
    TRI_PARTITE_SYSTEM_PROMPT,
)
from audiobook_factory.glossary.gateway_bridge import (
    execute_glossary_llm,
)
from audiobook_factory.glossary.manager import (
    GlossaryManager,
)

__all__ = [
    "EntityCategory",
    "ChapterEntity",
    "ChapterGlossary",
    "CandidateEntity",
    "ChapterLexicalScanner",
    "ENGLISH_NON_ENTITY_STOPWORDS",
    "GlossaryClassifier",
    "TRI_PARTITE_SYSTEM_PROMPT",
    "execute_glossary_llm",
    "GlossaryManager",
]
