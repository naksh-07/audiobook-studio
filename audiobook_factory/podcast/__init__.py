#!/usr/bin/env python3
"""
Audiobook Factory - Dedicated 2-Host Podcast Engine Package.
"""

from __future__ import annotations
from audiobook_factory.podcast.contracts import (
    HostProfile,
    PodcastSegment,
    PodcastEpisodePlan,
    HostRole,
    PodcastSectionType,
)
from audiobook_factory.podcast.persona_engine import HostPersonaEngine
from audiobook_factory.podcast.spoken_transformer import SpokenBreathabilityTransformer
from audiobook_factory.podcast.episode_generator import PodcastEpisodeGenerator
from audiobook_factory.podcast.project_generator import generate_project_podcasts
from audiobook_factory.podcast.orchestrator import PodcastOrchestrator

__all__ = [
    "HostProfile",
    "PodcastSegment",
    "PodcastEpisodePlan",
    "HostRole",
    "PodcastSectionType",
    "HostPersonaEngine",
    "SpokenBreathabilityTransformer",
    "PodcastEpisodeGenerator",
    "generate_project_podcasts",
    "PodcastOrchestrator",
]

