#!/usr/bin/env python3
"""
Tests for synchronous Gate 2.8 and Gate 2.9 pre-flight enforcement in TTSDispatcher.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from audiobook_factory.tts.dispatcher import TTSDispatcher
from audiobook_factory.gates.contracts import GateAuditError


def test_dispatcher_halts_on_gate28_banned_dsp(tmp_path: Path):
    """Verify TTSDispatcher halts on Gate 2.8 violation (banned asetrate/atempo DSP)."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_file = scripts_dir / "chapter_001_script.json"

    # Script containing banned DSP
    script_data = [
        {"index": 1, "speaker": "Narrator", "type": "narration", "text": "Night fell."},
        {
            "index": 2,
            "speaker": "Hero",
            "type": "dialogue",
            "text": "Hello there.",
            "eq_filters": ["asetrate=24000*1.2"],
        },
    ]
    with open(script_file, "w", encoding="utf-8") as f:
        json.dump(script_data, f)

    # Set up valid voice registry
    with open(tmp_path / "voice_registry.json", "w", encoding="utf-8") as f:
        json.dump({"Hero": {"voice": "Charon", "assigned_voice_id": "Charon"}}, f)

    # Set up cast lock
    with open(tmp_path / "cast_lock.json", "w", encoding="utf-8") as f:
        json.dump({"locks": {"hero": {"locked": True, "voice_id": "Charon"}}}, f)

    dispatcher = TTSDispatcher(project_dir=tmp_path, strict_speakers=True)

    with pytest.raises(GateAuditError) as exc_info:
        dispatcher.synthesize_chapter_script(script_file, chapter_num=1)

    assert "Destructive digital pitch-shifting (asetrate) is strictly forbidden" in str(exc_info.value)


def test_dispatcher_halts_on_gate29_acoustic_out_of_bounds(tmp_path: Path):
    """Verify TTSDispatcher halts on Gate 2.9 violation (pitch or speed out of bounds)."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_file = scripts_dir / "chapter_001_script.json"

    # Script containing extreme pitch out of bounds
    script_data = [
        {"index": 1, "speaker": "Narrator", "type": "narration", "text": "Night fell."},
        {
            "index": 2,
            "speaker": "Hero",
            "type": "dialogue",
            "text": "Hello there.",
            "pitch": 2.50,  # Max allowed is 1.35
            "speed": 1.0,
        },
    ]
    with open(script_file, "w", encoding="utf-8") as f:
        json.dump(script_data, f)

    with open(tmp_path / "voice_registry.json", "w", encoding="utf-8") as f:
        json.dump({"Hero": {"voice": "Charon", "assigned_voice_id": "Charon"}}, f)

    with open(tmp_path / "cast_lock.json", "w", encoding="utf-8") as f:
        json.dump({"locks": {"hero": {"locked": True, "voice_id": "Charon"}}}, f)

    dispatcher = TTSDispatcher(project_dir=tmp_path, strict_speakers=True)

    with pytest.raises(GateAuditError) as exc_info:
        dispatcher.synthesize_chapter_script(script_file, chapter_num=1)

    assert "pitch" in str(exc_info.value).lower()
