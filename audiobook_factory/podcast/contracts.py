#!/usr/bin/env python3
"""
Audiobook Factory - Dedicated Podcast Engine Data Contracts (Pydantic v2).
Defines strictly typed schemas for 2-Host conversational podcast episodes,
host persona profiles, spoken-first breathability segments, and episode structures.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

HostRole = Literal["inquisitive_driver", "domain_expert", "guest_commentator"]
PodcastSectionType = Literal[
    "cold_open_hook",
    "show_intro",
    "scene_deepdive",
    "reenactment",
    "cognitive_reset_banter",
    "show_outro",
]


class HostProfile(BaseModel):
    """
    Vocal and behavioral persona configuration for a podcast host.
    """
    model_config = ConfigDict(extra="ignore")

    host_id: str = Field(..., description="Unique host identifier, e.g. 'host_a' or 'host_b'")
    name: str = Field(..., description="Display name for the host")
    role: HostRole = Field(default="inquisitive_driver", description="Conversational dynamic role")
    voice_id: str = Field(default="Puck", description="Gemini TTS voice name (e.g. Puck, Aoede, Fenrir, Charon)")
    pitch_shift: float = Field(default=0.0, ge=-20.0, le=20.0, description="Pitch semitone offset (-12 to +12)")
    speed_multiplier: float = Field(default=1.0, ge=0.7, le=1.4, description="Speech cadence rate multiplier")
    pan: float = Field(default=0.0, ge=-1.0, le=1.0, description="Acoustic azimuth stereo pan (-1.0 Left to +1.0 Right)")
    energy_baseline: float = Field(default=0.8, ge=0.2, le=1.0, description="Base vocal projection energy")
    interjection_lexicon: List[str] = Field(
        default_factory=list,
        description="Natural spoken conversational particles and interjections"
    )


class PodcastSegment(BaseModel):
    """
    Atomic spoken dialogue turn in a podcast episode.
    Designed for maximum breathability (<= 22 words) and acoustic naturalness.
    """
    model_config = ConfigDict(extra="ignore")

    index: int = Field(..., ge=1, description="1-indexed sequence number in episode")
    speaker: str = Field(..., description="Host name or character name in re-enactment")
    text: str = Field(..., description="Spoken-first natural dialogue text")
    emotion: str = Field(default="neutral", description="Emotional vocal delivery tag")
    section_type: PodcastSectionType = Field(default="scene_deepdive", description="Episode structural section")
    pause_after_ms: int = Field(default=450, ge=100, le=3000, description="Silence after turn in ms")
    interjection_type: Optional[str] = Field(default=None, description="Type of conversational reaction (e.g. 'gasp', 'laughter', 'agreement')")
    acting: Dict[str, Any] = Field(default_factory=dict, description="Voice acting delivery hints")
    spatial: Dict[str, Any] = Field(default_factory=dict, description="Stereo pan and acoustic environment")
    beat_ref: Optional[str] = Field(default=None, description="Referenced DramaticBeat ID from core AST")
    spu_ref: Optional[str] = Field(default=None, description="Referenced source paragraph SPU ID")


class PodcastEpisodePlan(BaseModel):
    """
    Holistic 5-Part 2-Host Podcast Episode Plan (durable artifact: podcast_plan.json).
    """
    model_config = ConfigDict(extra="ignore")

    episode_id: str = Field(..., description="Unique episode ID, e.g. 'podcast_ep_001'")
    episode_title: str = Field(default="Audiobook Studio Deep-Dive", description="Title of the podcast episode")
    source_chapter_id: str = Field(..., description="Linked source chapter identifier")
    language: Literal["en", "hi"] = Field(default="hi", description="Delivery language")
    hosts: Dict[str, HostProfile] = Field(default_factory=dict, description="Active host profiles")
    hook_statement: str = Field(default="", description="15-30s opening teaser statement")
    segments: List[PodcastSegment] = Field(default_factory=list, description="Ordered spoken dialogue turns")
    total_duration_estimate_sec: float = Field(default=0.0, ge=0.0, description="Estimated total run time in seconds")
    target_lufs: float = Field(default=-16.0, description="Target podcast integrated loudness (-16.0 LUFS)")

    def save_to_file(self, path: Path | str) -> None:
        """Atomically persist podcast plan to JSON."""
        import uuid
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(f".tmp_pod_{uuid.uuid4().hex[:8]}")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(self.model_dump_json(indent=2))
            tmp.replace(p)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    @classmethod
    def load_from_file(cls, path: Path | str) -> PodcastEpisodePlan:
        """Load podcast plan from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)
