import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from audiobook_factory.podcast.orchestrator import PodcastOrchestrator
from audiobook_factory.podcast.contracts import PodcastEpisodePlan, PodcastSegment
from audiobook_factory.podcast.persona_engine import HostPersonaEngine


@pytest.fixture
def mock_podcast_project(tmp_path):
    proj_dir = tmp_path / "mock_podcast_book"
    proj_dir.mkdir(parents=True, exist_ok=True)
    trans_dir = proj_dir / "translation"
    trans_dir.mkdir(parents=True, exist_ok=True)

    sample_md = (
        "# Chapter 1: The Gathering Storm\n\n"
        "The night was cold and the wind howled through the ruined towers of Kaer Morhen.\n\n"
        "Geralt cleaned his silver sword by the dying embers of the hearth.\n\n"
        "\"We do not have much time,\" Vesemir warned, looking out into the mist.\n"
    )
    (trans_dir / "chapter_001.md").write_text(sample_md, encoding="utf-8")
    return proj_dir


def test_orchestrator_generate_episode_script(mock_podcast_project):
    """Test generating podcast plan and script artifacts using mocked LLM response."""
    orchestrator = PodcastOrchestrator(model="mock-model")

    mock_llm_turns = [
        {"speaker": "समीर", "text": "क्या आप जानते हैं कि उस रात काएर मोर्हेन में क्या हुआ था?", "emotion": "tense", "section_type": "cold_open_hook"},
        {"speaker": "प्रिया", "text": "नमस्ते दोस्तों, आज हम विच की इस ख़तरनाक रात की दास्तान में दाखिल हो रहे हैं।", "emotion": "intrigued", "section_type": "show_intro"},
        {"speaker": "समीर", "text": "गेराल्ट अपनी तलवार साफ कर रहा था और वेसेमिर ने आने वाले ख़तरे का आगाज़ कर दिया।", "emotion": "thoughtful", "section_type": "scene_deepdive"},
        {"speaker": "प्रिया", "text": "सोचिए, इतनी ठंड में जब बुज़ुर्ग वेसेमिर ऐसा कहें, तो ख़तरा कितना बड़ा होगा!", "emotion": "shocked", "section_type": "scene_deepdive"},
        {"speaker": "समीर", "text": "हाहा, वेसेमिर कभी बिना वजह नहीं घबराते!", "emotion": "humorous", "section_type": "cognitive_reset_banter"},
        {"speaker": "प्रिया", "text": "तो ये थी आज की दास्तान, अगले एपिसोड में मिलते हैं।", "emotion": "neutral", "section_type": "show_outro"},
    ]

    with patch("audiobook_factory.podcast.episode_generator.call_gemini", return_value=mock_llm_turns):
        plan_path, script_path = orchestrator.generate_episode_script(
            project_dir=mock_podcast_project,
            chapter_num=1,
            use_hindi=True,
            overwrite=True,
        )

        assert plan_path.exists()
        assert script_path.exists()

        plan = PodcastEpisodePlan.load_from_file(plan_path)
        assert plan.source_chapter_id == "chapter_001" or plan.episode_id == "podcast_ep_001"
        assert len(plan.segments) == 6
        assert plan.target_lufs == -16.0

        with open(script_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)

        assert len(script_data) == 6
        assert script_data[0]["speaker"] == "समीर"
        assert script_data[0]["voice"] == "Puck"
        # Check stereo pan formatting
        assert script_data[0].get("formant_params", {}).get("pan") == -0.25
        assert script_data[1].get("formant_params", {}).get("pan") == 0.25


def test_orchestrator_synthesize_podcast_script(mock_podcast_project):
    """Test synthesis delegation to TTSDispatcher."""
    orchestrator = PodcastOrchestrator()
    script_file = mock_podcast_project / "scripts" / "chapter_001_podcast_script.json"
    script_file.parent.mkdir(parents=True, exist_ok=True)
    script_file.write_text("[]", encoding="utf-8")

    audio_chunks_dir = mock_podcast_project / "audio_chunks"
    audio_chunks_dir.mkdir(parents=True, exist_ok=True)
    fake_chunk = audio_chunks_dir / "p001_s0001_take1.wav"
    fake_chunk.write_text("dummy", encoding="utf-8")

    with patch("audiobook_factory.podcast.orchestrator.TTSDispatcher") as MockDispatcher:
        mock_instance = MagicMock()
        MockDispatcher.return_value = mock_instance

        segments = orchestrator.synthesize_podcast_script(
            project_dir=mock_podcast_project,
            script_file=script_file,
            chapter_num=1,
            workers=2,
        )

        MockDispatcher.assert_called_once()
        mock_instance.synthesize_chapter_script.assert_called_once_with(script_file, 1)
        assert len(segments) >= 1


def test_orchestrator_master_podcast_episode(mock_podcast_project):
    """Test mastering podcast episode with spatial staging and -16.0 LUFS target."""
    orchestrator = PodcastOrchestrator()
    audio_segments = [mock_podcast_project / "audio_chunks" / "c001_s0001_take1.wav"]
    script_data = [{"index": 1, "speaker": "Sameer", "dialogue": "Hello world"}]

    with patch("audiobook_factory.podcast.orchestrator.concatenate_and_master_chapter") as mock_master, \
         patch("audiobook_factory.podcast.orchestrator.subprocess.run") as mock_subproc, \
         patch("audiobook_factory.podcast.orchestrator.get_ffmpeg", return_value="ffmpeg"):

        out_m4a = orchestrator.master_podcast_episode(
            project_dir=mock_podcast_project,
            chapter_num=1,
            chap_stem="chapter_001",
            script_data=script_data,
            audio_segments=audio_segments,
            target_lufs=-16.0,
            true_peak_db=-1.0,
        )

        mock_master.assert_called_once()
        call_kwargs = mock_master.call_args[1]
        assert call_kwargs["target_lufs"] == -16.0
        assert call_kwargs["true_peak_db"] == -1.0
        assert call_kwargs["spatial_staging"] is True

        mock_subproc.assert_called_once()
        assert out_m4a.name == "chapter_001_podcast.m4a"


def test_orchestrator_produce_podcast_episode(mock_podcast_project):
    """Test full single-command produce_podcast_episode coordination."""
    orchestrator = PodcastOrchestrator()

    fake_plan = PodcastEpisodePlan(
        episode_id="podcast_ep_001",
        episode_title="Test Ep",
        source_chapter_id="ch01",
        language="hi",
        hosts=HostPersonaEngine.get_default_hosts(is_hindi=True),
        hook_statement="Hook",
        segments=[],
        total_duration_estimate_sec=120.0,
        target_lufs=-16.0,
    )

    plan_path = mock_podcast_project / "podcasts" / "chapter_001_podcast_plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    fake_plan.save_to_file(plan_path)

    script_path = mock_podcast_project / "scripts" / "chapter_001_podcast_script.json"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text('[{"speaker": "समीर", "dialogue": "नमस्ते"}]', encoding="utf-8")

    with patch.object(orchestrator, "generate_episode_script", return_value=(plan_path, script_path)), \
         patch.object(orchestrator, "synthesize_podcast_script", return_value=[]), \
         patch.object(orchestrator, "master_podcast_episode", return_value=mock_podcast_project / "podcasts" / "chapter_001_podcast.m4a"), \
         patch("audiobook_factory.podcast.orchestrator.get_audio_duration", return_value=120.0):

        res = orchestrator.produce_podcast_episode(
            project_dir=mock_podcast_project,
            chapter_num=1,
            use_hindi=True,
        )

        assert res["chapter_num"] == 1
        assert res["episode_title"] == "Test Ep"
        assert res["target_lufs"] == -16.0
        assert res["duration_min"] == 2.0
        assert res["total_turns"] == 1
