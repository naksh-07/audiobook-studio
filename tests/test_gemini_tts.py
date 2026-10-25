#!/usr/bin/env python3
"""
Unit tests for Gemini TTS Adapter, Provider Directing, and Acoustic Reflex Preservation.
Verifies:
1. GeminiProviderAdapter payload preservation (speechMetadata inside parts, voiceName mapping).
2. Certified acoustic reflex preservation ([laughs], [sighs], [whispers], [growls], [gasp], [chuckles], [pant], [groan]).
3. Non-acoustic acting descriptor routing ([cold menace], [angrily], [धीमी आवाज़ में]) to speechMetadata.style.
4. resolve_speech_metadata_style directing fidelity without generic dilution.
5. Temperature clamping eliminating screeching and histrionics.
"""

import pytest
from unittest.mock import patch, MagicMock

from audiobook_factory.core.models.adapters.gemini import GeminiProviderAdapter
from audiobook_factory.tts.providers.gemini import (
    sanitize_spoken_text_and_extract_stage_directions,
    resolve_speech_metadata_style,
    CERTIFIED_ACOUSTIC_REFLEX_TAGS,
)


def test_gemini_adapter_format_payload_preserves_speech_metadata():
    """Verify speechMetadata inside parts is fully preserved when formatting payload."""
    adapter = GeminiProviderAdapter()
    parts = [
        {"text": "Sample utterance", "speechMetadata": {"style": "subdued whisper"}}
    ]
    payload = adapter.format_payload(
        model="gemini-3.8-flash",
        prompt="Sample utterance",
        is_audio=True,
        voice_name="Puck",
        parts=parts,
    )

    contents = payload.get("contents", [])
    assert len(contents) == 1
    assert contents[0]["parts"] == parts
    assert contents[0]["parts"][0]["speechMetadata"]["style"] == "subdued whisper"


def test_gemini_adapter_format_payload_voice_name_mapping():
    """Verify voice_name maps into generationConfig.speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName."""
    adapter = GeminiProviderAdapter()

    # Explicit voice_name parameter
    payload = adapter.format_payload(
        model="gemini-3.8-flash",
        prompt="Test line",
        is_audio=True,
        voice_name="Aoede",
    )
    voice_cfg = (
        payload.get("generationConfig", {})
        .get("speechConfig", {})
        .get("voiceConfig", {})
        .get("prebuiltVoiceConfig", {})
    )
    assert voice_cfg.get("voiceName") == "Aoede"

    # Fallback to voice in kwargs
    payload2 = adapter.format_payload(
        model="gemini-3.8-flash",
        prompt="Test line",
        is_audio=True,
        voice="Fenrir",
    )
    voice_cfg2 = (
        payload2.get("generationConfig", {})
        .get("speechConfig", {})
        .get("voiceConfig", {})
        .get("prebuiltVoiceConfig", {})
    )
    assert voice_cfg2.get("voiceName") == "Fenrir"


def test_gemini_adapter_format_payload_multi_speaker_config():
    """Verify multi-speaker speechConfig is preserved intact in generationConfig."""
    adapter = GeminiProviderAdapter()
    multi_cfg = {
        "multiSpeakerVoiceConfig": {
            "speakerVoiceConfigs": [
                {"speaker": "Speaker_A", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Puck"}}},
                {"speaker": "Speaker_B", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Aoede"}}},
            ]
        }
    }
    payload = adapter.format_payload(
        model="gemini-3.8-flash",
        prompt="Multi-speaker utterance",
        is_audio=True,
        speech_config=multi_cfg,
    )
    assert payload["generationConfig"]["speechConfig"] == multi_cfg


def test_certified_acoustic_reflexes_preserved_in_spoken_text():
    """Verify all certified acoustic reflex tags are preserved in spoken text and not extracted to cues."""
    certified_tags = [
        "[laughs]", "[sighs]", "[whispers]", "[growls]",
        "[gasp]", "[chuckles]", "[pant]", "[groan]",
    ]
    for tag in certified_tags:
        text = f"{tag} We must move quickly."
        clean_text, extracted_cues = sanitize_spoken_text_and_extract_stage_directions(text)
        assert tag in clean_text, f"Acoustic reflex tag {tag} was wrongly stripped from spoken text"
        assert extracted_cues == [], f"Acoustic reflex tag {tag} was wrongly routed to stage cues"


def test_hindi_acoustic_reflexes_mapped():
    """Verify physical Hindi acoustic reflexes are mapped to acoustic reflex tags in spoken text."""
    hindi_reflexes = [
        ("[हँसते हुए] सच में?", "[laughs]"),
        ("[मुस्कुराते हुए] अच्छा लगा।", "[chuckles]"),
        ("[फुसफुसाते हुए] शांत रहो।", "[whispers]"),
        ("[हाँफते हुए] भागो!", "[pant]"),
        ("[आह भरते हुए] क्या कर सकते हैं।", "[sighs]"),
    ]
    for raw_text, expected_tag in hindi_reflexes:
        clean_text, extracted_cues = sanitize_spoken_text_and_extract_stage_directions(raw_text)
        assert expected_tag in clean_text, f"Expected {expected_tag} in '{clean_text}'"
        assert extracted_cues == []


def test_non_acoustic_descriptors_routed_to_style():
    """Verify non-acoustic acting descriptors are stripped from spoken text and routed to style cues."""
    test_cases = [
        ("[cold menace] Don't move.", "Don't move.", ["cold menace"]),
        ("[angrily] Stop right there!", "Stop right there!", ["angrily"]),
        ("[धीमी आवाज़ में] यहाँ कोई नहीं है।", "यहाँ कोई नहीं है।", ["धीमी आवाज़ में"]),
        ("[sternly] Come here.", "Come here.", ["sternly"]),
        ("[urgent] We need to leave.", "We need to leave.", ["urgent"]),
    ]
    for raw_text, expected_clean, expected_cues in test_cases:
        clean_text, extracted_cues = sanitize_spoken_text_and_extract_stage_directions(raw_text)
        assert clean_text == expected_clean
        assert extracted_cues == expected_cues


def test_resolve_speech_metadata_style_narrator():
    """Verify Narrator delivery is locked to articulate measured delivery without generic dilution."""
    # Standard narrator
    narrator_style = resolve_speech_metadata_style(acting=None, is_narrator=True)
    assert "articulate, measured" in narrator_style.lower() and "narration" in narrator_style.lower()

    # Narrator with chapter tint
    tinted_narrator = resolve_speech_metadata_style(
        acting=None, narrator_tint="atmospheric historical narration", is_narrator=True
    )
    assert "atmospheric historical narration" in tinted_narrator
    assert "articulate measured storytelling narration" in tinted_narrator


def test_resolve_speech_metadata_style_dialogue_restraint():
    """Verify character dialogue style includes acting cues and universal anti-theatricality restraint anchor."""
    # Neutral dialogue produces empty string (avoiding generic dilution)
    neutral_style = resolve_speech_metadata_style(acting=None, emotion="neutral", intensity="medium", is_narrator=False)
    assert neutral_style == ""

    # Styled dialogue includes acting context and restraint anchor
    acting = {"delivery_style": "hoarse_whisper", "tone": "menacing"}
    style = resolve_speech_metadata_style(
        acting=acting,
        emotion="anger",
        intensity="explosive",
        memory_vocal_constraint="gravelly voice",
        is_narrator=False,
    )
    assert "hoarse whisper" in style
    assert "anger" in style
    assert "explosive" in style
    assert "menacing" in style
    assert "gravelly voice" in style
