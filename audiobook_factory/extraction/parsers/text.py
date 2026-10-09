#!/usr/bin/env python3
"""
Audiobook Studio - Pillar 1: Plain Text & Markdown Forensic Parser.
Extracts clean, structured canonical representations, provenance, and chapter ASTs
from plain text (.txt) and Markdown (.md) documents.
Features:
- Character-accurate and line-offset provenance tracking.
- Non-destructive normalization with sacred raw_text preservation.
- Chapter segmentation and meso-tier semantic splitting (> 12,000 words).
- Generates CanonicalBook and ExtractionQualityReport.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from audiobook_factory.extraction.contracts import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalBlock,
    SourceProvenance,
    ExtractionQualityReport,
)
from audiobook_factory.extraction.normalizer import normalize_block_text
from audiobook_factory.extraction.segmenter import (
    segment_chapters_from_text,
    split_large_chapter_on_semantic_boundary,
)


class PlainTextParser:
    """
    Forensic parser for plain text and Markdown documents.
    """

    def __init__(self, file_path: Path, source_type: Optional[str] = None):
        self.file_path = Path(file_path).resolve()
        self.source_type = source_type or self.file_path.suffix.lstrip(".").lower() or "txt"
        if not self.file_path.exists():
            raise FileNotFoundError(f"Source file not found: {self.file_path}")

    def parse(self, raw_text: Optional[str] = None) -> CanonicalBook:
        """
        Parses text content into a CanonicalBook with full block-level provenance.
        """
        if raw_text is None:
            raw_text = self.file_path.read_text(encoding="utf-8", errors="replace")

        # Normalize CRLF line endings for consistent character coordinate indexing
        raw_doc = raw_text.replace("\r\n", "\n").replace("\r", "\n")

        # Build line-offset lookup table for accurate line_start/line_end provenance
        line_offsets: List[Tuple[int, int, int]] = []
        ln_cursor = 0
        for ln_num, ln_str in enumerate(raw_doc.splitlines(keepends=True), 1):
            line_offsets.append((ln_cursor, ln_cursor + len(ln_str.rstrip("\n")), ln_num))
            ln_cursor += len(ln_str)

        chap_dicts = segment_chapters_from_text(raw_doc)
        canonical_chapters: List[CanonicalChapter] = []
        global_reading_order = 0

        for idx, cd in enumerate(chap_dicts, 1):
            title = cd.get("title", f"Chapter {idx}")
            content = cd.get("content", "")
            words = cd.get("words", len(content.split()))
            c_char_start = int(cd.get("char_start", 0))
            is_lit = bool(cd.get("is_literary_chapter", True))
            b_origin = str(cd.get("boundary_origin", "detected_heading"))
            lit_num = cd.get("literary_chapter_number")
            parent_id = f"lit-ch-{lit_num:03d}" if lit_num is not None else None

            if words > 12000:
                splits = split_large_chapter_on_semantic_boundary(
                    title,
                    content,
                    max_words=12000,
                    base_char_start=c_char_start,
                    is_literary_chapter=is_lit,
                    boundary_origin=b_origin,
                    literary_chapter_number=lit_num,
                    parent_chapter_id=parent_id,
                )
            else:
                splits = [{
                    **cd,
                    "title": title,
                    "content": content,
                    "words": words,
                    "char_start": c_char_start,
                    "char_end": int(cd.get("char_end", c_char_start + len(content))),
                    "parent_chapter_id": parent_id,
                }]

            for part in splits:
                p_title = part["title"]
                p_content = part["content"]
                p_words = part["words"]
                p_char_start = int(part.get("char_start", c_char_start))
                p_unit_type = part.get("unit_type", "literary_chapter" if is_lit else "production_chunk")
                p_is_lit = bool(part.get("is_literary_chapter", is_lit))
                p_is_prod = bool(part.get("is_production_chunk", not p_is_lit))
                p_origin = part.get("boundary_origin", b_origin)
                p_lit_num = part.get("literary_chapter_number", lit_num)
                p_parent_id = part.get("parent_chapter_id", parent_id)
                p_parent_title = part.get("parent_chapter_title", title if is_lit else None)
                p_chunk_idx = part.get("chunk_index", 1)
                p_total_chunks = part.get("total_chunks", 1)

                blocks: List[CanonicalBlock] = []
                p_block_idx = 0
                for match in re.finditer(r"(?:[^\n]+(?:\n(?!\n)[^\n]*)*)", p_content):
                    raw_para = match.group(0)
                    lstrip_len = len(raw_para) - len(raw_para.lstrip())
                    para_clean = raw_para.strip()
                    if not para_clean:
                        continue

                    norm_para, norm_warnings = normalize_block_text(para_clean)
                    if not norm_para:
                        continue

                    p_block_idx += 1
                    global_reading_order += 1
                    block_doc_start = p_char_start + match.start() + lstrip_len
                    block_doc_end = block_doc_start + len(para_clean)

                    matching_lines = [
                        ln_num
                        for l_s, l_e, ln_num in line_offsets
                        if l_e >= block_doc_start and l_s <= block_doc_end
                    ]
                    l_start = matching_lines[0] if matching_lines else 1
                    l_end = matching_lines[-1] if matching_lines else l_start

                    b_type = "scene_break" if re.match(r"^(\*|\-|\_)\s*\1\s*\1+$", para_clean) else "paragraph"
                    prov = SourceProvenance(
                        source_file=str(self.file_path),
                        source_type=self.source_type,
                        line_start=l_start,
                        line_end=l_end,
                        reading_order=global_reading_order,
                        char_offset=block_doc_start,
                        extraction_method="text_parser",
                    )
                    meta: Dict[str, Any] = {}
                    if norm_warnings:
                        meta["normalization_warnings"] = norm_warnings

                    block = CanonicalBlock(
                        id=f"b-ch{len(canonical_chapters)+1:03d}-{p_block_idx:04d}",
                        type=b_type,
                        raw_text=para_clean,
                        normalized_text=norm_para,
                        provenance=prov,
                        semantic_metadata=meta,
                    )
                    blocks.append(block)

                chap_num = len(canonical_chapters) + 1
                chap_conf = "MEDIUM" if p_origin == "fallback_production_chunk" else "HIGH"
                canonical_chap = CanonicalChapter(
                    id=f"ch-{chap_num:03d}",
                    number=chap_num,
                    title=p_title,
                    blocks=blocks,
                    confidence=chap_conf,
                    words=p_words,
                    unit_type=p_unit_type,
                    is_literary_chapter=p_is_lit,
                    is_production_chunk=p_is_prod,
                    boundary_origin=p_origin,
                    parent_chapter_id=p_parent_id,
                    parent_chapter_title=p_parent_title,
                    literary_chapter_number=p_lit_num,
                    chunk_index=p_chunk_idx,
                    total_chunks_in_chapter=p_total_chunks,
                )
                canonical_chapters.append(canonical_chap)

        report = ExtractionQualityReport(
            source_type=self.source_type,
            source_path=str(self.file_path),
            extraction_engine="text_parser",
            total_pages_or_docs=1,
            total_words=sum(c.words for c in canonical_chapters),
            total_chapters=len(canonical_chapters),
            total_blocks=sum(len(c.blocks) for c in canonical_chapters),
        )

        book_slug = re.sub(r"[^\w\-]", "_", self.file_path.stem.lower()).strip("_")
        canonical_book = CanonicalBook(
            book_id=book_slug,
            title=self.file_path.stem.replace("_", " ").title(),
            source_type=self.source_type,
            source_path=str(self.file_path),
            extraction_engine="text_parser",
            quality_report=report,
            chapters=canonical_chapters,
        )
        return canonical_book


class MarkdownParser(PlainTextParser):
    """
    Forensic parser for Markdown (.md) documents.
    Inherits line-offset coordinate tracking and chapter segmentation from PlainTextParser.
    """
    def __init__(self, file_path: Path):
        super().__init__(file_path, source_type="md")
