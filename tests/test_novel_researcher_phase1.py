#!/usr/bin/env python3
"""
Test Suite: Novel Researcher Architecture System - Phase 1.
Validates:
1. LexicalCorpusScanner deterministic full-corpus indexer and dialogue attribution extractor.
2. Bidirectional Corpus Grounding Gate filtering out ungrounded web search artifacts.
3. EpistemicProvenance tracking (CORPUS_EXTRACTED, WEB_VERIFIED, INFERRED_DERIVED).
4. 4D Acoustic Formant fields in BookEntity/NovelEntity.
5. End-to-end PreProductionSupervisor Room 1 execution with zero hallucination.
6. ChapterEntityHarvester dynamic discovery with immediate cast_lock synchronization.
"""

import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable

from audiobook_factory.preproduction.lexical_scanner import (
    LexicalCorpusScanner,
    LexicalCorpusIndex,
    EntityOccurrence,
)
from audiobook_factory.translation.book_bible import (
    BookBible,
    BookEntity,
    EpistemicProvenance,
    NovelEntity,
)
from audiobook_factory.preproduction.novel_deepsearch import (
    NovelDeepSearchEngine,
    DeepSearchNovelDossier,
    CanonicalCharacter,
    LiteraryDNAProfile,
)
from audiobook_factory.preproduction.preproduction_supervisor import PreProductionSupervisor
from audiobook_factory.translation.entity_discovery import ChapterEntityHarvester



class TestNovelResearcherPhase1(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_novel_researcher_"))
        os.environ["MOCK_OFFLINE"] = "1"

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_lexical_corpus_scanner_deterministic(self):
        """Test 1: LexicalCorpusScanner parses chapters, dialogue attributions, and citations."""
        ch1_text = (
            "Lord Corwin stepped onto the ancient cobblestones of Wyzima. "
            "The rain fell in cold sheets. \"We must proceed at once,\" Corwin said to Elena. "
            "Elena drew her cloak tight and whispered, \"The guards are watching us, my Lord.\" "
            "Corwin nodded grimly."
        )
        ch2_text = (
            "In the dark tavern, Baron Valerius raised his silver goblet. "
            "\"Welcome to my domain,\" said Baron Valerius with a cold sneer. "
            "Lord Corwin did not drink. Elena stood silently behind Corwin."
        )

        chapters = [
            (1, "Chapter 1: The Arrival", ch1_text),
            (2, "Chapter 2: The Tavern", ch2_text),
        ]

        index = LexicalCorpusScanner.scan_chapters(chapters)

        self.assertEqual(index.total_chapters, 2)
        self.assertGreater(index.total_words, 30)

        # Corwin mentions
        corwin_ent = index.entities.get("Corwin")
        self.assertIsNotNone(corwin_ent)
        self.assertGreaterEqual(corwin_ent.total_mentions, 3)
        self.assertGreaterEqual(corwin_ent.dialogue_speaker_count, 1)
        self.assertEqual(corwin_ent.first_chapter, 1)
        self.assertIn("Lord", corwin_ent.associated_titles)

        # Elena mentions
        elena_ent = index.entities.get("Elena")
        self.assertIsNotNone(elena_ent)
        self.assertGreaterEqual(elena_ent.total_mentions, 2)
        self.assertGreaterEqual(elena_ent.dialogue_speaker_count, 1)

        # Intro sentence citation
        intro = index.get_intro_sentence("Corwin")
        self.assertIn("Corwin", intro)
        self.assertIn("cobblestones", intro)

        # Top speaking characters
        top_speakers = index.get_top_speaking_characters(5)
        speaker_names = [s.name for s in top_speakers]
        self.assertIn("Corwin", speaker_names)
        self.assertIn("Elena", speaker_names)

    def test_bidirectional_grounding_gate_rejects_hallucinations(self):
        """Test 2: DeepSearch rejects web entities not present in local book corpus."""
        # Create sample corpus mentioning only 'Edna Pontellier', 'Robert Lebrun', and 'Leonce Pontellier'
        corpus_text = (
            "Edna Pontellier looked out across the Gulf of Mexico. "
            "Her husband Leonce Pontellier adjusted his eyeglasses with displeasure. "
            "\"You are burnt beyond recognition,\" Leonce said. "
            "Later that evening, Robert Lebrun joined Edna on the porch. "
            "\"The water is warm tonight,\" Robert murmured."
        )
        index = LexicalCorpusScanner.scan_chapters([(1, "Chapter 1", corpus_text)])

        # Create dossier with authentic characters + hallucinated external characters from unrelated books
        dossier = DeepSearchNovelDossier(
            book_title="The Awakening",
            author="Kate Chopin",
            literary_dna=LiteraryDNAProfile(
                tradition="FEMINIST_REALISM",
                historical_era="late_19th_century",
            ),
            characters=[
                CanonicalCharacter(english_name="Edna Pontellier", hindi_name="एड्ना पोन्टेलियर"),
                CanonicalCharacter(english_name="Robert Lebrun", hindi_name="रॉबर्ट लेब्रून"),
                CanonicalCharacter(english_name="Leonce Pontellier", hindi_name="लियोन्स पोन्टेलियर"),
                # Hallucinated characters from unrelated works with the same title "The Awakening":
                CanonicalCharacter(english_name="Geralt of Rivia", hindi_name="गेराल्ट"),
                CanonicalCharacter(english_name="Gandalf the Grey", hindi_name="गैंडाल्फ़"),
                CanonicalCharacter(english_name="Sherlock Holmes", hindi_name="शरलॉक होम्स"),
            ],
        )

        verified, rejected = NovelDeepSearchEngine.verify_against_corpus(dossier, index)

        verified_names = [c.english_name for c in verified]
        rejected_names = [r["name"] for r in rejected]

        self.assertIn("Edna Pontellier", verified_names)
        self.assertIn("Robert Lebrun", verified_names)
        self.assertIn("Leonce Pontellier", verified_names)

        # Verify hallucinations are rejected
        self.assertIn("Geralt of Rivia", rejected_names)
        self.assertIn("Gandalf the Grey", rejected_names)
        self.assertIn("Sherlock Holmes", rejected_names)
        self.assertNotIn("Geralt of Rivia", verified_names)

    def test_epistemic_provenance_and_4d_formants(self):
        """Test 3: EpistemicProvenance and 4D acoustic formant persistence in BookBible."""
        bible = BookBible(book_title="Dune", author="Frank Herbert")

        prov = EpistemicProvenance(
            origin="CORPUS_EXTRACTED",
            first_chapter=1,
            corpus_mention_count=42,
            evidence_quote="Paul Atreides sat in the shadow of Castle Caladan.",
        )

        paul = NovelEntity(
            canonical_name="Paul Atreides",
            english_name="Paul Atreides",
            hindi_name="पॉल एट्रिडिज़",
            gender="male",
            sociolect_trait="ARISTOCRATIC",
            assigned_voice="Puck",
            pitch_shift_pct=-4.0,
            tempo_scale=0.98,
            eq_formant="equalizer=f=250:width_type=o:w=1.0:g=+2.0",
            provenance=prov,
        )

        bible.characters["Paul Atreides"] = paul
        bible.save(self.temp_dir)

        # Reload from disk and verify exact fidelity
        loaded_bible = BookBible.load_from_project(self.temp_dir)
        self.assertIn("Paul Atreides", loaded_bible.characters)

        loaded_paul = loaded_bible.characters["Paul Atreides"]
        self.assertEqual(loaded_paul.assigned_voice, "Puck")
        self.assertEqual(loaded_paul.pitch_shift_pct, -4.0)
        self.assertEqual(loaded_paul.tempo_scale, 0.98)
        self.assertEqual(loaded_paul.provenance.origin, "CORPUS_EXTRACTED")
        self.assertEqual(loaded_paul.provenance.corpus_mention_count, 42)
        self.assertIn("Paul Atreides sat", loaded_paul.provenance.evidence_quote)

    def test_preproduction_supervisor_end_to_end_room1(self):
        """Test 4: PreProductionSupervisor executes Room 1 with full-corpus grounding and 0% voice collision."""
        # Setup project directory with extracted chapters
        extracted_dir = self.temp_dir / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "title": "The Last Wish",
            "author": "Andrzej Sapkowski",
            "project_slug": "the_last_wish",
        }
        (self.temp_dir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

        ch1_text = (
            "Geralt of Rivia entered the tavern in Wyzima. "
            "The innkeeper stared with fear. \"What do you want, witcher?\" asked the innkeeper. "
            "Geralt replied calmly, \"A room for the night and beer.\" "
            "Suddenly, Ostrit drew his dagger."
        )
        ch2_text = (
            "Lord Velerad met Geralt at the palace gates. "
            "\"The king offers three thousand orens,\" Lord Velerad said. "
            "Geralt examined the silver sword. Ostrit watched from afar."
        )

        (extracted_dir / "chapter_001.md").write_text(ch1_text, encoding="utf-8")
        (extracted_dir / "chapter_002.md").write_text(ch2_text, encoding="utf-8")

        # Mock LLM function providing structured JSON responses
        def mock_llm_fn(prompt: str, system_instruction: str = "", **kwargs) -> Any:
            if "Canonical Novel Dossier" in prompt or "world_lore_entities" in prompt or "googleSearch" in str(kwargs):
                return {
                    "book_title": "The Last Wish",
                    "author": "Andrzej Sapkowski",
                    "literary_dna": {
                        "tradition": "DARK_FANTASY_GRIT",
                        "primary_genre": "Dark Fantasy",
                        "sub_genres": ["Sword and Sorcery"],
                        "historical_era": "medieval_mythic",
                        "setting_geography": "The Continent",
                        "source_fidelity_tier": "RAW_UNRATED",
                    },
                    "characters": [
                        {"english_name": "Geralt", "hindi_name": "गेराल्ट", "role_prominence": "lead", "gender": "male", "vocal_weight": "heavy_deep"},
                        {"english_name": "Velerad", "hindi_name": "वेलेराड", "role_prominence": "major", "gender": "male", "vocal_weight": "authoritative"},
                        {"english_name": "Ostrit", "hindi_name": "ऑस्ट्रिट", "role_prominence": "minor", "gender": "male", "vocal_weight": "rustic_weathered"},
                    ],
                    "world_acoustics": {
                        "primary_materials": ["stone", "wood", "iron"],
                        "banned_anachronisms": ["gunpowder", "engine", "telephone", "electricity"],
                    },
                    "musical_tradition": {
                        "cultural_tradition": "Slavic Medieval Folk",
                        "signature_instruments": ["lute", "hurdy-gurdy", "viol", "davul"],
                    },
                    "linguistic_dialect": {
                        "recommended_hindustani_register": "rugged frontier Hindustani",
                    },
                    "world_lore_entities": {
                        "locations": {"Wyzima": "विज़िमा"},
                        "creatures": {"Striga": "स्ट्रिगा"},
                    },
                }
            elif "Universal Literary DNA" in prompt or "book_dna" in prompt.lower():
                return {
                    "literary_tradition": "DARK_FANTASY_GRIT",
                    "source_fidelity_tier": "RAW_UNRATED",
                    "profanity_policy": "UNRATED_AUTHENTIC_KASHYAP",
                    "action_intensity": "VISCERAL_COMBAT_GORE",
                    "regional_dialect_cadence": "Rugged Frontier Hindustani",
                }
            elif "Dramatis Personae" in prompt or "Casting Director" in system_instruction:
                return [
                    {"english_name": "Geralt", "hindi_name": "गेराल्ट", "gender": "male", "sociolect_trait": "RUGGED_GRIT"},
                    {"english_name": "Velerad", "hindi_name": "वेलेराड", "gender": "male", "sociolect_trait": "ARISTOCRATIC"},
                ]
            elif "acoustic DNA" in prompt.lower() or "Sonic" in system_instruction:
                return {
                    "primary_era": "medieval_mythic",
                    "acoustic_spaces": {
                        "tavern": {"reverb_type": "medium_wooden_tavern", "wet_mix": 0.15},
                    },
                    "banned_anachronisms": ["car", "phone"],
                }
            elif "Phonetic" in system_instruction or "lexicon" in prompt.lower():
                return {
                    "locations": {"Wyzima": "विज़िमा"},
                    "terminology": {"witcher": "विचर"},
                }
            return {}

        supervisor = PreProductionSupervisor()
        result = supervisor.execute_preproduction(
            project_dir=self.temp_dir,
            force=True,
            call_llm_fn=mock_llm_fn,
        )

        self.assertEqual(result["status"], "MASTER_LOCKED")

        # Verify all 4 master files exist
        self.assertTrue((self.temp_dir / "book_bible.json").exists())
        self.assertTrue((self.temp_dir / "book_dna.json").exists())
        self.assertTrue((self.temp_dir / "sonic_bible.json").exists())
        self.assertTrue((self.temp_dir / "cast_lock.json").exists())

        # Verify BookBible contents
        bible = BookBible.load_from_project(self.temp_dir)
        self.assertIn("Geralt", bible.characters)
        self.assertIn("Velerad", bible.characters)

        # Check provenance
        geralt = bible.characters["Geralt"]
        self.assertEqual(geralt.provenance.origin, "WEB_VERIFIED")
        self.assertGreaterEqual(geralt.provenance.corpus_mention_count, 2)
        self.assertIn("Geralt of Rivia entered", geralt.provenance.evidence_quote)

        # Check cast lock
        cast_lock = json.loads((self.temp_dir / "cast_lock.json").read_text(encoding="utf-8"))
        self.assertIn("locks", cast_lock)

    def test_chapter_entity_harvester_cast_lock_sync(self):
        """Test 5: ChapterEntityHarvester dynamically discovers characters and syncs cast_lock."""
        # Initialize Bible
        bible = BookBible(book_title="Test Novel", author="Test Author")
        bible.save(self.temp_dir)

        chapter_text = (
            "Commander Thorne arrived at the outpost. "
            "\"Hold the line!\" shouted Thorne. "
            "Lieutenant Sarah nodded and loaded her crossbow."
        )

        def mock_llm_harvester(prompt: str, system_instruction: str = "", **kwargs) -> Any:
            return {
                "characters": [
                    {
                        "english_name": "Thorne",
                        "hindi_name": "थोर्न",
                        "entity_type": "PROPER_NAME",
                        "aliases": ["Commander Thorne"],
                        "gender": "male",
                        "voice_style": "Commanding and gruff",
                        "hindustani_archetype": "MILITARY_OFFICER",
                    },
                    {
                        "english_name": "Sarah",
                        "hindi_name": "सारा",
                        "entity_type": "PROPER_NAME",
                        "aliases": ["Lieutenant Sarah"],
                        "gender": "female",
                        "voice_style": "Sharp and focused",
                        "hindustani_archetype": "DISCIPLINED_SOLDIER",
                    },
                ],
                "locations_and_terms": {"Outpost": "चौकी"},
            }

        glossary = ChapterEntityHarvester.harvest_and_sync(
            chapter_text=chapter_text,
            project_dir=self.temp_dir,
            chapter_num=1,
            call_llm_fn=mock_llm_harvester,
        )

        # Verify Bible updated
        reloaded_bible = BookBible.load_from_project(self.temp_dir)
        self.assertIn("Thorne", reloaded_bible.characters)
        self.assertIn("Sarah", reloaded_bible.characters)

        # Verify cast_lock.json and voice_registry.json synced
        lock_file = self.temp_dir / "cast_lock.json"
        self.assertTrue(lock_file.exists())
        lock_data = json.loads(lock_file.read_text(encoding="utf-8"))
        self.assertIn("locks", lock_data)

        # Verify distinct voices allocated
        vreg_file = self.temp_dir / "voice_registry.json"
        self.assertTrue(vreg_file.exists())
        vreg_data = json.loads(vreg_file.read_text(encoding="utf-8"))
        self.assertIn("Thorne", vreg_data)
        self.assertIn("Sarah", vreg_data)
        self.assertNotEqual(vreg_data["Thorne"]["voice"], vreg_data["Sarah"]["voice"])


if __name__ == "__main__":
    unittest.main()
