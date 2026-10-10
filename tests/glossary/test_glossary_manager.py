#!/usr/bin/env python3
"""
Test Suite: Room 1.5 Standalone Glossary & Chapter Metadata Subsystem.
======================================================================
Tests:
1. Data contracts and multi-consumer projections (Translation, Dramaturgy, Scripting).
2. Zero-token fast path in ChapterLexicalScanner.
3. Tri-Partite classification and alias unification in GlossaryClassifier.
4. End-to-end GlossaryManager synchronization with BookBible and cast_lock.json.
5. ModelGateway routing and fail-closed compliance.
6. Backward compatibility for legacy ChapterEntityHarvester shim.
"""

import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

from audiobook_factory.glossary.contracts import (
    EntityCategory,
    ChapterEntity,
    ChapterGlossary,
)
from audiobook_factory.glossary.scanner import (
    ChapterLexicalScanner,
    CandidateEntity,
)
from audiobook_factory.glossary.classifier import (
    GlossaryClassifier,
    TRI_PARTITE_SYSTEM_PROMPT,
)
from audiobook_factory.glossary.gateway_bridge import (
    execute_glossary_llm,
)
from audiobook_factory.glossary.manager import (
    GlossaryManager,
)
from audiobook_factory.metadata.book_bible import BookBible, BookEntity
from audiobook_factory.translation.entity_discovery import (
    ChapterEntityHarvester,
    DiscoveredEntity,
    EntityDiscoveryEngine,
)


class TestGlossarySubsystem(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_glossary_subsystem_"))
        self._prev_mock_offline = os.environ.get("MOCK_OFFLINE")
        os.environ["MOCK_OFFLINE"] = "1"

    def tearDown(self):
        if self._prev_mock_offline is not None:
            os.environ["MOCK_OFFLINE"] = self._prev_mock_offline
        else:
            os.environ.pop("MOCK_OFFLINE", None)
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_contracts_and_multi_consumer_projections(self):
        """Tests ChapterEntity and ChapterGlossary projections for Translation, Scripting, and Dramaturgy."""
        entity1 = ChapterEntity(
            canonical_id="lord_corwin",
            english_name="Lord Corwin",
            hindi_name="लॉर्ड कॉरविन",
            category="PROPER_NAME",
            aliases=["Corwin", "Silver Falcon", "सिल्वर फाल्कन"],
            gender="male",
            voice_style="Aristocratic, deep",
            sociolect_archetype="ARISTOCRATIC",
        )
        entity2 = ChapterEntity(
            canonical_id="the_stranger",
            english_name="The Stranger",
            hindi_name="अजनबी",
            category="OCCUPATIONAL_ROLE",
            aliases=["Traveller"],
            gender="male",
        )

        glossary = ChapterGlossary(
            chapter_num=3,
            chapter_id="chapter_003",
            entities={"Lord Corwin": entity1, "The Stranger": entity2},
            locations={"Kaer Morhen": "काएर मोर्हेन"},
            terminology={"Silver Sword": "चांदी की तलवार"},
        )

        # 1. Translation Projection (flat en -> hi map)
        trans_map = glossary.to_translation_glossary()
        self.assertEqual(trans_map["Lord Corwin"], "लॉर्ड कॉरविन")
        self.assertEqual(trans_map["Silver Falcon"], "लॉर्ड कॉरविन")
        self.assertEqual(trans_map["The Stranger"], "अजनबी")
        self.assertEqual(trans_map["Kaer Morhen"], "काएर मोर्हेन")
        self.assertEqual(trans_map["Silver Sword"], "चांदी की तलवार")

        # 2. Scripting Roster Projection
        roster = glossary.to_scripting_roster(use_hindi=True)
        self.assertIn("characters", roster)
        self.assertIn("लॉर्ड कॉरविन", roster["characters"])
        corwin_roster = roster["characters"]["लॉर्ड कॉरविन"]
        self.assertIn("Silver Falcon", corwin_roster["aliases"])
        self.assertEqual(corwin_roster["gender"], "male")

        # 3. Dramaturgy Known Characters
        dram_chars = glossary.to_dramaturgy_characters()
        self.assertIn("Lord Corwin", dram_chars)
        self.assertIn("लॉर्ड कॉरविन", dram_chars)
        self.assertIn("The Stranger", dram_chars)

        # 4. Atomic Persistence
        art_path = self.temp_dir / "glossary" / "chapter_003_glossary.json"
        glossary.save_to_file(art_path)
        self.assertTrue(art_path.exists())
        loaded = ChapterGlossary.load_from_file(art_path)
        self.assertEqual(loaded.chapter_num, 3)
        self.assertEqual(len(loaded.entities), 2)
        self.assertEqual(loaded.version_hash, glossary.version_hash)

    def test_02_scanner_zero_token_fast_path(self):
        """Verifies scanner bypasses candidates if all entities are already cataloged in BookBible."""
        bible = BookBible(book_title="Test Fantasy")
        bible.characters["Geralt"] = BookEntity(
            canonical_id="geralt",
            english_name="Geralt",
            hindi_name="गेराल्ट",
            aliases=["The Witcher", "White Wolf"],
        )
        bible.locations["Wyzima"] = "विज़िमा"

        # Text mentioning only known entities and common words
        text_known_only = (
            "The morning was cold. Geralt walked through the streets of Wyzima. "
            "He looked around. Geralt drew his breath. Wyzima was silent."
        )

        candidates = ChapterLexicalScanner.scan_chapter_text(
            text=text_known_only,
            book_bible=bible,
            min_frequency=2,
        )
        # All mentioned entities are known -> zero candidates returned -> 0 LLM tokens consumed!
        self.assertEqual(len(candidates), 0)

        # Text introducing an uncataloged character and moniker
        text_with_new_entity = (
            text_known_only + "\n\n"
            "Baron Valerius stepped into the tavern. Baron Valerius signaled to Geralt. "
            "The Night Raven was waiting in the shadows. The Night Raven spoke quietly."
        )

        candidates_new = ChapterLexicalScanner.scan_chapter_text(
            text=text_with_new_entity,
            book_bible=bible,
            min_frequency=2,
        )
        cand_names = [c.name for c in candidates_new]
        self.assertIn("Baron Valerius", cand_names)
        self.assertIn("Night Raven", cand_names)

    def test_03_classifier_tri_partite_taxonomy(self):
        """Verifies GlossaryClassifier correctly maps Proper Names, Heraldic Monikers, and Roles."""
        candidates = [
            CandidateEntity(name="Baron Valerius", frequency=2),
            CandidateEntity(name="Night Raven", frequency=2),
            CandidateEntity(name="The Innkeeper", frequency=3),
        ]

        def mock_llm_classify(prompt: str, system_instruction: str = "", **kwargs) -> Any:
            self.assertIn("TRI-PARTITE", system_instruction)
            return {
                "characters": [
                    {
                        "english_name": "Baron Valerius",
                        "hindi_name": "बैरोन वालेरियस",
                        "entity_type": "PROPER_NAME",
                        "aliases": ["Valerius"],
                        "gender": "male",
                        "voice_style": "Authoritative and noble",
                        "hindustani_archetype": "ARISTOCRATIC",
                    },
                    {
                        "english_name": "Night Raven",
                        "hindi_name": "नाइट रेवेन",
                        "entity_type": "HERALDIC_MONIKER",
                        "aliases": ["Shadow Spy"],
                        "gender": "female",
                        "voice_style": "Whispering, cold",
                    },
                    {
                        "english_name": "The Innkeeper",
                        "hindi_name": "सरायवाला",
                        "entity_type": "OCCUPATIONAL_ROLE",
                        "aliases": ["Tavern Owner"],
                        "gender": "male",
                    },
                ],
                "locations_and_terms": {
                    "Black Lake": "ब्लैक लेक",
                    "Bloodstone": "ब्लडस्टोन",
                },
            }

        entities, locations, terms = GlossaryClassifier.classify_candidates(
            candidates=candidates,
            chapter_text="Sample excerpt text.",
            chapter_num=2,
            call_llm_fn=mock_llm_classify,
        )

        self.assertEqual(len(entities), 3)
        valerius = next(e for e in entities if e.english_name == "Baron Valerius")
        self.assertEqual(valerius.hindi_name, "बैरोन वालेरियस")
        self.assertEqual(valerius.category, "PROPER_NAME")

        raven = next(e for e in entities if e.english_name == "Night Raven")
        self.assertEqual(raven.hindi_name, "नाइट रेवेन")
        self.assertEqual(raven.category, "HERALDIC_MONIKER")

        innkeeper = next(e for e in entities if e.english_name == "The Innkeeper")
        self.assertEqual(innkeeper.hindi_name, "सरायवाला")
        self.assertEqual(innkeeper.category, "OCCUPATIONAL_ROLE")

        self.assertIn("Black Lake", locations)
        self.assertIn("Bloodstone", terms)

    def test_04_glossary_manager_end_to_end_and_state_sync(self):
        """Tests GlossaryManager single-pass execution, BookBible update, and cast_lock synchronization."""
        # Initialize project directory
        proj_dir = self.temp_dir / "proj_novel"
        proj_dir.mkdir(parents=True)
        bible = BookBible(book_title="Chronicles of Aldoria")
        bible.save(proj_dir)

        chapter_text = (
            "Commander Thorne stood on the ramparts of Fort Silver. "
            "Commander Thorne watched the snow falling. "
            "\"Keep watch,\" Thorne said. "
            "Lieutenant Sarah approached Commander Thorne with a sealed letter. "
            "Lieutenant Sarah waited in silence."
        )

        def mock_llm_sync(prompt: str, system_instruction: str = "", **kwargs) -> Any:
            return {
                "characters": [
                    {
                        "english_name": "Thorne",
                        "hindi_name": "थोर्न",
                        "entity_type": "PROPER_NAME",
                        "aliases": ["Commander Thorne"],
                        "gender": "male",
                        "voice_style": "Gruff, stern",
                        "hindustani_archetype": "MILITARY_OFFICER",
                    },
                    {
                        "english_name": "Sarah",
                        "hindi_name": "सारा",
                        "entity_type": "PROPER_NAME",
                        "aliases": ["Lieutenant Sarah"],
                        "gender": "female",
                        "voice_style": "Crisp, precise",
                    },
                ],
                "locations_and_terms": {
                    "Fort Silver": "फोर्ट सिल्वर",
                },
            }

        glossary = GlossaryManager.scan_and_sync_chapter(
            chapter_text=chapter_text,
            project_dir=proj_dir,
            chapter_num=1,
            call_llm_fn=mock_llm_sync,
            force_classification=True,
        )

        self.assertIsInstance(glossary, ChapterGlossary)
        self.assertEqual(glossary.chapter_num, 1)
        self.assertIn("Thorne", glossary.entities)
        self.assertIn("Sarah", glossary.entities)
        self.assertIn("Fort Silver", glossary.locations)

        # 1. Verify BookBible was updated and saved
        reloaded_bible = BookBible.load_from_project(proj_dir)
        self.assertIn("Thorne", reloaded_bible.characters)
        self.assertIn("Sarah", reloaded_bible.characters)
        self.assertIn("Fort Silver", reloaded_bible.locations)

        # 2. Verify cast_lock.json was updated with dynamic voice allocation
        cast_lock_file = proj_dir / "cast_lock.json"
        self.assertTrue(cast_lock_file.exists())
        cast_data = json.loads(cast_lock_file.read_text(encoding="utf-8"))
        self.assertIn("locks", cast_data)
        self.assertIn("Thorne", cast_data["locks"])
        self.assertIn("Sarah", cast_data["locks"])
        self.assertIn("voice_id", cast_data["locks"]["Thorne"])

        # 3. Verify durable chapter glossary file was saved
        chapter_glossary_file = proj_dir / "glossary" / "chapter_001_glossary.json"
        self.assertTrue(chapter_glossary_file.exists())

        # 4. Verify translation and scripting export methods
        trans_glossary = GlossaryManager.export_for_translation(1, proj_dir)
        self.assertEqual(trans_glossary["Thorne"], "थोर्न")
        self.assertEqual(trans_glossary["Commander Thorne"], "थोर्न")
        self.assertEqual(trans_glossary["Fort Silver"], "फोर्ट सिल्वर")

        script_roster = GlossaryManager.export_for_scripting(1, proj_dir, use_hindi=True)
        self.assertIn("थोर्न", script_roster["characters"])
        self.assertIn("Commander Thorne", script_roster["characters"]["थोर्न"]["aliases"])

    def test_05_gateway_bridge_compliance_and_fail_closed(self):
        """Verifies execute_glossary_llm fails closed when ModelGateway is unavailable."""
        with patch.dict(os.environ, {"MOCK_OFFLINE": "0", "GEMINI_API_KEY": ""}):
            with patch("audiobook_factory.core.models.gateway.get_model_gateway", side_effect=ImportError("No gateway")):
                with self.assertRaises(RuntimeError) as ctx:
                    execute_glossary_llm(prompt="Test Prompt", json_mode=True)
                self.assertIn("ModelGateway", str(ctx.exception))
                self.assertIn("strictly forbidden", str(ctx.exception))

    def test_06_backward_compatibility_entity_discovery_shim(self):
        """Verifies legacy ChapterEntityHarvester and EntityDiscoveryEngine work via the shim."""
        proj_dir = self.temp_dir / "proj_legacy"
        proj_dir.mkdir(parents=True)
        bible = BookBible(book_title="Legacy Test")
        bible.save(proj_dir)

        chapter_text = (
            "Geralt drew his steel blade. The Witcher confronted the beast. "
            "Geralt shouted to Yennefer."
        )

        def mock_llm_legacy(prompt: str, system_instruction: str = "", **kwargs) -> Any:
            return {
                "characters": [
                    {
                        "english_name": "Geralt",
                        "hindi_name": "गेराल्ट",
                        "entity_type": "PROPER_NAME",
                        "aliases": ["The Witcher"],
                        "gender": "male",
                    }
                ],
                "locations_and_terms": {},
            }

        legacy_glossary = ChapterEntityHarvester.harvest_and_sync(
            chapter_text=chapter_text,
            project_dir=proj_dir,
            chapter_num=1,
            call_llm_fn=mock_llm_legacy,
        )

        self.assertIsInstance(legacy_glossary, dict)
        self.assertIn("characters", legacy_glossary)
        char_names = [c["english_name"] for c in legacy_glossary["characters"]]
        self.assertIn("Geralt", char_names)

        # Verify EntityDiscoveryEngine compatibility
        engine_res = EntityDiscoveryEngine.discover_entities_from_text(
            text=chapter_text,
            book_bible=bible,
            chapter_num=1,
            call_llm_fn=mock_llm_legacy,
        )
        self.assertIsInstance(engine_res, list)

    def test_07_classifier_unwrapped_list_recovery(self):
        """Verifies that GlossaryClassifier safely parses unwrapped JSON lists without AttributeError."""
        from audiobook_factory.glossary.classifier import GlossaryClassifier
        from audiobook_factory.glossary.scanner import CandidateEntity

        classifier = GlossaryClassifier()
        candidates = [CandidateEntity(name="Jean-Luc", frequency=3)]

        # Mock LLM returning a raw JSON list directly (not a dict with "characters")
        def mock_llm_raw_list(prompt, **kwargs):
            return [
                {
                    "english_name": "Jean-Luc",
                    "hindi_name": "जीन-ल्यूक",
                    "entity_type": "PROPER_NAME",
                    "aliases": ["Captain"],
                    "gender": "male",
                }
            ]

        entities, locations, terminology = classifier.classify_candidates(
            chapter_text="Captain Jean-Luc commanded the ship.",
            candidates=candidates,
            chapter_num=1,
            call_llm_fn=mock_llm_raw_list,
        )

        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].english_name, "Jean-Luc")
        self.assertEqual(entities[0].hindi_name, "जीन-ल्यूक")

    def test_08_scanner_hyphenated_entities(self):
        """Verifies that ChapterLexicalScanner detects hyphenated proper names as single entities."""
        from audiobook_factory.glossary.scanner import ChapterLexicalScanner

        scanner = ChapterLexicalScanner()
        text = "Captain Jean-Luc Picard spoke with Silver-Falcon in the courtyard."

        candidates = scanner.scan_chapter_text(text=text, min_frequency=1)
        candidate_names = [c.name for c in candidates]

        self.assertIn("Captain Jean-Luc Picard", candidate_names)
        self.assertIn("Silver-Falcon", candidate_names)


if __name__ == "__main__":
    unittest.main()

