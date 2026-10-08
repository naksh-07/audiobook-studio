import pytest
from unittest.mock import MagicMock, patch
from audiobook_factory.dramaturgy.contracts import (
    DramaticBeat,
    SceneDramaticPlan,
    DramaticPlan,
    PerformanceBible,
    CharacterPerformanceProfile,
)
from audiobook_factory.adapters.audiobook import AudiobookAdapter


def test_audiobook_adapter_binds_performance_bible():
    """Verify AudiobookAdapter binds character delivery styles, restraint, and pace from PerformanceBible."""
    geralt_profile = CharacterPerformanceProfile(
        character_name="Geralt",
        baseline_pace=0.92,
        baseline_energy=0.85,
        articulation="crisp_measured",
        restraint_level=0.9,
        emotional_behaviors={
            "anger": "cold_quiet_menace",
            "threat": "whispered_lethal_calm",
            "neutral": "gravelly_cynical",
        },
        speech_quirks=["cynical_grunt", "flat_affect"],
    )
    pb = PerformanceBible(
        characters={"Geralt": geralt_profile},
        narrator_style={"baseline_pace": 1.0, "tone": "objective_cinematic_observer"},
    )

    beat = DramaticBeat(
        beat_id="b1",
        scene_id="s1",
        index=1,
        dramatic_function="threat",
        summary="Geralt warns the thugs",
    )
    scene = SceneDramaticPlan(scene_id="s1", scene_title="Tavern Warning", beats=[beat])
    dramatic_plan = DramaticPlan(chapter_id="ch01", scenes=[scene])

    adapter = AudiobookAdapter(model="mock-model", performance_bible=pb)

    mock_chunk_fn = MagicMock(return_value=[
        {"index": 1, "speaker": "Geralt", "text": "Walk away while you still can.", "type": "dialogue", "emotion": "anger"},
        {"index": 2, "speaker": "Narrator", "text": "The tavern went completely quiet.", "type": "narration"},
    ])

    with patch("audiobook_factory.adapters.audiobook.get_persistent_key_pool") as mock_pool:
        mock_pool.return_value.get_key.return_value = "dummy-key"

        segments = adapter.adapt(
            chapter_text="Walk away while you still can. The tavern went completely quiet.",
            dramatic_plan=dramatic_plan,
            call_chunk_fn=mock_chunk_fn,
        )

        assert len(segments) == 2

        # Check Geralt character segment
        g_seg = segments[0]
        assert g_seg["speaker"] == "Geralt"
        assert g_seg["acting"]["delivery_style"] == "cold_quiet_menace"
        assert g_seg["acting"]["restraint"] == 0.9
        assert g_seg["acting"]["pacing"] == 0.92
        assert g_seg["acting"]["articulation"] == "crisp_measured"
        assert "cynical_grunt" in g_seg["acting"]["speech_quirks"]

        # Check Narrator segment
        n_seg = segments[1]
        assert n_seg["speaker"] == "Narrator"
        assert n_seg["acting"]["delivery_style"] == "calm_authoritative"
        assert n_seg["acting"]["tone"] == "objective_cinematic_observer"
        assert n_seg["intensity_level"] == "medium"
        assert n_seg["subtext"] == ""
        assert n_seg["underlying_emotion"] == "neutral"
