#!/usr/bin/env python3
"""
Audiobook Studio - Command Line Interface for Podcast & Technical Document Engine.
==================================================================================
Subcommands:
  produce   - Ingest document, generate dual-host script, synthesize voices & master audio.
  script    - Ingest document and generate podcast_script.json only.
  render    - Synthesize and master an existing podcast_script.json file.
  inspect   - Inspect a podcast script or production manifest.
"""

from __future__ import annotations
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List

from audiobook_factory.podcast.contracts import VerbalizationStyle
from audiobook_factory.podcast.orchestrator import PodcastOrchestrator, process_document_to_podcast


def create_podcast_parser() -> argparse.ArgumentParser:
    """Constructs the argument parser for podcast CLI subcommands."""
    parser = argparse.ArgumentParser(
        prog="podcast",
        description="Audiobook Studio - Technical Paper & Research Podcast Generator",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Podcast action to execute")

    # -------------------------------------------------------------
    # Subcommand: produce
    # -------------------------------------------------------------
    p_produce = subparsers.add_parser(
        "produce",
        help="Run end-to-end ingestion, scripting, TTS synthesis, and EBU R128 mastering",
    )
    p_produce.add_argument("file", help="Path to input paper/document (.pdf, .md, .txt, .epub)")
    p_produce.add_argument("--output-dir", default=None, help="Target project output directory")
    p_produce.add_argument(
        "--style",
        choices=["conversational_podcast", "formal_lecture", "narrative_audiobook"],
        default="conversational_podcast",
        help="Podcast verbalization style (default: conversational_podcast)",
    )
    p_produce.add_argument("--host-a-name", default="Dr. Vance", help="Name of Lead Explainer host (default: Dr. Vance)")
    p_produce.add_argument("--host-a-voice", default="Charon", help="TTS voice for Host A (default: Charon)")
    p_produce.add_argument("--host-b-name", default="Maya", help="Name of Co-host (default: Maya)")
    p_produce.add_argument("--host-b-voice", default="Aoede", help="TTS voice for Host B (default: Aoede)")
    p_produce.add_argument("--mock", action="store_true", help="Run with synthetic audio chunks (zero quota / offline mode)")
    p_produce.add_argument("--force-gate", action="store_true", help="Bypass Extraction Quality Gate REVIEW failure")

    # -------------------------------------------------------------
    # Subcommand: script
    # -------------------------------------------------------------
    p_script = subparsers.add_parser(
        "script",
        help="Ingest document and generate dual-host podcast_script.json without audio synthesis",
    )
    p_script.add_argument("file", help="Path to input paper/document (.pdf, .md, .txt, .epub)")
    p_script.add_argument("--output-dir", default=None, help="Target project output directory")
    p_script.add_argument(
        "--style",
        choices=["conversational_podcast", "formal_lecture", "narrative_audiobook"],
        default="conversational_podcast",
        help="Podcast verbalization style (default: conversational_podcast)",
    )
    p_script.add_argument("--host-a-name", default="Dr. Vance", help="Name of Lead Explainer host")
    p_script.add_argument("--host-a-voice", default="Charon", help="TTS voice for Host A")
    p_script.add_argument("--host-b-name", default="Maya", help="Name of Co-host")
    p_script.add_argument("--host-b-voice", default="Aoede", help="TTS voice for Host B")
    p_script.add_argument("--force-gate", action="store_true", help="Bypass Extraction Quality Gate REVIEW failure")

    # -------------------------------------------------------------
    # Subcommand: render
    # -------------------------------------------------------------
    p_render = subparsers.add_parser(
        "render",
        help="Synthesize and master an existing podcast_script.json file",
    )
    p_render.add_argument("script_file", help="Path to podcast_script.json")
    p_render.add_argument("--output-dir", default=None, help="Target production directory")
    p_render.add_argument("--mock", action="store_true", help="Run with synthetic audio chunks (zero quota / offline mode)")

    # -------------------------------------------------------------
    # Subcommand: inspect
    # -------------------------------------------------------------
    p_inspect = subparsers.add_parser(
        "inspect",
        help="Inspect an existing podcast script or production manifest",
    )
    p_inspect.add_argument("path", help="Path to podcast_script.json or production manifest JSON")

    return parser


def handle_produce(args: argparse.Namespace) -> int:
    """Handles the produce subcommand."""
    print(f"[*] Starting podcast production for: {args.file}")
    res = process_document_to_podcast(
        source_file=args.file,
        output_dir=args.output_dir,
        style=args.style,
        host_a_name=args.host_a_name,
        host_a_voice=args.host_a_voice,
        host_b_name=args.host_b_name,
        host_b_voice=args.host_b_voice,
        script_only=False,
        mock_mode=args.mock,
        force_gate=args.force_gate,
    )

    if res.status == "SUCCESS":
        print(f"\n[+] Podcast successfully produced!")
        print(f"    Episode Title / ID : {res.podcast_id}")
        print(f"    Total Spoken Turns : {res.total_segments}")
        print(f"    Total Spoken Words : {res.total_words}")
        print(f"    Mastered Duration  : {res.duration_sec:.1f} seconds")
        print(f"    Integrated Loudness: {res.integrated_lufs:.1f} LUFS")
        print(f"    True Peak Ceiling  : {res.true_peak_db:.1f} dBTP")
        print(f"    Script Path        : {res.script_path}")
        print(f"    Mastered Audio     : {res.mastered_audio_path}")
        return 0
    else:
        print(f"\n[!] Podcast production failed: {res.error_message}", file=sys.stderr)
        return 1


def handle_script(args: argparse.Namespace) -> int:
    """Handles the script subcommand."""
    print(f"[*] Generating podcast script for: {args.file}")
    res = process_document_to_podcast(
        source_file=args.file,
        output_dir=args.output_dir,
        style=args.style,
        host_a_name=args.host_a_name,
        host_a_voice=args.host_a_voice,
        host_b_name=args.host_b_name,
        host_b_voice=args.host_b_voice,
        script_only=True,
        mock_mode=False,
        force_gate=args.force_gate,
    )

    if res.status == "SUCCESS":
        print(f"\n[+] Script successfully generated!")
        print(f"    Total Turns : {res.total_segments}")
        print(f"    Total Words : {res.total_words}")
        print(f"    Est Duration: {res.duration_sec:.1f} seconds")
        print(f"    Script Path : {res.script_path}")
        return 0
    else:
        print(f"\n[!] Script generation failed: {res.error_message}", file=sys.stderr)
        return 1


def handle_render(args: argparse.Namespace) -> int:
    """Handles the render subcommand."""
    print(f"[*] Rendering script audio for: {args.script_file}")
    orchestrator = PodcastOrchestrator()
    res = orchestrator.render_existing_script(
        script_path=args.script_file,
        output_dir=args.output_dir,
        mock_mode=args.mock,
    )

    if res.status == "SUCCESS":
        print(f"\n[+] Audio rendering complete!")
        print(f"    Duration      : {res.duration_sec:.1f}s")
        print(f"    Mastered Audio: {res.mastered_audio_path}")
        return 0
    else:
        print(f"\n[!] Audio rendering failed: {res.error_message}", file=sys.stderr)
        return 1


def handle_inspect(args: argparse.Namespace) -> int:
    """Handles the inspect subcommand."""
    p = Path(args.path)
    if not p.exists():
        print(f"[!] Path not found: {p}", file=sys.stderr)
        return 1

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"=== [PODCAST INSPECT: {p.name}] ===")
    if "segments" in data:
        print(f"Type            : Podcast Screenplay Script")
        print(f"Title / ID      : {data.get('title', data.get('chapter_id', 'Unknown'))}")
        print(f"Total Segments  : {len(data['segments'])}")
        print(f"Total Words     : {data.get('total_words', 0)}")
        print(f"Est. Runtime    : {data.get('estimated_duration_sec', 0.0):.1f}s")
        if "cast" in data:
            print("Cast:")
            for c in data["cast"]:
                print(f"  • {c.get('display_name', c.get('character'))} ({c.get('voice', 'Default')} - {c.get('role')})")
    elif "status" in data and "mastered_audio_path" in data:
        print(f"Type            : Production Manifest")
        print(f"Podcast ID      : {data.get('podcast_id')}")
        print(f"Status          : {data.get('status')}")
        print(f"Mastered Audio  : {data.get('mastered_audio_path')}")
        print(f"Duration        : {data.get('duration_sec', 0.0):.1f}s")
        print(f"Integrated LUFS : {data.get('integrated_lufs', -19.0)} LUFS")
        print(f"True Peak       : {data.get('true_peak_db', -1.5)} dBTP")
    else:
        print(json.dumps(data, indent=2))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the podcast CLI."""
    parser = create_podcast_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 1

    handlers = {
        "produce": handle_produce,
        "script": handle_script,
        "render": handle_render,
        "inspect": handle_inspect,
    }

    try:
        return handlers[args.subcommand](args)
    except Exception as e:
        print(f"\n[!] CLI Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
