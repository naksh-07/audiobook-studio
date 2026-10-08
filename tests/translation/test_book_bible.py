#!/usr/bin/env python3
"""
Unit tests for Persistent Canonical Book Bible and Legacy Projection.
"""

import unittest
import tempfile
import json
from pathlib import Path

from audiobook_factory.translation.book_bible import BookBible, BookEntity, DynamicRelationship


class TestBookBible(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_import_legacy_glossary_and_save_projection(self):
        # Create legacy glossary
        trans_dir = self.project_dir / "translation"
        trans_dir.mkdir(parents=True, exist_ok=True)
        glossary_file = trans_dir / "glossary.json"

        sample_glossary = {
            "characters": [
                {
                    "english_name": "Geralt of Rivia",
                    "hindi_name": "रिविया का गेराल्ट",
                    "gender": "male",
                    "voice_style": "gruff, calm",
                    "recommended_pronoun_level": "tum",
                    "hindustani_archetype": "COLD_CYNIC",
                }
            ],
            "relationships": [
                {"from": "Geralt", "to": "Dandelion", "level": "tum"}
            ],
            "locations_and_terms": {
                "Witcher": "विचर",
                "Temple of Melitele": "मेलीतेले का मंदिर",
                "Silver sword": "चाँदी की तलवार",
            },
            "general_tone": "Cinematic Hindustani",
        }

        with open(glossary_file, "w", encoding="utf-8") as f:
            json.dump(sample_glossary, f, ensure_ascii=False)

        # Load BookBible
        bible = BookBible.load_from_project(self.project_dir)
        self.assertIn("Geralt of Rivia", bible.characters)
        self.assertEqual(bible.characters["Geralt of Rivia"].hindi_name, "रिविया का गेराल्ट")
        self.assertEqual(bible.characters["Geralt of Rivia"].sociolect_archetype, "COLD_CYNIC")
        self.assertIn("Witcher", bible.terminology)
        self.assertEqual(bible.terminology["Witcher"], "विचर")

        # Save and verify both book_bible.json and glossary.json projection exist
        bible.save(self.project_dir)
        self.assertTrue((self.project_dir / "book_bible.json").exists())
        self.assertTrue(glossary_file.exists())

        # Verify legacy projection contents
        with open(glossary_file, "r", encoding="utf-8") as f:
            projected = json.load(f)
        self.assertEqual(len(projected["characters"]), 1)
        self.assertEqual(projected["characters"][0]["english_name"], "Geralt of Rivia")

    def test_02_version_hash_determinism(self):
        bible = BookBible(book_title="Test Book", author="Test Author")
        bible.characters["Geralt"] = BookEntity(
            canonical_id="geralt",
            english_name="Geralt",
            hindi_name="गेराल्ट",
        )
        h1 = bible.get_version_hash()
        h2 = bible.get_version_hash()
        self.assertEqual(h1, h2)

        # Modify entity and verify hash changes
        bible.characters["Geralt"].hindi_name = "रिविया का गेराल्ट"
        h3 = bible.get_version_hash()
        self.assertNotEqual(h1, h3)

    def test_03_propose_entity_auto_commit_and_flag_conflicts(self):
        bible = BookBible(book_title="Test Book")
        bible.characters["Foltest"] = BookEntity(
            canonical_id="foltest",
            english_name="Foltest",
            hindi_name="फ़ोल्टेस्ट",
            is_canonical=True,
        )

        # Non-conflicting new character with high confidence -> auto-commit
        new_char = BookEntity(
            canonical_id="ostrit",
            english_name="Ostrit",
            hindi_name="ओस्ट्रिट",
            confidence=0.9,
        )
        success = bible.propose_new_entity(new_char, chapter_num=1)
        self.assertTrue(success)
        self.assertIn("Ostrit", bible.characters)

        # Conflicting spelling for existing character -> flag conflict
        conflicting = BookEntity(
            canonical_id="foltest",
            english_name="Foltest",
            hindi_name="फोल्टेस्ट_गलत",
            confidence=0.95,
        )
        success_conflict = bible.propose_new_entity(conflicting, chapter_num=2)
        self.assertFalse(success_conflict)
        self.assertEqual(len(bible.flagged_conflicts), 1)
        self.assertEqual(bible.flagged_conflicts[0].conflict_type, "name_spelling")
        # Canonical spelling preserved
        self.assertEqual(bible.characters["Foltest"].hindi_name, "फ़ोल्टेस्ट")

    def test_04_full_chapter_entity_harvesting(self):
        """
        Verify that EntityDiscoveryEngine and ChapterEntityHarvester scan 100% of chapter text
        and discover characters introduced late in long chapters (e.g. at character 35,000+).
        """
        from audiobook_factory.translation.entity_discovery import EntityDiscoveryEngine, ChapterEntityHarvester

        filler_intro = "The riders rode through the dark forest under the silver moon.\n\n" * 500  # ~32,000 characters
        late_scene = "Near the midnight campfire, Lord Malakar unsheathed his blade. Lord Malakar spoke with his commander."
        full_chapter = filler_intro + late_scene  # > 32,000 characters

        bible = BookBible(book_title="Test Epic")
        discovered = EntityDiscoveryEngine.discover_entities_from_text(
            text=full_chapter,
            book_bible=bible,
            chapter_num=1,
            call_llm_fn=None,
        )
        discovered_names = [d.name for d in discovered]
        self.assertIn("Lord Malakar", discovered_names, "Entity at char 32,000+ must be discovered by full chapter scanning")

        # Test ChapterEntityHarvester syncs the late-discovered character to bible
        ChapterEntityHarvester.harvest_and_sync(
            chapter_text=full_chapter,
            project_dir=self.project_dir,
            chapter_num=1,
            global_glossary=None,
            call_llm_fn=lambda prompt, system_instruction, json_mode=True: {
                "characters": [
                    {
                        "english_name": "Lord Malakar",
                        "hindi_name": "लॉर्ड मालाकार",
                        "entity_type": "PROPER_NAME",
                        "aliases": ["The Shadow Commander"],
                        "gender": "male",
                    }
                ],
                "locations_and_terms": {},
            },
        )
        updated_bible = BookBible.load_from_project(self.project_dir)
        self.assertIn("Lord Malakar", updated_bible.characters)
        self.assertEqual(updated_bible.characters["Lord Malakar"].hindi_name, "लॉर्ड मालाकार")


if __name__ == "__main__":
    unittest.main()
