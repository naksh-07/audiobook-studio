"""
Unit and integration tests for Audiobook Studio Engine Bridge (Phase 1).
Tests JSON APIs, vectorized peak extraction, 5-Room DAG telemetry, and CLI dispatch.
"""

import sys
import json
import time
import subprocess
from pathlib import Path
import pytest

from audiobook_factory.api.studio_bridge import (
    get_engine_status,
    list_projects,
    get_project_detail,
    extract_audio_peaks,
    list_curated_voices,
    WORKSPACE_DIR,
    PROJECTS_DIR,
)

SAMPLE_WAV_PATH = (
    WORKSPACE_DIR
    / "audiobooks"
    / "projects"
    / "sword_of_destiny_-_andrzej_sapkowski__worldfreebooks_com"
    / "audio_chunks"
    / "b0001_narrator_s0001_to_s0002_raw.wav"
)


class TestStudioBridgeEngineStatus:
    def test_get_engine_status_structure(self):
        status = get_engine_status()
        assert isinstance(status, dict)
        assert status["status"] == "ready"
        assert "engine_version" in status
        assert "active_gemini_keys" in status
        assert "total_gemini_keys" in status
        assert status["active_projects_count"] >= 1
        assert Path(status["workspace_dir"]).exists()


class TestStudioBridgeProjects:
    def test_list_projects(self):
        projects = list_projects()
        assert isinstance(projects, list)
        assert len(projects) >= 1
        
        # Check expected keys in each project
        found_sword = False
        for p in projects:
            assert "slug" in p
            assert "title" in p
            assert "progress_percent" in p
            assert "chapters_count" in p
            assert "total_segments" in p
            if p["slug"] == "sword_of_destiny_-_andrzej_sapkowski__worldfreebooks_com":
                found_sword = True
                assert p["total_segments"] > 100
                assert p["progress_percent"] > 90.0
        assert found_sword

    def test_get_project_detail_success(self):
        slug = "sword_of_destiny_-_andrzej_sapkowski__worldfreebooks_com"
        detail = get_project_detail(slug)
        assert isinstance(detail, dict)
        assert detail["slug"] == slug
        assert detail["title"] == "Sword of Destiny"
        assert len(detail["chapters"]) >= 1

        # Check 5-Room DAG
        dag = detail.get("pipeline_dag")
        assert isinstance(dag, dict)
        assert "room1_ingest" in dag
        assert "room2_translate" in dag
        assert "room3_dramaturgy" in dag
        assert "room4_synth" in dag
        assert "room5_master" in dag
        assert dag["room1_ingest"]["status"] == "passed"
        assert dag["room2_translate"]["status"] == "passed"
        assert dag["room3_dramaturgy"]["status"] == "passed"

        # Check recent segments & authentic Hindi script
        recent = detail.get("recent_segments")
        assert isinstance(recent, list)
        assert len(recent) > 0
        first_seg = recent[0]
        assert "text_content" in first_seg
        assert "speaker" in first_seg
        assert "audio_path" in first_seg
        # Check that Hindi characters exist
        assert any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in first_seg["text_content"])

        # Check character roster
        chars = detail.get("characters")
        assert isinstance(chars, list)
        assert len(chars) > 0
        assert any(c.get("sample_audio") is not None for c in chars)

        # Active audio exists
        assert detail.get("active_audio") is not None

    def test_get_project_detail_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            get_project_detail("non_existent_project_slug_xyz")


class TestStudioBridgePeakExtraction:
    @pytest.mark.skipif(not SAMPLE_WAV_PATH.exists(), reason="Sample wav chunk not present on disk")
    def test_extract_audio_peaks_valid(self):
        t0 = time.time()
        res = extract_audio_peaks(str(SAMPLE_WAV_PATH), num_points=400)
        elapsed_ms = (time.time() - t0) * 1000

        # Sub-50ms performance contract
        assert elapsed_ms < 50.0

        assert res["points_count"] == 400
        assert len(res["peaks"]) == 400
        assert res["duration_sec"] > 0.0
        assert res["sample_rate"] > 0

        # Validate range of peaks
        for min_val, max_val in res["peaks"]:
            assert isinstance(min_val, float)
            assert isinstance(max_val, float)
            assert -1.0 <= min_val <= 1.0
            assert -1.0 <= max_val <= 1.0
            assert min_val <= max_val

    @pytest.mark.skipif(not SAMPLE_WAV_PATH.exists(), reason="Sample wav chunk not present on disk")
    def test_extract_audio_peaks_custom_points(self):
        res = extract_audio_peaks(str(SAMPLE_WAV_PATH), num_points=120)
        assert res["points_count"] == 120
        assert len(res["peaks"]) == 120

    def test_extract_audio_peaks_missing_file(self):
        with pytest.raises(FileNotFoundError):
            extract_audio_peaks("non_existent_path.wav")


class TestStudioBridgeVoices:
    def test_list_curated_voices(self):
        voices = list_curated_voices()
        assert isinstance(voices, list)
        assert len(voices) >= 3
        voice_ids = [v.get("voice_id") or v.get("id") for v in voices]
        assert any("Aoede" in str(v) or "hi-in" in str(v) for v in voice_ids)


class TestStudioBridgeCLI:
    def test_cli_status(self):
        cmd = [sys.executable, "-m", "audiobook_factory.api.studio_bridge", "status"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert data["status"] == "ready"

    @pytest.mark.skipif(not SAMPLE_WAV_PATH.exists(), reason="Sample wav chunk not present on disk")
    def test_cli_peaks(self):
        cmd = [
            sys.executable,
            "-m",
            "audiobook_factory.api.studio_bridge",
            "peaks",
            "--path",
            str(SAMPLE_WAV_PATH),
            "--points",
            "50",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert data["points_count"] == 50
        assert len(data["peaks"]) == 50

    def test_cli_project_detail(self):
        cmd = [
            sys.executable,
            "-m",
            "audiobook_factory.api.studio_bridge",
            "project-detail",
            "--slug",
            "sword_of_destiny_-_andrzej_sapkowski__worldfreebooks_com",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert data["slug"] == "sword_of_destiny_-_andrzej_sapkowski__worldfreebooks_com"
        assert "pipeline_dag" in data
        assert "recent_segments" in data
