#!/usr/bin/env python3
"""
Audiobook Studio - Unified Podcast & Verbalization Data Contracts.
Defines strongly-typed Pydantic v2 schemas for:
1. Research paper/whitepaper verbalization (dual-host & narrative).
2. Chapter narrative 2-host conversational podcast episodes.
3. Host persona profiles, spoken-first breathability segments, and episode structures.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, AliasChoices

# Unified HostRole covering both whitepaper and narrative dynamics
HostRole = Literal[
    "lead_explainer",
    "inquisitive_cohost",
    "solo_narrator",
    "inquisitive_driver",
    "domain_expert",
    "guest_commentator",
]

VerbalizationStyle = Literal[
    "conversational_podcast",
    "formal_lecture",
    "narrative_audiobook",
]

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
    Unified configuration and vocal persona profile for a podcast host.
    Compatible with both whitepaper verbalization and chapter narrative podcasting.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    host_id: str = Field(
        default="",
        validation_alias=AliasChoices("host_id", "id", "character"),
        description="Unique host identifier, e.g. 'host_a' or 'host_b'"
    )
    name: str = Field(
        validation_alias=AliasChoices("name", "display_name"),
        description="Display name for the host"
    )
    role: HostRole = Field(
        default="lead_explainer",
        description="Conversational dynamic role"
    )
    voice_id: str = Field(
        default="Charon",
        validation_alias=AliasChoices("voice_id", "default_voice", "voice"),
        description="Gemini TTS voice name (e.g. Puck, Aoede, Fenrir, Charon)"
    )
    pitch_shift: float = Field(default=0.0, ge=-20.0, le=20.0, description="Pitch semitone offset (-12 to +12)")
    speed_multiplier: float = Field(default=1.0, ge=0.7, le=1.4, description="Speech cadence rate multiplier")
    pan: float = Field(default=0.0, ge=-1.0, le=1.0, description="Acoustic azimuth stereo pan (-1.0 Left to +1.0 Right)")
    energy_baseline: float = Field(default=0.8, ge=0.2, le=1.0, description="Base vocal projection energy")
    acting_style: str = "engaging, articulate, measured, clear"
    formant_preset: Optional[str] = None
    interjection_lexicon: List[str] = Field(
        default_factory=list,
        description="Natural spoken conversational particles and interjections"
    )

    def model_post_init(self, __context: Any) -> None:
        if not self.host_id and self.name:
            self.host_id = self.name.lower().replace(" ", "_")

    @property
    def id(self) -> str:
        return self.host_id

    @property
    def default_voice(self) -> str:
        return self.voice_id


class PodcastSegment(BaseModel):
    """
    Atomic spoken dialogue turn in a podcast script or episode.
    Designed for maximum breathability (<= 22 words) and acoustic naturalness.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    segment_id: str = Field(
        default="",
        validation_alias=AliasChoices("segment_id", "id"),
        description="Unique turn ID"
    )
    index: int = Field(default=1, ge=1, description="1-indexed sequence number in episode")
    speaker: str = Field(..., description="Host name or character name in re-enactment")
    character_name: str = Field(
        default="",
        validation_alias=AliasChoices("character_name", "character", "display_name"),
        description="Character name"
    )
    text: str = Field(..., description="Spoken-first natural dialogue text")
    emotion: str = Field(default="neutral", description="Emotional vocal delivery tag")
    section_type: PodcastSectionType = Field(default="scene_deepdive", description="Episode structural section")
    acting_directive: str = "natural conversational delivery"
    source_block_id: Optional[str] = None
    source_block_type: Optional[str] = None
    pause_after_ms: int = Field(default=350, ge=100, le=3000, description="Silence after turn in ms")
    interjection_type: Optional[str] = Field(default=None, description="Type of conversational reaction")
    acting: Dict[str, Any] = Field(default_factory=dict, description="Voice acting delivery hints")
    spatial: Dict[str, Any] = Field(default_factory=dict, description="Stereo pan and acoustic environment")
    beat_ref: Optional[str] = Field(default=None, description="Referenced DramaticBeat ID from core AST")
    spu_ref: Optional[str] = Field(default=None, description="Referenced source paragraph SPU ID")
    words: int = 0

    def model_post_init(self, __context: Any) -> None:
        if not self.character_name:
            self.character_name = self.speaker
        if not self.segment_id:
            self.segment_id = f"seg_{self.index:03d}"
        if not self.words and self.text:
            self.words = len(self.text.split())

    @property
    def id(self) -> str:
        return self.segment_id


class PodcastScript(BaseModel):
    """Complete structured dual-host or narrative podcast script."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    podcast_id: str = Field(validation_alias=AliasChoices("podcast_id", "chapter_id"))
    title: str
    source_document_id: str = Field(default="")
    style: VerbalizationStyle = "conversational_podcast"
    hosts: List[HostProfile] = Field(default_factory=list, validation_alias=AliasChoices("hosts", "cast"))
    segments: List[PodcastSegment] = Field(default_factory=list)
    total_words: int = 0
    total_segments: int = 0
    estimated_duration_sec: float = 0.0

    def model_post_init(self, __context: Any) -> None:
        if not self.total_segments:
            self.total_segments = len(self.segments)
        if not self.total_words:
            self.total_words = sum(s.words for s in self.segments)
        if not self.estimated_duration_sec and self.total_words:
            self.estimated_duration_sec = round(self.total_words / 2.5, 2)

    def to_screenplay_json(self) -> Dict[str, Any]:
        """Projects podcast script into standard Room 4 TTS screenplay format."""
        return {
            "chapter_id": self.podcast_id,
            "title": self.title,
            "total_segments": self.total_segments,
            "total_words": self.total_words,
            "estimated_duration_sec": self.estimated_duration_sec,
            "cast": [
                {
                    "character": h.host_id or h.name,
                    "display_name": h.name,
                    "voice": h.voice_id,
                    "role": h.role,
                }
                for h in self.hosts
            ],
            "segments": [
                {
                    "id": s.segment_id,
                    "speaker": s.speaker,
                    "character": s.character_name,
                    "text": s.text,
                    "acting_directive": s.acting_directive,
                    "pause_after_ms": s.pause_after_ms,
                    "words": s.words,
                }
                for s in self.segments
            ],
        }


class PodcastEpisodePlan(BaseModel):
    """
    Holistic 5-Part 2-Host Podcast Episode Plan (durable artifact: podcast_plan.json).
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

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


class PodcastProductionResult(BaseModel):
    """Execution telemetry and output references for synthesized and mastered podcast audio."""
    model_config = ConfigDict(extra="ignore")

    podcast_id: str
    status: Literal["SUCCESS", "FAILED"] = "SUCCESS"
    total_segments: int = 0
    total_words: int = 0
    duration_sec: float = 0.0
    canonical_book_path: Optional[str] = None
    script_path: Optional[str] = None
    dialogue_raw_path: Optional[str] = None
    mastered_audio_path: Optional[str] = None
    integrated_lufs: float = -19.0
    true_peak_db: float = -1.5
    loudness_range_lu: float = 0.0
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
