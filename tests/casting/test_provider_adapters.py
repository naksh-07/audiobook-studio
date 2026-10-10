#!/usr/bin/env python3
"""
Unit tests for Dual Provider Voice Adapters (GeminiVoiceAdapter & QwenVoiceAdapter).
Verifies:
1. GeminiVoiceAdapter translates formants to style descriptors and FFmpeg EQ clauses.
2. Gemini narrator style is calm articulate at temperature 0.32.
3. QwenVoiceAdapter translates tempo to native speed float and binds reference audio.
4. Provider capabilities match real provider constraints.
"""

import pytest
from audiobook_factory.casting.adapters import GeminiVoiceAdapter, QwenVoiceAdapter
from audiobook_factory.casting.contracts import CharacterCastAssignment, SpectralFormantProfile


def test_01_gemini_voice_adapter_dialogue_and_narrator():
    adapter = GeminiVoiceAdapter()
    caps = adapter.get_provider_capabilities()
    assert caps.provider_name == "gemini_tts"
    assert caps.supports_style_prompt is True
    assert caps.supports_reference_audio is False

    # Dialogue segment
    seg = {
        "speaker": "Commander Valen",
        "text": "Hold the line!",
        "emotion": "authoritative",
        "formant_profile": {
            "chest_resonance_150hz_db": 2.5,
            "nasal_presence_2800hz_db": 0.0,
            "throat_clarity_3200hz_db": 0.0,
            "air_shelf_8000hz_db": 0.0,
            "target_tempo_multiplier": 0.97,
        }
    }
    cast = CharacterCastAssignment(
        character_id="valen",
        canonical_name="Commander Valen",
        voice_id="hi-in-advisor-10",
        gender="male",
    )

    payload = adapter.adapt_segment_to_provider(seg, cast)
    assert payload["provider"] == "gemini_tts"
    assert payload["voice_name"] == "hi-in-advisor-10"
    assert "deep resonant chest register" in payload["speechMetadata"]["style"]
    assert 0.30 <= payload["temperature"] <= 0.55
    assert len(payload["post_dsp_eq_filters"]) > 0
    assert any("equalizer=f=150" in f for f in payload["post_dsp_eq_filters"])

    # Narrator segment
    narr_seg = {"speaker": "Narrator", "text": "The wind howled through the passes."}
    narr_payload = adapter.adapt_segment_to_provider(narr_seg)
    assert narr_payload["voice_name"] == "Aoede"
    assert "calm, steady, articulate" in narr_payload["speechMetadata"]["style"]
    assert narr_payload["temperature"] == 0.32


def test_02_qwen_voice_adapter():
    adapter = QwenVoiceAdapter()
    caps = adapter.get_provider_capabilities()
    assert caps.provider_name == "qwen3_tts"
    assert caps.supports_reference_audio is True
    assert caps.supports_native_speed is True

    seg = {
        "speaker": "Sorceress Elena",
        "text": "The wards are breaking.",
        "emotion": "fearful",
        "formant_profile": {
            "chest_resonance_150hz_db": -1.0,
            "nasal_presence_2800hz_db": 2.0,
            "throat_clarity_3200hz_db": 1.0,
            "air_shelf_8000hz_db": 0.0,
            "target_tempo_multiplier": 1.04,
        }
    }
    cast = CharacterCastAssignment(
        character_id="elena",
        canonical_name="Sorceress Elena",
        voice_id="qwen-elena-v1",
        gender="female",
    )

    payload = adapter.adapt_segment_to_provider(seg, cast)
    assert payload["provider"] == "qwen3_tts"
    assert payload["speed"] == 1.04
    assert payload["sample_rate"] == 24000
    assert "fearful" in payload["instruction"].lower()
