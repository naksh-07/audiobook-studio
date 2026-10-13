#!/usr/bin/env python3
"""
Audiobook Factory - Room 1.5: Glossary Classifier & Alias Unifier.
==================================================================
Classifies candidate entities via ModelGateway using the Tri-Partite Entity Taxonomy:
1. PROPER_NAME: Phonetic Devanagari transliteration (Edward -> एडवर्ड, Corwin -> कॉरविन).
2. HERALDIC_MONIKER: Phonetic Devanagari transliteration (Silver Falcon -> सिल्वर फाल्कन).
   STRICT BAN: Never literally translate heraldic personal monikers (चांदी का बाज़ banned).
3. OCCUPATIONAL_ROLE: Spoken natural Hindustani translation (The Stranger -> अजनबी, The Butcher -> कसाई).
4. ALIAS UNIFICATION: Unify aliases referring to the same person under one canonical record.
"""

from __future__ import annotations
import json
from typing import Dict, Any, List, Optional, Callable, Tuple

from audiobook_factory.logger import logger
from audiobook_factory.glossary.contracts import ChapterEntity, EntityCategory
from audiobook_factory.glossary.scanner import CandidateEntity
from audiobook_factory.glossary.gateway_bridge import execute_glossary_llm


TRI_PARTITE_SYSTEM_PROMPT = (
    "You are an Expert Literary Lexicographer, Voice Casting Director, and Translation Dramaturge for prestige audiobooks.\n"
    "Analyze the provided chapter passage and candidate entities, then classify and transliterate them into Devanagari Hindi.\n\n"
    "CRITICAL TRI-PARTITE ENTITY TAXONOMY:\n"
    "1. PROPER_NAME (Personal Names, Surnames, Given Names):\n"
    "   - Phonetically transliterate into clean Devanagari Hindi (e.g. 'Edward' -> 'एडवर्ड', 'Corwin' -> 'कॉरविन', 'Elena' -> 'एलेना').\n"
    "   - PHONETIC FIDELITY: Pronounce foreign vowels and diphthongs phonetically (e.g. final 'a' is 'आ' or 'या', e.g. 'Elena' -> 'एलेना', 'Freya' -> 'फ्रेया'). "
    "NEVER confuse proper names with single English letter sounds (e.g. NEVER transliterate names as single letters like 'टी और वी') or common English words.\n"
    "   - NEVER substitute foreign fantasy names with Indian village names.\n"
    "2. HERALDIC_MONIKER / COGNOMEN (Heraldic Nicknames, Formal Titles, Epithets used as Names):\n"
    "   - Treat heraldic monikers as PROPER NAMES! Phonetically transliterate into Devanagari.\n"
    "   - GOLD STANDARD: 'Silver Falcon' -> 'सिल्वर फाल्कन', 'Night Raven' -> 'नाइट रेवेन', 'Gold-Tooth' -> 'गोल्ड-टूथ'.\n"
    "   - STRICTLY FORBIDDEN: NEVER translate heraldic personal monikers literally word-for-word into Hindi (STRICTLY BANNED: 'चांदी का बाज़', 'रात का कौवा' as character names)!\n"
    "3. OCCUPATIONAL_ROLE / DESCRIPTIVE EPITHET (Generic situational roles or initial descriptors):\n"
    "   - Translate into natural spoken Hindustani (e.g. 'The Stranger' -> 'अजनबी', 'The Butcher' -> 'कसाई', 'The Alderman' -> 'एल्डरमैन', 'The Innkeeper' -> 'सरायवाला').\n"
    "   - ZERO ENGLISH ARTICLES: English articles ('The', 'A', 'An') do not exist in Hindi and MUST NEVER be transliterated as 'द' or 'ए'. Always strip leading articles completely (e.g. 'The Stranger' -> 'अजनबी', 'The Butcher' -> 'कसाई'). NEVER write 'द कसाई' or 'द अजनबी'!\n"
    "4. MYTHICAL BEASTS & TITULAR ORDERS/CLASSES (e.g. dragon, basilisk, wyvern, chimera, gryphon, warlock, paladin):\n"
    "   - Treat beast species and titular order titles as PROPER NOUNS: phonetically transliterate into Devanagari (e.g. 'dragon' -> 'ड्रैगन', 'basilisk' -> 'बैसिलिस्क', 'warlock' -> 'वॉरलॉक').\n"
    "   - STRICTLY FORBIDDEN: NEVER translate mythical monster species or titular orders into awkward invented compound literal calques (STRICTLY BANNED: compound calques like 'अफ़ई-सरीसृप' or 'जादू-शिकारी').\n"
    "5. ALIAS UNIFICATION & LINKING (CRITICAL FOR AUDIO DRAMA CASTING):\n"
    "   - If a character is introduced by a descriptive role or moniker before revealing their true name (e.g. 'The Stranger' is revealed to be 'Lord Corwin' / 'Silver Falcon'), "
    "explicitly group them under the SAME canonical character record with aliases!\n"
    "   - This prevents the screenplay engine and TTS casting from splitting one character across multiple voice actors."
)


class GlossaryClassifier:
    """
    Classifies raw candidate entities and extracts Devanagari equivalents.
    """

    @classmethod
    def classify_candidates(
        cls,
        candidates: List[CandidateEntity],
        chapter_text: str,
        chapter_num: int = 1,
        known_characters: Optional[List[str]] = None,
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> Tuple[List[ChapterEntity], Dict[str, str], Dict[str, str]]:
        """
        Classifies candidate entities using ModelGateway.
        Returns:
            (discovered_characters, locations_map, terminology_map)
        """
        if not candidates and not chapter_text.strip():
            return [], {}, {}

        # Excerpt context from chapter: first 6000 chars + mid 3000 chars
        excerpt = chapter_text[:6000]
        if len(chapter_text) > 10000:
            mid = len(chapter_text) // 2
            excerpt += "\n\n[...]\n\n" + chapter_text[mid : mid + 3000]

        candidate_names = [c.name for c in candidates]
        known_list = known_characters or []

        prompt = f"""Known Characters so far: {json.dumps(known_list, ensure_ascii=False)}

Candidate Entities Extracted from Chapter {chapter_num}:
{json.dumps(candidate_names, ensure_ascii=False)}

Chapter {chapter_num} Passage Excerpt:
\"\"\"
{excerpt}
\"\"\"

Output JSON strictly matching this schema:
{{
  "characters": [
    {{
      "english_name": "string (canonical English name)",
      "hindi_name": "string (phonetic Devanagari or Hindustani role)",
      "entity_type": "PROPER_NAME" | "HERALDIC_MONIKER" | "OCCUPATIONAL_ROLE",
      "aliases": ["string (alternative monikers, nicknames, and descriptors)"],
      "gender": "male" | "female",
      "voice_style": "string (brief acoustic/acting style description)",
      "hindustani_archetype": "string (e.g. RUGGED_GRIT, ARISTOCRATIC, MILITARY_OFFICER)"
    }}
  ],
  "locations_and_terms": {{
    "English Location or Lore Term": "Devanagari Translation"
  }}
}}
"""

        try:
            if call_llm_fn is not None:
                raw_response = call_llm_fn(prompt=prompt, system_instruction=TRI_PARTITE_SYSTEM_PROMPT, json_mode=True)
            else:
                raw_response = execute_glossary_llm(
                    prompt=prompt,
                    system_instruction=TRI_PARTITE_SYSTEM_PROMPT,
                    task="extraction",
                    temperature=0.10,
                    json_mode=True,
                )
        except Exception as e:
            logger.warning(f"  [!] GlossaryClassifier LLM dispatch warning: {e}")
            raw_response = {}

        data: Any = {}
        if isinstance(raw_response, (dict, list)):
            data = raw_response
        elif isinstance(raw_response, str) and raw_response.strip():
            try:
                data = json.loads(raw_response)
            except Exception:
                import json_repair
                data = json_repair.loads(raw_response) if raw_response else {}

        chars_raw: List[Any] = []
        terms_raw: Dict[str, Any] = {}

        if isinstance(data, list):
            # If LLM returned a list directly
            chars_raw = data
        elif isinstance(data, dict):
            # Handle wrapped keys (e.g. {"data": {...}})
            if "data" in data and isinstance(data["data"], dict):
                data = data["data"]

            chars_raw = data.get("characters", [])
            if not chars_raw:
                for alt_key in ("entities", "candidates", "results"):
                    if isinstance(data.get(alt_key), list):
                        chars_raw = data[alt_key]
                        break

            terms_raw = data.get("locations_and_terms", {})
            if not isinstance(terms_raw, dict):
                terms_raw = {}

        entities: List[ChapterEntity] = []
        locations: Dict[str, str] = {}
        terminology: Dict[str, str] = {}

        # 1. Process characters
        if isinstance(chars_raw, list):
            for c in chars_raw:
                if not isinstance(c, dict):
                    continue
                # Support english_name or name
                raw_eng = c.get("english_name") or c.get("name", "")
                if not raw_eng or not str(raw_eng).strip():
                    continue
                eng = str(raw_eng).strip()
                # Support hindi_name or suggested_devanagari
                raw_hin = c.get("hindi_name") or c.get("suggested_devanagari", "")
                hin = str(raw_hin).strip() if raw_hin else eng
                cat_raw = str(c.get("entity_type") or c.get("category", "PROPER_NAME")).upper()
                valid_cat: EntityCategory = "PROPER_NAME"
                if cat_raw in ("PROPER_NAME", "HERALDIC_MONIKER", "OCCUPATIONAL_ROLE", "LOCATION", "LORE_TERM"):
                    valid_cat = cat_raw  # type: ignore

                aliases = [a.strip() for a in c.get("aliases", []) if isinstance(a, str) and a.strip()]

                gender_raw = str(c.get("gender", "unknown")).lower()
                gender_val = gender_raw if gender_raw in ("male", "female") else "male"

                entities.append(
                    ChapterEntity(
                        canonical_id=eng.lower().replace(" ", "_"),
                        english_name=eng,
                        hindi_name=hin,
                        category=valid_cat,
                        aliases=sorted(list(set(aliases))),
                        gender=gender_val,  # type: ignore
                        voice_style=c.get("voice_style", ""),
                        sociolect_archetype=c.get("hindustani_archetype", "NEUTRAL"),
                        confidence=0.95,
                        first_appearance_chapter=chapter_num,
                        is_canonical=True,
                    )
                )

        # 2. Process locations and terminology
        if isinstance(terms_raw, dict):
            for eng_term, hi_term in terms_raw.items():
                if not isinstance(eng_term, str) or not isinstance(hi_term, str) or not eng_term.strip():
                    continue
                e_clean = eng_term.strip()
                h_clean = hi_term.strip()
                e_lower = e_clean.lower()
                LOCATION_KEYWORDS = (
                    "mountain", "valley", "city", "river", "kingdom", "tavern", "inn", "castle",
                    "tower", "gate", "outpost", "lake", "fort", "sea", "ocean", "forest", "wood",
                    "woods", "isle", "island", "road", "street", "hall", "keep", "pass", "hill",
                    "peak", "bay", "haven", "bridge", "port", "temple", "shrine", "village", "town"
                )
                if any(w in e_lower for w in LOCATION_KEYWORDS):
                    locations[e_clean] = h_clean
                else:
                    terminology[e_clean] = h_clean

        return entities, locations, terminology
