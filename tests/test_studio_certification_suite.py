#!/usr/bin/env python3
"""
Audiobook Factory - 8-Pillar Studio Certification Test Suite.
Verifies automated auditing of all 8 production pillars, fail-closed defect detection,
and serialization/deserialization of StudioCertificationReport scorecards.
"""

import json
import pytest
from pathlib import Path

from audiobook_factory.certification.contracts import (
    PillarAuditResult,
    StudioCertificationReport,
)
from audiobook_factory.certification.runner import StudioCertificationRunner
from audiobook_factory.podcast.contracts import PodcastEpisodePlan, HostProfile, PodcastSegment


@pytest.fixture
def mock_fully_compliant_project(tmp_path: Path) -> Path:
    """Creates a mock project directory with valid deliverables across all 8 pillars."""
    project_dir = tmp_path / "mock_sword_of_destiny"
    project_dir.mkdir(parents=True, exist_ok=True)

    # 1. Extraction
    extracted_dir = project_dir / "extracted"
    extracted_dir.mkdir()
    (extracted_dir / "chapter_001.md").write_text(
        "# Chapter 1: The Bounds of Reason\n" * 10, encoding="utf-8"
    )

    # 2. Translation
    translation_dir = project_dir / "translation"
    translation_dir.mkdir()
    (translation_dir / "chapter_001.md").write_text(
        "# अध्याय १: मर्यादा की सीमाएँ\n" * 10, encoding="utf-8"
    )

    # 3. Dramaturgy & SPU alignment
    dramaturgy_dir = project_dir / "dramaturgy"
    dramaturgy_dir.mkdir()
    plan_data = {
        "chapter_id": "ch01",
        "scene_plans": [
            {
                "scene_idx": 0,
                "title": "Tavern Confrontation",
                "start_paragraph_idx": 0,
                "end_paragraph_idx": 5,
                "spu_ids": ["spu_001"],
            }
        ]
    }
    (dramaturgy_dir / "chapter_001_plan.json").write_text(
        json.dumps(plan_data, indent=2), encoding="utf-8"
    )

    # 4. Attribution & 5. Performance
    scripts_dir = project_dir / "scripts"
    scripts_dir.mkdir()
    script_data = [
        {
            "index": 0,
            "speaker": "Narrator",
            "text": "The wind howled through the ruined stone towers.",
            "acting": "calm, steady, articulate, measured audiobook delivery",
            "pacing_factor": 1.0,
        },
        {
            "index": 1,
            "speaker": "Geralt",
            "text": "Step away from the bridge.",
            "acting": "understated natural dialogue (never theatrical)",
            "pacing_factor": 1.0,
        },
    ]
    (scripts_dir / "chapter_001_script.json").write_text(
        json.dumps(script_data, indent=2), encoding="utf-8"
    )

    # 6. Loudness & Mastered Files
    mastered_dir = project_dir / "mastered"
    mastered_dir.mkdir()
    (mastered_dir / "chapter_001_mastered.m4a").write_bytes(b"MOCK_MASTERED_AUDIO_CH1")

    # 7. Spatial Staging & Podcast Track
    podcasts_dir = project_dir / "podcasts"
    podcasts_dir.mkdir()
    podcast_plan = PodcastEpisodePlan(
        episode_id="ep_001",
        episode_title="The Witcher Breakdown Episode 1",
        source_chapter_id="ch01",
        language="hi",
        hosts={
            "host_a": HostProfile(host_id="host_a", name="Sameer", role="inquisitive_driver", voice_id="Puck", pan=-0.25),
            "host_b": HostProfile(host_id="host_b", name="Priya", role="domain_expert", voice_id="Kore", pan=0.25),
        },
        hook_statement="Did Geralt break the Witcher code?",
        segments=[
            PodcastSegment(
                index=1,
                speaker="Sameer",
                text="Welcome back everyone.",
                section_type="cold_open_hook",
            )
        ],
        total_duration_estimate_sec=60.0,
        target_lufs=-16.0,
    )
    podcast_plan.save_to_file(podcasts_dir / "episode_001_podcast_plan.json")
    (podcasts_dir / "episode_001_podcast.m4a").write_bytes(b"MOCK_PODCAST_EP1")

    # 8. Packaging Deliverables
    (project_dir / "mock_sword_of_destiny.m4b").write_bytes(b"MOCK_M4B_CONTAINER")
    packaged_podcasts_dir = project_dir / "packaged_podcasts"
    packaged_podcasts_dir.mkdir()
    (packaged_podcasts_dir / "episode_001_packaged.m4a").write_bytes(b"MOCK_PACKAGED_PODCAST")

    return project_dir


def test_studio_certification_fully_compliant(mock_fully_compliant_project: Path):
    """Verify that a compliant project passes all 8 pillars and achieves is_certified=True."""
    report = StudioCertificationRunner.certify_project(
        mock_fully_compliant_project, format_mode="both"
    )

    assert report.is_certified is True
    assert report.overall_score == 100.0
    assert len(report.pillars) == 8

    for pid, res in report.pillars.items():
        assert res.status == "PASSED", f"Pillar {pid} failed: {res.critical_findings}"
        assert len(res.critical_findings) == 0

    # Verify JSON persistence
    saved_report_file = mock_fully_compliant_project / "STUDIO_CERTIFICATION_REPORT.json"
    assert saved_report_file.exists()

    reloaded = StudioCertificationReport.load_from_file(saved_report_file)
    assert reloaded.project_id == report.project_id
    assert reloaded.is_certified is True
    assert reloaded.overall_score == 100.0


def test_studio_certification_fail_closed_critical_defects(tmp_path: Path):
    """Verify that critical defects in any pillar trigger is_certified=False."""
    bad_project = tmp_path / "bad_project"
    bad_project.mkdir()

    # 1. Extraction has empty file (< 50 bytes)
    extracted_dir = bad_project / "extracted"
    extracted_dir.mkdir()
    (extracted_dir / "chapter_001.md").write_text("tiny", encoding="utf-8")

    # 2. Translation has untranslated placeholder
    translation_dir = bad_project / "translation"
    translation_dir.mkdir()
    (translation_dir / "chapter_001.md").write_text(
        "Some text [UNTRANSLATED] line here", encoding="utf-8"
    )

    # 3. Dramaturgy non-monotonic segment indices
    scripts_dir = bad_project / "scripts"
    scripts_dir.mkdir()
    bad_script = [
        {"index": 2, "speaker": "", "text": "Empty speaker line", "acting": "screeching and hysterical"},
        {"index": 1, "speaker": "Geralt", "text": "Valid text", "acting": "calm"},
    ]
    (scripts_dir / "chapter_001_script.json").write_text(
        json.dumps(bad_script, indent=2), encoding="utf-8"
    )

    report = StudioCertificationRunner.certify_project(bad_project, format_mode="both")

    assert report.is_certified is False
    assert report.overall_score < 80.0

    # Check specific pillar failures
    assert report.pillars["P1_EXTRACTION"].status == "FAILED"
    assert any("Empty or corrupted" in f for f in report.pillars["P1_EXTRACTION"].critical_findings)

    assert report.pillars["P2_TRANSLATION"].status == "FAILED"
    assert any("Untranslated placeholder" in f for f in report.pillars["P2_TRANSLATION"].critical_findings)

    assert report.pillars["P3_DRAMATURGY"].status == "FAILED"
    assert any("Non-monotonic" in f for f in report.pillars["P3_DRAMATURGY"].critical_findings)

    assert report.pillars["P4_ATTRIBUTION"].status == "FAILED"
    assert any("Empty speaker" in f for f in report.pillars["P4_ATTRIBUTION"].critical_findings)

    assert report.pillars["P5_PERFORMANCE"].status == "FAILED"
    assert any("Banned theatrical directive" in f for f in report.pillars["P5_PERFORMANCE"].critical_findings)


def test_studio_certification_spatial_staging_checks(tmp_path: Path):
    """Verify spatial staging checks for insufficiently panned podcast hosts."""
    proj = tmp_path / "spatial_proj"
    proj.mkdir()
    podcasts_dir = proj / "podcasts"
    podcasts_dir.mkdir()

    # Host A and Host B both centered (pan=0.0) -> should trigger warning and reduce P7 score
    unpanned_plan = PodcastEpisodePlan(
        episode_id="ep_001",
        episode_title="Centered Hosts",
        source_chapter_id="ch01",
        language="en",
        hosts={
            "host_a": HostProfile(host_id="host_a", name="Alex", role="inquisitive_driver", voice_id="Puck", pan=0.0),
            "host_b": HostProfile(host_id="host_b", name="Maya", role="domain_expert", voice_id="Kore", pan=0.0),
        },
        hook_statement="Centered audio",
        segments=[],
        total_duration_estimate_sec=10.0,
        target_lufs=-16.0,
    )
    unpanned_plan.save_to_file(podcasts_dir / "ep1_podcast_plan.json")

    # In podcast mode, P7 should have warnings
    p7_pod = StudioCertificationRunner._audit_spatial_staging(proj, format_mode="podcast")
    assert p7_pod.status == "WARNING"
    assert len(p7_pod.warnings) >= 2
    assert p7_pod.score < 100.0

    # In audiobook mode, P7 should be SKIPPED cleanly
    p7_audiobook = StudioCertificationRunner._audit_spatial_staging(proj, format_mode="audiobook")
    assert p7_audiobook.status == "SKIPPED"
    assert p7_audiobook.score == 100.0


def test_cmd_audit_book_scorecard_execution(mock_fully_compliant_project: Path, monkeypatch, capsys):
    """Verify that cmd_audit_book runs macro Gate 6 and prints 8-Pillar Scorecard without crashing."""
    from audiobook_factory.cli.commands.audit import cmd_audit_book
    import types

    args = types.SimpleNamespace(project_dir=str(mock_fully_compliant_project), certify=True)
    
    # Mock audit_book_master so macro Gate 6 returns passed
    with monkeypatch.context() as m:
        m.setattr(
            "audiobook_factory.cli.commands.audit.audit_book_master",
            lambda p: {
                "overall_passed": True,
                "overall_status": "PASSED",
                "gate_6a": {"status": "PASSED"},
                "gate_6b": {"status": "PASSED", "details": {"average_lufs": -19.0}},
                "gate_6c": {"status": "PASSED", "details": {"total_chapters": 1}},
                "gate_6d": {"status": "PASSED"},
            }
        )
        cmd_audit_book(args)

    captured = capsys.readouterr()
    assert "8-PILLAR STUDIO PRODUCTION CERTIFICATION SCORECARD" in captured.out
    assert "Extraction & Provenance" in captured.out
    assert "OVERALL SCORE: 100.0%" in captured.out
    assert "🏆 CERTIFIED" in captured.out

