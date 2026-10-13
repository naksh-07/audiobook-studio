#!/usr/bin/env python3
"""
Unit tests for TTS Gateway Bridge (Room 4 Control Plane).
Verifies:
1. Restoration of speechMetadata.style in execute_tts_synthesize.
2. Narrator transparency lock: strictly 0.32 temperature, zero speechMetadata acting directives.
3. Character dialogue dynamic temperature clamping: [0.35, 0.52] (never > 0.52).
4. Preservation of certified acoustic reflexes and extraction of non-acoustic stage cues.
5. Universal novel-agnostic invariants (zero hardcoded titles or character names).
"""

import os
from unittest.mock import patch, MagicMock
import pytest

from audiobook_factory.core.models.adapters.base import SpeechResult
from audiobook_factory.tts.gateway_bridge import (
    execute_tts_synthesize,
    execute_tts_to_file,
    split_text_into_speech_chunks,
)


def _mock_speech_result(duration_sec: float = 0.5) -> SpeechResult:
    return SpeechResult(
        audio_bytes=b"RIFF" + b"\x00" * 44,
        mime_type="audio/wav",
        sample_rate=24000,
        duration_sec=duration_sec,
        tokens_used=10,
        model_id="gemini-3.8-flash",
        provider="gemini",
    )


def test_execute_tts_synthesize_restores_speech_metadata_style():
    """Verify speechMetadata.style is constructed and preserved for character dialogue."""
    with patch("audiobook_factory.core.models.gateway.get_model_gateway") as mock_gw_getter:
        mock_gateway = MagicMock()
        mock_gateway.synthesize_speech.return_value = _mock_speech_result()
        mock_gw_getter.return_value = mock_gateway

        res = execute_tts_synthesize(
            text="Step back right now.",
            voice_name="Puck",
            speaker="Character_Alpha",
            style_desc="whispering urgently",
        )

        assert mock_gateway.synthesize_speech.called
        call_kwargs = mock_gateway.synthesize_speech.call_args[1]
        assert call_kwargs["parts"] == [
            {"text": "Step back right now.", "speechMetadata": {"style": "whispering urgently"}}
        ]


def test_execute_tts_synthesize_narrator_locked_and_no_style():
    """Verify Narrator is locked to 0.32 temperature with zero speechMetadata.style."""
    with patch("audiobook_factory.core.models.gateway.get_model_gateway") as mock_gw_getter:
        mock_gateway = MagicMock()
        mock_gateway.synthesize_speech.return_value = _mock_speech_result()
        mock_gw_getter.return_value = mock_gateway

        res = execute_tts_synthesize(
            text="The wind howled across the valley.",
            voice_name="Aoede",
            speaker="Narrator",
            style_desc="theatrical melodrama",
            temperature=0.55,
        )

        assert mock_gateway.synthesize_speech.called
        call_kwargs = mock_gateway.synthesize_speech.call_args[1]
        assert call_kwargs["temperature"] == 0.32
        assert call_kwargs["parts"] == [
            {"text": "The wind howled across the valley."}
        ]


def test_execute_tts_synthesize_empty_style_no_speech_metadata():
    """Verify empty or neutral style produces clean parts without speechMetadata."""
    with patch("audiobook_factory.core.models.gateway.get_model_gateway") as mock_gw_getter:
        mock_gateway = MagicMock()
        mock_gateway.synthesize_speech.return_value = _mock_speech_result()
        mock_gw_getter.return_value = mock_gateway

        res = execute_tts_synthesize(
            text="I understand.",
            voice_name="Fenrir",
            speaker="Character_Beta",
            style_desc="",
        )

        call_kwargs = mock_gateway.synthesize_speech.call_args[1]
        assert call_kwargs["parts"] == [{"text": "I understand."}]


def test_execute_tts_synthesize_temperature_clamping_bounds():
    """Verify temperature clamping enforces [0.35, 0.52] with zero histrionics (never > 0.52)."""
    with patch("audiobook_factory.core.models.gateway.get_model_gateway") as mock_gw_getter:
        mock_gateway = MagicMock()
        mock_gateway.synthesize_speech.return_value = _mock_speech_result()
        mock_gw_getter.return_value = mock_gateway

        # Under-clamp test
        execute_tts_synthesize("Low temp test", speaker="Role_1", temperature=0.20)
        assert mock_gateway.synthesize_speech.call_args[1]["temperature"] == 0.35

        # Over-clamp test (never allow > 0.52)
        execute_tts_synthesize("High temp test", speaker="Role_1", temperature=0.65)
        assert mock_gateway.synthesize_speech.call_args[1]["temperature"] == 0.52

        # Extreme drama dynamic scaling
        execute_tts_synthesize("Rage test", speaker="Role_1", intensity="explosive", emotion="rage")
        temp_explosive = mock_gateway.synthesize_speech.call_args[1]["temperature"]
        assert 0.50 <= temp_explosive <= 0.52

        # Subdued drama dynamic scaling
        execute_tts_synthesize("Whisper test", speaker="Role_1", intensity="low", emotion="subdued")
        temp_subdued = mock_gateway.synthesize_speech.call_args[1]["temperature"]
        assert 0.35 <= temp_subdued <= 0.38


def test_execute_tts_synthesize_preserves_explicit_parts():
    """Verify explicit parts (e.g. multi-speaker batch parts) are preserved without stripping."""
    custom_parts = [
        {"text": "Turn 1", "speechMetadata": {"speaker": "Spk_1", "style": "stern"}},
        {"text": "Turn 2", "speechMetadata": {"speaker": "Spk_2", "style": "defiant"}},
    ]
    with patch("audiobook_factory.core.models.gateway.get_model_gateway") as mock_gw_getter:
        mock_gateway = MagicMock()
        mock_gateway.synthesize_speech.return_value = _mock_speech_result()
        mock_gw_getter.return_value = mock_gateway

        execute_tts_synthesize("Combined prompt", speaker="Spk_1", parts=custom_parts)
        call_kwargs = mock_gateway.synthesize_speech.call_args[1]
        assert call_kwargs["parts"] == custom_parts


def test_execute_tts_synthesize_auto_extracts_non_acoustic_stage_cues():
    """Verify bracketed non-acoustic cues are extracted to speechMetadata.style."""
    with patch("audiobook_factory.core.models.gateway.get_model_gateway") as mock_gw_getter:
        mock_gateway = MagicMock()
        mock_gateway.synthesize_speech.return_value = _mock_speech_result()
        mock_gw_getter.return_value = mock_gateway

        execute_tts_synthesize("[cold menace] Do not move.", speaker="Role_1")
        call_kwargs = mock_gateway.synthesize_speech.call_args[1]
        assert call_kwargs["text"] == "Do not move."
        assert call_kwargs["parts"] == [
            {"text": "Do not move.", "speechMetadata": {"style": "cold menace"}}
        ]


def test_execute_tts_synthesize_preserves_acoustic_reflex_in_spoken_text():
    """Verify certified acoustic reflex tags remain in spoken text without routing to style."""
    with patch("audiobook_factory.core.models.gateway.get_model_gateway") as mock_gw_getter:
        mock_gateway = MagicMock()
        mock_gateway.synthesize_speech.return_value = _mock_speech_result()
        mock_gw_getter.return_value = mock_gateway

        execute_tts_synthesize("[sighs] We have arrived.", speaker="Role_1")
        call_kwargs = mock_gateway.synthesize_speech.call_args[1]
        assert "[sighs]" in call_kwargs["text"]
        assert call_kwargs["parts"] == [{"text": "[sighs] We have arrived."}]
