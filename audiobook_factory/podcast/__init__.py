#!/usr/bin/env python3
"""
Audiobook Studio - Unified Podcast Engine & Verbalization Subsystem.
Provides:
1. NotebookLM-style dual-host podcast script generation, mathematical formula verbalization,
   and Markdown table insight extraction from technical whitepapers.
2. 5-Part 2-Host conversational narrative podcast episode generation from chapters.
3. Spoken breathability transformation (<= 22 words per turn), stereo spatial staging,
   and broadcast EBU R128 (-16.0 / -19.0 LUFS) vocal mastering.
"""

from __future__ import annotations
from audiobook_factory.podcast.contracts import (
    PodcastScript,
    PodcastSegment,
    HostProfile,
    PodcastEpisodePlan,
    HostRole,
    VerbalizationStyle,
    PodcastSectionType,
    PodcastProductionResult,
)
from audiobook_factory.podcast.verbalizer import (
    MathVerbalizer,
    TableVerbalizer,
    AbstractCalloutVerbalizer,
)
from audiobook_factory.podcast.script_builder import (
    PodcastScriptBuilder,
    generate_podcast_script_from_file,
)
from audiobook_factory.podcast.producer import (
    HannMicroFadeProcessor,
    PodcastAudioProducer,
    produce_podcast_audio,
)
from audiobook_factory.podcast.persona_engine import HostPersonaEngine
from audiobook_factory.podcast.spoken_transformer import SpokenBreathabilityTransformer
from audiobook_factory.podcast.episode_generator import PodcastEpisodeGenerator
from audiobook_factory.podcast.project_generator import generate_project_podcasts
from audiobook_factory.podcast.orchestrator import (
    PodcastOrchestrator,
    process_document_to_podcast,
)

__all__ = [
    "PodcastScript",
    "PodcastSegment",
    "HostProfile",
    "PodcastEpisodePlan",
    "HostRole",
    "VerbalizationStyle",
    "PodcastSectionType",
    "PodcastProductionResult",
    "MathVerbalizer",
    "TableVerbalizer",
    "AbstractCalloutVerbalizer",
    "PodcastScriptBuilder",
    "generate_podcast_script_from_file",
    "HannMicroFadeProcessor",
    "PodcastAudioProducer",
    "produce_podcast_audio",
    "HostPersonaEngine",
    "SpokenBreathabilityTransformer",
    "PodcastEpisodeGenerator",
    "generate_project_podcasts",
    "PodcastOrchestrator",
    "process_document_to_podcast",
]
