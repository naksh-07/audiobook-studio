#!/usr/bin/env python3
"""
Audiobook Factory - Command Line Interface (Vocals-Only Studio Engine).
Fast, reliable, multi-voice audiobook generation and EBU R128 mastering.
100% focused on vocal clarity, character attribution, and pristine M4B delivery.
"""

import os
import sys
import argparse
from pathlib import Path

# Configure UTF-8 for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

WORKSPACE_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = WORKSPACE_DIR / "audiobooks" / "projects"

from audiobook_factory.cli.commands.pipeline import (
    cmd_extract,
    cmd_research,
    cmd_translate,
    cmd_script,
    cmd_podcast,
    cmd_synthesize,
    cmd_master,
    cmd_produce,
    cmd_auto,
)
from audiobook_factory.cli.commands.audio import (
    cmd_package,
)
from audiobook_factory.cli.commands.audit import (
    cmd_audit_book,
    cmd_audit,
    cmd_doctor,
)
from audiobook_factory.cli.commands.keys import (
    cmd_keys,
)



__all__ = [
    "cmd_extract",
    "cmd_translate",
    "cmd_script",
    "cmd_podcast",
    "cmd_synthesize",
    "cmd_master",
    "cmd_produce",
    "cmd_auto",
    "cmd_package",
    "cmd_audit_book",
    "cmd_audit",
    "cmd_keys",
    "WORKSPACE_DIR",
    "PROJECTS_DIR",
]


def main():
    parser = argparse.ArgumentParser(
        prog="audiobook-factory",
        description="Vocals-Only Production Audiobook Factory (Extraction, Translation, Multi-Voice TTS, Mastering & M4B Packaging)",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Pipeline step to execute")

    # extract
    p_extract = subparsers.add_parser("extract", help="Extract and segment book file into clean Markdown chapters")
    p_extract.add_argument("file", help="Input book path (.epub, .pdf, .txt, .md)")
    p_extract.add_argument("--force-gate", action="store_true", help="Bypass Extraction Quality Gate REVIEW failure and force production")

    # research (Room 1 Pre-Production Studio & Novel Researcher)
    p_research = subparsers.add_parser("research", help="Run Room 1 Pre-Production Studio & Novel Researcher (Lore, Characters, Cast Lock)")
    p_research.add_argument("book", help="Project book slug (folder name)")
    p_research.add_argument("--force", action="store_true", help="Force overwrite of existing master state")
    p_research.add_argument("--model", default=None, help="LLM model override for pre-production (default: gemini-3.8-flash)")

    # translate
    p_translate = subparsers.add_parser("translate", help="Translate extracted chapters into literary Hindi")
    p_translate.add_argument("book", help="Project book slug (folder name)")
    p_translate.add_argument("--model", default="gemini-3.8-flash", help="Gemini translation model (default: gemini-3.8-flash)")
    p_translate.add_argument("--chapter", type=int, default=None, help="Specific chapter number to translate")
    p_translate.add_argument("--chapters", type=str, default=None, help="Comma-separated or range of chapters (e.g. 1-2 or 1,2)")
    p_translate.add_argument("--force-gate", action="store_true", help="Bypass translation quality gate REVIEW failure and force production")

    # script
    p_script = subparsers.add_parser("script", help="Generate screenplay script JSON with speaker tags")
    p_script.add_argument("book", help="Project book slug")
    p_script.add_argument("--hindi", action="store_true", help="Use translated Hindi chapters")
    p_script.add_argument("--dramatized", action="store_true", help="Multi-voice character attribution mode")
    p_script.add_argument("--adapter", choices=["audiobook", "podcast"], default="audiobook", help="Format script adapter: audiobook (default) or podcast")
    p_script.add_argument("--flow", action="store_true", default=True, help="Enable Audible Flow mode (preserves prose and tags, eliminates Foley)")
    p_script.add_argument("--cast-mode", choices=["ensemble", "solo"], default="ensemble", help="Cast mode: ensemble (multi-voice cast) or solo (master narrator)")
    p_script.add_argument("--chapter", type=int, default=None, help="Specific chapter number to script")
    p_script.add_argument("--chapters", type=str, default=None, help="Comma-separated or range of chapters (e.g. 1-2 or 1,2)")
    p_script.add_argument("--overwrite", action="store_true", help="Overwrite existing script files")

    # podcast
    p_podcast = subparsers.add_parser("podcast", help="Generate 2-Host conversational narrative podcast episodes or whitepaper audio")
    p_podcast.add_argument("target", help="Project book slug OR input research paper path (.pdf, .md, .txt)")
    p_podcast.add_argument("--hindi", action="store_true", help="Generate Hindi/Hindustani podcast (default)")
    p_podcast.add_argument("--english", action="store_true", help="Generate English podcast")
    p_podcast.add_argument("--produce", action="store_true", help="Synthesize and master podcast episode to -16.0 LUFS broadcast audio")
    p_podcast.add_argument("--chapter", type=int, default=None, help="Specific chapter number")
    p_podcast.add_argument("--chapters", type=str, default=None, help="Comma-separated or range of chapters (e.g. 1-2 or 1,2)")
    p_podcast.add_argument("--workers", default=3, type=int, help="Number of concurrent TTS synthesis workers (default: 3)")
    p_podcast.add_argument("--target-lufs", default=-16.0, type=float, help="Target broadcast integrated loudness (default: -16.0 LUFS)")
    p_podcast.add_argument("--overwrite", action="store_true", help="Overwrite existing podcast files")
    p_podcast.add_argument("--output-dir", default=None, help="Target project output directory")
    p_podcast.add_argument("--style", choices=["conversational_podcast", "formal_lecture", "narrative_audiobook"], default="conversational_podcast", help="Verbalization style")
    p_podcast.add_argument("--host-a-name", default="Dr. Vance", help="Lead explainer host name")
    p_podcast.add_argument("--host-a-voice", default="Charon", help="Lead explainer host voice")
    p_podcast.add_argument("--host-b-name", default="Maya", help="Inquisitive co-host name")
    p_podcast.add_argument("--host-b-voice", default="Aoede", help="Inquisitive co-host voice")
    p_podcast.add_argument("--mock", action="store_true", help="Run in mock/offline mode")
    p_podcast.add_argument("--script-only", action="store_true", help="Generate podcast_script.json only")
    p_podcast.add_argument("--force-gate", action="store_true", help="Force bypass of extraction quality gate review")

    # synthesize
    p_synth = subparsers.add_parser("synthesize", help="Synthesize audio segments via Gemini Cloud TTS")
    p_synth.add_argument("book", help="Project book slug")
    p_synth.add_argument("--chapter", type=int, default=None, help="Specific chapter number to synthesize")
    p_synth.add_argument("--chapters", type=str, default=None, help="Comma-separated or range of chapters (e.g. 1-2 or 1,2)")
    p_synth.add_argument("--backend", default="gemini_tts", choices=["gemini_tts"], help="TTS engine (default: gemini_tts)")
    p_synth.add_argument("--voice", default="Aoede", help="Default voice persona")

    # master
    p_master = subparsers.add_parser("master", help="Concatenate segments and master audio with EBU R128 (-19 LUFS)")
    p_master.add_argument("book", help="Project book slug")
    p_master.add_argument("--chapter", type=int, default=None, help="Specific chapter number to master")
    p_master.add_argument("--chapters", type=str, default=None, help="Comma-separated or range of chapters (e.g. 1-2 or 1,2)")

    # package
    p_pack = subparsers.add_parser("package", help="Assemble final chapterized container (Audiobook M4B or Podcast M4A)")
    p_pack.add_argument("book", help="Project book slug or path")
    p_pack.add_argument("--format", choices=["audiobook", "podcast", "both"], default="audiobook", help="Target delivery format: audiobook (default), podcast, or both")
    p_pack.add_argument("--cover", default=None, help="Cover art image path")
    p_pack.add_argument("--enforce-gate6", action="store_true", help="Abort packaging if any Gate 6 verification check fails")

    # audit-book
    p_audit_book = subparsers.add_parser("audit-book", help="Run Macro-Tier Gate 6 master audit across entire book project")
    p_audit_book.add_argument("project_dir", help="Project directory or book slug")

    # auto
    p_auto = subparsers.add_parser("auto", help="Run entire end-to-end vocals-only pipeline in one command")
    p_auto.add_argument("file", help="Input book path")
    p_auto.add_argument("--hindi", action="store_true", help="Translate English book to Hindi")
    p_auto.add_argument("--format", choices=["audiobook", "podcast", "both"], default="audiobook", help="Output format: audiobook (default), podcast, or both")
    p_auto.add_argument("--backend", default="gemini_tts", choices=["gemini_tts"], help="TTS engine (default: gemini_tts)")
    p_auto.add_argument("--voice", default="Aoede", help="Voice persona")
    p_auto.add_argument("--dramatized", action="store_true", help="Multi-voice dramatization")
    p_auto.add_argument("--flow", action="store_true", default=True, help="Enable Audible Flow mode (preserves prose and tags)")
    p_auto.add_argument("--cast-mode", choices=["ensemble", "solo"], default="ensemble", help="Cast mode: ensemble or solo")
    p_auto.add_argument("--cover", default=None, help="Cover art image path")
    p_auto.add_argument("--workers", default=3, type=int, help="Number of concurrent TTS synthesis workers (default: 3)")
    p_auto.add_argument("--force-gate", action="store_true", help="Bypass Extraction Quality Gate REVIEW failure and force production")
    p_auto.add_argument("--chapter", type=int, default=None, help="Specific chapter number to produce")
    p_auto.add_argument("--chapters", type=str, default=None, help="Comma-separated or range of chapters (e.g. 1-2 or 1,2)")

    # produce
    p_produce = subparsers.add_parser("produce", help="Produce mastered vocal chapters with EBU R128 (-19 LUFS) & timeline ledger")
    p_produce.add_argument("book", help="Project book slug")
    p_produce.add_argument("--chapter", type=int, default=None, help="Specific chapter number to produce")
    p_produce.add_argument("--all", action="store_true", help="Produce all chapters in sequence")
    p_produce.add_argument("--voice", default="Aoede", help="Lead voice persona")
    p_produce.add_argument("--workers", default=3, type=int, help="TTS synthesis workers")
    p_produce.add_argument("--clean-dsp", action="store_true", default=True, help="Clean studio vocal DSP without pitch shifting")

    # audit
    p_audit = subparsers.add_parser("audit", help="Run multi-gate verification audit on a chapter")
    p_audit.add_argument("book", help="Project book slug")
    p_audit.add_argument("--chapter", type=int, required=True, help="Chapter number to audit")

    # doctor
    p_doctor = subparsers.add_parser("doctor", help="Run zero-token Pre-Flight Metadata Doctor forensic audit")
    p_doctor.add_argument("book", help="Project book slug or path")

    # keys
    p_keys = subparsers.add_parser("keys", help="Inspect and audit API key inventory, leases, and quota fleet status")
    p_keys.add_argument("keys_action", nargs="?", default="status", choices=["status", "list", "add", "sweep", "test", "audit", "reset", "quarantine"], help="Action: status, list, add, sweep, test, audit, reset, quarantine (default: status)")
    p_keys.add_argument("quarantine_action", nargs="?", default="list", choices=["list", "inspect", "purge", "export", "restore"], help="Quarantine subaction (when keys_action=quarantine): list, inspect, purge, export, restore")
    p_keys.add_argument("--alias", default=None, help="Key alias for quarantine inspect/purge/restore")
    p_keys.add_argument("--out", default=None, help="Export output path (used with quarantine export)")
    p_keys.add_argument("--all", action="store_true", dest="purge_all", help="Purge all quarantined keys (used with quarantine purge)")
    p_keys.add_argument("--include-keys", action="store_true", dest="include_keys", help="Include raw keys in export")
    p_keys.add_argument("--provider", default="gemini", help="Provider filter (default: gemini)")
    p_keys.add_argument("--limit", type=int, default=25, help="Number of audit log records to display (default: 25)")
    p_keys.add_argument("--key", default=None, help="API key to register (used with 'add')")

    # tts (Modular Platform Core)
    p_tts = subparsers.add_parser("tts", help="Ad-hoc speech synthesis via modular TTS Platform Core")
    p_tts.add_argument("text", help="Text or prompt to synthesize")
    p_tts.add_argument("--voice", default="Puck", help="Voice identifier (default: Puck)")
    p_tts.add_argument("--model", default="gemini-3.8-flash", help="TTS model (default: gemini-3.8-flash)")
    p_tts.add_argument("--out", default="output.wav", help="Output WAV path (default: output.wav)")

    # dsp
    p_dsp = subparsers.add_parser("dsp", help="Apply C++ JUCE parametric vocal EQ, compression, and True-Peak limiter")
    p_dsp.add_argument("--input", "-i", required=True, help="Input WAV audio file")
    p_dsp.add_argument("--output", "-o", required=True, help="Output mastered WAV audio file")
    p_dsp.add_argument("--target-lufs", type=float, default=-19.0, help="Target LUFS (default: -19.0)")
    p_dsp.add_argument("--true-peak", type=float, default=-1.5, help="True Peak ceiling in dBTP (default: -1.5)")

    # qa-audit
    p_qa = subparsers.add_parser("qa-audit", help="Forensic speech QA audit (VAD, speaking rate bounds, dropouts, loops, MOS)")
    p_qa.add_argument("--input", "-i", required=True, help="Input WAV audio file")
    p_qa.add_argument("--text", "-t", default="", help="Expected spoken text")
    p_qa.add_argument("--speaker", "-s", default="Narrator", help="Speaker name")

    # enhance
    p_enh = subparsers.add_parser("enhance", help="Apply DeepFilterNet3 neural speech de-artifacting with auto-bypass")
    p_enh.add_argument("--input", "-i", required=True, help="Input WAV audio file")
    p_enh.add_argument("--output", "-o", required=True, help="Output enhanced WAV file")

    # match-ref
    p_mr = subparsers.add_parser("match-ref", help="Match target frequency spectrum to reference golden master (clamped +/-3dB)")
    p_mr.add_argument("--target", "-t", required=True, help="Target WAV audio file")
    p_mr.add_argument("--reference", "-r", required=True, help="Golden reference WAV master")
    p_mr.add_argument("--output", "-o", required=True, help="Output matched WAV file")
    p_mr.add_argument("--max-clamp", type=float, default=3.0, help="Maximum spectral correction in dB (default: 3.0)")

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    from audiobook_factory.cli.commands.audio import (
        cmd_dsp,
        cmd_qa_audit,
        cmd_enhance,
        cmd_match_ref,
    )

    def _handle_podcast(a):
        target_path = Path(a.target)
        if target_path.exists() and target_path.is_file():
            from audiobook_factory.podcast.orchestrator import process_document_to_podcast
            res = process_document_to_podcast(
                source_file=target_path,
                output_dir=a.output_dir,
                style=a.style,
                host_a_name=a.host_a_name,
                host_a_voice=a.host_a_voice,
                host_b_name=a.host_b_name,
                host_b_voice=a.host_b_voice,
                script_only=a.script_only,
                mock_mode=a.mock,
                force_gate=a.force_gate,
            )
            if res.status != "SUCCESS":
                print(f"\n[!] Podcast production failed: {res.error_message}", file=sys.stderr)
                sys.exit(1)
        else:
            a.book = a.target
            cmd_podcast(a)

    def _handle_tts(a):
        from audiobook_factory import GenericTTSClient
        client = GenericTTSClient(model=a.model, default_voice=a.voice)
        print(f"[*] Synthesizing speech via GenericTTSClient ({a.model}, voice: {a.voice})...")
        out_path = Path(a.out)
        res = client.speak(text=a.text, output_path=out_path, voice=a.voice)
        print(f"[+] Audio successfully synthesized: {res} ({out_path.stat().st_size} bytes)")

    cmds = {
        "extract": cmd_extract,
        "research": cmd_research,
        "translate": cmd_translate,
        "script": cmd_script,
        "podcast": _handle_podcast,
        "synthesize": cmd_synthesize,
        "master": cmd_master,
        "package": cmd_package,
        "produce": cmd_produce,
        "auto": cmd_auto,
        "audit": cmd_audit,
        "audit-book": cmd_audit_book,
        "doctor": cmd_doctor,
        "keys": cmd_keys,
        "tts": _handle_tts,
        "dsp": cmd_dsp,
        "qa-audit": cmd_qa_audit,
        "enhance": cmd_enhance,
        "match-ref": cmd_match_ref,
    }

    try:
        cmds[args.subcommand](args)
    except KeyboardInterrupt:
        print("\n\n[!] Production aborted by user (Ctrl+C). Checkpoints safely preserved on disk.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n[!] Pipeline Error: {e}", file=sys.stderr)
        if os.environ.get("DEBUG"):
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
