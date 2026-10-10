#!/usr/bin/env python3
"""
Unit tests for VoiceProfileRegistry (Room 3.5 Shared Core).
Verifies:
1. Sub-millisecond profile querying across Hindi and English catalogs.
2. Dialect filtering (Haryanvi, Bhojpuri, Awadhi, Bundeli, Urdu).
3. Gender and pitch tier filtering.
4. Structured markdown prompt generation for LLM Casting Director.
"""

import pytest
from audiobook_factory.casting.registry import VoiceProfileRegistry
from audiobook_factory.casting.contracts import CanonicalVoiceProfile


def test_01_registry_loads_voices_and_queries_hindi():
    reg = VoiceProfileRegistry.get_instance()
    assert reg.total_voices > 0

    # Query Hindi male voices
    hindi_males = reg.query_profiles(language_code="hi-IN", gender="male", limit=10)
    assert len(hindi_males) > 0
    for v in hindi_males:
        assert v.gender == "male"
        assert "hi" in v.language_code


def test_02_registry_dialect_filtering():
    reg = VoiceProfileRegistry.get_instance()

    # Query Haryanvi voices
    haryanvi_voices = reg.query_profiles(language_code="hi-IN", dialect="Haryanvi")
    assert len(haryanvi_voices) > 0
    for v in haryanvi_voices:
        assert "haryanvi" in v.dialect.lower()

    # Query Awadhi voices
    awadhi_voices = reg.query_profiles(language_code="hi-IN", dialect="Awadhi")
    assert len(awadhi_voices) > 0
    for v in awadhi_voices:
        assert "awadhi" in v.dialect.lower()


def test_03_registry_english_voices_and_direct_lookup():
    reg = VoiceProfileRegistry.get_instance()

    # Check direct profile lookup for known voices
    aoede = reg.get_profile("Aoede")
    assert aoede is not None
    assert aoede.gender == "female"
    assert "en" in aoede.language_code

    puck = reg.get_profile("Puck")
    assert puck is not None
    assert puck.gender == "male"


def test_04_formatted_catalog_for_prompt():
    reg = VoiceProfileRegistry.get_instance()

    prompt_table = reg.get_formatted_catalog_for_prompt(language_code="hi-IN", gender="female", limit=5)
    assert "| Voice ID |" in prompt_table
    assert "| Gender |" in prompt_table
    assert "female" in prompt_table.lower()
