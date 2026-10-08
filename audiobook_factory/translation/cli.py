"""
Audiobook Factory - Standalone Translation CLI
==============================================
Command line utility for running the decoupled literary translation engine
without needing any audio, TTS, or screenplay studio dependencies.

Usage Examples:
    # Translate a chapter or book file
    python -m audiobook_factory.translation.cli translate chapter.txt -o chapter_hi.md --tier RAW_UNRATED

    # Verify parity between English source and Hindi translation
    python -m audiobook_factory.translation.cli parity chapter.txt chapter_hi.md
"""

import argparse
import json
import sys
from pathlib import Path

from .contracts import FidelityTier, TranslationRequest
from .engine import TranslationEngine
from .parity_gate import DeterministicParityGate


def main():
    parser = argparse.ArgumentParser(
        prog="python -m audiobook_factory.translation.cli",
        description="Standalone Decoupled Literary Translation Engine (Option D Architecture)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: translate
    trans_parser = subparsers.add_parser("translate", help="Translate source document into literary Hindustani")
    trans_parser.add_argument("input_file", type=Path, help="Path to input text or markdown file")
    trans_parser.add_argument("-o", "--output", type=Path, required=True, help="Path to output translated markdown file")
    trans_parser.add_argument(
        "--tier",
        type=str,
        default="RAW_UNRATED",
        choices=["RAW_UNRATED", "CLASSIC_REVERENT"],
        help="Stylistic fidelity tier (default: RAW_UNRATED)",
    )
    trans_parser.add_argument(
        "--glossary",
        type=Path,
        default=None,
        help="Optional path to JSON glossary file (en -> hi mapping)",
    )
    trans_parser.add_argument(
        "--budget",
        type=int,
        default=1024,
        help="Gemini Flash thinking budget in tokens (default: 1024)",
    )

    # Subcommand: parity
    parity_parser = subparsers.add_parser("parity", help="Run deterministic parity audit on existing translation")
    parity_parser.add_argument("source_file", type=Path, help="Path to original English source file")
    parity_parser.add_argument("translation_file", type=Path, help="Path to translated Hindi markdown file")

    args = parser.parse_args()

    if args.command == "translate":
        run_translate(args)
    elif args.command == "parity":
        run_parity(args)


def run_translate(args):
    if not args.input_file.exists():
        print(f"Error: Input file '{args.input_file}' not found.", file=sys.stderr)
        sys.exit(1)

    source_text = args.input_file.read_text(encoding="utf-8")
    tier = FidelityTier(args.tier)

    glossary = {}
    if args.glossary and args.glossary.exists():
        try:
            glossary = json.loads(args.glossary.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: Failed to load glossary '{args.glossary}': {e}", file=sys.stderr)

    req = TranslationRequest(
        source_text=source_text,
        source_title=args.input_file.stem,
        tier=tier,
        dynamic_glossary=glossary,
        thinking_budget=args.budget,
    )

    print(f"[*] Commencing translation for '{args.input_file.name}' ({len(source_text.split())} words)...")
    print(f"    Tier: {tier.value} | Thinking Budget: {args.budget} tokens")

    engine = TranslationEngine()
    result = engine.translate(req)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result.translated_markdown, encoding="utf-8")

    print(f"[+] Translation successfully saved to: {args.output}")
    print(f"    Total Chunks: {result.total_chunks} | LLM Calls: {result.llm_calls_made} | Time: {result.elapsed_seconds}s")
    print(f"    Length Ratio: {result.parity.length_ratio:.2f} (Source words: {result.parity.source_word_count}, Target: {result.parity.target_word_count})")
    print(f"    Paragraph Parity: {result.parity.paragraph_parity_ratio:.2f} (Source: {result.parity.source_paragraph_count}, Target: {result.parity.target_paragraph_count})")
    print(f"    Dialogue Quotes: {result.parity.quote_parity_ratio:.2f} (Source: {result.parity.source_quote_count}, Target: {result.parity.target_quote_count})")
    print(f"    Parity Gate Passed: {'YES' if result.parity.passed_all_gates else 'NO'}")

    if not result.parity.passed_all_gates:
        print("    [!] Parity Warnings:", file=sys.stderr)
        for reason in result.parity.rejection_reasons:
            print(f"        - {reason}", file=sys.stderr)


def run_parity(args):
    if not args.source_file.exists() or not args.translation_file.exists():
        print("Error: Source or translation file not found.", file=sys.stderr)
        sys.exit(1)

    src_text = args.source_file.read_text(encoding="utf-8")
    tgt_text = args.translation_file.read_text(encoding="utf-8")

    gate = DeterministicParityGate()
    metrics = gate.verify(src_text, tgt_text)

    print(f"[*] Full-Text Parity Audit for '{args.translation_file.name}' against '{args.source_file.name}':")
    print(f"    Length Ratio: {metrics.length_ratio:.2f} (src: {metrics.source_word_count}, tgt: {metrics.target_word_count})")
    print(f"    Paragraph Parity: {metrics.paragraph_parity_ratio:.2f} (src: {metrics.source_paragraph_count}, tgt: {metrics.target_paragraph_count})")
    print(f"    Quote Parity: {metrics.quote_parity_ratio:.2f} (src: {metrics.source_quote_count}, tgt: {metrics.target_quote_count})")
    print(f"    Negations: src: {metrics.source_negations_count}, tgt: {metrics.target_negations_count}")
    print(f"    Verdict: {'PASS' if metrics.passed_all_gates else 'FAIL'}")

    if not metrics.passed_all_gates:
        print("    Rejection Reasons:")
        for r in metrics.rejection_reasons:
            print(f"      - {r}")
        sys.exit(2)


if __name__ == "__main__":
    main()
