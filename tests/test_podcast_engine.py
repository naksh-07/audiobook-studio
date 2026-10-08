import pytest
from unittest.mock import MagicMock
from audiobook_factory.podcast.contracts import HostProfile, PodcastSegment, PodcastEpisodePlan
from audiobook_factory.podcast.persona_engine import HostPersonaEngine
from audiobook_factory.podcast.spoken_transformer import SpokenBreathabilityTransformer
from audiobook_factory.podcast.episode_generator import PodcastEpisodeGenerator
from audiobook_factory.adapters import get_adapter, PodcastAdapter
from audiobook_factory.dramaturgy.contracts import (
    DramaticBeat,
    SceneDramaticPlan,
    DramaticPlan,
)


def test_podcast_contracts_and_serialization(tmp_path):
    """Verify PodcastEpisodePlan schema and disk serialization."""
    hosts = HostPersonaEngine.get_default_hosts(is_hindi=True)
    seg1 = PodcastSegment(
        index=1,
        speaker="समीर",
        text="अरे प्रिया, क्या तुम्हें पता है आज हम किस कहानी में जाने वाले हैं?",
        emotion="excited",
        section_type="show_intro",
        pause_after_ms=400,
    )
    seg2 = PodcastSegment(
        index=2,
        speaker="प्रिया",
        text="बिल्कुल समीर, आज हम उस अंधेरी रात के रहस्य को सुलझाएंगे!",
        emotion="intrigued",
        section_type="show_intro",
        pause_after_ms=450,
    )
    plan = PodcastEpisodePlan(
        episode_id="podcast_ep_001",
        episode_title="The Midnight Secret",
        source_chapter_id="ch01",
        language="hi",
        hosts=hosts,
        hook_statement="A deadly secret revealed.",
        segments=[seg1, seg2],
        total_duration_estimate_sec=25.0,
        target_lufs=-16.0,
    )

    save_path = tmp_path / "test_podcast_plan.json"
    plan.save_to_file(save_path)
    assert save_path.exists()

    loaded = PodcastEpisodePlan.load_from_file(save_path)
    assert loaded.episode_id == "podcast_ep_001"
    assert len(loaded.segments) == 2
    assert loaded.hosts["host_a"].name == "समीर"
    assert loaded.hosts["host_b"].name == "प्रिया"


def test_spoken_breathability_transformer():
    """Verify that sentences > 22 words are split into breathable units."""
    long_sentence_en = (
        "Although the detective had spent years studying the mysterious disappearance of the ancient manuscript from the cathedral library, "
        "he never anticipated that the chief archivist himself would be the one orchestrating the entire conspiracy behind closed doors."
    )
    units = SpokenBreathabilityTransformer.split_into_breathable_units(long_sentence_en, is_hindi=False)
    assert len(units) >= 2
    for u in units:
        word_count = len(u.split())
        assert word_count <= SpokenBreathabilityTransformer.MAX_WORDS_PER_BREATH, f"Unit '{u}' exceeded word cap ({word_count})"

    long_sentence_hi = (
        "हालाँकि जासूस ने कई सालों तक उस रहस्यमयी हवेली की छानबीन की थी, "
        "लेकिन उसने कभी सपने में भी नहीं सोचा था कि उस रात हवेली के पुराने तहखाने में छिपा राज़ "
        "उसकी पूरी ज़िंदगी का सबसे बड़ा ख़तरा बन जाएगा।"
    )
    units_hi = SpokenBreathabilityTransformer.split_into_breathable_units(long_sentence_hi, is_hindi=True)
    assert len(units_hi) >= 2
    for u in units_hi:
        word_count = len(u.split())
        assert word_count <= SpokenBreathabilityTransformer.MAX_WORDS_PER_BREATH, f"Hindi unit '{u}' exceeded word cap ({word_count})"


def test_podcast_episode_generator_with_dramatic_ast():
    """Verify 5-part episode generation from core Dramaturgy AST."""
    beat1 = DramaticBeat(
        beat_id="b1",
        scene_id="s1",
        index=1,
        dramatic_function="setup",
        summary="Geralt arrives at the tavern",
        tension_before=0.3,
        tension_after=0.4,
    )
    beat2 = DramaticBeat(
        beat_id="b2",
        scene_id="s1",
        index=2,
        dramatic_function="reveal",
        summary="A hidden curse is unveiled",
        tension_before=0.5,
        tension_after=0.9,
    )
    scene = SceneDramaticPlan(
        scene_id="s1",
        scene_title="Tavern Revelation",
        dramatic_purpose="Introduce central mystery",
        primary_conflict="Witcher vs Village suspicion",
        stakes="Survival and innocent blood",
        beats=[beat1, beat2],
    )
    dramatic_plan = DramaticPlan(
        chapter_id="ch01",
        chapter_num=1,
        scenes=[scene],
    )

    generator = PodcastEpisodeGenerator(model="mock-gemini")

    mock_llm_response = [
        {"speaker": "समीर", "text": "रुकिए! क्या आपको पता है कि उस रात क्या हुआ था?", "emotion": "tense", "section_type": "cold_open_hook"},
        {"speaker": "प्रिया", "text": "स्वागत है दोस्तों, आज हम विच की उस रहस्यमयी दास्तान में उतर रहे हैं।", "emotion": "intrigued", "section_type": "show_intro"},
        {"speaker": "समीर", "text": "जब गेराल्ट सराय में कदम रखता है, तो हर कोई उसे शक की निगाहों से देखता है।", "emotion": "thoughtful", "section_type": "scene_deepdive"},
        {"speaker": "प्रिया", "text": "और फिर सबसे बड़ा मोड़ आता है जब उस श्राप का सच सामने आता है!", "emotion": "shocked", "section_type": "scene_deepdive"},
        {"speaker": "समीर", "text": "भाई, ये तो सच में रोंगटे खड़े कर देने वाला था!", "emotion": "humorous", "section_type": "cognitive_reset_banter"},
        {"speaker": "प्रिया", "text": "तो ये थी आज की दास्तान, अगले एपिसोड में क्या होगा, जानने के लिए बने रहिए।", "emotion": "neutral", "section_type": "show_outro"},
    ]

    mock_llm_fn = MagicMock(return_value=mock_llm_response)

    episode_plan = generator.generate_episode(
        chapter_text="Mock chapter source text",
        dramatic_plan=dramatic_plan,
        chapter_num=1,
        is_hindi=True,
        call_llm_fn=mock_llm_fn,
    )

    assert episode_plan.episode_id == "podcast_ep_001"
    assert len(episode_plan.segments) >= 6
    sections_present = {s.section_type for s in episode_plan.segments}
    assert "cold_open_hook" in sections_present
    assert "show_intro" in sections_present
    assert "scene_deepdive" in sections_present
    assert "cognitive_reset_banter" in sections_present
    assert "show_outro" in sections_present


def test_podcast_adapter_registry_and_adapt():
    """Verify PodcastAdapter integrates via get_adapter and returns standard segments."""
    adapter = get_adapter("podcast", model="mock-model")
    assert isinstance(adapter, PodcastAdapter)
    assert adapter.adapter_id == "podcast"

    beat = DramaticBeat(
        beat_id="b1",
        scene_id="s1",
        index=1,
        dramatic_function="climax",
        summary="Climactic showdown",
        tension_before=0.8,
        tension_after=0.95,
    )
    scene = SceneDramaticPlan(scene_id="s1", scene_title="Showdown", beats=[beat])
    dramatic_plan = DramaticPlan(chapter_id="ch01", scenes=[scene])

    mock_llm_response = [
        {"speaker": "Alex", "text": "Wait, did he actually draw his sword right there?", "emotion": "shocked", "section_type": "cold_open_hook"},
        {"speaker": "Maya", "text": "Yes, Alex, and that changed everything in the story!", "emotion": "excited", "section_type": "show_intro"},
    ]
    mock_llm_fn = MagicMock(return_value=mock_llm_response)

    segments = adapter.adapt(
        chapter_text="Showdown text",
        dramatic_plan=dramatic_plan,
        is_hindi=False,
        call_llm_fn=mock_llm_fn,
    )

    assert len(segments) == 2
    assert segments[0]["speaker"] == "Alex"
    assert segments[0]["acoustic_env"] == "podcast_studio"
    assert segments[1]["speaker"] == "Maya"
    assert segments[1]["spatial"]["azimuth_pan"] == 0.25
