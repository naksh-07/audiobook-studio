"""
Unit tests for Standalone Translation Contracts (Option D)
"""

import unittest
from audiobook_factory.translation.contracts import (
    FidelityTier,
    TranslationRequest,
    TranslationResult,
    ParagraphAlignment,
    ParityMetrics,
)


class TestStandaloneContracts(unittest.TestCase):
    def test_01_request_creation_and_defaults(self):
        req = TranslationRequest(
            source_text="The cold wind blew across the mountain.",
            source_title="Chapter 1",
        )
        self.assertEqual(req.tier, FidelityTier.RAW_UNRATED)
        self.assertEqual(req.thinking_budget, 1024)
        self.assertEqual(req.chunk_size_words, 1800)
        self.assertEqual(req.source_language, "en")
        self.assertEqual(req.target_language, "hi")

    def test_02_paragraph_alignment_model(self):
        align = ParagraphAlignment(
            index=0,
            source_paragraph="He drew his sword.",
            target_paragraph="उसने अपनी तलवार खींची।",
            source_hash="abcd1234efgh5678",
            target_hash="1234abcd5678efgh",
        )
        self.assertEqual(align.index, 0)
        self.assertEqual(align.source_paragraph, "He drew his sword.")

    def test_03_parity_metrics_model(self):
        metrics = ParityMetrics(
            source_paragraph_count=5,
            target_paragraph_count=5,
            paragraph_parity_ratio=1.0,
            source_quote_count=6,
            target_quote_count=6,
            quote_parity_ratio=1.0,
            source_word_count=500,
            target_word_count=480,
            length_ratio=0.96,
            source_negations_count=2,
            target_negations_count=2,
            passed_all_gates=True,
            rejection_reasons=[],
        )
        self.assertTrue(metrics.passed_all_gates)
        self.assertEqual(len(metrics.rejection_reasons), 0)

    def test_04_translation_result_model(self):
        metrics = ParityMetrics(
            source_paragraph_count=1,
            target_paragraph_count=1,
            paragraph_parity_ratio=1.0,
            source_quote_count=0,
            target_quote_count=0,
            quote_parity_ratio=1.0,
            source_word_count=10,
            target_word_count=9,
            length_ratio=0.90,
            source_negations_count=0,
            target_negations_count=0,
            passed_all_gates=True,
        )
        res = TranslationResult(
            translated_markdown="यह एक वाक्य है।",
            alignments=[],
            parity=metrics,
            total_chunks=1,
            llm_calls_made=1,
            elapsed_seconds=1.2,
        )
        self.assertEqual(res.translated_markdown, "यह एक वाक्य है।")
        self.assertEqual(res.total_chunks, 1)


if __name__ == "__main__":
    unittest.main()
