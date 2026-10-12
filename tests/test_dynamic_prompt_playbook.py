#!/usr/bin/env python3
"""
Unit tests for 2-Tier Standalone Dynamic Prompt & Directing Subsystem.
Tests ProductionPlaybook, ChapterDirectorCard, ProductionPlaybookSynthesizer,
and ChapterSteeringDirector in pure isolation.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock

from audiobook_factory.contracts.playbook import (
    ProductionPlaybook,
    ChapterDirectorCard,
)
from audiobook_factory.preproduction.playbook_synthesizer import (
    ProductionPlaybookSynthesizer,
)
from audiobook_factory.glossary.chapter_director import (
    ChapterSteeringDirector,
)


class TestDynamicPromptPlaybook(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_playbook_schema_and_defaults(self):
        pb = ProductionPlaybook(
            project_id="proj-witcher",
            book_title="The Last Wish",
            author="Andrzej Sapkowski",
            literary_tradition="DARK_FANTASY_GRIT",
            source_fidelity_tier="RAW_UNRATED",
            regional_dialect_cadence="Epic Mythic Hindustani",
            translation_system_prompt="Custom Witcher Translation Directives",
            screenplay_system_prompt="Custom Witcher Screenplay Directives",
            narrator_master_demeanor="weathered, resonant epic chronicler",
        )
        self.assertEqual(pb.project_id, "proj-witcher")
        self.assertEqual(pb.book_title, "The Last Wish")
        self.assertEqual(pb.narrator_master_demeanor, "weathered, resonant epic chronicler")
        d = pb.model_dump()
        reconstructed = ProductionPlaybook.model_validate(d)
        self.assertEqual(reconstructed.book_title, pb.book_title)

    def test_02_chapter_director_card_to_prompt_context(self):
        card = ChapterDirectorCard(
            chapter_num=1,
            chapter_title="The Voice of Reason",
            scene_atmosphere="Dark, damp tavern standoff with heavy tension.",
            dramatic_tension="Simmering suspicion erupting into sudden combat.",
            character_emotional_states={
                "Geralt": "Guarded, weary, alert for sudden strike",
                "Tavern-keeper": "Terrified, begging for peace",
            },
            pacing_cadence="Staccato, urgent dialogue with rapid beats",
            narrator_vocal_tint="low, tense, watchful dread",
            key_motifs_or_sensory_details=["cold beer", "gleam of silver", "blood on sawdust"],
        )
        ctx = card.to_prompt_context()
        self.assertIn("### CHAPTER DRAMATIC STEERING (Chapter 1: The Voice of Reason):", ctx)
        self.assertIn("Dark, damp tavern standoff", ctx)
        self.assertIn("Geralt: Guarded, weary", ctx)
        self.assertIn("low, tense, watchful dread", ctx)
        self.assertIn("blood on sawdust", ctx)

    def test_03_playbook_synthesizer_with_mock_llm(self):
        mock_response = {
            "translation_system_prompt": "Synthesized Custom Rules: Mythic Cadence without village panchayat terms.",
            "screenplay_system_prompt": "Stanislavski Directives: Intense psychological subtext.",
            "narrator_master_demeanor": "somber, resonant tavern chronicler",
            "proverb_style": "High fantasy cultural equivalency",
        }
        mock_fn = MagicMock(return_value=mock_response)
        synthesizer = ProductionPlaybookSynthesizer(model="mock-model")

        book_dna = {
            "literary_tradition": "MEDIEVAL_HIGH_FANTASY",
            "source_fidelity_tier": "RAW_UNRATED",
            "regional_dialect_cadence": "Archaic Mythic Hindustani",
            "world_atmosphere_summary": "Grim, monster-infested frontier",
        }
        meta = {"title": "Fantasy Tale", "author": "Epic Author", "project_slug": "fantasy_tale"}

        pb = synthesizer.synthesize_playbook(
            book_dna=book_dna,
            book_metadata=meta,
            call_llm_fn=mock_fn,
        )

        self.assertEqual(pb.project_id, "proj-fantasy_tale")
        self.assertIn("Synthesized Custom Rules", pb.translation_system_prompt)
        self.assertEqual(pb.narrator_master_demeanor, "somber, resonant tavern chronicler")

    def test_04_playbook_synthesizer_heuristic_fallbacks(self):
        synthesizer = ProductionPlaybookSynthesizer()

        # 1. Fantasy heuristic
        pb_fantasy = synthesizer._heuristic_fallback(
            project_id="proj-test",
            book_title="Sword Legend",
            author="Author",
            tradition="MEDIEVAL_DARK_FANTASY",
            fidelity_tier="RAW_UNRATED",
            cadence="Epic Hindustani",
            atmosphere="Grim battles",
            banned_anachronisms=["phones", "cars"],
            acceptable_loanwords=["dragon", "sword"],
        )
        self.assertIn("measured, resonant, atmospheric epic narrator", pb_fantasy.narrator_master_demeanor)
        self.assertIn("ZERO ENGLISH ARTICLES IN DEVANAGARI", pb_fantasy.translation_system_prompt)
        self.assertIn("PHONETIC FIDELITY FOR BEASTS", pb_fantasy.translation_system_prompt)
        self.assertIn("phones, cars", pb_fantasy.translation_system_prompt)

        # 2. Classic heuristic
        pb_classic = synthesizer._heuristic_fallback(
            project_id="proj-test",
            book_title="Classic Tale",
            author="Munshi",
            tradition="RURAL_CLASSIC_REALISM",
            fidelity_tier="CLASSIC_REVERENT",
            cadence="Awadhi Hindustani",
            atmosphere="Rural pathos",
            banned_anachronisms=[],
            acceptable_loanwords=[],
        )
        self.assertIn("dignified", pb_classic.narrator_master_demeanor.lower())
        self.assertIn("SACRED REVERENCE & PATHOS", pb_classic.translation_system_prompt)

    def test_05_chapter_steering_director_with_mock_llm(self):
        mock_response = {
            "scene_atmosphere": "Quiet cemetery at twilight; heavy mist and distant crows.",
            "dramatic_tension": "Melancholic reflection interrupted by sudden ominous footsteps.",
            "character_emotional_states": {
                "Protagonist": "Grief-stricken but acutely vigilant"
            },
            "pacing_cadence": "Slow, atmospheric phrasing building to alert tension",
            "narrator_vocal_tint": "hushed, solemn, expectant whisper",
            "key_motifs_or_sensory_details": ["wet grass", "carved marble", "cold mist"],
        }
        mock_fn = MagicMock(return_value=mock_response)
        director = ChapterSteeringDirector(model="mock-model")

        chapter_text = "The cold fog clung to the ancient tombstones. Geralt walked silently among the graves."
        card = director.direct_chapter(
            chapter_text=chapter_text,
            chapter_num=3,
            chapter_title="The Cemetery",
            call_llm_fn=mock_fn,
        )

        self.assertEqual(card.chapter_num, 3)
        self.assertIn("Quiet cemetery", card.scene_atmosphere)
        self.assertEqual(card.narrator_vocal_tint, "hushed, solemn, expectant whisper")
        self.assertEqual(card.character_emotional_states["Protagonist"], "Grief-stricken but acutely vigilant")

    def test_06_chapter_steering_director_heuristic_combat_and_suspense(self):
        director = ChapterSteeringDirector()

        # Combat text
        combat_text = "The assassin drew his steel blade and lunged forward with a vicious slash. Blood sprayed as swords collided."
        card_combat = director._heuristic_fallback(chapter_text=combat_text, chapter_num=1, chapter_title="The Clash")
        self.assertIn("confrontation", card_combat.scene_atmosphere.lower())
        self.assertIn("urgent", card_combat.narrator_vocal_tint.lower())

        # Suspense text
        suspense_text = "A sudden creak echoed in the darkness. Silence fell over the shadowed corridor as they whispered in fear."
        card_suspense = director._heuristic_fallback(chapter_text=suspense_text, chapter_num=2, chapter_title="The Hall")
        self.assertIn("suspense", card_suspense.scene_atmosphere.lower())
        self.assertIn("watchful", card_suspense.narrator_vocal_tint.lower())

    def test_07_persistence_save_and_load(self):
        card = ChapterDirectorCard(
            chapter_num=5,
            chapter_title="The King's Court",
            scene_atmosphere="Opulent grand hall with whispered political intrigue.",
            dramatic_tension="High political stakes.",
        )
        saved_path = ChapterSteeringDirector.save_director_card(card, self.test_dir)
        self.assertTrue(saved_path.exists())

        loaded_card = ChapterSteeringDirector.load_director_card(self.test_dir, chapter_num=5)
        self.assertIsNotNone(loaded_card)
        self.assertEqual(loaded_card.chapter_title, "The King's Court")
        self.assertIn("Opulent grand hall", loaded_card.scene_atmosphere)


    def test_08_dynamic_prompt_builder_with_playbook_and_card(self):
        from audiobook_factory.translation.prompt_builder import DynamicPromptBuilder
        from audiobook_factory.translation.chunker import MacroChunk
        from audiobook_factory.translation.contracts import FidelityTier, TranslationRequest

        pb = ProductionPlaybook(
            project_id="proj-epic",
            book_title="Epic Saga",
            literary_tradition="HIGH_FANTASY",
            translation_system_prompt="### CUSTOM TAILORED HIGH FANTASY INVARIANTS: NO VILLAGE PANCHAYAT TERMS.",
        )
        sys_inst = DynamicPromptBuilder.build_system_instruction(FidelityTier.RAW_UNRATED, playbook=pb)
        self.assertIn("CUSTOM TAILORED HIGH FANTASY INVARIANTS", sys_inst)
        self.assertIn("Master Literary Adapter", sys_inst)

        card = ChapterDirectorCard(
            chapter_num=4,
            chapter_title="The Ancient Crypt",
            scene_atmosphere="Claustrophobic, mossy stone corridor with dripping water.",
        )
        chunk = MacroChunk(
            index=0,
            text="The heroes stepped into the crypt cautiously.",
            word_count=7,
            start_paragraph_idx=0,
            end_paragraph_idx=1,
        )
        req = TranslationRequest(
            source_text="The heroes stepped into the crypt cautiously.",
            playbook=pb,
            director_card=card,
        )
        user_p = DynamicPromptBuilder.build_user_prompt(chunk, req)
        self.assertIn("### CHAPTER DRAMATIC STEERING (Chapter 4: The Ancient Crypt):", user_p)
        self.assertIn("Claustrophobic, mossy stone corridor", user_p)

    def test_09_translation_engine_e2e_with_playbook_and_card(self):
        from audiobook_factory.translation.engine import TranslationEngine
        from audiobook_factory.translation.contracts import FidelityTier, TranslationRequest

        captured_system = []
        captured_prompt = []

        def mock_llm(prompt, system_instruction="", **kwargs):
            captured_prompt.append(prompt)
            captured_system.append(system_instruction)
            return "नायक सावधानी से तहखाने में दाखिल हुए।"

        engine = TranslationEngine(llm_fn=mock_llm)
        pb = ProductionPlaybook(
            project_id="proj-demo",
            book_title="Demo Book",
            translation_system_prompt="SPECIAL DEMO PLAYBOOK SYSTEM INSTRUCTIONS",
        )
        card = ChapterDirectorCard(
            chapter_num=2,
            scene_atmosphere="Electric neon cyberpunk alleyway in rain.",
        )
        req = TranslationRequest(
            source_text="The hero stepped out into the rain.",
            tier=FidelityTier.RAW_UNRATED,
            playbook=pb,
            director_card=card,
        )
        res = engine.translate(req)

        self.assertIn("नायक सावधानी से तहखाने में दाखिल हुए।", res.translated_markdown)
        self.assertEqual(len(captured_system), 1)
        self.assertIn("SPECIAL DEMO PLAYBOOK SYSTEM INSTRUCTIONS", captured_system[0])
        self.assertEqual(len(captured_prompt), 1)
        self.assertIn("Electric neon cyberpunk alleyway", captured_prompt[0])

    def test_10_stanislavski_subtext_director_with_card(self):
        from audiobook_factory.script.agents.stanislavski_director import StanislavskiSubtextDirector

        captured_prompt = []

        def mock_llm(prompt, **kwargs):
            captured_prompt.append(prompt)
            return [{"index": 1, "actioning": "confront", "subtext": "testing defenses", "intensity_level": "high"}]

        director = StanislavskiSubtextDirector(model="mock-model")
        card = ChapterDirectorCard(
            chapter_num=7,
            scene_atmosphere="High-noon standoff in a desolate frontier town.",
        )
        segments = [{"index": 1, "speaker": "Gunslinger", "type": "dialogue", "text": "Draw."}]
        directed = director.direct_subtext(segments, call_llm_fn=mock_llm, director_card=card)

        self.assertEqual(directed[0]["actioning"], "confront")
        self.assertIn("High-noon standoff in a desolate frontier town", captured_prompt[0])
        self.assertNotIn("Standard narrative encounter.", captured_prompt[0])

    def test_11_tts_gemini_speech_style_narrator_tint(self):
        from audiobook_factory.tts.providers.gemini import resolve_speech_metadata_style

        # Default without tint
        def_style = resolve_speech_metadata_style(acting=None, emotion="neutral")
        self.assertEqual(def_style, "calm, steady, articulate, measured audiobook delivery")

        # With narrator tint
        tinted_style = resolve_speech_metadata_style(
            acting=None,
            emotion="neutral",
            narrator_tint="ominous tavern dread, low watchful tension",
            is_narrator=True,
        )
        self.assertIn("ominous tavern dread, low watchful tension", tinted_style)
        self.assertIn("grounded, natural spoken dialogue", tinted_style)

    def test_12_adversarial_chapter_zero_dialogue(self):
        """Stress test: Chapter with 0 dialogue (100% pure descriptive prose)."""
        director = ChapterSteeringDirector(model="mock-model")
        pure_prose = (
            "The ancient forest stood motionless under the pale moonlight. Dense fog crept over "
            "the mossy boulders, suffocating every whisper of the wind. A lonely crow took flight, "
            "its black wings slicing through the freezing mountain mist."
        )
        card = director._heuristic_fallback(chapter_text=pure_prose, chapter_num=10, chapter_title="Silent Woods")
        self.assertEqual(card.chapter_num, 10)
        self.assertIsNotNone(card.scene_atmosphere)
        self.assertEqual(card.character_emotional_states, {})
        # Prompt formatting handles empty character stances cleanly
        ctx = card.to_prompt_context()
        self.assertNotIn("Character Emotional Stances", ctx)
        self.assertIn("Silent Woods", ctx)

    def test_13_adversarial_chapter_all_dialogue_zero_prose(self):
        """Stress test: Chapter with 100% dialogue and 0 narrative prose."""
        director = ChapterSteeringDirector(model="mock-model")
        pure_dialogue = (
            '"Stop right there!"\n'
            '"Who goes there?"\n'
            '"Drop your blade or bleed!"\n'
            '"You will regret those words, coward."\n'
            '"Kill him now!"'
        )
        card = director._heuristic_fallback(chapter_text=pure_dialogue, chapter_num=11, chapter_title="The Standoff")
        self.assertEqual(card.chapter_num, 11)
        # Should detect combat keywords ('blade', 'bleed', 'kill')
        self.assertIn("confrontation", card.scene_atmosphere.lower())
        self.assertIn("urgent", card.narrator_vocal_tint.lower())

    def test_14_adversarial_extreme_unicode_stress(self):
        """Stress test: Extreme multilingual Unicode (Devanagari, Urdu Nastaliq, French/Polish diacritics)."""
        synthesizer = ProductionPlaybookSynthesizer()
        director = ChapterSteeringDirector()

        # Complex multilingual Unicode payload
        unicode_title = "D'Artagnan & Stanisław: حویلی کی داستان — रक्त और बर्फ़"
        unicode_atmosphere = "गहरी धुंध, خونی جنگ, naïve façade, déjà vu, żółć, crêpe, Łódź."
        unicode_prose = (
            "दरवाज़ा चरमराया। ख़ामोशी छा गई। Stanisław wyciągnął miecz. "
            "« C'est une trahison ! » Il s'avança avec méfiance."
        )

        pb = synthesizer._heuristic_fallback(
            project_id="proj-unicode-test",
            book_title=unicode_title,
            author="Émile Zola & مرزا غالب",
            tradition="UNIVERSAL_HISTORICAL_DRAMA",
            fidelity_tier="RAW_UNRATED",
            cadence="Hindustani Urdu Mix",
            atmosphere=unicode_atmosphere,
            banned_anachronisms=["téléphone", "موبائل"],
            acceptable_loanwords=["rendez-vous", "फ़रमान"],
        )
        self.assertEqual(pb.book_title, unicode_title)
        self.assertIn("téléphone, موبائل", pb.translation_system_prompt)
        self.assertIn("rendez-vous, फ़रमान", pb.translation_system_prompt)

        card = director._heuristic_fallback(
            chapter_text=unicode_prose,
            chapter_num=99,
            chapter_title="خونی معرکہ (Bloody Duel)",
            playbook=pb,
        )
        ctx = card.to_prompt_context()
        self.assertIn("خونی معرکہ", ctx)
        self.assertIn("Bloody Duel", ctx)
        # Serialization & roundtrip validation with non-ASCII preserved
        d = card.model_dump()
        reconstructed = ChapterDirectorCard.model_validate(d)
        self.assertEqual(reconstructed.chapter_title, card.chapter_title)

    def test_15_adversarial_llm_malformed_json_and_markdown_fences(self):
        """Stress test: LLM returning raw string, markdown code fences, or partially truncated JSON."""
        synthesizer = ProductionPlaybookSynthesizer(model="mock-model")
        director = ChapterSteeringDirector(model="mock-model")

        # 1. Markdown code block wrapping valid JSON
        fenced_json = (
            "```json\n"
            "{\n"
            '  "translation_system_prompt": "Fenced System Prompt",\n'
            '  "screenplay_system_prompt": "Fenced Screenplay",\n'
            '  "narrator_master_demeanor": "fenced demeanor",\n'
            '  "proverb_style": "fenced style"\n'
            "}\n"
            "```"
        )
        pb = synthesizer.synthesize_playbook(
            book_dna={"literary_tradition": "FANTASY"},
            book_metadata={"title": "Fenced Test", "author": "Tester", "project_slug": "fenced"},
            call_llm_fn=MagicMock(return_value=fenced_json),
        )
        self.assertEqual(pb.translation_system_prompt, "Fenced System Prompt")
        self.assertEqual(pb.narrator_master_demeanor, "fenced demeanor")

        # 2. Malformed / truncated JSON string (missing closing brace) handled gracefully via json_repair
        truncated_json = (
            '{\n  "scene_atmosphere": "Unclosed atmospheric tension",\n  "dramatic_tension": "unresolved"'
        )
        card = director.direct_chapter(
            chapter_text="Some dramatic narrative words.",
            chapter_num=4,
            call_llm_fn=MagicMock(return_value=truncated_json),
        )
        self.assertEqual(card.scene_atmosphere, "Unclosed atmospheric tension")
        self.assertEqual(card.dramatic_tension, "unresolved")

        # 3. Completely garbage / non-JSON string falls back cleanly to heuristic generator
        garbage_response = "I am an AI and cannot generate JSON right now! Error 500."
        card_fallback = director.direct_chapter(
            chapter_text="The blade slashed across the armor with blood spraying.",
            chapter_num=5,
            call_llm_fn=MagicMock(return_value=garbage_response),
        )
        self.assertIn("confrontation", card_fallback.scene_atmosphere.lower())
        self.assertIn("urgent", card_fallback.narrator_vocal_tint.lower())

    def test_16_adversarial_empty_and_whitespace_inputs(self):
        """Stress test: Empty strings, None values, whitespace strings."""
        director = ChapterSteeringDirector()
        empty_card = director.direct_chapter(chapter_text="   \n\t  ", chapter_num=1, chapter_title="")
        self.assertEqual(empty_card.chapter_num, 1)
        self.assertEqual(empty_card.scene_atmosphere, "Standard narrative encounter.")
        self.assertEqual(empty_card.dramatic_tension, "steady narrative progression")
        self.assertIn("### CHAPTER DRAMATIC STEERING (Chapter 1):", empty_card.to_prompt_context())

    def test_17_adversarial_null_dereferencing_in_playbook_and_dossier(self):
        """Regression test: dossier with None sub-dicts or LLM returning None fields."""
        synthesizer = ProductionPlaybookSynthesizer(model="mock-model")

        # 1. Dossier with None subdicts
        pb = synthesizer.synthesize_playbook(
            book_dna=None,
            book_dossier={
                "world_acoustics": None,
                "linguistic_dialect": None,
                "literary_dna": None,
            },
        )
        self.assertIsNotNone(pb)
        self.assertEqual(pb.banned_anachronisms, [])
        self.assertEqual(pb.acceptable_loanwords, [])

        # 2. LLM response with None values for optional strings
        mock_llm = MagicMock(return_value={
            "translation_system_prompt": "Valid Translation Prompt",
            "screenplay_system_prompt": None,
            "narrator_master_demeanor": None,
            "proverb_style": None,
        })
        pb2 = synthesizer.synthesize_playbook(
            book_dna={"literary_tradition": "FANTASY"},
            call_llm_fn=mock_llm,
        )
        self.assertEqual(pb2.translation_system_prompt, "Valid Translation Prompt")
        self.assertEqual(pb2.screenplay_system_prompt, "")
        self.assertEqual(pb2.narrator_master_demeanor, "calm, steady, articulate, measured audiobook delivery")

    def test_18_adversarial_null_dereferencing_in_chapter_director(self):
        """Regression test: chapter_director with None text or LLM returning None sub-objects."""
        director = ChapterSteeringDirector(model="mock-model")

        # 1. None chapter text does not raise AttributeError
        card = director.direct_chapter(chapter_text=None, chapter_num=2)
        self.assertEqual(card.chapter_num, 2)
        self.assertEqual(card.scene_atmosphere, "Standard narrative encounter.")

        # 2. LLM returning None for tension, states, motifs, etc.
        mock_llm = MagicMock(return_value={
            "scene_atmosphere": "Quiet foggy valley",
            "dramatic_tension": None,
            "character_emotional_states": None,
            "pacing_cadence": None,
            "narrator_vocal_tint": None,
            "key_motifs_or_sensory_details": None,
        })
        card2 = director.direct_chapter(
            chapter_text="Some valid prose in the valley.",
            chapter_num=5,
            call_llm_fn=mock_llm,
        )
        self.assertEqual(card2.scene_atmosphere, "Quiet foggy valley")
        self.assertEqual(card2.dramatic_tension, "steady narrative progression")
        self.assertEqual(card2.character_emotional_states, {})
        self.assertEqual(card2.key_motifs_or_sensory_details, [])

    def test_19_adversarial_null_dereferencing_in_directors(self):
        """Regression test: segments with speaker=None, text=None, or invalid spatial pan."""
        from audiobook_factory.script.agents.stanislavski_director import StanislavskiSubtextDirector
        from audiobook_factory.script.agents.physical_blocking_director import PhysicalBlockingDirector
        from audiobook_factory.script.staging_enricher import _enrich_performance_and_staging_llm

        sd = StanislavskiSubtextDirector(model="mock-model")
        pbd = PhysicalBlockingDirector(model="mock-model")

        # Segments with None values
        bad_segments = [
            {"index": 1, "speaker": None, "text": None, "type": "narration"},
            {"index": 2, "speaker": "Hero", "text": "I am here.", "type": "dialogue"},
        ]

        # 1. StanislavskiSubtextDirector does not crash on None text/speaker
        mock_stan = MagicMock(return_value=[{"index": 2, "actioning": "declare"}])
        out_stan = sd.direct_subtext(bad_segments, call_llm_fn=mock_stan)
        self.assertEqual(len(out_stan), 2)
        self.assertEqual(out_stan[0]["actioning"], "narrate")

        # 2. PhysicalBlockingDirector does not crash on None text/speaker or non-float pan
        mock_block = MagicMock(return_value=[
            {"index": 1, "spatial": {"pan": "center"}},
            {"index": 2, "spatial": {"azimuth_pan": "invalid"}},
        ])
        out_block = pbd.direct_blocking(bad_segments, call_llm_fn=mock_block)
        self.assertEqual(len(out_block), 2)
        self.assertEqual(out_block[0]["spatial"]["pan"], 0.0)
        self.assertEqual(out_block[1]["spatial"]["pan"], 0.0)

    def test_20_dict_playbook_and_director_card_compatibility(self):
        """Test that plain dictionary representations of playbooks and cards are fully supported."""
        from audiobook_factory.translation.prompt_builder import DynamicPromptBuilder
        from audiobook_factory.translation.chunker import MacroChunk
        from audiobook_factory.translation.contracts import FidelityTier, TranslationRequest
        from audiobook_factory.script.agents.stanislavski_director import StanislavskiSubtextDirector
        from audiobook_factory.script.agents.physical_blocking_director import PhysicalBlockingDirector

        dict_pb = {
            "translation_system_prompt": "CUSTOM DICT PLAYBOOK DIRECTIVES",
            "screenplay_system_prompt": "CUSTOM DICT SCREENPLAY DIRECTIVES",
        }
        dict_card = {
            "chapter_num": 3,
            "chapter_title": "Dict Scene",
            "scene_atmosphere": "Gloomy rainy ruin",
            "dramatic_tension": "Rising dread",
        }

        # 1. DynamicPromptBuilder system instruction with dict playbook
        sys_prompt = DynamicPromptBuilder.build_system_instruction(FidelityTier.RAW_UNRATED, playbook=dict_pb)
        self.assertIn("CUSTOM DICT PLAYBOOK DIRECTIVES", sys_prompt)

        # 2. DynamicPromptBuilder user prompt with dict card
        chunk = MacroChunk(index=0, text="Prose text.", word_count=2, start_paragraph_idx=0, end_paragraph_idx=1)
        req = TranslationRequest(source_text="Prose text.", playbook=dict_pb, director_card=dict_card)
        user_p = DynamicPromptBuilder.build_user_prompt(chunk, req)
        self.assertIn("Gloomy rainy ruin", user_p)
        self.assertIn("Rising dread", user_p)

        # 3. Stanislavski director with dict card & dict playbook
        sd = StanislavskiSubtextDirector(model="mock-model")
        captured = []
        def mock_llm(prompt, system_instruction="", **kwargs):
            captured.append((prompt, system_instruction))
            return []
        sd.direct_subtext(
            segments=[{"index": 1, "speaker": "A", "text": "Hi"}],
            call_llm_fn=mock_llm,
            director_card=dict_card,
            playbook=dict_pb,
        )
        self.assertIn("Gloomy rainy ruin", captured[0][0])
        self.assertIn("CUSTOM DICT SCREENPLAY DIRECTIVES", captured[0][1])

    def test_21_audiobook_adapter_null_safety(self):
        """Test that AudiobookAdapter handles None chapter_text and None dramatic_plan cleanly."""
        from audiobook_factory.adapters.audiobook import AudiobookAdapter

        adapter = AudiobookAdapter()
        # None chapter text returns empty list
        res_empty = adapter.adapt(chapter_text=None, dramatic_plan=None, call_chunk_fn=lambda **kw: [])
        self.assertEqual(res_empty, [])

        # Valid text with None dramatic_plan does not crash
        res_valid = adapter.adapt(
            chapter_text="Simple text",
            dramatic_plan=None,
            call_chunk_fn=lambda **kw: [{"index": 1, "speaker": "Narrator", "text": "Simple text"}],
        )
        self.assertEqual(len(res_valid), 1)

    def test_22_atomic_file_saving_and_load_robustness(self):
        """Test atomic file persistence and string chapter numbers in ChapterSteeringDirector."""
        card = ChapterDirectorCard(
            chapter_num=7,
            chapter_title="Atomic Save Chapter",
            scene_atmosphere="Rock-solid atomicity.",
        )
        saved_path = ChapterSteeringDirector.save_director_card(card, self.test_dir)
        self.assertTrue(saved_path.exists())

        # Load with string chapter number e.g. "7"
        loaded = ChapterSteeringDirector.load_director_card(self.test_dir, chapter_num="7")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.chapter_num, 7)
        self.assertEqual(loaded.chapter_title, "Atomic Save Chapter")


if __name__ == "__main__":
    unittest.main()


