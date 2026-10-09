#!/usr/bin/env python3
"""
Audiobook Studio - Podcast & Verbalization Data Contracts.
Defines strongly-typed Pydantic v2 schemas for dual-host and narrative
podcast scripts, host profiles, and verbalization segment units.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, AliasChoices


HostRole = Literal["lead_explainer", "inquisitive_cohost", "solo_narrator"]
VerbalizationStyle = Literal["conversational_podcast", "formal_lecture", "narrative_audiobook"]


class HostProfile(BaseModel):
    """Configuration profile for a podcast host or commentator."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = Field(validation_alias=AliasChoices("id", "character"))
    name: str = Field(validation_alias=AliasChoices("name", "display_name"))
    role: HostRole = "lead_explainer"
    default_voice: str = Field(default="Charon", validation_alias=AliasChoices("default_voice", "voice"))
    acting_style: str = "engaging, articulate, measured, clear"
    formant_preset: Optional[str] = None


class PodcastSegment(BaseModel):
    """Atomic spoken dialogue turn in a podcast script."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    segment_id: str = Field(validation_alias=AliasChoices("segment_id", "id"))
    speaker: str
    character_name: str = Field(default="", validation_alias=AliasChoices("character_name", "character", "display_name"))
    text: str
    acting_directive: str = "natural conversational delivery"
    source_block_id: Optional[str] = None
    source_block_type: Optional[str] = None
    pause_after_ms: int = 250
    words: int = 0

    def model_post_init(self, __context: Any) -> None:
        if not self.character_name:
            self.character_name = self.speaker
        if not self.words and self.text:
            self.words = len(self.text.split())


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
            # Approx 150 words per minute for natural podcast cadence (~2.5 words/sec)
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
                    "character": h.id,
                    "display_name": h.name,
                    "voice": h.default_voice,
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

