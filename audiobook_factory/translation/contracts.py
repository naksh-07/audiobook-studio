"""
Audiobook Factory - Translation Contracts & Data Models
======================================================
Defines strongly typed Pydantic models for the standalone, decoupled
literary translation subsystem (Option D Architecture).
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field


class FidelityTier(str, Enum):
    """Stylistic guidance tier for literary Hindustani translation."""
    RAW_UNRATED = "RAW_UNRATED"          # Mature dark fantasy, visceral combat, uncensored tavern slang
    CLASSIC_REVERENT = "CLASSIC_REVERENT"  # Heritage classics (Premchand, Tagore), dignified pathos, zero profanity


class TranslationRequest(BaseModel):
    """Input payload for a standalone translation request."""
    source_text: str = Field(..., description="Full raw source text of the chapter or document.")
    source_title: str = Field(default="", description="Optional title or chapter heading.")
    tier: FidelityTier = Field(default=FidelityTier.RAW_UNRATED, description="Stylistic guidance tier.")
    book_bible_path: Optional[str] = Field(default=None, description="Path to persistent book_bible.json.")
    dynamic_glossary: Dict[str, str] = Field(default_factory=dict, description="In-memory entity translations (en -> hi).")
    chunk_size_words: int = Field(default=1800, ge=500, le=3000, description="Target macro-chunk word count.")
    max_single_chunk_words: int = Field(default=2200, ge=1000, le=4000, description="Max word count to translate in 1 call.")
    thinking_budget: int = Field(default=1024, ge=0, le=4096, description="Gemini Flash internal deliberation budget.")
    source_language: str = Field(default="en", description="Source ISO language code.")
    target_language: str = Field(default="hi", description="Target ISO language code.")
    temperature: float = Field(default=0.35, ge=0.0, le=1.0, description="Sampling temperature.")
    playbook: Optional[Any] = Field(default=None, description="Optional ProductionPlaybook with novel-tailored prompt directives.")
    director_card: Optional[Any] = Field(default=None, description="Optional ChapterDirectorCard with chapter scene atmosphere & stakes.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional caller metadata.")



class ParagraphAlignment(BaseModel):
    """Bilingual sentence/paragraph alignment mapping for provenance and QA."""
    index: int = Field(..., description="0-indexed sequence number of the paragraph.")
    source_paragraph: str = Field(..., description="Source English paragraph text.")
    target_paragraph: str = Field(..., description="Target Hindi Devanagari paragraph text.")
    source_hash: str = Field(..., description="SHA-256 hash (first 16 hex chars) of source paragraph.")
    target_hash: str = Field(..., description="SHA-256 hash (first 16 hex chars) of target paragraph.")


class ParityMetrics(BaseModel):
    """Deterministic full-text parity verification metrics."""
    source_paragraph_count: int
    target_paragraph_count: int
    paragraph_parity_ratio: float
    source_quote_count: int
    target_quote_count: int
    quote_parity_ratio: float
    source_word_count: int
    target_word_count: int
    length_ratio: float
    source_negations_count: int
    target_negations_count: int
    passed_all_gates: bool
    rejection_reasons: List[str] = Field(default_factory=list)


class TranslationResult(BaseModel):
    """Output payload from the standalone translation engine."""
    translated_markdown: str = Field(..., description="Pristine Hindi Devanagari translation.")
    alignments: List[ParagraphAlignment] = Field(default_factory=list, description="Paragraph-level alignment map.")
    parity: ParityMetrics = Field(..., description="Deterministic full-text validation report.")
    new_entities_discovered: Dict[str, str] = Field(default_factory=dict, description="Extracted terminology additions.")
    total_chunks: int = 1
    llm_calls_made: int = 1
    elapsed_seconds: float = 0.0


# Default Gemini model used for text translation if not resolved dynamically
DEFAULT_TRANSLATION_MODEL: str = "gemini-3.8-flash"

