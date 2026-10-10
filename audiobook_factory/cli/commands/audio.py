from __future__ import annotations
import os
import sys
import re
import json
from pathlib import Path

from audiobook_factory.cli.context import get_projects_dir, get_workspace_dir
from audiobook_factory.audio_utils import get_ffmpeg, get_audio_duration
from audiobook_factory.packager import package_m4b_audiobook


def cmd_soundscape(args):
    print("[*] Soundscape planning is decoupled in Vocals-Only mode.")


def cmd_bgm(args):
    print("[*] BGM and soundscape scoring are decoupled in Vocals-Only mode.")


def cmd_stems(args):
    print("[*] Discrete multi-track stems are decoupled in Vocals-Only mode (pure vocal master delivered).")


def cmd_package(args):
    target = Path(args.book)
    project_dir = target if (target.exists() and target.is_dir()) else (get_projects_dir() / args.book)
    cover = Path(args.cover) if getattr(args, "cover", None) else None
    enforce = getattr(args, "enforce_gate6", False)
    format_mode = getattr(args, "format", "audiobook")

    from audiobook_factory.packaging import package_project
    res = package_project(
        project_dir=project_dir,
        format_mode=format_mode,
        cover_image=cover,
        enforce_gate6=enforce,
    )
    print(f"\n[DONE] Finished Packaging ({format_mode}):")
    for k, v in res.get("artifacts", {}).items():
        print(f"  - {k}: {v}")



def cmd_direct(args):
    print("[*] AgentDirector manifest direct is decoupled in Vocals-Only mode.")


def cmd_render(args):
    print("[*] Manifest multitrack render is decoupled in Vocals-Only mode.")


def cmd_timeline(args):
    print("[*] Timeline command executed.")


def cmd_dsp(args):
    """Executes C++ JUCE DSP vocal mastering on input WAV file."""
    from audiobook_factory.mcp.server import apply_vocal_dsp_tool
    try:
        res = apply_vocal_dsp_tool(
            input_wav=args.input,
            output_wav=args.output,
            target_lufs=getattr(args, "target_lufs", -19.0),
            true_peak_ceiling_dbtp=getattr(args, "true_peak", -1.5),
        )
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_qa_audit(args):
    """Executes forensic speech QA audit on an audio segment or chapter."""
    from audiobook_factory.mcp.server import audit_audio_quality_tool
    try:
        text = getattr(args, "text", "")
        speaker = getattr(args, "speaker", "Narrator")
        res = audit_audio_quality_tool(audio_path=args.input, expected_text=text, speaker=speaker)
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_enhance(args):
    """Executes DeepFilterNet3 neural vocal cleaning on audio file."""
    from audiobook_factory.mcp.server import enhance_vocal_stem_tool
    try:
        res = enhance_vocal_stem_tool(input_wav=args.input, output_wav=args.output)
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_match_ref(args):
    """Matches target frequency spectrum to reference golden master."""
    from audiobook_factory.mcp.server import match_reference_spectrum_tool
    try:
        res = match_reference_spectrum_tool(
            target_wav=args.target,
            reference_wav=args.reference,
            output_wav=args.output,
            max_clamp_db=getattr(args, "max_clamp", 3.0),
        )
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(1)

