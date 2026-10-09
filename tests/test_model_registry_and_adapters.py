#!/usr/bin/env python3
"""
Comprehensive Test Suite for Phase 3: Model Registry & Polymorphic Adapters.
============================================================================
Validates:
1. Canonical Model Registry lookups, filtering, and dynamic resolution.
2. Flagship tier floors for creative tasks (Translation, Screenplay -> Tier 1).
3. Audio tier assignment for TTS tasks (gemini-3.8-flash-tts).
4. Critical Gemini 3.8 Thinking Token fix:
   - thinkingBudget = 0 on utility/ping tasks.
   - thinkingBudget = 1024 on creative text tasks.
5. Fiction safety framing with BLOCK_NONE thresholds.
6. Gemini Flash TTS inlineData base64 decoding.
7. OpenAI-Compatible Adapter payload construction and response parsing.
8. Local GPU Adapter VRAM guard mutex protection.
"""

import sys
import os
import json
import base64
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from audiobook_factory.core.models.registry import (
    ModelRegistry,
    ModelTier,
    Modality,
    TaskCategory,
    ModelCapability,
    get_model_registry,
    CANONICAL_MODELS,
)
from audiobook_factory.core.models.adapters import (
    GeminiProviderAdapter,
    OpenAICompatibleAdapter,
    LocalGpuAdapter,
    HardwareVRAMGuard,
    GenerationResult,
    SpeechResult,
    ApiHttpError,
)


class TestModelRegistryAndAdapters(unittest.TestCase):

    def setUp(self):
        self.registry = get_model_registry()
        self.gemini_adapter = GeminiProviderAdapter()
        self.openai_adapter = OpenAICompatibleAdapter(provider="cerebras")
        self.local_adapter = LocalGpuAdapter()

    # =========================================================================
    # 1. Model Registry Lookups & Capabilities
    # =========================================================================
    def test_01_canonical_models_registered(self):
        """Verifies primary production models are registered with correct specs."""
        m_38 = self.registry.get_model("gemini-3.8-flash")
        self.assertIsNotNone(m_38)
        self.assertEqual(m_38.tier, ModelTier.TIER_1_FLAGSHIP)
        self.assertEqual(m_38.context_window, 1_048_576)
        self.assertTrue(m_38.supports_thinking)
        self.assertIn("translation", m_38.recommended_tasks)

        m_tts = self.registry.get_model("gemini-3.8-flash-tts")
        self.assertIsNotNone(m_tts)
        self.assertEqual(m_tts.tier, ModelTier.TIER_AUDIO)
        self.assertEqual(m_tts.free_rpd, 10)  # Hard 10 RPD daily quota ceiling
        self.assertIn(Modality.AUDIO, m_tts.modalities)

    def test_02_registry_filtering(self):
        """Verifies filtering by provider, task, and tier."""
        cerebras_models = self.registry.list_models(provider="cerebras")
        self.assertGreaterEqual(len(cerebras_models), 2)
        model_ids = [m.model_id for m in cerebras_models]
        self.assertIn("llama3.3-70b", model_ids)

        audio_models = self.registry.filter_models(modality=Modality.AUDIO)
        audio_ids = [m.model_id for m in audio_models]
        self.assertIn("gemini-3.8-flash-tts", audio_ids)

    def test_03_dynamic_model_resolution(self):
        """
        Critical Architectural Invariant:
        Translation & Screenplay must resolve to Tier 1 Flagship.
        TTS must resolve to Audio Tier.
        """
        best_trans = self.registry.resolve_best_model(task="translation")
        self.assertEqual(best_trans.tier, ModelTier.TIER_1_FLAGSHIP)
        self.assertEqual(best_trans.model_id, "gemini-3.8-flash")

        best_tts = self.registry.resolve_best_model(task="tts")
        self.assertEqual(best_tts.tier, ModelTier.TIER_AUDIO)
        self.assertEqual(best_tts.model_id, "gemini-3.8-flash-tts")

    # =========================================================================
    # 2. Gemini 3.8 Thinking Token Configuration Fix
    # =========================================================================
    def test_04_gemini_thinking_token_payload_fix(self):
        """
        Verifies:
        1. When thinking_budget is explicitly 0 (utility ping), thinkingConfig is {"thinkingBudget": 0}.
        2. When task is creative text (3.8 Flash), default thinkingBudget is injected (1024).
        """
        # Utility ping: thinking_budget = 0
        payload_ping = self.gemini_adapter.format_payload(
            model="gemini-3.8-flash",
            prompt="ping",
            thinking_budget=0,
        )
        self.assertIn("thinkingConfig", payload_ping["generationConfig"])
        self.assertEqual(payload_ping["generationConfig"]["thinkingConfig"]["thinkingBudget"], 0)

        # Creative task: default thinkingBudget for 3.8
        payload_creative = self.gemini_adapter.format_payload(
            model="gemini-3.8-flash",
            prompt="Translate this chapter...",
            thinking_budget=1024,
        )
        self.assertEqual(payload_creative["generationConfig"]["thinkingConfig"]["thinkingBudget"], 1024)

    def test_05_gemini_fiction_safety_and_system_instruction(self):
        """Verifies injection of BLOCK_NONE safety settings and systemInstruction."""
        payload = self.gemini_adapter.format_payload(
            model="gemini-3.8-flash",
            prompt="Geralt drew his silver blade.",
            system_instruction="You are a Witcher dramatist.",
            response_json=True,
        )

        # System instruction
        self.assertIn("systemInstruction", payload)
        self.assertEqual(payload["systemInstruction"]["parts"][0]["text"], "You are a Witcher dramatist.")

        # JSON mime type
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")

        # Safety settings (BLOCK_NONE)
        safety = payload["safetySettings"]
        categories = {s["category"] for s in safety}
        self.assertIn("HARM_CATEGORY_HARASSMENT", categories)
        self.assertIn("HARM_CATEGORY_DANGEROUS_CONTENT", categories)
        for s in safety:
            self.assertEqual(s["threshold"], "BLOCK_NONE")

    def test_06_gemini_tts_speech_payload(self):
        """Verifies Gemini TTS payload formatting with voiceConfig and responseModalities."""
        payload = self.gemini_adapter.format_payload(
            model="gemini-3.8-flash-tts",
            prompt="नमस्ते दुनिया",
            is_audio=True,
            voice_name="Puck",
        )

        gen_config = payload["generationConfig"]
        self.assertEqual(gen_config["responseModalities"], ["AUDIO"])
        self.assertIn("speechConfig", gen_config)
        voice_cfg = gen_config["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]
        self.assertEqual(voice_cfg["voiceName"], "Puck")

    # =========================================================================
    # 3. Gemini Response Parsing & Audio Decoding
    # =========================================================================
    def test_07_gemini_response_parsing(self):
        """Verifies parsing of text candidates, thoughts, and usage metadata."""
        mock_resp = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Thinking through the translation...", "thought": True},
                            {"text": "यह हिंदी अनुवाद है।"}
                        ]
                    },
                    "finishReason": "STOP"
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 25,
                "candidatesTokenCount": 50,
                "totalTokenCount": 75
            }
        }

        with patch.object(self.gemini_adapter, "_execute_http_post", return_value=mock_resp):
            res = self.gemini_adapter.generate_text(
                model="gemini-3.8-flash",
                prompt="test prompt",
                api_key="AIzaSyFakeKey123",
            )

            self.assertEqual(res.text, "यह हिंदी अनुवाद है।")
            self.assertEqual(res.thoughts, "Thinking through the translation...")
            self.assertEqual(res.finish_reason, "STOP")
            self.assertEqual(res.tokens_used, 75)
            self.assertEqual(res.prompt_tokens, 25)
            self.assertEqual(res.completion_tokens, 50)

    def test_08_gemini_tts_audio_base64_decoding(self):
        """Verifies inlineData base64 decoding to raw PCM WAV bytes."""
        fake_wav_bytes = b"RIFF" + b"\x00" * 40 + b"WAVEfmt "
        b64_audio = base64.b64encode(fake_wav_bytes).decode("ascii")

        mock_resp = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/wav",
                                    "data": b64_audio
                                }
                            }
                        ]
                    }
                }
            ],
            "usageMetadata": {"totalTokenCount": 120}
        }

        with patch.object(self.gemini_adapter, "_execute_http_post", return_value=mock_resp):
            speech_res = self.gemini_adapter.synthesize_speech(
                model="gemini-3.8-flash-tts",
                text="नमस्कार",
                voice_name="Puck",
                api_key="AIzaSyFakeKey123",
            )

            self.assertEqual(speech_res.audio_bytes, fake_wav_bytes)
            self.assertEqual(speech_res.mime_type, "audio/wav")
            self.assertEqual(speech_res.tokens_used, 120)
            self.assertGreater(speech_res.duration_sec, 0.0)

    # =========================================================================
    # 4. OpenAI-Compatible Adapter
    # =========================================================================
    def test_09_openai_compat_payload_and_parsing(self):
        """Verifies OpenAI-compatible chat completion payload construction and parsing."""
        payload = self.openai_adapter.format_payload(
            model="llama3.3-70b",
            prompt="Hello world",
            system_instruction="Be concise",
            max_output_tokens=100,
            response_json=True,
        )

        self.assertEqual(payload["model"], "llama3.3-70b")
        self.assertEqual(len(payload["messages"]), 2)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertEqual(payload["max_tokens"], 100)
        self.assertEqual(payload["response_format"], {"type": "json_object"})

        mock_resp = {
            "choices": [
                {
                    "message": {"content": '{"status": "ok"}'},
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 10,
                "total_tokens": 25
            }
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_cm = MagicMock()
            mock_cm.read.return_value = json.dumps(mock_resp).encode("utf-8")
            mock_cm.__enter__.return_value = mock_cm
            mock_urlopen.return_value = mock_cm

            res = self.openai_adapter.generate_text(
                model="llama3.3-70b",
                prompt="test",
                api_key="csk-fake-key",
            )

            self.assertEqual(res.text, '{"status": "ok"}')
            self.assertEqual(res.finish_reason, "stop")
            self.assertEqual(res.tokens_used, 25)

    # =========================================================================
    # 5. Local GPU Adapter & Hardware VRAM Guard
    # =========================================================================
    def test_10_local_gpu_adapter_vram_protection(self):
        """Verifies HardwareVRAMGuard prevents concurrent GPU execution collisions."""
        res = self.local_adapter.generate_text(
            model="spark-x2.5-4b",
            prompt="Test local prompt",
        )
        self.assertIn("[LOCAL_GPU_OUTPUT", res.text)
        self.assertEqual(res.provider, "local")

        # Test audio generation
        speech = self.local_adapter.synthesize_speech(
            model="mms-forced-aligner",
            text="align text",
            voice_name="",
        )
        self.assertTrue(speech.audio_bytes.startswith(b"RIFF"))


if __name__ == "__main__":
    unittest.main()
