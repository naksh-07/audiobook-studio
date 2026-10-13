#!/usr/bin/env python3
"""
Unit tests for TTSDispatcher Phase 4 Deliverables:
1. Bi-directional Cast Lock resolution (English & Devanagari & Aliases)
2. Phase-safe 4D Parametric EQ Formant Profile Parsing & Filter Generation
3. Phase-safe micro-pitch alteration (asetrate/aresample) with strict ban on WSOLA atempo
4. Hann micro-fades (12ms pre-speech, 18ms post-speech with curve=hsin)
5. Zero-crossing snapping at audio boundaries
"""

import os
import json
import wave
import struct
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from audiobook_factory.tts.dispatcher import (
    TTSDispatcher,
    _parse_eq_formant_profile,
    _norm_speaker_key,
)
from audiobook_factory.casting.contracts import CastLock


def _create_synthetic_wav_file(path: Path, dur_sec: float = 1.0, sample_rate: int = 24000) -> Path:
    """Creates a valid PCM WAV file on disk for DSP testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(sample_rate * dur_sec)
    samples = [4000 if (i // 50) % 2 == 0 else -4000 for i in range(num_samples)]
    pcm = struct.pack(f"<{num_samples}h", *samples)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return path


# -----------------------------------------------------------------------------
# 1. Bi-directional Cast Lock Resolution Tests
# -----------------------------------------------------------------------------

def test_get_speaker_config_cast_lock_resolution_english(tmp_path: Path):
    dispatcher = TTSDispatcher(project_dir=tmp_path, strict_speakers=True)
    assert dispatcher.cast_lock_manager is not None

    eq_prof = {
        "chest_resonance_150hz_db": 2.5,
        "nasal_presence_2800hz_db": 1.0,
        "throat_clarity_3200hz_db": -1.0,
        "air_shelf_8000hz_db": 0.5,
    }
    dispatcher.cast_lock_manager.lock_character(
        character_id="magistrate_john",
        character_name="Alderman",
        display_name_hi="एल्डरमैन",
        aliases=["Alderman", "नगर प्रमुख"],
        voice_id="hi-in-tutor-8",
        calibration_overrides={"pitch": 0.95, "speed": 1.05},
        eq_formant_profile=eq_prof,
    )

    cfg = dispatcher.get_speaker_config("Alderman", seg_type="dialogue")
    assert cfg["voice"] == "hi-in-tutor-8"
    assert cfg["pitch"] == 0.95
    assert cfg["speed"] == 1.05
    assert cfg["eq_formant_profile"] == eq_prof
    assert cfg["cast_locked"] is True


def test_get_speaker_config_cast_lock_resolution_devanagari(tmp_path: Path):
    dispatcher = TTSDispatcher(project_dir=tmp_path, strict_speakers=True)

    eq_prof = {
        "chest_resonance_150hz_db": 3.0,
        "nasal_presence_2800hz_db": 2.0,
    }
    dispatcher.cast_lock_manager.lock_character(
        character_id="three_jackdaws",
        character_name="Three Jackdaws",
        display_name_hi="थ्री जैकडॉज़",
        aliases=["Three Jackdaws", "बोर्च", "थ्री जैकडॉज़"],
        voice_id="hi-in-tutor-5",
        calibration_overrides={"pitch": 1.04, "speed": 1.02},
        eq_formant_profile=eq_prof,
    )

    # Lookup using Devanagari display name
    cfg_dev = dispatcher.get_speaker_config("थ्री जैकडॉज़", seg_type="dialogue")
    assert cfg_dev["voice"] == "hi-in-tutor-5"
    assert cfg_dev["pitch"] == 1.04
    assert cfg_dev["speed"] == 1.02
    assert cfg_dev["eq_formant_profile"] == eq_prof

    # Lookup using Devanagari alias
    cfg_alias = dispatcher.get_speaker_config("बोर्च", seg_type="dialogue")
    assert cfg_alias["voice"] == "hi-in-tutor-5"
    assert cfg_alias["pitch"] == 1.04

    # Lookup using English canonical name
    cfg_eng = dispatcher.get_speaker_config("Three Jackdaws", seg_type="dialogue")
    assert cfg_eng["voice"] == "hi-in-tutor-5"


def test_get_speaker_config_fallback_to_voice_map_and_alias(tmp_path: Path):
    dispatcher = TTSDispatcher(project_dir=tmp_path, strict_speakers=True)

    dispatcher.voice_map["Mercenary"] = {"voice": "hi-in-advisor-10", "pitch": 0.92, "speed": 1.0}
    cfg = dispatcher.get_speaker_config("Mercenary", seg_type="dialogue")
    assert cfg["voice"] == "hi-in-advisor-10"
    assert cfg["pitch"] == 0.92

    dispatcher.alias_map["भाड़े का सैनिक"] = "Mercenary"
    cfg_alias = dispatcher.get_speaker_config("भाड़े का सैनिक", seg_type="dialogue")
    assert cfg_alias["voice"] == "hi-in-advisor-10"


# -----------------------------------------------------------------------------
# 2. 4-Band Parametric EQ Formant Profile Parsing Tests
# -----------------------------------------------------------------------------

def test_parse_eq_formant_profile_canonical_dict():
    profile = {
        "chest_resonance_150hz_db": 2.5,
        "nasal_presence_2800hz_db": 1.4,
        "throat_clarity_3200hz_db": -1.8,
        "air_shelf_8000hz_db": 0.8,
    }
    filters = _parse_eq_formant_profile(profile)
    assert len(filters) == 4
    assert "equalizer=f=150:width_type=q:w=1.2:g=+2.5" in filters
    assert "equalizer=f=2800:width_type=q:w=1.4:g=+1.4" in filters
    assert "equalizer=f=3200:width_type=q:w=1.4:g=-1.8" in filters
    assert "equalizer=f=8000:width_type=q:w=1.2:g=+0.8" in filters


def test_parse_eq_formant_profile_zero_gain_is_skipped():
    profile = {
        "chest_resonance_150hz_db": 2.0,
        "nasal_presence_2800hz_db": 0.0,
        "throat_clarity_3200hz_db": 0.0,
        "air_shelf_8000hz_db": 0.0,
    }
    filters = _parse_eq_formant_profile(profile)
    assert len(filters) == 1
    assert "equalizer=f=150:width_type=q:w=1.2:g=+2.0" in filters


def test_parse_eq_formant_profile_explicit_bands_list():
    profile = {
        "bands": [
            {"f": 150, "g": 1.8, "w": 1.2},
            {"frequency": 2800, "gain": 2.2, "width": 1.4},
        ]
    }
    filters = _parse_eq_formant_profile(profile)
    assert len(filters) == 2
    assert "equalizer=f=150:width_type=q:w=1.2:g=+1.8" in filters
    assert "equalizer=f=2800:width_type=q:w=1.4:g=+2.2" in filters


def test_parse_eq_formant_profile_string_filter():
    filter_str = "equalizer=f=150:width_type=q:w=1.2:g=+2.5,equalizer=f=2800:width_type=q:w=1.4:g=+1.0"
    filters = _parse_eq_formant_profile(filter_str)
    assert len(filters) == 2
    assert "equalizer=f=150:width_type=q:w=1.2:g=+2.5" in filters
    assert "equalizer=f=2800:width_type=q:w=1.4:g=+1.0" in filters


def test_parse_eq_formant_profile_stringified_dict():
    profile_str = '{"chest_resonance_150hz_db": 2.0, "nasal_presence_2800hz_db": 1.5}'
    filters = _parse_eq_formant_profile(profile_str)
    assert len(filters) == 2
    assert "equalizer=f=150:width_type=q:w=1.2:g=+2.0" in filters
    assert "equalizer=f=2800:width_type=q:w=1.4:g=+1.5" in filters


# -----------------------------------------------------------------------------
# 3. DSP Filter Construction & Hann Micro-Fades in synthesize_segment()
# -----------------------------------------------------------------------------

def test_synthesize_segment_dsp_filters_construction(tmp_path: Path):
    dispatcher = TTSDispatcher(project_dir=tmp_path, strict_speakers=False)
    captured_cmds = []

    def mock_call_gemini_tts(text, output_file, *args, **kwargs):
        _create_synthetic_wav_file(Path(output_file), dur_sec=1.5)

    def mock_subprocess_run(cmd, *args, **kwargs):
        captured_cmds.append(cmd)
        out_target = Path(cmd[-1])
        _create_synthetic_wav_file(out_target, dur_sec=1.5)
        res = MagicMock()
        res.returncode = 0
        return res

    dispatcher.cast_lock_manager.lock_character(
        character_id="hunter",
        character_name="Hunter",
        voice_id="hi-in-advisor-10",
        calibration_overrides={"pitch": 0.95, "speed": 1.0},
        eq_formant_profile={
            "chest_resonance_150hz_db": 2.5,
            "nasal_presence_2800hz_db": 1.2,
        },
    )

    segment = {
        "speaker": "Hunter",
        "type": "dialogue",
        "text": "The beast tracks lead into the ancient forest.",
    }

    with patch("audiobook_factory.tts.dispatcher._call_gemini_tts", side_effect=mock_call_gemini_tts), \
         patch.object(dispatcher.pronunciation_auditor, "audit_take", return_value=MagicMock(passed=True)), \
         patch("subprocess.run", side_effect=mock_subprocess_run):

        out_file, dur = dispatcher.synthesize_segment(segment, chapter_num=1, seg_num=1)

    assert len(captured_cmds) == 1
    ffmpeg_cmd = captured_cmds[0]
    af_index = ffmpeg_cmd.index("-af")
    filter_chain = ffmpeg_cmd[af_index + 1]

    # Verify phase-safe micro-pitch shift
    assert "asetrate=22800,aresample=24000" in filter_chain
    # Verify WSOLA atempo is strictly banned
    assert "atempo" not in filter_chain
    # Verify 4-band parametric EQ formants
    assert "equalizer=f=150:width_type=q:w=1.2:g=+2.5" in filter_chain
    assert "equalizer=f=2800:width_type=q:w=1.4:g=+1.2" in filter_chain
    # Verify Hann micro-fades (12ms pre-speech, 18ms post-speech)
    assert "afade=t=in:ss=0:d=0.012:curve=hsin" in filter_chain
    assert "d=0.018:curve=hsin" in filter_chain
    assert "alimiter=limit=-1.2dB" in filter_chain


def test_synthesize_segment_real_dsp_execution(tmp_path: Path):
    """Runs actual FFmpeg execution to ensure filter complex syntax executes without error."""
    dispatcher = TTSDispatcher(project_dir=tmp_path, strict_speakers=False)

    def mock_call_gemini_tts(text, output_file, *args, **kwargs):
        _create_synthetic_wav_file(Path(output_file), dur_sec=1.0)

    dispatcher.cast_lock_manager.lock_character(
        character_id="bard",
        character_name="Bard",
        voice_id="hi-in-tutor-5",
        calibration_overrides={"pitch": 1.05, "speed": 1.0},
        eq_formant_profile={
            "chest_resonance_150hz_db": -1.0,
            "nasal_presence_2800hz_db": 2.0,
            "throat_clarity_3200hz_db": 1.5,
            "air_shelf_8000hz_db": 1.0,
        },
    )

    segment = {
        "speaker": "Bard",
        "type": "dialogue",
        "text": "Listen to the song of the silver mountains.",
    }

    with patch("audiobook_factory.tts.dispatcher._call_gemini_tts", side_effect=mock_call_gemini_tts), \
         patch.object(dispatcher.pronunciation_auditor, "audit_take", return_value=MagicMock(passed=True)):

        out_file, dur = dispatcher.synthesize_segment(segment, chapter_num=1, seg_num=2)

    assert out_file.exists()
    assert out_file.stat().st_size > 1000
    with wave.open(str(out_file), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 24000
        assert wf.getnframes() > 0
