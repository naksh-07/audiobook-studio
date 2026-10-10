"""
Unit tests for Standalone TranslationEngine (Option D)
"""

import unittest
from unittest.mock import MagicMock
from audiobook_factory.translation.contracts import (
    FidelityTier,
    TranslationRequest,
    TranslationResult,
)
from audiobook_factory.translation.engine import TranslationEngine


class TestTranslationEngineStandalone(unittest.TestCase):
    def test_01_translate_single_chunk_mocked(self):
        source = (
            "The iron gates of the citadel creaked open slowly in the morning fog.\n\n"
            "Inside the courtyard, thirty armed guards stood with drawn swords."
        )

        mock_hindi = (
            "किले के भारी लोहे के फाटक सुबह के घने कोहरे में चरमराते हुए धीरे-धीरे खुले।\n\n"
            "भीतर के अहाते में तीस हथियारबंद पहरेदार नंगी तलवारें ताने खड़े थे।"
        )

        mock_llm = MagicMock(return_value=mock_hindi)
        engine = TranslationEngine(llm_fn=mock_llm)

        req = TranslationRequest(
            source_text=source,
            source_title="Opening Scene",
            tier=FidelityTier.RAW_UNRATED,
            thinking_budget=1024,
        )

        result: TranslationResult = engine.translate(req)

        self.assertEqual(result.total_chunks, 1)
        self.assertEqual(result.llm_calls_made, 1)
        self.assertIn("किले के भारी लोहे के फाटक", result.translated_markdown)
        self.assertEqual(len(result.alignments), 2)
        self.assertTrue(result.parity.passed_all_gates)
        self.assertGreaterEqual(result.parity.length_ratio, 0.75)

    def test_02_dynamic_glossary_passed_in_prompt(self):
        source = "Lord Alden approached the high throne."
        mock_hindi = "लॉर्ड एल्डन ऊंचे सिंहासन के करीब पहुंचे।"

        captured_prompt = []

        def capture_llm(prompt, **kwargs):
            captured_prompt.append(prompt)
            return mock_hindi

        engine = TranslationEngine(llm_fn=capture_llm)

        req = TranslationRequest(
            source_text=source,
            dynamic_glossary={"Lord Alden": "लॉर्ड एल्डन", "throne": "सिंहासन"},
        )

        result = engine.translate(req)
        self.assertEqual(len(captured_prompt), 1)
        self.assertIn("Lord Alden", captured_prompt[0])
        self.assertIn("लॉर्ड एल्डन", captured_prompt[0])

    def test_03_classic_reverent_system_instruction(self):
        source = "The holy priest prayed by the river at dusk."
        mock_hindi = "पवित्र पुरोहित ने शाम के धुंधलके में नदी किनारे प्रार्थना की।"

        captured_system = []

        def capture_llm(prompt, system_instruction="", **kwargs):
            captured_system.append(system_instruction)
            return mock_hindi

        engine = TranslationEngine(llm_fn=capture_llm)

        req = TranslationRequest(
            source_text=source,
            tier=FidelityTier.CLASSIC_REVERENT,
        )

        result = engine.translate(req)
        self.assertGreater(len(captured_system), 0)
        self.assertIn("DIGNIFIED HERITAGE & PATHOS", captured_system[0])
        self.assertIn("SACRED REVERENCE", captured_system[0])

    def test_04_preamble_stripping(self):
        source = "Night fell upon the forest."
        mock_raw = "Here is the translation:\n\nरात जंगल पर उतर आई।"

        mock_llm = MagicMock(return_value=mock_raw)
        engine = TranslationEngine(llm_fn=mock_llm)

        req = TranslationRequest(source_text=source)
        result = engine.translate(req)

        self.assertNotIn("Here is the translation", result.translated_markdown)
        self.assertEqual(result.translated_markdown, "रात जंगल पर उतर आई।")


if __name__ == "__main__":
    unittest.main()
