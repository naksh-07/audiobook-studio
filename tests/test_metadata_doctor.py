#!/usr/bin/env python3
"""
Test Suite: Zero-Token Pre-Flight Metadata Doctor.
Verifies millisecond-fast offline consistency checks across all 5 rooms:
Extraction, Canon, Cast Lock SSOT, Translation Glossary, Screenplay Coverage,
and Mastering V2 EBU R128 Ledgers.
"""

import json
import tempfile
import pytest
from pathlib import Path

from audiobook_factory.metadata.doctor import MetadataDoctor, MetadataDoctorReport
from audiobook_factory.contracts import ScreenplayScript, ScreenplaySegment


class TestMetadataDoctor:

    @pytest.fixture
    def healthy_project(self, tmp_path):
        """Creates a fully consistent, well-formed multi-room project."""
        pdir = tmp_path / "healthy_novel"
        pdir.mkdir()

        # Room 0: Extracted Chapters
        ext_dir = pdir / "extracted"
        ext_dir.mkdir()
        (ext_dir / "chapter_001.md").write_text("# Chapter 1\nSome text here.", encoding="utf-8")
        (pdir / "metadata.json").write_text(json.dumps({"title": "Healthy Novel", "author": "Author"}), encoding="utf-8")

        # Room 1: Canon & Lore (BookBible)
        bible_data = {
            "book_title": "Healthy Novel",
            "author": "Author",
            "entities": {
                "characters": {
                    "Geralt": {
                        "canonical_name": "Geralt",
                        "assigned_voice": "Charon",
                        "pitch_ratio": 0.95,
                        "gender": "male",
                    },
                    "Yennefer": {
                        "canonical_name": "Yennefer",
                        "assigned_voice": "Aoede",
                        "pitch_ratio": 1.05,
                        "gender": "female",
                    },
                },
                "locations": {
                    "Rivia": {"canonical_name": "Rivia"}
                },
            },
        }
        (pdir / "book_bible.json").write_text(json.dumps(bible_data, ensure_ascii=False), encoding="utf-8")

        # Room 1: Cast Lock SSOT
        cast_lock_data = {
            "locks": {
                "Geralt": {
                    "character_name": "Geralt",
                    "voice_id": "Charon",
                    "calibration_overrides": {"pitch": 0.95, "speed": 1.0},
                    "locked": True,
                },
                "Yennefer": {
                    "character_name": "Yennefer",
                    "voice_id": "Aoede",
                    "calibration_overrides": {"pitch": 1.05, "speed": 1.0},
                    "locked": True,
                },
            }
        }
        (pdir / "cast_lock.json").write_text(json.dumps(cast_lock_data, ensure_ascii=False), encoding="utf-8")

        # Room 2: Translation Glossary
        trans_dir = pdir / "translation"
        trans_dir.mkdir()
        glossary_data = {
            "characters": [
                {"english_name": "Geralt", "hindi_name": "गेराल्ट"},
                {"english_name": "Yennefer", "hindi_name": "येनेफ़र"},
            ]
        }
        (trans_dir / "glossary.json").write_text(json.dumps(glossary_data, ensure_ascii=False), encoding="utf-8")

        # Room 3: Screenplay Script
        scripts_dir = pdir / "scripts"
        scripts_dir.mkdir()
        script = ScreenplayScript(
            segments=[
                ScreenplaySegment(index=1, type="narration", speaker="Narrator", text="The night was dark."),
                ScreenplaySegment(index=2, type="dialogue", speaker="Geralt", text="Evil is evil."),
                ScreenplaySegment(index=3, type="dialogue", speaker="Yennefer", text="We must proceed."),
            ]
        )
        (scripts_dir / "chapter_001_script.json").write_text(script.model_dump_json(), encoding="utf-8")

        # Room 5: Mastering V2 Ledger
        mastered_dir = pdir / "mastered"
        mastered_dir.mkdir()
        ledger_data = {
            "chapter_file": "chapter_001.m4a",
            "integrated_lufs": -19.1,
            "true_peak_dbtp": -2.1,
            "loudness_range_lu": 6.5,
            "status": "PASS",
        }
        (mastered_dir / "chapter_001_mastering_ledger.json").write_text(json.dumps(ledger_data), encoding="utf-8")

        return pdir

    def test_01_healthy_project_all_checks_pass(self, healthy_project):
        report = MetadataDoctor.diagnose_project(healthy_project)
        assert isinstance(report, MetadataDoctorReport)
        assert report.passed is True
        assert report.status == "PASS"
        assert report.failed_checks == 0
        assert len(report.errors) == 0
        assert report.is_healthy() is True

        table = report.format_table()
        assert "Overall Status : [OK] PASS" in table
        assert "Extraction Inventory" in table
        assert "Book Bible Canon" in table
        assert "Cast Lock & Voice SSOT" in table
        assert "Mastering V2 Compliance" in table

    def test_02_detects_pitch_bounds_violation(self, healthy_project):
        cast_lock_file = healthy_project / "cast_lock.json"
        data = json.loads(cast_lock_file.read_text(encoding="utf-8"))
        data["locks"]["Geralt"]["calibration_overrides"]["pitch"] = 1.45  # Out of [0.85, 1.15]
        cast_lock_file.write_text(json.dumps(data), encoding="utf-8")

        report = MetadataDoctor.diagnose_project(healthy_project)
        assert report.passed is False
        assert report.status == "FAIL"
        assert any("pitch 1.45 outside 0.85-1.15" in err for err in report.errors)

    def test_03_detects_pitch_collision_warning(self, healthy_project):
        cast_lock_file = healthy_project / "cast_lock.json"
        data = json.loads(cast_lock_file.read_text(encoding="utf-8"))
        # Add another character sharing Charon with identical pitch 0.95 (< 4% separation)
        data["locks"]["Dandelion"] = {
            "character_name": "Dandelion",
            "voice_id": "Charon",
            "calibration_overrides": {"pitch": 0.95, "speed": 1.0},
            "locked": True,
        }
        cast_lock_file.write_text(json.dumps(data), encoding="utf-8")

        report = MetadataDoctor.diagnose_project(healthy_project)
        assert report.passed is True  # Warning, not hard failure
        assert report.status == "WARN"
        assert any("share 'Charon' with only 0.0% pitch separation" in w for w in report.warnings)

    def test_04_detects_unregistered_speaking_character(self, healthy_project):
        scripts_dir = healthy_project / "scripts"
        script = ScreenplayScript(
            segments=[
                ScreenplaySegment(index=1, type="narration", speaker="Narrator", text="The night was dark."),
                ScreenplaySegment(index=2, type="dialogue", speaker="UnknownStranger", text="Who goes there?"),
            ]
        )
        (scripts_dir / "chapter_001_script.json").write_text(script.model_dump_json(), encoding="utf-8")

        report = MetadataDoctor.diagnose_project(healthy_project)
        assert report.passed is False
        assert report.status == "FAIL"
        assert any("UnknownStranger" in err for err in report.errors)

    def test_05_detects_mastering_v2_true_peak_breach(self, healthy_project):
        ledger_file = healthy_project / "mastered" / "chapter_001_mastering_ledger.json"
        data = json.loads(ledger_file.read_text(encoding="utf-8"))
        data["true_peak_dbtp"] = -1.2  # Breaches -2.0 / -1.8 ceiling!
        ledger_file.write_text(json.dumps(data), encoding="utf-8")

        report = MetadataDoctor.diagnose_project(healthy_project)
        assert report.passed is False
        assert report.status == "FAIL"
        assert any("True Peak breach" in err for err in report.errors)

    def test_06_nonexistent_project_fails_safely(self, tmp_path):
        fake_path = tmp_path / "does_not_exist"
        report = MetadataDoctor.diagnose_project(fake_path)
        assert report.passed is False
        assert report.status == "FAIL"
        assert "Project directory not found" in report.errors[0]

    def test_07_studio_bridge_doctor_summary_no_attribute_error(self, healthy_project, monkeypatch):
        from audiobook_factory.api import studio_bridge
        monkeypatch.setattr(studio_bridge, "PROJECTS_DIR", healthy_project.parent)
        
        detail = studio_bridge.get_project_detail(healthy_project.name)
        assert detail is not None
        assert "doctor_summary" in detail
        doc_sum = detail["doctor_summary"]
        assert doc_sum is not None
        assert doc_sum["status"] == "PASS"
        assert doc_sum["overall_healthy"] is True
        assert isinstance(doc_sum["issues"], list)

    def test_08_speaker_coverage_supports_character_roster_and_case_insensitive(self, healthy_project):
        # Remove cast_lock.json and book_bible.json
        (healthy_project / "cast_lock.json").unlink()
        (healthy_project / "book_bible.json").unlink()

        # Add character_roster.json
        roster_data = {
            "characters": {
                "Geralt": {"display_name": "Geralt", "english_name": "Geralt", "assigned_voice_id": "Charon"},
                "Yennefer": {"display_name": "Yennefer", "english_name": "Yennefer", "assigned_voice_id": "Aoede"},
            }
        }
        (healthy_project / "character_roster.json").write_text(json.dumps(roster_data), encoding="utf-8")

        # Add script with lowercase narrator and Foley
        scripts_dir = healthy_project / "scripts"
        script = ScreenplayScript(
            segments=[
                ScreenplaySegment(index=1, type="narration", speaker="narrator", text="The night was dark."),
                ScreenplaySegment(index=2, type="dialogue", speaker="Geralt", text="Evil is evil."),
                ScreenplaySegment(index=3, type="action", speaker="sfx", text="[rain]"),
            ]
        )
        (scripts_dir / "chapter_001_script.json").write_text(script.model_dump_json(), encoding="utf-8")

        report = MetadataDoctor.diagnose_project(healthy_project)
        # Should not fail speaker coverage
        spk_checks = [c for c in report.checks if c.name == "Screenplay Speaker Coverage"]
        assert len(spk_checks) == 1
        assert spk_checks[0].status == "PASS"

    def test_09_gate6b_ledger_discovery_and_true_peak_zero(self, healthy_project):
        from audiobook_factory.gates.album import audit_gate6b_loudness_continuity
        
        # Audio file in media/ subdirectory
        media_dir = healthy_project / "media"
        media_dir.mkdir()
        audio_file = media_dir / "chapter_001.wav"
        audio_file.write_bytes(b"\x00" * 2000)

        # Ledger in mastered/ directory with 0.0 true peak
        ledger_file = healthy_project / "mastered" / "chapter_001_mastering_ledger.json"
        ledger_data = {
            "chapter_id": "chapter_001",
            "metadata": {
                "integrated_lufs": -19.0,
                "true_peak_dbtp": -1.5,
                "true_peak_ceiling_dbtp": -1.4,
            }
        }
        ledger_file.write_text(json.dumps(ledger_data), encoding="utf-8")

        res = audit_gate6b_loudness_continuity([audio_file], strict=False)
        assert res.passed is True
        assert res.status == "PASS"
        assert len(res.errors) == 0
