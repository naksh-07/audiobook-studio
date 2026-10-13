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
from audiobook_factory.casting.phonetic_transliteration import (
    derive_devanagari_name,
    is_devanagari,
)

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
        display_name_hi: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> CastLock:
        """
        Dynamically casts a single character and locks their assignment permanently.
        Preserves bilingual Devanagari and Latin aliases, enforces strict gender congruence,
        and guarantees narrator vocal separation (Aoede reserved strictly for narration).
        """
        c_clean = character_name.strip()
        if not c_clean:
            raise ValueError("character_name cannot be empty.")

        disp_hi = display_name_hi.strip() if display_name_hi else None
        if not disp_hi or not is_devanagari(disp_hi):
            derived_hi, dev_aliases = derive_devanagari_name(
                c_clean, project_dir=self.project_dir, aliases=aliases
            )
            disp_hi = derived_hi or disp_hi
            if aliases:
                for da in dev_aliases:
                    if da and da not in aliases:
                        aliases.append(da)
            else:
                aliases = list(dev_aliases)

        alias_set = set()
        if aliases:
            for a in aliases:
                if a and str(a).strip():
                    alias_set.add(str(a).strip())
        if disp_hi:
            alias_set.add(disp_hi)
        if c_clean:
            alias_set.add(c_clean)
        all_aliases = sorted(list(alias_set))

        # Check existing lock first (immutable cast lock)
        existing = self.lock_manager.get_lock(c_clean)
        if not existing and disp_hi:
            existing = self.lock_manager.get_lock(disp_hi)
        if not existing:
            for a in all_aliases:
                existing = self.lock_manager.get_lock(a)
                if existing:
                    break

        if existing and existing.locked:
            logger.debug(f"[StudioCastingDirector] Reusing existing lock for '{c_clean}' -> {existing.voice_id}")
            return existing

        # Check supreme narrator default
        if c_clean.lower() in ("narrator", "narration", "सूत्रधार") or (disp_hi and disp_hi.lower() in ("narrator", "narration", "सूत्रधार")):
            narr_voice = "Aoede"
            for a in ("सूत्रधार", "Narrator", "narration"):
                if a not in all_aliases:
                    all_aliases.append(a)
            return self.lock_manager.lock_character(
                character_id=c_clean.lower().replace(" ", "_"),
                character_name=c_clean,
                display_name_hi=disp_hi or "सूत्रधार",
                aliases=all_aliases,
                voice_id=narr_voice,
                selection_rationale="Supreme Narrator authoritative lock",
                calibration_overrides={"pitch": 1.0, "speed": 1.0},
            )

        # Collect already used voices in project
        used_voices = set()
        # Reserved Narrator Separation: Aoede is reserved exclusively for Narration
        used_voices.add("Aoede")
        for lock in self.lock_manager.manifest.locks.values():
            if lock.locked:
                used_voices.add(lock.voice_id)

        lang_code = "hi-IN" if use_hindi else "en-US"
        cand_gender = (gender or "").lower()
        if cand_gender not in ("male", "female"):
            female_markers = (
                "female", "woman", "girl", "lady", "queen", "princess", "sorceress",
                "witch", "priestess", "maiden", "matron", "mother", "daughter", "sister",
                "damsel", "nun", "aunt", "niece", "bride", "widow", "heroine",
                "स्त्री", "महिला", "लड़की", "रानी", "माता", "कन्या", "युवती", "बहन", "पत्नी"
            )
            arch_lower = (archetype or "").lower()
            name_lower = c_clean.lower()
            if any(m in arch_lower for m in female_markers) or any(m in name_lower for m in female_markers):
                cand_gender = "female"
            else:
                cand_gender = "male"

        if is_child and cand_gender == "male":
            cand_gender = "female"  # Anime Seiyū child boy rule

        # Archetype Matching Preference
        arch_low = (archetype or "").lower()
        archetype_pref: Optional[str] = None
        if cand_gender == "male":
            if any(w in arch_low for w in ("bard", "minstrel", "witty", "companion", "jester", "rogue")):
                archetype_pref = "Puck"
            elif any(w in arch_low for w in ("knight", "noble", "aristocrat", "solemn", "paladin")):
                archetype_pref = "Algieba" if "Algieba" not in used_voices else "Fenrir"
            elif any(w in arch_low for w in ("warrior", "mercenary", "gravelly", "hardened", "soldier", "brute", "veteran")):
                archetype_pref = "Algenib" if "Algenib" not in used_voices else "Charon"
        elif cand_gender == "female":
            if any(w in arch_low for w in ("sorceress", "queen", "regal", "witch", "leader")):
                archetype_pref = "Kore"
            elif any(w in arch_low for w in ("young", "girl", "maiden", "vibrant", "princess", "daughter", "apprentice")) or is_child:
                archetype_pref = "Leda"
            elif any(w in arch_low for w in ("soft", "gentle", "intimate", "healer", "poetic")):
                archetype_pref = "Achernar"
            elif any(w in arch_low for w in ("matron", "maternal", "mother", "elder", "priestess")):
                archetype_pref = "Callisto"

        # Format candidates table for prompt
        catalog_table = self.registry.get_formatted_catalog_for_prompt(
            language_code=lang_code,
            gender=cand_gender,
            exclude_voice_ids=used_voices,
            limit=25,
        )

        prompt = f"""Language Production: {"Hindi (Devanagari)" if use_hindi else "English"}
Character to Cast:
- Name: "{c_clean}"
- Gender: {cand_gender}
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

        # Gender alignment validation: must match profile gender (unless child)
        gender_invalid = False
        if v_prof and not is_child:
            if v_prof.gender and v_prof.gender.lower() != cand_gender:
                logger.warning(f"  [StudioCastingDirector] Gender mismatch: requested {cand_gender}, got {v_prof.gender} for '{c_clean}'. Recasting.")
                gender_invalid = True

        # Narrator separation: non-narrator characters cannot use Aoede
        if voice_id == "Aoede":
            gender_invalid = True

        # Collision validation: if voice already used in project and alternatives exist, recast
        collision_invalid = voice_id in used_voices if voice_id else False

        fallback_male_voices = ["Fenrir", "Orus", "Algieba", "Achird", "Algenib", "Enceladus", "Puck", "Zephyr", "Charon"]
        fallback_female_voices = ["Kore", "Leda", "Achernar", "Callisto"]

        if not voice_id or not v_prof or gender_invalid or collision_invalid:
            # First attempt: use preferred archetype voice if available and unused
            if archetype_pref and archetype_pref not in used_voices:
                voice_id = archetype_pref
            else:
                # Deterministic fallback query respecting gender and excluding already used voices
                fallback_cands = self.registry.query_profiles(
                    language_code=lang_code,
                    gender=cand_gender,
                    dialect=dialect_hint,
                    exclude_voice_ids=used_voices,
                    limit=1,
                )
                if fallback_cands:
                    voice_id = fallback_cands[0].voice_id
                else:
                    if cand_gender == "female":
                        avail_f = [v for v in fallback_female_voices if v not in used_voices]
                        voice_id = avail_f[0] if avail_f else fallback_female_voices[len(self.lock_manager.manifest.locks) % len(fallback_female_voices)]
                    else:
                        avail_m = [v for v in fallback_male_voices if v not in used_voices]
                        voice_id = avail_m[0] if avail_m else fallback_male_voices[len(self.lock_manager.manifest.locks) % len(fallback_male_voices)]

        # Specific archetype anchors:
        # Bard / Minstrel / Witty Companion -> strictly Puck (pitch: 1.0, speed: 1.0)
        # Female Sorceress / Queen -> Kore
        # Maiden / Young girl -> Leda or Achernar (pitch: 1.0)
        rationale = res.get("casting_rationale") if isinstance(res, dict) else "Studio Casting Director assignment"
        formants = res.get("baseline_formants") if isinstance(res, dict) and isinstance(res.get("baseline_formants"), dict) else {}

        if cand_gender == "male" and any(w in arch_low for w in ("bard", "minstrel", "witty", "companion", "jester")):
            voice_id = "Puck"
            formants["pitch"] = 1.0
            formants["speed"] = 1.0
        elif cand_gender == "female" and any(w in arch_low for w in ("sorceress", "queen", "regal", "witch")):
            voice_id = "Kore" if "Kore" not in used_voices else "Callisto"
        elif (is_child or any(w in arch_low for w in ("maiden", "young girl", "princess", "daughter", "child"))) and cand_gender == "female":
            voice_id = "Leda" if "Leda" not in used_voices else "Achernar"
            formants["pitch"] = 1.0

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

        # Strict Female Invariant Guard: Under no circumstances may a female role receive a male voice or Aoede
        if cand_gender == "female":
            prof = self.registry.get_profile(voice_id)
            if not prof or prof.gender != "female" or voice_id == "Aoede":
                avail_fem = [v for v in ("Kore", "Leda", "Achernar", "Callisto") if v not in used_voices]
                voice_id = avail_fem[0] if avail_fem else ("Leda" if is_child else "Kore")

        # Strictly clamp pitch overrides to safe vocal bounds: 0.94 <= pitch <= 1.06 (hard ceiling [0.88, 1.12])
        if "pitch" in formants:
            try:
                p_val = float(formants["pitch"])
                formants["pitch"] = max(0.94, min(1.06, p_val))
            except (ValueError, TypeError):
                formants["pitch"] = 1.0

        lock = self.lock_manager.lock_character(
            character_id=c_clean.lower().replace(" ", "_"),
            character_name=c_clean,
            display_name_hi=disp_hi,
            aliases=all_aliases,
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
        Preserves bilingual Devanagari and Latin aliases in the manifest and voice registry.
        """
        for char_info in raw_characters:
            name = (char_info.get("canonical_name") or char_info.get("english_name") or char_info.get("name") or "").strip()
            if not name or name.lower() in ("foley", "sfx"):
                continue

            display_name_hi = (
                char_info.get("display_name_hi") or
                char_info.get("hindi_name") or
                char_info.get("name_hi") or
                char_info.get("display_name")
            )
            raw_aliases = char_info.get("aliases") or []
            aliases = [str(a).strip() for a in raw_aliases if a and str(a).strip()]

            # Derive authentic Devanagari transliteration if missing or Latin
            if not display_name_hi or not is_devanagari(display_name_hi):
                derived_hi, dev_aliases = derive_devanagari_name(
                    name, project_dir=self.project_dir, aliases=aliases
                )
                display_name_hi = derived_hi or display_name_hi
                for da in dev_aliases:
                    if da and da not in aliases:
                        aliases.append(da)

            if display_name_hi and display_name_hi not in aliases:
                aliases.append(display_name_hi)

            if not force_recast:
                if self.lock_manager.is_locked(name):
                    continue
                if display_name_hi and self.lock_manager.is_locked(display_name_hi):
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
                display_name_hi=display_name_hi,
                aliases=aliases,
                call_llm_fn=call_llm_fn,
            )

        return self.lock_manager.manifest
