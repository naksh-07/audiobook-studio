import pytest
from unittest.mock import MagicMock, patch
from audiobook_factory.dramaturgy.contracts import (
    DramaticBeat,
    SceneDramaticPlan,
    DramaticPlan,
    CharacterDramaticObjective,
)
from audiobook_factory.script.screenplay_cleaner import clean_screenplay_pass2
from audiobook_factory.script.agents.stanislavski_director import StanislavskiSubtextDirector
from audiobook_factory.director import SoundDesignDirectorMixin, DramaturgyMixin, AgentDirector


def test_dramaturgy_contracts_spu_fields():
    """Verify contracts support paragraph indices and SPU IDs."""
    beat = DramaticBeat(
        beat_id="b1",
        scene_id="s1",
        index=1,
        dramatic_function="reveal",
        summary="Test goal",
        subtext="Test subtext",
        start_paragraph_idx=5,
        end_paragraph_idx=10,
    )
    assert beat.start_paragraph_idx == 5
    assert beat.end_paragraph_idx == 10

    scene = SceneDramaticPlan(
        scene_id="s1",
        scene_title="Test Scene",
        start_paragraph_idx=0,
        end_paragraph_idx=20,
        spu_ids=["spu_001", "spu_002"],
        beats=[beat],
    )
    assert scene.start_paragraph_idx == 0
    assert scene.end_paragraph_idx == 20
    assert len(scene.spu_ids) == 2
    assert scene.beats[0].start_paragraph_idx == 5


def test_scene_scoped_beat_mapping_zero_contamination():
    """
    Test that ScreenplayCleaner maps beats strictly within their parent scene bounds,
    preventing Scene 2 segments from being contaminated with Scene 1 beats.
    """
    raw_screenplay = [
        # Scene 1 (index 1..3)
        {"index": 1, "speaker": "Alice", "text": "Hello there.", "type": "dialogue", "scene_idx": 1, "scene_id": "scene_001"},
        {"index": 2, "speaker": "Bob", "text": "Good morning.", "type": "dialogue", "scene_idx": 1, "scene_id": "scene_001"},
        {"index": 3, "speaker": "Alice", "text": "Any news?", "type": "dialogue", "scene_idx": 1, "scene_id": "scene_001"},
        # Scene 2 (index 4..13)
        {"index": 4, "speaker": "Narrator", "text": "They walked into the deep forest.", "type": "narration", "scene_idx": 2, "scene_id": "scene_002"},
        {"index": 5, "speaker": "Bob", "text": "It is getting dark.", "type": "dialogue", "scene_idx": 2, "scene_id": "scene_002"},
        {"index": 6, "speaker": "Alice", "text": "Stay close.", "type": "dialogue", "scene_idx": 2, "scene_id": "scene_002"},
        {"index": 7, "speaker": "Bob", "text": "Did you hear that sound?", "type": "dialogue", "scene_idx": 2, "scene_id": "scene_002"},
        {"index": 8, "speaker": "Alice", "text": "What sound?", "type": "dialogue", "scene_idx": 2, "scene_id": "scene_002"},
        {"index": 9, "speaker": "Narrator", "text": "A branch snapped nearby.", "type": "narration", "scene_idx": 2, "scene_id": "scene_002"},
        {"index": 10, "speaker": "Bob", "text": "Over there!", "type": "dialogue", "scene_idx": 2, "scene_id": "scene_002"},
        {"index": 11, "speaker": "Alice", "text": "Draw your sword.", "type": "dialogue", "scene_idx": 2, "scene_id": "scene_002"},
        {"index": 12, "speaker": "Bob", "text": "I am ready.", "type": "dialogue", "scene_idx": 2, "scene_id": "scene_002"},
        {"index": 13, "speaker": "Narrator", "text": "The shadows deepened.", "type": "narration", "scene_idx": 2, "scene_id": "scene_002"},
    ]

    beat_s1_b1 = DramaticBeat(
        beat_id="s1_b1",
        scene_id="scene_001",
        index=1,
        dramatic_function="setup",
        summary="Morning greeting",
        subtext="Casual warmth",
    )
    beat_s1_b2 = DramaticBeat(
        beat_id="s1_b2",
        scene_id="scene_001",
        index=2,
        dramatic_function="question",
        summary="Inquire about news",
        subtext="Underlying worry",
    )

    beat_s2_b1 = DramaticBeat(
        beat_id="s2_b1",
        scene_id="scene_002",
        index=1,
        dramatic_function="escalation",
        summary="Forest entry and vigilance",
        subtext="Growing dread",
    )
    beat_s2_b2 = DramaticBeat(
        beat_id="s2_b2",
        scene_id="scene_002",
        index=2,
        dramatic_function="threat",
        summary="Prepare for imminent ambush",
        subtext="Adrenaline surge",
    )

    scene1 = SceneDramaticPlan(
        scene_id="scene_001",
        scene_title="Morning Village",
        start_paragraph_idx=0,
        end_paragraph_idx=3,
        beats=[beat_s1_b1, beat_s1_b2],
    )
    scene2 = SceneDramaticPlan(
        scene_id="scene_002",
        scene_title="Dark Forest Ambush",
        start_paragraph_idx=3,
        end_paragraph_idx=13,
        beats=[beat_s2_b1, beat_s2_b2],
    )

    dramatic_plan = DramaticPlan(
        chapter_id="ch01",
        scenes=[scene1, scene2],
    )

    cleaned = clean_screenplay_pass2(raw_screenplay, dramatic_plan=dramatic_plan)
    assert len(cleaned) == 13

    # Check Scene 1 items (indices 0..2)
    assert cleaned[0]["scene_id"] == "scene_001"
    assert cleaned[0]["beat_id"] == "s1_b1"
    assert cleaned[2]["scene_id"] == "scene_001"
    assert cleaned[2]["beat_id"] == "s1_b2"

    # Check Scene 2 items (indices 3..12) - MUST NEVER HAVE "s1_b*" beats!
    for seg in cleaned[3:]:
        assert seg["scene_id"] == "scene_002"
        assert seg["beat_id"].startswith("s2_"), f"Cross-scene contamination: {seg['beat_id']} found in Scene 2!"

    # First half of Scene 2 should be s2_b1, second half s2_b2
    assert cleaned[3]["beat_id"] == "s2_b1"
    assert cleaned[12]["beat_id"] == "s2_b2"


def test_stanislavski_director_preserves_dramatic_plan_subtext():
    """
    Test that StanislavskiSubtextDirector preserves pre-existing DramaticPlan
    objectives on segments without overwriting them or causing representation drift.
    """
    segments = [
        {
            "index": 1,
            "speaker": "Geralt",
            "text": "Evil is evil, Stregobor. Lesser, greater, middling, makes no difference.",
            "type": "dialogue",
            "scene_idx": 1,
            "beat_id": "beat_01",
            "character_objective": "Refuse moral compromise",
            "subtext": "Absolute ethical firmness",
            "actioning": "deflect",
        },
        {
            "index": 2,
            "speaker": "Stregobor",
            "text": "You speak in absolutes.",
            "type": "dialogue",
            "scene_idx": 1,
        },
    ]

    director = StanislavskiSubtextDirector(model="mock-gemini")

    mock_llm_fn = MagicMock(return_value=[
        {
            "index": 1,
            "actioning": "overwritten_intent",
            "subtext": "overwritten_subtext",
            "intensity_level": "high",
        },
        {
            "index": 2,
            "actioning": "gaslight",
            "subtext": "Persuade Witcher to kill Renfri",
            "underlying_emotion": "frustration",
            "intensity_level": "medium",
            "acting": {"delivery_style": "dry_condescending", "pacing": 0.95},
        }
    ])

    directed = director.direct_subtext(segments, call_llm_fn=mock_llm_fn)

    # Segment 1 should PRESERVE its existing actioning and subtext
    assert directed[0]["actioning"] == "deflect"
    assert directed[0]["subtext"] == "Absolute ethical firmness"

    # Segment 2 should have resolved subtext from LLM
    assert directed[1]["actioning"] == "gaslight"
    assert directed[1]["subtext"] == "Persuade Witcher to kill Renfri"
    assert directed[1]["acting"]["delivery_style"] == "dry_condescending"


def test_sound_design_director_mixin_compatibility():
    """Verify that SoundDesignDirectorMixin and DramaturgyMixin alias properly."""
    assert issubclass(AgentDirector, SoundDesignDirectorMixin)
    assert DramaturgyMixin is SoundDesignDirectorMixin

    with patch("audiobook_factory.director.director.get_sound_bank"), \
         patch("audiobook_factory.director.director.get_persistent_key_pool"):
        director = AgentDirector(model="mock-directing", sound_bank=MagicMock())
        assert hasattr(director, "_pass1_dramaturgy_and_silence_carving")
        assert hasattr(director, "_enforce_silence_carving")
        assert hasattr(director, "_build_deterministic_dramaturgy_plan")
