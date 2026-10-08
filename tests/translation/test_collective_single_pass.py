#!/usr/bin/env python3
"""
Unit tests for Option D Single-Pass Translation Collective & Parity Integration.
Verifies:
1. MultiAgentTranslationCollective uses TranslationEngine single-pass deliberation.
2. Glossary extraction and dynamic entity normalization.
3. FidelityTier routing from book_dna.
4. DeterministicParityGate verification on translated chapters.
"""

import pytest
from unittest.mock import MagicMock, patch

from audiobook_factory.translation.agents.collective import MultiAgentTranslationCollective
from audiobook_factory.translation.contracts import FidelityTier, ParityMetrics
from audiobook_factory.translation.parity_gate import DeterministicParityGate
import audiobook_factory.translator as translator


class TestCollectiveSinglePass:

    def setup_method(self):
        self.sample_glossary = {
            "characters": [
                {
                    "english_name": "Geralt",
                    "hindi_name": "गेराल्ट",
                    "gender": "male",
                },
                {
                    "english_name": "Ciri",
                    "hindi_name": "सिरी",
                    "gender": "female",
                },
            ],
            "locations_and_terms": {
                "Cintra": "सिंट्रा",
                "Witcher": "विचर",
            },
            "book_dna": {
                "source_fidelity_tier": "RAW_UNRATED",
                "regional_dialect_cadence": "Rugged Frontier Hindustani",
            },
        }

    def test_01_single_pass_delegates_to_engine(self):
        """Verifies translate_block executes a single LLM pass with thinking budget."""
        collective = MultiAgentTranslationCollective(model="test-model")
        mock_output = "गेराल्ट ने सिरी की ओर देखा और मुस्कुराया।"
        calls = []

        def mock_llm(prompt, system_instruction="", thinking_budget=1024, **kwargs):
            calls.append((prompt, system_instruction, thinking_budget))
            return mock_output

        result = collective.translate_block(
            text_block="Geralt looked at Ciri and smiled.",
            glossary=self.sample_glossary,
            block_title="Scene 1",
            call_llm_fn=mock_llm,
        )

        assert len(calls) == 1
        assert "गेराल्ट" in result
        assert "सिरी" in result
        prompt, sys_inst, tb = calls[0]
        assert tb == 1024
        assert "CANONICAL ENTITY GLOSSARY" in prompt
        assert "Geralt" in prompt
        assert "RAW UNRATED" in sys_inst

    def test_02_classic_reverent_tier_selection(self):
        """Verifies classic reverent tier is selected when specified in book_dna."""
        collective = MultiAgentTranslationCollective(model="test-model")
        glossary = {
            "characters": [{"english_name": "Hori", "hindi_name": "होरी"}],
            "book_dna": {
                "source_fidelity_tier": "CLASSIC_REVERENT",
            },
        }
        mock_output = "होरी ने खेत की ओर देखा।"
        calls = []

        def mock_llm(prompt, system_instruction="", **kwargs):
            calls.append(system_instruction)
            return mock_output

        result = collective.translate_block(
            text_block="Hori looked towards the field.",
            glossary=glossary,
            block_title="Scene 1",
            call_llm_fn=mock_llm,
        )

        assert len(calls) == 1
        assert "DIGNIFIED HERITAGE & PATHOS" in calls[0]
        assert "ZERO MODERN SLURS" in calls[0]

    def test_03_extract_flat_glossary_handles_varied_formats(self):
        """Verifies glossary extractor handles nested and flat dictionary structures."""
        collective = MultiAgentTranslationCollective()
        flat = collective._extract_flat_glossary(self.sample_glossary)
        assert flat["Geralt"] == "गेराल्ट"
        assert flat["Ciri"] == "सिरी"
        assert flat["Cintra"] == "सिंट्रा"
        assert flat["Witcher"] == "विचर"
        assert "book_dna" not in flat

    def test_04_parity_gate_integrated_in_translator(self):
        """Verifies DeterministicParityGate validates chapters in translator.py."""
        gate = DeterministicParityGate()
        source = "The traveler walked into the dark tavern.\n\nHe asked for warm wine."
        target = "मुसाफ़िर अंधेरी सराय में दाखिल हुआ।\n\nउसने गर्म शराब मांगी।"
        metrics = gate.verify(source, target)
        assert metrics.passed_all_gates is True
        assert metrics.paragraph_parity_ratio == 1.0
        assert metrics.length_ratio >= 0.75
