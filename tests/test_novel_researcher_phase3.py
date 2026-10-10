#!/usr/bin/env python3
"""
Test Suite: Novel Researcher Architecture System - Phase 3.
Validates:
1. Neutral metadata package (audiobook_factory.metadata) & backward compatibility shim.
2. NovelStateMaintainer atomic transactional commit of all master state files (NR-GATE-06).
3. Staged commit rollback safety on failure.
4. PreProductionSupervisor decoupled orchestration delegating persistence to NovelStateMaintainer.
5. NovelStateMaintainer.discover_and_lock_character atomic multi-file synchronization.
"""

import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any

from audiobook_factory.metadata import (
    BookBible,
    BookEntity,
    NovelEntity,
    EpistemicProvenance,
    NovelStateMaintainer,
    MasterPreProductionState,
)
from audiobook_factory.preproduction.vocal_acoustic_director import (
    VocalSpacesManifest,
    VocalSpaceProfile,
)
from audiobook_factory.preproduction.preproduction_supervisor import PreProductionSupervisor


class TestNovelResearcherPhase3(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_novel_researcher_phase3_"))
        self._prev_mock_offline = os.environ.get("MOCK_OFFLINE")
        os.environ["MOCK_OFFLINE"] = "1"

    def tearDown(self):
        if self._prev_mock_offline is not None:
            os.environ["MOCK_OFFLINE"] = self._prev_mock_offline
        else:
            os.environ.pop("MOCK_OFFLINE", None)
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_metadata_package_imports_and_backward_compatibility(self):
        """Test 1: audiobook_factory.metadata provides canonical models; translation shim is 100% compatible."""
        # Check metadata imports
        self.assertEqual(NovelEntity, BookEntity)
        prov = EpistemicProvenance(origin="CORPUS_EXTRACTED", first_chapter=1, corpus_mention_count=5)
        entity = NovelEntity(
            canonical_name="Geralt of Rivia",
            english_name="Geralt of Rivia",
            hindi_name="गेराल्ट",
            provenance=prov,
        )
        self.assertEqual(entity.english_name, "Geralt of Rivia")
        self.assertEqual(entity.provenance.origin, "CORPUS_EXTRACTED")

        # Check backward-compatibility shim from translation.book_bible
        from audiobook_factory.translation.book_bible import (
            BookBible as LegacyBookBible,
            BookEntity as LegacyBookEntity,
            NovelEntity as LegacyNovelEntity,
            EpistemicProvenance as LegacyProvenance,
        )
        self.assertIs(LegacyBookBible, BookBible)
        self.assertIs(LegacyBookEntity, BookEntity)
        self.assertIs(LegacyNovelEntity, NovelEntity)
        self.assertIs(LegacyProvenance, EpistemicProvenance)

    def test_novel_state_maintainer_atomic_commit_all_files(self):
        """Test 2: NovelStateMaintainer commits all 5 master state files atomically with 4D sync."""
        p_dir = self.temp_dir / "master_proj"
        p_dir.mkdir(parents=True, exist_ok=True)

        book_meta = {"title": "The Last Wish", "author": "Andrzej Sapkowski", "project_slug": "last_wish"}
        book_dna = {"literary_tradition": "DARK_FANTASY", "source_fidelity_tier": "RAW_UNRATED"}
        bible = BookBible(book_title="The Last Wish", author="Andrzej Sapkowski")
        bible.characters["Geralt"] = BookEntity(
            canonical_name="Geralt",
            english_name="Geralt",
            hindi_name="गेराल्ट",
            provenance=EpistemicProvenance(origin="CORPUS_EXTRACTED"),
        )

        v_spaces = VocalSpacesManifest(
            project_id="proj-last_wish",
            book_title="The Last Wish",
            spaces={
                "tavern": VocalSpaceProfile(reverb_type="medium_wooden_hall", wet_mix=0.15),
            },
        )

        roster = {"project_id": "proj-last_wish", "characters": {"Geralt": {"assigned_voice_id": "Fenrir"}}}
        voice_reg = {
            "Geralt": {
                "voice": "Fenrir",
                "pitch": 0.94,
                "speed": 0.98,
                "bass_boost_db": 2.0,
                "presence_boost_db": 1.5,
            }
        }
        cast_lock = {"project_slug": "proj-last_wish", "locks": {"Geralt": {"voice_id": "Fenrir"}}}

        state = NovelStateMaintainer.commit_master_preproduction(
            project_dir=p_dir,
            book_metadata=book_meta,
            book_dna=book_dna,
            book_bible=bible,
            vocal_spaces=v_spaces,
            roster=roster,
            voice_registry=voice_reg,
            cast_lock=cast_lock,
        )

        self.assertIsInstance(state, MasterPreProductionState)
        self.assertEqual(state.book_title, "The Last Wish")

        # Verify all 7 files exist
        self.assertTrue((p_dir / "book_dna.json").exists())
        self.assertTrue((p_dir / "book_bible.json").exists())
        self.assertTrue((p_dir / "vocal_spaces.json").exists())
        self.assertTrue((p_dir / "sonic_bible.json").exists())
        self.assertTrue((p_dir / "character_roster.json").exists())
        self.assertTrue((p_dir / "voice_registry.json").exists())
        self.assertTrue((p_dir / "cast_lock.json").exists())
        self.assertTrue((p_dir / "translation" / "glossary.json").exists())

        # Verify 4D formant back-synchronization into BookBible
        saved_bible = BookBible.model_validate(json.loads((p_dir / "book_bible.json").read_text(encoding="utf-8")))
        geralt_ent = saved_bible.characters["Geralt"]
        self.assertEqual(geralt_ent.assigned_voice, "Fenrir")
        self.assertEqual(geralt_ent.pitch_shift_pct, -6.0)
        self.assertEqual(geralt_ent.tempo_scale, 0.98)
        self.assertIn("equalizer=f=220", geralt_ent.eq_formant)

    def test_nr_gate_06_atomic_commit_rollback_on_io_failure(self):
        """Test 3: NR-GATE-06 ensures staged files are rolled back cleanly if a write error occurs."""
        p_dir = self.temp_dir / "failing_proj"
        p_dir.mkdir(parents=True, exist_ok=True)

        book_meta = {"title": "Failing Book", "project_slug": "failing"}
        book_dna = {"literary_tradition": "TEST"}
        bible = BookBible(book_title="Failing Book")
        v_spaces = VocalSpacesManifest(project_id="proj-failing", book_title="Failing Book")

        # Force a failure by passing non-serializable object in cast_lock
        invalid_cast_lock = {"unserializable": object()}

        with self.assertRaises(IOError):
            NovelStateMaintainer.commit_master_preproduction(
                project_dir=p_dir,
                book_metadata=book_meta,
                book_dna=book_dna,
                book_bible=bible,
                vocal_spaces=v_spaces,
                roster={},
                voice_registry={},
                cast_lock=invalid_cast_lock,
            )

        # Assert no leftover .tmp files
        tmp_files = list(p_dir.glob("*.tmp*"))
        self.assertEqual(len(tmp_files), 0, f"Found leftover staging files: {tmp_files}")

    def test_preproduction_supervisor_decoupled_orchestration(self):
        """Test 4: PreProductionSupervisor delegates persistence to NovelStateMaintainer producing full lock."""
        extracted_dir = self.temp_dir / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        meta = {"title": "Decoupled Novel", "author": "Author A", "project_slug": "decoupled_novel"}
        (self.temp_dir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

        ch_text = 'Elena entered the chamber. "The stars are aligning," Elena whispered. Drake nodded. "Indeed," Drake replied.'
        (extracted_dir / "chapter_001.md").write_text(ch_text, encoding="utf-8")

        def mock_llm_room1(prompt: str, system_instruction: str = "", **kwargs) -> Any:
            if "Canonical Novel Dossier" in prompt:
                return {
                    "book_title": "Decoupled Novel",
                    "author": "Author A",
                    "literary_dna": {"tradition": "HIGH_FANTASY", "source_fidelity_tier": "STANDARD_ADULT"},
                    "characters": [
                        {"english_name": "Elena", "hindi_name": "एलेना", "gender": "female"},
                        {"english_name": "Drake", "hindi_name": "ड्रेक", "gender": "male"},
                    ],
                    "world_lore_entities": {"locations": {"Chamber": "कक्ष"}},
                }
            elif "Universal Literary DNA" in prompt or "book_dna" in prompt.lower():
                return {"literary_tradition": "HIGH_FANTASY", "source_fidelity_tier": "STANDARD_ADULT"}
            elif "Dramatis Personae" in prompt:
                return [
                    {"english_name": "Elena", "hindi_name": "एलेना", "gender": "female"},
                    {"english_name": "Drake", "hindi_name": "ड्रेक", "gender": "male"},
                ]
            elif "vocal_spaces" in prompt.lower() or "Vocal Acoustic" in system_instruction or "vocal spaces" in prompt.lower():
                return {
                    "project_id": "proj-decoupled_novel",
                    "book_title": "Decoupled Novel",
                    "spaces": {
                        "chamber": {
                            "reverb_type": "stone_vault",
                            "wet_mix": 0.18,
                            "predelay_ms": 20,
                            "decay_time_s": 1.4,
                            "proximity_staging": "conversational_close",
                            "high_shelf_damping_db": -1.5,
                        }
                    },
                }
            elif "Phonetic" in system_instruction or "lexicon" in prompt.lower():
                return {"locations": {"Chamber": "कक्ष"}, "terminology": {}}
            return {}

        supervisor = PreProductionSupervisor()
        res = supervisor.execute_preproduction(
            project_dir=self.temp_dir,
            force=True,
            call_llm_fn=mock_llm_room1,
        )

        self.assertEqual(res["status"], "MASTER_LOCKED")

        # Verify load_master_state reads and validates everything
        master_state = NovelStateMaintainer.load_master_state(self.temp_dir)
        self.assertIsNotNone(master_state)
        self.assertEqual(master_state.book_title, "Decoupled Novel")
        self.assertIn("Elena", master_state.book_bible.characters)
        self.assertIn("Drake", master_state.book_bible.characters)
        self.assertIn("chamber", master_state.vocal_spaces.spaces)

    def test_dynamic_character_locking_atomic_sync(self):
        """Test 5: discover_and_lock_character atomically updates BookBible, cast_lock, and voice_registry."""
        proj_dir = self.temp_dir / "sync_proj"
        proj_dir.mkdir(parents=True, exist_ok=True)

        bible = BookBible(project_id="proj-sync", book_title="Sync Book")
        bible.save(proj_dir)

        cast_res = NovelStateMaintainer.discover_and_lock_character(
            project_dir=proj_dir,
            speaker_name="Regis",
            gender="male",
            use_hindi=True,
            book_bible=bible,
        )

        self.assertIn("voice", cast_res)
        self.assertIn("pitch", cast_res)

        # Verify BookBible updated with 4D acoustics
        saved_bible = BookBible.load_from_project(proj_dir)
        self.assertIn("Regis", saved_bible.characters)
        regis_ent = saved_bible.characters["Regis"]
        self.assertEqual(regis_ent.assigned_voice, cast_res["voice"])
        self.assertEqual(regis_ent.tempo_scale, cast_res["speed"])

        # Verify cast_lock.json updated
        cast_locks = json.loads((proj_dir / "cast_lock.json").read_text(encoding="utf-8"))
        self.assertIn("Regis", cast_locks.get("locks", {}))


if __name__ == "__main__":
    unittest.main()
