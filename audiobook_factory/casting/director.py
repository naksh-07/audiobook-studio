#!/usr/bin/env python3
"""
Audiobook Factory - Room 3.5 Subsystem 1: Studio Voice Casting Director.
========================================================================
LLM-directed ensemble casting agent powered by ModelGateway (123+ API key pool).
Takes upstream character DNA (Room 1 BookBible & Room 1.5 ChapterGlossary)
and queries the 2,089-voice VoiceProfileRegistry to assign non-colliding,
dramatically grounded voices with regional Hindustani dialect matching
and Anime Seiyū child calibration.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Callable, Tuple

from audiobook_factory.logger import logger
from audiobook_factory.casting.contracts import (
    CanonicalVoiceProfile,
    CharacterCastAssignment,
    SpectralFormantProfile,
    CastLock,
    CastLockManifest,
)
from audiobook_factory.casting.registry import VoiceProfileRegistry
from audiobook_factory.casting.cast_lock import CastLockManager
from audiobook_factory.casting.gateway_bridge import execute_casting_llm

logger = logging.getLogger("AudiobookFactory")

CASTING_DIRECTOR_SYSTEM_PROMPT = """You are the Lead Casting Director for a prestige Hollywood & BBC Radio Audio Drama studio.
Your mission is to cast speaking roles in a dramatic novel with distinct, authentic vocal identities from the available voice catalog.

CRITICAL CASTING RULES:
1. GENDER ALIGNMENT: Strict gender matching unless explicitly casting children under Anime Seiyū rules.
2. ANIME SEIYŪ CHILD RULE:
   - For pre-pubescent child boys and girls (age < 13), ALWAYS choose a youthful female voice with bright upper harmonics (e.g. `hi-in-tutor-7`, `hi-in-tutor-9`, or `Leda`). NEVER cast an adult baritone!
   - For adolescent teen boys (age 13-18), prefer young male voices (age <= 28) or tomboyish female voices.
3. REGIONAL HINDUSTANI DIALECT MATCHING (for Hindi productions):
   - Haryanvi: Warriors, soldiers, martial brawlers, blunt guards.
   - Bhojpuri: Earthy rustics, butchers, tavernkeepers, commoners, warm loyal companions.
   - Awadhi: Poetic, gentle, maternal healers, priestesses, traditional aristocracy.
   - Bundeli: Rugged foresters, rebels, town magistrates.
   - Urdu: Aristocrats, courtly nobles, scholars, philosophers, elder mentors.
   - Standard: Urban, contemporary, neutral roles.
4. VOCAL CONTRAST IN ENSEMBLE:
   - Two characters who converse frequently MUST have distinct voice IDs and pitch registers!
   - Avoid assigning the same base voice to two characters of the same gender in the same social tier.
5. RESTRICTIONS:
   - You MUST pick voice IDs ONLY from the provided Available Voices Table.
   - Never invent voice IDs that do not exist in the table.
"""


class StudioCastingDirector:
    """
    Intelligent AI Voice Casting Director for audiobook ensembles.
    """

    def __init__(self, project_dir: Optional[Path | str] = None):
        self.project_dir = Path(project_dir).resolve() if project_dir else Path.cwd()
        self.registry = VoiceProfileRegistry.get_instance()
        self.lock_manager = CastLockManager(self.project_dir)

    def cast_character(
        self,
        character_name: str,
        gender: Optional[str] = None,
        archetype: str = "",
        dialect_hint: Optional[str] = None,
        is_child: bool = False,
        age_hint: Optional[int] = None,
        use_hindi: bool = True,
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> CastLock:
        """
        Dynamically casts a single character and locks their assignment permanently.
        """
        c_clean = character_name.strip()
        if not c_clean:
            raise ValueError("character_name cannot be empty.")

        # Check existing lock first (immutable cast lock)
        existing = self.lock_manager.get_lock(c_clean)
        if existing and existing.locked:
            logger.debug(f"[StudioCastingDirector] Reusing existing lock for '{c_clean}' -> {existing.voice_id}")
            return existing

        # Check supreme narrator default
        if c_clean.lower() in ("narrator", "narration", "सूत्रधार"):
            narr_voice = "Aoede" if not use_hindi else "hi-in-tutor-1"
            if gender and gender.lower() == "female" and use_hindi:
                narr_voice = "hi-in-concierge-3"
            return self.lock_manager.lock_character(
                character_id=c_clean.lower().replace(" ", "_"),
                character_name=c_clean,
                voice_id=narr_voice,
                selection_rationale="Supreme Narrator authoritative lock",
                calibration_overrides={"pitch": 1.0, "speed": 1.0},
            )

        # Collect already used voices in project
        used_voices = set()
        for lock in self.lock_manager.manifest.locks.values():
            if lock.locked:
                used_voices.add(lock.voice_id)

        lang_code = "hi-IN" if use_hindi else "en-US"
        cand_gender = (gender or "male").lower()
        if is_child and cand_gender == "male":
            cand_gender = "female"  # Anime Seiyū child boy rule

        # Format candidates table for prompt
        catalog_table = self.registry.get_formatted_catalog_for_prompt(
            language_code=lang_code,
            gender=cand_gender if cand_gender in ("male", "female") else None,
            exclude_voice_ids=used_voices,
            limit=25,
        )

        prompt = f"""Language Production: {"Hindi (Devanagari)" if use_hindi else "English"}
Character to Cast:
- Name: "{c_clean}"
- Gender: {gender or "neutral"}
- Age Hint: {age_hint if age_hint is not None else "Adult"}
- Is Child (< 13yo): {is_child}
- Archetype / Sociolect: "{archetype}"
- Dialect Hint: "{dialect_hint or 'Standard'}"

Already Cast Voices in Ensemble (AVOID DUPLICATION):
{json.dumps(list(used_voices), ensure_ascii=False)}

Available Voices Catalog:
{catalog_table}

Select the single best voice ID for this character.
Output JSON strictly adhering to this schema:
{{
  "assigned_voice_id": "string (must match a Voice ID from the table)",
  "dialect": "string (e.g. Haryanvi, Bhojpuri, Awadhi, Bundeli, Urdu, Standard)",
  "casting_rationale": "string (brief justification of why this voice fits the dramatic role)",
  "baseline_formants": {{
    "chest_resonance_150hz_db": 0.0,
    "nasal_presence_2800hz_db": 0.0,
    "throat_clarity_3200hz_db": 0.0,
    "air_shelf_8000hz_db": 0.0,
    "target_tempo_multiplier": 1.0
  }}
}}
"""

        try:
            if call_llm_fn:
                res = call_llm_fn(prompt=prompt, system_instruction=CASTING_DIRECTOR_SYSTEM_PROMPT, json_mode=True)
            else:
                res = execute_casting_llm(
                    prompt=prompt,
                    system_instruction=CASTING_DIRECTOR_SYSTEM_PROMPT,
                    task="directing",
                    json_mode=True,
                )
        except Exception as e:
            logger.warning(f"  [StudioCastingDirector] LLM call failed for '{c_clean}': {e}. Falling back to deterministic selection.")
            res = {}

        voice_id = res.get("assigned_voice_id") if isinstance(res, dict) else None
        # Verify voice exists in registry
        v_prof = self.registry.get_profile(voice_id) if voice_id else None

        # Gender alignment validation: if gender specified, must match profile gender (unless child)
        gender_invalid = False
        if v_prof and cand_gender in ("male", "female") and not is_child:
            if v_prof.gender and v_prof.gender.lower() != cand_gender:
                logger.warning(f"  [StudioCastingDirector] Gender mismatch: requested {cand_gender}, got {v_prof.gender} for '{c_clean}'. Recasting.")
                gender_invalid = True

        # Collision validation: if voice already used in project and alternatives exist, recast
        collision_invalid = voice_id in used_voices if voice_id else False

        if not voice_id or not v_prof or gender_invalid or collision_invalid:
            # Deterministic fallback query respecting gender and excluding already used voices
            fallback_cands = self.registry.query_profiles(
                language_code=lang_code,
                gender=cand_gender if cand_gender in ("male", "female") else None,
                dialect=dialect_hint,
                exclude_voice_ids=used_voices,
                limit=1,
            )
            if fallback_cands:
                voice_id = fallback_cands[0].voice_id
            elif not v_prof:
                voice_id = "hi-in-tutor-7" if (use_hindi and is_child) else ("hi-in-advisor-10" if use_hindi else "Charon")

        # Anime Seiyū Child Rule Guard:
        # If character is pre-pubescent child (< 13yo), NEVER allow an adult male baritone!
        if is_child:
            v_prof = self.registry.get_profile(voice_id)
            if v_prof and (v_prof.gender == "male" or (v_prof.perceived_age and v_prof.perceived_age > 30)):
                logger.info(f"  [Anime Seiyū Guard] Re-casting child '{c_clean}' away from adult voice '{voice_id}' to youthful voice.")
                child_cands = self.registry.query_profiles(
                    language_code=lang_code,
                    gender="female",
                    pitch_tier="high",
                    exclude_voice_ids=used_voices,
                    limit=1,
                )
                voice_id = child_cands[0].voice_id if child_cands else ("hi-in-tutor-7" if use_hindi else "Leda")


        rationale = res.get("casting_rationale") if isinstance(res, dict) else "Studio Casting Director assignment"
        formants = res.get("baseline_formants") if isinstance(res, dict) and isinstance(res.get("baseline_formants"), dict) else {}

        lock = self.lock_manager.lock_character(
            character_id=c_clean.lower().replace(" ", "_"),
            character_name=c_clean,
            voice_id=voice_id,
            selection_rationale=rationale,
            calibration_overrides=formants,
        )
        return lock

    def cast_ensemble_from_roster(
        self,
        raw_characters: List[Dict[str, Any]],
        use_hindi: bool = True,
        force_recast: bool = False,
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> CastLockManifest:
        """
        Casts a complete character roster for a project novel ensemble.
        """
        for char_info in raw_characters:
            name = (char_info.get("canonical_name") or char_info.get("english_name") or char_info.get("name") or "").strip()
            if not name or name.lower() in ("foley", "sfx"):
                continue

            if not force_recast and self.lock_manager.is_locked(name):
                continue

            gender = char_info.get("gender")
            arch = char_info.get("archetype") or char_info.get("vocal_archetype") or ""
            is_ch = bool(char_info.get("is_child", False))
            dialect = char_info.get("recommended_dialect") or char_info.get("dialect")
            age = char_info.get("age")
            age_int = int(age) if isinstance(age, int) or (isinstance(age, str) and age.isdigit()) else None

            self.cast_character(
                character_name=name,
                gender=gender,
                archetype=arch,
                dialect_hint=dialect,
                is_child=is_ch,
                age_hint=age_int,
                use_hindi=use_hindi,
                call_llm_fn=call_llm_fn,
            )

        return self.lock_manager.manifest
