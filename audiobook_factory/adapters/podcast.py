#!/usr/bin/env python3
"""
Audiobook Factory - Script Adapters: Dedicated 2-Host Podcast Adapter.
Bridges the unified Dramaturgy AST (DramaticPlan) to the 2-Host Podcast Engine,
producing broadcast-ready conversational script segments.
"""

from __future__ import annotations
import os
import logging
from typing import List, Dict, Any, Optional

from audiobook_factory.adapters.base import BaseScriptAdapter
from audiobook_factory.dramaturgy.contracts import DramaticPlan
from audiobook_factory.podcast.contracts import PodcastEpisodePlan, HostProfile
from audiobook_factory.podcast.episode_generator import PodcastEpisodeGenerator
from audiobook_factory.podcast.persona_engine import HostPersonaEngine

logger = logging.getLogger("AudiobookFactory")


class PodcastAdapter(BaseScriptAdapter):
    """
    Script Adapter for 2-Host Conversational Narrative Podcasts.
    Consumes literary Dramaturgy AST and outputs audio-first conversational segments
    ready for Gemini Flash TTS synthesis and EBU R128 mastering.
    """
    adapter_id: str = "podcast"
    format_name: str = "2-Host Narrative Podcast"

    def __init__(
        self,
        model: Optional[str] = None,
        hosts: Optional[Dict[str, HostProfile]] = None,
    ):
        self.model = model
        self.hosts = hosts
        self.generator = PodcastEpisodeGenerator(model=model, hosts=hosts)

    def adapt(
        self,
        chapter_text: str,
        dramatic_plan: DramaticPlan,
        character_roster: Optional[Dict[str, Any]] = None,
        memory_context: Optional[Any] = None,
        is_hindi: bool = False,
        chapter_num: int = 1,
        chapter_id: str = "chapter_001",
        call_llm_fn: Optional[Any] = None,
        return_plan: bool = False,
        **kwargs,
    ) -> Any:
        """
        Transforms chapter text and dramatic plan into 2-Host podcast script segments.
        """
        episode_plan = self.generator.generate_episode(
            chapter_text=chapter_text,
            dramatic_plan=dramatic_plan,
            chapter_num=chapter_num,
            chapter_id=chapter_id,
            is_hindi=is_hindi,
            call_llm_fn=call_llm_fn,
        )

        # Convert PodcastSegments to downstream Screenplay segment dicts
        standard_segments: List[Dict[str, Any]] = []
        hosts_by_name = {h.name: h for h in episode_plan.hosts.values()}
        for seg in episode_plan.segments:
            host = hosts_by_name.get(seg.speaker)
            voice = host.voice_id if host else "Puck"
            pan = host.pan if host else 0.0
            formant_params = {
                "pan": pan,
                "pitch_shift_pct": host.pitch_shift if host else 0.0,
                "tempo_rate": host.speed_multiplier if host else 1.0,
            }
            seg_dict = {
                "index": seg.index,
                "speaker": seg.speaker,
                "text": seg.text,
                "dialogue": seg.text,
                "type": "dialogue",
                "emotion": seg.emotion,
                "voice": voice,
                "pause_after_ms": seg.pause_after_ms,
                "section_type": seg.section_type,
                "interjection_type": seg.interjection_type,
                "acting": seg.acting,
                "spatial": seg.spatial,
                "formant_params": formant_params,
                "acoustic_env": "podcast_studio",
            }
            standard_segments.append(seg_dict)

        if return_plan:
            return standard_segments, episode_plan
        return standard_segments
