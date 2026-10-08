#!/usr/bin/env python3
"""
Unit tests for UniversalInputGuard and DeliveryIntentExtractor.
Verifies stage direction stripping, SSML pause extraction, control character scrubbing,
and sacred vs. spoken text immutability.
"""

import pytest
from audiobook_factory.tts.contracts import TTSPipelineMode
from audiobook_factory.tts.guard.input_guard import UniversalInputGuard
from audiobook_factory.tts.guard.delivery_extractor import DeliveryIntentExtractor


def test_input_guard_empty_rejection():
    with pytest.raises(ValueError, match="Input text cannot be empty"):
        UniversalInputGuard.sanitize_and_guard(raw_text="   ", voice_id="Puck")


def test_input_guard_control_char_scrubbing():
    dirty_text = "नमस्ते\x00\x08 दुनिया\u200b!"
    req = UniversalInputGuard.sanitize_and_guard(raw_text=dirty_text, voice_id="Puck")
    assert "\x00" not in req.literary_text
    assert "\u200b" not in req.literary_text
    assert "नमस्ते दुनिया!" in req.spoken_text


def test_input_guard_sacred_vs_spoken_immutability():
    raw = "उसने ₹500 दिए और 10km चला।"
    req = UniversalInputGuard.sanitize_and_guard(raw_text=raw, voice_id="Puck")

    # Literary text preserves original numbers/symbols
    assert req.literary_text == "उसने ₹500 दिए और 10km चला।"

    # Spoken text is phonetized for TTS
    assert "पाँच सौ रुपये" in req.spoken_text
    assert "दस किलोमीटर" in req.spoken_text
    assert "₹500" not in req.spoken_text


def test_delivery_intent_extraction_and_tag_stripping():
    raw_with_cues = "[whispers] धीरे बोलो, कोई सुन लेगा! [urgent]"
    req = UniversalInputGuard.sanitize_and_guard(raw_text=raw_with_cues, voice_id="Puck")

    # Spoken text must NOT contain brackets
    assert "[" not in req.spoken_text
    assert "]" not in req.spoken_text
    assert "whispers" not in req.spoken_text
    assert req.spoken_text == "धीरे बोलो, कोई सुन लेगा!"

    # Delivery intent captured
    assert req.delivery_intent.emotion in ("whisper", "urgency")
    assert "whispers" in req.delivery_intent.extracted_stage_cues
    assert "urgent" in req.delivery_intent.extracted_stage_cues


def test_ssml_break_tag_extraction():
    ssml_text = "पहला वाक्य। <break time=\"500ms\"/> दूसरा वाक्य।"
    req = UniversalInputGuard.sanitize_and_guard(raw_text=ssml_text, voice_id="Puck")

    # SSML tags stripped from spoken text
    assert "<break" not in req.spoken_text
    assert "पहला वाक्य। दूसरा वाक्य।" == req.spoken_text
    assert req.suggested_pause_after_ms >= 500


def test_parenthetical_cues_extraction():
    paren_text = "(गुस्से में) तुम यहाँ क्या कर रहे हो?"
    req = UniversalInputGuard.sanitize_and_guard(raw_text=paren_text, voice_id="Puck")

    assert "(" not in req.spoken_text
    assert ")" not in req.spoken_text
    assert req.spoken_text == "तुम यहाँ क्या कर रहे हो?"
    assert req.delivery_intent.emotion == "anger"
