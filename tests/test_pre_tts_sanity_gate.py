#!/usr/bin/env python3
"""
Test Suite: Gate 2.9 (Pre-TTS Config & Attribution Sanity Gate).
================================================================
Validates:
1. Valid audiobook & podcast scripts pass.
2. Unregistered / misspelled speakers fail closed.
3. Swallowed quotes in narrator lines fail closed.
4. Hindi grammatical gender discordance (Speaker Inversion) is detected.
5. Speech verb tag co-reference mismatch is detected.
6. Out-of-bounds acoustic parameters (pitch, speed, null voice_id) fail closed.
7. Text hygiene (empty dialogue, markdown fences) fails closed.
8. Podcast stereo spatial pan and host validation.
9. Integration with PodcastOrchestrator pre-synthesis verification.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from audiobook_factory.gates.pre_synthesis import (
    PreSynthesisGate,
    audit_gate2_9_pre_tts_sanity,
)
from audiobook_factory.gates.contracts import GateAuditError, AuditResult
from audiobook_factory.podcast.orchestrator import PodcastOrchestrator


class TestPreTTSSanityGate:

    @pytest.fixture
    def mock_project(self, tmp_path):
        """Creates a mock project folder with character roster and voice registry."""
        pdir = tmp_path / "test_book_project"
        pdir.mkdir()

        # Character Roster
        roster = {
            "characters": {
                "Geralt": {
                    "english_name": "Geralt",
                    "hindi_name": "गेराल्ट",
                    "gender": "male",
                    "aliases": ["Witcher", "White Wolf"],
                },
                "Renfri": {
                    "english_name": "Renfri",
                    "hindi_name": "रेन्फ्री",
                    "gender": "female",
                    "aliases": ["Shrike"],
                },
            }
        }
        (pdir / "character_roster.json").write_text(json.dumps(roster, ensure_ascii=False), encoding="utf-8")

        # Voice Registry
        voice_reg = {
            "Geralt": {"voice": "Fenrir", "gender": "male", "pitch": 0.95, "speed": 1.0},
            "Renfri": {"voice": "Aoede", "gender": "female", "pitch": 1.05, "speed": 1.0},
            "Narrator": {"voice": "Puck", "gender": "neutral", "pitch": 1.0, "speed": 1.0},
        }
        (pdir / "voice_registry.json").write_text(json.dumps(voice_reg, ensure_ascii=False), encoding="utf-8")

        return pdir

    def test_01_valid_audiobook_script_passes(self, mock_project):
        """Valid screenplay with registered characters and safe acoustic parameters passes Gate 2.9."""
        valid_script = [
            {"index": 1, "speaker": "Narrator", "type": "narration", "text": "The wind howled outside the tavern."},
            {"index": 2, "speaker": "Geralt", "type": "dialogue", "text": "मैं यहाँ किसी झगड़े के लिए नहीं आया हूँ।", "pitch_shift": 0.95, "speed_multiplier": 1.0},
            {"index": 3, "speaker": "Renfri", "type": "dialogue", "text": "तुम चाहे जो भी कहो, फैसला तो तलवार ही करेगी।", "pitch_shift": 1.05, "speed_multiplier": 1.0},
        ]

        res = audit_gate2_9_pre_tts_sanity(
            script_file=valid_script,
            project_dir=mock_project,
            format_mode="audiobook",
            strict=True,
        )

        assert res.passed is True
        assert res.status == "PASS"
        assert len(res.errors) == 0

    def test_02_unregistered_speaker_fails_closed(self, mock_project):
        """An unregistered / misspelled character strictly halts synthesis via GateAuditError."""
        invalid_script = [
            {"index": 1, "speaker": "Narrator", "type": "narration", "text": "Someone entered."},
            {"index": 2, "speaker": "UnknownBandit_99", "type": "dialogue", "text": "Drop your coins!"},
        ]

        with pytest.raises(GateAuditError, match="Unregistered speaker 'UnknownBandit_99'"):
            audit_gate2_9_pre_tts_sanity(
                script_file=invalid_script,
                project_dir=mock_project,
                strict=True,
            )

    def test_03_swallowed_quotes_in_narrator_fails(self, mock_project):
        """Direct dialogue quotes trapped inside Narrator lines trigger anti-swallow failure."""
        swallowed_script = [
            {"index": 1, "speaker": "Narrator", "type": "narration", "text": 'Geralt stepped forward and said: "Stay back or die!"'},
        ]

        with pytest.raises(GateAuditError, match="Direct dialogue quote swallowed into Narrator line"):
            audit_gate2_9_pre_tts_sanity(
                script_file=swallowed_script,
                project_dir=mock_project,
                strict=True,
            )

    def test_04_gender_discordance_speaker_swap_detection(self, mock_project):
        """Detects Hindi first-person verb inflection discordance as a Speaker Inversion warning."""
        discordant_script = [
            # Renfri is registered as female, but spoken with masculine "रहा हूँ"
            {"index": 1, "speaker": "Renfri", "type": "dialogue", "text": "मैं खुद वहाँ जा रहा हूँ और फैसला करूँगा।"},
        ]

        res = audit_gate2_9_pre_tts_sanity(
            script_file=discordant_script,
            project_dir=mock_project,
            strict=False,
        )

        assert any("Possible Speaker Inversion" in w and "Female character 'Renfri'" in w for w in res.warnings)

    def test_05_speech_verb_co_reference_mismatch(self, mock_project):
        """Detects lead-in tag naming Geralt, but dialogue assigned to Renfri."""
        mismatched_script = [
            {"index": 1, "speaker": "Narrator", "type": "narration", "text": "Geralt said:"},
            {"index": 2, "speaker": "Renfri", "type": "dialogue", "text": "We must leave now."},
        ]

        res = audit_gate2_9_pre_tts_sanity(
            script_file=mismatched_script,
            project_dir=mock_project,
            strict=False,
        )

        assert any("Speech verb tag co-reference mismatch" in w for w in res.warnings)

    def test_06_acoustic_range_clamping_fails(self, mock_project):
        """Out-of-bounds pitch_shift or speed_multiplier fails closed."""
        # Extreme pitch shift
        bad_pitch_script = [
            {"index": 1, "speaker": "Geralt", "type": "dialogue", "text": "Testing pitch.", "pitch_shift": 1.95},
        ]
        with pytest.raises(GateAuditError, match="Out-of-bounds pitch_shift 1.95"):
            audit_gate2_9_pre_tts_sanity(script_file=bad_pitch_script, project_dir=mock_project, strict=True)

        # Extreme speed
        bad_speed_script = [
            {"index": 1, "speaker": "Geralt", "type": "dialogue", "text": "Testing speed.", "speed_multiplier": 2.5},
        ]
        with pytest.raises(GateAuditError, match="Out-of-bounds speed_multiplier 2.5"):
            audit_gate2_9_pre_tts_sanity(script_file=bad_speed_script, project_dir=mock_project, strict=True)

    def test_07_text_hygiene_markdown_fences_and_empty_text(self, mock_project):
        """Leaked markdown fences or empty dialogue strings fail closed."""
        # Leaked fence
        fence_script = [
            {"index": 1, "speaker": "Geralt", "type": "dialogue", "text": "```json\nHello\n```"},
        ]
        with pytest.raises(GateAuditError, match="leaked markdown fences"):
            audit_gate2_9_pre_tts_sanity(script_file=fence_script, project_dir=mock_project, strict=True)

        # Empty text
        empty_script = [
            {"index": 1, "speaker": "Geralt", "type": "dialogue", "text": "   "},
        ]
        with pytest.raises(GateAuditError, match="empty or whitespace-only dialogue text"):
            audit_gate2_9_pre_tts_sanity(script_file=empty_script, project_dir=mock_project, strict=True)

    def test_08_podcast_mode_host_pan_and_validation(self, mock_project):
        """Podcast mode validates Host A left pan, Host B right pan, and host roster."""
        podcast_script = [
            {"index": 1, "speaker": "Host_A", "type": "dialogue", "text": "Welcome to our discussion today.", "pan": -0.25},
            {"index": 2, "speaker": "Host_B", "type": "dialogue", "text": "Thanks! It is great to be here.", "pan": 0.25},
        ]

        res = audit_gate2_9_pre_tts_sanity(
            script_file=podcast_script,
            project_dir=mock_project,
            format_mode="podcast",
            strict=True,
        )
        assert res.passed is True

        # Invalid pan
        bad_pan_script = [
            {"index": 1, "speaker": "Host_A", "type": "dialogue", "text": "Welcome.", "pan": 2.5},
        ]
        with pytest.raises(GateAuditError, match="Invalid stereo pan 2.5"):
            audit_gate2_9_pre_tts_sanity(script_file=bad_pan_script, project_dir=mock_project, format_mode="podcast", strict=True)

    def test_09_podcast_orchestrator_integration(self, mock_project):
        """PodcastOrchestrator invokes Gate 2.9 before synthesis and aborts on corrupt script."""
        orchestrator = PodcastOrchestrator(model="mock-model")
        scripts_dir = mock_project / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        # Write invalid script with unknown speaker
        bad_script_path = scripts_dir / "chapter_001_podcast_script.json"
        bad_script_path.write_text(
            json.dumps([
                {"index": 1, "speaker": "RogueSpeaker_Unknown", "type": "dialogue", "text": "Should fail gate."},
            ]),
            encoding="utf-8",
        )

        with pytest.raises(GateAuditError, match="Unregistered speaker 'RogueSpeaker_Unknown'"):
            orchestrator.synthesize_podcast_script(
                project_dir=mock_project,
                chapter_num=1,
                script_file=bad_script_path,
            )
