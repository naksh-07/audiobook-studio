import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from audiobook_factory.orchestrator import PipelineOrchestrator


@pytest.fixture
def mock_novel_file(tmp_path):
    novel_path = tmp_path / "test_novel.txt"
    novel_path.write_text("# Chapter 1: The First Encounter\n\nIt was a quiet evening in the village.\n", encoding="utf-8")
    return novel_path


def test_dual_track_orchestrator_both_mode(tmp_path, mock_novel_file):
    """Test PipelineOrchestrator running both Audiobook and Podcast tracks in one run."""
    projects_dir = tmp_path / "projects"
    orchestrator = PipelineOrchestrator(projects_dir)

    mock_meta = {"book_id": "test_novel", "title": "Test Novel", "author": "Test Author"}

    with patch("audiobook_factory.orchestrator.process_book_file", return_value=mock_meta), \
         patch("audiobook_factory.orchestrator.translate_book_project") as mock_trans, \
         patch("audiobook_factory.orchestrator.verify_translation_coverage_gates"), \
         patch("audiobook_factory.orchestrator.generate_project_scripts") as mock_ab_scripts, \
         patch("audiobook_factory.orchestrator.verify_screenplay_project_gates"), \
         patch("audiobook_factory.podcast.generate_project_podcasts") as mock_pod_scripts, \
         patch.object(orchestrator, "produce_chapter") as mock_produce_ab, \
         patch("audiobook_factory.podcast.orchestrator.PodcastOrchestrator.produce_podcast_episode", return_value={"master_file": str(projects_dir / "test_novel" / "podcasts" / "ch01.wav")}), \
         patch("audiobook_factory.packaging.package_project", return_value={"artifacts": {"audiobook_m4b": "book.m4b", "podcast_episodes": ["ep1.m4a"]}}), \
         patch("audiobook_factory.orchestrator.verify_packaging_gates"):

        project_dir = projects_dir / "test_novel"
        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "chapter_001_script.json").write_text("[]", encoding="utf-8")
        mock_ab_scripts.return_value = scripts_dir

        podcasts_dir = project_dir / "podcasts"
        podcasts_dir.mkdir(parents=True, exist_ok=True)
        (podcasts_dir / "chapter_001_podcast_plan.json").write_text("{}", encoding="utf-8")

        res = orchestrator.run_autonomous_pipeline(
            input_file=mock_novel_file,
            hindi=True,
            format_mode="both",
        )

        assert isinstance(res, dict)
        assert "audiobook_m4b" in res
        assert "podcast_episodes" in res

        mock_trans.assert_called_once()
        mock_ab_scripts.assert_called_once()
        mock_pod_scripts.assert_called_once()
        mock_produce_ab.assert_called_once()


def test_chunk_namespacing_isolation():
    """Verify audiobook ('c') and podcast ('p') filenames have distinct prefixes."""
    from audiobook_factory.tts.audio_slicer import compute_canonical_segment_filename

    fn_audiobook = compute_canonical_segment_filename(1, 1, "Hello world", prefix="c")
    fn_podcast = compute_canonical_segment_filename(1, 1, "Hello world", prefix="p")

    assert fn_audiobook.startswith("c001_s0001_")
    assert fn_podcast.startswith("p001_s0001_")
    assert fn_audiobook != fn_podcast
