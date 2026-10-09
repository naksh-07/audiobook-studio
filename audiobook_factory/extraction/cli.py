#!/usr/bin/env python3
"""
Audiobook Studio - Pillar 1: Standalone Extraction CLI.
Command-line interface for forensic document extraction, AST auditing, and inspection.
Usage:
  python -m audiobook_factory.extraction.cli extract <book_file> [--out <dir>] [--book-id <slug>] [--force-gate] [--json]
  python -m audiobook_factory.extraction.cli audit <canonical_dir> [--force-gate] [--json]
  python -m audiobook_factory.extraction.cli inspect <target> [--json]
"""

from __future__ import annotations
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List

from audiobook_factory.extraction.contracts import (
    CanonicalBook,
    ExtractionQualityReport,
    ExtractionGateAuditError,
)
from audiobook_factory.extraction.engine import ExtractionEngine, process_book_file
from audiobook_factory.extraction.quality_gate import ExtractionQualityAuditor


def cmd_extract(args: argparse.Namespace) -> int:
    """Handles the 'extract' subcommand."""
    source_path = Path(args.source).resolve()
    if not source_path.exists():
        print(f"[ERROR] Source file not found: {source_path}", file=sys.stderr)
        return 1

    out_dir = Path(args.out).resolve()
    try:
        canonical_book = ExtractionEngine.extract(
            input_file=source_path,
            output_base_dir=out_dir,
            force_gate=args.force_gate,
            book_id=args.book_id,
            quiet=args.json,
        )
    except ExtractionGateAuditError as gate_err:
        print(f"\n[FAIL-CLOSED GATE HALT]\n{gate_err}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[ERROR] Extraction failed: {exc}", file=sys.stderr)
        return 1

    metadata = canonical_book.to_legacy_metadata()
    if args.json:
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
    else:
        print("\n" + "=" * 65)
        print(f"  EXTRACTION SUCCESSFUL: {canonical_book.title}")
        print("=" * 65)
        print(f"Book ID             : {canonical_book.book_id}")
        print(f"Source Format       : {canonical_book.source_type.upper()}")
        print(f"Total Chapters/Units: {len(canonical_book.chapters)}")
        print(f"Literary Chapters   : {len(canonical_book.get_literary_chapters())}")
        print(f"Production Chunks   : {len(canonical_book.get_production_chunks())}")
        print(f"Total Words         : {canonical_book.quality_report.total_words:,}")
        print(f"Gate 0.1 Status     : {canonical_book.quality_report.gate_status}")
        print(f"Output Directory    : {out_dir / canonical_book.book_id}")
        print("=" * 65)
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Handles the 'audit' subcommand."""
    canon_dir = Path(args.canonical_dir).resolve()
    if canon_dir.is_file() and canon_dir.name == "book.json":
        canon_dir = canon_dir.parent

    if not canon_dir.exists():
        print(f"[ERROR] Canonical directory not found: {canon_dir}", file=sys.stderr)
        return 1

    try:
        book = CanonicalBook.load_canonical(canon_dir)
    except Exception as exc:
        print(f"[ERROR] Failed to load canonical AST from {canon_dir}: {exc}", file=sys.stderr)
        return 1

    try:
        report = ExtractionQualityAuditor.audit(book, force_gate=args.force_gate)
    except ExtractionGateAuditError as gate_err:
        print(f"\n[GATE AUDIT HALT]\n{gate_err}", file=sys.stderr)
        return 2

    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print("\n" + "=" * 65)
        print(f"  EXTRACTION QUALITY GATE 0.1 AUDIT: {report.gate_status}")
        print("=" * 65)
        print(f"Book ID            : {book.book_id}")
        print(f"Gate Status        : {report.gate_status}")
        print(f"Overall Confidence : {report.overall_confidence}")
        print(f"Total Chapters     : {report.total_chapters}")
        print(f"Total Words        : {report.total_words:,}")
        print(f"Suspicious Pages   : {len(report.suspicious_pages)}")
        print(f"Warnings Count     : {len(report.warnings)}")
        print(f"Errors Count       : {len(report.errors)}")
        print("=" * 65)
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Handles the 'inspect' subcommand."""
    target_path = Path(args.target).resolve()
    canon_dir = target_path
    if target_path.is_file():
        canon_dir = target_path.parent
    elif (target_path / "canonical").exists():
        canon_dir = target_path / "canonical"

    try:
        book = CanonicalBook.load_canonical(canon_dir)
    except Exception as exc:
        print(f"[ERROR] Failed to load book from {canon_dir}: {exc}", file=sys.stderr)
        return 1

    lit_chaps = book.get_literary_chapters()
    prod_chunks = book.get_production_chunks()

    inspect_data = {
        "book_id": book.book_id,
        "title": book.title,
        "author": book.author,
        "source_type": book.source_type,
        "total_units": len(book.chapters),
        "literary_chapters_count": len(lit_chaps),
        "production_chunks_count": len(prod_chunks),
        "total_words": book.quality_report.total_words,
        "total_blocks": book.quality_report.total_blocks,
        "gate_status": book.quality_report.gate_status,
        "chapters": [
            {
                "number": c.number,
                "title": c.title,
                "words": c.words,
                "unit_type": c.unit_type,
                "is_literary": c.is_literary_chapter,
                "blocks_count": len(c.blocks),
            }
            for c in book.chapters
        ],
    }

    if args.json:
        print(json.dumps(inspect_data, indent=2, ensure_ascii=False))
    else:
        print("\n" + "=" * 70)
        print(f"  CANONICAL BOOK INSPECTOR: {book.title} (ID: {book.book_id})")
        print("=" * 70)
        print(f"Author             : {book.author}")
        print(f"Source Format      : {book.source_type.upper()}")
        print(f"Total Output Units : {len(book.chapters)}")
        print(f"Literary Chapters  : {len(lit_chaps)}")
        print(f"Production Chunks  : {len(prod_chunks)}")
        print(f"Total Words        : {book.quality_report.total_words:,}")
        print(f"Total Blocks       : {book.quality_report.total_blocks:,}")
        print(f"Gate 0.1 Status    : {book.quality_report.gate_status}")
        print("\nChapters:")
        for c in book.chapters[:20]:
            kind = "[LIT]" if c.is_literary_chapter else "[PROD]"
            print(f"  {c.number:02d}. {kind:6s} {c.title:<40s} ({c.words:,} words, {len(c.blocks)} blocks)")
        if len(book.chapters) > 20:
            print(f"  ... and {len(book.chapters) - 20} more chapters.")
        print("=" * 70)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Builds the argument parser for extraction CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m audiobook_factory.extraction.cli",
        description="Audiobook Studio - Pillar 1: Standalone Forensic Document Extraction CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. extract
    p_extract = subparsers.add_parser("extract", help="Ingest a book file into canonical AST and legacy markdown")
    p_extract.add_argument("source", help="Path to book file (.epub, .pdf, .txt, .md)")
    p_extract.add_argument("--out", "-o", default="projects", help="Base output directory (default: projects)")
    p_extract.add_argument("--book-id", help="Custom unique book ID/slug")
    p_extract.add_argument("--force-gate", action="store_true", help="Bypass Gate 0.1 fail-closed check on REVIEW")
    p_extract.add_argument("--json", action="store_true", help="Output metadata manifest as JSON")

    # 2. audit
    p_audit = subparsers.add_parser("audit", help="Run Gate 0.1 quality audit on serialized canonical book")
    p_audit.add_argument("canonical_dir", help="Path to canonical directory containing book.json")
    p_audit.add_argument("--force-gate", action="store_true", help="Bypass fail-closed gate error")
    p_audit.add_argument("--json", action="store_true", help="Output audit report as JSON")

    # 3. inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect canonical book AST details and chapter metrics")
    p_inspect.add_argument("target", help="Path to book.json or canonical directory")
    p_inspect.add_argument("--json", action="store_true", help="Output inspection data as JSON")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "extract":
        return cmd_extract(args)
    elif args.command == "audit":
        return cmd_audit(args)
    elif args.command == "inspect":
        return cmd_inspect(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
