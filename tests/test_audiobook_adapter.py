import pytest
from unittest.mock import MagicMock, patch
from audiobook_factory.adapters import (
    BaseScriptAdapter,
    AudiobookAdapter,
    get_adapter,
    list_registered_adapters,
)
from audiobook_factory.dramaturgy.contracts import (
    DramaticBeat,
    SceneDramaticPlan,
    DramaticPlan,
    DramaticValidationResult,
)


def test_audiobook_adapter_registry():
    """Verify AudiobookAdapter is registered and instantiated via get_adapter."""
    registered = list_registered_adapters()
    assert "audiobook" in registered
    assert "podcast" in registered

    adapter = get_adapter("audiobook")
    assert isinstance(adapter, AudiobookAdapter)
    assert isinstance(adapter, BaseScriptAdapter)
    assert adapter.adapter_id == "audiobook"


def test_audiobook_adapter_adapt_flow():
    """Verify AudiobookAdapter processes chapter text through chunk parsing and clean pass 2."""
    beat1 = DramaticBeat(
        beat_id="b1",
        scene_id="s1",
        index=1,
        dramatic_function="setup",
        summary="Opening confrontation",
    )
    scene1 = SceneDramaticPlan(
        scene_id="s1",
        scene_title="Tavern Scene",
        start_paragraph_idx=0,
        end_paragraph_idx=5,
        beats=[beat1],
    )
    dramatic_plan = DramaticPlan(
        chapter_id="ch01",
        scenes=[scene1],
    )

    adapter = AudiobookAdapter(model="mock-audiobook-model")

    mock_chunk_fn = MagicMock(return_value=[
        {"index": 1, "speaker": "Geralt", "text": "Who are you?", "type": "dialogue"},
        {"index": 2, "speaker": "Narrator", "text": "He asked calmly.", "type": "narration"},
        {"index": 3, "speaker": "Geralt", "text": "State your business.", "type": "dialogue"},
    ])

    with patch("audiobook_factory.adapters.audiobook.get_persistent_key_pool") as mock_pool:
        mock_pool.return_value.get_key.return_value = "dummy-key"

        segments = adapter.adapt(
            chapter_text="Who are you? He asked calmly. State your business.",
            dramatic_plan=dramatic_plan,
            call_chunk_fn=mock_chunk_fn,
        )

        assert len(segments) >= 2
        # Verify Audible Flow split-quote stitching occurred
        dialogue_turns = [s for s in segments if s.get("type") == "dialogue"]
        assert len(dialogue_turns) == 1
        assert "Who are you?" in dialogue_turns[0]["text"]
        assert "State your business." in dialogue_turns[0]["text"]
        assert dialogue_turns[0]["speaker"] == "Geralt"
        assert dialogue_turns[0]["beat_id"] == "b1"


def test_audiobook_adapter_validate_hook():
    """Verify adapter.validate runs Gate 2.5 DramaticValidator."""
    adapter = AudiobookAdapter(model="mock-audiobook-model")
    beat = DramaticBeat(beat_id="b1", scene_id="s1", index=1, dramatic_function="setup", summary="Scene 1 beat")
    scene = SceneDramaticPlan(scene_id="s1", scene_title="Scene 1", beats=[beat])
    dramatic_plan = DramaticPlan(chapter_id="ch01", scenes=[scene])

    segments = [
        {"index": 1, "speaker": "Narrator", "text": "The wind howled.", "type": "narration", "scene_id": "s1", "beat_id": "b1"},
        {"index": 2, "speaker": "Geralt", "text": "A storm is coming.", "type": "dialogue", "scene_id": "s1", "beat_id": "b1", "actioning": "observe"},
    ]

    val_res = adapter.validate(segments=segments, dramatic_plan=dramatic_plan, source_text="The wind howled. 'A storm is coming.'")
    assert isinstance(val_res, DramaticValidationResult)
    assert val_res.passed is True
