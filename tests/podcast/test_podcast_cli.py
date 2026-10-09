#!/usr/bin/env python3
"""
Unit and integration tests for the Podcast CLI and Orchestrator Subsystem (Phase 4).
Tests CLI argument parsing, subcommands (produce, script, render, inspect),
and unified end-to-end programmatic orchestration on scientific research papers.
"""

import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from audiobook_factory.podcast.cli import main as podcast_cli_main, create_podcast_parser
from audiobook_factory.podcast.orchestrator import (
    PodcastOrchestrator,
    process_document_to_podcast,
)
from audiobook_factory.podcast.contracts import PodcastProductionResult


@pytest.fixture
def temp_workspace(tmp_path: Path):
    """Provides an isolated workspace directory."""
    ws = tmp_path / "podcast_cli_workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def benchmark_paper_path() -> Path:
    """Returns path to the benchmark sample research paper."""
    p = Path("benchmarks/sample_research_paper.md")
    if not p.exists():
        pytest.skip("Benchmark sample_research_paper.md not found.")
    return p


def test_01_podcast_cli_parser_structure():
    """Verifies that the podcast CLI parser has all required subcommands and arguments."""
    parser = create_podcast_parser()
    assert parser.prog == "podcast"

    # Test produce args
    produce_args = parser.parse_args(["produce", "paper.pdf", "--mock", "--style", "conversational_podcast"])
    assert produce_args.subcommand == "produce"
    assert produce_args.file == "paper.pdf"
    assert produce_args.mock is True
    assert produce_args.style == "conversational_podcast"

    # Test script args
    script_args = parser.parse_args(["script", "paper.md", "--host-a-voice", "Charon"])
    assert script_args.subcommand == "script"
    assert script_args.file == "paper.md"
    assert script_args.host_a_voice == "Charon"

    # Test render args
    render_args = parser.parse_args(["render", "script.json", "--mock"])
    assert render_args.subcommand == "render"
    assert render_args.script_file == "script.json"
    assert render_args.mock is True

    # Test inspect args
    inspect_args = parser.parse_args(["inspect", "manifest.json"])
    assert inspect_args.subcommand == "inspect"
    assert inspect_args.path == "manifest.json"


def test_02_cli_script_subcommand(temp_workspace: Path, benchmark_paper_path: Path):
    """Verifies that the 'script' subcommand ingests document and writes podcast_script.json."""
    out_dir = temp_workspace / "script_test"
    ret = podcast_cli_main([
        "script",
        str(benchmark_paper_path),
        "--output-dir",
        str(out_dir),
    ])

    assert ret == 0
    script_file = out_dir / "podcast_script.json"
    assert script_file.exists()

    with open(script_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "segments" in data
    assert len(data["segments"]) > 0


def test_03_cli_produce_subcommand_mock(temp_workspace: Path, benchmark_paper_path: Path):
    """Verifies full end-to-end 1-shot production via CLI produce subcommand."""
    out_dir = temp_workspace / "produce_test"
    ret = podcast_cli_main([
        "produce",
        str(benchmark_paper_path),
        "--output-dir",
        str(out_dir),
        "--mock",
    ])

    assert ret == 0
    assert (out_dir / "canonical" / "book.json").exists()
    assert (out_dir / "podcast_script.json").exists()
    assert (out_dir / "production" / "editorial").exists()
    assert (out_dir / "production" / "mastered").exists()

    # Verify manifest
    manifest_files = list((out_dir / "production").glob("*_production_manifest.json"))
    assert len(manifest_files) >= 1
    with open(manifest_files[0], "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["status"] == "SUCCESS"
    assert manifest["integrated_lufs"] == -19.0


def test_04_cli_render_subcommand_mock(temp_workspace: Path, benchmark_paper_path: Path):
    """Verifies rendering existing podcast_script.json via CLI render subcommand."""
    # First generate script
    script_dir = temp_workspace / "render_script_stage"
    podcast_cli_main(["script", str(benchmark_paper_path), "--output-dir", str(script_dir)])
    script_file = script_dir / "podcast_script.json"
    assert script_file.exists()

    # Now render script
    render_dir = temp_workspace / "render_audio_stage"
    ret = podcast_cli_main([
        "render",
        str(script_file),
        "--output-dir",
        str(render_dir),
        "--mock",
    ])

    assert ret == 0
    assert (render_dir / "mastered").exists()
    mastered_files = list((render_dir / "mastered").glob("*.wav"))
    assert len(mastered_files) >= 1


def test_05_cli_inspect_subcommand(temp_workspace: Path, benchmark_paper_path: Path):
    """Verifies inspect subcommand on script and manifest files."""
    test_dir = temp_workspace / "inspect_test"
    podcast_cli_main(["produce", str(benchmark_paper_path), "--output-dir", str(test_dir), "--mock"])

    script_file = test_dir / "podcast_script.json"
    ret_script = podcast_cli_main(["inspect", str(script_file)])
    assert ret_script == 0

    manifest_files = list((test_dir / "production").glob("*_production_manifest.json"))
    assert len(manifest_files) >= 1
    ret_manifest = podcast_cli_main(["inspect", str(manifest_files[0])])
    assert ret_manifest == 0


def test_06_orchestrator_programmatic_api(temp_workspace: Path, benchmark_paper_path: Path):
    """Verifies programmatic PodcastOrchestrator execution and parameter overrides."""
    orchestrator = PodcastOrchestrator(projects_dir=temp_workspace)
    result = orchestrator.process_document_to_podcast(
        source_file=benchmark_paper_path,
        output_dir=temp_workspace / "programmatic_run",
        host_a_name="Prof. Harrison",
        host_a_voice="Fenrir",
        host_b_name="Alex",
        host_b_voice="Puck",
        mock_mode=True,
    )

    assert isinstance(result, PodcastProductionResult)
    assert result.status == "SUCCESS"
    assert result.total_segments > 0
    assert result.duration_sec > 0.0
    assert Path(result.canonical_book_path).exists()
    assert Path(result.script_path).exists()
    assert Path(result.mastered_audio_path).exists()


def test_07_root_audiobook_cli_podcast_dispatch(temp_workspace: Path, benchmark_paper_path: Path):
    """Verifies root audiobook_cli.py dispatches podcast subcommand correctly."""
    from audiobook_cli import main as root_cli_main

    out_dir = temp_workspace / "root_cli_podcast_test"
    test_args = [
        "audiobook_cli.py",
        "podcast",
        str(benchmark_paper_path),
        "--output-dir",
        str(out_dir),
        "--mock",
    ]

    with patch.object(sys, "argv", test_args):
        try:
            root_cli_main()
        except SystemExit as e:
            assert e.code == 0 or e.code is None

    assert (out_dir / "podcast_script.json").exists()
    assert (out_dir / "production" / "mastered").exists()
