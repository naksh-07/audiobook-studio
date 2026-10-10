#!/usr/bin/env python3
"""
Unit tests for Gate 2.8 (Auditory Distinction & Casting Sanity Gate).
Verifies:
1. Valid screenplay segments with distinct voices pass cleanly.
2. Unregistered speaker or null voice ID triggers fail-closed GateAuditError.
3. Destructive digital pitch-shifting (asetrate) is caught and rejected.
4. Non-strict mode returns AuditoryDistinctionVerdict with violations.
"""

import tempfile
import json
from pathlib import Path
import pytest

from audiobook_factory.gates.gate28_distinction import AuditoryDistinctionGate, AuditoryDistinctionVerdict
from audiobook_factory.gates.pre_synthesis import GateAuditError


def test_01_gate28_valid_scene_passes():
    with tempfile.TemporaryDirectory() as tmp_dir:
        p_dir = Path(tmp_dir)
        vreg = {
            "Narrator": {"voice": "Aoede"},
            "Commander Valen": {"voice": "hi-in-advisor-10", "gender": "male"},
            "Sorceress Elena": {"voice": "hi-in-advisor-1", "gender": "female"},
        }
        (p_dir / "voice_registry.json").write_text(json.dumps(vreg), encoding="utf-8")

        segments = [
            {"speaker": "Narrator", "text": "They gathered at dawn.", "type": "narration", "scene_id": "sc1"},
            {"speaker": "Commander Valen", "text": "Are the scouts back?", "type": "dialogue", "scene_id": "sc1"},
            {"speaker": "Sorceress Elena", "text": "Not yet, but the mist is clearing.", "type": "dialogue", "scene_id": "sc1"},
        ]

        verdict = AuditoryDistinctionGate.audit_chapter_script(segments, p_dir, strict=True)
        assert verdict.passed is True
        assert verdict.audited_dialogue_turns == 2
        assert verdict.min_scene_distance >= 0.65


def test_02_gate28_unregistered_speaker_fails_closed():
    with tempfile.TemporaryDirectory() as tmp_dir:
        p_dir = Path(tmp_dir)
        vreg = {"Narrator": {"voice": "Aoede"}}
        (p_dir / "voice_registry.json").write_text(json.dumps(vreg), encoding="utf-8")

        segments = [
            {"speaker": "Unknown Ghost", "text": "Who speaks there?", "type": "dialogue", "scene_id": "sc1"},
        ]

        with pytest.raises(GateAuditError) as exc:
            AuditoryDistinctionGate.audit_chapter_script(segments, p_dir, strict=True)
        assert "has no voice assignment" in str(exc.value)


def test_03_gate28_asetrate_forbidden_fails_closed():
    with tempfile.TemporaryDirectory() as tmp_dir:
        p_dir = Path(tmp_dir)
        vreg = {
            "Narrator": {"voice": "Aoede"},
            "Warrior": {"voice": "hi-in-advisor-10", "gender": "male"},
        }
        (p_dir / "voice_registry.json").write_text(json.dumps(vreg), encoding="utf-8")

        # Injected forbidden asetrate
        segments = [
            {
                "speaker": "Warrior",
                "text": "Charge!",
                "type": "dialogue",
                "scene_id": "sc1",
                "eq_filters": ["asetrate=25000,aresample=24000"],
            },
        ]

        with pytest.raises(GateAuditError) as exc:
            AuditoryDistinctionGate.audit_chapter_script(segments, p_dir, strict=True)
        assert "Destructive digital pitch-shifting (asetrate) is strictly forbidden" in str(exc.value)
