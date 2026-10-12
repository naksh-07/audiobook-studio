#!/usr/bin/env python3
"""
Audiobook Factory - Script Adapters: Audiobook Script Adapter.
Encapsulates the Audible Flow Standard: prose fidelity, narrator transparency,
em-dash lead-ins, anti-swap dialogue attribution, Stanislavski subtext enrichment,
and Performance Bible delivery directives.
"""

from __future__ import annotations
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from audiobook_factory.adapters.base import BaseScriptAdapter
from audiobook_factory.dramaturgy.contracts import DramaticPlan, PerformanceBible, CharacterPerformanceProfile
from audiobook_factory.dramaturgy.beat_planner import BeatPlanner
from audiobook_factory.model_manager import get_model_manager, TaskType, LLMUnavailableError
from audiobook_factory.key_manager import get_persistent_key_pool
from audiobook_factory.script.staging_enricher import _parse_dramatized_chunk_llm
from audiobook_factory.script.screenplay_cleaner import clean_screenplay_pass2

logger = logging.getLogger("AudiobookFactory")


def _get_chunk_parser():
    import sys
    sb = sys.modules.get("audiobook_factory.script_builder")
    if sb and hasattr(sb, "_parse_dramatized_chunk_llm"):
        return sb._parse_dramatized_chunk_llm
    return _parse_dramatized_chunk_llm


class AudiobookAdapter(BaseScriptAdapter):
    """
    Standard Audiobook Adapter producing multi-cast Audible-standard screenplays.
    Maintains 100% fidelity to the original prose, applies scene-scoped beat metadata,
    binds Performance Bible character profiles, and structures narrator and character lines
    with em-dash flow and micro-fade directives.
    """
    adapter_id: str = "audiobook"
    format_name: str = "Audible Multi-Cast Audiobook"

    def __init__(
        self,
        model: Optional[str] = None,
        performance_bible: Optional[Union[PerformanceBible, Dict[str, Any], Path, str]] = None,
    ):
        self.model = model
        self.performance_bible = self._load_performance_bible(performance_bible)

    def _load_performance_bible(
        self, pb: Optional[Union[PerformanceBible, Dict[str, Any], Path, str]]
    ) -> Optional[PerformanceBible]:
        """Parses or loads PerformanceBible from object, dict, or path."""
        if pb is None:
            return None
        if isinstance(pb, PerformanceBible):
            return pb
        if isinstance(pb, (str, Path)):
            p = Path(pb).resolve()
            if p.exists():
                try:
                    return PerformanceBible.load_from_file(p)
                except Exception as e:
                    logger.warning(f"  [!] Failed to load PerformanceBible from {p}: {e}")
            return None
        if isinstance(pb, dict):
            try:
                return PerformanceBible.model_validate(pb)
            except Exception as e:
                logger.warning(f"  [!] Failed to validate PerformanceBible dict: {e}")
        return None

    def _resolve_model(self, api_key: Optional[str] = None) -> str:
        if self.model:
            return self.model
        return get_model_manager().resolve_active_model(TaskType.SCREENPLAY, api_key=api_key)

    def adapt(
        self,
        chapter_text: str,
        dramatic_plan: DramaticPlan,
        character_roster: Optional[Dict[str, Any]] = None,
        memory_context: Optional[Any] = None,
        is_hindi: bool = False,
        chapter_num: int = 1,
        chapter_id: str = "chapter_001",
        performance_bible: Optional[Union[PerformanceBible, Dict[str, Any], Path, str]] = None,
        call_chunk_fn: Optional[Any] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Transforms chapter text and dramatic plan into Audible-compliant script segments.
        """
        self.pre_adapt(chapter_text=chapter_text, dramatic_plan=dramatic_plan, **kwargs)

        chunk_parser = call_chunk_fn or _get_chunk_parser()
        active_pb = self._load_performance_bible(performance_bible) or self.performance_bible

        pool = get_persistent_key_pool()
        api_key = pool.get_key(service="text") if pool else None

        if not api_key:
            logger.error("  [!] STRICT HALT: No text API key available for audiobook screenplay attribution.")
            raise LLMUnavailableError("API key pool exhausted for screenplay attribution. Production strictly halted.")

        model = self._resolve_model(api_key=api_key)
        memory_prompt_str = (
            memory_context.get_prompt_context()
            if memory_context is not None and hasattr(memory_context, "get_prompt_context")
            else ""
        )

        # JIT Load Chapter Director Card and Production Playbook if available
        eff_card = kwargs.get("director_card")
        eff_playbook = kwargs.get("playbook")
        proj_dir_str = os.environ.get("CURRENT_PROJECT_DIR")
        if proj_dir_str and Path(proj_dir_str).exists():
            p_dir = Path(proj_dir_str)
            if eff_card is None:
                try:
                    from audiobook_factory.glossary.chapter_director import ChapterSteeringDirector
                    eff_card = ChapterSteeringDirector.load_director_card(p_dir, chapter_num)
                except Exception:
                    pass
            if eff_playbook is None:
                pb_file = p_dir / "production_playbook.json"
                if pb_file.exists():
                    try:
                        from audiobook_factory.contracts.playbook import ProductionPlaybook
                        eff_playbook = ProductionPlaybook.model_validate_json(pb_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass

        ch_text = chapter_text or ""
        if not ch_text.strip():
            return []

        max_chunk_words = int(os.environ.get("SCREENPLAY_CHUNK_WORDS", "500"))
        words_count = len(ch_text.split())

        dramatic_scenes = getattr(dramatic_plan, "scenes", None) or []
        if words_count <= max_chunk_words or not dramatic_plan:
            dramatic_context_str = ""
            if dramatic_scenes:
                primary_scene = dramatic_scenes[0]
                ctx_parts = [
                    f"Active Dramatic Scene: {primary_scene.scene_id} ({primary_scene.scene_type})",
                    f"Setting: {primary_scene.location} ({primary_scene.time_context})",
                    f"Dramatic Purpose: {primary_scene.dramatic_purpose}",
                    f"Scene Question: {primary_scene.scene_question}",
                    f"Stakes: {primary_scene.stakes}",
                    f"Primary Conflict: {primary_scene.primary_conflict}",
                ]
                if primary_scene.listener_knowledge_state:
                    ctx_parts.append(f"Audience Knowledge: {primary_scene.listener_knowledge_state}")
                if primary_scene.beats:
                    ctx_parts.append("Planned Dramatic Beats:")
                    for b in primary_scene.beats:
                        obj_s = f", Objective: '{b.objective.immediate_goal}'" if b.objective else ""
                        act_s = f", Actioning: '{b.objective.actioning}'" if b.objective else ""
                        ctx_parts.append(f"  - [{b.beat_id}] Function: {b.dramatic_function}{act_s}{obj_s}")
                dramatic_context_str = "\n".join(ctx_parts)

            raw_items = chunk_parser(
                chunk_text=ch_text,
                preceding_context=memory_prompt_str,
                is_hindi=is_hindi,
                character_roster=character_roster,
                api_key="",
                model=model,
                dramatic_context=dramatic_context_str,
                director_card=eff_card,
                playbook=eff_playbook,
            )
            if not raw_items:
                logger.error("  [!] STRICT HALT: Screenplay LLM returned no segments. Refusing to degrade to flat narrator.")
                raise LLMUnavailableError("Screenplay LLM returned empty segments. Production strictly halted.")

        else:
            chunks = BeatPlanner.slice_chapter_by_beats(
                chapter_text=ch_text,
                dramatic_plan=dramatic_plan,
                max_words=max_chunk_words,
            )

            raw_items = []
            rolling_context = memory_prompt_str

            for c_idx, chunk_info in enumerate(chunks, 1):
                c_text = chunk_info["text"]
                sc = dramatic_plan.get_scene(chunk_info["scene_id"])
                c_dramatic_lines = []
                if sc:
                    c_dramatic_lines.append(f"Dramatic Scene: {sc.scene_id} ({sc.scene_type}) - Setting: {sc.location}")
                    c_dramatic_lines.append(f"Scene Purpose: {sc.dramatic_purpose} | Stakes: {sc.stakes}")
                    c_dramatic_lines.append(f"Primary Conflict: {sc.primary_conflict}")
                    if sc.listener_knowledge_state:
                        c_dramatic_lines.append(f"Audience Knowledge: {sc.listener_knowledge_state}")
                if chunk_info.get("beat_ids"):
                    c_dramatic_lines.append("Active Dramatic Beats in this section:")
                    for bid in chunk_info["beat_ids"]:
                        b = dramatic_plan.get_beat(bid)
                        if b:
                            obj_s = f", Objective: '{b.objective.immediate_goal}'" if b.objective else ""
                            act_s = f", Actioning: '{b.objective.actioning}'" if b.objective else ""
                            c_dramatic_lines.append(f"  * [{b.beat_id}] Function: {b.dramatic_function}{act_s}{obj_s}, Tension: {b.tension_before}->{b.tension_after}")
                chunk_dramatic_ctx = "\n".join(c_dramatic_lines)

                chunk_items = chunk_parser(
                    chunk_text=c_text,
                    preceding_context=rolling_context,
                    is_hindi=is_hindi,
                    character_roster=character_roster,
                    api_key="",
                    model=model,
                    dramatic_context=chunk_dramatic_ctx,
                    director_card=eff_card,
                    playbook=eff_playbook,
                )

                if chunk_items:
                    raw_items.extend(chunk_items)
                    tail_lines = []
                    for it in chunk_items[-3:]:
                        sp = it.get("speaker", "Narrator")
                        typ = it.get("type", "dialogue")
                        txt = (it.get("text", "") or "").strip()
                        if len(txt) > 85:
                            txt = txt[:82] + "..."
                        tail_lines.append(f"  - [{typ.upper()}] {sp}: \"{txt}\"")
                    rolling_context = (
                        (f"{memory_prompt_str}\n\n" if memory_prompt_str else "")
                        + f"Preceding Scene Context (Last exchanges of chunk {c_idx}):\n"
                        + "\n".join(tail_lines)
                        + "\nATTRIBUTION INSTRUCTION: Use this conversational memory to attribute opening dialogue tags "
                        f"and pronouns (e.g. 'उसने', 'वह', 'he', 'she') to the correct character."
                    )
                else:
                    logger.error(f"  [!] STRICT HALT: Chunk {c_idx} parsing returned empty segments. Halting to preserve dramatization.")
                    raise LLMUnavailableError(f"Screenplay LLM returned empty segments for chunk {c_idx}. Production strictly halted.")

        if not raw_items:
            logger.error("  [!] STRICT HALT: Screenplay LLM returned no segments. Refusing to degrade to flat narrator.")
            raise LLMUnavailableError("Screenplay LLM returned empty segments. Production strictly halted.")

        cleaned = clean_screenplay_pass2(
            raw_items,
            is_hindi=is_hindi,
            character_roster=character_roster,
            memory_context=memory_context,
            dramatic_plan=dramatic_plan,
        )

        return self.post_adapt(
            segments=cleaned,
            dramatic_plan=dramatic_plan,
            performance_bible=active_pb,
            **kwargs,
        )

    def post_adapt(
        self,
        segments: List[Dict[str, Any]],
        dramatic_plan: DramaticPlan,
        performance_bible: Optional[PerformanceBible] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Applies Performance Bible binding and enforces the Narrator Transparency Invariant.
        """
        pb = performance_bible or self.performance_bible

        for seg in segments:
            speaker = (seg.get("speaker") or "Narrator").strip()
            is_narrator = speaker.lower() in ("narrator", "narration", "")

            if is_narrator:
                # Narrator Transparency Invariant: Calm, steady, articulate, measured audiobook delivery
                seg["actioning"] = "narrate"
                narr_style = pb.narrator_style if pb and pb.narrator_style else {}
                seg["acting"] = {
                    "delivery_style": "calm_authoritative",
                    "pacing": narr_style.get("baseline_pace", 1.0),
                    "tone": narr_style.get("tone", "objective_cinematic_observer"),
                }
                seg["intensity_level"] = "medium"
                seg["subtext"] = ""
                seg["underlying_emotion"] = "neutral"
            elif pb:
                # Bind Character Performance Profile
                prof = pb.get_profile(speaker)
                if prof:
                    seg.setdefault("acting", {})
                    acting = seg["acting"]

                    if "pacing" not in acting:
                        acting["pacing"] = prof.baseline_pace
                    if "restraint" not in acting:
                        acting["restraint"] = prof.restraint_level
                    if "articulation" not in acting:
                        acting["articulation"] = prof.articulation
                    if prof.speech_quirks and "speech_quirks" not in acting:
                        acting["speech_quirks"] = prof.speech_quirks

                    # Map emotion to specialized delivery behavior if present in profile
                    cur_emotion = seg.get("emotion") or seg.get("surface_emotion") or "neutral"
                    if cur_emotion in prof.emotional_behaviors:
                        acting["delivery_style"] = prof.emotional_behaviors[cur_emotion]
                    elif "delivery_style" not in acting:
                        acting["delivery_style"] = "natural"

        return segments
