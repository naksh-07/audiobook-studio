"""
Audiobook Factory - Paragraph Alignment Engine
==============================================
Maps source English paragraphs to target Hindi Devanagari paragraphs with
SHA-256 cryptographic provenance for traceability and human QA.
"""

import hashlib
import re
from typing import List
from .contracts import ParagraphAlignment


class ParagraphAlignmentEngine:
    """
    Computes bidirectional paragraph alignments between source English prose
    and target Hindi Devanagari Markdown.
    """

    @staticmethod
    def _hash_text(text: str) -> str:
        """Returns 16-character SHA-256 prefix of normalized text."""
        cleaned = re.sub(r"\s+", " ", text.strip())
        return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _split_paragraphs(text: str) -> List[str]:
        """Splits text into non-empty paragraphs."""
        normalized = text.replace("\r\n", "\n")
        paras = re.split(r"\n\s*\n+", normalized)
        return [p.strip() for p in paras if p.strip()]

    def align(self, source_text: str, target_text: str) -> List[ParagraphAlignment]:
        """
        Aligns source paragraphs with target paragraphs.
        Handles equal counts (1:1) and unequal counts (proportional mapping).
        """
        src_paras = self._split_paragraphs(source_text)
        tgt_paras = self._split_paragraphs(target_text)

        if not src_paras or not tgt_paras:
            return []

        alignments: List[ParagraphAlignment] = []

        # Ideal case: 1:1 paragraph match
        if len(src_paras) == len(tgt_paras):
            for i, (src_p, tgt_p) in enumerate(zip(src_paras, tgt_paras)):
                alignments.append(
                    ParagraphAlignment(
                        index=i,
                        source_paragraph=src_p,
                        target_paragraph=tgt_p,
                        source_hash=self._hash_text(src_p),
                        target_hash=self._hash_text(tgt_p),
                    )
                )
            return alignments

        # Proportional mapping when counts differ
        src_len = len(src_paras)
        tgt_len = len(tgt_paras)

        for i in range(max(src_len, tgt_len)):
            src_idx = min(int(i * (src_len / max(src_len, tgt_len))), src_len - 1)
            tgt_idx = min(int(i * (tgt_len / max(src_len, tgt_len))), tgt_len - 1)

            src_p = src_paras[src_idx]
            tgt_p = tgt_paras[tgt_idx]

            alignments.append(
                ParagraphAlignment(
                    index=len(alignments),
                    source_paragraph=src_p,
                    target_paragraph=tgt_p,
                    source_hash=self._hash_text(src_p),
                    target_hash=self._hash_text(tgt_p),
                )
            )

        return alignments
