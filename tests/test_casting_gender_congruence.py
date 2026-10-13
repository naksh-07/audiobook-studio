#!/usr/bin/env python3
"""
Unit tests for Casting Gender Congruence and Gate 2.8 validation.
Verifies fail-closed GateAuditError when cross-gender casting occurs.
"""

import unittest
import tempfile
import json
from pathlib import Path

from audiobook_factory.gates.gate28_distinction import AuditoryDistinctionGate
from audiobook_factory.gates.pre_synthesis import GateAuditError
from audiobook_factory.tts.voice_catalog import get_voice_catalog
from audiobook_factory.casting.registry import VoiceProfileRegistry


class TestCastingGenderCongruence(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.p_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_voice_catalog_male_character_never_gets_female_voice(self):
        catalog = get_voice_catalog()
        # Even with no archetype or rustic archetype, adult male must get male voice
        v_id = catalog.get_best_matching_voice(
            gender="male",
            language_code="hi-IN",
            archetype="rustic commoner butcher",
        )
        meta = catalog.get_voice(v_id)
        self.assertIsNotNone(meta)
        self.assertEqual(meta.get("gender"), "male")

        # Test another role
        v_id_bard = catalog.get_best_matching_voice(
            gender="male",
            language_code="hi-IN",
            archetype="charismatic noble bard companion",
        )
        meta_bard = catalog.get_voice(v_id_bard)
        self.assertEqual(meta_bard.get("gender"), "male")

    def test_gate_28_fails_closed_on_cross_gender_casting(self):
        # Create character_roster.json declaring 'Gar' and 'Cicada' as male
        roster_data = {
            "characters": {
                "Gar": {"english_name": "Gar", "gender": "male", "assigned_voice_id": "Kore"},
                "Geralt": {"english_name": "Geralt", "gender": "male", "assigned_voice_id": "Charon"},
            }
        }
        (self.p_dir / "character_roster.json").write_text(json.dumps(roster_data), encoding="utf-8")

        # Voice registry intentionally misassigning a female voice to Gar
        # 'Kore' is female
        reg_data = {
            "Gar": {"voice": "Kore", "pitch": 1.0, "speed": 1.0},
            "Geralt": {"voice": "Charon", "pitch": 1.0, "speed": 1.0},
        }
        (self.p_dir / "voice_registry.json").write_text(json.dumps(reg_data), encoding="utf-8")

        # Cast lock
        lock_data = {
            "locks": {
                "gar": {"character_id": "gar", "character_name": "Gar", "voice_id": "Kore", "locked": True},
                "geralt": {"character_id": "geralt", "character_name": "Geralt", "voice_id": "Charon", "locked": True},
            }
        }
        (self.p_dir / "cast_lock.json").write_text(json.dumps(lock_data), encoding="utf-8")

        segments = [
            {"index": 1, "type": "dialogue", "speaker": "Gar", "text": "रुको!", "scene_id": "scene_01"},
            {"index": 2, "type": "dialogue", "speaker": "Geralt", "text": "क्या बात है?", "scene_id": "scene_01"},
        ]

        # Gate 2.8 MUST fail closed with GateAuditError
        with self.assertRaises(GateAuditError) as ctx:
            AuditoryDistinctionGate.audit_chapter_script(
                segments=segments,
                project_dir=self.p_dir,
                strict=True,
            )

        err_text = str(ctx.exception)
        self.assertIn("Casting Congruence Violation", err_text)
        self.assertIn("Gar", err_text)
        self.assertIn("female", err_text)

    def test_gate_28_passes_when_gender_congruent_and_separated(self):
        # Correct assignment: Gar (male voice: Fenrir), Geralt (male voice: Charon)
        roster_data = {
            "characters": {
                "Gar": {"english_name": "Gar", "gender": "male", "assigned_voice_id": "Fenrir"},
                "Geralt": {"english_name": "Geralt", "gender": "male", "assigned_voice_id": "Charon"},
            }
        }
        (self.p_dir / "character_roster.json").write_text(json.dumps(roster_data), encoding="utf-8")

        reg_data = {
            "Gar": {"voice": "Fenrir", "pitch": 0.90, "speed": 0.96},
            "Geralt": {"voice": "Charon", "pitch": 1.0, "speed": 1.0},
        }
        (self.p_dir / "voice_registry.json").write_text(json.dumps(reg_data), encoding="utf-8")

        lock_data = {
            "locks": {
                "gar": {"character_id": "gar", "character_name": "Gar", "voice_id": "Fenrir", "locked": True},
                "geralt": {"character_id": "geralt", "character_name": "Geralt", "voice_id": "Charon", "locked": True},
            }
        }
        (self.p_dir / "cast_lock.json").write_text(json.dumps(lock_data), encoding="utf-8")

        segments = [
            {"index": 1, "type": "dialogue", "speaker": "Gar", "text": "रुको!", "scene_id": "scene_01"},
            {"index": 2, "type": "dialogue", "speaker": "Geralt", "text": "क्या बात है?", "scene_id": "scene_01"},
        ]

        verdict = AuditoryDistinctionGate.audit_chapter_script(
            segments=segments,
            project_dir=self.p_dir,
            strict=True,
        )
        self.assertTrue(verdict.passed)
        self.assertEqual(len(verdict.violations), 0)


if __name__ == "__main__":
    unittest.main()
