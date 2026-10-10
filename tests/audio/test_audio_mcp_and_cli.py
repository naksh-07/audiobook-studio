import io
import sys
import wave
import json
import numpy as np
import pytest
from pathlib import Path
from types import SimpleNamespace

from audiobook_factory.mcp.server import (
    apply_vocal_dsp_tool,
    audit_audio_quality_tool,
    match_reference_spectrum_tool,
    enhance_vocal_stem_tool,
    measure_ebu_r128_loudness_tool,
    audit_chapter_qa_tool,
    run_stdio_server,
)
from audiobook_factory.cli.commands.audio import (
    cmd_dsp,
    cmd_qa_audit,
    cmd_enhance,
    cmd_match_ref,
)


def _generate_wav(path: Path, duration_sec: float = 1.0, freq: float = 440.0, sample_rate: int = 48000, amplitude: float = 0.5):
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    audio = amplitude * np.sin(2 * np.pi * freq * t)
    int16_samples = (audio * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int16_samples.tobytes())


def test_mcp_apply_vocal_dsp_tool(tmp_path: Path):
    in_wav = tmp_path / "in.wav"
    out_wav = tmp_path / "out.wav"
    _generate_wav(in_wav, duration_sec=1.5, amplitude=0.4)

    res = apply_vocal_dsp_tool(
        input_wav=str(in_wav),
        output_wav=str(out_wav),
        target_lufs=-19.0,
        true_peak_ceiling_dbtp=-1.5,
    )

    assert res["status"] == "SUCCESS"
    assert "backend_used" in res
    assert Path(res["output_path"]).exists()
    assert res["true_peak_dbtp"] <= -1.4


def test_mcp_audit_audio_quality_tool(tmp_path: Path):
    wav = tmp_path / "segment.wav"
    _generate_wav(wav, duration_sec=1.0, amplitude=0.3)

    res = audit_audio_quality_tool(
        audio_path=str(wav),
        expected_text="यह एक परीक्षण संवाद है।",
        speaker="Geralt",
        segment_index=1,
    )

    assert "segment_uid" in res
    assert "status" in res
    assert "predicted_mos" in res
    assert res["speaker"] == "Geralt"


def test_mcp_match_reference_spectrum_tool(tmp_path: Path):
    tgt = tmp_path / "tgt.wav"
    ref = tmp_path / "ref.wav"
    out = tmp_path / "matched.wav"
    _generate_wav(tgt, duration_sec=1.0, freq=300.0, amplitude=0.3)
    _generate_wav(ref, duration_sec=1.0, freq=600.0, amplitude=0.4)

    res = match_reference_spectrum_tool(
        target_wav=str(tgt),
        reference_wav=str(ref),
        output_wav=str(out),
        max_clamp_db=3.0,
    )

    assert res["status"] == "SUCCESS"
    assert Path(res["output_path"]).exists()
    assert res["max_clamp_db"] == 3.0


def test_mcp_enhance_vocal_stem_tool(tmp_path: Path):
    in_wav = tmp_path / "noisy.wav"
    out_wav = tmp_path / "clean.wav"
    _generate_wav(in_wav, duration_sec=1.0, amplitude=0.4)

    res = enhance_vocal_stem_tool(
        input_wav=str(in_wav),
        output_wav=str(out_wav),
        snr_bypass_db=45.0,
    )

    assert res["status"] == "SUCCESS"
    assert Path(res["output_path"]).exists()
    assert "was_enhanced" in res


def test_mcp_measure_ebu_r128_loudness_tool(tmp_path: Path):
    wav = tmp_path / "measure.wav"
    _generate_wav(wav, duration_sec=1.0, amplitude=0.4)

    res = measure_ebu_r128_loudness_tool(str(wav))

    assert "integrated_lufs" in res
    assert "true_peak_dbtp" in res
    assert "compliant_audible" in res


def test_mcp_audit_chapter_qa_tool(tmp_path: Path):
    seg1 = tmp_path / "seg1.wav"
    seg2 = tmp_path / "seg2.wav"
    _generate_wav(seg1, duration_sec=1.0, amplitude=0.3)
    _generate_wav(seg2, duration_sec=1.2, amplitude=0.4)

    script_segments = [
        {"speaker": "Narrator", "text": "रात का सन्नाटा गहरा था।"},
        {"speaker": "Yennefer", "text": "क्या तुम सुन रहे हो?"},
    ]

    res = audit_chapter_qa_tool(
        audio_segments=[str(seg1), str(seg2)],
        script_segments=script_segments,
        chapter_num=1,
    )

    assert res["chapter_num"] == 1
    assert res["total_segments"] == 2
    assert len(res["evaluations"]) == 2
    assert "overall_status" in res


def test_mcp_stdio_server_loop(monkeypatch, tmp_path: Path):
    wav = tmp_path / "test.wav"
    _generate_wav(wav, duration_sec=1.0, amplitude=0.3)

    req1 = {"tool": "measure_ebu_r128_loudness", "args": {"audio_path": str(wav)}}
    req2 = {"tool": "unknown_tool", "args": {}}
    input_str = json.dumps(req1) + "\n" + json.dumps(req2) + "\n"

    fake_stdin = io.StringIO(input_str)
    fake_stdout = io.StringIO()

    monkeypatch.setattr(sys, "stdin", fake_stdin)
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    run_stdio_server()

    output_lines = [line for line in fake_stdout.getvalue().split("\n") if line.strip()]
    assert len(output_lines) == 2

    resp1 = json.loads(output_lines[0])
    assert resp1["status"] == "ok"
    assert "integrated_lufs" in resp1["result"]

    resp2 = json.loads(output_lines[1])
    assert resp2["status"] == "error"
    assert "Unknown tool" in resp2["message"]


def test_cli_dsp_command(tmp_path: Path, capsys):
    in_wav = tmp_path / "cli_in.wav"
    out_wav = tmp_path / "cli_out.wav"
    _generate_wav(in_wav, duration_sec=1.0, amplitude=0.3)

    args = SimpleNamespace(
        input=str(in_wav),
        output=str(out_wav),
        target_lufs=-19.0,
        true_peak=-1.5,
    )

    cmd_dsp(args)
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["status"] == "SUCCESS"
    assert out_wav.exists()


def test_cli_qa_audit_command(tmp_path: Path, capsys):
    wav = tmp_path / "cli_qa.wav"
    _generate_wav(wav, duration_sec=1.0, amplitude=0.3)

    args = SimpleNamespace(
        input=str(wav),
        text="परीक्षण पाठ",
        speaker="Narrator",
    )

    cmd_qa_audit(args)
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert "status" in res
    assert "predicted_mos" in res


def test_cli_enhance_command(tmp_path: Path, capsys):
    in_wav = tmp_path / "cli_noisy.wav"
    out_wav = tmp_path / "cli_enhanced.wav"
    _generate_wav(in_wav, duration_sec=1.0, amplitude=0.3)

    args = SimpleNamespace(
        input=str(in_wav),
        output=str(out_wav),
    )

    cmd_enhance(args)
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["status"] == "SUCCESS"
    assert out_wav.exists()


def test_cli_match_ref_command(tmp_path: Path, capsys):
    tgt = tmp_path / "cli_tgt.wav"
    ref = tmp_path / "cli_ref.wav"
    out = tmp_path / "cli_matched.wav"
    _generate_wav(tgt, duration_sec=1.0, freq=300.0, amplitude=0.3)
    _generate_wav(ref, duration_sec=1.0, freq=600.0, amplitude=0.4)

    args = SimpleNamespace(
        target=str(tgt),
        reference=str(ref),
        output=str(out),
        max_clamp=3.0,
    )

    cmd_match_ref(args)
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["status"] == "SUCCESS"
    assert out.exists()
