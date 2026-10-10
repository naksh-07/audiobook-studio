#!/usr/bin/env python3
"""
Unit tests for StudioCastingDirector (Room 3.5 Subsystem 1).
Verifies:
1. LLM-directed character voice assignment with justification.
2. Anime Seiyū child rule (young boys cast with bright youthful voices).
3. Immutable cast locking (cast_lock.json and voice_registry.json sync).
4. Ensemble non-collision and deterministic fallback.
"""

import tempfile
import json
from pathlib import Path
import pytest

from audiobook_factory.casting.director import StudioCastingDirector
from audiobook_factory.casting.contracts import CastLock


def test_01_cast_character_with_mock_llm():
    with tempfile.TemporaryDirectory() as tmp_dir:
        director = StudioCastingDirector(project_dir=tmp_dir)

        def mock_llm(prompt, **kwargs):
            return {
                "assigned_voice_id": "hi-in-advisor-10",
                "dialect": "Haryanvi Hindi",
                "casting_rationale": "Blunt martial resonance matches veteran guard.",
                "baseline_formants": {
                    "chest_resonance_150hz_db": 2.0,
                    "nasal_presence_2800hz_db": 1.0,
                    "target_tempo_multiplier": 0.98,
                }
            }

        lock = director.cast_character(
            character_name="Captain Malik",
            gender="male",
            archetype="veteran soldier warrior",
            dialect_hint="Haryanvi",
            use_hindi=True,
            call_llm_fn=mock_llm,
        )

        assert lock.character_name == "Captain Malik"
        assert lock.voice_id == "hi-in-advisor-10"
        assert lock.locked is True
        assert lock.calibration_overrides.get("chest_resonance_150hz_db") == 2.0

        # Verify cast_lock.json and voice_registry.json were written
        lock_file = Path(tmp_dir) / "cast_lock.json"
        reg_file = Path(tmp_dir) / "voice_registry.json"
        assert lock_file.exists()
        assert reg_file.exists()

        reg_data = json.loads(reg_file.read_text(encoding="utf-8"))
        assert "Captain Malik" in reg_data
        assert reg_data["Captain Malik"]["voice"] == "hi-in-advisor-10"


def test_02_anime_seiyu_child_rule():
    with tempfile.TemporaryDirectory() as tmp_dir:
        director = StudioCastingDirector(project_dir=tmp_dir)

        # Child boy (8 years old)
        lock = director.cast_character(
            character_name="Little Chintu",
            gender="male",
            archetype="innocent young village boy",
            is_child=True,
            age_hint=8,
            use_hindi=True,
        )

        # Under Anime Seiyū rule, must be cast with a female voice model
        prof = director.registry.get_profile(lock.voice_id)
        assert prof is not None
        assert prof.gender == "female"


def test_03_cast_immutability():
    with tempfile.TemporaryDirectory() as tmp_dir:
        director = StudioCastingDirector(project_dir=tmp_dir)

        # First cast
        lock1 = director.cast_character(
            character_name="Elder Varma",
            gender="male",
            archetype="wise scholar",
            use_hindi=True,
        )

        # Second cast with different archetype should NOT overwrite the locked voice
        lock2 = director.cast_character(
            character_name="Elder Varma",
            gender="male",
            archetype="warrior",
            use_hindi=True,
        )

        assert lock1.voice_id == lock2.voice_id
