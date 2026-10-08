"""
Audiobook Factory - Deterministic Parity Gate
=============================================
Zero-token full-text verification in pure Python:
- Paragraph count parity (+/- 15%)
- Dialogue quote parity (+/- 10%)
- Text length ratio (>= 75%)
- Negation polarity parity
- Anti-tamper & cleanliness checks
"""

import re
from typing import List, Set, Tuple
from .contracts import ParityMetrics


# English and Hindi negation marker lexicons
ENGLISH_NEGATIONS = {
    "no", "not", "never", "neither", "nor", "none",
    "nothing", "nowhere", "hardly", "scarcely", "barely", "cannot", "can't",
    "won't", "don't", "didn't", "isn't", "aren't", "wasn't", "weren't",
}

HINDI_SINGLE_NEGATIONS = {
    "नहीं", "मत", "ना", "न", "बिना", "बग़ैर", "इनकार", "नाकाम", "मना",
}

HINDI_COMPOUND_NEGATION_PATTERNS = [
    r"कभी\s+नहीं",
    r"कुछ\s+नहीं",
    r"कोई\s+नहीं",
]

PREAMBLE_PATTERNS = [
    r"^here\s+is\s+(the\s+)?translation",
    r"^sure,\s+here\s+is",
    r"^certainly,",
    r"^below\s+is\s+(the\s+)?translation",
]


class DeterministicParityGate:
    """
    Evaluates 100% of the chapter text without incurring LLM token costs or API latency.
    Guarantees structural parity and semantic continuity between English and Hindi.
    """

    def __init__(
        self,
        paragraph_tolerance: float = 0.15,
        quote_tolerance: float = 0.10,
        min_length_ratio: float = 0.75,
        negation_tolerance: float = 0.50,
        forbidden_patterns: Optional[List[str]] = None,
    ):
        self.paragraph_tolerance = paragraph_tolerance
        self.quote_tolerance = quote_tolerance
        self.min_length_ratio = min_length_ratio
        self.negation_tolerance = negation_tolerance
        self.forbidden_patterns = forbidden_patterns or []

    @staticmethod
    def _count_paragraphs(text: str) -> int:
        paras = [p.strip() for p in re.split(r"\n\s*\n+", text.replace("\r\n", "\n")) if p.strip()]
        return max(1, len(paras))

    @staticmethod
    def _count_dialogue_quotes(text: str) -> int:
        # Count paired quotation marks across common Unicode types
        double_quotes = text.count('"') + text.count('“') + text.count('”')
        return double_quotes

    @staticmethod
    def _count_negations_english(text: str) -> int:
        tokens = re.findall(r"\b[a-zA-Z']+\b", text.lower())
        return sum(1 for t in tokens if t in ENGLISH_NEGATIONS)

    @staticmethod
    def _count_negations_hindi(text: str) -> int:
        count = 0
        cleaned = text
        for pat in HINDI_COMPOUND_NEGATION_PATTERNS:
            matches = re.findall(pat, cleaned)
            count += len(matches)
            cleaned = re.sub(pat, " ", cleaned)
        tokens = re.findall(r"[\u0900-\u097F]+", cleaned)
        count += sum(1 for t in tokens if t in HINDI_SINGLE_NEGATIONS)
        return count

    def verify(
        self,
        source_text: str,
        target_text: str,
        forbidden_patterns: Optional[List[str]] = None,
    ) -> ParityMetrics:
        """
        Runs comprehensive deterministic checks across the full source and target texts.
        """
        rejection_reasons: List[str] = []

        # 1. Paragraph Count Parity
        src_paras = self._count_paragraphs(source_text)
        tgt_paras = self._count_paragraphs(target_text)
        para_ratio = round(tgt_paras / src_paras, 3)

        # Allow +/- tolerance; for very short passages (<= 2 paragraphs), permit delta <= 1
        if abs(para_ratio - 1.0) > self.paragraph_tolerance:
            if src_paras > 2 or abs(tgt_paras - src_paras) > 1:
                rejection_reasons.append(
                    f"Paragraph count divergence: source has {src_paras}, target has {tgt_paras} (ratio {para_ratio:.2f}, limit +/- {self.paragraph_tolerance:.2f})"
                )

        # 2. Dialogue Quote Parity
        src_quotes = self._count_dialogue_quotes(source_text)
        tgt_quotes = self._count_dialogue_quotes(target_text)
        if src_quotes >= 4:
            quote_ratio = round(tgt_quotes / src_quotes, 3)
            if abs(quote_ratio - 1.0) > self.quote_tolerance and abs(tgt_quotes - src_quotes) > 2:
                rejection_reasons.append(
                    f"Dialogue quote parity divergence: source has {src_quotes} quotes, target has {tgt_quotes} (ratio {quote_ratio:.2f}, limit +/- {self.quote_tolerance:.2f})"
                )
        else:
            quote_ratio = 1.0

        # 3. Text Length Ratio Gate
        src_words = max(1, len(source_text.split()))
        tgt_words = max(1, len(target_text.split()))
        length_ratio = round(tgt_words / src_words, 3)

        if length_ratio < self.min_length_ratio:
            rejection_reasons.append(
                f"Severe text truncation detected: target length ratio {length_ratio:.2f} is below minimum threshold {self.min_length_ratio:.2f} (source: {src_words} words, target: {tgt_words} words)"
            )

        # 4. Negation Parity Check
        src_negs = self._count_negations_english(source_text)
        tgt_negs = self._count_negations_hindi(target_text)
        if src_negs >= 5:
            neg_ratio = tgt_negs / src_negs
            if abs(neg_ratio - 1.0) > self.negation_tolerance:
                rejection_reasons.append(
                    f"Action/negation disparity: source has {src_negs} negative markers, target has {tgt_negs} (ratio {neg_ratio:.2f})"
                )

        # 5. Anti-Tamper & Cleanliness Checks
        check_patterns = forbidden_patterns or self.forbidden_patterns
        for pat in check_patterns:
            if re.search(pat, target_text):
                rejection_reasons.append(f"Forbidden pattern detected in translation: '{pat}'")

        first_line = target_text.strip().split("\n")[0].lower() if target_text.strip() else ""
        for pat in PREAMBLE_PATTERNS:
            if re.search(pat, first_line):
                rejection_reasons.append(f"Conversational preamble detected at start of translation: '{first_line[:50]}...'")

        passed = len(rejection_reasons) == 0

        return ParityMetrics(
            source_paragraph_count=src_paras,
            target_paragraph_count=tgt_paras,
            paragraph_parity_ratio=para_ratio,
            source_quote_count=src_quotes,
            target_quote_count=tgt_quotes,
            quote_parity_ratio=quote_ratio,
            source_word_count=src_words,
            target_word_count=tgt_words,
            length_ratio=length_ratio,
            source_negations_count=src_negs,
            target_negations_count=tgt_negs,
            passed_all_gates=passed,
            rejection_reasons=rejection_reasons,
        )
