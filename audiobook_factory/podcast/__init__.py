#!/usr/bin/env python3
"""
Audiobook Studio - Podcast & Technical Verbalization Subsystem.
Provides NotebookLM-style dual-host podcast script generation, mathematical formula
verbalization, Markdown table insight extraction, and academic abstract audio adapters.
"""

from audiobook_factory.podcast.contracts import (
    PodcastScript,
    PodcastSegment,
    HostProfile,
    HostRole,
    VerbalizationStyle,
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

__all__ = [
    "PodcastScript",
    "PodcastSegment",
    "HostProfile",
    "HostRole",
    "VerbalizationStyle",
    "MathVerbalizer",
    "TableVerbalizer",
    "AbstractCalloutVerbalizer",
    "PodcastScriptBuilder",
    "generate_podcast_script_from_file",
]
