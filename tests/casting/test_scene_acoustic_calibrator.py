#!/usr/bin/env python3
"""
Unit tests for SceneAcousticCalibrator (Room 3.5 Subsystem 2).
Verifies:
1. Male + Female dialogue pairs maintain high separation distance.
2. Same-gender colliding speakers receive complementary 4D parametric EQ formants.
3. Parametric EQ clauses are valid FFmpeg filter strings.
4. Phase-Safe Invariant: Zero digital pitch-shifting (asetrate) or WSOLA (atempo).
"""

import pytest
from audiobook_factory.casting.calibrator import SceneAcousticCalibrator
from audiobook_factory.casting.contracts import SpectralFormantProfile


def test_01_gender_contrast_gives_high_distance():
    calibrator = SceneAcousticCalibrator()

    voice_map = {
        "Commander Valen": {"voice": "hi-in-advisor-10", "gender": "male"},
        "Sorceress Elena": {"voice": "hi-in-advisor-1", "gender": "female"},
    }

    dist = calibrator.calculate_speaker_distance("Commander Valen", "Sorceress Elena", voice_map)
    assert dist >= 0.80


def test_02_same_gender_colliding_voices_trigger_complementary_calibration():
    calibrator = SceneAcousticCalibrator()

    # Two soldiers sharing the same base voice
    voice_map = {
        "Soldier A": {"voice": "hi-in-advisor-10", "gender": "male"},
        "Soldier B": {"voice": "hi-in-advisor-10", "gender": "male"},
    }

    segments = [
        {"speaker": "Narrator", "text": "They stood at the battlements.", "type": "narration"},
        {"speaker": "Soldier A", "text": "Do you see the banners in the mist?", "type": "dialogue"},
        {"speaker": "Soldier B", "text": "Yes, they are marching under the raven.", "type": "dialogue"},
    ]

    calibrated_segs, matrix = calibrator.calibrate_scene_segments(
        scene_id="scene_001",
        segments=segments,
        voice_map=voice_map,
    )

    # Initial distance before adjustment was 0.0 or low
    assert "Soldier A:Soldier B" in matrix.pairwise_distances
    # Calibration adjustments must be applied to both soldiers
    assert "Soldier A" in matrix.calibration_adjustments
    assert "Soldier B" in matrix.calibration_adjustments

    adj_a = matrix.calibration_adjustments["Soldier A"]
    adj_b = matrix.calibration_adjustments["Soldier B"]

    # Soldier A gets chest resonance anchor, Soldier B gets forward nasal/presence
    assert adj_a.chest_resonance_150hz_db > 0.0
    assert adj_b.nasal_presence_2800hz_db > 0.0

    # Segments must contain the new filters
    s_a = [s for s in calibrated_segs if s.get("speaker") == "Soldier A"][0]
    s_b = [s for s in calibrated_segs if s.get("speaker") == "Soldier B"][0]

    assert len(s_a.get("eq_filters", [])) > 0
    assert len(s_b.get("eq_filters", [])) > 0

    # Phase-Safe Invariant: Zero asetrate or atempo in eq_filters!
    all_filters = " ".join(s_a["eq_filters"] + s_b["eq_filters"])
    assert "asetrate" not in all_filters
    assert "atempo" not in all_filters
    assert "equalizer=f=" in all_filters


def test_03_ffmpeg_filter_formatting():
    profile = SpectralFormantProfile(
        chest_resonance_150hz_db=2.5,
        nasal_presence_2800hz_db=-1.5,
        throat_clarity_3200hz_db=2.0,
        air_shelf_8000hz_db=-1.0,
    )
    filters = profile.to_ffmpeg_filters()
    assert len(filters) == 4
    assert any("equalizer=f=150" in f for f in filters)
    assert any("equalizer=f=2800" in f for f in filters)
    assert any("equalizer=f=3200" in f for f in filters)
    assert any("equalizer=f=8000" in f for f in filters)
