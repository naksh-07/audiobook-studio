#!/usr/bin/env python3
"""
Audiobook Factory - Dedicated Podcast Engine: 5-Part Episode Generator.
Coordinates the end-to-end 2-Host narrative podcast pipeline:
1. Cold Open Hook (15-30s high-tension teaser).
2. Show Intro & Premise Setup (30-45s).
3. Scene Deep-Dives & Re-enactments (3-4 min blocks).
4. Cognitive Reset & Banter Bridges (20-30s).
5. Episode Outro & Teaser (45-60s).
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable

from audiobook_factory.dramaturgy.contracts import DramaticPlan, SceneDramaticPlan
from audiobook_factory.podcast.contracts import (
    HostProfile,
    PodcastSegment,
    PodcastEpisodePlan,
    PodcastSectionType,
)
from audiobook_factory.podcast.persona_engine import HostPersonaEngine
from audiobook_factory.podcast.spoken_transformer import SpokenBreathabilityTransformer
from audiobook_factory.dramaturgy.gateway_bridge import execute_dramaturgy_llm
from audiobook_factory.model_manager import get_model_manager, TaskType, LLMUnavailableError

# Backward compatibility alias for testing hooks; routes to ModelGateway by default
call_gemini = execute_dramaturgy_llm

logger = logging.getLogger("AudiobookFactory")


class PodcastEpisodeGenerator:
    """
    Generates dynamic 2-Host narrative podcasts from literary Dramaturgy ASTs.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        hosts: Optional[Dict[str, HostProfile]] = None,
    ):
        self.model = model
        self.hosts = hosts

    def _resolve_model(self) -> str:
        if self.model:
            return self.model
        return get_model_manager().resolve_active_model(TaskType.SCREENPLAY)

    def generate_episode(
        self,
        chapter_text: str,
        dramatic_plan: DramaticPlan,
        chapter_num: int = 1,
        chapter_id: str = "chapter_001",
        is_hindi: bool = True,
        call_llm_fn: Optional[Callable[..., Any]] = None,
        episode_title: Optional[str] = None,
    ) -> PodcastEpisodePlan:
        """
        Generates a complete 5-part 2-Host podcast episode from the unified DramaticPlan AST.
        """
        active_hosts = self.hosts or HostPersonaEngine.get_default_hosts(is_hindi=is_hindi)
        host_a = active_hosts.get("host_a") or HostProfile(host_id="host_a", name="Host A")
        host_b = active_hosts.get("host_b") or HostProfile(host_id="host_b", name="Host B")

        # 1. Identify Highest Tension Beat for Cold Open Hook
        highest_beat = None
        max_tension = -1.0
        for sc in dramatic_plan.scenes:
            for bt in sc.beats:
                t_score = max(bt.tension_before, bt.tension_after)
                if t_score > max_tension:
                    max_tension = t_score
                    highest_beat = bt

        hook_context = (
            f"High Tension Peak ({highest_beat.dramatic_function}): {highest_beat.summary} (Subtext: {highest_beat.subtext})"
            if highest_beat
            else "High stakes opening tension."
        )

        # 2. Build Structural Scene Synopsis from Dramaturgy Core
        scene_summaries = []
        for s_idx, sc in enumerate(dramatic_plan.scenes, 1):
            beats_desc = ", ".join([f"{b.dramatic_function} ('{b.summary}')" for b in sc.beats[:4]])
            scene_summaries.append(
                f"Scene {s_idx} [{sc.scene_title or sc.scene_id}] ({sc.scene_type}):\n"
                f"  - Purpose: {sc.dramatic_purpose}\n"
                f"  - Conflict: {sc.primary_conflict}\n"
                f"  - Stakes: {sc.stakes}\n"
                f"  - Key Beats: {beats_desc}"
            )
        scenes_block = "\n".join(scene_summaries)

        sys_prompt = HostPersonaEngine.build_system_prompt(active_hosts, is_hindi=is_hindi)

        prompt = f"""Generate a 5-Part 2-Host Narrative Podcast Episode for Chapter {chapter_num}.

EPISODE HOOK TARGET:
{hook_context}

DRAMATURGICAL SCENE ARCHITECTURE:
{scenes_block}

OVERALL CHAPTER ARC:
{dramatic_plan.overall_arc_summary or 'A gripping dramatic progression.'}

EPISODE STRUCTURE REQUIREMENT (Strictly 5 Parts):
1. 'cold_open_hook': 15-30s punchy teaser grabbing the listener mid-action.
2. 'show_intro': {host_a.name} & {host_b.name} introduce today's high-stakes chapter and character dilemmas.
3. 'scene_deepdive': Detailed dramatic exploration and re-enactment of key scenes, unpacking why characters make the choices they make.
4. 'cognitive_reset_banter': Brief 20-30s natural banter/reaction to a major reveal or moral turning point.
5. 'show_outro': Wrap-up, takeaway on character transformation, and cliffhanger teaser for what comes next.

OUTPUT FORMAT: Strict JSON list of dialogue turns:
[
  {{
    "speaker": "{host_a.name}" | "{host_b.name}",
    "text": string (conversational, spoken-first, max 18-22 words per turn),
    "emotion": "excited" | "shocked" | "intrigued" | "tense" | "thoughtful" | "humorous" | "neutral",
    "section_type": "cold_open_hook" | "show_intro" | "scene_deepdive" | "reenactment" | "cognitive_reset_banter" | "show_outro",
    "interjection_type": string (optional, e.g. "gasp", "laughter", "agreement")
  }}
]
"""
        model = self._resolve_model()
        logger.info(f"[*] Podcast Generator: Synthesizing 2-Host podcast for Chapter {chapter_num} ({model})...")

        raw_turns = None
        if call_llm_fn:
            raw_turns = call_llm_fn(prompt=prompt, system_instruction=sys_prompt, model=model, json_mode=True)
            if isinstance(raw_turns, str):
                import json_repair
                raw_turns = json_repair.loads(raw_turns)
        else:
            try:
                raw_turns = call_gemini(
                    prompt=prompt,
                    system_instruction=sys_prompt,
                    task="screenplay",
                    model=model,
                    json_mode=True,
                    max_output_tokens=16384,
                    thinking_budget=1024,
                )
            except Exception as e:
                logger.error(f"  [!] Podcast LLM generation failed: {e}")
                raise LLMUnavailableError(f"Podcast LLM generation failed: {e}")

        if isinstance(raw_turns, dict):
            for k in ("turns", "segments", "dialogue", "items", "results"):
                if k in raw_turns and isinstance(raw_turns[k], list):
                    raw_turns = raw_turns[k]
                    break

        if not isinstance(raw_turns, list) or not raw_turns:
            logger.error("  [!] Podcast generator received empty or invalid response from LLM.")
            raise LLMUnavailableError("Podcast generator received empty response from LLM.")

        # 3. Post-Process through SpokenBreathabilityTransformer & Apply Staging
        final_segments: List[PodcastSegment] = []
        seg_idx = 1
        for item in raw_turns:
            if not isinstance(item, dict):
                continue
            spk = item.get("speaker", host_a.name)
            txt = (item.get("text") or "").strip()
            emo = item.get("emotion", "neutral")
            sec = item.get("section_type", "scene_deepdive")
            inj = item.get("interjection_type")

            # Determine spatial panning based on host
            pan = 0.0
            if spk == host_a.name:
                pan = host_a.pan
            elif spk == host_b.name:
                pan = host_b.pan

            spatial_dict = {"azimuth_pan": pan, "acoustic_env": "podcast_studio"}

            breathable_units = SpokenBreathabilityTransformer.format_podcast_turn(
                text=txt,
                speaker=spk,
                index=seg_idx,
                emotion=emo,
                section_type=sec,
                spatial=spatial_dict,
                is_hindi=is_hindi,
            )
            for bu in breathable_units:
                p_seg = PodcastSegment(
                    index=len(final_segments) + 1,
                    speaker=bu["speaker"],
                    text=bu["text"],
                    emotion=bu["emotion"],
                    section_type=bu["section_type"],
                    pause_after_ms=bu["pause_after_ms"],
                    interjection_type=inj,
                    spatial=bu["spatial"],
                )
                final_segments.append(p_seg)
                seg_idx += 1

        # Calculate estimated run time (~135 words per min)
        total_words = sum(len(s.text.split()) for s in final_segments)
        duration_est = round((total_words / 135.0) * 60.0, 1)

        ep_title = episode_title or f"Chapter {chapter_num} Deep-Dive: {dramatic_plan.scenes[0].scene_title if dramatic_plan.scenes else 'The Turning Point'}"

        plan = PodcastEpisodePlan(
            episode_id=f"podcast_ep_{chapter_num:03d}",
            episode_title=ep_title,
            source_chapter_id=chapter_id,
            language="hi" if is_hindi else "en",
            hosts=active_hosts,
            hook_statement=highest_beat.summary if highest_beat else "",
            segments=final_segments,
            total_duration_estimate_sec=duration_est,
            target_lufs=-16.0,
        )

        logger.info(
            f"[+] Podcast Episode Plan Generated: {len(final_segments)} turns, "
            f"~{duration_est/60.0:.1f} mins duration."
        )
        return plan
