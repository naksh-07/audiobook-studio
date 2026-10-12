#!/usr/bin/env python3
"""
Audiobook Factory - Contracts: Dynamic Production Playbook & Chapter Director Schemas.
Pydantic v2 data models for novel-wide and chapter-level artistic steering.
Zero cross-room dependencies.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class ProductionPlaybook(BaseModel):
    """Novel-level master prompt and artistic steering playbook."""
    model_config = ConfigDict(extra="ignore")

    project_id: str = Field(default="proj-novel", description="Canonical project ID")
    book_title: str = Field(default="Unknown Novel", description="Book title")
    author: str = Field(default="Unknown Author", description="Author name")
    literary_tradition: str = Field(default="UNIVERSAL_CONTEMPORARY", description="Extracted literary tradition")
    source_fidelity_tier: str = Field(default="RAW_UNRATED", description="'RAW_UNRATED', 'CLASSIC_REVERENT', or 'DRAMATIC_MODERN'")
    regional_dialect_cadence: str = Field(default="Standard Spoken Hindustani", description="Derived spoken register")
    world_atmosphere_summary: str = Field(default="", description="Summary of narrative atmosphere and tone")
    translation_system_prompt: str = Field(
        default="",
        description="Tailored system instruction containing novel-specific invariants, register, and loanword rules."
    )
    screenplay_system_prompt: str = Field(
        default="",
        description="Novel-specific dialogue subtext and dramatic delivery instructions."
    )
    narrator_master_demeanor: str = Field(
        default="calm, steady, articulate, measured audiobook delivery",
        description="Base vocal demeanor and demeanor tint for the novel's lead narrator."
    )
    banned_anachronisms: List[str] = Field(default_factory=list, description="Anachronistic words/concepts forbidden in this world")
    acceptable_loanwords: List[str] = Field(default_factory=list, description="Permitted vocabulary loanwords")
    proverb_style: str = Field(default="sense-for-sense cultural equivalent", description="Idiom transposition philosophy")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ChapterDirectorCard(BaseModel):
    """Chapter-level dramatic steering card for dynamic room injection."""
    model_config = ConfigDict(extra="ignore")

    chapter_num: int = Field(default=1, description="1-indexed chapter number")
    chapter_title: str = Field(default="", description="Chapter title or heading")
    scene_atmosphere: str = Field(
        default="Standard narrative encounter.",
        description="Atmospheric and emotional mood of the chapter."
    )
    dramatic_tension: str = Field(
        default="steady narrative progression",
        description="Dominant tension trajectory."
    )
    character_emotional_states: Dict[str, str] = Field(
        default_factory=dict,
        description="Key character emotional stances in this specific chapter."
    )
    pacing_cadence: str = Field(
        default="measured conversational with natural spoken pauses",
        description="Rhythm and clause length guidance for translation and delivery."
    )
    narrator_vocal_tint: str = Field(
        default="calm, observant, grounded delivery",
        description="Atmospheric vocal tint for narrator segments in this chapter."
    )
    key_motifs_or_sensory_details: List[str] = Field(
        default_factory=list,
        description="Sensory details, weather, ambient props, or recurring motifs."
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def to_prompt_context(self) -> str:
        """Formats the director card into a pristine Markdown block for injection into LLM prompts."""
        title_part = f": {str(self.chapter_title).strip()}" if self.chapter_title else ""
        parts = [
            f"### CHAPTER DRAMATIC STEERING (Chapter {self.chapter_num}{title_part}):",
            f"- **Scene Atmosphere & Setting**: {str(self.scene_atmosphere).strip()}",
            f"- **Dramatic Tension**: {str(self.dramatic_tension).strip()}",
            f"- **Pacing & Cadence**: {str(self.pacing_cadence).strip()}",
        ]
        if self.character_emotional_states:
            parts.append("- **Character Emotional Stances**:")
            for char, state in sorted(self.character_emotional_states.items(), key=lambda x: str(x[0])):
                parts.append(f"  * {str(char).strip()}: {str(state).strip()}")
        tint = str(self.narrator_vocal_tint or "").strip()
        if tint and tint.lower() not in ("none", "neutral"):
            parts.append(f"- **Narrator Delivery Demeanor**: {tint}")
        valid_motifs = [str(m).strip() for m in self.key_motifs_or_sensory_details if m and str(m).strip()]
        if valid_motifs:
            parts.append(f"- **Sensory Anchors & Motifs**: {', '.join(valid_motifs)}")
        return "\n".join(parts)
