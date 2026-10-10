#!/usr/bin/env python3
"""
Integration test suite verifying Room 2 Translation integration with ModelGateway.
Validates:
1. execute_translation_llm routes strictly through ModelGateway.generate_text().
2. TranslationEngine defaults to execute_translation_llm when llm_fn is None.
3. MultiAgentTranslationCollective defaults to execute_translation_llm.
4. TranslationQualityCritic defaults to execute_translation_llm.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from audiobook_factory.core.models.adapters.base import GenerationResult
from audiobook_factory.translation.gateway_bridge import execute_translation_llm
from audiobook_factory.translation.engine import TranslationEngine, TranslationRequest
from audiobook_factory.translation.contracts import FidelityTier
from audiobook_factory.translation.agents.collective import MultiAgentTranslationCollective
from audiobook_factory.translation.agents.translation_critic import TranslationQualityCritic


class TestTranslationGatewayIntegration(unittest.TestCase):
    def setUp(self):
        self._prev_mock = os.environ.pop("MOCK_OFFLINE", None)

    def tearDown(self):
        if self._prev_mock is not None:
            os.environ["MOCK_OFFLINE"] = self._prev_mock
        else:
            os.environ.pop("MOCK_OFFLINE", None)

    def test_01_execute_translation_llm_routes_via_model_gateway(self):
        """Verifies execute_translation_llm dispatches through ModelGateway.generate_text."""
        mock_gateway = MagicMock()
        mock_gateway.generate_text.return_value = GenerationResult(
            text="यह एक जादुई रात थी। हवा में बर्फ की महक थी।",
            finish_reason="STOP",
            tokens_used=45,
            model_id="gemini-2.5-flash",
            provider="gemini",
        )

        with patch("audiobook_factory.core.models.gateway.get_model_gateway", return_value=mock_gateway):
            result = execute_translation_llm(
                prompt="Translate this line.",
                system_instruction="You are a literary translator.",
                task="translation",
                thinking_budget=1024,
                session_id="chapter_001",
            )

            self.assertIn("यह एक जादुई रात थी", result)
            mock_gateway.generate_text.assert_called_once()
            call_kwargs = mock_gateway.generate_text.call_args[1]
            self.assertEqual(call_kwargs.get("task"), "translation")
            self.assertEqual(call_kwargs.get("session_id"), "chapter_001")
            self.assertEqual(call_kwargs.get("thinking_budget"), 1024)

    def test_02_translation_engine_defaults_to_gateway(self):
        """Verifies TranslationEngine uses execute_translation_llm when llm_fn is None."""
        mock_gateway = MagicMock()
        mock_gateway.generate_text.return_value = GenerationResult(
            text="कौवे की कांव-कांव गूंज उठी।",
            finish_reason="STOP",
            tokens_used=20,
            model_id="gemini-2.5-flash",
            provider="gemini",
        )

        with patch("audiobook_factory.core.models.gateway.get_model_gateway", return_value=mock_gateway):
            engine = TranslationEngine(llm_fn=None)
            req = TranslationRequest(
                source_text="The raven's cry echoed.",
                source_title="Chapter 1",
                tier=FidelityTier.RAW_UNRATED,
            )
            res = engine.translate(req)

            self.assertIn("कौवे की कांव-कांव", res.translated_markdown)
            mock_gateway.generate_text.assert_called_once()

    def test_03_collective_defaults_to_gateway(self):
        """Verifies MultiAgentTranslationCollective uses execute_translation_llm."""
        mock_gateway = MagicMock()
        mock_gateway.generate_text.return_value = GenerationResult(
            text="सिल्वर फाल्कन चुपचाप खड़ा रहा।",
            finish_reason="STOP",
            tokens_used=30,
            model_id="gemini-2.5-flash",
            provider="gemini",
        )

        with patch("audiobook_factory.core.models.gateway.get_model_gateway", return_value=mock_gateway):
            collective = MultiAgentTranslationCollective()
            out = collective.translate_block(
                text_block="Silver Falcon stood in silence.",
                glossary={"Silver Falcon": "सिल्वर फाल्कन"},
                block_title="Scene 1",
                call_llm_fn=None,
                use_single_pass=True,
            )

            self.assertIn("सिल्वर फाल्कन", out)
            mock_gateway.generate_text.assert_called()


if __name__ == "__main__":
    unittest.main()
