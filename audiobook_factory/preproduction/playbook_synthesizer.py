#!/usr/bin/env python3
"""
Audiobook Factory - Room 1: Production Playbook Synthesizer.
=============================================================
Synthesizes a novel-wide ProductionPlaybook containing tailor-made prompt
directives, custom spoken registers, and narrator vocal demeanors.
Pure standalone module with zero cross-room circular dependencies.
"""

from __future__ import annotations
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path

from audiobook_factory.contracts.playbook import ProductionPlaybook
from audiobook_factory.preproduction.gateway_bridge import execute_preproduction_llm
from audiobook_factory.model_manager import get_model_manager, TaskType
from audiobook_factory.safety import get_dramatic_fiction_framing

logger = logging.getLogger("AudiobookFactory")


class ProductionPlaybookSynthesizer:
    """Standalone Synthesizer for novel-tailored production playbooks."""

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def _resolve_model(self) -> str:
        if self.model:
            return self.model
        return get_model_manager().resolve_active_model(TaskType.EXTRACTION)

    def synthesize_playbook(
        self,
        book_dna: Dict[str, Any],
        book_dossier: Optional[Dict[str, Any]] = None,
        book_metadata: Optional[Dict[str, Any]] = None,
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> ProductionPlaybook:
        """
        Synthesizes the authoritative novel-level ProductionPlaybook.
        Takes verified literary DNA and Dossier in, returns ProductionPlaybook out.
        """
        meta = book_metadata if isinstance(book_metadata, dict) else {}
        dna = book_dna if isinstance(book_dna, dict) else {}
        dossier = book_dossier if isinstance(book_dossier, dict) else {}

        book_title = meta.get("title") or dna.get("book_title") or "Unknown Novel"
        author = meta.get("author") or dna.get("author") or "Unknown Author"
        project_slug = meta.get("project_slug") or "novel"
        project_id = f"proj-{project_slug}"

        lit_dna = dossier.get("literary_dna") if isinstance(dossier.get("literary_dna"), dict) else {}
        ling_dia = dossier.get("linguistic_dialect") if isinstance(dossier.get("linguistic_dialect"), dict) else {}
        world_ac = dossier.get("world_acoustics") if isinstance(dossier.get("world_acoustics"), dict) else {}

        tradition = dna.get("literary_tradition") or lit_dna.get("tradition") or "UNIVERSAL_CONTEMPORARY"
        fidelity_tier = dna.get("source_fidelity_tier") or lit_dna.get("source_fidelity_tier") or "RAW_UNRATED"
        cadence = dna.get("regional_dialect_cadence") or ling_dia.get("recommended_hindustani_register") or "Standard Spoken Hindustani"

        raw_anachronisms = dna.get("banned_anachronisms") or world_ac.get("banned_anachronisms") or []
        if isinstance(raw_anachronisms, list):
            banned_anachronisms = [str(x).strip() for x in raw_anachronisms if x and str(x).strip()]
        elif isinstance(raw_anachronisms, str):
            banned_anachronisms = [x.strip() for x in raw_anachronisms.split(",") if x.strip()]
        else:
            banned_anachronisms = []

        raw_loanwords = dna.get("acceptable_loanwords") or ling_dia.get("acceptable_loanwords") or []
        if isinstance(raw_loanwords, list):
            acceptable_loanwords = [str(x).strip() for x in raw_loanwords if x and str(x).strip()]
        elif isinstance(raw_loanwords, str):
            acceptable_loanwords = [x.strip() for x in raw_loanwords.split(",") if x.strip()]
        else:
            acceptable_loanwords = []

        atmosphere = (
            dna.get("world_atmosphere_summary") or
            lit_dna.get("narrative_tone") or
            "dramatic, atmospheric storytelling"
        )

        model = self.model or ("mock-model" if call_llm_fn else self._resolve_model())

        fiction_framing = get_dramatic_fiction_framing(title=book_title, author=author)
        sys_prompt = (
            fiction_framing +
            "You are an elite Literary Dramaturge, Dialogue Director, and Audio Drama Showrunner.\n"
            "Your task is to synthesize a tailor-made Production Playbook for adapting a novel into "
            "premier full-cast spoken Hindustani audio fiction.\n\n"
            "NON-NEGOTIABLE INVARIANTS:\n"
            "1. NOVEL-AGNOSTIC RIGOR: Derive all directives from the provided literary tradition, setting, and dialect cadence.\n"
            "2. ANTI-ONE-SIZE-FITS-ALL: NEVER apply generic UP/Bihar idioms to European fantasy, gothic horror, or modern noir. "
            "Tailor the register, proverbs, and tone precisely to this world.\n"
            "3. ZERO ENGLISH ARTICLES: Strip 'The', 'A', 'An' before foreign proper names and titles in Devanagari.\n"
            "4. PHONETIC FIDELITY FOR BEASTS & PROPER NAMES: Phonetic transliteration into Devanagari; zero literal calques.\n"
            "5. NARRATOR DEMEANOR: Define a distinct, atmospheric base vocal demeanor for the lead narrator fitting this specific world.\n"
        )

        user_prompt = f"""Synthesize Production Playbook for the following work:
Book Title: {book_title}
Author: {author}
Literary Tradition: {tradition}
Source Fidelity Tier: {fidelity_tier}
Regional Dialect Cadence: {cadence}
World Atmosphere: {atmosphere}
Permitted Loanwords: {', '.join(acceptable_loanwords) if acceptable_loanwords else 'Standard context loanwords'}
Banned Anachronisms: {', '.join(banned_anachronisms) if banned_anachronisms else 'Standard period anachronisms'}

Output JSON format:
{{
  "translation_system_prompt": "Complete, comprehensive multi-paragraph system prompt for Gemini Flash translation actor containing 11 tailored invariants, custom spoken Hindustani register, anti-bowdlerization stance, zero English articles rule, phonetic transliteration rules, and acceptable loanwords policy.",
  "screenplay_system_prompt": "Specific Stanislavski and dialogue delivery guidance matching this authorial style and psychological tone.",
  "narrator_master_demeanor": "Precise vocal demeanor descriptor for the lead narrator (e.g. 'measured, somber, atmospheric chronicler of dark medieval realms' or 'sharp, wry, urban observer').",
  "proverb_style": "How idioms and proverbs should be transposed for this specific setting."
}}
"""
        logger.info(f"  [ProductionPlaybookSynthesizer] Synthesizing tailored playbook for '{book_title}' using {model}...")

        try:
            if call_llm_fn:
                raw = call_llm_fn(prompt=user_prompt, system_instruction=sys_prompt, model=model, json_mode=True)
                if isinstance(raw, str):
                    import re
                    import json_repair
                    clean_raw = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip(), flags=re.IGNORECASE)
                    clean_raw = re.sub(r"\n?```\s*$", "", clean_raw.strip())
                    res = json_repair.loads(clean_raw)
                else:
                    res = raw
            else:
                res = execute_preproduction_llm(
                    prompt=user_prompt,
                    system_instruction=sys_prompt,
                    task="extraction",
                    model=model,
                    json_mode=True,
                    max_output_tokens=4096,
                    thinking_budget=1024,
                )

            if isinstance(res, dict) and res.get("translation_system_prompt"):
                logger.info(f"[+] ProductionPlaybookSynthesizer: Successfully synthesized playbook for '{book_title}'.")
                res_banned = res.get("banned_anachronisms")
                if isinstance(res_banned, list):
                    eff_banned = [str(x).strip() for x in res_banned if x and str(x).strip()]
                else:
                    eff_banned = banned_anachronisms

                res_loans = res.get("acceptable_loanwords")
                if isinstance(res_loans, list):
                    eff_loans = [str(x).strip() for x in res_loans if x and str(x).strip()]
                else:
                    eff_loans = acceptable_loanwords

                return ProductionPlaybook(
                    project_id=project_id,
                    book_title=book_title,
                    author=author,
                    literary_tradition=tradition,
                    source_fidelity_tier=str(fidelity_tier),
                    regional_dialect_cadence=cadence,
                    world_atmosphere_summary=atmosphere,
                    translation_system_prompt=str(res.get("translation_system_prompt") or "").strip(),
                    screenplay_system_prompt=str(res.get("screenplay_system_prompt") or "").strip(),
                    narrator_master_demeanor=str(res.get("narrator_master_demeanor") or "calm, steady, articulate, measured audiobook delivery").strip(),
                    banned_anachronisms=eff_banned,
                    acceptable_loanwords=eff_loans,
                    proverb_style=str(res.get("proverb_style") or "sense-for-sense cultural equivalent").strip(),
                )
        except Exception as e:
            logger.warning(f"  [!] ProductionPlaybookSynthesizer LLM notice: {e}. Falling back to calibrated heuristic synthesis.")

        return self._heuristic_fallback(
            project_id=project_id,
            book_title=book_title,
            author=author,
            tradition=tradition,
            fidelity_tier=str(fidelity_tier),
            cadence=cadence,
            atmosphere=atmosphere,
            banned_anachronisms=banned_anachronisms,
            acceptable_loanwords=acceptable_loanwords,
        )

    def _heuristic_fallback(
        self,
        project_id: str,
        book_title: str,
        author: str,
        tradition: str,
        fidelity_tier: str,
        cadence: str,
        atmosphere: str,
        banned_anachronisms: List[str],
        acceptable_loanwords: List[str],
    ) -> ProductionPlaybook:
        """Deterministic, calibrated fallback generator matching literary genre traditions."""
        trad_lower = tradition.lower()
        is_classic = "classic" in fidelity_tier.lower() or "reverent" in fidelity_tier.lower() or "classic" in trad_lower
        is_fantasy = any(w in trad_lower for w in ("fantasy", "myth", "epic", "medieval", "sword", "witcher"))
        is_gothic = any(w in trad_lower for w in ("gothic", "horror", "victorian", "supernatural"))
        is_noir = any(w in trad_lower for w in ("crime", "noir", "thriller", "detective", "hardboiled"))
        is_rural = any(w in trad_lower for w in ("rural", "village", "peasant", "premchand", "pathos"))

        # 1. Narrator Master Demeanor
        if is_classic:
            if is_rural:
                narrator_demeanor = "dignified, warm, evocative rural storyteller with classical poise and lyrical Hindustani warmth"
            else:
                narrator_demeanor = "dignified, lyrical, reverent literary delivery with classical poise"
        elif is_fantasy:
            narrator_demeanor = "measured, resonant, atmospheric epic narrator with steady authority and dramatic gravity"
        elif is_gothic:
            narrator_demeanor = "somber, eerie, shadowed vocal delivery with delicate suspense and gothic chill"
        elif is_noir:
            narrator_demeanor = "cynical, grounded, sharp urban narrator with dry wit and rhythmic cadence"
        elif is_rural:
            narrator_demeanor = "warm, evocative, deeply empathetic rural storyteller with lyrical Hindustani warmth"
        else:
            narrator_demeanor = "calm, steady, articulate, measured audiobook delivery"


        # 2. Translation System Prompt Construction
        anachronism_note = (
            f"Strictly avoid anachronisms: {', '.join(banned_anachronisms)}."
            if banned_anachronisms else "Strictly avoid modern technological anachronisms."
        )
        loanwords_note = (
            f"Permitted contextual loanwords: {', '.join(acceptable_loanwords)}."
            if acceptable_loanwords else ""
        )

        if is_classic:
            trans_prompt = f"""### CORE DIRECTIVES - DIGNIFIED HERITAGE & PATHOS ({tradition}):
1. SACRED REVERENCE & PATHOS: Honor the emotional gravity, dignified moral depth, and lyrical beauty of classic literature.
2. AUTHENTIC LITERARY CADENCE: Express emotion through rich, poetic Hindustani matching '{cadence}'.
3. ZERO MODERN SLURS / TAPORI VULGARITY: Street profanity and modern casual slang are strictly banned. Render emotional friction through formal verbal sparring and dignified sarcasm.
4. SOCIAL HIERARCHY & HONORIFICS: Preserve traditional social relations and respectful pronouns ('आप', 'हुज़ूर', 'सरकार', 'श्रीमान') with absolute consistency.
5. SENSORY ELEGANCE: Describe beauty, nature, sorrow, and longing with classical grace.
6. CANON ADHERENCE & ZERO CHATTER: Output ONLY complete unabridged Devanagari Markdown. Never summarize, truncate, or chatter.
7. ZERO ENGLISH ARTICLES IN DEVANAGARI: Strip leading English articles ('The', 'A', 'An'); never transliterate 'The' as 'द'.
8. PHONETIC FIDELITY: Transliterate proper names, places, beast species, and titular orders phonetically into Devanagari without awkward compound calques.
9. HISTORICAL COHERENCE: {anachronism_note} {loanwords_note}"""
        else:
            idiom_guidance = (
                f"Transpose idioms into authentic '{cadence}' spoken cadence without parody or out-of-world rural cliches."
                if not is_rural else
                "Transpose idioms into organic rural spoken cadence with authentic desi flavour."
            )
            trans_prompt = f"""### CORE DIRECTIVES - HIGH-FIDELITY LITERARY DIRECTIVES ({tradition}):
1. LITERARY ANTI-BOWDLERIZATION: Never sanitize, dilute, or soften raw violence, tavern profanity, visceral combat gore, or sexual intimacy.
2. 70/30 ANTI-PARODY & WORLD-ANCHOR: 70% Canon Sacredness / 30% Sensory Desi Amplification. Anchor dialogue in the authentic world; avoid comical out-of-place Indian village terms unless setting demands it.
3. AUTHENTIC PROFANITY & DIALOGUE GRIT: Translate coarse insults into earthy, living spoken Hindustani. Polite TV-serial substitutions ('दुष्ट', 'बुरी स्त्री') are strictly banned.
4. THE 19-TO-21 AMPLIFICATION RULE: When source English is mild (19), elevate it to authentic Desi dramatic punch (21).
5. SPOKEN CADENCE & IDIOMS: {idiom_guidance}
6. TU <-> MAAI-BAAP DYNAMIC POWER SHIFT: Arrogant opponents start with 'तू/अबे'; when intimidated, speech collapses into respectful submission ('माई-बाप / सरकार / हुज़ूर').
7. ATMOSPHERIC TEXTURE: Season dialogue and prose with sensory Hindustani and Urdu texture reflecting '{atmosphere}'.
8. SOMATIC INTIMACY & PHYSICALITY: Sensory touch, heat, skin friction, breath. Strictly ban clinical biology terms ('योनि', 'लिंग').
9. VISCERAL COMBAT & GORE: Visceral strikes, blood spray, bone fractures. Use sharp, staccato clauses during fight scenes.
10. ANTI-SANSKRITIZATION: Ban stiff, textbook Sanskrit ('युवतियां' -> 'लड़कियां/औरतें'; 'दर्पण' -> 'आईना'). Use living spoken Hindustani of premium OTT drama and Audible originals.
11. CANON ADHERENCE & ZERO CHATTER: Output ONLY complete unabridged Devanagari Markdown. Never summarize or omit content.
12. ZERO ENGLISH ARTICLES IN DEVANAGARI: English articles ('The', 'A', 'An') do not exist in Hindi and MUST NEVER be transliterated as 'द' or 'ए'. Always strip leading articles completely before proper names, locations, and titles.
13. PHONETIC FIDELITY FOR BEASTS, ORDERS & PROPER NAMES: Transliterate mythical monster/beast species and titular orders phonetically into Devanagari; NEVER invent literal compound calques. Pronounce foreign proper names phonetically.
14. WORLD INTEGRITY: {anachronism_note} {loanwords_note}"""

        screenplay_prompt = (
            f"Direct dialogue for '{book_title}' with deep psychological subtext fitting {tradition}. "
            f"Dialogue rhythm: {cadence}. Emphasize unsaid motivations, status clashes, and raw emotional subtext."
        )

        return ProductionPlaybook(
            project_id=project_id,
            book_title=book_title,
            author=author,
            literary_tradition=tradition,
            source_fidelity_tier=fidelity_tier,
            regional_dialect_cadence=cadence,
            world_atmosphere_summary=atmosphere,
            translation_system_prompt=trans_prompt.strip(),
            screenplay_system_prompt=screenplay_prompt.strip(),
            narrator_master_demeanor=narrator_demeanor,
            banned_anachronisms=banned_anachronisms,
            acceptable_loanwords=acceptable_loanwords,
            proverb_style="context-accurate sense-for-sense",
        )
