#!/usr/bin/env python3
"""
Audiobook Factory - Antigravity Audio MCP Server (v5.4).
========================================================
Exposes high-level studio mastering DSP, QA auditing, neural speech polish,
and reference spectrum matching endpoints for Antigravity autonomous agents.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from audiobook_factory.logger import logger
from audiobook_factory.audio.contracts import (
    DSPConfig,
    AudioQAConfig,
    EnhancerConfig,
    ReferenceMatcherConfig,
)
from audiobook_factory.audio.dsp import VocalDSPProcessor, has_pedalboard_engine
from audiobook_factory.audio.qa_auditor import AudioQAAuditor
from audiobook_factory.audio.enhancer import NeuralVocalEnhancer
from audiobook_factory.audio.reference_matcher import ReferenceSpectrumMatcher


def apply_vocal_dsp_tool(
    input_wav: str,
    output_wav: str,
    target_lufs: float = -19.0,
    true_peak_ceiling_dbtp: float = -1.5,
    subsonic_hz: float = 75.0,
    boxiness_cut_db: float = -1.5,
    presence_lift_db: float = 0.8,
) -> Dict[str, Any]:
    """
    Applies C++ JUCE parametric vocal EQ, optical compression, and lookahead True-Peak limiting.
    """
    dsp = VocalDSPProcessor()
    cfg = DSPConfig(
        target_lufs=target_lufs,
        true_peak_ceiling_dbtp=true_peak_ceiling_dbtp,
        subsonic_hz=subsonic_hz,
        boxiness_cut_db=boxiness_cut_db,
        presence_lift_db=presence_lift_db,
    )
    result = dsp.master_chapter(input_wav, output_wav, dsp_config=cfg)
    return {
        "status": "SUCCESS",
        "backend_used": result.backend_used,
        "output_path": str(result.output_path),
        "integrated_lufs": result.integrated_lufs,
        "true_peak_dbtp": result.true_peak_dbtp,
        "loudness_range_lu": result.loudness_range_lu,
        "execution_duration_sec": result.execution_duration_sec,
    }


def audit_audio_quality_tool(
    audio_path: str,
    expected_text: str = "",
    speaker: str = "Narrator",
    segment_index: int = 1,
) -> Dict[str, Any]:
    """
    Audits a single speech audio segment for dead air, WPM pacing, dropouts, loops, and MOS.
    """
    auditor = AudioQAAuditor()
    eval_res = auditor.audit_segment(
        audio_path=audio_path,
        expected_text=expected_text,
        speaker=speaker,
        segment_index=segment_index,
    )
    return eval_res.model_dump()


def match_reference_spectrum_tool(
    target_wav: str,
    reference_wav: str,
    output_wav: str,
    max_clamp_db: float = 3.0,
) -> Dict[str, Any]:
    """
    Matches frequency spectrum and tonal envelope of target audio to a golden reference track.
    """
    matcher = ReferenceSpectrumMatcher(
        config=ReferenceMatcherConfig(enable_reference_matching=True, max_spectral_correction_db=max_clamp_db)
    )
    out_path = matcher.match_files(target_wav, reference_wav, output_wav)
    return {
        "status": "SUCCESS",
        "output_path": str(out_path),
        "max_clamp_db": max_clamp_db,
    }


def enhance_vocal_stem_tool(
    input_wav: str,
    output_wav: str,
    snr_bypass_db: float = 45.0,
) -> Dict[str, Any]:
    """
    Cleans synthetic TTS hash and room noise via DeepFilterNet3 / spectral gate with auto-bypass.
    """
    enhancer = NeuralVocalEnhancer(
        config=EnhancerConfig(enable_neural_enhancement=True, snr_bypass_threshold_db=snr_bypass_db)
    )
    was_enhanced = enhancer.enhance_file(input_wav, output_wav)
    return {
        "status": "SUCCESS",
        "output_path": str(output_wav),
        "was_enhanced": was_enhanced,
    }


def measure_ebu_r128_loudness_tool(audio_path: str) -> Dict[str, Any]:
    """
    Measures ITU-R BS.1770-4 Integrated Loudness (LUFS), True Peak (dBTP), and LRA.
    """
    dsp = VocalDSPProcessor()
    data, sr = dsp._read_wav(Path(audio_path))
    lufs, tp, lra = dsp.measure_loudness(data, sr=sr)
    return {
        "filepath": str(Path(audio_path).resolve()),
        "integrated_lufs": round(lufs, 2),
        "true_peak_dbtp": round(tp, 2),
        "loudness_range_lu": round(lra, 2),
        "compliant_audible": (-21.0 <= lufs <= -17.0 and tp <= -1.4),
    }


def audit_chapter_qa_tool(
    audio_segments: List[str],
    script_segments: Optional[List[Dict[str, Any]]] = None,
    chapter_num: int = 1,
) -> Dict[str, Any]:
    """
    Audits an entire chapter timeline and returns aggregated forensic QA report.
    """
    auditor = AudioQAAuditor()
    report = auditor.audit_chapter(
        audio_segments=audio_segments,
        script_segments=script_segments,
        chapter_num=chapter_num,
    )
    return report.model_dump()


def run_stdio_server():
    """Simple JSON-RPC / Stdio server loop for Antigravity agent communication."""
    tools = {
        "apply_vocal_dsp": apply_vocal_dsp_tool,
        "audit_audio_quality": audit_audio_quality_tool,
        "match_reference_spectrum": match_reference_spectrum_tool,
        "enhance_vocal_stem": enhance_vocal_stem_tool,
        "measure_ebu_r128_loudness": measure_ebu_r128_loudness_tool,
        "audit_chapter_qa": audit_chapter_qa_tool,
    }

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            if not isinstance(req, dict):
                raise ValueError("Request must be a JSON object.")
            tool_name = req.get("tool")
            args = req.get("args", {})
            if tool_name in tools:
                res = tools[tool_name](**args)
                sys.stdout.write(json.dumps({"status": "ok", "result": res}) + "\n")
            else:
                sys.stdout.write(json.dumps({"status": "error", "message": f"Unknown tool: {tool_name}"}) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"status": "error", "message": str(e)}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
