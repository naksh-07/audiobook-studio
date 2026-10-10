import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from audiobook_factory.packaging.chapter_metadata import ChapterMetadataGenerator
from audiobook_factory.packaging.multi_format import package_project, package_podcast_episodes
from audiobook_factory.podcast.contracts import PodcastEpisodePlan, PodcastSegment
from audiobook_factory.podcast.persona_engine import HostPersonaEngine


def test_generate_audiobook_metadata():
    """Verify FFMETADATA1 generation for audiobook chapters."""
    chapter_durations = [
        {"chapter_num": 1, "title": "The Arrival", "duration_ms": 120000},
        {"chapter_num": 2, "title": "The Conclave", "duration_ms": 180000},
    ]
    meta_text = ChapterMetadataGenerator.generate_audiobook_metadata(
        book_title="Sword of Destiny",
        author="Andrzej Sapkowski",
        chapter_durations=chapter_durations,
    )

    assert ";FFMETADATA1" in meta_text
    assert "title=Sword of Destiny" in meta_text
    assert "artist=Andrzej Sapkowski" in meta_text
    assert "genre=Audiobook" in meta_text
    assert "[CHAPTER]" in meta_text
    assert "START=0" in meta_text
    assert "END=120000" in meta_text
    assert "title=The Arrival" in meta_text
    assert "START=120000" in meta_text
    assert "END=300000" in meta_text
    assert "title=The Conclave" in meta_text


def test_generate_podcast_metadata():
    """Verify FFMETADATA1 generation for podcast episodes with show notes."""
    hosts = HostPersonaEngine.get_default_hosts(is_hindi=True)
    plan = PodcastEpisodePlan(
        episode_id="podcast_ep_001",
        episode_title="Chapter 1 Breakdown",
        source_chapter_id="ch01",
        language="hi",
        hosts=hosts,
        hook_statement="A deadly secret in the temple",
        segments=[],
        total_duration_estimate_sec=60.0,
        target_lufs=-16.0,
    )
    seg_durs = [
        {"section_type": "cold_open_hook", "duration_ms": 15000},
        {"section_type": "scene_deepdive", "duration_ms": 45000},
    ]

    meta_text = ChapterMetadataGenerator.generate_podcast_metadata(
        episode_plan=plan,
        show_title="The Witcher Chronicles",
        segment_durations=seg_durs,
    )

    assert ";FFMETADATA1" in meta_text
    assert "title=Chapter 1 Breakdown" in meta_text
    assert "artist=समीर & प्रिया" in meta_text
    assert "album=The Witcher Chronicles" in meta_text
    assert "genre=Podcast" in meta_text
    assert "description=Episode Summary: A deadly secret in the temple" in meta_text
    assert "title=Cold Open Hook" in meta_text
    assert "title=Scene Deepdive" in meta_text


def test_package_project_dispatch(tmp_path):
    """Verify package_project orchestrates audiobook and podcast packaging cleanly."""
    proj_dir = tmp_path / "mock_project"
    proj_dir.mkdir(parents=True, exist_ok=True)

    with patch("audiobook_factory.packaging.multi_format.package_m4b_audiobook", return_value=proj_dir / "book.m4b") as mock_m4b, \
         patch("audiobook_factory.packaging.multi_format.package_podcast_episodes", return_value=[proj_dir / "ep1.m4a"]) as mock_pod:

        # 1. Audiobook mode
        res_ab = package_project(proj_dir, format_mode="audiobook")
        mock_m4b.assert_called_once()
        mock_pod.assert_not_called()
        assert "audiobook_m4b" in res_ab["artifacts"]

        mock_m4b.reset_mock()
        mock_pod.reset_mock()

        # 2. Podcast mode
        res_pod = package_project(proj_dir, format_mode="podcast")
        mock_m4b.assert_not_called()
        mock_pod.assert_called_once()
        assert "podcast_episodes" in res_pod["artifacts"]

        mock_m4b.reset_mock()
        mock_pod.reset_mock()

        # 3. Both mode
        res_both = package_project(proj_dir, format_mode="both")
        mock_m4b.assert_called_once()
        mock_pod.assert_called_once()
        assert "audiobook_m4b" in res_both["artifacts"]
        assert "podcast_episodes" in res_both["artifacts"]
