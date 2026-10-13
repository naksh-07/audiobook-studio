#!/usr/bin/env python3
"""
Audiobook Factory - End-to-End Autonomous Pipeline Simulation Suite.
Simulates end-to-end production runs across 'audiobook', 'podcast', and 'both' modes,
verifying gate validation, artifact generation, telemetry logging, and studio certification.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from audiobook_factory.orchestrator import PipelineOrchestrator
from audiobook_factory.certification.runner import StudioCertificationRunner
from audiobook_factory.podcast.contracts import PodcastEpisodePlan, HostProfile, PodcastSegment


@pytest.fixture
def mock_pipeline_environment(tmp_path: Path):
    """Sets up a temporary directory and dummy input file for pipeline simulation."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    input_file = tmp_path / "The_Witcher_Blood_of_Elves.txt"
    input_file.write_text("# Chapter 1: The Town of Oxenfurt\n\nSome novel text here...", encoding="utf-8")

    return projects_dir, input_file


def test_pipeline_simulation_both_tracks(mock_pipeline_environment):
    """Simulates a full dual-track autonomous run ('both' format mode)."""
    projects_dir, input_file = mock_pipeline_environment
    orchestrator = PipelineOrchestrator(projects_dir=projects_dir)

    book_slug = "the_witcher_blood_of_elves"
    project_dir = projects_dir / book_slug
    project_dir.mkdir(parents=True, exist_ok=True)

    # Setup directories
    extracted_dir = project_dir / "extracted"
    extracted_dir.mkdir(exist_ok=True)
    (extracted_dir / "chapter_001.md").write_text("# Chapter 1\n" * 10, encoding="utf-8")

    translation_dir = project_dir / "translation"
    translation_dir.mkdir(exist_ok=True)
    (translation_dir / "chapter_001.md").write_text("# अध्याय १\n" * 10, encoding="utf-8")

    scripts_dir = project_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    script_data = [
        {"index": 0, "speaker": "Narrator", "text": "The wind howled.", "acting": "calm delivery"},
        {"index": 1, "speaker": "Geralt", "text": "Halt.", "acting": "calm dialogue"},
    ]
    (scripts_dir / "chapter_001_script.json").write_text(json.dumps(script_data), encoding="utf-8")

    podcasts_dir = project_dir / "podcasts"
    podcasts_dir.mkdir(exist_ok=True)
    pod_plan = PodcastEpisodePlan(
        episode_id="ep_001",
        episode_title="Blood of Elves Episode 1",
        source_chapter_id="ch01",
        language="hi",
        hosts={
            "host_a": HostProfile(host_id="host_a", name="Sameer", role="inquisitive_driver", voice_id="Puck", pan=-0.25),
            "host_b": HostProfile(host_id="host_b", name="Priya", role="domain_expert", voice_id="Kore", pan=0.25),
        },
        hook_statement="Hook line",
        segments=[],
        total_duration_estimate_sec=30.0,
        target_lufs=-16.0,
    )
    pod_plan.save_to_file(podcasts_dir / "chapter_001_podcast_plan.json")

    mastered_dir = project_dir / "mastered"
    mastered_dir.mkdir(exist_ok=True)
    (mastered_dir / "chapter_001_mastered.m4a").write_bytes(b"MASTERED_AUDIO")

    mock_m4b = project_dir / "the_witcher_blood_of_elves.m4b"
    mock_m4b.write_bytes(b"MOCK_M4B")

    packaged_podcasts_dir = project_dir / "packaged_podcasts"
    packaged_podcasts_dir.mkdir(exist_ok=True)
    mock_pod_pkg = packaged_podcasts_dir / "chapter_001_podcast.m4a"
    mock_pod_pkg.write_bytes(b"MOCK_PODCAST_M4A")

    with patch("audiobook_factory.orchestrator.process_book_file") as mock_extract, \
         patch("audiobook_factory.preproduction.run_preproduction") as mock_preprod, \
         patch("audiobook_factory.orchestrator.translate_book_project") as mock_trans, \
         patch("audiobook_factory.orchestrator.verify_translation_coverage_gates"), \
         patch("audiobook_factory.orchestrator.generate_project_scripts") as mock_scripts, \
         patch("audiobook_factory.orchestrator.verify_screenplay_project_gates"), \
         patch("audiobook_factory.podcast.generate_project_podcasts") as mock_pod_gen, \
         patch.object(PipelineOrchestrator, "produce_chapter") as mock_prod_chap, \
         patch("audiobook_factory.podcast.orchestrator.PodcastOrchestrator.produce_podcast_episode") as mock_pod_orch, \
         patch("audiobook_factory.packaging.package_project") as mock_pkg, \
         patch("audiobook_factory.orchestrator.verify_packaging_gates"):
        mock_preprod.return_value = {"status": "CACHED_LOCKED"}

        mock_extract.return_value = {
            "book_id": book_slug,
            "title": "Blood of Elves",
            "author": "Andrzej Sapkowski",
            "chapters": [1],
        }
        mock_scripts.return_value = scripts_dir
        mock_prod_chap.return_value = {
            "chapter_id": 1,
            "master_file": mastered_dir / "chapter_001_mastered.m4a",
            "dialogue_file": mastered_dir / "chapter_001_mastered.m4a",
            "ledger_file": scripts_dir / "chapter_001_timeline_ledger.json",
            "duration_min": 1.5,
            "total_segments": 2,
        }
        mock_pod_orch.return_value = {
            "chapter_id": 1,
            "master_file": podcasts_dir / "chapter_001_podcast.m4a",
            "duration_sec": 30.0,
            "total_segments": 1,
        }
        mock_pkg.return_value = {
            "artifacts": {
                "audiobook_m4b": str(mock_m4b),
                "podcast_episodes": [str(mock_pod_pkg)],
            }
        }

        result = orchestrator.run_autonomous_pipeline(
            input_file=input_file,
            hindi=True,
            dramatized=True,
            format_mode="both",
        )

        assert isinstance(result, dict)
        assert result["audiobook_m4b"] == mock_m4b
        assert result["podcast_episodes"] == [mock_pod_pkg]

        # Verify telemetry report was written
        telemetry_file = project_dir / "TELEMETRY_REPORT.json"
        assert telemetry_file.exists()

        # Run Studio Certification on the simulated project
        cert_report = StudioCertificationRunner.certify_project(project_dir, format_mode="both")
        assert cert_report.is_certified is True
        assert cert_report.overall_score == 100.0


def test_pipeline_simulation_podcast_only(mock_pipeline_environment):
    """Simulates a podcast-only autonomous run ('podcast' format mode)."""
    projects_dir, input_file = mock_pipeline_environment
    orchestrator = PipelineOrchestrator(projects_dir=projects_dir)

    book_slug = "the_witcher_blood_of_elves"
    project_dir = projects_dir / book_slug
    project_dir.mkdir(parents=True, exist_ok=True)

    podcasts_dir = project_dir / "podcasts"
    podcasts_dir.mkdir(exist_ok=True)
    pod_plan = PodcastEpisodePlan(
        episode_id="ep_001",
        episode_title="Blood of Elves Episode 1",
        source_chapter_id="ch01",
        language="en",
        hosts={
            "host_a": HostProfile(host_id="host_a", name="Alex", role="inquisitive_driver", voice_id="Puck", pan=-0.25),
            "host_b": HostProfile(host_id="host_b", name="Maya", role="domain_expert", voice_id="Kore", pan=0.25),
        },
        hook_statement="Hook statement",
        segments=[],
        total_duration_estimate_sec=20.0,
        target_lufs=-16.0,
    )
    pod_plan.save_to_file(podcasts_dir / "chapter_001_podcast_plan.json")

    mock_pod_pkg = project_dir / "packaged_podcasts" / "chapter_001_podcast.m4a"
    mock_pod_pkg.parent.mkdir(parents=True, exist_ok=True)
    mock_pod_pkg.write_bytes(b"MOCK_PODCAST_M4A")

    with patch("audiobook_factory.orchestrator.process_book_file") as mock_extract, \
         patch("audiobook_factory.preproduction.run_preproduction") as mock_preprod, \
         patch("audiobook_factory.podcast.generate_project_podcasts") as mock_pod_gen, \
         patch("audiobook_factory.podcast.orchestrator.PodcastOrchestrator.produce_podcast_episode") as mock_pod_orch, \
         patch("audiobook_factory.packaging.package_project") as mock_pkg:
        mock_preprod.return_value = {"status": "CACHED_LOCKED"}

        mock_extract.return_value = {
            "book_id": book_slug,
            "title": "Blood of Elves",
            "author": "Andrzej Sapkowski",
            "chapters": [1],
        }
        mock_pod_orch.return_value = {
            "chapter_id": 1,
            "master_file": podcasts_dir / "chapter_001_podcast.m4a",
            "duration_sec": 20.0,
            "total_segments": 1,
        }
        mock_pkg.return_value = {
            "artifacts": {
                "podcast_episodes": [str(mock_pod_pkg)],
            }
        }

        result = orchestrator.run_autonomous_pipeline(
            input_file=input_file,
            hindi=False,
            dramatized=False,
            format_mode="podcast",
        )

        assert result == mock_pod_pkg


def test_pipeline_simulation_audiobook_only(mock_pipeline_environment):
    """Simulates an audiobook-only autonomous run ('audiobook' format mode)."""
    projects_dir, input_file = mock_pipeline_environment
    orchestrator = PipelineOrchestrator(projects_dir=projects_dir)

    book_slug = "the_witcher_blood_of_elves"
    project_dir = projects_dir / book_slug
    project_dir.mkdir(parents=True, exist_ok=True)

    extracted_dir = project_dir / "extracted"
    extracted_dir.mkdir(exist_ok=True)
    (extracted_dir / "chapter_001.md").write_text("# Chapter 1\n" * 10, encoding="utf-8")

    scripts_dir = project_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    (scripts_dir / "chapter_001_script.json").write_text(json.dumps([{"index": 0, "speaker": "Narrator", "text": "Audiobook text"}]))

    mock_m4b = project_dir / "the_witcher_blood_of_elves.m4b"
    mock_m4b.write_bytes(b"MOCK_M4B")

    with patch("audiobook_factory.orchestrator.process_book_file") as mock_extract, \
         patch("audiobook_factory.preproduction.run_preproduction") as mock_preprod, \
         patch("audiobook_factory.orchestrator.generate_project_scripts") as mock_scripts, \
         patch("audiobook_factory.orchestrator.verify_screenplay_project_gates"), \
         patch.object(PipelineOrchestrator, "produce_chapter") as mock_prod_chap, \
         patch("audiobook_factory.packaging.package_project") as mock_pkg, \
         patch("audiobook_factory.orchestrator.verify_packaging_gates"):
        mock_preprod.return_value = {"status": "CACHED_LOCKED"}

        mock_extract.return_value = {
            "book_id": book_slug,
            "title": "Blood of Elves",
            "author": "Andrzej Sapkowski",
            "chapters": [1],
        }
        mock_scripts.return_value = scripts_dir
        mock_prod_chap.return_value = {
            "chapter_id": 1,
            "master_file": project_dir / "mastered" / "chapter_001_mastered.m4a",
            "dialogue_file": project_dir / "mastered" / "chapter_001_mastered.m4a",
            "ledger_file": scripts_dir / "chapter_001_timeline_ledger.json",
            "duration_min": 1.0,
            "total_segments": 1,
        }
        mock_pkg.return_value = {
            "artifacts": {
                "audiobook_m4b": str(mock_m4b),
            }
        }

        result = orchestrator.run_autonomous_pipeline(
            input_file=input_file,
            hindi=False,
            dramatized=False,
            format_mode="audiobook",
        )

        assert result == mock_m4b

