"""
Audiobook Factory - Standalone Translation Engine
================================================
Independent, decoupled literary translation engine (Option D Architecture).
Supports macro-chunking, single-pass Gemini Flash execution with internal deliberation,
and full-text deterministic parity verification.
"""

import os
import re
import time
import json
from typing import Any, Callable, Dict, List, Optional

from .contracts import (
    FidelityTier,
    ParagraphAlignment,
    ParityMetrics,
    TranslationRequest,
    TranslationResult,
)
from .chunker import BilingualMacroChunker, MacroChunk
from .prompt_builder import DynamicPromptBuilder
from .alignment import ParagraphAlignmentEngine
from .parity_gate import DeterministicParityGate


class TranslationEngine:
    """
    Decoupled text-to-text literary translation engine:
    - Zero imports of audio, tts, screenplay, or sound effects modules.
    - Full dependency injection for LLM callables.
    - Cohesive macro-chunking (1-2 calls per chapter).
    - Single-pass high-fidelity generation with thinking budget.
    - Full-text deterministic parity gate verification.
    """

    def __init__(
        self,
        llm_fn: Optional[Callable[..., str]] = None,
        model_name: Optional[str] = None,
    ):
        if llm_fn is not None:
            self.llm_fn = llm_fn
        else:
            try:
                from .gateway_bridge import execute_translation_llm
                self.llm_fn = execute_translation_llm
            except Exception:
                self.llm_fn = None
        from .contracts import DEFAULT_TRANSLATION_MODEL
        self.model_name = model_name or DEFAULT_TRANSLATION_MODEL
        self.chunker = BilingualMacroChunker()
        self.alignment_engine = ParagraphAlignmentEngine()
        self.parity_gate = DeterministicParityGate()

    def translate(self, request: TranslationRequest) -> TranslationResult:
        """
        Executes end-to-end literary translation on the provided request.
        """
        start_time = time.time()
        source_text = request.source_text.strip()
        if not source_text:
            empty_parity = ParityMetrics(
                source_paragraph_count=0,
                target_paragraph_count=0,
                paragraph_parity_ratio=1.0,
                source_quote_count=0,
                target_quote_count=0,
                quote_parity_ratio=1.0,
                source_word_count=0,
                target_word_count=0,
                length_ratio=0.0,
                source_negations_count=0,
                target_negations_count=0,
                passed_all_gates=False,
                rejection_reasons=["Empty source text"],
            )
            return TranslationResult(
                translated_markdown="",
                alignments=[],
                parity=empty_parity,
                total_chunks=0,
                llm_calls_made=0,
                elapsed_seconds=0.0,
            )

        # 1. Macro-Chunking
        self.chunker.target_chunk_words = request.chunk_size_words
        self.chunker.max_single_chunk_words = request.max_single_chunk_words
        chunks: List[MacroChunk] = self.chunker.chunk_text(source_text)
        total_chunks = len(chunks)

        translated_parts: List[str] = []
        llm_calls_made = 0

        # 2. Sequential Macro-Chunk Translation with Sliding Context
        for i, chunk in enumerate(chunks):
            # Pass trailing Hindi context from previous chunk if available
            if translated_parts:
                prev_text = translated_parts[-1]
                prev_words = prev_text.split()
                chunk.preceding_target_context = (
                    " ".join(prev_words[-150:]) if len(prev_words) > 150 else prev_text
                )

            system_instruction = DynamicPromptBuilder.build_system_instruction(
                request.tier,
                playbook=request.playbook,
            )
            user_prompt = DynamicPromptBuilder.build_user_prompt(
                chunk,
                request,
                total_chunks=total_chunks,
                director_card=request.director_card,
            )


            chunk_output = self._call_llm(
                user_prompt=user_prompt,
                system_instruction=system_instruction,
                thinking_budget=request.thinking_budget,
                temperature=request.temperature,
            )
            llm_calls_made += 1

            clean_chunk = self._sanitize_output(chunk_output)
            translated_parts.append(clean_chunk)

        # 3. Assemble complete translated Markdown
        final_markdown = "\n\n".join(translated_parts).strip()

        # 4. Paragraph Alignment Provenance
        alignments = self.alignment_engine.align(source_text, final_markdown)

        # 5. Deterministic Full-Text Parity Gate
        parity = self.parity_gate.verify(source_text, final_markdown)

        elapsed = round(time.time() - start_time, 2)

        return TranslationResult(
            translated_markdown=final_markdown,
            alignments=alignments,
            parity=parity,
            new_entities_discovered={},
            total_chunks=total_chunks,
            llm_calls_made=llm_calls_made,
            elapsed_seconds=elapsed,
        )

    def _call_llm(
        self,
        user_prompt: str,
        system_instruction: str,
        thinking_budget: int = 1024,
        temperature: float = 0.35,
    ) -> str:
        """Executes LLM call via injected callable or fallback direct HTTP runner."""
        if self.llm_fn:
            # Flexible callable signature adaptation (positional vs keyword, kwargs support)
            try:
                return self.llm_fn(
                    user_prompt,
                    system_instruction=system_instruction,
                    thinking_budget=thinking_budget,
                    temperature=temperature,
                )
            except TypeError:
                pass
            try:
                return self.llm_fn(
                    prompt=user_prompt,
                    system_instruction=system_instruction,
                    thinking_budget=thinking_budget,
                    temperature=temperature,
                )
            except TypeError:
                pass
            try:
                return self.llm_fn(
                    user_prompt,
                    system_instruction=system_instruction,
                )
            except TypeError:
                pass
            try:
                return self.llm_fn(
                    prompt=user_prompt,
                    system_instruction=system_instruction,
                )
            except TypeError:
                pass
            try:
                return self.llm_fn(user_prompt)
            except TypeError:
                return self.llm_fn(prompt=user_prompt)

        # Fail closed: No unmetered direct HTTP calls allowed
        raise RuntimeError(
            "No LLM callable configured for TranslationEngine and direct unmetered HTTP calls are forbidden. "
            "Please provide an LLM callable or configure ModelGateway."
        )

    @staticmethod
    def _sanitize_output(text: str) -> str:
        """Strips markdown fences, preambles, and conversational artifacts robustly."""
        cleaned = text.strip()
        # Robustly strip opening and closing fences (even if output is truncated)
        cleaned = re.sub(r"^```(?:markdown|json|md|text)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)

        # Strip common AI preambles
        cleaned = re.sub(
            r"^(?:Here is the translation:?|Certainly,? here is the translation:?|Below is the translated text:?)\s*\n+",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        return cleaned.strip()
