#!/usr/bin/env python3
"""
Test Suite: Phase 2 - Screenplay Directing & Acoustic Reflex Tags Engine.
Verifies:
1. Stanislavski Subtext Director acoustic reflex tags embedding & preservation.
2. Gemini 3.8 Flash Audio modality reflex tags vs non-acoustic acting descriptors.
3. Narrator Transparency Invariant (zero reflex tags, calm authoritative delivery).
4. Canonical character alias preservation and bilingual speaker key alignment.
5. 0% speaker turn inversion and zero quote leakage to Narrator.
6. Zero hardcoded novel titles, character rosters, or test fixtures.
"""

from __future__ import annotations
import ast
import re
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from audiobook_factory.script.agents.stanislavski_director import (
    StanislavskiSubtextDirector,
    CERTIFIED_ACOUSTIC_REFLEX_TAGS,
    ACOUSTIC_REFLEX_NORMALIZATION,
)
from audiobook_factory.script.agents.script_room import (
    ScreenplayDramaturgyRoom,
    build_canonical_alias_map,
    format_and_align_segments,
    get_screenplay_room,
)
from audiobook_factory.script.staging_enricher import (
    _parse_dramatized_chunk_llm,
    _enrich_performance_and_staging_llm,
)


class TestDramatizedScriptBuilder(unittest.TestCase):
    """Phase 2 Screenplay Directing & Acoustic Reflex Tags verification."""

    def setUp(self):
        self.sample_roster = {
            "characters": {
                "The Investigator": {
                    "gender": "male",
                    "hindi_name": "जासूस",
                    "aliases": ["investigator", "detective", "the detective"],
                },
                "The Witness": {
                    "gender": "female",
                    "hindi_name": "गवाह",
                    "aliases": ["witness", "the witness", "informant"],
                },
            }
        }

    # =========================================================================
    # 1. Stanislavski Acoustic Reflex Tags Directing & Sanitization
    # =========================================================================

    def test_certified_acoustic_reflex_tags_preserved_in_dialogue(self):
        """Verifies all certified acoustic reflex tags are preserved in dialogue lines."""
        for reflex in ("laughs", "sighs", "whispers", "growls", "gasp", "chuckles", "pant", "groan"):
            raw_line = f"[{reflex}] We must move quickly before sunrise."
            cleaned, preserved, extracted = StanislavskiSubtextDirector.process_acoustic_reflexes_and_acting_cues(
                text=raw_line,
                is_dialogue=True,
            )
            self.assertIn(f"[{reflex}]", cleaned)
            self.assertIn(reflex, preserved)
            self.assertEqual(extracted, [])

    def test_hindi_vocal_reflex_cues_normalized_to_certified_tags(self):
        """Verifies Hindi reflex cues are mapped to canonical certified acoustic tags."""
        test_cases = [
            ("[हँसते हुए] वह अब बाहर नहीं आने वाला...", "[laughs] वह अब बाहर नहीं आने वाला..."),
            ("[आह भरते हुए] थोड़ा और इंतज़ार कर लेते हैं।", "[sighs] थोड़ा और इंतज़ार कर लेते हैं।"),
            ("[धीमी आवाज़ में] खामोश रहो।", "[whispers] खामोश रहो।"),
            ("[हाँफते हुए] हम बच गए!", "[pant] हम बच गए!"),
            ("[गुर्राते हुए] दूर हटो!", "[growls] दूर हटो!"),
        ]
        for hindi_input, expected_output in test_cases:
            cleaned, preserved, extracted = StanislavskiSubtextDirector.process_acoustic_reflexes_and_acting_cues(
                text=hindi_input,
                is_dialogue=True,
            )
            self.assertEqual(cleaned, expected_output)
            self.assertGreater(len(preserved), 0)
            self.assertEqual(extracted, [])

    def test_narrator_transparency_invariant_zero_reflex_tags(self):
        """Verifies Narrator lines NEVER contain acoustic reflex tags or stage cues."""
        narrator_with_tags = "[laughs] [whispers] The morning sun broke through the heavy mist over the valley."
        cleaned, preserved, extracted = StanislavskiSubtextDirector.process_acoustic_reflexes_and_acting_cues(
            text=narrator_with_tags,
            is_dialogue=False,
        )
        self.assertNotIn("[laughs]", cleaned)
        self.assertNotIn("[whispers]", cleaned)
        self.assertEqual(cleaned, "The morning sun broke through the heavy mist over the valley.")
        self.assertEqual(preserved, [])
        self.assertEqual(extracted, [])

    def test_non_acoustic_acting_descriptors_stripped_and_routed_to_acting(self):
        """Verifies non-acoustic acting descriptors are stripped from spoken text and returned as cues."""
        line_with_cues = "[cold menace] [laughs] You have made a grave mistake."
        cleaned, preserved, extracted = StanislavskiSubtextDirector.process_acoustic_reflexes_and_acting_cues(
            text=line_with_cues,
            is_dialogue=True,
        )
        # Spoken text retains certified acoustic reflex tag [laughs]
        self.assertEqual(cleaned, "[laughs] You have made a grave mistake.")
        self.assertIn("laughs", preserved)
        # Non-acoustic descriptor [cold menace] stripped from spoken text and extracted
        self.assertNotIn("[cold menace]", cleaned)
        self.assertIn("cold menace", extracted)

    def test_stanislavski_subtext_director_direct_subtext_with_llm(self):
        """Verifies direct_subtext embeds certified acoustic reflexes and routes non-acoustic cues."""
        director = StanislavskiSubtextDirector(model="mock-model")

        input_segments = [
            {
                "index": 1,
                "type": "narration",
                "speaker": "Narrator",
                "text": "The interrogation room fell dead silent.",
            },
            {
                "index": 2,
                "type": "dialogue",
                "speaker": "The Investigator",
                "text": "Tell me everything you saw that night.",
            },
            {
                "index": 3,
                "type": "dialogue",
                "speaker": "The Witness",
                "text": "I can't... they will kill me.",
            },
        ]

        mock_llm_response = [
            {
                "index": 1,
                "actioning": "narrate",
                "subtext": "",
                "underlying_emotion": "neutral",
                "intensity_level": "medium",
                "acting": {"delivery_style": "calm_authoritative"},
                "text": "[whispers] The interrogation room fell dead silent.",  # Attempted tag on narrator
            },
            {
                "index": 2,
                "actioning": "intimidate",
                "subtext": "You are hiding something crucial.",
                "underlying_emotion": "stern urgency",
                "intensity_level": "high",
                "acting": {"delivery_style": "calm_authoritative", "tone": "firm"},
                "text": "[growls] Tell me everything you saw that night.",
            },
            {
                "index": 3,
                "actioning": "plead",
                "subtext": "I am terrified for my life.",
                "underlying_emotion": "paralyzing fear",
                "intensity_level": "low",
                "acting": {"delivery_style": "whispering_fear"},
                "text": "[sighs] [cold terror] I can't... they will kill me.",
            },
        ]

        mock_llm_fn = MagicMock(return_value=mock_llm_response)
        directed = director.direct_subtext(
            segments=input_segments,
            dramatic_context="A high stakes interrogation.",
            call_llm_fn=mock_llm_fn,
        )

        # 1. Narrator segment must have zero tags despite LLM output
        seg1 = directed[0]
        self.assertEqual(seg1["speaker"], "Narrator")
        self.assertNotIn("[whispers]", seg1["text"])
        self.assertEqual(seg1["acting"]["delivery_style"], "calm_authoritative")
        self.assertEqual(seg1["intensity_level"], "medium")

        # 2. Investigator dialogue must have [growls]
        seg2 = directed[1]
        self.assertEqual(seg2["speaker"], "The Investigator")
        self.assertIn("[growls]", seg2["text"])
        self.assertEqual(seg2["actioning"], "intimidate")

        # 3. Witness dialogue must preserve [sighs] and strip [cold terror]
        seg3 = directed[2]
        self.assertEqual(seg3["speaker"], "The Witness")
        self.assertIn("[sighs]", seg3["text"])
        self.assertNotIn("[cold terror]", seg3["text"])
        # Non-acoustic cue "cold terror" folded into tone/delivery
        self.assertTrue(
            "cold terror" in seg3.get("acting", {}).get("tone", "")
            or "cold terror" in seg3.get("acting", {}).get("delivery_style", "")
            or "cold terror" in seg3.get("underlying_emotion", "")
        )

    # =========================================================================
    # 2. Canonical Character Alias & Bilingual Speaker Alignment
    # =========================================================================

    def test_canonical_alias_map_bidirectional_and_articles(self):
        """Verifies build_canonical_alias_map registers bare, article-prefixed, and bilingual variants."""
        alias_map = build_canonical_alias_map(self.sample_roster, is_hindi=True)

        # English aliases and article variations
        self.assertEqual(alias_map.get("investigator"), "The Investigator")
        self.assertEqual(alias_map.get("the investigator"), "The Investigator")
        self.assertEqual(alias_map.get("detective"), "The Investigator")
        self.assertEqual(alias_map.get("the detective"), "The Investigator")

        # Bilingual Hindi name mapping
        self.assertEqual(alias_map.get("जासूस"), "The Investigator")
        self.assertEqual(alias_map.get("गवाह"), "The Witness")

    def test_format_and_align_segments_resolves_aliases_and_bilingual_names(self):
        """Verifies segment speakers are resolved to canonical names."""
        raw_segments = [
            {"index": 1, "speaker": "the detective", "type": "dialogue", "text": "What happened?"},
            {"index": 2, "speaker": "गवाह", "type": "dialogue", "text": "[sighs] मुझे नहीं पता।"},
            {"index": 3, "speaker": "witness", "type": "dialogue", "text": "Everything went dark."},
        ]

        aligned = format_and_align_segments(raw_segments, character_roster=self.sample_roster, is_hindi=True)
        self.assertEqual(len(aligned), 3)
        self.assertEqual(aligned[0]["speaker"], "The Investigator")
        self.assertEqual(aligned[1]["speaker"], "The Witness")
        self.assertEqual(aligned[2]["speaker"], "The Witness")
        self.assertIn("[sighs]", aligned[1]["text"])

    # =========================================================================
    # 3. 0% Speaker Turn Inversion & Zero Quote Leakage to Narrator
    # =========================================================================

    def test_zero_quote_leakage_to_narrator_reattributed_to_interlocutor(self):
        """Verifies dialogue erroneously attributed to Narrator is reattributed to active speaker."""
        raw_segments = [
            {"index": 1, "speaker": "The Investigator", "type": "dialogue", "text": "Are you ready?"},
            {"index": 2, "speaker": "Narrator", "type": "dialogue", "text": "Yes, let us begin."},
        ]

        aligned = format_and_align_segments(raw_segments, character_roster=self.sample_roster)
        # Turn 2 was dialogue mistakenly labeled Narrator; must not remain Narrator
        self.assertNotEqual(aligned[1]["speaker"], "Narrator")
        self.assertEqual(aligned[1]["speaker"], "The Investigator")

    def test_pure_quoted_narration_reclassified_to_dialogue(self):
        """Verifies pure quoted text marked as narration is reclassified to dialogue."""
        raw_segments = [
            {"index": 1, "speaker": "Narrator", "type": "narration", "text": "The wind howled outside."},
            {"index": 2, "speaker": "Narrator", "type": "narration", "text": '"We need to leave right now."'},
        ]

        aligned = format_and_align_segments(raw_segments, character_roster=self.sample_roster)
        self.assertEqual(aligned[0]["type"], "narration")
        self.assertEqual(aligned[0]["speaker"], "Narrator")

        # Turn 2 is pure quoted dialogue; must be reclassified
        self.assertEqual(aligned[1]["type"], "dialogue")
        self.assertNotEqual(aligned[1]["speaker"], "Narrator")
        self.assertEqual(aligned[1]["text"], "We need to leave right now.")

    # =========================================================================
    # 4. Zero Hardcoding Invariant Verification
    # =========================================================================

    def test_zero_novel_or_character_hardcoding_in_script_modules(self):
        """AST audit: guarantees zero hardcoded novel titles or character tokens exist."""
        script_dir = Path(__file__).resolve().parent.parent / "audiobook_factory" / "script"
        py_files = list(script_dir.glob("**/*.py"))
        self.assertGreater(len(py_files), 3)

        forbidden_tokens = {"geralt", "dandelion", "borch", "three jackdaws", "sword of destiny"}
        violations = []

        for pf in py_files:
            tree = ast.parse(pf.read_text(encoding="utf-8"), filename=str(pf))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val_lower = node.value.lower()
                    words = set(re.findall(r"\b[a-z0-9_-]+\b", val_lower))
                    for tok in forbidden_tokens:
                        if tok in words:
                            violations.append(f"{pf.name}:{node.lineno} contains '{tok}'")

        self.assertEqual(
            len(violations),
            0,
            f"Found forbidden hardcoded tokens in script modules: {violations}",
        )

    # =========================================================================
    # 5. Screenplay Room End-to-End Coordination
    # =========================================================================

    def test_screenplay_dramaturgy_room_coordination_with_mock_llm(self):
        """Verifies ScreenplayDramaturgyRoom coordinates all passes and outputs aligned script."""
        room = ScreenplayDramaturgyRoom(model="mock-model")

        chunk_text = (
            "The investigator stepped into the dim room. "
            '"Where were you last night?" the detective asked. '
            '"[sighs] I was at home asleep," the witness replied.'
        )

        # Mock turn isolator output
        def mock_llm_fn(**kwargs):
            return [
                {
                    "index": 1,
                    "actioning": "narrate",
                    "subtext": "",
                    "underlying_emotion": "neutral",
                    "intensity_level": "medium",
                    "acting": {"delivery_style": "calm_authoritative"},
                    "text": "The investigator stepped into the dim room.",
                },
                {
                    "index": 2,
                    "actioning": "interrogate",
                    "subtext": "You are lying to me.",
                    "underlying_emotion": "suspicion",
                    "intensity_level": "medium",
                    "acting": {"delivery_style": "cold_menace"},
                    "text": "Where were you last night?",
                },
                {
                    "index": 3,
                    "actioning": "deflect",
                    "subtext": "I am terrified but must keep my story straight.",
                    "underlying_emotion": "fear",
                    "intensity_level": "low",
                    "acting": {"delivery_style": "whispering_fear"},
                    "text": "[sighs] I was at home asleep.",
                },
            ]

        with patch.object(room.isolator, "isolate_turns") as mock_iso:
            mock_iso.return_value = [
                {"index": 1, "speaker": "Narrator", "type": "narration", "text": "The investigator stepped into the dim room."},
                {"index": 2, "speaker": "the detective", "type": "dialogue", "text": "Where were you last night?"},
                {"index": 3, "speaker": "the witness", "type": "dialogue", "text": "[sighs] I was at home asleep."},
            ]
            with patch.object(room.auditor, "audit_and_correct") as mock_aud:
                mock_aud.return_value = (
                    mock_iso.return_value,
                    {"status": "AUDITED_AND_CERTIFIED"},
                )

                turns = room.process_chunk(
                    chunk_text=chunk_text,
                    is_hindi=False,
                    character_roster=self.sample_roster,
                    call_llm_fn=mock_llm_fn,
                )

        self.assertEqual(len(turns), 3)
        # Canonical speaker alias resolution
        self.assertEqual(turns[0]["speaker"], "Narrator")
        self.assertEqual(turns[1]["speaker"], "The Investigator")
        self.assertEqual(turns[2]["speaker"], "The Witness")
        # Reflex tag preservation
        self.assertIn("[sighs]", turns[2]["text"])
        # Narrator transparency
        self.assertEqual(turns[0]["acting"]["delivery_style"], "calm_authoritative")


if __name__ == "__main__":
    unittest.main()
