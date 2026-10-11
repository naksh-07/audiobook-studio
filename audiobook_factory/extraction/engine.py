#!/usr/bin/env python3
"""
Audiobook Studio - Pillar 1: Universal Document Extractor & Extraction Engine.
Coordinates forensic ingestion across EPUB, PDF, TXT, and Markdown files:
- Canonical Book Model & Block-level Provenance (contracts.py)
- Non-destructive Literary Normalizer (normalizer.py)
- Chapter Segmenter & Meso-tier Semantic Splitter (segmenter.py)
- Specialized Parsers (parsers/epub.py, parsers/pdf/, parsers/text.py)
- Independent Extraction Quality Gate 0.1 (quality_gate.py)
"""

from __future__ import annotations
import os
import re
import json
import html
import shutil
import zipfile
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from audiobook_factory.extraction.contracts import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalBlock,
    SourceProvenance,
    ExtractionQualityReport,
    ExtractionGateAuditError,
)
from audiobook_factory.extraction.normalizer import clean_book_text, normalize_block_text
from audiobook_factory.extraction.segmenter import (
    segment_chapters_from_text,
    split_large_chapter_on_semantic_boundary,
)
from audiobook_factory.extraction.quality_gate import ExtractionQualityAuditor
from audiobook_factory.extraction.parsers.epub import ForensicEPUBParser, extract_epub
from audiobook_factory.extraction.parsers.text import PlainTextParser, MarkdownParser
from audiobook_factory.extraction.parsers.pdf import (
    ForensicPDFEngine,
    GeminiVisionPDFExtractor,
    PDFQualityAnalyzer,
    PageQualityAudit,
)


def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 hash of a file for integrity provenance."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class ExtractionEngine:
    """
    Core coordinating engine for document ingestion and AST generation.
    Stateless, format-agnostic, and encapsulated.
    """

    @classmethod
    def extract(
        cls,
        input_file: Path,
        output_base_dir: Path,
        force_gate: bool = False,
        book_id: Optional[str] = None,
        quiet: bool = False,
    ) -> CanonicalBook:
        """
        Ingests a book document, verifies Gate 0.1, writes canonical representations,
        and projects legacy markdown artifacts.
        Returns: CanonicalBook instance.
        """
        t_start = time.time()
        input_file = Path(input_file).resolve()
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        output_base_dir = Path(output_base_dir).resolve()
        ext = input_file.suffix.lower()
        if book_id:
            raw_slug = str(book_id).lower()
        else:
            clean_stem = re.sub(r"\[.*?\]|\(.*?\)", "", input_file.stem).strip()
            raw_slug = (clean_stem or input_file.stem).lower()

        book_slug = re.sub(r"[^\w\-]", "_", raw_slug).strip("_")
        book_slug = re.sub(r"_+", "_", book_slug)
        if not book_slug:
            book_slug = "book"
        project_dir = output_base_dir / book_slug
        raw_dir = project_dir / "raw"
        canonical_dir = project_dir / "canonical"
        extracted_dir = project_dir / "extracted"

        raw_dir.mkdir(parents=True, exist_ok=True)
        canonical_dir.mkdir(parents=True, exist_ok=True)
        extracted_dir.mkdir(parents=True, exist_ok=True)

        file_size_bytes = input_file.stat().st_size
        file_sha256 = compute_sha256(input_file)
        ext = input_file.suffix.lower()

        if not quiet:
            print(f"[*] Ingesting book: '{input_file.name}' (Format: {ext.upper()}, Size: {file_size_bytes / (1024*1024):.2f} MB)...")

        # 1. Preserve Raw Source
        raw_copy_path = raw_dir / f"source_original{ext}"
        raw_copied = False
        if not raw_copy_path.exists():
            try:
                shutil.copy2(input_file, raw_copy_path)
                raw_copied = True
            except Exception as copy_err:
                print(f"[!] WARNING: Failed to archive raw source to '{raw_copy_path}': {copy_err}")
        else:
            raw_copied = True

        source_manifest = {
            "book_id": book_slug,
            "original_path": str(input_file),
            "source_format": ext.lstrip("."),
            "file_size_bytes": file_size_bytes,
            "sha256": file_sha256,
            "archived_copy": str(raw_copy_path) if raw_copied else None,
            "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with open(raw_dir / "source_manifest.json", "w", encoding="utf-8") as f:
            json.dump(source_manifest, f, indent=2)

        # 2. Extract Document based on format with crash boundary
        try:
            canonical_book: Optional[CanonicalBook] = None

            if ext == ".epub":
                parser = ForensicEPUBParser(input_file)
                canonical_book, _ = parser.parse()

            elif ext == ".pdf":
                pdf_engine = ForensicPDFEngine(input_file)
                cleaned_pages, page_audits, escalated_pages = pdf_engine.extract_pages()
                canonical_chapters = pdf_engine.segment_into_canonical_chapters(
                    cleaned_pages,
                    page_audits,
                    escalated_pages=escalated_pages,
                    max_words=12000,
                )

                suspicious_nums = [a.page_number for a in page_audits if a.is_suspicious]
                page_warnings: List[str] = []
                for a in page_audits:
                    for w in a.warnings:
                        msg = f"Page {a.page_number}: {w}"
                        if msg not in page_warnings:
                            page_warnings.append(msg)

                report = ExtractionQualityReport(
                    source_type="pdf",
                    source_path=str(input_file),
                    extraction_engine="pdf_layout_selective",
                    total_pages_or_docs=len(page_audits),
                    total_words=sum(c.words for c in canonical_chapters),
                    total_chapters=len(canonical_chapters),
                    total_blocks=sum(len(c.blocks) for c in canonical_chapters),
                    suspicious_pages=suspicious_nums,
                    fallback_pages=escalated_pages,
                    fallback_used=len(escalated_pages) > 0,
                    warnings=page_warnings,
                )

                canonical_book = CanonicalBook(
                    book_id=book_slug,
                    title=input_file.stem.replace("_", " ").title(),
                    source_type="pdf",
                    source_path=str(input_file),
                    extraction_engine="pdf_layout_selective",
                    quality_report=report,
                    chapters=canonical_chapters,
                )

            elif ext in (".txt", ".md"):
                text_parser = PlainTextParser(input_file, source_type=ext.lstrip("."))
                canonical_book = text_parser.parse()

            else:
                raise ValueError(f"Unsupported file format: {ext}")

            if canonical_book:
                canonical_book.book_id = book_slug

            canonical_book.quality_report.duration_sec = round(time.time() - t_start, 2)

            # 3. Independent Quality Gate Audit (Fail-Closed on REVIEW unless force_gate is True)
            ExtractionQualityAuditor.audit(canonical_book, force_gate=force_gate)

            # 4. Save Canonical Representations
            canonical_book.save_canonical(canonical_dir)

            # 5. Project Legacy Markdown Output (extracted/chapter_XXX.md)
            canonical_book.project_legacy_extracted(extracted_dir)

            # 6. Generate and Save Legacy Project Metadata
            legacy_metadata = canonical_book.to_legacy_metadata()
            with open(project_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(legacy_metadata, f, indent=2, ensure_ascii=False)

            total_words = legacy_metadata["total_words"]
            total_chapters = legacy_metadata["total_chapters"]
            est_hours = legacy_metadata["estimated_total_hours"]
            gate = canonical_book.quality_report.gate_status
            if not quiet:
                print(f"[+] Ingestion complete: {total_chapters} chapters ({total_words} words, ~{est_hours} hrs) [Gate: {gate}] -> {project_dir}")
            return canonical_book

        except Exception as parse_err:
            error_manifest = {
                "status": "EXTRACTION_FAILED",
                "error_type": type(parse_err).__name__,
                "error_message": str(parse_err),
                "book_id": book_slug,
                "source_file": str(input_file),
                "failed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            try:
                with open(project_dir / "extraction_error.json", "w", encoding="utf-8") as ef:
                    json.dump(error_manifest, ef, indent=2)
            except Exception:
                pass
            raise


def process_book_file(
    input_file: Path,
    output_base_dir: Path,
    force_gate: bool = False,
    book_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Standard function wrapper maintaining 100% backward compatibility with existing callers.
    Delegates to ExtractionEngine.extract() and returns the legacy metadata dictionary.
    """
    canonical_book = ExtractionEngine.extract(
        input_file=input_file,
        output_base_dir=output_base_dir,
        force_gate=force_gate,
        book_id=book_id,
    )
    return canonical_book.to_legacy_metadata()


def extract_gemini_pdf(file_path: Path, api_key: str | None = None) -> str:
    """
    Extract clean structured Markdown from PDF using local pypdf parser with selective Gemini fallback.
    Maintains 100% backward compatibility with legacy API.
    """
    file_path = Path(file_path).resolve()
    engine = ForensicPDFEngine(
        file_path=file_path,
        escalation_engine=GeminiVisionPDFExtractor(api_key=api_key),
    )
    pages, _, _ = engine.extract_pages()
    full_text = "\n\n".join(p for p in pages if p.strip())
    return clean_book_text(full_text)


def extract_chapters(source: str | Path) -> List[Dict[str, Any]]:
    """
    Universal chapter extractor: accepts file path or raw text string.
    Enforces Meso-Tier 12,000 word ceiling by splitting oversized chapters on semantic boundaries.
    """
    raw_chapters: List[Dict[str, Any]] = []

    is_file = False
    if isinstance(source, Path):
        is_file = source.is_file()
    elif isinstance(source, str) and len(source) < 300 and ("\n" not in source):
        try:
            is_file = Path(source).is_file()
        except Exception:
            is_file = False

    if is_file:
        source_path = Path(source).resolve()
        ext = source_path.suffix.lower()
        if ext == ".epub":
            _, epub_chapters = extract_epub(source_path)
            for idx, item in enumerate(epub_chapters, 1):
                if isinstance(item, dict):
                    raw_chapters.append(item)
                else:
                    sub = segment_chapters_from_text(item)
                    if sub:
                        raw_chapters.extend(sub)
                    else:
                        raw_chapters.append({
                            "title": f"Production Chunk {idx}",
                            "content": item,
                            "words": len(item.split()),
                            "unit_type": "production_chunk",
                            "is_literary_chapter": False,
                            "is_production_chunk": True,
                            "boundary_origin": "spine_fallback",
                            "literary_chapter_number": None,
                            "parent_chapter_title": None,
                            "chunk_index": idx,
                            "total_chunks": 1,
                        })
        elif ext in (".txt", ".md"):
            with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = clean_book_text(f.read())
            raw_chapters = segment_chapters_from_text(raw_text)
        elif ext == ".pdf":
            pdf_engine = ForensicPDFEngine(source_path)
            cleaned_pages, page_audits, escalated_pages = pdf_engine.extract_pages()
            canon_chaps = pdf_engine.segment_into_canonical_chapters(
                cleaned_pages, page_audits, escalated_pages=escalated_pages, max_words=12000
            )
            guarded_pdf_chapters: List[Dict[str, Any]] = []
            for c in canon_chaps:
                guarded_pdf_chapters.append({
                    "title": c.title,
                    "content": c.to_plain_text(),
                    "words": c.words,
                    "unit_type": c.unit_type,
                    "is_literary_chapter": c.is_literary_chapter,
                    "is_production_chunk": c.is_production_chunk,
                    "boundary_origin": c.boundary_origin,
                    "literary_chapter_number": c.literary_chapter_number,
                    "parent_chapter_id": c.parent_chapter_id,
                    "parent_chapter_title": c.parent_chapter_title,
                    "chunk_index": c.chunk_index,
                    "total_chunks": c.total_chunks_in_chapter,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "source_location": c.source_location,
                })
            return guarded_pdf_chapters
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    else:
        raw_text = clean_book_text(str(source))
        raw_chapters = segment_chapters_from_text(raw_text)

    # Meso-Tier 12,000 word guard
    guarded_chapters: List[Dict[str, Any]] = []
    for chap in raw_chapters:
        title = chap.get("title", "Chapter")
        content = chap.get("content", "")
        words = chap.get("words", len(content.split()))
        is_lit = bool(chap.get("is_literary_chapter", True))
        b_origin = str(chap.get("boundary_origin", "detected_heading"))
        lit_num = chap.get("literary_chapter_number")
        c_start = int(chap.get("char_start", 0))

        if words > 12000:
            split_parts = split_large_chapter_on_semantic_boundary(
                title,
                content,
                max_words=12000,
                base_char_start=c_start,
                is_literary_chapter=is_lit,
                boundary_origin=b_origin,
                literary_chapter_number=lit_num,
            )
            guarded_chapters.extend(split_parts)
        else:
            guarded_chapters.append({
                **chap,
                "title": title,
                "content": content,
                "words": words,
                "unit_type": chap.get("unit_type", "literary_chapter" if is_lit else "production_chunk"),
                "is_literary_chapter": is_lit,
                "is_production_chunk": bool(chap.get("is_production_chunk", not is_lit)),
                "boundary_origin": b_origin,
                "literary_chapter_number": lit_num,
                "chunk_index": chap.get("chunk_index", 1),
                "total_chunks": chap.get("total_chunks", 1),
            })

    return guarded_chapters
