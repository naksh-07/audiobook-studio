#!/usr/bin/env python3
"""
Unit and integration test verifying that Pre-Production Room 1 agents
route strictly through ModelGateway and KeyLeaseManager without raw urllib requests.
"""

import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from audiobook_factory.core.models.adapters.base import GenerationResult
from audiobook_factory.preproduction.gateway_bridge import execute_preproduction_llm
from audiobook_factory.preproduction.book_dna_agent import BookDNAAgent
from audiobook_factory.preproduction.dramatis_personae_agent import DramatisPersonaeAgent
from audiobook_factory.preproduction.novel_deepsearch import NovelDeepSearchEngine
from audiobook_factory.preproduction.phonetic_lexicon_dramaturge import PhoneticLexiconDramaturge
from audiobook_factory.preproduction.sonic_world_architect import SonicWorldArchitect
from audiobook_factory.preproduction.vocal_acoustic_director import VocalAcousticDirector


class TestPreProductionGatewayIntegration(unittest.TestCase):
    """Verifies Pre-Production Room 1 integration with ModelGateway."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_preprod_gateway_"))
        # Ensure offline mock flag is not set for gateway tests
        if "MOCK_OFFLINE" in os.environ:
            del os.environ["MOCK_OFFLINE"]

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_execute_preproduction_llm_routes_via_model_gateway(self):
        """Verifies execute_preproduction_llm calls ModelGateway.generate_text and parses JSON."""
        mock_gateway = MagicMock()
        mock_gateway.generate_text.return_value = GenerationResult(
            text="```json\n{\n  \"status\": \"success\",\n  \"count\": 42\n}\n```",
            finish_reason="STOP",
            tokens_used=60,
            model_id="gemini-2.5-flash",
            provider="gemini",
        )

        with patch("audiobook_factory.preproduction.gateway_bridge.get_model_gateway", return_value=mock_gateway):
            result = execute_preproduction_llm(
                prompt="Test prompt",
                system_instruction="Test system",
                task="directing",
                json_mode=True,
            )

            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("status"), "success")
            self.assertEqual(result.get("count"), 42)

            mock_gateway.generate_text.assert_called_once()
            call_kwargs = mock_gateway.generate_text.call_args[1]
            self.assertEqual(call_kwargs.get("task"), "directing")
            self.assertTrue(call_kwargs.get("response_json"))

    def test_02_book_dna_agent_routes_through_gateway_by_default(self):
        """Verifies BookDNAAgent calls execute_preproduction_llm when call_llm_fn is None."""
        agent = BookDNAAgent(model="gemini-2.5-pro")
        sample_text = "The dark woods surrounded the tavern. Rain poured down the thatch."
        meta = {"title": "The Woods", "author": "J. Doe"}

        mock_gateway = MagicMock()
        mock_gateway.generate_text.return_value = GenerationResult(
            text=json.dumps({
                "literary_tradition": "DARK_FANTASY_GRIT",
                "source_fidelity_tier": "RAW_UNRATED",
                "regional_dialect_cadence": "Rugged Frontier Hindustani",
                "profanity_policy": "UNRATED_AUTHENTIC",
                "action_intensity": "VISCERAL_COMBAT_GORE",
                "intimacy_intensity": "EARTHY_SENSUAL_REALISM",
                "world_atmosphere_summary": "Gritty, dark medieval world.",
            }),
            finish_reason="STOP",
            tokens_used=120,
            model_id="gemini-2.5-pro",
            provider="gemini",
        )

        with patch("audiobook_factory.preproduction.gateway_bridge.get_model_gateway", return_value=mock_gateway):
            dna = agent.analyze_book_dna(
                novel_text_sample=sample_text,
                book_metadata=meta,
                call_llm_fn=None,  # Default call path
                enable_web_research=False,
            )

            self.assertEqual(dna.get("literary_tradition"), "DARK_FANTASY_GRIT")
            self.assertEqual(dna.get("source_fidelity_tier"), "RAW_UNRATED")
            mock_gateway.generate_text.assert_called_once()

    def test_03_dramatis_personae_agent_routes_through_gateway_by_default(self):
        """Verifies DramatisPersonaeAgent calls execute_preproduction_llm when call_llm_fn is None."""
        agent = DramatisPersonaeAgent(model="gemini-2.5-pro")
        sample_text = '"I am Geralt of Rivia," he said. Baron Valerius nodded.'
        meta = {"title": "The Last Wish", "author": "A. Sapkowski"}

        mock_gateway = MagicMock()
        mock_gateway.generate_text.return_value = GenerationResult(
            text=json.dumps([
                {
                    "english_name": "Geralt",
                    "hindi_name": "गेराल्ट",
                    "gender": "male",
                    "prominence": "lead",
                    "vocal_archetype": "heavy_deep",
                    "sociolect_trait": "RUGGED_GRIT",
                    "recommended_pronoun_level": "tum",
                }
            ]),
            finish_reason="STOP",
            tokens_used=100,
            model_id="gemini-2.5-pro",
            provider="gemini",
        )

        with patch("audiobook_factory.preproduction.gateway_bridge.get_model_gateway", return_value=mock_gateway):
            chars = agent.extract_dramatis_personae(
                novel_text_sample=sample_text,
                book_metadata=meta,
                call_llm_fn=None,  # Default call path
            )

            self.assertEqual(len(chars), 1)
            self.assertEqual(chars[0]["english_name"], "Geralt")
            self.assertEqual(chars[0]["hindi_name"], "गेराल्ट")
            mock_gateway.generate_text.assert_called_once()

    def test_04_vocal_acoustic_director_routes_through_gateway_by_default(self):
        """Verifies VocalAcousticDirector calls execute_preproduction_llm when call_llm_fn is None."""
        director = VocalAcousticDirector(model="gemini-2.5-pro")
        sample_text = "They sat inside the warm stone hall of Kaer Morhen."
        meta = {"title": "Witcher", "author": "A. Sapkowski"}

        mock_gateway = MagicMock()
        mock_gateway.generate_text.return_value = GenerationResult(
            text=json.dumps({
                "spaces": {
                    "great_hall": {
                        "reverb_type": "stone_keep_hall",
                        "wet_mix": 0.22,
                        "decay_time_sec": 1.8,
                        "predelay_ms": 28.0,
                    }
                }
            }),
            finish_reason="STOP",
            tokens_used=95,
            model_id="gemini-2.5-pro",
            provider="gemini",
        )

        with patch("audiobook_factory.preproduction.gateway_bridge.get_model_gateway", return_value=mock_gateway):
            manifest = director.design_vocal_spaces(
                novel_text_sample=sample_text,
                book_metadata=meta,
                call_llm_fn=None,  # Default call path
            )

            self.assertIn("great_hall", manifest.spaces)
            self.assertEqual(manifest.spaces["great_hall"].reverb_type, "stone_keep_hall")
            mock_gateway.generate_text.assert_called_once()


if __name__ == "__main__":
    unittest.main()
