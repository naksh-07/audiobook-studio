#!/usr/bin/env python3
"""
Audiobook Factory - Universal TTS Input Guard.
Performs deterministic text normalization, NFC unicode cleanup, control-character stripping,
SSML and stage-cue extraction, numeral/currency phonetization, and produces immutable
CanonicalTTSRequest objects adhering to the Sacred Text vs. Spoken Text invariant.
"""

from __future__ import annotations
import re
import unicodedata
import uuid
from typing import Dict, Any, Optional, List, Tuple

from audiobook_factory.tts.contracts import CanonicalTTSRequest, DeliveryIntent, TTSPipelineMode
from audiobook_factory.tts.guard.numeral_expander import NumeralAndTokenExpander
from audiobook_factory.tts.guard.delivery_extractor import DeliveryIntentExtractor


class UniversalInputGuard:
    """
    Universal Input Guard Layer across all TTS generation pathways.
    Enforces that:
    1. Literary Text is preserved immutably (NFC normalized, no semantic alterations).
    2. Spoken Text is fully phonetized (Devanagari numerals, currency words, acronyms, zero leaked stage brackets).
    3. Delivery Intent is strongly-typed and extracted.
    4. Control characters and zero-width artifacts are eliminated.
    """

    # Control characters to strip: C0 control chars (excluding \t, \n, \r), delete (0x7F), zero-width chars
    CONTROL_CHAR_REGEX = re.compile(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b\u200c\u200d\ufeff\u00ad]"
    )

    # Maximum character limit for a single unchunked atomic TTS request
    MAX_ATOMIC_CHARS: int = 1500

    @classmethod
    def sanitize_and_guard(
        cls,
        raw_text: str,
        voice_id: str,
        segment_uid: Optional[str] = None,
        speaker: str = "Narrator",
        language: str = "hi-IN",
        temperature: float = 0.40,
        sample_rate: int = 24000,
        pipeline_mode: TTSPipelineMode = TTSPipelineMode.GENERIC,
        chapter_num: Optional[int] = None,
        scene_num: Optional[int] = None,
        default_intent: Optional[DeliveryIntent] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CanonicalTTSRequest:
        """
        Validates, normalizes, and transforms raw input text into a CanonicalTTSRequest.

        Raises:
            ValueError: If input text is empty or consists solely of whitespace.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("Input text cannot be empty or whitespace-only.")

        uid = segment_uid or f"seg_{uuid.uuid4().hex[:12]}"
        meta = dict(metadata or {})

        # 1. Unicode NFC Normalization and Control Character Scrubbing
        normalized_raw = unicodedata.normalize("NFC", raw_text)
        cleaned_raw = cls.CONTROL_CHAR_REGEX.sub("", normalized_raw)
        cleaned_raw = re.sub(r"[ \t]+", " ", cleaned_raw).strip()

        if not cleaned_raw:
            raise ValueError("Input text became empty after stripping control characters.")

        # 2. Extract Stage Directions, SSML tags, and Emotional Delivery Intent
        text_without_cues, extracted_intent, cue_meta = DeliveryIntentExtractor.extract_intent_and_clean_text(
            cleaned_raw, default_intent=default_intent
        )

        # 3. Phonetize Numerals, Currencies, Units, Roman Numerals, Acronyms
        spoken_phonetized, expansions = NumeralAndTokenExpander.expand_text(
            text_without_cues, language=language
        )

        # 4. Normalize Spoken Punctuation (collapse redundant punctuation without removing emotional cadence)
        spoken_text = cls._normalize_spoken_punctuation(spoken_phonetized)

        # 5. Determine Suggested Boundary Pauses
        pause_before_ms, pause_after_ms = cls._calculate_suggested_pauses(
            spoken_text, cue_meta.get("ssml_break_ms", 0), pipeline_mode
        )

        # 6. Check Length Thresholds
        if len(spoken_text) > cls.MAX_ATOMIC_CHARS and pipeline_mode == TTSPipelineMode.GENERIC:
            meta["length_warning"] = (
                f"Input text length ({len(spoken_text)} chars) exceeds recommended single-request "
                f"atomic limit ({cls.MAX_ATOMIC_CHARS} chars). Consider using LongFormTTSClient."
            )

        meta["numeral_expansions"] = expansions
        meta["extracted_cues_count"] = cue_meta.get("extracted_cues_count", 0)

        return CanonicalTTSRequest(
            segment_uid=uid,
            literary_text=cleaned_raw,
            spoken_text=spoken_text,
            voice_id=voice_id,
            language=language,
            speaker=speaker,
            delivery_intent=extracted_intent,
            temperature=temperature,
            sample_rate=sample_rate,
            pipeline_mode=pipeline_mode,
            chapter_num=chapter_num,
            scene_num=scene_num,
            suggested_pause_before_ms=pause_before_ms,
            suggested_pause_after_ms=pause_after_ms,
            metadata=meta,
        )

    # API compatibility alias
    guard_and_normalize = sanitize_and_guard

    @classmethod
    def _normalize_spoken_punctuation(cls, text: str) -> str:
        """
        Cleans up duplicate or problematic punctuation in spoken text while preserving
        dialogue structure and Hindi danda (।) / double danda (॥).
        """
        t = text
        # Collapse multiple question marks or exclamation marks (???? -> ?, !!!! -> !)
        t = re.sub(r"\?{2,}", "?", t)
        t = re.sub(r"!{2,}", "!", t)
        # Collapse multiple periods (more than 3 into standard ellipsis ...)
        t = re.sub(r"\.{4,}", "...", t)
        # Collapse multiple commas
        t = re.sub(r",{2,}", ",", t)
        # Collapse multiple dandas
        t = re.sub(r"।{2,}", "।", t)
        # Clean up stray or orphaned quotes
        t = re.sub(r"[\"“”'‘’]{2,}", '"', t)
        # Normalize whitespace around punctuation
        t = re.sub(r"\s+([,\.!\?।])", r"\1", t)
        t = re.sub(r"\s+", " ", t)
        return t.strip()

    @classmethod
    def _calculate_suggested_pauses(
        cls,
        text: str,
        ssml_break_ms: int,
        pipeline_mode: TTSPipelineMode,
    ) -> Tuple[int, int]:
        """Calculates natural editorial pauses based on punctuation and SSML hints."""
        pause_before = 0
        pause_after = 350  # Default sentence pause

        if ssml_break_ms > 0:
            pause_after = max(pause_after, ssml_break_ms)

        if text.endswith("...") or text.endswith("…"):
            pause_after = 600  # Trailing thought / hesitation
        elif text.endswith("?") or text.endswith("!"):
            pause_after = 450  # Emphatic boundary
        elif text.endswith(",") or text.endswith(";"):
            pause_after = 200  # Clause boundary

        if text.startswith("...") or text.startswith("…") or text.startswith("--"):
            pause_before = 250  # Leading hesitation

        if pipeline_mode == TTSPipelineMode.MULTI_CAST:
            # Multi-cast dialogue turns have slightly tighter snapping
            pause_after = max(150, min(pause_after, 500))

        return pause_before, pause_after
