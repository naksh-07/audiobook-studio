#!/usr/bin/env python3
"""
Audiobook Studio - Podcast & Technical Verbalization Subsystem.
Provides NotebookLM-style dual-host podcast script generation, mathematical formula
verbalization, Markdown table insight extraction, dialogue editorial concatenation,
and broadcast EBU R128 vocal mastering.
"""

from audiobook_factory.podcast.contracts import (
    PodcastScript,
    PodcastSegment,
    HostProfile,
    HostRole,
    VerbalizationStyle,
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
from audiobook_factory.podcast.orchestrator import (
    PodcastOrchestrator,
    process_document_to_podcast,
)

__all__ = [
    "PodcastScript",
    "PodcastSegment",
    "HostProfile",
    "HostRole",
    "VerbalizationStyle",
    "PodcastProductionResult",
    "MathVerbalizer",
    "TableVerbalizer",
    "AbstractCalloutVerbalizer",
    "PodcastScriptBuilder",
    "generate_podcast_script_from_file",
    "HannMicroFadeProcessor",
    "PodcastAudioProducer",
    "produce_podcast_audio",
    "PodcastOrchestrator",
    "process_document_to_podcast",
]
