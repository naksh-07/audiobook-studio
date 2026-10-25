#!/usr/bin/env python3
"""
Audiobook Factory - Room 3.5: Voice Profile Registry.
=====================================================
Unified canonical catalog registry providing sub-millisecond query,
semantic archetype search, dialect matching, and provider capability
inspection across 2,089 curated Google Gemini and open-source TTS voices.
"""

from __future__ import annotations
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

from audiobook_factory.logger import logger
from audiobook_factory.casting.contracts import (
    CanonicalVoiceProfile,
    ProviderCapabilities,
    CharacterCastingProfile,
    CastingGender,
    PitchBand,
)

CURATED_CATALOG_JSON = Path(__file__).resolve().parent.parent / "tts" / "data" / "curated_voice_catalog.json"
CATALOG_DB_PATH = Path(__file__).resolve().parent.parent / "tts" / "data" / "voice_catalog.db"

# Universal Offline Fallback: Curated native Hindi & English voices if data files are missing
EMBEDDED_VOICE_DATA = {
    "hi-IN": [
        {"id": "Enceladus", "display_name": "Enceladus", "gender": "male", "pitch": "low", "age": 48, "dialect": "Bhojpuri Hindi / Rustic", "timbre": "heavy, gruff, low gravelly vocal fry, menacing", "archetypes": ["adult", "butcher", "brawler", "brute", "giant", "rustic", "tavernkeeper", "villain"]},
        {"id": "Charon", "display_name": "Charon", "gender": "male", "pitch": "low", "age": 45, "dialect": "Standard Hindi / Urdu", "timbre": "amused, aristocratic, smooth, velvety confident swagger, relaxed baritone", "archetypes": ["adult", "noble", "charismatic_noble", "bard", "warrior", "veteran", "lead"]},
        {"id": "Puck", "display_name": "Puck", "gender": "male", "pitch": "medium", "age": 30, "dialect": "Haryanvi Hindi / Street", "timbre": "abrasive, sharp, snarling, aggressive street thug sneer, tense, hurried", "archetypes": ["adult", "rogue", "thug", "rascal", "mercenary", "youth", "scout"]},
        {"id": "Achird", "display_name": "Achird", "gender": "male", "pitch": "medium", "age": 62, "dialect": "Bundeli Hindi / Elder", "timbre": "anxious, quavering, elderly magistrate, hesitant breathy", "archetypes": ["elder", "magistrate", "official", "alderman", "counselor", "scholar"]},
        {"id": "Fenrir", "display_name": "Fenrir", "gender": "male", "pitch": "medium", "age": 55, "dialect": "Urdu / Standard Hindi", "timbre": "authoritative, passionate, dramatic warrior", "archetypes": ["elder", "king", "mentor", "commander", "warrior"]},
        {"id": "Orus", "display_name": "Orus", "gender": "male", "pitch": "low", "age": 40, "dialect": "Haryanvi Hindi", "timbre": "firm, serious, soldierly, no-nonsense", "archetypes": ["adult", "commander", "soldier", "magistrate", "guard"]},
        {"id": "Sadachbia", "display_name": "Sadachbia", "gender": "male", "pitch": "low", "age": 50, "dialect": "Standard Hindi", "timbre": "professional, measured, calm diplomat", "archetypes": ["elder", "advisor", "diplomat", "monk"]},
        {"id": "Aoede", "display_name": "Aoede", "gender": "female", "pitch": "medium", "age": 32, "dialect": "Standard Hindi / Literary", "timbre": "calm, steady, articulate, measured audiobook delivery", "archetypes": ["adult", "literary_narrator", "storyteller"]},
        {"id": "Kore", "display_name": "Kore", "gender": "female", "pitch": "medium", "age": 40, "dialect": "Awadhi Hindi", "timbre": "firm, authoritative, direct, and regal", "archetypes": ["adult", "queen", "sorceress", "leader"]},
        {"id": "Leda", "display_name": "Leda", "gender": "female", "pitch": "high", "age": 22, "dialect": "Awadhi Hindi", "timbre": "youthful, vibrant, bright, and energetic", "archetypes": ["youth", "maiden", "princess", "apprentice"]},
        {"id": "Zephyr", "display_name": "Zephyr", "gender": "female", "pitch": "high", "age": 28, "dialect": "Bhojpuri Hindi", "timbre": "bright, clear, breezy, and witty", "archetypes": ["adult", "heroine", "scout", "warrior_maiden"]},
        {"id": "hi-in-tutor-1", "display_name": "Senior Scholar 1", "gender": "male", "pitch": "low", "age": 56, "dialect": "Urdu", "timbre": "deep, resonant, and confident", "archetypes": ["elder", "stoic_warrior", "literary_narrator", "mentor"]},
        {"id": "hi-in-advisor-10", "display_name": "Authoritative Advisor 10", "gender": "male", "pitch": "low", "age": 31, "dialect": "Haryanvi Hindi", "timbre": "textured, resonant, and soothing", "archetypes": ["adult", "warrior", "soldier", "brawler"]},
        {"id": "hi-in-advisor-2", "display_name": "Rustic Trader 2", "gender": "male", "pitch": "low", "age": 47, "dialect": "Bhojpuri Hindi", "timbre": "professional yet approachable", "archetypes": ["adult", "rustic", "butcher", "commoner"]},
        {"id": "hi-in-tutor-5", "display_name": "Charismatic Noble 5", "gender": "male", "pitch": "low", "age": 35, "dialect": "Bhojpuri Hindi", "timbre": "resonant and witty", "archetypes": ["adult", "charismatic_noble", "bard", "companion"]},
        {"id": "hi-in-assistant-1", "display_name": "Warm Host 1", "gender": "male", "pitch": "low", "age": 55, "dialect": "Urdu", "timbre": "conversational, dry humor, and warm", "archetypes": ["elder", "innkeeper", "ally"]},
        {"id": "hi-in-concierge-2", "display_name": "Philosopher 2", "gender": "male", "pitch": "low", "age": 33, "dialect": "Bundeli Hindi", "timbre": "reflective, calm, and reassuring", "archetypes": ["adult", "scholar", "philosopher"]},
        {"id": "hi-in-advisor-4", "display_name": "Elder Counselor 4", "gender": "male", "pitch": "medium", "age": 54, "dialect": "Bundeli Hindi", "timbre": "laid-back, encouraging, and chill", "archetypes": ["elder", "advisor", "noble"]},
        {"id": "hi-in-tutor-8", "display_name": "Town Magistrate 8", "gender": "male", "pitch": "low", "age": 53, "dialect": "Haryanvi Hindi", "timbre": "light, airy, and precise", "archetypes": ["elder", "magistrate", "official", "alderman"]},
        {"id": "hi-in-commercial-2", "display_name": "Youth Scout 2", "gender": "male", "pitch": "low", "age": 24, "dialect": "Awadhi Hindi", "timbre": "professional yet approachable", "archetypes": ["youth", "apprentice", "scout"]},
        {"id": "hi-in-tutor-3", "display_name": "Young Companion 3", "gender": "male", "pitch": "low", "age": 24, "dialect": "Awadhi Hindi", "timbre": "comforting someone who is stressed", "archetypes": ["youth", "brother", "companion"]},
        {"id": "hi-in-advisor-1", "display_name": "Regal Commander 1", "gender": "female", "pitch": "low", "age": 32, "dialect": "Awadhi Hindi", "timbre": "comforting, authoritative, and deep", "archetypes": ["adult", "queen", "sorceress", "commander"]},
        {"id": "hi-in-concierge-3", "display_name": "Velvet Matron 3", "gender": "female", "pitch": "medium", "age": 54, "dialect": "Awadhi Hindi", "timbre": "deep, velvety, and unhurried", "archetypes": ["elder", "maternal", "priestess", "aristocrat"]},
        {"id": "hi-in-advisor-12", "display_name": "Elder Healer 12", "gender": "female", "pitch": "medium", "age": 54, "dialect": "Urdu", "timbre": "warm and engaging", "archetypes": ["elder", "grandmother", "healer", "matron"]},
        {"id": "hi-in-tutor-4", "display_name": "Heroine Adviser 4", "gender": "female", "pitch": "medium", "age": 28, "dialect": "Bundeli Hindi", "timbre": "warm and engaging", "archetypes": ["adult", "sorceress", "heroine", "adviser"]},
        {"id": "hi-in-tutor-7", "display_name": "Breezy Princess 7", "gender": "female", "pitch": "high", "age": 29, "dialect": "Urdu", "timbre": "bright, breezy, and youthful", "archetypes": ["youth", "princess", "young_maiden", "scout"]},
        {"id": "hi-in-training-9", "display_name": "Warrior Maiden 9", "gender": "female", "pitch": "high", "age": 36, "dialect": "Bhojpuri Hindi", "timbre": "confident and clear", "archetypes": ["adult", "heroine", "warrior_maiden"]},
        {"id": "hi-in-assistant-5", "display_name": "Clear Ally 5", "gender": "female", "pitch": "high", "age": 33, "dialect": "Awadhi Hindi", "timbre": "confident and clear", "archetypes": ["adult", "friend", "ally"]},
        {"id": "hi-in-tutor-9", "display_name": "Apprentice Maiden 9", "gender": "female", "pitch": "high", "age": 25, "dialect": "Awadhi Hindi", "timbre": "warm and engaging", "archetypes": ["youth", "daughter", "apprentice"]},
    ],
    "en-US": [
        {"id": "Enceladus", "display_name": "Enceladus", "gender": "male", "pitch": "low", "age": 48, "dialect": "American English", "timbre": "heavy, gruff, low gravelly vocal fry, menacing", "archetypes": ["adult", "butcher", "brawler", "brute", "giant", "rustic", "tavernkeeper", "villain"]},
        {"id": "Charon", "display_name": "Charon", "gender": "male", "pitch": "low", "age": 45, "dialect": "American English", "timbre": "amused, aristocratic, smooth, velvety confident swagger, relaxed baritone", "archetypes": ["adult", "noble", "charismatic_noble", "bard", "warrior", "veteran", "lead"]},
        {"id": "Puck", "display_name": "Puck", "gender": "male", "pitch": "medium", "age": 30, "dialect": "American English", "timbre": "abrasive, sharp, snarling, aggressive street thug sneer, tense, hurried", "archetypes": ["adult", "rogue", "thug", "rascal", "mercenary", "youth", "scout"]},
        {"id": "Achird", "display_name": "Achird", "gender": "male", "pitch": "medium", "age": 62, "dialect": "American English", "timbre": "anxious, quavering, elderly magistrate, hesitant breathy", "archetypes": ["elder", "magistrate", "official", "alderman", "counselor", "scholar"]},
        {"id": "Fenrir", "display_name": "Fenrir", "gender": "male", "pitch": "medium", "age": 55, "dialect": "American English", "timbre": "authoritative, passionate, dramatic warrior", "archetypes": ["elder", "king", "mentor", "commander", "warrior"]},
        {"id": "Orus", "display_name": "Orus", "gender": "male", "pitch": "low", "age": 40, "dialect": "American English", "timbre": "firm, serious, soldierly, no-nonsense", "archetypes": ["adult", "commander", "soldier", "magistrate", "guard"]},
        {"id": "Sadachbia", "display_name": "Sadachbia", "gender": "male", "pitch": "low", "age": 50, "dialect": "American English", "timbre": "professional, measured, calm diplomat", "archetypes": ["elder", "advisor", "diplomat", "monk"]},
        {"id": "Aoede", "display_name": "Aoede", "gender": "female", "pitch": "medium", "age": 32, "dialect": "American English", "timbre": "calm, steady, articulate, measured audiobook delivery", "archetypes": ["adult", "literary_narrator", "storyteller"]},
        {"id": "Kore", "display_name": "Kore", "gender": "female", "pitch": "medium", "age": 40, "dialect": "American English", "timbre": "firm, authoritative, direct, and regal", "archetypes": ["adult", "queen", "sorceress", "leader"]},
        {"id": "Leda", "display_name": "Leda", "gender": "female", "pitch": "high", "age": 22, "dialect": "American English", "timbre": "youthful, vibrant, bright, and energetic", "archetypes": ["youth", "maiden", "princess", "apprentice"]},
        {"id": "Zephyr", "display_name": "Zephyr", "gender": "female", "pitch": "high", "age": 28, "dialect": "American English", "timbre": "bright, clear, breezy, and witty", "archetypes": ["adult", "heroine", "scout", "warrior_maiden"]},
    ]
}


class VoiceProfileRegistry:
    """
    Central, high-performance voice registry managing all available TTS voice assets.
    """

    _instance: Optional[VoiceProfileRegistry] = None

    def __init__(self, catalog_path: Optional[Path] = None):
        self._profiles_by_id: Dict[str, CanonicalVoiceProfile] = {}
        self._profiles_by_lang: Dict[str, List[CanonicalVoiceProfile]] = {}
        self._catalog_path = Path(catalog_path) if catalog_path else CURATED_CATALOG_JSON
        self._load_registry()

    @classmethod
    def get_instance(cls, catalog_path: Optional[Path] = None) -> VoiceProfileRegistry:
        """Returns the process-wide cached singleton instance."""
        if cls._instance is None or catalog_path is not None:
            cls._instance = cls(catalog_path=catalog_path)
        return cls._instance

    def _load_registry(self) -> None:
        """Loads and indexes all voices into typed CanonicalVoiceProfile objects."""
        loaded = False

        if self._catalog_path.exists():
            try:
                with open(self._catalog_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                langs = data.get("languages", {})
                for l_code, v_list in langs.items():
                    for v in v_list:
                        profile = self._build_profile_from_dict(v, default_lang=l_code)
                        self._profiles_by_id[profile.voice_id] = profile
                        self._profiles_by_lang.setdefault(l_code, []).append(profile)
                loaded = True
                logger.debug(f"[VoiceProfileRegistry] Loaded {len(self._profiles_by_id)} profiles from {self._catalog_path.name}.")
            except Exception as e:
                logger.warning(f"[VoiceProfileRegistry] Error loading JSON catalog from {self._catalog_path}: {e}")

        if not loaded:
            logger.info("[VoiceProfileRegistry] Initializing with embedded fallback voice catalog.")
            for l_code, v_list in EMBEDDED_VOICE_DATA.items():
                for v in v_list:
                    profile = self._build_profile_from_dict(v, default_lang=l_code)
                    self._profiles_by_id[profile.voice_id] = profile
                    self._profiles_by_lang.setdefault(l_code, []).append(profile)

    def _build_profile_from_dict(self, v: Dict[str, Any], default_lang: str = "hi-IN") -> CanonicalVoiceProfile:
        """Constructs a CanonicalVoiceProfile from raw catalog dictionary."""
        vid = v.get("id") or v.get("voice_id", "unknown")
        d_name = v.get("display_name", vid)
        l_code = v.get("language_code", default_lang)
        reg_code = v.get("region_code", "IN" if "hi" in l_code else "US")
        gender_raw = str(v.get("gender") or v.get("sex", "neutral")).lower()
        gender: CastingGender = "female" if "female" in gender_raw else ("male" if "male" in gender_raw else "neutral")

        pitch_raw = str(v.get("pitch") or v.get("pitch_category", "medium")).lower()
        pitch_tier: PitchBand = "medium"
        if "low" in pitch_raw:
            pitch_tier = "low" if "medium" not in pitch_raw else "medium_low"
        elif "high" in pitch_raw:
            pitch_tier = "high" if "medium" not in pitch_raw else "medium_high"

        archs = v.get("archetypes", [])
        if isinstance(archs, str):
            archs = [a.strip() for a in archs.split(",") if a.strip()]

        caps = ProviderCapabilities(
            provider_name="gemini_tts",
            supports_reference_audio=False,
            supports_style_prompt=True,
            supports_native_speed=False,
            native_sample_rate_hz=24000,
            supported_controls=["speechMetadata.style", "temperature", "parametric_eq"],
        )

        return CanonicalVoiceProfile(
            voice_id=vid,
            display_name=d_name,
            language_code=l_code,
            region_code=reg_code,
            gender=gender,
            perceived_age=v.get("age"),
            dialect=v.get("dialect", "Standard"),
            pitch_tier=pitch_tier,
            timbre=v.get("timbre") or v.get("invariant_timbre", ""),
            role=v.get("role", ""),
            persona=v.get("persona", ""),
            archetypes=archs,
            description=v.get("description", ""),
            default_provider="gemini_tts",
            capabilities=caps,
        )

    def get_profile(self, voice_id: str) -> Optional[CanonicalVoiceProfile]:
        """Retrieves exact voice profile by voice_id."""
        return self._profiles_by_id.get(voice_id)

    @property
    def total_voices(self) -> int:
        return len(self._profiles_by_id)

    def query_profiles(
        self,
        language_code: str = "hi-IN",
        gender: Optional[str] = None,
        dialect: Optional[str] = None,
        pitch_tier: Optional[str] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        archetype: Optional[str] = None,
        exclude_voice_ids: Optional[Set[str]] = None,
        limit: int = 50,
    ) -> List[CanonicalVoiceProfile]:
        """
        Sub-millisecond query across profiles with filtering by dialect, gender, age, and archetype.
        """
        candidates = self._profiles_by_lang.get(language_code, [])
        if not candidates and language_code != "en-US":
            candidates = self._profiles_by_lang.get("hi-IN" if "hi" in language_code else "en-US", [])

        exclude_set = exclude_voice_ids or set()
        results: List[CanonicalVoiceProfile] = []

        g_filter = gender.lower() if gender else None
        d_filter = dialect.lower() if dialect else None
        p_filter = pitch_tier.lower() if pitch_tier else None
        arch_clean = archetype.lower().replace("-", " ").replace("_", " ") if archetype else None

        for p in candidates:
            if p.voice_id in exclude_set:
                continue
            if g_filter and p.gender != g_filter and g_filter in ("male", "female"):
                continue
            if p_filter and p.pitch_tier != p_filter:
                continue
            if d_filter and d_filter not in p.dialect.lower():
                continue
            if min_age is not None and p.perceived_age is not None and p.perceived_age < min_age:
                continue
            if max_age is not None and p.perceived_age is not None and p.perceived_age > max_age:
                continue

            if arch_clean:
                p_text = f"{' '.join(p.archetypes)} {p.timbre} {p.description}".lower()
                if arch_clean not in p_text:
                    continue

            results.append(p)
            if len(results) >= limit:
                break

        return results

    def get_formatted_catalog_for_prompt(
        self,
        language_code: str = "hi-IN",
        gender: Optional[str] = None,
        exclude_voice_ids: Optional[Set[str]] = None,
        limit: int = 30,
    ) -> str:
        """
        Formats a structured markdown table for LLM Casting Director prompts.
        Provides the AI Casting Director with concrete voice candidates, their timbres,
        dialects, age, and archetypes.
        """
        profiles = self.query_profiles(
            language_code=language_code,
            gender=gender,
            exclude_voice_ids=exclude_voice_ids,
            limit=limit,
        )
        if not profiles:
            return "No matching voices available in catalog."

        lines = [
            "| Voice ID | Gender | Age | Dialect | Pitch | Timbre & Vocal Archetype |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for p in profiles:
            age_s = str(p.perceived_age) if p.perceived_age else "Adult"
            desc_s = f"{p.timbre}. ({', '.join(p.archetypes[:3])})" if p.archetypes else p.timbre
            lines.append(f"| `{p.voice_id}` | {p.gender} | {age_s} | {p.dialect} | {p.pitch_tier} | {desc_s} |")

        return "\n".join(lines)
