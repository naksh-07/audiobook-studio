#!/usr/bin/env python3
"""
Audiobook Factory - Script Engine: Dramatized Screenplay Builder.
Coordinates literary Dramaturgy AST generation, format adaptation via AudiobookAdapter,
Performance Bible binding, and Gate 2.5 validation.
"""

from __future__ import annotations
import hashlib
import logging
from typing import List, Dict, Any, Optional

from audiobook_factory.dramaturgy.scene_analyzer import SceneAnalyzer
from audiobook_factory.dramaturgy.beat_planner import BeatPlanner
from audiobook_factory.dramaturgy.contracts import DramaticPlan
from audiobook_factory.dramaturgy.dramatic_validator import DramaticValidator
from audiobook_factory.adapters.audiobook import AudiobookAdapter

logger = logging.getLogger("AudiobookFactory")


def build_dramatized_script_llm(
    chapter_text: str,
    is_hindi: bool = False,
    character_roster: Optional[Dict[str, Any]] = None,
    memory_context: Optional[Any] = None,
    chapter_num: int = 1,
    chapter_id: str = "chapter_001",
    return_dramatic_plan: bool = False,
    adapter: Optional[Any] = None,
    performance_bible: Optional[Any] = None,
) -> Any:
    """
    Option C Dramatized Screenplay Builder:
    1. Synthesizes the unified literary DramaticPlan AST (Scenes + Beats + SPU bounds).
    2. Routes through the AudiobookAdapter (or requested adapter) with Performance Bible binding.
    3. Runs Gate 2.5 DramaticValidator to guarantee structural and dramatic integrity.
    """
    known_chars = None
    if character_roster and "characters" in character_roster:
        chars = character_roster["characters"]
        if isinstance(chars, dict):
            known_chars = list(chars.keys())
        elif isinstance(chars, list):
            known_chars = [c.get("english_name", "") for c in chars if isinstance(c, dict) and c.get("english_name")]

    # 1. Synthesize Holistic Chapter Dramatic Plan (Option C Core)
    scenes = SceneAnalyzer.segment_and_analyze_scenes(
        chapter_text=chapter_text,
        chapter_num=chapter_num,
        chapter_title=f"Chapter {chapter_num}",
        known_characters=known_chars,
        memory_context=memory_context,
    )
    scenes = BeatPlanner.plan_chapter_beats(
        chapter_text=chapter_text,
        scenes=scenes,
        known_characters=known_chars,
        memory_context=memory_context,
    )
    total_beats = sum(len(s.beats) for s in scenes)
    s_hash = hashlib.sha256(chapter_text.encode("utf-8")).hexdigest()
    dramatic_plan = DramaticPlan(
        chapter_id=chapter_id,
        chapter_num=chapter_num,
        scenes=scenes,
        total_beats=total_beats,
        source_hash=s_hash,
    )

    # 2. Format Adaptation Layer with Performance Bible
    active_adapter = adapter or AudiobookAdapter(performance_bible=performance_bible)
    cleaned = active_adapter.adapt(
        chapter_text=chapter_text,
        dramatic_plan=dramatic_plan,
        character_roster=character_roster,
        memory_context=memory_context,
        is_hindi=is_hindi,
        chapter_num=chapter_num,
        chapter_id=chapter_id,
        performance_bible=performance_bible,
    )

    # 3. Gate 2.5 Dramatic Validation
    val_res = DramaticValidator.validate_screenplay_and_plan(
        segments=cleaned,
        dramatic_plan=dramatic_plan,
        source_text=chapter_text,
        known_characters=known_chars,
        memory_context=memory_context,
    )

    if return_dramatic_plan:
        return cleaned, dramatic_plan, val_res
    return cleaned
