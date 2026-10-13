#!/usr/bin/env python3
"""
Audiobook Factory - Casting Contracts & Data Models (Pydantic v2).
Defines schemas for Character Casting Profiles, Voice Candidate Scoring,
Voice Audition Scenes, Multi-Dimensional Casting Evaluation, and Cast Locks.
"""

from __future__ import annotations
import re
import json
import datetime
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal, Set
from pydantic import BaseModel, Field, ConfigDict, model_validator, AliasChoices


CastingGender = Literal["male", "female", "neutral"]
PerceivedAgeCategory = Literal[
    "child",
    "youth",
    "young_adult",
    "prime_adult",
    "mature_adult",
    "elder",
]
VocalWeight = Literal["light", "medium", "heavy"]
TimbreType = Literal["gravelly", "smooth", "raspy", "warm", "sharp", "resonant", "brittle", "textured"]
PitchBand = Literal["low", "medium_low", "medium", "medium_high", "high"]
BrightnessLevel = Literal["dark", "neutral", "bright"]
ProjectionLevel = Literal["intimate", "conversational", "projected", "bellowing"]

AuditionDramaticMode = Literal[
    "neutral",
    "conversational",
    "authority",
    "anger",
    "vulnerability",
    "fear",
    "whisper",
    "humor",
    "action",
    "transition",
]


class CharacterCastingProfile(BaseModel):
    """
    Unified Casting Profile derived from canonical character identity,
    linguistic profile, and dramaturgy performance profile.
    """
    model_config = ConfigDict(extra="ignore")

    character_id: str = Field(..., description="Unique character identifier (e.g. 'char_hero')")
    canonical_name: str = Field(..., description="Canonical character display name")
    gender: CastingGender = Field(default="neutral", description="Biological / dramatic vocal gender")
    perceived_age: PerceivedAgeCategory = Field(default="prime_adult", description="Perceived acoustic age band")
    sociolect_archetype: str = Field(default="NEUTRAL", description="Sociolect archetype from book bible")

    # 1. Personality Traits (0.0 to 1.0)
    warmth: float = Field(default=0.5, ge=0.0, le=1.0)
    aggression: float = Field(default=0.5, ge=0.0, le=1.0)
    restraint: float = Field(default=0.5, ge=0.0, le=1.0)
    authority: float = Field(default=0.5, ge=0.0, le=1.0)
    vulnerability: float = Field(default=0.3, ge=0.0, le=1.0)
    humor: float = Field(default=0.2, ge=0.0, le=1.0)
    seriousness: float = Field(default=0.8, ge=0.0, le=1.0)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)

    # 2. Speech Dynamics
    pace: float = Field(default=1.0, ge=0.5, le=2.0)
    articulation: str = Field(default="natural", description="Speech clarity: crisp, natural, colloquial, sluggish, sharp")
    formality: int = Field(default=2, ge=0, le=5)
    verbosity: str = Field(default="balanced", description="terse, balanced, elaborate, theatrical")
    rhythm: str = Field(default="steady", description="staccato, steady, fluid, syncopated, halting")
    sentence_style: str = Field(default="balanced")

    # 3. Dramatic Range Demands (0.0 to 1.0)
    range_anger: float = Field(default=0.5, ge=0.0, le=1.0)
    range_fear: float = Field(default=0.3, ge=0.0, le=1.0)
    range_grief: float = Field(default=0.3, ge=0.0, le=1.0)
    range_joy: float = Field(default=0.3, ge=0.0, le=1.0)
    range_intimacy: float = Field(default=0.3, ge=0.0, le=1.0)
    range_tension: float = Field(default=0.6, ge=0.0, le=1.0)
    range_action: float = Field(default=0.5, ge=0.0, le=1.0)

    # 4. Vocal Weight & Acoustic Preferences
    vocal_weight: VocalWeight = Field(default="medium")
    timbre_preference: TimbreType = Field(default="resonant")
    pitch_preference: PitchBand = Field(default="medium")
    brightness: BrightnessLevel = Field(default="neutral")
    projection: ProjectionLevel = Field(default="conversational")

    # 5. Delivery Styles
    required_styles: List[str] = Field(default_factory=list)
    forbidden_styles: List[str] = Field(default_factory=list)

    @classmethod
    def from_entities(
        cls,
        character_id: str,
        canonical_name: str,
        entity: Optional[Any] = None,
        language_profile: Optional[Any] = None,
        performance_profile: Optional[Any] = None,
    ) -> CharacterCastingProfile:
        """
        Synthesizes a unified CharacterCastingProfile by inspecting existing
        BookEntity, CharacterLanguageProfile, and CharacterPerformanceProfile.
        Zero duplication of domain knowledge.
        """
        gender: CastingGender = "neutral"
        if entity:
            ent_gender = getattr(entity, "gender", None) or (entity.get("gender") if isinstance(entity, dict) else None)
            if ent_gender:
                g_str = str(ent_gender).lower()
                if "female" in g_str:
                    gender = "female"
                elif "male" in g_str:
                    gender = "male"

        archetype = "NEUTRAL"
        if entity:
            archetype = getattr(entity, "sociolect_archetype", None) or (entity.get("sociolect_archetype") if isinstance(entity, dict) else "NEUTRAL") or "NEUTRAL"

        base_pace = 1.0
        base_energy = 0.75
        articulation = "natural"
        restraint = 0.50
        req_styles: List[str] = []
        forbid_styles: List[str] = []

        if performance_profile:
            base_pace = getattr(performance_profile, "baseline_pace", 1.0)
            base_energy = getattr(performance_profile, "baseline_energy", 0.75)
            articulation = getattr(performance_profile, "articulation", "natural")
            restraint = getattr(performance_profile, "restraint_level", 0.50)
            emo_beh = getattr(performance_profile, "emotional_behaviors", {})
            if isinstance(emo_beh, dict):
                req_styles.extend(list(emo_beh.values()))

        formality = 2
        verbosity = "balanced"
        if language_profile:
            formality = getattr(language_profile, "formality_level", 2)
            verbosity = getattr(language_profile, "sentence_length_preference", "balanced")
            forbid = getattr(language_profile, "prohibited_registers", [])
            if isinstance(forbid, list):
                forbid_styles.extend([str(x) for x in forbid])

        # Infer acoustic weight & authority from archetype and restraint
        authority = 0.7 if "COMMANDER" in archetype or "ARISTOCRAT" in archetype or "MATRIARCH" in archetype else 0.5
        vocal_weight: VocalWeight = "heavy" if (base_energy > 0.85 or authority > 0.65) else ("light" if base_energy < 0.60 else "medium")
        timbre_pref: TimbreType = "gravelly" if "CYNIC" in archetype or "SURVIVOR" in archetype else ("sharp" if "ARISTOCRAT" in archetype else "resonant")
        pitch_pref: PitchBand = "low" if (gender == "male" and authority >= 0.6) else ("medium_low" if gender == "female" and authority >= 0.6 else "medium")

        return cls(
            character_id=character_id,
            canonical_name=canonical_name,
            gender=gender,
            sociolect_archetype=archetype,
            authority=authority,
            restraint=restraint,
            pace=base_pace,
            articulation=articulation,
            formality=formality,
            verbosity=verbosity,
            vocal_weight=vocal_weight,
            timbre_preference=timbre_pref,
            pitch_preference=pitch_pref,
            required_styles=req_styles,
            forbidden_styles=forbid_styles,
        )


class VoiceCandidateScore(BaseModel):
    """
    Explainable candidate evaluation output from VoiceCandidateEngine.
    """
    model_config = ConfigDict(extra="ignore")

    voice_id: str
    display_name: str
    overall_score: float = Field(..., ge=0.0, le=1.0)
    strengths: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    recommendation_summary: str = ""


class AuditionScene(BaseModel):
    """
    Single standardized dramatic audition scene.
    """
    model_config = ConfigDict(extra="ignore")

    scene_id: str
    dramatic_mode: AuditionDramaticMode
    line_text: str
    delivery_directive: str
    target_emotion: str
    suggested_pace: float = 1.0


class AuditionResult(BaseModel):
    """
    Audio generation result for a single audition scene.
    """
    model_config = ConfigDict(extra="ignore")

    candidate_voice_id: str
    scene_id: str
    dramatic_mode: AuditionDramaticMode
    audio_path: str
    duration_sec: float = 0.0
    passed: bool = True
    overall_score: float = 0.0
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    diagnostics: List[str] = Field(default_factory=list)


class CastingEvaluationRecord(BaseModel):
    """
    Comprehensive audition and metadata evaluation of a candidate voice.
    Preserves audit evidence for winning and losing candidates alike.
    """
    model_config = ConfigDict(extra="ignore")

    candidate_voice_id: str
    character_id: str
    overall_fit_score: float = Field(..., ge=0.0, le=1.0)
    rank: int = 1
    passed_audition: bool = True
    dimension_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="character_fit, timbre_fit, emotional_range, naturalness, authority, vulnerability, whisper_quality, high_intensity_quality, long_form_suitability, ensemble_distinctiveness"
    )
    strengths: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    audition_results: List[AuditionResult] = Field(default_factory=list)
    evaluation_summary: str = ""


HONORIFIC_BLACKLIST: Set[str] = {
    "lord", "sir", "master", "lady", "king", "queen", "baron", "duke",
    "captain", "witcher", "the", "alderman", "doctor", "dr", "father",
    "brother", "sister", "dame", "count", "duchess", "prince", "princess",
    "elder", "general", "chief", "officer", "inspector", "innkeeper",
    "commander", "emperor", "empress", "mr", "mrs", "miss",
    "chancellor", "leader", "mistress",
    # Hindi honorifics & titles
    "महाराज", "राजा", "रानी", "श्रीमान", "स्वामी", "प्रभु", "ठाकुर",
    "मालिक", "कप्तान", "विचर", "मुखिया", "चौधरी", "सर", "लॉर्ड", "मास्टर",
    # Common variations / transliterations
    "लोर्ड", "किन्ग", "सिर", "मास्टेर",
    "चान्सेल्लोर", "लीडेर", "मिस्ट्रेस्स",
    # Generic occupations, titles, numbers, and descriptors
    "man", "मान", "fat", "फ़ाट", "फाट", "yellow", "येल्लोव", "येलो",
    "jerkin", "जेर्किन", "cobbler", "कोब्ब्लेर", "कॉबलर", "sorcerer", "सोर्सेरेर", "सोर्सरर",
    "sorceress", "सोर्सेरेस्स", "सोर्सरेस", "halberdier", "हाल्बेर्डिेर", "हलबर्डियर",
    "warrior", "वार्रिोर", "वॉरियर", "वारियर", "reaver", "रीवेर", "रीवर",
    "denesle", "डेनेस्ले", "golden", "गोल्डेन", "गोल्डन", "dragon", "ड्रागोन", "ड्रैगन",
    "little", "लिट्ट्ले", "लिटिल", "duke", "डुके", "ड्यूक", "baron", "बारोन", "बैरन",
    "queen", "क्वीन", "miss", "मिस्स", "मिस", "mrs", "म्र्स", "मिसेज",
}


class CastLock(BaseModel):
    """
    Persistent, formal Cast Lock contract.
    Guarantees stable character-to-voice attribution across the entire novel.
    Recasting requires explicit invalidation and causes downstream regeneration.
    """
    model_config = ConfigDict(extra="ignore")

    character_id: str = ""
    character_name: str = ""
    display_name_hi: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    voice_id: str
    casting_version: str = "1.0.0"
    locked: bool = True
    locked_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    locked_by: str = "Director"
    selection_rank: int = 1
    selection_rationale: str = ""
    casting_evidence: Dict[str, Any] = Field(default_factory=dict)
    calibration_overrides: Dict[str, Any] = Field(default_factory=dict)
    eq_formant_profile: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def _fill_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cid = data.get("character_id") or data.get("character_name") or ""
            cname = data.get("character_name") or data.get("character_id") or ""
            data["character_id"] = cid
            data["character_name"] = cname
            if "aliases" not in data or data["aliases"] is None:
                data["aliases"] = []
        return data

    @property
    def pitch(self) -> float:
        """Phase-safe pitch modifier from calibration overrides, defaulting to 1.0."""
        if self.calibration_overrides and "pitch" in self.calibration_overrides:
            try:
                return float(self.calibration_overrides["pitch"])
            except (ValueError, TypeError):
                pass
        return 1.0

    @property
    def speed(self) -> float:
        """Pacing / tempo modifier from calibration overrides, defaulting to 1.0."""
        if self.calibration_overrides and "speed" in self.calibration_overrides:
            try:
                return float(self.calibration_overrides["speed"])
            except (ValueError, TypeError):
                pass
        return 1.0

    def matches(self, name_or_alias: str) -> bool:
        """
        Case-insensitive, whitespace-insensitive, Devanagari nukta-normalized matching
        across character_id, character_name, display_name_hi, and aliases.
        Supports whole-word token matching for non-honorific queries of length >= 3.
        """
        if not name_or_alias:
            return False

        def _normalize(s: str) -> str:
            if not s:
                return ""
            d = unicodedata.normalize("NFD", str(s))
            d = d.replace("\u093c", "")
            d = unicodedata.normalize("NFC", d)
            d = d.strip().lower().replace("_", " ")
            return re.sub(r"\s+", " ", d)

        target = _normalize(name_or_alias)
        if not target:
            return False

        candidates = [self.character_id, self.character_name]
        if self.display_name_hi:
            candidates.append(self.display_name_hi)
        if self.aliases:
            candidates.extend(self.aliases)

        for cand in candidates:
            if not cand:
                continue
            norm_cand = _normalize(cand)
            if norm_cand == target:
                return True
            # Whole-word token matching for non-honorific targets of length >= 3
            if len(target) >= 3 and target not in HONORIFIC_BLACKLIST:
                cand_tokens = norm_cand.split()
                if target in cand_tokens:
                    return True
        return False


class CastLockManifest(BaseModel):
    """
    Project-level manifest storing all locked character voices (cast_lock.json).
    """
    model_config = ConfigDict(extra="ignore")

    project_slug: str = Field(default="", validation_alias=AliasChoices("project_slug", "project_id"))
    version: str = "1.0.0"
    locks: Dict[str, CastLock] = Field(default_factory=dict)
    recast_history: List[Dict[str, Any]] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())

    @model_validator(mode="before")
    @classmethod
    def _fill_lock_keys(cls, data: Any) -> Any:
        if isinstance(data, dict) and "locks" in data and isinstance(data["locks"], dict):
            for key, lock_val in data["locks"].items():
                if isinstance(lock_val, dict):
                    if not lock_val.get("character_id"):
                        lock_val["character_id"] = key
                    if not lock_val.get("character_name"):
                        lock_val["character_name"] = key
        return data

    def get_lock(self, identifier: str) -> Optional[CastLock]:
        """Resolves cast lock leveraging matches() for bilingual and alias lookup."""
        if not identifier:
            return None
        t_clean = str(identifier).strip()
        t_low = t_clean.lower()
        if t_low in HONORIFIC_BLACKLIST or t_clean in HONORIFIC_BLACKLIST:
            return None
        t_norm = unicodedata.normalize("NFD", t_clean).replace("\u093c", "")
        t_norm = unicodedata.normalize("NFC", t_norm).strip().lower()
        if t_norm in HONORIFIC_BLACKLIST:
            return None
        # 1. Direct dictionary key match
        if identifier in self.locks:
            return self.locks[identifier]
        # 2. Match across all locks using lock.matches()
        for lock in self.locks.values():
            if lock.matches(identifier):
                return lock
        return None


class ProviderCapabilities(BaseModel):
    """Supported TTS delivery controls and audio constraints per provider."""
    model_config = ConfigDict(extra="ignore")

    provider_name: Literal["gemini_tts", "qwen3_tts", "local_winrt"] = "gemini_tts"
    supports_reference_audio: bool = False
    supports_style_prompt: bool = True
    supports_native_speed: bool = False
    native_sample_rate_hz: int = 24000
    supported_controls: List[str] = Field(
        default_factory=lambda: ["speechMetadata.style", "temperature", "parametric_eq"]
    )


class CanonicalVoiceProfile(BaseModel):
    """
    Immutable voice asset entry in the unified voice catalog.
    Represents a single available voice across 2,089 catalog entries.
    """
    model_config = ConfigDict(extra="ignore")

    voice_id: str = Field(..., description="Unique voice identifier e.g. 'hi-in-advisor-10' or 'Aoede'")
    display_name: str
    language_code: str = "hi-IN"
    region_code: str = "IN"
    gender: CastingGender = "neutral"
    perceived_age: Optional[int] = None
    dialect: str = "Standard"
    pitch_tier: PitchBand = "medium"
    timbre: str = ""
    role: str = ""
    persona: str = ""
    archetypes: List[str] = Field(default_factory=list)
    description: str = ""
    default_provider: Literal["gemini_tts", "qwen3_tts"] = "gemini_tts"
    reference_audio_path: Optional[str] = None
    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)


class SpectralFormantProfile(BaseModel):
    """
    Phase-Safe 4D Parametric EQ Formant Profile.
    Applies surgical analog-style EQ offsets (+/- 2-3 dB) to separate co-speakers
    without destructive digital pitch-shifting (asetrate) or WSOLA time-stretching.
    """
    model_config = ConfigDict(extra="ignore")

    chest_resonance_150hz_db: float = Field(default=0.0, ge=-4.0, le=4.0)
    nasal_presence_2800hz_db: float = Field(default=0.0, ge=-3.0, le=4.0)
    throat_clarity_3200hz_db: float = Field(default=0.0, ge=-3.0, le=3.0)
    air_shelf_8000hz_db: float = Field(default=0.0, ge=-4.0, le=4.0)
    target_tempo_multiplier: float = Field(default=1.0, ge=0.85, le=1.15)

    def to_ffmpeg_filters(self) -> List[str]:
        """Generates phase-safe FFmpeg audio filter clauses."""
        filters = []
        if abs(self.chest_resonance_150hz_db) >= 0.2:
            filters.append(f"equalizer=f=150:t=q:w=1.2:g={self.chest_resonance_150hz_db:+.1f}")
        if abs(self.nasal_presence_2800hz_db) >= 0.2:
            filters.append(f"equalizer=f=2800:t=q:w=1.4:g={self.nasal_presence_2800hz_db:+.1f}")
        if abs(self.throat_clarity_3200hz_db) >= 0.2:
            filters.append(f"equalizer=f=3200:t=q:w=1.4:g={self.throat_clarity_3200hz_db:+.1f}")
        if abs(self.air_shelf_8000hz_db) >= 0.2:
            filters.append(f"equalizer=f=8000:t=q:w=1.0:g={self.air_shelf_8000hz_db:+.1f}")
        return filters


class SceneContrastMatrix(BaseModel):
    """
    Scene-level acoustic contrast evaluation between active speaking characters.
    Enforces minimum separation distance (>= 0.65) to guarantee distinct listener perception.
    """
    model_config = ConfigDict(extra="ignore")

    scene_id: str
    active_speakers: List[str] = Field(default_factory=list)
    pairwise_distances: Dict[str, float] = Field(default_factory=dict)
    min_distance: float = 1.0
    is_contrast_sufficient: bool = True
    calibration_adjustments: Dict[str, SpectralFormantProfile] = Field(default_factory=dict)


class CharacterCastAssignment(BaseModel):
    """
    Authoritative character-to-voice assignment binding.
    """
    model_config = ConfigDict(extra="ignore")

    character_id: str
    canonical_name: str
    voice_id: str
    assigned_provider: Literal["gemini_tts", "qwen3_tts"] = "gemini_tts"
    gender: CastingGender = "neutral"
    dialect: str = "Standard"
    casting_rationale: str = ""
    baseline_formants: SpectralFormantProfile = Field(default_factory=SpectralFormantProfile)
    pronunciation_overrides: Dict[str, str] = Field(default_factory=dict)
    locked: bool = True
    version: str = "1.0.0"

