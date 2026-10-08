#!/usr/bin/env python3
"""
Audiobook Factory - Dedicated Podcast Engine: Spoken Breathability Transformer.
Transforms dense written prose or long LLM responses into audio-first,
breathable conversational turns (capped at 18-22 words per breath),
with organic pre-roll breath timing and particle enrichment.
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Optional


class SpokenBreathabilityTransformer:
    """
    Transforms written sentences into spoken-first audio dialogue:
    1. Splits long complex sentences (> 22 words) into natural conversational turns.
    2. De-nests subordinate clauses.
    3. Injects conversational breath pauses and pre-roll breath timing.
    """

    MAX_WORDS_PER_BREATH: int = 22
    TARGET_WORDS_PER_BREATH: int = 14

    @classmethod
    def split_into_breathable_units(cls, text: str, is_hindi: bool = False) -> List[str]:
        """Splits a long passage or monologue into punchy spoken phrases."""
        if not text:
            return []

        clean_text = text.strip()
        words = clean_text.split()
        if len(words) <= cls.MAX_WORDS_PER_BREATH:
            return [clean_text]

        # Natural acoustic boundary split points
        if is_hindi:
            split_patterns = [
                r"(?<=[।!?])\s+",
                r"(?<=[,])\s+(?=और|लेकिन|परन्तु|क्योंकि|तो|मगर|यानी|मतलब|सच में|सुनो|अरे)",
                r"(?<=[,])\s+",
            ]
        else:
            split_patterns = [
                r"(?<=[.!?])\s+",
                r"(?<=[,;])\s+(?=and|but|because|so|yet|which|meaning|actually|right|wait|look)",
                r"(?<=[,;])\s+",
            ]

        units = [clean_text]
        for pattern in split_patterns:
            new_units = []
            for u in units:
                if len(u.split()) > cls.MAX_WORDS_PER_BREATH:
                    parts = re.split(pattern, u)
                    new_units.extend([p.strip() for p in parts if p.strip()])
                else:
                    new_units.append(u)
            units = new_units

        # Final word-count clamp: if any unit is still over MAX_WORDS_PER_BREATH, split on word count
        final_units = []
        for u in units:
            u_words = u.split()
            if len(u_words) <= cls.MAX_WORDS_PER_BREATH:
                final_units.append(u)
            else:
                chunk = []
                for w in u_words:
                    chunk.append(w)
                    if len(chunk) >= cls.TARGET_WORDS_PER_BREATH and w.endswith((".", ",", "!", "?", "।", "—")):
                        final_units.append(" ".join(chunk))
                        chunk = []
                    elif len(chunk) >= cls.MAX_WORDS_PER_BREATH:
                        final_units.append(" ".join(chunk))
                        chunk = []
                if chunk:
                    final_units.append(" ".join(chunk))

        return final_units

    @classmethod
    def format_podcast_turn(
        cls,
        text: str,
        speaker: str,
        index: int,
        emotion: str = "neutral",
        section_type: str = "scene_deepdive",
        spatial: Optional[Dict[str, Any]] = None,
        is_hindi: bool = False,
        interjection_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Splits a single speaker turn into multiple breathable segments with pre-roll breath timing."""
        units = cls.split_into_breathable_units(text, is_hindi=is_hindi)
        segments = []

        for u_idx, u in enumerate(units):
            # Trailing pauses: slightly shorter within a multi-unit turn, standard between turns
            pause = 300 if u_idx < len(units) - 1 else 450

            # Organic pre-roll breath timing on question or high-emotion turns
            pre_breath = 0
            if u_idx == 0:
                is_question = u.strip().endswith(("?", "??"))
                is_exclamation = u.strip().endswith(("!", "!!"))
                if is_question or is_exclamation or interjection_type or emotion in ("shocked", "tense", "excited"):
                    pre_breath = 140

            segments.append({
                "index": index + u_idx,
                "speaker": speaker,
                "text": u,
                "emotion": emotion,
                "section_type": section_type,
                "pause_after_ms": pause,
                "pre_roll_breath_ms": pre_breath,
                "interjection_type": interjection_type if u_idx == 0 else None,
                "spatial": spatial or {},
            })
        return segments
