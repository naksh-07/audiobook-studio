#!/usr/bin/env python3
"""
Audiobook Factory - Room 2: Multi-Agent Translation Collective Coordinator.
Orchestrates the 4 specialized translation agents into an integrated creative room:
1. LiteraryDraftTranslator: Sense-for-sense dramatic narrative & scene mode translation.
2. HindustaniCadenceSpecialist: Spoken prosody, dialogue breath pauses, and honorific shifts.
3. SubtextAndIdiomDramaturge: Earthy Hindustani metaphors, rustic grit & 19-to-21 amplification.
4. TranslationQualityCritic: Canon consistency audit, anti-omission check & reflection repair.
"""

from __future__ import annotations
import os
import time
from typing import Dict, Any, Optional, Callable, Tuple

from audiobook_factory.logger import logger
from audiobook_factory.model_manager import get_model_manager, TaskType
from .draft_translator import LiteraryDraftTranslator
from .cadence_specialist import HindustaniCadenceSpecialist
from .idiom_dramaturge import SubtextAndIdiomDramaturge
from .translation_critic import TranslationQualityCritic


from audiobook_factory.translation.contracts import FidelityTier, TranslationRequest
from audiobook_factory.translation.engine import TranslationEngine


class MultiAgentTranslationCollective:
    """Coordinates the translation collective across the 100+ key pool using Option D Single-Pass Engine."""

    def __init__(self, model: Optional[str] = None):
        self.model = model
        self.draft_translator = LiteraryDraftTranslator(model=model)
        self.cadence_specialist = HindustaniCadenceSpecialist(model=model)
        self.idiom_dramaturge = SubtextAndIdiomDramaturge(model=model)
        self.quality_critic = TranslationQualityCritic(model=model)

    def _extract_flat_glossary(self, glossary: Dict[str, Any]) -> Dict[str, str]:
        """Extracts flattened English->Hindi entity mappings from any glossary schema."""
        if not glossary or not isinstance(glossary, dict):
            return {}
        extracted: Dict[str, str] = {}
        chars = glossary.get("characters", [])
        if isinstance(chars, list):
            for item in chars:
                if isinstance(item, dict):
                    eng = item.get("english_name")
                    hin = item.get("hindi_name")
                    if eng and hin:
                        extracted[str(eng)] = str(hin)
        terms = glossary.get("locations_and_terms", {})
        if isinstance(terms, dict):
            for k, v in terms.items():
                if isinstance(k, str) and isinstance(v, str):
                    extracted[k] = v
        ignore_keys = {"characters", "relationships", "locations_and_terms", "general_tone", "book_metadata", "book_dna"}
        for k, v in glossary.items():
            if k not in ignore_keys and isinstance(k, str) and isinstance(v, str):
                extracted[k] = v
        return extracted

    def translate_block(
        self,
        text_block: str,
        glossary: Dict[str, Any],
        block_title: str = "",
        preceding_context: str = "",
        adult_mode: bool = True,
        book_dna: Optional[Dict[str, Any]] = None,
        call_llm_fn: Optional[Callable[..., str]] = None,
        use_single_pass: bool = True,
    ) -> str:
        """
        Translates an English text block into publication-grade Hindustani.
        By default uses Option D Single-Pass Engine (1024 thinking budget).
        Pass use_single_pass=False to use legacy 4-agent serial cascade.
        """
        if not use_single_pass:
            return self.translate_block_legacy(
                text_block=text_block,
                glossary=glossary,
                block_title=block_title,
                preceding_context=preceding_context,
                adult_mode=adult_mode,
                book_dna=book_dna,
                call_llm_fn=call_llm_fn,
            )

        t_start = time.time()
        words = len(text_block.split())
        logger.info(f"[*] [Translation Collective] Option D Single-Pass Translation for '{block_title}' ({words} words)...")

        eff_dna = book_dna or (glossary.get("book_dna") if isinstance(glossary, dict) else None)
        tier_str = str((eff_dna or {}).get("source_fidelity_tier", "")).upper()
        if "CLASSIC" in tier_str or "REVERENT" in tier_str or not adult_mode:
            tier = FidelityTier.CLASSIC_REVERENT
        else:
            tier = FidelityTier.RAW_UNRATED

        flat_glossary = self._extract_flat_glossary(glossary)

        # Injected or default LLM callable
        if call_llm_fn:
            eff_llm = call_llm_fn
        else:
            from audiobook_factory.translator import call_gemini
            eff_llm = lambda prompt, system_instruction="", thinking_budget=1024, **kw: call_gemini(
                prompt=prompt,
                system_instruction=system_instruction,
                model=self.model,
                thinking_budget=thinking_budget,
                **kw,
            )

        engine = TranslationEngine(
            llm_fn=eff_llm,
            model_name=self.model or "gemini-2.5-flash",
        )

        request = TranslationRequest(
            source_text=text_block,
            source_title=block_title,
            tier=tier,
            dynamic_glossary=flat_glossary,
            thinking_budget=1024,
            temperature=0.35,
            metadata={
                "preceding_context": preceding_context,
                "adult_mode": adult_mode,
                "book_dna": eff_dna or {},
            },
        )

        result = engine.translate(request)
        candidate_hindi = result.translated_markdown

        # Deterministic Canon Inspection, Register Audit & Sanitization
        final_certified, _ = self.quality_critic.audit_and_certify(
            source_text=text_block,
            hindi_text=candidate_hindi,
            glossary=glossary,
            block_title=block_title,
            call_llm_fn=call_llm_fn,
        )

        total_elapsed = time.time() - t_start
        logger.info(f"[+] [Translation Collective] Certified '{block_title}' in {total_elapsed:.1f}s ({len(final_certified)} chars)")
        return final_certified

    def translate_block_legacy(
        self,
        text_block: str,
        glossary: Dict[str, Any],
        block_title: str = "",
        preceding_context: str = "",
        adult_mode: bool = True,
        book_dna: Optional[Dict[str, Any]] = None,
        call_llm_fn: Optional[Callable[..., str]] = None,
    ) -> str:
        """Legacy 4-Pass Serial Cascade (Draft -> Cadence -> Idiom -> QualityCritic)."""
        t_start = time.time()
        words = len(text_block.split())
        logger.info(f"[*] [Translation Collective - Legacy] Commencing 4-Agent Translation for '{block_title}' ({words} words)...")

        eff_dna = book_dna or (glossary.get("book_dna") if isinstance(glossary, dict) else None)

        # Pass 1: Literary Draft Translator
        logger.info(f"  [Room 2 Pass 1/4] LiteraryDraftTranslator running...")
        pass1_draft: Optional[str] = None
        last_err: Optional[Exception] = None
        for attempt in range(2):
            try:
                pass1_draft = self.draft_translator.translate_draft(
                    text_block=text_block,
                    glossary=glossary,
                    block_title=block_title,
                    preceding_context=preceding_context,
                    adult_mode=adult_mode,
                    book_dna=eff_dna,
                    call_llm_fn=call_llm_fn,
                )
                if pass1_draft and len(pass1_draft.strip()) >= 10:
                    break
            except Exception as e:
                last_err = e
                logger.warning(f"  [!] Pass 1 LiteraryDraftTranslator attempt {attempt + 1}/2 notice: {e}")
                time.sleep(1.0)

        if not pass1_draft or len(pass1_draft.strip()) < 10:
            err_msg = f": {last_err}" if last_err else ""
            raise RuntimeError(f"Pass 1 LiteraryDraftTranslator returned empty translation for {block_title}{err_msg}")

        # Pass 2: Hindustani Cadence Specialist
        logger.info(f"  [Room 2 Pass 2/4] HindustaniCadenceSpecialist running...")
        try:
            pass2_cadence = self.cadence_specialist.refine_cadence(
                source_text=text_block,
                draft_hindi=pass1_draft,
                glossary=glossary,
                block_title=block_title,
                preceding_context=preceding_context,
                call_llm_fn=call_llm_fn,
            )
        except Exception as e:
            logger.warning(f"  [!] Pass 2 HindustaniCadenceSpecialist notice: {e}. Falling back to Pass 1 draft.")
            pass2_cadence = pass1_draft

        # Pass 3: Subtext & Idiom Dramaturge
        logger.info(f"  [Room 2 Pass 3/4] SubtextAndIdiomDramaturge running...")
        try:
            pass3_enriched = self.idiom_dramaturge.enrich_idioms_and_subtext(
                source_text=text_block,
                cadence_hindi=pass2_cadence,
                glossary=glossary,
                block_title=block_title,
                preceding_context=preceding_context,
                book_dna=eff_dna,
                call_llm_fn=call_llm_fn,
            )
        except Exception as e:
            logger.warning(f"  [!] Pass 3 SubtextAndIdiomDramaturge notice: {e}. Falling back to Pass 2 cadence.")
            pass3_enriched = pass2_cadence

        # Pass 4: Translation Quality Critic
        logger.info(f"  [Room 2 Pass 4/4] TranslationQualityCritic auditing...")
        try:
            final_certified, report = self.quality_critic.audit_and_certify(
                source_text=text_block,
                hindi_text=pass3_enriched,
                glossary=glossary,
                block_title=block_title,
                call_llm_fn=call_llm_fn,
            )
        except Exception as e:
            logger.warning(f"  [!] Pass 4 TranslationQualityCritic notice: {e}. Preserving Pass 3 text.")
            final_certified = pass3_enriched

        total_elapsed = time.time() - t_start
        logger.info(f"[+] [Translation Collective - Legacy] Certified '{block_title}' in {total_elapsed:.1f}s ({len(final_certified)} chars)")
        return final_certified


_collective_instance: Optional[MultiAgentTranslationCollective] = None


def get_translation_collective(model: Optional[str] = None) -> MultiAgentTranslationCollective:
    """Returns singleton translation collective instance."""
    global _collective_instance
    if _collective_instance is None or (model and _collective_instance.model != model):
        _collective_instance = MultiAgentTranslationCollective(model=model)
    return _collective_instance
