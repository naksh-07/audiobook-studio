"""
Unit tests for DeterministicParityGate (Option D)
"""

import unittest
from audiobook_factory.translation.parity_gate import DeterministicParityGate


class TestDeterministicParityGate(unittest.TestCase):
    def setUp(self):
        self.gate = DeterministicParityGate()

    def test_01_valid_translation_passes(self):
        source = (
            '"Who goes there?" the guard demanded, raising his halberd.\n\n'
            '"Just a traveller seeking shelter from the rain," he replied.'
        )
        target = (
            '"वहाँ कौन है?" पहरेदार ने अपना भाला उठाते हुए कड़क आवाज़ में पूछा।\n\n'
            '"सिर्फ एक मुसाफिर, जो बारिश से बचने के लिए पनाह ढूँढ रहा है," उसने जवाब दिया।'
        )
        metrics = self.gate.verify(source, target)
        self.assertTrue(metrics.passed_all_gates, f"Failed reasons: {metrics.rejection_reasons}")
        self.assertEqual(metrics.source_paragraph_count, 2)
        self.assertEqual(metrics.target_paragraph_count, 2)
        self.assertEqual(len(metrics.rejection_reasons), 0)

    def test_02_severe_truncation_fails(self):
        source = "This is a very long paragraph that goes on and on describing the landscape and history in extensive detail. " * 10
        target = "यह एक छोटा सा वाक्य है।"  # Much shorter (< 75% length)
        metrics = self.gate.verify(source, target)
        self.assertFalse(metrics.passed_all_gates)
        self.assertTrue(any("truncation" in r.lower() for r in metrics.rejection_reasons))

    def test_03_paragraph_disparity_fails(self):
        source = "Para 1.\n\nPara 2.\n\nPara 3.\n\nPara 4.\n\nPara 5.\n\nPara 6.\n\nPara 7.\n\nPara 8."
        target = "Combined all paras into one single block of text."
        metrics = self.gate.verify(source, target)
        self.assertFalse(metrics.passed_all_gates)
        self.assertTrue(any("paragraph count divergence" in r.lower() for r in metrics.rejection_reasons))

    def test_04_dialogue_quote_disparity_fails(self):
        source = '"Line 1," he said. "Line 2," she said. "Line 3," he added. "Line 4," she finished.'
        target = 'उसने पहली बात कही। उसने दूसरी बात कही। उसने तीसरी बात कही। उसने चौथी बात कही।'
        metrics = self.gate.verify(source, target)
        self.assertFalse(metrics.passed_all_gates)
        self.assertTrue(any("dialogue quote parity" in r.lower() for r in metrics.rejection_reasons))

    def test_05_forbidden_calque_fails(self):
        source = "The traveler entered the tavern."
        target = "वह मुसाफिर सराय में दाखिल हुआ।"
        gate = DeterministicParityGate(forbidden_patterns=[r"दाखिल\s+हुआ"])
        metrics = gate.verify(source, target)
        self.assertFalse(metrics.passed_all_gates)
        self.assertTrue(any("forbidden pattern" in r.lower() for r in metrics.rejection_reasons))

    def test_06_conversational_preamble_fails(self):
        source = "The rain poured over the roofs."
        target = "Here is the translation:\n\nबारिश छतों पर बरस रही थी।"
        metrics = self.gate.verify(source, target)
        self.assertFalse(metrics.passed_all_gates)
        self.assertTrue(any("conversational preamble" in r.lower() for r in metrics.rejection_reasons))

    def test_07_single_quote_dialogue_passes(self):
        # British publication style with single quotes and contractions in source
        source = (
            "'He won't escape,' the guard shouted. 'Don't let him pass!'\n\n"
            "'I'm trying,' the captain replied. 'Hold the line!'"
        )
        target = (
            '"वह बच नहीं पाएगा," पहरेदार चिल्लाया। "उसे आगे मत जाने दो!"\n\n'
            '"मैं कोशिश कर रहा हूँ," कप्तान ने जवाब दिया। "कतार बनाए रखो!"'
        )
        metrics = self.gate.verify(source, target)
        self.assertTrue(metrics.passed_all_gates, f"Failed reasons: {metrics.rejection_reasons}")
        self.assertEqual(metrics.source_quote_count, 8)
        self.assertEqual(metrics.target_quote_count, 8)

    def test_08_screenplay_leak_fails(self):
        source = (
            "'Who are you?' he asked.\n\n"
            "'I am a traveller,' she said."
        )
        target = (
            "**गेराल्ट:** तुम कौन हो?\n\n"
            "**अजनबी:** मैं एक मुसाफिर हूँ।"
        )
        metrics = self.gate.verify(source, target)
        self.assertFalse(metrics.passed_all_gates)
        self.assertTrue(any("screenplay speaker tag leakage" in r.lower() for r in metrics.rejection_reasons))


if __name__ == "__main__":
    unittest.main()
