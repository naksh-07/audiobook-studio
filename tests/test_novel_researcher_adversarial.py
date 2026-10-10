#!/usr/bin/env python3
"""
Adversarial Test Suite: Novel Researcher Architecture System.
Tests edge cases, malformed LLM responses, unicode quirks, empty dialogue strings,
extreme 4D formant ratios, and corrupted metadata recovery.
"""

import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any, List

from audiobook_factory.preproduction.lexical_scanner import (
    LexicalCorpusScanner,
    LexicalCorpusIndex,
)
from audiobook_factory.preproduction.vocal_acoustic_director import (
    VocalAcousticDirector,
    VocalSpacesManifest,
    VocalSpaceProfile,
)
from audiobook_factory.translation.book_bible import BookEntity
from audiobook_factory.translation.entity_discovery import (
    ChapterEntityHarvester,
    DiscoveredEntity,
    EntityDiscoveryEngine,
)
from audiobook_factory.character_caster import CharacterCaster


class TestNovelResearcherAdversarial(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_novel_researcher_adversarial_"))
        self._prev_mock_offline = os.environ.get("MOCK_OFFLINE")
        os.environ["MOCK_OFFLINE"] = "1"

    def tearDown(self):
        if self._prev_mock_offline is not None:
            os.environ["MOCK_OFFLINE"] = self._prev_mock_offline
        else:
            os.environ.pop("MOCK_OFFLINE", None)
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_lexical_scanner_unicode_and_empty_dialogue(self):
        """Tests 0-word dialogue, Unicode variations, and empty paragraphs in LexicalCorpusScanner."""
        chapters = [
            (1, '"" said Geralt.\n\n"   " whispered Yennefer.\n\n"Hold!" shouted Baron Valerius.'),
            (2, 'गेराल्ट said nothing.\n\n"We move at dawn," said Geralt.'),
        ]

        idx = LexicalCorpusScanner.scan_chapters(chapters)
        self.assertIsInstance(idx, LexicalCorpusIndex)
        self.assertGreaterEqual(idx.get_mention_count("Geralt"), 1)
        self.assertGreaterEqual(idx.get_mention_count("Valerius"), 1)

    def test_vocal_filter_complex_extreme_pitch_ratio(self):
        """Tests that extreme pitch shifts (-100% or +300%) do not crash with ZeroDivisionError."""
        director = VocalAcousticDirector()
        manifest = VocalSpacesManifest(
            project_id="proj-extreme",
            book_title="Extreme Pitch Novel",
            spaces={"hall": VocalSpaceProfile()},
        )

        entity_zero = BookEntity(
            canonical_name="Ghost",
            english_name="Ghost",
            pitch_shift_pct=-100.0,  # Could cause ratio = 0 without clamping
        )

        filter_str = director.build_vocal_filter_complex(
            character_entity=entity_zero,
            space_name="hall",
            spaces_manifest=manifest,
        )
        self.assertIn("highpass=f=60", filter_str)
        self.assertIn("asetrate=", filter_str)

    def test_entity_discovery_dict_wrapped_llm_response(self):
        """Tests that ChapterEntityHarvester handles dict-wrapped LLM JSON (e.g. {'entities': [...]})."""
        from audiobook_factory.translation.book_bible import BookBible
        bible = BookBible(project_id="proj-adversarial", book_title="Test Title")
        chapter_text = "Eskel walked into the courtyard. Eskel drew his silver sword."

        def mock_dict_llm(prompt: str, system_instruction: str = "", **kwargs):
            return {
                "entities": [
                    {
                        "name": "Eskel",
                        "category": "character",
                        "suggested_devanagari": "एस्केल",
                        "confidence": 0.95,
                    }
                ]
            }

        discovered = EntityDiscoveryEngine.discover_entities_from_text(
            text=chapter_text,
            book_bible=bible,
            chapter_num=1,
            call_llm_fn=mock_dict_llm,
        )
        self.assertEqual(len(discovered), 1)
        self.assertEqual(discovered[0].name, "Eskel")
        self.assertEqual(discovered[0].suggested_devanagari, "एस्केल")
        self.assertEqual(discovered[0].confidence, 0.95)

    def test_character_caster_corrupted_json_recovery(self):
        """Tests that CharacterCaster recovers gracefully when JSON files contain malformed types."""
        project_dir = self.temp_dir / "corrupted_proj"
        project_dir.mkdir(parents=True, exist_ok=True)

        # Write corrupted non-dict JSON
        (project_dir / "character_roster.json").write_text("[]", encoding="utf-8")
        (project_dir / "voice_registry.json").write_text('"corrupted_string"', encoding="utf-8")
        (project_dir / "cast_lock.json").write_text("null", encoding="utf-8")

        res = CharacterCaster.cast_single_speaker(
            project_dir=project_dir,
            speaker_name="Triss Merigold",
            gender="female",
            use_hindi=True,
        )
        self.assertIn("voice", res)
        self.assertIn("pitch", res)
        self.assertIn("speed", res)


    def test_state_maintainer_corrupt_files_load(self):
        """Tests partial corrupt files during load_master_state()."""
        from audiobook_factory.metadata.state_maintainer import NovelStateMaintainer
        proj_dir = self.temp_dir / "proj_corrupt"
        proj_dir.mkdir(parents=True)
        (proj_dir / "book_bible.json").write_text("{corrupt", encoding="utf-8")
        (proj_dir / "cast_lock.json").write_text("{}", encoding="utf-8")
        (proj_dir / "vocal_spaces.json").write_text("{}", encoding="utf-8")
        
        state = NovelStateMaintainer.load_master_state(proj_dir)
        self.assertIsNone(state)

    def test_state_maintainer_partial_files_commit(self):
        """Tests attempting atomic commit when some target files exist and others do not."""
        from audiobook_factory.metadata.state_maintainer import NovelStateMaintainer, MasterPreProductionState
        from audiobook_factory.metadata.book_bible import BookBible
        from audiobook_factory.preproduction.vocal_acoustic_director import VocalSpacesManifest
        
        proj_dir = self.temp_dir / "proj_partial"
        proj_dir.mkdir(parents=True)
        (proj_dir / "book_bible.json").write_text('{"old": "data"}', encoding="utf-8")
        
        bible = BookBible(book_title="Test Partial")
        v_spaces = VocalSpacesManifest(project_id="p1", book_title="Test Partial")
        
        state = NovelStateMaintainer.commit_master_preproduction(
            proj_dir, {}, {}, bible, v_spaces, {}, {}, {}
        )
        self.assertIsInstance(state, MasterPreProductionState)
        self.assertTrue((proj_dir / "cast_lock.json").exists())
        self.assertTrue((proj_dir / "vocal_spaces.json").exists())

    def test_state_maintainer_idempotency_discovery(self):
        """Tests idempotency of dynamic character discovery and locking."""
        from audiobook_factory.metadata.state_maintainer import NovelStateMaintainer
        proj_dir = self.temp_dir / "proj_idempotency"
        proj_dir.mkdir(parents=True)
        
        res1 = NovelStateMaintainer.discover_and_lock_character(proj_dir, "Geralt", gender="male")
        res2 = NovelStateMaintainer.discover_and_lock_character(proj_dir, "Geralt", gender="male")
        self.assertEqual(res1["voice"], res2["voice"])
        self.assertEqual(res1["pitch"], res2["pitch"])

    def test_state_maintainer_invalid_dir(self):
        """Tests NovelStateMaintainer with missing metadata.json logic or invalid directory paths."""
        from audiobook_factory.metadata.state_maintainer import NovelStateMaintainer
        from audiobook_factory.metadata.book_bible import BookBible
        from audiobook_factory.preproduction.vocal_acoustic_director import VocalSpacesManifest
        import sys

        bible = BookBible(book_title="Readonly")
        v_spaces = VocalSpacesManifest(project_id="ro", book_title="Readonly")

        if sys.platform == "win32":
            # On Windows, os.chmod does not affect directory write permissions.
            # Using an existing file as proj_dir triggers NotADirectoryError / FileExistsError on subpath creation.
            proj_dir = self.temp_dir / "proj_not_a_dir.txt"
            proj_dir.write_text("I am a file, not a directory", encoding="utf-8")
        else:
            proj_dir = self.temp_dir / "proj_readonly"
            proj_dir.mkdir(parents=True)
            proj_dir.chmod(0o555)

        try:
            with self.assertRaises(Exception):
                NovelStateMaintainer.commit_master_preproduction(
                    proj_dir, {}, {}, bible, v_spaces, {}, {}, {}
                )
        finally:
            if sys.platform != "win32" and proj_dir.exists():
                proj_dir.chmod(0o777)

if __name__ == "__main__":
    unittest.main()
