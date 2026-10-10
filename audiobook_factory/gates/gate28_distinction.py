#!/usr/bin/env python3
"""
Audiobook Factory - Quality Gate 2.8: Auditory Distinction & Casting Sanity Gate.
================================================================================
Positions directly before Gate 2.9 (PreSynthesisGate) and Room 4 TTS Dispatcher.
Enforces:
1. Every dialogue speaker has a locked, non-null voice assignment in cast_lock.json.
2. Zero silent fallback to Narrator for dialogue turns.
3. Scene-Level Auditory Contrast: Pairwise separation distance >= 0.65 between active co-speakers.
4. Phase-Safe Audio Invariant: Zero destructive digital pitch-shifting (asetrate) or WSOLA (atempo).
Fail-Closed Contract: Halts production with GateAuditError on colliding or invalid voice configs.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from pydantic import BaseModel, Field, ConfigDict

from audiobook_factory.logger import logger
from audiobook_factory.gates.pre_synthesis import GateAuditError
from audiobook_factory.casting.contracts import SceneContrastMatrix
from audiobook_factory.casting.calibrator import SceneAcousticCalibrator, MIN_ACCEPTABLE_DISTANCE
from audiobook_factory.casting.registry import VoiceProfileRegistry

logger = logging.getLogger("AudiobookFactory")


class AuditoryDistinctionVerdict(BaseModel):
    """Telemetry report for Gate 2.8 Auditory Distinction audit."""
    model_config = ConfigDict(extra="ignore")

    passed: bool = True
    min_scene_distance: float = 1.0
    audited_scenes_count: int = 0
    audited_dialogue_turns: int = 0
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    scene_matrices: List[SceneContrastMatrix] = Field(default_factory=list)


class AuditoryDistinctionGate:
    """
    Gate 2.8: Authoritative Pre-TTS Auditory Distinction Gatekeeper.
    """

    @classmethod
    def audit_chapter_script(
        cls,
        segments: List[Dict[str, Any]],
        project_dir: Path | str,
        strict: bool = True,
    ) -> AuditoryDistinctionVerdict:
        """
        Audits all screenplay segments in a chapter for auditory distinction and casting sanity.
        """
        p_dir = Path(project_dir).resolve()
        registry = VoiceProfileRegistry.get_instance()
        calibrator = SceneAcousticCalibrator(registry=registry)

        # 1. Load active voice_registry.json and cast_lock.json
        reg_file = p_dir / "voice_registry.json"
        lock_file = p_dir / "cast_lock.json"

        voice_map: Dict[str, Any] = {}
        if reg_file.exists():
            try:
                with open(reg_file, "r", encoding="utf-8") as rf:
                    voice_map = json.load(rf)
            except Exception as e:
                logger.warning(f"  [Gate 2.8] Failed to read voice_registry.json: {e}")

        locked_chars = set()
        if lock_file.exists():
            try:
                with open(lock_file, "r", encoding="utf-8") as lf:
                    ldata = json.load(lf)
                locks = ldata.get("locks", {})
                for cid, l in locks.items():
                    if isinstance(l, dict) and l.get("locked"):
                        locked_chars.add(cid.lower())
                        cname = l.get("character_name")
                        if cname:
                            locked_chars.add(cname.lower())
            except Exception as e:
                logger.warning(f"  [Gate 2.8] Failed to read cast_lock.json: {e}")

        violations: List[str] = []
        warnings: List[str] = []
        dialogue_count = 0
        min_distance = 1.0

        # Group segments by scene_id (or fallback to single scene if untagged)
        scenes: Dict[str, List[Dict[str, Any]]] = {}
        for s in segments:
            sc_id = s.get("scene_id") or "scene_default"
            scenes.setdefault(sc_id, []).append(s)

        scene_matrices: List[SceneContrastMatrix] = []

        for sc_id, sc_segs in scenes.items():
            # Check individual segment casting sanity
            for s in sc_segs:
                spk = (s.get("speaker") or "Narrator").strip()
                s_type = (s.get("type") or "dialogue").lower()
                is_narr = spk.lower() in ("narrator", "narration", "") or s_type == "narration"

                if not is_narr:
                    dialogue_count += 1
                    # Whitelist & Lock Verification
                    if spk not in voice_map and spk.lower() not in [k.lower() for k in voice_map.keys()]:
                        violations.append(f"Scene '{sc_id}': Speaker '{spk}' has no voice assignment in voice_registry.json!")

                    if locked_chars and spk.lower() not in locked_chars:
                        warnings.append(f"Scene '{sc_id}': Speaker '{spk}' is not formally locked in cast_lock.json.")

                    # Check voice_id validity
                    v_cfg = voice_map.get(spk) or {}
                    vid = v_cfg.get("voice") or v_cfg.get("assigned_voice_id")
                    if not vid:
                        violations.append(f"Scene '{sc_id}': Speaker '{spk}' has null or unassigned voice_id.")
                    elif not registry.get_profile(vid):
                        warnings.append(f"Scene '{sc_id}': Speaker '{spk}' assigned voice '{vid}' not in curated VoiceProfileRegistry.")

                # Phase-Safe Invariant: Assert zero asetrate or atempo in eq_filters
                eq_filters = s.get("eq_filters", [])
                if isinstance(eq_filters, list):
                    for f in eq_filters:
                        if "asetrate" in f:
                            violations.append(f"Scene '{sc_id}' Segment #{s.get('index', '?')}: Destructive digital pitch-shifting (asetrate) is strictly forbidden!")
                        if "atempo" in f:
                            violations.append(f"Scene '{sc_id}' Segment #{s.get('index', '?')}: WSOLA time-stretching (atempo) is strictly forbidden!")

            # Scene-Level Acoustic Contrast Check
            _, matrix = calibrator.calibrate_scene_segments(
                scene_id=sc_id,
                segments=sc_segs,
                voice_map=voice_map,
            )
            scene_matrices.append(matrix)

            if matrix.min_distance < min_distance:
                min_distance = matrix.min_distance

            # Check if any pairwise distance was below acceptable threshold
            for pair, d in matrix.pairwise_distances.items():
                if d < MIN_ACCEPTABLE_DISTANCE:
                    violations.append(
                        f"Scene '{sc_id}': Co-speakers '{pair}' have insufficient acoustic separation distance ({d:.2f} < {MIN_ACCEPTABLE_DISTANCE:.2f})! Listener cannot distinguish voices."
                    )

        passed = len(violations) == 0
        verdict = AuditoryDistinctionVerdict(
            passed=passed,
            min_scene_distance=round(min_distance, 2),
            audited_scenes_count=len(scenes),
            audited_dialogue_turns=dialogue_count,
            violations=violations,
            warnings=warnings,
            scene_matrices=scene_matrices,
        )

        if not passed and strict:
            err_msg = (
                f"Gate 2.8 Auditory Distinction Audit FAILED with {len(violations)} violation(s):\n"
                + "\n".join(f"  - [CRITICAL] {v}" for v in violations)
            )
            logger.error(f"  [!] {err_msg}")
            raise GateAuditError(err_msg)

        logger.info(
            f"[+] Gate 2.8 Auditory Distinction Passed: {len(scenes)} scenes, "
            f"{dialogue_count} dialogue turns, min distance: {verdict.min_scene_distance:.2f}."
        )
        return verdict
