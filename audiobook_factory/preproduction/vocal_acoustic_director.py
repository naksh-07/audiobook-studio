#!/usr/bin/env python3
"""
Audiobook Factory - Room 1 Subsystem 6: Vocal Acoustic Director.
==============================================================
Profiles narrative physical environments and synthesizes the authoritative vocal_spaces.json.
Enforces the Vocals-Only Invariant: 0 Foley SFX tracks, 0 BGM generation.
100% focused on Audible-standard vocal excellence, room impulse response modeling,
distance staging, and 4D parametric EQ formant DSP generation.
"""

from __future__ import annotations
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Literal
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict

from audiobook_factory.llm_client import call_gemini as default_call_gemini
from audiobook_factory.model_manager import get_model_manager, TaskType
from audiobook_factory.safety import get_dramatic_fiction_framing

logger = logging.getLogger("AudiobookFactory")


class VocalSpaceProfile(BaseModel):
    """Acoustic room impulse and vocal staging configuration for a physical space."""
    model_config = ConfigDict(extra="ignore")

    reverb_type: str = Field(
        default="medium_room",
        description="e.g. medium_wooden_hall, damp_stone_vault, dense_outdoor_forest, intimate_parlor, open_meadow"
    )
    wet_mix: float = Field(
        default=0.12,
        ge=0.01,
        le=0.45,
        description="Wet signal ratio for room reverberation (0.02 - 0.40)"
    )
    predelay_ms: int = Field(
        default=18,
        ge=2,
        le=80,
        description="Early reflection delay in milliseconds (4 - 60ms)"
    )
    decay_time_s: float = Field(
        default=1.2,
        ge=0.2,
        le=5.0,
        description="RT60 reverberation decay time in seconds (0.2 - 4.5s)"
    )
    proximity_staging: Literal[
        "intimate_whisper", "conversational_close", "medium_room", "spatial_echo", "distant_shout", "direct_voice", "dry_outdoor"
    ] = "conversational_close"
    high_shelf_damping_db: float = Field(
        default=-1.5,
        description="High frequency air and material absorption damping in dB"
    )
    low_shelf_warmth_db: float = Field(
        default=0.0,
        description="Low frequency proximity warmth in dB"
    )
    dominant_materials: List[str] = Field(
        default_factory=lambda: ["wood", "stone", "cloth"],
        description="Dominant physical materials influencing room reflections"
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class VocalSpacesManifest(BaseModel):
    """Canonical Manifest of all vocal room acoustics across the novel."""
    model_config = ConfigDict(extra="ignore")

    project_id: str
    book_title: str
    primary_era: str = "universal_contemporary"
    spaces: Dict[str, VocalSpaceProfile] = Field(default_factory=dict)

    def to_legacy_sonic_bible(self) -> Dict[str, Any]:
        """Produces a clean backwards-compatible sonic_bible.json without SFX/BGM pollution."""
        acoustic_spaces = {}
        for sp_name, sp_obj in self.spaces.items():
            acoustic_spaces[sp_name] = {
                "reverb_type": sp_obj.reverb_type,
                "wet_mix": sp_obj.wet_mix,
                "predelay_ms": sp_obj.predelay_ms,
                "decay_time_s": sp_obj.decay_time_s,
                "dominant_materials": sp_obj.dominant_materials,
            }

        return {
            "project_id": self.project_id,
            "book_title": self.book_title,
            "primary_era": self.primary_era,
            "acoustic_spaces": acoustic_spaces,
            "signature_foley_palettes": {},
            "world_ambience_motifs": [],
        }


class VocalAcousticDirector:
    """
    Subsystem 6 Showrunner: Profiles novel environments into spatial vocal impulse acoustics
    and generates studio FFmpeg 4D formant filter chains.
    """

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def _resolve_model(self) -> str:
        if self.model:
            return self.model
        return get_model_manager().resolve_active_model(TaskType.DIRECTING)

    def design_vocal_spaces(
        self,
        novel_text_sample: str,
        book_metadata: Dict[str, Any],
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> VocalSpacesManifest:
        """
        Synthesizes the complete vocal_spaces.json profiling the novel's vocal acoustics.
        """
        model = self.model or ("mock-model" if call_llm_fn else self._resolve_model())
        book_title = book_metadata.get("title", "Unknown Novel")
        author = book_metadata.get("author", "Unknown Author")
        project_slug = book_metadata.get("project_slug", "novel")

        fiction_framing = get_dramatic_fiction_framing(title=book_title, author=author)

        sys_prompt = (
            fiction_framing +
            "You are an Academy-Award winning Audio Drama Supervising Sound Editor and Vocal Acoustic Architect.\n"
            "Analyze the novel's recurring environments, rooms, outdoor landscapes, and architectural materials.\n"
            "Synthesize an authoritative vocal_spaces.json specifying pure room impulse acoustics and proximity staging for voice actors.\n\n"
            "NON-NEGOTIABLE VOCALS-ONLY INVARIANT:\n"
            "- Focus 100% on VOCAL ACOUSTICS (room reverb, early reflections, proximity staging, high-frequency damping).\n"
            "- STRICTLY FORBIDDEN: Do NOT generate Foley sound effects, footstep banks, or background music cues.\n\n"
            "Requirements per space:\n"
            "- 'reverb_type': descriptive acoustic preset (e.g. 'medium_wooden_hall', 'damp_stone_vault', 'dense_outdoor_forest', 'intimate_parlor')\n"
            "- 'wet_mix': float between 0.04 (dry/outdoor) and 0.35 (cavernous/cathedral)\n"
            "- 'predelay_ms': int between 6ms and 45ms\n"
            "- 'decay_time_s': float between 0.4s and 3.5s\n"
            "- 'proximity_staging': 'intimate_whisper' | 'conversational_close' | 'medium_room' | 'spatial_echo' | 'distant_shout'\n"
            "- 'high_shelf_damping_db': float between -4.0dB and 0.0dB\n"
            "- 'dominant_materials': list of strings (e.g. ['wood', 'stone', 'cloth', 'mud', 'vegetation'])"
        )

        prompt = f"""Book Title: {book_title}
Author: {author}

Passages Sampled Across Novel:
\"\"\"
{novel_text_sample[:16000]}
\"\"\"

Output JSON: An authoritative vocal spaces manifest:
{{
  "project_id": "proj-{project_slug}",
  "book_title": "{book_title}",
  "primary_era": "string (e.g. 'medieval_mythic', 'victorian_gothic', 'contemporary_noir')",
  "spaces": {{
    "space_key_name": {{
      "reverb_type": "string",
      "wet_mix": 0.15,
      "predelay_ms": 20,
      "decay_time_s": 1.2,
      "proximity_staging": "conversational_close",
      "high_shelf_damping_db": -1.5,
      "low_shelf_warmth_db": 0.0,
      "dominant_materials": ["wood", "stone"]
    }}
  }}
}}
"""
        logger.info(f"  [VocalAcousticDirector] Profiling vocal spaces for '{book_title}' using {model}...")

        raw_data: Dict[str, Any] = {}
        try:
            if call_llm_fn:
                res = call_llm_fn(prompt=prompt, system_instruction=sys_prompt, model=model, json_mode=True)
                if isinstance(res, str):
                    import json_repair
                    raw_data = json_repair.loads(res)
                elif isinstance(res, dict):
                    raw_data = res
            else:
                raw_data = default_call_gemini(
                    prompt=prompt,
                    system_instruction=sys_prompt,
                    task_type=TaskType.DIRECTING,
                    response_mime_type="application/json",
                    max_output_tokens=8192,
                    thinking_budget=1024,
                    max_retries=6,
                    model=model,
                )
        except Exception as e:
            logger.warning(f"  [!] VocalAcousticDirector error: {e}. Falling back to default universal vocal spaces.")
            raw_data = {}

        if not isinstance(raw_data, dict) or not raw_data.get("spaces"):
            raw_data = self._build_default_manifest(project_slug, book_title)

        # Ensure correct fields
        raw_data.setdefault("project_id", f"proj-{project_slug}")
        raw_data.setdefault("book_title", book_title)
        raw_data.setdefault("primary_era", "universal_contemporary")

        return VocalSpacesManifest.model_validate(raw_data)

    @classmethod
    def build_vocal_filter_complex(
        cls,
        character_entity: Optional[Any] = None,
        space_name: str = "",
        spaces_manifest: Optional[VocalSpacesManifest] = None,
        pitch_shift_pct: Optional[float] = None,
        tempo_scale: Optional[float] = None,
        eq_formant: Optional[str] = None,
    ) -> str:
        """
        Builds a studio-grade FFmpeg filter chain for a vocal take:
        1. 4D Formant Morphing: asetrate (pitch), atempo (speed), parametric equalizer
        2. Proximity & Spatial Room Reverb: wet mix, decay time, predelay
        """
        eff_pitch_pct = pitch_shift_pct
        eff_tempo = tempo_scale
        eff_eq = eq_formant

        if character_entity is not None:
            if eff_pitch_pct is None:
                eff_pitch_pct = getattr(character_entity, "pitch_shift_pct", 0.0)
            if eff_tempo is None:
                eff_tempo = getattr(character_entity, "tempo_scale", 1.0)
            if eff_eq is None:
                eff_eq = getattr(character_entity, "eq_formant", "")

        eff_pitch_pct = eff_pitch_pct or 0.0
        eff_tempo = eff_tempo or 1.0
        eff_eq = eff_eq or ""

        filters: List[str] = []

        # 1. Highpass clean subsonic rumble (Audible Broadcast standard: 60Hz)
        filters.append("highpass=f=60:poles=2")

        # 2. Pitch morphing via asetrate + compensatory tempo
        if abs(eff_pitch_pct) > 0.5:
            ratio = max(0.1, 1.0 + (eff_pitch_pct / 100.0))
            sample_rate = 24000
            new_rate = int(round(sample_rate * ratio))
            # Compensate tempo so duration stays natural
            inv_tempo = 1.0 / ratio
            filters.append(f"asetrate={new_rate},aresample={sample_rate}")
            if abs(inv_tempo - 1.0) > 0.01:
                filters.append(f"atempo={inv_tempo:.4f}")

        # 3. Dedicated tempo scale (if different from 1.0)
        if abs(eff_tempo - 1.0) > 0.01:
            filters.append(f"atempo={eff_tempo:.4f}")

        # 4. Parametric EQ Formant curves
        if eff_eq:
            for eq_clause in eff_eq.split(","):
                eq_clean = eq_clause.strip()
                if eq_clean and eq_clean not in filters:
                    filters.append(eq_clean)

        # 5. Spatial Room Impulse & Reverb Staging
        if spaces_manifest and space_name and space_name in spaces_manifest.spaces:
            space_prof = spaces_manifest.spaces[space_name]
            reverb_filter = cls.build_room_reverb_filter(space_prof)
            if reverb_filter:
                filters.append(reverb_filter)

        return ",".join(filters)

    @classmethod
    def build_room_reverb_filter(cls, space_profile: VocalSpaceProfile) -> str:
        """
        Synthesizes a clean, non-destructive FFmpeg aecho / damping filter for room acoustics.
        """
        wet = space_profile.wet_mix
        decay = min(0.65, max(0.15, space_profile.decay_time_s * 0.18))
        predelay = max(10, min(80, space_profile.predelay_ms))

        # Build clean studio echo filter: aecho=in_gain:out_gain:delays:decays
        in_gain = 0.95
        out_gain = round(wet, 3)
        echo_str = f"aecho={in_gain}:{out_gain}:{predelay}:{decay:.2f}"

        # High-shelf air absorption damping if specified
        if space_profile.high_shelf_damping_db < -0.2:
            damp_eq = f"equalizer=f=4500:t=q:w=1.0:g={space_profile.high_shelf_damping_db:.1f}"
            return f"{echo_str},{damp_eq}"

        return echo_str

    @staticmethod
    def _build_default_manifest(project_slug: str, book_title: str) -> Dict[str, Any]:
        """Fallback clean vocal spaces manifest."""
        return {
            "project_id": f"proj-{project_slug}",
            "book_title": book_title,
            "primary_era": "universal_contemporary",
            "spaces": {
                "intimate_interior": {
                    "reverb_type": "furnished_room",
                    "wet_mix": 0.08,
                    "predelay_ms": 12,
                    "decay_time_s": 0.8,
                    "proximity_staging": "conversational_close",
                    "high_shelf_damping_db": -1.0,
                    "dominant_materials": ["wood", "cloth"],
                },
                "tavern_or_hall": {
                    "reverb_type": "medium_wooden_hall",
                    "wet_mix": 0.16,
                    "predelay_ms": 22,
                    "decay_time_s": 1.4,
                    "proximity_staging": "conversational_close",
                    "high_shelf_damping_db": -1.5,
                    "dominant_materials": ["wood", "stone"],
                },
                "outdoor_open": {
                    "reverb_type": "open_landscape",
                    "wet_mix": 0.04,
                    "predelay_ms": 8,
                    "decay_time_s": 0.4,
                    "proximity_staging": "direct_voice",
                    "high_shelf_damping_db": -0.5,
                    "dominant_materials": ["dirt", "vegetation"],
                },
                "cavern_or_vault": {
                    "reverb_type": "damp_stone_vault",
                    "wet_mix": 0.28,
                    "predelay_ms": 35,
                    "decay_time_s": 2.6,
                    "proximity_staging": "spatial_echo",
                    "high_shelf_damping_db": -2.5,
                    "dominant_materials": ["stone", "water"],
                },
            },
        }
