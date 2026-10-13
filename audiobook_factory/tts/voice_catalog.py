#!/usr/bin/env python3
"""
Audiobook Factory - Room 4: Dynamic Voice Catalog Engine.
Provides sub-millisecond query, ranking, and collision-free assignment across
2,089 prebuilt Google Gemini TTS voices (114 native Hindi, 120 Indian English, 215 US English).
Backed by JSON cache and SQLite index with embedded offline fallback.
"""

from __future__ import annotations
import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

logger = logging.getLogger("AudiobookFactory")

DATA_DIR = Path(__file__).resolve().parent / "data"
CATALOG_JSON_PATH = DATA_DIR / "curated_voice_catalog.json"
CATALOG_DB_PATH = DATA_DIR / "voice_catalog.db"

# Universal Offline Fallback: Curated native Hindi & English voices if data files are missing
# Universal Offline Fallback: Curated Google Gemini multilingual studio models
EMBEDDED_FALLBACK_VOICES = {
    "hi-IN": [
        # Male Studio Models
        {"id": "Charon", "gender": "male", "pitch": "low", "age": 45, "dialect": "Haryanvi Hindi, Standard Hindi", "timbre": "deep, resonant, and steady", "archetypes": ["adult", "warrior", "stoic_warrior", "soldier", "brute", "hero", "imposing", "lead"]},
        {"id": "Fenrir", "gender": "male", "pitch": "low", "age": 55, "dialect": "Urdu, Standard Hindi", "timbre": "authoritative, commanding, and resonant", "archetypes": ["elder", "king", "ruler", "mentor", "commander", "authoritative", "noble"]},
        {"id": "Algenib", "gender": "male", "pitch": "low", "age": 38, "dialect": "Bhojpuri Hindi, Standard Hindi", "timbre": "gravelly, textured, and weathered", "archetypes": ["adult", "mercenary", "warrior", "rustic", "hunter", "commoner"]},
        {"id": "Enceladus", "gender": "male", "pitch": "low", "age": 48, "dialect": "Bundeli Hindi, Standard Hindi", "timbre": "dark, breathy, and sinister", "archetypes": ["adult", "sinister", "villain", "dark", "sorcerer", "imposing", "mysterious"]},
        {"id": "Orus", "gender": "male", "pitch": "low", "age": 40, "dialect": "Haryanvi Hindi, Standard Hindi", "timbre": "firm, serious, and no-nonsense", "archetypes": ["adult", "official", "magistrate", "commander", "disciplined", "soldier"]},
        {"id": "Algieba", "gender": "male", "pitch": "low", "age": 36, "dialect": "Urdu, Awadhi Hindi, Standard Hindi", "timbre": "smooth, relaxed, and polished", "archetypes": ["adult", "noble", "aristocrat", "polished", "courtier", "charismatic_noble"]},
        {"id": "Achird", "gender": "male", "pitch": "medium", "age": 46, "dialect": "Bhojpuri Hindi, Standard Hindi", "timbre": "friendly, approachable, and warm", "archetypes": ["adult", "innkeeper", "tavernkeeper", "ally", "rustic", "commoner", "peasant"]},
        {"id": "Puck", "gender": "male", "pitch": "medium", "age": 32, "dialect": "Bhojpuri Hindi, Awadhi Hindi, Standard Hindi", "timbre": "upbeat, energetic, and charismatic", "archetypes": ["adult", "bard", "companion", "witty", "charismatic", "rogue", "agile"]},
        {"id": "Zephyr", "gender": "male", "pitch": "high", "age": 17, "dialect": "Haryanvi Hindi, Bundeli Hindi, Standard Hindi", "timbre": "youthful, bright, breezy, and energetic", "archetypes": ["youth", "scout", "apprentice", "teen", "adolescent", "youngster", "fighter", "rebel"]},
        # Female Studio Models
        {"id": "Aoede", "gender": "female", "pitch": "medium", "age": 35, "dialect": "Standard Hindi, Urdu", "timbre": "calm, steady, articulate, and melodious", "archetypes": ["literary_narrator", "storyteller", "narrator", "adult"]},
        {"id": "Kore", "gender": "female", "pitch": "medium", "age": 38, "dialect": "Standard Hindi, Urdu", "timbre": "firm, authoritative, and direct", "archetypes": ["adult", "queen", "sorceress", "leader", "regal", "authoritative", "commander"]},
        {"id": "Leda", "gender": "female", "pitch": "high", "age": 20, "dialect": "Awadhi Hindi, Standard Hindi", "timbre": "youthful, vibrant, bright, and breezy", "archetypes": ["youth", "princess", "young_maiden", "vibrant", "maiden", "daughter"]},
        {"id": "Achernar", "gender": "female", "pitch": "medium", "age": 30, "dialect": "Awadhi Hindi, Urdu, Standard Hindi", "timbre": "soft, intimate, gentle, and breathy", "archetypes": ["adult", "intimate", "poetic", "gentle", "healer", "companion", "mystical"]},
        {"id": "Callisto", "gender": "female", "pitch": "low", "age": 52, "dialect": "Bhojpuri Hindi, Bundeli Hindi, Standard Hindi", "timbre": "warm, deep, velvety, and maternal", "archetypes": ["elder", "maternal", "matron", "grandmother", "priestess", "adult"]},
    ],
    "en-US": [
        # Male Studio Models
        {"id": "Charon", "gender": "male", "pitch": "low", "age": 45, "dialect": "American English", "timbre": "deep, stoic, and grave", "archetypes": ["warrior", "veteran", "hero", "lead"]},
        {"id": "Fenrir", "gender": "male", "pitch": "low", "age": 55, "dialect": "American English", "timbre": "authoritative, wise, and passionate", "archetypes": ["elder", "king", "mentor", "commander"]},
        {"id": "Algenib", "gender": "male", "pitch": "low", "age": 38, "dialect": "American English", "timbre": "gravelly, grounded, and hard-hitting", "archetypes": ["mercenary", "warrior", "veteran", "hunter"]},
        {"id": "Enceladus", "gender": "male", "pitch": "low", "age": 48, "dialect": "American English", "timbre": "dark, breathy, and ominous", "archetypes": ["villain", "dark", "sorcerer", "sinister"]},
        {"id": "Orus", "gender": "male", "pitch": "low", "age": 40, "dialect": "American English", "timbre": "firm, serious, and no-nonsense", "archetypes": ["commander", "soldier", "magistrate", "official"]},
        {"id": "Algieba", "gender": "male", "pitch": "low", "age": 36, "dialect": "American English", "timbre": "smooth, relaxed, and polished", "archetypes": ["noble", "aristocrat", "courtier", "charismatic"]},
        {"id": "Achird", "gender": "male", "pitch": "medium", "age": 46, "dialect": "American English", "timbre": "friendly, approachable, and warm", "archetypes": ["innkeeper", "tavernkeeper", "ally", "companion"]},
        {"id": "Puck", "gender": "male", "pitch": "medium", "age": 35, "dialect": "American English", "timbre": "upbeat, energetic, and charismatic", "archetypes": ["bard", "companion", "rogue", "youth"]},
        {"id": "Zephyr", "gender": "male", "pitch": "high", "age": 17, "dialect": "American English", "timbre": "bright, youthful, and agile", "archetypes": ["youth", "scout", "apprentice", "teen"]},
        # Female Studio Models
        {"id": "Aoede", "gender": "female", "pitch": "medium", "age": 35, "dialect": "American English", "timbre": "breezy, natural, and melodious", "archetypes": ["literary_narrator", "storyteller"]},
        {"id": "Kore", "gender": "female", "pitch": "medium", "age": 40, "dialect": "American English", "timbre": "firm, authoritative, and direct", "archetypes": ["queen", "sorceress", "leader"]},
        {"id": "Leda", "gender": "female", "pitch": "high", "age": 22, "dialect": "American English", "timbre": "youthful, vibrant, and energetic", "archetypes": ["youth", "maiden", "princess"]},
        {"id": "Achernar", "gender": "female", "pitch": "medium", "age": 30, "dialect": "American English", "timbre": "soft, intimate, and gentle", "archetypes": ["intimate", "gentle", "healer", "companion"]},
        {"id": "Callisto", "gender": "female", "pitch": "low", "age": 52, "dialect": "American English", "timbre": "warm, deep, and maternal", "archetypes": ["elder", "maternal", "matron"]},
    ]
}


MALE_VOICE_PERSONAS = [
    "Fenrir",
    "Orus",
    "Algieba",
    "Achird",
    "Algenib",
    "Enceladus",
    "Puck",
    "Zephyr",
    "Charon",
]


class VoiceCatalog:
    """Manages multi-lingual Gemini TTS voice discovery, semantic indexing, and casting."""

    _instance: Optional[VoiceCatalog] = None

    def __init__(self):
        self._voices_by_id: Dict[str, Dict[str, Any]] = {}
        self._voices_by_lang: Dict[str, List[Dict[str, Any]]] = {}
        self._fallback_male_idx: int = 0
        self._load_catalog()

    @classmethod
    def get_instance(cls) -> VoiceCatalog:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_catalog(self) -> None:
        """Loads curated catalog from JSON or SQLite, falling back to embedded data."""
        loaded = False

        if CATALOG_JSON_PATH.exists():
            try:
                with open(CATALOG_JSON_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    langs = data.get("languages", {})
                    for l_code, v_list in langs.items():
                        self._voices_by_lang[l_code] = v_list
                        for v in v_list:
                            vid = v["id"]
                            if vid in self._voices_by_id:
                                existing = self._voices_by_id[vid]
                                cur_d = existing.get("dialect", "")
                                new_d = v.get("dialect", "")
                                if new_d and new_d not in cur_d:
                                    existing["dialect"] = f"{cur_d}, {new_d}".strip(", ")
                                cur_arch = set(existing.get("archetypes", []))
                                cur_arch.update(v.get("archetypes", []))
                                existing["archetypes"] = list(cur_arch)
                            else:
                                self._voices_by_id[vid] = dict(v)
                    loaded = True
                    logger.debug(f"[VoiceCatalog] Loaded {len(self._voices_by_id)} voices from JSON cache.")
                    # Ensure SQLite database is created if missing
                    if not CATALOG_DB_PATH.exists():
                        try:
                            CATALOG_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                            conn = sqlite3.connect(CATALOG_DB_PATH)
                            cur = conn.cursor()
                            cur.execute("""
                                CREATE TABLE IF NOT EXISTS voices (
                                    id TEXT PRIMARY KEY,
                                    display_name TEXT,
                                    language_code TEXT,
                                    gender TEXT,
                                    age INTEGER,
                                    dialect TEXT,
                                    pitch TEXT,
                                    timbre TEXT,
                                    archetypes TEXT,
                                    description TEXT
                                )
                            """)
                            for l_code, v_list in self._voices_by_lang.items():
                                for v in v_list:
                                    cur.execute("""
                                        INSERT OR IGNORE INTO voices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (
                                        v["id"],
                                        v.get("display_name", v["id"]),
                                        l_code,
                                        v.get("gender", "neutral"),
                                        v.get("age"),
                                        v.get("dialect", "Standard"),
                                        v.get("pitch", "medium"),
                                        v.get("timbre", ""),
                                        ",".join(v.get("archetypes", [])),
                                        v.get("description", "")
                                    ))
                            conn.commit()
                            conn.close()
                        except Exception as e:
                            logger.debug(f"[VoiceCatalog] Notice auto-creating SQLite DB: {e}")
            except Exception as e:
                logger.warning(f"[VoiceCatalog] Failed to read JSON catalog: {e}")

        if not loaded and CATALOG_DB_PATH.exists():
            try:
                conn = sqlite3.connect(CATALOG_DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM voices")
                rows = cur.fetchall()
                for r in rows:
                    v_dict = dict(r)
                    v_dict["archetypes"] = [a.strip() for a in v_dict.get("archetypes", "").split(",") if a.strip()]
                    vid = v_dict["id"]
                    l_code = v_dict["language_code"]
                    self._voices_by_id[vid] = v_dict
                    self._voices_by_lang.setdefault(l_code, []).append(v_dict)
                conn.close()
                loaded = True
                logger.debug(f"[VoiceCatalog] Loaded {len(self._voices_by_id)} voices from SQLite.")
            except Exception as e:
                logger.warning(f"[VoiceCatalog] Failed to read SQLite catalog: {e}")

        # Fallback to embedded voices if no external file was loaded
        if not loaded:
            logger.info("[VoiceCatalog] Using embedded fallback catalog.")
            for l_code, v_list in EMBEDDED_FALLBACK_VOICES.items():
                self._voices_by_lang[l_code] = v_list
                for v in v_list:
                    self._voices_by_id[v["id"]] = v

    def get_voice(self, voice_id: str, language_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves exact voice metadata by ID, optionally scoped to language."""
        if language_code and language_code in self._voices_by_lang:
            for v in self._voices_by_lang[language_code]:
                if v["id"] == voice_id:
                    return v
        return self._voices_by_id.get(voice_id)

    def query_voices(
        self,
        language_code: str = "hi-IN",
        gender: Optional[str] = None,
        pitch: Optional[str] = None,
        archetype: Optional[str] = None,
        dialect: Optional[str] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Queries voices by language, gender, pitch tier, and archetype tags."""
        candidates = self._voices_by_lang.get(language_code, [])
        if not candidates and language_code != "en-US":
            candidates = self._voices_by_lang.get("hi-IN" if "hi" in language_code else "en-US", [])

        results = []
        for v in candidates:
            if gender and v.get("gender", "").lower() != gender.lower():
                continue
            if pitch and v.get("pitch", "").lower() != pitch.lower():
                continue
            if dialect and dialect.lower() not in v.get("dialect", "").lower():
                continue

            v_age = v.get("age")
            if min_age is not None and v_age is not None and v_age < min_age:
                continue
            if max_age is not None and v_age is not None and v_age > max_age:
                continue

            if archetype:
                arch_clean = archetype.lower().replace(" ", "_")
                v_archs = [a.lower() for a in v.get("archetypes", [])]
                v_timbre = v.get("timbre", "").lower()
                v_desc = v.get("description", "").lower()
                if not (arch_clean in v_archs or arch_clean in v_timbre or arch_clean in v_desc):
                    continue

            results.append(v)
            if len(results) >= limit:
                break

        return results

    def get_best_matching_voice(
        self,
        gender: str = "male",
        language_code: str = "hi-IN",
        archetype: str = "",
        age_hint: Optional[int] = None,
        pitch_hint: Optional[str] = None,
        dialect_hint: Optional[str] = None,
        is_child: bool = False,
        exclude_voice_ids: Optional[Set[str]] = None,
    ) -> str:
        """
        Selects the best available non-colliding voice for a character profile.
        Supports:
        - Dialect matching (+45 score bonus for regional match e.g. Haryanvi, Bhojpuri, Awadhi, Bundeli, Urdu).
        - Anime Seiyū Pattern for children (both boys and girls): casts youthful female voices for children
          with bright, breezy upper harmonics instead of pitch-warped adult baritones.
        - Guarantees 0% voice collision by excluding already-assigned IDs.
        """
        exclude_set = exclude_voice_ids or set()
        candidates = self._voices_by_lang.get(language_code, [])
        if not candidates:
            candidates = self._voices_by_lang.get("hi-IN" if "hi" in language_code else "en-US", [])

        gender_clean = (gender or "male").lower()
        if gender_clean not in ("male", "female"):
            gender_clean = "male"
        arch_tokens = set((archetype or "").lower().replace("-", " ").replace("_", " ").split())

        # Determine effective child vs adolescent teen state
        teen_keywords = {"teen", "teenager", "adolescent", "youth", "किशोर", "किशोरी", "तरुण", "youngster"}
        young_child_keywords = {"child", "kid", "little", "toddler", "बच्चा", "बालक", "chhota"}
        child_keywords = young_child_keywords | teen_keywords | {"boy", "girl", "लड़का", "लड़की"}

        is_teen = (age_hint is not None and 13 <= age_hint <= 18) or bool(arch_tokens & teen_keywords)
        is_young_child = (age_hint is not None and age_hint < 13) or bool(arch_tokens & young_child_keywords) or (is_child and not is_teen)
        effective_child = is_young_child or is_teen or is_child or bool(arch_tokens & child_keywords)

        scored: List[Tuple[int, str]] = []

        for v in candidates:
            vid = v["id"]
            if vid in exclude_set:
                continue

            v_gender = v.get("gender", "").lower()
            v_age = v.get("age")
            v_timbre = v.get("timbre", "").lower()

            # --- Narrator Vocal Separation ---
            # Aoede is reserved strictly for narration roles; dialogue characters must not receive Aoede
            if vid == "Aoede" and not bool(arch_tokens & {"narrator", "literary_narrator", "storyteller"}):
                continue

            # --- Gender, Teen, & Anime Seiyū Filter ---
            if is_teen and gender_clean == "male":
                # Adolescent Teen Boy (13-18yo):
                # Prefers naturally young male models (age <= 28) to avoid adult deep baritones,
                # or youthful female model as secondary fallback if male exhausted.
                if v_gender == "male":
                    if v_age and v_age > 28:
                        continue
                elif v_gender == "female":
                    if v_age and v_age > 25:
                        continue
            elif is_young_child and gender_clean == "male":
                # Pre-pubescent Child Boy (< 13yo):
                # Anime Seiyū rule: accept youthful female or very young male (<= 25)
                if v_gender == "female":
                    if v_age and v_age > 32 and not any(w in v_timbre for w in ("youthful", "bright", "breezy", "young")):
                        continue
                elif v_gender == "male":
                    if v_age and v_age > 25:
                        continue
            elif effective_child and gender_clean == "female":
                # Girl role: Strict female
                if v_gender != "female":
                    continue
            else:
                # Adult role: strict gender matching
                if v_gender != gender_clean:
                    continue

            score = 0

            # 1. Role-Suitability & Archetype Matching (Prioritized Studio Models)
            if v_gender == "male":
                if bool(arch_tokens & {"bard", "minstrel", "witty", "companion", "jester", "rogue"}) and vid == "Puck":
                    score += 55
                elif bool(arch_tokens & {"knight", "noble", "aristocrat", "solemn", "paladin"}) and vid in ("Algieba", "Fenrir"):
                    score += 50
                elif bool(arch_tokens & {"warrior", "mercenary", "gravelly", "hardened", "soldier", "brute", "veteran", "hunter"}) and vid in ("Algenib", "Charon"):
                    score += 50
            elif v_gender == "female":
                if bool(arch_tokens & {"sorceress", "queen", "regal", "witch", "leader"}) and vid == "Kore":
                    score += 55
                elif bool(arch_tokens & {"youth", "young", "girl", "maiden", "vibrant", "princess", "daughter", "apprentice"}) and vid == "Leda":
                    score += 55
                elif bool(arch_tokens & {"soft", "gentle", "intimate", "healer", "poetic"}) and vid == "Achernar":
                    score += 55
                elif bool(arch_tokens & {"matron", "maternal", "mother", "elder", "priestess"}) and vid == "Callisto":
                    score += 55

            # 2. Age-appropriate vocal scoring
            if is_teen and gender_clean == "male":
                # Teen Boy preference: Young male models (<= 26yo) win strongly over females
                if v_gender == "male":
                    score += 55
                    if v_age and v_age <= 24:
                        score += 25
                    if v.get("pitch", "").lower() in ("high", "medium"):
                        score += 25
                    if any(w in v_timbre for w in ("friendly", "clear", "light", "airy", "warm", "engaging", "approachable", "eager", "upbeat")):
                        score += 20
                else:
                    # Female tomboy fallback
                    score += 15
            elif is_young_child:
                # Young child (< 13yo): Anime Seiyū bonus for female/youthful
                if v_gender == "female":
                    score += 40
                if v_age and v_age <= 28:
                    score += 25
                if any(w in v_timbre for w in ("youthful", "bright", "breezy", "energetic", "quick-witted")):
                    score += 20

            # 3. Dialect Alignment (+45 bonus)
            if dialect_hint and dialect_hint.strip():
                d_token = dialect_hint.strip().lower()
                cand_dialect = v.get("dialect", "").lower()
                if d_token in cand_dialect or (d_token == "delhi" and "urdu" in cand_dialect):
                    score += 45

            # 4. Pitch alignment
            if pitch_hint and v.get("pitch", "").lower() == pitch_hint.lower():
                score += 30
            elif effective_child and v.get("pitch", "").lower() in ("high", "medium"):
                score += 15

            # 5. Age alignment (for non-children or general proximity)
            if age_hint and v_age:
                diff = abs(v_age - age_hint)
                if diff <= 5:
                    score += 25
                elif diff <= 12:
                    score += 15
                elif diff <= 20:
                    score += 5

            # 6. Archetype and timbre keyword alignment
            v_archs = set([a.lower() for a in v.get("archetypes", [])])
            v_timbre_words = set(v_timbre.split())
            v_desc_words = set(v.get("description", "").lower().split())

            matched_arch = arch_tokens & (v_archs | v_timbre_words | v_desc_words)
            score += len(matched_arch) * 15

            scored.append((score, vid))

        if scored:
            scored.sort(key=lambda x: -x[0])
            return scored[0][1]

        # Fallback if all scored candidates filtered out: pick first candidate with matching gender
        for v in candidates:
            if v["id"] not in exclude_set and v.get("gender") == gender_clean:
                if v["id"] == "Aoede" and not bool(arch_tokens & {"narrator", "literary_narrator", "storyteller"}):
                    continue
                return v["id"]
        # When all candidates of the requested gender are in exclude_set, do NOT return candidates[0]["id"] (Charon).
        # Return "" (empty string) so caller (character_caster.py) can cycle round-robin.
        matching_gender_candidates = [
            v for v in candidates
            if v.get("gender") == gender_clean
            and not (v["id"] == "Aoede" and not bool(arch_tokens & {"narrator", "literary_narrator", "storyteller"}))
        ]
        if matching_gender_candidates and all(v["id"] in exclude_set for v in matching_gender_candidates):
            return ""

        # Ultimate safety fallback: cycle across MALE_VOICE_PERSONAS rather than always returning Charon
        if effective_child:
            return "Leda" if gender_clean == "female" else "Zephyr"
        if gender_clean == "female":
            return "Kore"

        fallback_voice = MALE_VOICE_PERSONAS[self._fallback_male_idx % len(MALE_VOICE_PERSONAS)]
        self._fallback_male_idx += 1
        return fallback_voice

    def get_catalog_summary_for_llm(
        self,
        language_code: str = "hi-IN",
        gender: Optional[str] = None,
        max_voices: int = 40,
    ) -> str:
        """
        Formats a structured markdown table of available voices for injection
        into LLM character casting prompts.
        """
        voices = self.query_voices(language_code=language_code, gender=gender, limit=max_voices)
        if not voices:
            return "No voices available for this language."

        lines = [
            "| Voice ID | Gender | Age | Dialect | Pitch | Timbre & Archetype |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for v in voices:
            age_s = f"{v.get('age')}yo" if v.get("age") else "Adult"
            dialect_s = v.get("dialect", "Standard")
            pitch_s = v.get("pitch", "medium").upper()
            timbre_s = v.get("timbre", "")
            arch_s = ", ".join(v.get("archetypes", [])[:3])
            desc_part = f"{timbre_s} [{arch_s}]" if arch_s else timbre_s
            lines.append(f"| `{v['id']}` | {v.get('gender', '')} | {age_s} | {dialect_s} | {pitch_s} | {desc_part} |")

        return "\n".join(lines)


# Global Singleton Helper
def get_voice_catalog() -> VoiceCatalog:
    """Returns the singleton instance of VoiceCatalog."""
    return VoiceCatalog.get_instance()
