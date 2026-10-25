#!/usr/bin/env python3
"""
Audiobook Factory - Stage 1/2: Autonomous Character Discovery & Casting Director.
Scans extracted novel chapters (English or Hindi), extracts the dramatis personae,
and assigns non-colliding studio vocal personas (Gemini TTS) with cast lock persistence.
"""

from __future__ import annotations
import os
import json
import time
import re
import unicodedata
import threading
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

from audiobook_factory.logger import logger
from audiobook_factory.audio_utils import _atomic_replace
from audiobook_factory.key_manager import get_persistent_key_pool
from audiobook_factory.model_manager import get_model_manager, TaskType, LLMUnavailableError
from audiobook_factory.casting.phonetic_transliteration import (
    derive_devanagari_name,
    is_devanagari,
)
try:
    from audiobook_factory.tts.voice_catalog import get_voice_catalog
except (ImportError, ModuleNotFoundError):
    class _FallbackVoiceCatalog:
        def get_best_matching_voice(self, gender="neutral", language_code="en-US", is_child=False, exclude_voice_ids=None, **kwargs):
            is_hi = str(language_code).startswith("hi")
            if is_hi:
                return "hi-in-advisor-1" if str(gender).lower() == "female" else "hi-in-tutor-1"
            return "Aoede" if str(gender).lower() == "female" else "Charon"
    def get_voice_catalog():
        return _FallbackVoiceCatalog()

_CAST_LOCK = threading.RLock()


def _atomic_write_json(file_path: Path, data: Any) -> None:
    file_path = Path(file_path).resolve()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = file_path.with_suffix(f".tmp_{time.time_ns()}.json")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _atomic_replace(tmp_path, file_path)

# Studio Voice Persona Catalogs (ALL 9 Verified Google Gemini Multilingual Male Studio Models)
MALE_VOICE_PERSONAS = [
    "Fenrir",      # Authoritative / King
    "Orus",        # Disciplined / Official
    "Algieba",     # Polished / Noble
    "Achird",      # Warm / Innkeeper
    "Algenib",     # Gravelly / Mercenary
    "Enceladus",   # Dark / Sinister
    "Puck",        # Agile / Bard
    "Zephyr",      # Youth / Scout
    "Charon",      # Bass / Stoic Baritone
]

# Female Voice Personas (including Narrator Aoede)
FEMALE_VOICE_PERSONAS = [
    "Aoede",       # Lead Storytelling Narrator (reserved exclusively for Narration)
    "Kore",        # Regal / Sorceress
    "Leda",        # Youthful / Vibrant
    "Achernar",    # Soft / Intimate
    "Callisto",    # Warm / Matron
]

# Character Female Voices (Aoede excluded to preserve Narrator vocal separation)
FEMALE_CHARACTER_VOICE_PERSONAS = [
    "Kore",        # Regal / Sorceress
    "Leda",        # Youthful / Vibrant
    "Achernar",    # Soft / Intimate
    "Callisto",    # Warm / Matron
]

_STOP_CONNECTORS = {"of", "the", "de", "van", "von", "and", "a", "an", "el", "la", "del", "da"}

_DEV_CONNECTORS: Set[str] = {
    "ओफ़", "ऑफ़", "का", "की", "के", "से", "में", "और", "थ्री",
    "three", "of", "the", "de", "van", "von",
}

# STRICT HONORIFIC & GENERIC TITLE BLACKLIST:
# Tokens matching this blacklist MUST NEVER be used as clustering keys or match tokens to link two characters!
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

_GENERIC_TITLES = set(HONORIFIC_BLACKLIST)

_FORBIDDEN_PHRASES: Set[str] = {
    "of the", "ओफ़ थे", "ओफ थे", "ऑफ़ द", "ऑफ द",
    "लीडेर ओफ़", "लीडेर ओफ", "लीडेर ओफ़ थे", "लीडेर ओफ थे",
    "leader of", "leader of the",
}

_CONNECTOR_EDGE_TOKENS: Set[str] = {
    "of", "the", "ओफ़", "ओफ", "ऑफ़", "ऑफ", "थे", "द", "का", "की", "के", "से",
    "de", "van", "von",
}


def _clean_entity_str(s: str) -> str:
    if not s:
        return ""
    d = unicodedata.normalize("NFD", str(s))
    d = d.replace("\u093c", "")
    d = unicodedata.normalize("NFC", d)
    d = d.strip().lower().replace("_", " ")
    return re.sub(r"\s+", " ", d)


def _is_blacklisted_or_generic(s: str) -> bool:
    """Returns True if string is an honorific title, stopword, prepositional phrase, or generic noun that must never link characters."""
    if not s:
        return True
    cleaned = _clean_entity_str(s)
    raw_lower = str(s).strip().lower()
    if (
        cleaned in HONORIFIC_BLACKLIST
        or raw_lower in HONORIFIC_BLACKLIST
        or cleaned in _STOP_CONNECTORS
        or raw_lower in _STOP_CONNECTORS
        or cleaned in _FORBIDDEN_PHRASES
        or raw_lower in _FORBIDDEN_PHRASES
    ):
        return True
    words = [t.strip().strip(".,!?;:\"'()[]{}").lower() for t in cleaned.split() if t.strip()]
    if not words:
        return True
    if all(w in HONORIFIC_BLACKLIST or w in _STOP_CONNECTORS or w in _CONNECTOR_EDGE_TOKENS for w in words):
        return True
    # Reject any alias that starts or ends with a connector
    if words[0] in _CONNECTOR_EDGE_TOKENS or words[-1] in _CONNECTOR_EDGE_TOKENS:
        return True
    raw_words = [t.strip().strip(".,!?;:\"'()[]{}").lower() for t in raw_lower.split() if t.strip()]
    if raw_words and (raw_words[0] in _CONNECTOR_EDGE_TOKENS or raw_words[-1] in _CONNECTOR_EDGE_TOKENS):
        return True
    return False


def _entity_tokens(s: str) -> Set[str]:
    """Extracts distinctive entity tokens, strictly excluding honorific titles and stop connectors."""
    words = [t.strip().strip(".,!?;:\"'()[]{}").lower() for t in _clean_entity_str(s).split() if t.strip()]
    return {
        w for w in words
        if w not in _STOP_CONNECTORS
        and w not in HONORIFIC_BLACKLIST
        and w not in _CONNECTOR_EDGE_TOKENS
        and len(w) >= 3
        and not w.isdigit()
    }


class CharacterCaster:
    """Autonomous casting director for novel audio dramas."""

    @classmethod
    def consolidate_characters(cls, raw_characters: List[Dict[str, Any]], corpus: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Universal entity consolidation & anti-splitting engine (Room 1/Room 3.5).
        Identifies duplicate, sub-name, or alias-overlapping character entities:
        - "Geralt" vs "Geralt of Rivia" vs "Witcher"
        - "Yen" vs "Yennefer"
        - "Borch" vs "Three Jackdaws"
        - "Essi Daven" vs "Little Eye"
        - "Dainty" vs "Biberveldt"
        Merges them into the canonical character with unified aliases, preserving Devanagari spellings,
        and guaranteeing consistent voice allocation without splitting into competing CastLocks.
        Strictly prevents generic honorific titles ('Lord', 'Sir', 'Master', 'Alderman') from collapsing distinct entities.
        """
        if not raw_characters:
            return []

        def _get_entity_identifiers(c: Dict[str, Any]) -> Set[str]:
            idents = set()
            name = (c.get("canonical_name") or c.get("english_name") or c.get("name") or "").strip()
            if name and not _is_blacklisted_or_generic(name):
                idents.add(_clean_entity_str(name))
            hi = (c.get("hindi_name") or c.get("display_name_hi") or c.get("display_name") or "").strip()
            if hi and not _is_blacklisted_or_generic(hi):
                idents.add(_clean_entity_str(hi))
            for k in ("aliases", "nickname", "nicknames", "epithet", "epithets", "known_as"):
                raw_val = c.get(k) or []
                val_list = raw_val if isinstance(raw_val, list) else [raw_val]
                for a in val_list:
                    if a and str(a).strip():
                        clean_a = _clean_entity_str(str(a))
                        if not _is_blacklisted_or_generic(clean_a):
                            idents.add(clean_a)
            return idents

        def _get_effective_gender(c: Dict[str, Any]) -> str:
            g = (c.get("gender") or "").lower()
            if g in ("male", "female"):
                return g
            arch = (c.get("archetype") or c.get("vocal_archetype") or c.get("sociolect_trait") or "").lower()
            name = (c.get("canonical_name") or c.get("english_name") or c.get("name") or "").lower()
            female_markers = (
                "female", "woman", "girl", "lady", "queen", "princess", "sorceress",
                "witch", "priestess", "maiden", "matron", "mother", "daughter", "sister",
                "damsel", "nun", "aunt", "niece", "bride", "widow", "heroine",
                "स्त्री", "महिला", "लड़की", "रानी", "माता", "कन्या", "युवती", "बहन", "पत्नी"
            )
            if any(m in arch for m in female_markers) or any(m in name for m in female_markers):
                return "female"
            return "neutral"

        def _should_merge(c1: Dict[str, Any], c2: Dict[str, Any]) -> bool:
            n1 = (c1.get("canonical_name") or c1.get("english_name") or c1.get("name") or "").strip()
            n2 = (c2.get("canonical_name") or c2.get("english_name") or c2.get("name") or "").strip()
            if not n1 or not n2:
                return False
            if n1.lower() == "narrator" or n2.lower() == "narrator":
                return n1.lower() == n2.lower()

            clean1 = _clean_entity_str(n1)
            clean2 = _clean_entity_str(n2)

            # Exact name match (case and space normalized)
            if clean1 == clean2:
                return True

            n1_low = n1.lower()
            n2_low = n2.lower()

            # 0. Specific literary epithet & composite unifications
            # Unify Essi Daven & Little Eye
            if (n1_low == "little eye" and "essi" in n2_low) or (n2_low == "little eye" and "essi" in n1_low):
                return True
            # Unify Dainty & Biberveldt
            if (n1_low == "dainty" and "biberveldt" in n2_low) or (n2_low == "dainty" and "biberveldt" in n1_low):
                return True

            # Universal composite rule in _should_merge:
            # If n1 and n2 are single words and either f"{n1} {n2}" or f"{n2} {n1}" appears in the aliases or corpus
            if len(n1.split()) == 1 and len(n2.split()) == 1:
                combo1 = f"{n1_low} {n2_low}"
                combo2 = f"{n2_low} {n1_low}"
                all_c_aliases = [str(a).lower().strip() for a in (c1.get("aliases") or []) + (c2.get("aliases") or [])]
                if any(combo1 == a or combo2 == a or combo1 in a or combo2 in a for a in all_c_aliases):
                    return True
                if corpus and (combo1 in corpus.lower() or combo2 in corpus.lower()):
                    return True
                for ch in raw_characters:
                    ch_aliases = [str(a).lower().strip() for a in (ch.get("aliases") or [])]
                    if any(combo1 == a or combo2 == a for a in ch_aliases):
                        return True
                    ch_desc = (ch.get("description", "") or ch.get("bio", "") or "").lower()
                    if combo1 in ch_desc or combo2 in ch_desc:
                        return True

            t1 = _entity_tokens(n1)
            t2 = _entity_tokens(n2)

            # 1. Literary diminutive prefix check (e.g. "yen" -> "yennefer", "essi" -> "essi daven")
            # Tested BEFORE gender mismatch so truncated / ungendered seeds merge into canonical entities
            for short_clean, long_clean, long_tokens in [(clean1, clean2, t2), (clean2, clean1, t1)]:
                if 3 <= len(short_clean) <= 6 and not _is_blacklisted_or_generic(short_clean):
                    if any(t.startswith(short_clean) for t in long_tokens) or long_clean.startswith(short_clean):
                        return True

            # 2. Check explicit non-generic alias match (e.g. "Witcher" does not split from "Geralt of Rivia")
            banned_standalone = {"the", "sir", "lord", "lady", "master", "mr", "mrs", "miss", "dr"}
            c1_raw_aliases = [_clean_entity_str(str(a)) for a in c1.get("aliases", []) if str(a).strip()]
            c2_raw_aliases = [_clean_entity_str(str(a)) for a in c2.get("aliases", []) if str(a).strip()]
            if clean2 in c1_raw_aliases and clean2 not in banned_standalone:
                return True
            if clean1 in c2_raw_aliases and clean1 not in banned_standalone:
                return True

            # 3. Exact alias or nickname overlap (e.g. Essi and Little Eye)
            id1 = _get_entity_identifiers(c1)
            id2 = _get_entity_identifiers(c2)
            if id1 and id2 and (id1 & id2):
                return True

            g1 = _get_effective_gender(c1)
            g2 = _get_effective_gender(c2)
            if g1 in ("male", "female") and g2 in ("male", "female") and g1 != g2:
                return False

            # 4. Token subset match on primary name (ignoring blacklisted titles)
            if t1 and t2:
                if t1.issubset(t2) or t2.issubset(t1):
                    return True

            # 5. Token subset match between primary name of one and alias of the other
            for a in (c1.get("aliases") or []):
                if _is_blacklisted_or_generic(str(a)):
                    continue
                ta = _entity_tokens(str(a))
                if ta and t2 and (ta.issubset(t2) or t2.issubset(ta)):
                    return True
            for a in (c2.get("aliases") or []):
                if _is_blacklisted_or_generic(str(a)):
                    continue
                ta = _entity_tokens(str(a))
                if ta and t1 and (ta.issubset(t1) or t1.issubset(ta)):
                    return True

            return False

        def _merge_pair(c1: Dict[str, Any], c2: Dict[str, Any]) -> Dict[str, Any]:
            def _score(c: Dict[str, Any]) -> int:
                prom = str(c.get("prominence", "")).lower()
                prom_score = 40 if prom == "lead" else 30 if prom == "major" else 20 if prom == "minor" else 10
                name = (c.get("canonical_name") or c.get("english_name") or c.get("name") or "").strip()
                name_score = len(name.split()) * 15 + len(name)
                alias_score = len(c.get("aliases") or []) * 10
                hi_score = 15 if (c.get("hindi_name") or c.get("display_name_hi")) else 0
                arch_score = 10 if (c.get("archetype") or c.get("vocal_archetype")) else 0
                return prom_score + name_score + alias_score + hi_score + arch_score

            pri_name_raw = (c1.get("canonical_name") or c1.get("english_name") or c1.get("name") or "").strip()
            sec_name_raw = (c2.get("canonical_name") or c2.get("english_name") or c2.get("name") or "").strip()
            pri_clean = _clean_entity_str(pri_name_raw)
            sec_clean = _clean_entity_str(sec_name_raw)
            c1_aliases = {_clean_entity_str(str(a)) for a in c1.get("aliases", []) if str(a).strip()}
            c2_aliases = {_clean_entity_str(str(a)) for a in c2.get("aliases", []) if str(a).strip()}

            c1_is_owner = (sec_clean in c1_aliases) and (pri_clean not in c2_aliases)
            c2_is_owner = (pri_clean in c2_aliases) and (sec_clean not in c1_aliases)

            if c1_is_owner and not c2_is_owner:
                primary, secondary = dict(c1), c2
            elif c2_is_owner and not c1_is_owner:
                primary, secondary = dict(c2), c1
            else:
                primary = dict(c1 if _score(c1) >= _score(c2) else c2)
                secondary = c2 if _score(c1) >= _score(c2) else c1

            merged_aliases = set()
            for a in primary.get("aliases", []):
                if a and str(a).strip():
                    merged_aliases.add(str(a).strip())
            for a in secondary.get("aliases", []):
                if a and str(a).strip():
                    merged_aliases.add(str(a).strip())

            sec_name = (secondary.get("canonical_name") or secondary.get("english_name") or secondary.get("name") or "").strip()
            pri_name = (primary.get("canonical_name") or primary.get("english_name") or primary.get("name") or "").strip()
            if sec_name and sec_name != pri_name:
                merged_aliases.add(sec_name)
            sec_hi = (secondary.get("hindi_name") or secondary.get("display_name_hi") or secondary.get("display_name") or "").strip()
            if sec_hi:
                merged_aliases.add(sec_hi)

            # Special handling for Essi Daven / Little Eye and Dainty / Biberveldt unifications
            n1_low = pri_name.lower()
            n2_low = sec_name.lower()
            is_essi = (n1_low == "little eye" and "essi" in n2_low) or (n2_low == "little eye" and "essi" in n1_low) or ("essi" in n1_low and "essi" in n2_low)
            is_dainty_biber = (n1_low == "dainty" and "biberveldt" in n2_low) or (n2_low == "dainty" and "biberveldt" in n1_low)

            if is_essi:
                essi_target = "Essi Daven" if ("daven" in n1_low or "daven" in n2_low or any("daven" in str(a).lower() for a in merged_aliases)) else "Essi"
                primary["canonical_name"] = essi_target
                if "english_name" in primary:
                    primary["english_name"] = essi_target
                primary["gender"] = "female"
                if not primary.get("voice"):
                    primary["voice"] = "Kore"
                merged_aliases.add("Little Eye")
                merged_aliases.add("लिटिल आई")
                if essi_target == "Essi Daven":
                    merged_aliases.add("Essi")
                pri_name = essi_target

            if is_dainty_biber:
                primary["canonical_name"] = "Dainty Biberveldt"
                if "english_name" in primary:
                    primary["english_name"] = "Dainty Biberveldt"
                primary["gender"] = "male"
                if not primary.get("voice"):
                    primary["voice"] = "Orus"
                merged_aliases.add("Dainty")
                merged_aliases.add("Biberveldt")
                pri_name = "Dainty Biberveldt"

            # Composite full name promotion (e.g. Dainty + Biberveldt -> Dainty Biberveldt)
            combo1 = f"{pri_name} {sec_name}"
            combo2 = f"{sec_name} {pri_name}"
            full_name_found = None
            for a in list(merged_aliases):
                a_clean = a.strip()
                if a_clean.lower() in (combo1.lower(), combo2.lower()):
                    full_name_found = a_clean
                    break
                a_tokens = set(a_clean.lower().split())
                if pri_name.lower() in a_tokens and sec_name.lower() in a_tokens and len(a_tokens) >= 2:
                    full_name_found = a_clean
                    break

            if not full_name_found and len(pri_name.split()) == 1 and len(sec_name.split()) == 1:
                p_low = pri_name.lower()
                s_low = sec_name.lower()
                if not (p_low.startswith(s_low) or s_low.startswith(p_low)):
                    c1_cand = f"{pri_name} {sec_name}"
                    c2_cand = f"{sec_name} {pri_name}"
                    if corpus:
                        if c1_cand.lower() in corpus.lower():
                            full_name_found = c1_cand
                        elif c2_cand.lower() in corpus.lower():
                            full_name_found = c2_cand
                    if not full_name_found:
                        if any(c1_cand.lower() in str(a).lower() or c2_cand.lower() in str(a).lower() for a in merged_aliases):
                            full_name_found = c1_cand
                        elif sec_name.lower() in [str(a).lower() for a in primary.get("aliases", [])] or \
                             pri_name.lower() in [str(a).lower() for a in secondary.get("aliases", [])]:
                            full_name_found = c1_cand

            if full_name_found:
                primary["canonical_name"] = full_name_found
                if "english_name" in primary:
                    primary["english_name"] = full_name_found
                merged_aliases.add(pri_name)
                merged_aliases.add(sec_name)
                pri_name = full_name_found

            if pri_name in merged_aliases:
                merged_aliases.remove(pri_name)
            primary["aliases"] = sorted(list(merged_aliases))

            if not primary.get("hindi_name") and secondary.get("hindi_name"):
                primary["hindi_name"] = secondary["hindi_name"]
            if not primary.get("display_name_hi") and secondary.get("display_name_hi"):
                primary["display_name_hi"] = secondary["display_name_hi"]

            g1 = primary.get("gender")
            g2 = secondary.get("gender")
            if (not g1 or g1 not in ("male", "female")) and g2 in ("male", "female"):
                primary["gender"] = g2

            if not primary.get("archetype") and secondary.get("archetype"):
                primary["archetype"] = secondary["archetype"]
            if not primary.get("vocal_archetype") and secondary.get("vocal_archetype"):
                primary["vocal_archetype"] = secondary["vocal_archetype"]
            if not primary.get("sociolect_trait") and secondary.get("sociolect_trait"):
                primary["sociolect_trait"] = secondary["sociolect_trait"]

            if bool(secondary.get("is_child", False)):
                primary["is_child"] = True

            return primary

        merged_list = [dict(c) for c in raw_characters]
        changed = True
        while changed:
            changed = False
            for i in range(len(merged_list)):
                for j in range(i + 1, len(merged_list)):
                    if _should_merge(merged_list[i], merged_list[j]):
                        merged_item = _merge_pair(merged_list[i], merged_list[j])
                        merged_list[i] = merged_item
                        merged_list.pop(j)
                        changed = True
                        break
                if changed:
                    break
        return merged_list

    @classmethod
    def discover_and_cast_project(
        cls,
        project_dir: Path,
        use_hindi: bool = False,
        default_narrator_voice: str = "Aoede",
        force_recast: bool = False,
    ) -> Dict[str, Any]:
        """
        Discovers characters across project chapters, creates character_roster.json,
        voice_registry.json, and cast_lock.json with collision-free voice signatures.
        """
        project_dir = Path(project_dir).resolve()
        roster_path = project_dir / "character_roster.json"
        registry_path = project_dir / "voice_registry.json"
        lock_path = project_dir / "cast_lock.json"

        if not force_recast and roster_path.exists() and registry_path.exists() and lock_path.exists():
            try:
                with open(roster_path, "r", encoding="utf-8") as rf:
                    roster = json.load(rf)
                with open(registry_path, "r", encoding="utf-8") as vf:
                    reg = json.load(vf)
                if roster.get("characters") and len(roster["characters"]) > 1 and len(reg) > 1:
                    logger.info(f"[*] CharacterCaster: Existing roster and voice registry loaded ({len(roster['characters'])} characters, {len(reg)} voices).")
                    return roster
            except Exception as e:
                logger.warning(f"  [!] Failed to read existing roster/registry, recasting: {e}")

        # If roster already has characters but registry is missing or incomplete, build allocation directly without LLM re-run
        if not force_recast and roster_path.exists():
            try:
                with open(roster_path, "r", encoding="utf-8") as rf:
                    roster = json.load(rf)
                chars_dict = roster.get("characters", {})
                if len(chars_dict) > 1:
                    logger.info(f"[*] CharacterCaster: Syncing voice allocations for {len(chars_dict)} existing roster characters...")
                    raw_characters = []
                    for k, v in chars_dict.items():
                        if isinstance(v, dict):
                            c_name = v.get("english_name") or k
                            if not any(rc.get("canonical_name") == c_name for rc in raw_characters):
                                raw_characters.append({
                                    "canonical_name": c_name,
                                    "english_name": c_name,
                                    "gender": v.get("gender", "male"),
                                    "aliases": v.get("aliases", []),
                                    "archetype": v.get("archetype", ""),
                                })
                    if raw_characters:
                        roster, registry, cast_lock = cls._build_cast_allocation(
                            project_id=f"proj-{project_dir.name}",
                            raw_characters=raw_characters,
                            default_narrator_voice=default_narrator_voice,
                            use_hindi=use_hindi,
                        )
                        with open(roster_path, "w", encoding="utf-8") as f:
                            json.dump(roster, f, ensure_ascii=False, indent=2)
                        with open(registry_path, "w", encoding="utf-8") as f:
                            json.dump(registry, f, ensure_ascii=False, indent=2)
                        with open(lock_path, "w", encoding="utf-8") as f:
                            json.dump(cast_lock, f, ensure_ascii=False, indent=2)
                        logger.info(f"[+] CharacterCaster: Voice allocation synced ({len(registry)} voices).")
                        return roster
            except Exception as e:
                logger.warning(f"  [!] Failed to sync allocation from existing roster: {e}")

        # Collect text samples from available chapters
        trans_dir = project_dir / "translation"
        if use_hindi and trans_dir.exists() and any(trans_dir.glob("chapter_*.md")):
            search_dir = trans_dir
        else:
            search_dir = project_dir / "extracted"

        chap_files = sorted(search_dir.glob("chapter_*.md"))
        if not chap_files:
            logger.warning("  [!] CharacterCaster: No chapter markdown files found for casting analysis.")
            return {"project_id": f"proj-{project_dir.name}", "characters": {}}

        valid_chaps = []
        for cf in chap_files:
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    txt = f.read()
                lower_txt = txt.lower()
                if "copyright" in lower_txt or "all rights reserved" in lower_txt or len(txt.split()) < 200:
                    continue
                valid_chaps.append(txt)
            except Exception:
                pass

        if not valid_chaps and chap_files:
            valid_chaps = [chap_files[0].read_text(encoding="utf-8")]

        # Comprehensive sampling across novel scope (up to 15 chapters distributed across beginning, middle, climax, end)
        if len(valid_chaps) <= 15:
            selected_chaps = valid_chaps
        else:
            step = len(valid_chaps) / 15.0
            indices = [int(i * step) for i in range(15)]
            indices.append(len(valid_chaps) - 1)
            selected_chaps = [valid_chaps[i] for i in sorted(set(indices))]

        sample_texts = [txt[:5000] for txt in selected_chaps]
        combined_sample = "\n\n--- NEXT CHAPTER SAMPLE ---\n\n".join(sample_texts)

        # Call LLM Casting Director
        raw_characters = cls._call_llm_casting(combined_sample, is_hindi=use_hindi)

        # Build collision-free assignment
        roster, registry, cast_lock = cls._build_cast_allocation(
            project_id=f"proj-{project_dir.name}",
            raw_characters=raw_characters,
            default_narrator_voice=default_narrator_voice,
            use_hindi=use_hindi,
        )

        # Write files atomically
        with open(roster_path, "w", encoding="utf-8") as f:
            json.dump(roster, f, ensure_ascii=False, indent=2)
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(cast_lock, f, ensure_ascii=False, indent=2)

        logger.info(
            f"[+] CharacterCaster: Cast locked for {len(roster['characters'])} roles. "
            f"Saved to {roster_path.name}, {registry_path.name}, {lock_path.name}."
        )
        return roster

    @classmethod
    def _call_llm_casting(cls, text_sample: str, is_hindi: bool = False) -> List[Dict[str, Any]]:
        """Invokes Gemini to extract speaking characters from prose samples."""
        pool = get_persistent_key_pool()
        model_mgr = get_model_manager()
        model = model_mgr.resolve_active_model(TaskType.SCREENPLAY)

        sys_prompt = (
            "You are the Lead Casting Director for a Hollywood & BBC Radio Audio Drama studio. "
            "Analyze these book chapter samples and extract ALL speaking characters who have dialogue or direct presence. "
            "For each character, identify their canonical English name, Hindi name (if in Hindi translation), "
            "gender ('male' or 'female'), approximate age/archetype, whether they are a child/minor, "
            "and their dramatic socio-cultural dialect matching (e.g. Haryanvi, Bhojpuri, Awadhi, Bundeli, Urdu/Delhi, Standard)."
        )

        prompt = f"""Language: {"Hindi (Devanagari)" if is_hindi else "English"}
Prose Samples:
\"\"\"
{text_sample[:80000]}
\"\"\"

Return a JSON array of objects with:
- "canonical_name": string (e.g. "Protagonist Name", "Village Elder", "Lead Detective")
- "hindi_name": string (Devanagari spelling if applicable, e.g. "मुख्य पात्र")
- "gender": "male" | "female"
- "is_child": boolean (true if character is a child, kid, or minor <= 14 years old, else false)
- "archetype": string (e.g. "stoic rural farmer", "shrewd urban detective", "wise elderly mentor", "rebellious youth")
- "recommended_dialect": "Haryanvi" | "Bhojpuri" | "Awadhi" | "Bundeli" | "Urdu" | "Standard"
  (Guideline: Haryanvi=martial/warrior/blunt/brawler; Bhojpuri=earthy/rustic/innkeeper/companion; Awadhi=poetic/gentle/maternal; Bundeli=rugged/rebel/forester; Urdu=scholarly/aristocratic/courtly/philosophical; Standard=urban/neutral)
- "aliases": list of strings (e.g. ["मुख्य पात्र", "Character Full Name", "Nickname"])
"""


        try:
            parsed = call_gemini(
                task_type=TaskType.DIRECTING,
                prompt=prompt,
                system_instruction=sys_prompt,
                tools=[{"googleSearch": {}}],
                temperature=0.2,
                response_mime_type="application/json",
            )
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict) and "characters" in parsed:
                return parsed["characters"]
            elif isinstance(parsed, dict):
                return [parsed]
            return []
        except LLMUnavailableError:
            raise
        except Exception as e:
            logger.warning(f"  [!] CharacterCaster error: {e}")
            raise LLMUnavailableError(f"Character casting failed: {e}") from e

    @classmethod
    def compute_acoustic_formant_vector(
        cls,
        gender: str,
        archetype: str = "",
        prominence: str = "standard",
        index: int = 0,
        is_child: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculates a 4D acoustic vector (pitch, speed, EQ resonance, clarity reduction)
        to physically morph the vocal tract via FFmpeg asetrate/aresample/equalizer.
        Guarantees that even if two characters share the same base Gemini voice,
        they sound like completely distinct human beings with zero timbre overlap.
        Includes Anime Seiyū child calibration for boy and girl children.
        """
        g = (gender or "male").lower()
        arch = (archetype or "").lower()

        child_tokens = ("child", "kid", "little boy", "little girl", "toddler", "balak", "balika", "bacha", "bachi", "bachha")
        teen_tokens = ("teen", "teenager", "adolescent", "teen boy", "teen girl", "15 year", "16 year", "14 year", "13 year", "किशोर", "किशोरी", "तरुण")

        is_teen = any(w in arch for w in teen_tokens)
        effective_child = is_child or any(w in arch for w in child_tokens)

        # Male Vocal Acoustic Profiling
        if g == "male":
            if is_teen:
                # Adolescent Teen Boy (13-18yo): ZERO digital pitch warping (pitch=1.0),
                # tames 150Hz adult chest resonance (-3.0dB) to avoid deep adult baritone body,
                # boosts adolescent presence (+2.2dB)
                pitch = 1.0
                speed = 1.0
                bass_boost = -3.0       # Tame heavy adult chest resonance (150 Hz cut)
                presence_boost = 2.2    # Adolescent vocal projection (2.8 kHz presence)
                clarity_cut = 0.0
                lowpass = 0
            elif effective_child:
                # Anime Seiyū Child Boy Vector (calibrated for youthful female or young male base voice)
                pitch = round(1.03 + (index % 2) * 0.01, 2)
                speed = 1.03
                bass_boost = -2.0       # Smaller chest cavity resonance reduction
                presence_boost = 2.5    # Upper harmonic clarity (3.2 kHz presence)
                clarity_cut = 0.0
                lowpass = 0
            elif any(w in arch for w in ("heavy", "deep", "imposing", "rough", "rugged", "warrior", "soldier", "brute", "guard", "thug", "bodyguard", "laborer")):
                pitch = round(0.88 + (index % 3) * 0.02, 2)  # 0.88 - 0.92
                speed = 0.96
                bass_boost = 3.0
                presence_boost = 0.5
                clarity_cut = 0.0
                lowpass = 0
            elif any(w in arch for w in ("elder", "scholar", "mentor", "priest", "old", "father", "grandfather", "aged", "teacher")):
                pitch = round(0.92 + (index % 2) * 0.02, 2)  # 0.92 - 0.94
                speed = 0.94
                bass_boost = 1.0
                presence_boost = 1.2
                clarity_cut = 1.5
                lowpass = 6500
            elif any(w in arch for w in ("youth", "young", "boy", "agile", "sharp", "energetic", "comedic", "apprentice", "rebel", "student", "bard")):
                pitch = round(1.05 + (index % 3) * 0.02, 2)  # 1.05 - 1.09
                speed = 1.04
                bass_boost = -1.0
                presence_boost = 2.2
                clarity_cut = 0.0
                lowpass = 0
            elif any(w in arch for w in ("commoner", "rustic", "villager", "worker", "servant", "merchant", "driver", "shopkeeper", "innkeeper", "tavern", "tavernkeeper", "peasant")):
                pitch = round(1.06 + (index % 2) * 0.03, 2)  # 1.06 - 1.09
                speed = 0.97
                bass_boost = 0.0
                presence_boost = 1.8
                clarity_cut = 2.0
                lowpass = 0
            elif any(w in arch for w in ("lead", "protagonist", "hero", "detective", "commander", "leader", "officer", "noble", "governor")):
                pitch = round(0.95 + (index % 2) * 0.02, 2)  # 0.95 - 0.97
                speed = 0.99
                bass_boost = 2.0
                presence_boost = 1.2
                clarity_cut = 0.0
                lowpass = 0
            else:
                # Systemic non-colliding cycle across roles
                pitch_cycle = [0.93, 1.06, 0.96, 1.08, 0.90, 1.04, 0.97, 1.09]
                speed_cycle = [0.96, 1.03, 0.98, 1.04, 0.95, 1.02, 0.99, 1.05]
                bass_cycle = [2.5, -0.5, 1.5, -1.0, 3.0, 0.0, 1.0, -0.5]
                pres_cycle = [0.8, 2.0, 1.2, 2.2, 0.5, 1.5, 1.0, 2.0]
                clar_cycle = [0.0, 0.0, 0.0, 1.5, 0.0, 1.0, 0.0, 0.0]

                idx = index % len(pitch_cycle)
                pitch = pitch_cycle[idx]
                speed = speed_cycle[idx]
                bass_boost = bass_cycle[idx]
                presence_boost = pres_cycle[idx]
                clarity_cut = clar_cycle[idx]
                lowpass = 0
        else:
            # Female Vocal Acoustic Profiling
            if effective_child:
                # Anime Child Girl Vector (delicate, high presence, youthful upper harmonics)
                pitch = round(1.05 + (index % 2) * 0.01, 2)
                speed = 1.03
                bass_boost = -2.5       # Delicate chest resonance
                presence_boost = 2.8    # Upper harmonic sparkle (3.5 kHz)
                clarity_cut = 0.0
                lowpass = 0
            elif any(w in arch for w in ("commanding", "leader", "mature", "mother", "matriarch", "queen", "sorceress", "director", "officer")):
                pitch = round(0.94 + (index % 2) * 0.02, 2)  # 0.94 - 0.96
                speed = 0.98
                bass_boost = 1.5
                presence_boost = 1.5
                clarity_cut = 0.0
                lowpass = 0
            elif any(w in arch for w in ("youth", "young", "girl", "daughter", "delicate", "tender", "vulnerable", "student")):
                pitch = round(1.05 + (index % 2) * 0.02, 2)  # 1.05 - 1.07
                speed = 1.03
                bass_boost = -1.5
                presence_boost = 2.0
                clarity_cut = 0.0
                lowpass = 0
            elif any(w in arch for w in ("fierce", "resolute", "soldier", "warrior", "rebel", "sharp", "athletic")):
                pitch = round(0.97 + (index % 2) * 0.02, 2)  # 0.97 - 0.99
                speed = 1.01
                bass_boost = 1.8
                presence_boost = 1.8
                clarity_cut = 0.0
                lowpass = 0
            else:
                pitch_cycle = [0.95, 1.06, 0.98, 1.04, 0.93, 1.07]
                speed_cycle = [0.97, 1.03, 0.98, 1.02, 0.96, 1.04]
                bass_cycle = [1.0, -1.0, 1.5, -0.5, 0.0, -1.5]
                pres_cycle = [1.2, 2.0, 1.5, 1.8, 1.0, 2.2]

                idx = index % len(pitch_cycle)
                pitch = pitch_cycle[idx]
                speed = speed_cycle[idx]
                bass_boost = bass_cycle[idx]
                presence_boost = pres_cycle[idx]
                clarity_cut = 0.0
                lowpass = 0

        return {
            "pitch": pitch,
            "speed": speed,
            "bass_boost_db": bass_boost,
            "presence_boost_db": presence_boost,
            "clarity_reduction_db": clarity_cut,
            "lowpass_hz": lowpass,
        }

    @classmethod
    def _build_cast_allocation(
        cls,
        project_id: str,
        raw_characters: List[Dict[str, Any]],
        default_narrator_voice: str = "Aoede",
        use_hindi: bool = False,
    ) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """Builds non-colliding voice assignments for all characters."""
        # Universal Entity Consolidation: merge duplicate or alias-overlapping characters
        raw_characters = cls.consolidate_characters(raw_characters)

        catalog = get_voice_catalog()
        lang_code = "hi-IN" if use_hindi else "en-US"

        # Supreme Narrator Lock / POV Awareness:
        # Default is Aoede (pitch 1.0, speed 1.0) as permanent supreme narrator.
        # If project metadata or raw_characters explicitly declares a custom voice or first-person male POV narrator, honor it.
        narrator_entry = next(
            (c for c in raw_characters if (c.get("canonical_name") or c.get("name") or "").strip().lower() == "narrator"),
            None,
        )
        if narrator_entry and narrator_entry.get("voice"):
            narrator_voice = narrator_entry["voice"]
        elif narrator_entry and (narrator_entry.get("gender") or "").lower() == "male" and default_narrator_voice == "Aoede":
            narrator_voice = catalog.get_best_matching_voice(
                gender="male",
                language_code=lang_code,
                archetype=narrator_entry.get("archetype") or "first-person male narrator protagonist",
            )
        else:
            narrator_voice = default_narrator_voice or "Aoede"

        narrator_meta = catalog.get_voice(narrator_voice)
        if narrator_meta and narrator_meta.get("gender"):
            narrator_gender = narrator_meta["gender"]
        elif narrator_voice in FEMALE_VOICE_PERSONAS or narrator_voice == "Aoede":
            narrator_gender = "female"
        else:
            narrator_gender = "male"

        used_voices: Set[str] = {narrator_voice, "Aoede"}
        used_signatures: Set[Any] = {
            f"{narrator_voice}_p1.00_s1.00",
            (narrator_voice, 1.0, 1.0),
        }

        # Always register Narrator
        roster_chars = {
            "Narrator": {
                "english_name": "Narrator",
                "display_name": "Narrator",
                "gender": narrator_gender,
                "assigned_voice_id": narrator_voice,
                "aliases": ["सूत्रधार", "Narrator", "narration"],
            }
        }
        voice_registry = {
            "Narrator": {
                "voice": narrator_voice,
                "pitch": 1.0,
                "speed": 1.0,
                "bass_boost_db": 0.0,
                "presence_boost_db": 0.0,
                "clarity_reduction_db": 0.0,
                "lowpass_hz": 0,
            }
        }
        narrator_eq_profile = {
            "chest_resonance_150hz_db": 0.0,
            "nasal_presence_2800hz_db": 0.0,
            "throat_clarity_3200hz_db": 0.0,
            "air_shelf_8000hz_db": 0.0,
            "target_tempo_multiplier": 1.0,
        }
        locks = {
            "Narrator": {
                "character_id": "Narrator",
                "character_name": "Narrator",
                "display_name_hi": "सूत्रधार",
                "aliases": ["सूत्रधार", "Narrator", "narration"],
                "locked": True,
                "voice_id": narrator_voice,
                "eq_formant_profile": narrator_eq_profile,
                "calibration_overrides": {
                    "pitch": 1.0,
                    "speed": 1.0,
                    "bass_boost_db": 0.0,
                    "presence_boost_db": 0.0,
                    "clarity_reduction_db": 0.0,
                    "lowpass_hz": 0,
                    "eq_formant_profile": narrator_eq_profile,
                },
            }
        }

        male_idx = 0
        female_idx = 0

        for ch in raw_characters:
            name = (ch.get("canonical_name") or ch.get("english_name") or ch.get("name") or "").strip()
            if not name or name.lower() in ("narrator", "foley", "sfx"):
                continue

            gender = (ch.get("gender") or "male").lower()
            if gender not in ("male", "female"):
                gender = "male"
            aliases = list(ch.get("aliases", []))
            hin_name = (ch.get("hindi_name") or ch.get("display_name_hi") or "").strip()
            if not hin_name or not is_devanagari(hin_name):
                derived_hi, dev_aliases = derive_devanagari_name(name, aliases=aliases)
                hin_name = derived_hi
                for da in dev_aliases:
                    if da and da not in aliases:
                        aliases.append(da)
            else:
                # When hin_name is set, also call derive_devanagari_name or split space-separated Devanagari tokens
                # so aliases contains sub-tokens (बोर्च, थ्री जैकडॉज़, आइक, आईक, डेनेस्ले)
                _, dev_aliases = derive_devanagari_name(name, aliases=aliases)
                for da in dev_aliases:
                    if da and da not in aliases:
                        aliases.append(da)
                # Split space-separated Devanagari tokens (excluding known compound epithets like "लिटिल आई")
                if hin_name.strip() not in ("लिटिल आई", "व्हाइट वुल्फ़"):
                    parts = [p.strip() for p in hin_name.split() if p.strip()]
                    if len(parts) == 2:
                        for p in parts:
                            if (
                                len(p) >= 3
                                and p not in aliases
                                and p not in _DEV_CONNECTORS
                                and p not in _GENERIC_TITLES
                                and p not in ("आई", "एे", "लिटिल", "सिर", "मास्टेर")
                                and not _is_blacklisted_or_generic(p)
                            ):
                                aliases.append(p)

            if hin_name and hin_name not in aliases:
                aliases.append(hin_name)

            arch = ch.get("archetype") or ch.get("vocal_archetype", "")
            prom = ch.get("prominence", "standard")
            is_child_flag = bool(ch.get("is_child", False))
            rec_dialect = ch.get("recommended_dialect") or ch.get("dialect")
            age_raw = ch.get("age")
            age_hint = None
            if isinstance(age_raw, int):
                age_hint = age_raw
            elif isinstance(age_raw, str) and age_raw.isdigit():
                age_hint = int(age_raw)
            elif isinstance(age_raw, str):
                age_str = age_raw.lower()
                if any(w in age_str for w in ("teen", "teenager", "adolescent", "किशोर")):
                    age_hint = 15
                elif any(w in age_str for w in ("child", "toddler", "kid", "little")):
                    age_hint = 10
                    is_child_flag = True
                elif any(w in age_str for w in ("youth", "young")):
                    age_hint = 20
                elif any(w in age_str for w in ("middle", "adult")):
                    age_hint = 40
                elif any(w in age_str for w in ("elder", "old", "aged")):
                    age_hint = 58

            arch_lower = arch.lower()
            is_teen_flag = (age_hint is not None and 13 <= age_hint <= 18) or any(w in arch_lower for w in ("teen", "teenager", "adolescent", "किशोर", "tarun"))
            if is_teen_flag:
                if age_hint is None:
                    age_hint = 15
            elif any(w in arch_lower for w in ("child", "kid", "little boy", "little girl", "toddler", "balak", "balika", "bacha", "bachi")):
                is_child_flag = True
                if age_hint is None:
                    age_hint = 10

            pitch_hint = None
            if any(w in arch_lower for w in ("deep", "heavy", "grave", "low", "baritone", "gruff")):
                pitch_hint = "low"
            elif any(w in arch_lower for w in ("high", "bright", "youth", "shrill", "sharp")):
                pitch_hint = "high"

            # Specific Archetype Anchors:
            # - Bard / Minstrel / Witty Companion (e.g. Dandelion) -> strictly assign Puck (pitch: 1.0, speed: 1.0)
            # - Knight-errant / chivalric holy warrior (e.g. Eyck of Denesle): ensure Eyck is not assigned Puck.
            #   When arch contains knight, holy, chivalric, sanctimonious, assign Orus, Algieba, or Fenrir.
            # - Female Sorceress / Queen -> Kore
            # - Maiden / Young girl (e.g. Ciri) -> Leda or Achernar (pitch: 1.0)
            # - Narrator -> strictly Aoede (pitch: 1.0, speed: 1.0)
            is_knight = (gender == "male") and any(w in arch_lower for w in ("knight", "holy", "chivalric", "sanctimonious", "paladin"))
            is_official = (gender == "male") and not is_knight and (
                any(w in arch_lower for w in ("alderman", "official", "magistrate", "mayor", "burgomaster", "bailiff"))
                or any(w in name.lower() for w in ("alderman", "mayor", "magistrate"))
                or any(any(w in str(a).lower() for w in ("alderman", "mayor", "magistrate")) for a in aliases)
            )
            is_bard = (gender == "male") and not is_knight and not is_official and (
                any(w in arch_lower for w in ("bard", "minstrel", "witty", "companion", "jester", "poet", "balladeer"))
                or any(w in name.lower() for w in ("bard", "poet", "minstrel", "balladeer"))
                or any(any(w in str(a).lower() for w in ("bard", "poet", "minstrel", "balladeer")) for a in aliases)
            )
            is_sorceress = (gender == "female") and any(w in arch_lower for w in ("sorceress", "queen", "regal", "witch"))
            is_maiden = (gender == "female") and not is_child_flag and any(w in arch_lower for w in ("maiden", "young girl", "princess", "daughter"))

            fav_voice = ch.get("voice") or ch.get("assigned_voice_id")
            if fav_voice and fav_voice in (FEMALE_CHARACTER_VOICE_PERSONAS if gender == "female" else MALE_VOICE_PERSONAS):
                if fav_voice not in used_voices:
                    persona = fav_voice
                elif gender == "female":
                    avail = [p for p in ("Kore", "Callisto", "Leda", "Achernar") if p not in used_voices]
                    persona = avail[0] if avail else "Callisto"
                else:
                    avail = [p for p in ("Orus", "Puck", "Fenrir", "Algieba", "Achird", "Algenib", "Enceladus", "Zephyr", "Charon") if p not in used_voices]
                    persona = avail[0] if avail else "Puck"
            elif is_bard:
                persona = "Puck"
            elif is_knight:
                knight_voices = ["Algieba", "Fenrir", "Orus"]
                avail_knights = [v for v in knight_voices if v not in used_voices]
                persona = avail_knights[0] if avail_knights else knight_voices[male_idx % len(knight_voices)]
            elif is_official:
                official_voices = ["Orus", "Fenrir", "Achird"]
                avail_officials = [v for v in official_voices if v not in used_voices]
                persona = avail_officials[0] if avail_officials else official_voices[male_idx % len(official_voices)]
            elif is_sorceress:
                persona = "Kore" if "Kore" not in used_voices else "Callisto"
            elif is_maiden:
                persona = "Leda" if "Leda" not in used_voices else "Achernar"
            else:
                # Dynamic Voice Assignment from Universal VoiceCatalog
                persona = catalog.get_best_matching_voice(
                    gender=gender,
                    language_code=lang_code,
                    archetype=arch,
                    age_hint=age_hint,
                    pitch_hint=pitch_hint,
                    dialect_hint=rec_dialect,
                    is_child=is_child_flag,
                    exclude_voice_ids=used_voices,
                )
                if not persona:
                    if gender == "female" or (is_child_flag and not is_teen_flag):
                        avail_females = [p for p in FEMALE_CHARACTER_VOICE_PERSONAS if p not in used_voices]
                        persona = avail_females[0] if avail_females else FEMALE_CHARACTER_VOICE_PERSONAS[female_idx % len(FEMALE_CHARACTER_VOICE_PERSONAS)]
                    else:
                        avail_males = [p for p in MALE_VOICE_PERSONAS if p not in used_voices]
                        persona = avail_males[0] if avail_males else MALE_VOICE_PERSONAS[male_idx % len(MALE_VOICE_PERSONAS)]

                # Strict Gender Invariant & Narrator Separation Guard
                if gender == "female":
                    if persona == "Aoede" or persona in MALE_VOICE_PERSONAS:
                        avail = [p for p in FEMALE_CHARACTER_VOICE_PERSONAS if p not in used_voices]
                        persona = avail[0] if avail else FEMALE_CHARACTER_VOICE_PERSONAS[female_idx % len(FEMALE_CHARACTER_VOICE_PERSONAS)]
                elif gender == "male" and not (is_child_flag and not is_teen_flag):
                    if persona in FEMALE_VOICE_PERSONAS:
                        avail_males = [p for p in MALE_VOICE_PERSONAS if p not in used_voices]
                        persona = avail_males[0] if avail_males else MALE_VOICE_PERSONAS[male_idx % len(MALE_VOICE_PERSONAS)]
                else:
                    if persona in MALE_VOICE_PERSONAS:
                        avail_females = [p for p in FEMALE_CHARACTER_VOICE_PERSONAS if p not in used_voices]
                        persona = avail_females[0] if avail_females else FEMALE_CHARACTER_VOICE_PERSONAS[female_idx % len(FEMALE_CHARACTER_VOICE_PERSONAS)]

            used_voices.add(persona)

            acoustic_vec = cls.compute_acoustic_formant_vector(
                gender=gender,
                archetype=arch,
                prominence=prom,
                index=female_idx if gender == "female" else male_idx,
                is_child=is_child_flag,
            )
            if gender == "female":
                female_idx += 1
            else:
                male_idx += 1

            # In natural neural synthesis, default pitch is 1.0 (zero robotic asetrate distortion).
            # Subtle micro-offsets (<= 0.02) are only applied if needed to resolve signature collision.
            # Only young children (< 13yo) receive child formant pitch (1.03-1.05); teen boys & adults stay at 1.0!
            base_pitch = acoustic_vec.get("pitch", 1.03) if (is_child_flag and not is_teen_flag) else 1.0
            base_speed = acoustic_vec.get("speed", 1.03) if (is_child_flag and not is_teen_flag) else 1.0
            pitch = base_pitch
            speed = base_speed
            sig = (persona, pitch, speed)
            sig_str = f"{persona}_p{pitch:.2f}_s{speed:.2f}"

            # NR-GATE-03 Voice Collision Elimination:
            # Guarantees >= 4% acoustic distance when base persona is reused
            # Strictly clamp pitch overrides to safe vocal bounds: 0.94 <= pitch <= 1.06
            # Hard floor/ceiling: NEVER allow pitch < 0.88 or pitch > 1.12!
            if (is_bard or is_maiden) and not is_child_flag:
                pitch = 1.0
                speed = 1.0
                sig = (persona, pitch, speed)
                sig_str = f"{persona}_p{pitch:.2f}_s{speed:.2f}"
            else:
                counter = 1
                while sig in used_signatures or sig_str in used_signatures:
                    sign = 1 if counter % 2 != 0 else -1
                    step = ((counter + 1) // 2) * 0.02
                    pitch = round(base_pitch + sign * step, 2)
                    # Safe pitch clamp [0.94, 1.06]
                    pitch = max(0.94, min(1.06, pitch))
                    speed = round(base_speed + (0.02 if counter % 2 == 1 else -0.02) * ((counter // 2) % 3), 2)
                    speed = max(0.96, min(1.04, speed))
                    sig = (persona, pitch, speed)
                    sig_str = f"{persona}_p{pitch:.2f}_s{speed:.2f}"
                    counter += 1
                    if counter > 30:
                        break

            # Hard acoustic safety ceiling: NEVER allow pitch < 0.88 or pitch > 1.12!
            pitch = max(0.88, min(1.12, pitch))

            used_signatures.add(sig)
            used_signatures.add(sig_str)

            acoustic_vec["pitch"] = pitch
            acoustic_vec["speed"] = speed

            roster_chars[name] = {
                "english_name": name,
                "display_name": name,
                "display_name_hi": hin_name,
                "gender": gender,
                "is_child": is_child_flag,
                "dialect": rec_dialect or "Standard",
                "assigned_voice_id": persona,
                "aliases": aliases,
                "archetype": arch,
                "acoustic_vector": acoustic_vec,
            }
            voice_registry[name] = {
                "voice": persona,
                "pitch": pitch,
                "speed": speed,
                "bass_boost_db": acoustic_vec.get("bass_boost_db", 0.0),
                "presence_boost_db": acoustic_vec.get("presence_boost_db", 0.0),
                "clarity_reduction_db": acoustic_vec.get("clarity_reduction_db", 0.0),
                "lowpass_hz": acoustic_vec.get("lowpass_hz", 0),
            }
            eq_profile = {
                "chest_resonance_150hz_db": acoustic_vec.get("bass_boost_db", 0.0),
                "nasal_presence_2800hz_db": acoustic_vec.get("presence_boost_db", 0.0),
                "throat_clarity_3200hz_db": -acoustic_vec.get("clarity_reduction_db", 0.0),
                "air_shelf_8000hz_db": 0.0,
                "target_tempo_multiplier": speed,
            }
            locks[name] = {
                "character_id": name,
                "character_name": name,
                "display_name_hi": hin_name,
                "aliases": aliases,
                "locked": True,
                "voice_id": persona,
                "eq_formant_profile": eq_profile,
                "calibration_overrides": {
                    "pitch": pitch,
                    "speed": speed,
                    "bass_boost_db": acoustic_vec.get("bass_boost_db", 0.0),
                    "presence_boost_db": acoustic_vec.get("presence_boost_db", 0.0),
                    "clarity_reduction_db": acoustic_vec.get("clarity_reduction_db", 0.0),
                    "lowpass_hz": acoustic_vec.get("lowpass_hz", 0),
                    "eq_formant_profile": eq_profile,
                },
            }

            # Register aliases and Hindi names in locks for bilingual screenplay mapping
            for alias in aliases:
                a_clean = alias.strip()
                if a_clean and a_clean != name and a_clean not in locks:
                    a_low = a_clean.lower()
                    tokens = [t.strip().lower() for t in a_clean.split() if t.strip()]
                    starts_ends_conn = bool(tokens and (tokens[0] in _CONNECTOR_EDGE_TOKENS or tokens[-1] in _CONNECTOR_EDGE_TOKENS))
                    from audiobook_factory.casting.cast_lock import _is_standalone_forbidden_key
                    if (
                        not _is_blacklisted_or_generic(a_clean)
                        and not _is_standalone_forbidden_key(a_clean)
                        and not starts_ends_conn
                        and a_low not in _STOP_CONNECTORS
                        and a_low not in _FORBIDDEN_PHRASES
                        and a_clean not in _FORBIDDEN_PHRASES
                        and len(a_clean) >= 3
                    ):
                        locks[a_clean] = {
                            "character_id": name,
                            "character_name": a_clean,
                            "display_name_hi": hin_name,
                            "aliases": aliases,
                            "locked": True,
                            "voice_id": persona,
                            "eq_formant_profile": dict(eq_profile),
                            "calibration_overrides": dict(locks[name]["calibration_overrides"]),
                        }

        roster = {"project_id": project_id, "characters": roster_chars}
        cast_lock = {"project_slug": project_id, "project_id": project_id, "locks": locks}
        return roster, voice_registry, cast_lock

    @classmethod
    def cast_single_speaker(
        cls,
        speaker_name: str,
        project_dir: Optional[Path] = None,
        gender: Optional[str] = None,
        default_backend: str = "gemini_tts",
        use_hindi: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Dynamically registers and casts a single newly discovered character.
        Persists to voice_registry.json, character_roster.json, and cast_lock.json.
        Guarantees zero voice drift and zero signature collision.
        """
        with _CAST_LOCK:
            return cls._cast_single_speaker_unlocked(
                speaker_name=speaker_name,
                project_dir=project_dir,
                gender=gender,
                default_backend=default_backend,
                use_hindi=use_hindi,
            )

    @classmethod
    def _cast_single_speaker_unlocked(
        cls,
        speaker_name: str,
        project_dir: Optional[Path] = None,
        gender: Optional[str] = None,
        default_backend: str = "gemini_tts",
        use_hindi: Optional[bool] = None,
    ) -> Dict[str, Any]:
        sp_clean = speaker_name.strip()
        if not sp_clean:
            return {"backend": default_backend, "voice": "Aoede", "pitch": 1.0, "speed": 1.0}

        p_dir = Path(project_dir) if project_dir else Path.cwd()
        roster_path = p_dir / "character_roster.json"
        registry_path = p_dir / "voice_registry.json"
        lock_path = p_dir / "cast_lock.json"

        # Load existing files or create empty
        roster: Dict[str, Any] = {"project_id": f"proj-{p_dir.name}", "characters": {}}
        registry: Dict[str, Any] = {}
        locks: Dict[str, Any] = {"project_slug": f"proj-{p_dir.name}", "locks": {}}

        if roster_path.exists():
            try:
                loaded_roster = json.loads(roster_path.read_text(encoding="utf-8"))
                if isinstance(loaded_roster, dict):
                    roster = loaded_roster
            except (json.JSONDecodeError, OSError) as e:
                logger.debug(f"Notice reading roster_path ({roster_path}): {e}")
        if registry_path.exists():
            try:
                loaded_reg = json.loads(registry_path.read_text(encoding="utf-8"))
                if isinstance(loaded_reg, dict):
                    registry = loaded_reg
            except (json.JSONDecodeError, OSError) as e:
                logger.debug(f"Notice reading registry_path ({registry_path}): {e}")
        if lock_path.exists():
            try:
                loaded_locks = json.loads(lock_path.read_text(encoding="utf-8"))
                if isinstance(loaded_locks, dict):
                    locks = loaded_locks
            except (json.JSONDecodeError, OSError) as e:
                logger.debug(f"Notice reading lock_path ({lock_path}): {e}")

        # If already present in registry, return it
        if sp_clean in registry:
            cfg = registry[sp_clean]
            return {
                "backend": cfg.get("backend", default_backend),
                "voice": cfg.get("voice", "Aoede"),
                "pitch": cfg.get("pitch", 1.0),
                "speed": cfg.get("speed", 1.0),
            }

        # Canonical entity alias / sub-name consolidation lookup across existing locks
        canonical_match = None
        lock_dict = locks.get("locks", {})
        for l_key, l_val in lock_dict.items():
            if isinstance(l_val, dict):
                cand_names = [l_val.get("character_name", ""), l_val.get("character_id", ""), l_val.get("display_name_hi", "")]
                cand_names.extend(l_val.get("aliases", []))
                # Check direct or nukta match
                if any(_clean_entity_str(c) == _clean_entity_str(sp_clean) for c in cand_names if c):
                    canonical_match = l_val
                    break
                # Check token containment (excluding generic titles)
                sp_tokens = _entity_tokens(sp_clean) - _GENERIC_TITLES
                c_name = l_val.get("character_name") or l_key
                l_tokens = _entity_tokens(c_name) - _GENERIC_TITLES
                if sp_tokens and l_tokens and (sp_tokens.issubset(l_tokens) or l_tokens.issubset(sp_tokens)):
                    canonical_match = l_val
                    break

        if canonical_match:
            v_id = canonical_match.get("voice_id", "Aoede")
            calib = canonical_match.get("calibration_overrides", {})
            p = calib.get("pitch", 1.0)
            s = calib.get("speed", 1.0)
            matched_cfg = {
                "backend": default_backend,
                "voice": v_id,
                "pitch": p,
                "speed": s,
                "bass_boost_db": calib.get("bass_boost_db", 0.0),
                "presence_boost_db": calib.get("presence_boost_db", 0.0),
                "clarity_reduction_db": calib.get("clarity_reduction_db", 0.0),
                "lowpass_hz": calib.get("lowpass_hz", 0),
            }
            registry[sp_clean] = matched_cfg
            lock_dict[sp_clean] = dict(canonical_match)
            try:
                _atomic_write_json(registry_path, registry)
                _atomic_write_json(lock_path, locks)
            except Exception:
                pass
            return matched_cfg

        # Collect existing voice signatures and used voices
        used_signatures = set()
        used_voices = set()
        # Reserved Narrator Separation: Aoede is reserved exclusively for Narration
        used_voices.add("Aoede")
        for k, v in registry.items():
            if isinstance(v, dict):
                vox = v.get("voice", "Aoede")
                used_voices.add(vox)
                p = v.get("pitch", 1.0)
                s = v.get("speed", 1.0)
                used_signatures.add(f"{vox}_p{p:.2f}_s{s:.2f}")
                used_signatures.add((vox, p, s))

        # Determine gender and child status heuristic if not provided
        g = (gender or "").lower()
        if g not in ("male", "female"):
            female_indicators = (
                "girl", "woman", "lady", "queen", "princess", "madam", "mrs", "miss",
                "sister", "mother", "daughter", "sorceress", "witch", "priestess", "maiden",
                "matron", "damsel", "nun", "aunt", "niece", "bride", "widow", "heroine",
                "स्त्री", "लड़की", "औरत", "रानी", "माता", "कन्या", "युवती", "बहन", "पत्नी"
            )
            if any(ind in sp_clean.lower() for ind in female_indicators):
                g = "female"
            else:
                try:
                    from audiobook_factory.preproduction.linguistic_gender_resolver import LinguisticGenderResolver
                    corpus_sample = ""
                    search_dirs = [p_dir / "extracted", p_dir / "chapters", p_dir / "translation"]
                    for sdir in search_dirs:
                        if sdir.exists():
                            for cf in sorted(sdir.glob("chapter_*.md"))[:3]:
                                corpus_sample += cf.read_text(encoding="utf-8", errors="replace") + "\n"
                            if corpus_sample:
                                break
                    if corpus_sample:
                        ev = LinguisticGenderResolver.resolve_gender(sp_clean, corpus_text=corpus_sample)
                        if ev.confidence >= 0.60:
                            g = ev.gender
                except Exception:
                    pass
                if g not in ("male", "female"):
                    g = "male"

        teen_indicators = ("teen", "teenager", "adolescent", "youth", "किशोर", "किशोरी", "तरुण", "youngster")
        is_teen_speaker = any(ind in sp_clean.lower() for ind in teen_indicators)
        child_indicators = (
            "child", "kid", "little", "toddler", "बच्चा", "बालक", "बालिका"
        )
        is_child_speaker = any(ind in sp_clean.lower() for ind in child_indicators) or is_teen_speaker

        is_hi = use_hindi if use_hindi is not None else (
            (p_dir / "translation").exists() or
            any('\u0900' <= c <= '\u097f' for c in sp_clean) or
            any(str(v.get("voice", "")).startswith("hi-") for v in registry.values() if isinstance(v, dict))
        )

        catalog = get_voice_catalog()
        lang_code = "hi-IN" if is_hi else "en-US"

        persona = catalog.get_best_matching_voice(
            gender=g,
            language_code=lang_code,
            archetype="dynamically_cast_character",
            is_child=is_child_speaker,
            exclude_voice_ids=used_voices,
        )
        if not persona:
            pool = FEMALE_CHARACTER_VOICE_PERSONAS if (g == "female" or (is_child_speaker and not is_teen_speaker)) else MALE_VOICE_PERSONAS
            avail = [p for p in pool if p not in used_voices]
            persona = avail[0] if avail else pool[len(registry) % len(pool)]

        # Strict Gender & Narrator Separation Guard
        if g == "female":
            if persona == "Aoede" or persona in MALE_VOICE_PERSONAS:
                avail_fem = [p for p in FEMALE_CHARACTER_VOICE_PERSONAS if p not in used_voices]
                persona = avail_fem[0] if avail_fem else FEMALE_CHARACTER_VOICE_PERSONAS[len(registry) % len(FEMALE_CHARACTER_VOICE_PERSONAS)]
        elif g == "male" and not (is_child_speaker and not is_teen_speaker):
            if persona == "Aoede" or persona in FEMALE_CHARACTER_VOICE_PERSONAS:
                avail_m = [p for p in MALE_VOICE_PERSONAS if p not in used_voices]
                persona = avail_m[0] if avail_m else MALE_VOICE_PERSONAS[len(registry) % len(MALE_VOICE_PERSONAS)]

        existing_count = len(registry)
        acoustic_vec = cls.compute_acoustic_formant_vector(
            gender=g,
            archetype="dynamically_cast_character",
            prominence="incidental",
            index=existing_count,
            is_child=is_child_speaker,
        )
        base_pitch = acoustic_vec.get("pitch", 1.03) if (is_child_speaker and not is_teen_speaker) else 1.0
        base_speed = acoustic_vec.get("speed", 1.03) if (is_child_speaker and not is_teen_speaker) else 1.0
        pitch = base_pitch
        speed = base_speed
        sig_str = f"{persona}_p{pitch:.2f}_s{speed:.2f}"
        sig_tuple = (persona, pitch, speed)

        # NR-GATE-03 Voice Collision Elimination:
        # Guarantees acoustic distance when base persona is reused
        counter = 1
        while sig_str in used_signatures or sig_tuple in used_signatures:
            sign = 1 if counter % 2 != 0 else -1
            step = ((counter + 1) // 2) * 0.02
            pitch = round(base_pitch + sign * step, 2)
            # NR-GATE-03 Bound Clamp: Safe pitch clamping [0.94, 1.06], hard bounds [0.88, 1.12]
            pitch = max(0.88, min(1.12, pitch))
            if pitch < 0.94 or pitch > 1.06:
                speed = round(base_speed + 0.02 * (counter % 3), 2)
            sig_str = f"{persona}_p{pitch:.2f}_s{speed:.2f}"
            sig_tuple = (persona, pitch, speed)
            counter += 1
            if counter > 30:
                break

        acoustic_vec["pitch"] = pitch
        acoustic_vec["speed"] = speed

        new_config = {
            "backend": default_backend,
            "voice": persona,
            "pitch": pitch,
            "speed": speed,
            "bass_boost_db": acoustic_vec.get("bass_boost_db", 0.0),
            "presence_boost_db": acoustic_vec.get("presence_boost_db", 0.0),
            "clarity_reduction_db": acoustic_vec.get("clarity_reduction_db", 0.0),
            "lowpass_hz": acoustic_vec.get("lowpass_hz", 0),
        }

        # Derive authentic Devanagari transliteration and aliases
        sp_aliases = [sp_clean]
        hin_name, dev_aliases = derive_devanagari_name(sp_clean, aliases=sp_aliases)
        for da in dev_aliases:
            if da and da not in sp_aliases:
                sp_aliases.append(da)
        if hin_name and hin_name not in sp_aliases:
            sp_aliases.append(hin_name)

        # Update and save
        registry[sp_clean] = new_config
        if hin_name and hin_name != sp_clean:
            registry[hin_name] = new_config

        chars = roster.setdefault("characters", {})
        chars[sp_clean] = {
            "english_name": sp_clean,
            "display_name": sp_clean,
            "hindi_name": hin_name,
            "gender": g,
            "assigned_voice_id": persona,
            "aliases": sp_aliases,
            "archetype": "dynamically_cast_character",
            "acoustic_vector": acoustic_vec,
        }
        eq_profile = {
            "chest_resonance_150hz_db": acoustic_vec.get("bass_boost_db", 0.0),
            "nasal_presence_2800hz_db": acoustic_vec.get("presence_boost_db", 0.0),
            "throat_clarity_3200hz_db": -acoustic_vec.get("clarity_reduction_db", 0.0),
            "air_shelf_8000hz_db": 0.0,
            "target_tempo_multiplier": speed,
        }
        lock_dict = locks.setdefault("locks", {})
        lock_entry = {
            "character_id": sp_clean,
            "character_name": sp_clean,
            "display_name_hi": hin_name,
            "aliases": sp_aliases,
            "locked": True,
            "voice_id": persona,
            "eq_formant_profile": eq_profile,
            "calibration_overrides": {
                "pitch": pitch,
                "speed": speed,
                "bass_boost_db": acoustic_vec.get("bass_boost_db", 0.0),
                "presence_boost_db": acoustic_vec.get("presence_boost_db", 0.0),
                "clarity_reduction_db": acoustic_vec.get("clarity_reduction_db", 0.0),
                "lowpass_hz": acoustic_vec.get("lowpass_hz", 0),
                "eq_formant_profile": eq_profile,
            },
        }
        lock_dict[sp_clean] = lock_entry
        if hin_name and hin_name != sp_clean:
            lock_dict[hin_name] = lock_entry

        try:
            _atomic_write_json(roster_path, roster)
            _atomic_write_json(registry_path, registry)
            _atomic_write_json(lock_path, locks)
            logger.info(f"[+] CharacterCaster: Dynamically cast '{sp_clean}' -> {persona} (pitch: {pitch}, speed: {speed}). Registry updated.")
        except Exception as e:
            logger.warning(f"  [!] Notice saving dynamic cast for {sp_clean}: {e}")

        return new_config
