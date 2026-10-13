import pytest
from audiobook_factory.dramaturgy.contracts import (
    DramaticBeat,
    SceneDramaticPlan,
    DramaticPlan,
    DramaticValidationResult,
)
from audiobook_factory.dramaturgy.dramatic_validator import DramaticValidator


def test_validator_passes_consistent_screenplay():
    """Verify DramaticValidator returns PASS on a well-formed screenplay."""
    beat = DramaticBeat(
        beat_id="b1",
        scene_id="s1",
        index=1,
        dramatic_function="setup",
        summary="Opening dialogue",
    )
    scene = SceneDramaticPlan(scene_id="s1", scene_title="Scene 1", beats=[beat])
    dramatic_plan = DramaticPlan(chapter_id="ch01", scenes=[scene])

    segments = [
        {"index": 1, "speaker": "Narrator", "text": "Night fell over the city.", "type": "narration", "scene_id": "s1", "beat_id": "b1"},
        {"index": 2, "speaker": "Geralt", "text": "The wind is howling.", "type": "dialogue", "scene_id": "s1", "beat_id": "b1", "actioning": "observe", "emotion": "calm"},
    ]

    result = DramaticValidator.validate_screenplay_and_plan(
        segments=segments,
        dramatic_plan=dramatic_plan,
        source_text="Night fell over the city. 'The wind is howling.'",
    )
    assert isinstance(result, DramaticValidationResult)
    assert result.passed is True
    assert result.status in ("PASS", "WARNING")


def test_validator_catches_non_monotonic_indices():
    """Verify DramaticValidator flags non-monotonic segment indices."""
    segments = [
        {"index": 1, "speaker": "Narrator", "text": "First line.", "type": "narration"},
        {"index": 3, "speaker": "Narrator", "text": "Skipped index 2.", "type": "narration"},
    ]
    result = DramaticValidator.validate_screenplay_and_plan(segments=segments)
    assert result.passed is False
    assert result.status == "FAIL"
    issue_codes = [i.code for i in result.issues]
    assert "NON_MONOTONIC_INDEX" in issue_codes


def test_validator_catches_emotional_teleportation():
    """Verify DramaticValidator detects volatile emotional jumps."""
    segments = [
        {"index": 1, "speaker": "Geralt", "text": "I am at peace.", "type": "dialogue", "emotion": "peaceful"},
        {"index": 2, "speaker": "Geralt", "text": "I will destroy everything!", "type": "dialogue", "emotion": "explosive"},
    ]
    result = DramaticValidator.validate_screenplay_and_plan(segments=segments)
    issue_codes = [i.code for i in result.issues]
    assert "EMOTIONAL_TELEPORTATION" in issue_codes


def test_validator_catches_epistemic_breach():
    """Verify DramaticValidator prevents characters from referencing UNKNOWN facts."""
    class MockMemoryContext:
        epistemic_constraints = {
            "geralt": {"UNKNOWN": ["the secret vault under the castle"]}
        }

    segments = [
        {
            "index": 1,
            "speaker": "Geralt",
            "text": "We need to break into the secret vault under the castle tonight.",
            "type": "dialogue",
            "actioning": "reveal",
            "emotion": "serious",
        }
    ]

    result = DramaticValidator.validate_screenplay_and_plan(
        segments=segments,
        memory_context=MockMemoryContext(),
    )
    issue_codes = [i.code for i in result.issues]
    assert "EPISTEMIC_ISOLATION_BREACH" in issue_codes
    assert result.status == "FAIL"


def test_validator_catches_narrator_dialogue_leakage():
    """Verify DramaticValidator strictly flags dialogue misattributed to Narrator."""
    segments = [
        {"index": 1, "speaker": "Narrator", "text": "He stepped into the clearing.", "type": "narration"},
        {"index": 2, "speaker": "Narrator", "text": "Nobody touched anything, sir!", "type": "dialogue"},
    ]
    result = DramaticValidator.validate_screenplay_and_plan(segments=segments)
    assert result.passed is False
    assert result.status == "FAIL"
    issue_codes = [i.code for i in result.issues]
    assert "NARRATOR_DIALOGUE_LEAKAGE" in issue_codes

