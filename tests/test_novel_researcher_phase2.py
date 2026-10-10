#!/usr/bin/env python3
"""
Test Suite: Novel Researcher Architecture System - Phase 2.
Validates:
1. VocalAcousticDirector room impulse response profiling and vocal_spaces.json manifest generation.
2. NR-GATE-04: Vocals-Only Cleanliness Gate (0 Foley SFX, 0 BGM tracks, pure vocal acoustics).
3. 4D Parametric Formant DSP filter builder (build_vocal_filter_complex) for FFmpeg chains.
4. NR-GATE-03: Voice Collision Elimination Gate (>= 4% acoustic distance across same base voice).
5. PreProductionSupervisor Room 1 End-to-End integration emitting vocal_spaces.json and cast_lock.json.
"""

import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any, List, Optional

from audiobook_factory.preproduction.vocal_acoustic_director import (
    VocalAcousticDirector,
    VocalSpacesManifest,
    VocalSpaceProfile,
)
from audiobook_factory.translation.book_bible import BookBible, BookEntity, EpistemicProvenance
from audiobook_factory.character_caster import CharacterCaster
from audiobook_factory.preproduction.preproduction_supervisor import PreProductionSupervisor


class TestNovelResearcherPhase2(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_novel_researcher_phase2_"))
        self._prev_mock_offline = os.environ.get("MOCK_OFFLINE")
        os.environ["MOCK_OFFLINE"] = "1"

    def tearDown(self):
        if self._prev_mock_offline is not None:
            os.environ["MOCK_OFFLINE"] = self._prev_mock_offline
        else:
            os.environ.pop("MOCK_OFFLINE", None)
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_vocal_acoustic_director_manifest_and_vocals_only_gate(self):
        """Test 1 & 2: VocalAcousticDirector designs vocal_spaces.json satisfying NR-GATE-04 (0 SFX/BGM)."""
        director = VocalAcousticDirector()

        sample_prose = (
            "They entered the cavernous stone hall of the keep. The flames flickered against cold granite. "
            "Outside in the dense forest, the wind whistled through pine needles. "
            "Down in the tavern, the heavy oak tables creaked under iron flagons."
        )

        book_meta = {
            "title": "Acoustic Odyssey",
            "author": "Test Author",
            "project_slug": "acoustic_odyssey",
        }

        def mock_llm_acoustic(prompt: str, system_instruction: str = "", **kwargs) -> Any:
            return {
                "project_id": "proj-acoustic_odyssey",
                "book_title": "Acoustic Odyssey",
                "primary_era": "medieval_gothic",
                "spaces": {
                    "stone_hall": {
                        "reverb_type": "damp_stone_vault",
                        "wet_mix": 0.24,
                        "predelay_ms": 32,
                        "decay_time_s": 2.2,
                        "proximity_staging": "spatial_echo",
                        "high_shelf_damping_db": -2.0,
                        "dominant_materials": ["granite", "iron"],
                    },
                    "dense_forest": {
                        "reverb_type": "outdoor_forest",
                        "wet_mix": 0.05,
                        "predelay_ms": 8,
                        "decay_time_s": 0.4,
                        "proximity_staging": "direct_voice",
                        "high_shelf_damping_db": -0.5,
                        "dominant_materials": ["pine", "dirt"],
                    },
                    "wooden_tavern": {
                        "reverb_type": "medium_wooden_hall",
                        "wet_mix": 0.14,
                        "predelay_ms": 18,
                        "decay_time_s": 1.1,
                        "proximity_staging": "conversational_close",
                        "high_shelf_damping_db": -1.2,
                        "dominant_materials": ["oak", "cloth"],
                    },
                },
            }

        manifest = director.design_vocal_spaces(
            novel_text_sample=sample_prose,
            book_metadata=book_meta,
            call_llm_fn=mock_llm_acoustic,
        )

        self.assertIsInstance(manifest, VocalSpacesManifest)
        self.assertEqual(manifest.project_id, "proj-acoustic_odyssey")
        self.assertIn("stone_hall", manifest.spaces)
        self.assertIn("dense_forest", manifest.spaces)
        self.assertIn("wooden_tavern", manifest.spaces)

        # NR-GATE-04: Vocals-Only Cleanliness Gate
        manifest_dict = manifest.model_dump()
        self.assertNotIn("signature_foley_palettes", manifest_dict)
        self.assertNotIn("world_ambience_motifs", manifest_dict)
        self.assertNotIn("sound_effects", manifest_dict)

        # Legacy backward compatibility check
        legacy_sonic = manifest.to_legacy_sonic_bible()
        self.assertIn("acoustic_spaces", legacy_sonic)
        self.assertEqual(legacy_sonic["signature_foley_palettes"], {})
        self.assertEqual(legacy_sonic["world_ambience_motifs"], [])

    def test_4d_formant_filter_builder(self):
        """Test 3: build_vocal_filter_complex produces clean studio FFmpeg filter chains."""
        director = VocalAcousticDirector()

        # Create a sample manifest with a space
        manifest = VocalSpacesManifest(
            project_id="proj-test",
            book_title="Test Book",
            spaces={
                "tavern": VocalSpaceProfile(
                    reverb_type="medium_wooden_hall",
                    wet_mix=0.15,
                    predelay_ms=20,
                    decay_time_s=1.2,
                    high_shelf_damping_db=-1.5,
                )
            },
        )

        # Character with 4D Formants
        entity = BookEntity(
            canonical_name="Baron Valerius",
            english_name="Baron Valerius",
            gender="male",
            pitch_shift_pct=-6.0,
            tempo_scale=0.96,
            eq_formant="equalizer=f=220:t=q:w=1.2:g=+3.0,equalizer=f=3400:t=q:w=1.0:g=-2.0",
        )

        filter_str = director.build_vocal_filter_complex(
            character_entity=entity,
            space_name="tavern",
            spaces_manifest=manifest,
        )

        self.assertIn("highpass=f=60", filter_str)
        self.assertIn("asetrate=22560", filter_str)  # 24000 * 0.94
        self.assertIn("equalizer=f=220", filter_str)
        self.assertIn("equalizer=f=3400", filter_str)
        self.assertIn("aecho=", filter_str)

    def test_nr_gate_03_voice_collision_elimination(self):
        """Test 4: NR-GATE-03 guarantees >= 4% acoustic distance when base voices collide."""
        raw_chars = [
            {"name": "Soldier A", "gender": "male", "vocal_archetype": "gruff"},
            {"name": "Soldier B", "gender": "male", "vocal_archetype": "gruff"},
            {"name": "Soldier C", "gender": "male", "vocal_archetype": "gruff"},
            {"name": "Soldier D", "gender": "male", "vocal_archetype": "gruff"},
        ]

        roster, registry, cast_lock = CharacterCaster._build_cast_allocation(
            project_id="proj-army",
            raw_characters=raw_chars,
            use_hindi=True,
        )

        # Check all soldiers assigned
        self.assertIn("Soldier A", registry)
        self.assertIn("Soldier B", registry)
        self.assertIn("Soldier C", registry)
        self.assertIn("Soldier D", registry)

        # Inspect pitches of characters sharing the same voice
        voice_to_pitches: Dict[str, List[float]] = {}
        for s_name in ["Soldier A", "Soldier B", "Soldier C", "Soldier D"]:
            cfg = registry[s_name]
            v = cfg["voice"]
            p = cfg["pitch"]
            voice_to_pitches.setdefault(v, []).append(p)

        # For any shared voice, ensure every pitch difference is at least 0.04 (4%)
        for v, pitches in voice_to_pitches.items():
            if len(pitches) > 1:
                sorted_p = sorted(pitches)
                for i in range(len(sorted_p) - 1):
                    diff = round(sorted_p[i + 1] - sorted_p[i], 4)
                    self.assertGreaterEqual(
                        diff,
                        0.039,
                        f"NR-GATE-03 Breach: Pitch difference {diff:.4f} between shared voice '{v}' is less than 4%",
                    )

    def test_preproduction_supervisor_end_to_end_with_vocal_spaces(self):
        """Test 5: PreProductionSupervisor executes Room 1 emitting vocal_spaces.json."""
        extracted_dir = self.temp_dir / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "title": "Dune Chronicles",
            "author": "Frank Herbert",
            "project_slug": "dune_chronicles",
        }
        (self.temp_dir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

        ch1_text = (
            "Paul Atreides gazed across the desert sands of Arrakis. "
            "\"The spice must flow,\" Paul whispered. "
            "Lady Jessica entered the chamber and stood beside Paul. "
            "Gurney Halleck tuned his baliset in the corner."
        )
        (extracted_dir / "chapter_001.md").write_text(ch1_text, encoding="utf-8")

        def mock_llm_room1(prompt: str, system_instruction: str = "", **kwargs) -> Any:
            if "Canonical Novel Dossier" in prompt or "world_lore_entities" in prompt or "googleSearch" in str(kwargs):
                return {
                    "book_title": "Dune Chronicles",
                    "author": "Frank Herbert",
                    "literary_dna": {
                        "tradition": "EPIC_SPECULATIVE_SCI_FI",
                        "primary_genre": "Science Fiction",
                        "historical_era": "distant_future",
                        "source_fidelity_tier": "STANDARD_ADULT",
                    },
                    "characters": [
                        {"english_name": "Paul Atreides", "hindi_name": "पॉल एट्रिडिज़", "role_prominence": "lead", "gender": "male"},
                        {"english_name": "Lady Jessica", "hindi_name": "लेडी जेसिका", "role_prominence": "major", "gender": "female"},
                        {"english_name": "Gurney Halleck", "hindi_name": "गर्नी हैलेक", "role_prominence": "major", "gender": "male"},
                    ],
                    "world_acoustics": {
                        "primary_materials": ["stone", "sand", "plasteel"],
                        "banned_anachronisms": ["internal_combustion_engine"],
                    },
                    "linguistic_dialect": {"recommended_hindustani_register": "elevated dramatic Hindustani"},
                    "world_lore_entities": {"locations": {"Arrakis": "अराकिस"}},
                }
            elif "Universal Literary DNA" in prompt or "book_dna" in prompt.lower():
                return {
                    "literary_tradition": "EPIC_SPECULATIVE_SCI_FI",
                    "source_fidelity_tier": "STANDARD_ADULT",
                    "profanity_policy": "MILD_COLLOQUIAL",
                    "regional_dialect_cadence": "Elevated Dramatic Hindustani",
                }
            elif "Dramatis Personae" in prompt or "Casting Director" in system_instruction:
                return [
                    {"english_name": "Paul Atreides", "hindi_name": "पॉल एट्रिडिज़", "gender": "male"},
                    {"english_name": "Lady Jessica", "hindi_name": "लेडी जेसिका", "gender": "female"},
                ]
            elif "vocal_spaces" in prompt.lower() or "Vocal Acoustic" in system_instruction or "reverb" in prompt.lower():
                return {
                    "project_id": "proj-dune_chronicles",
                    "book_title": "Dune Chronicles",
                    "primary_era": "distant_future",
                    "spaces": {
                        "desert_open": {
                            "reverb_type": "open_dune_expanse",
                            "wet_mix": 0.04,
                            "predelay_ms": 6,
                            "decay_time_s": 0.3,
                            "proximity_staging": "direct_voice",
                            "high_shelf_damping_db": -0.5,
                            "dominant_materials": ["sand"],
                        },
                        "stone_palace": {
                            "reverb_type": "high_ceiling_stone_hall",
                            "wet_mix": 0.22,
                            "predelay_ms": 28,
                            "decay_time_s": 1.8,
                            "proximity_staging": "conversational_close",
                            "high_shelf_damping_db": -1.8,
                            "dominant_materials": ["stone", "plasteel"],
                        },
                    },
                }
            elif "Phonetic" in system_instruction or "lexicon" in prompt.lower():
                return {
                    "locations": {"Arrakis": "अराकिस"},
                    "terminology": {"spice": "स्पाइस / मेलान्ज"},
                }
            return {}

        supervisor = PreProductionSupervisor()
        res = supervisor.execute_preproduction(
            project_dir=self.temp_dir,
            force=True,
            call_llm_fn=mock_llm_room1,
        )

        self.assertEqual(res["status"], "MASTER_LOCKED")

        # Verify all 5 master state artifacts exist
        self.assertTrue((self.temp_dir / "vocal_spaces.json").exists())
        self.assertTrue((self.temp_dir / "sonic_bible.json").exists())
        self.assertTrue((self.temp_dir / "book_bible.json").exists())
        self.assertTrue((self.temp_dir / "book_dna.json").exists())
        self.assertTrue((self.temp_dir / "cast_lock.json").exists())

        # Validate vocal_spaces.json content
        v_spaces = json.loads((self.temp_dir / "vocal_spaces.json").read_text(encoding="utf-8"))
        self.assertIn("spaces", v_spaces)
        self.assertIn("desert_open", v_spaces["spaces"])
        self.assertIn("stone_palace", v_spaces["spaces"])


if __name__ == "__main__":
    unittest.main()
