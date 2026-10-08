"""
Audiobook Factory - Bilingual Macro Chunker
==========================================
Segments literary chapters into narrative macro-chunks, preserving paragraph
integrity and maintaining sliding bilingual context windows.
"""

import re
from typing import List, Tuple
from pydantic import BaseModel, Field


class MacroChunk(BaseModel):
    """A cohesive macro-scene chunk of text for translation."""
    index: int
    text: str
    word_count: int
    start_paragraph_idx: int
    end_paragraph_idx: int
    preceding_source_context: str = ""
    preceding_target_context: str = ""


class BilingualMacroChunker:
    """
    Intelligent paragraph-preserving chunker:
    - Chapters <= max_single_chunk_words (e.g. 2,200 words) remain in 1 chunk (1 API call).
    - Longer chapters split at double-newline paragraph boundaries near target_chunk_words (e.g. 1,800 words).
    - Preserves trailing context (~150 words) to ensure cross-chunk pronoun and tone continuity.
    """

    def __init__(
        self,
        target_chunk_words: int = 1800,
        max_single_chunk_words: int = 2200,
        context_words: int = 150,
    ):
        self.target_chunk_words = target_chunk_words
        self.max_single_chunk_words = max_single_chunk_words
        self.context_words = context_words

    @staticmethod
    def split_paragraphs(text: str) -> List[str]:
        """Splits raw text into non-empty paragraphs preserving markdown formatting."""
        normalized = text.replace("\r\n", "\n")
        paras = re.split(r"\n\s*\n+", normalized)
        return [p.strip() for p in paras if p.strip()]

    def chunk_text(self, text: str) -> List[MacroChunk]:
        """
        Splits source text into a list of MacroChunk objects with preceding English context.
        """
        if not text or not text.strip():
            return []

        paragraphs = self.split_paragraphs(text)
        if not paragraphs:
            return []

        total_words = sum(len(p.split()) for p in paragraphs)

        # Optimization: Chapters <= max_single_chunk_words are translated in a single request
        if total_words <= self.max_single_chunk_words or len(paragraphs) <= 1:
            full_text = "\n\n".join(paragraphs)
            return [
                MacroChunk(
                    index=0,
                    text=full_text,
                    word_count=total_words,
                    start_paragraph_idx=0,
                    end_paragraph_idx=len(paragraphs) - 1,
                    preceding_source_context="",
                    preceding_target_context="",
                )
            ]

        # Multi-chunk segmentation for long chapters
        chunks: List[MacroChunk] = []
        current_paras: List[str] = []
        current_words = 0
        start_idx = 0

        for i, para in enumerate(paragraphs):
            para_words = len(para.split())

            # If adding this paragraph exceeds target and we already have substantial text
            if current_words + para_words > self.target_chunk_words and current_words >= (self.target_chunk_words // 2):
                chunk_text = "\n\n".join(current_paras)
                preceding_ctx = self._extract_trailing_context(chunks, chunk_text)

                chunks.append(
                    MacroChunk(
                        index=len(chunks),
                        text=chunk_text,
                        word_count=current_words,
                        start_paragraph_idx=start_idx,
                        end_paragraph_idx=i - 1,
                        preceding_source_context=preceding_ctx,
                        preceding_target_context="",
                    )
                )

                current_paras = [para]
                current_words = para_words
                start_idx = i
            else:
                current_paras.append(para)
                current_words += para_words

        # Flush final remaining chunk
        if current_paras:
            chunk_text = "\n\n".join(current_paras)
            preceding_ctx = self._extract_trailing_context(chunks, chunk_text)
            chunks.append(
                MacroChunk(
                    index=len(chunks),
                    text=chunk_text,
                    word_count=current_words,
                    start_paragraph_idx=start_idx,
                    end_paragraph_idx=len(paragraphs) - 1,
                    preceding_source_context=preceding_ctx,
                    preceding_target_context="",
                )
            )

        return chunks

    def _extract_trailing_context(self, previous_chunks: List[MacroChunk], current_chunk_text: str) -> str:
        """Extracts the trailing ~150 words from the immediately preceding chunk."""
        if not previous_chunks:
            return ""
        prev_text = previous_chunks[-1].text
        words = prev_text.split()
        if len(words) <= self.context_words:
            return prev_text
        return " ".join(words[-self.context_words:])
