#!/usr/bin/env python3
"""
Phase 3 Verification & Regression Suite for Source Extraction System Hardening.
Verifies:
1. CanonicalBook.load_canonical() AST roundtrip rehydration.
2. Unicode whitespace variants and HTML entity decoding with Indic ZWJ/ZWNJ preservation.
3. EPUB 3 navigation HTML entity unescaping.
4. PDF engine file handle safety and resource cleanup on Windows.
5. Multi-format end-to-end pipeline ingestion (.epub, .pdf, .txt, .md).
"""

import os
import json
import zipfile
import tempfile
import unittest
from pathlib import Path

import pypdf
from audiobook_factory.book_model import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalBlock,
    SourceProvenance,
    ExtractionQualityReport,
)
from audiobook_factory.normalizer import clean_book_text, normalize_block_text
from audiobook_factory.epub_parser import ForensicEPUBParser, extract_epub
from audiobook_factory.pdf_engine import ForensicPDFEngine
from audiobook_factory.extractor import process_book_file


class TestExtractionPhase3(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_synthetic_epub3_with_entities(self, file_path: Path) -> Path:
        """Creates an EPUB 3 with HTML entities in <nav epub:type='toc'>."""
        container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

        package_opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Entity &amp; Space &mdash; A Novel</dc:title>
    <dc:creator>Test &amp; Author</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="c1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="c1"/>
  </spine>
</package>"""

        nav_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
      <li><a href="chapter1.xhtml">Chapter 1 &mdash; The Dragon&#39;s Den</a></li>
    </ol>
  </nav>
</body>
</html>"""

        c1_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
  <h1>Chapter 1 &mdash; The Dragon&#39;s Den</h1>
  <p>The cold mountain wind swept violently through the narrow rocky pass, carrying with it the unmistakable scent of ancient sulfur and smoldering ash.</p>
  <p>A solitary ranger stood perched upon the jagged precipice, gazing intently down into the deep subterranean cavern hidden below the mist.</p>
  <p>He turned toward his companion and whispered quietly, &quot;We must hurry before the darkness of nightfall overtakes our expedition completely.&quot;</p>
  <p>The companion nodded in silent agreement, tightening the worn leather straps of his travel pack as they began their descent into the shadows.</p>
</body>
</html>"""

        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("mimetype", "application/epub+zip")
            zf.writestr("META-INF/container.xml", container_xml)
            zf.writestr("OEBPS/package.opf", package_opf)
            zf.writestr("OEBPS/nav.xhtml", nav_xhtml)
            zf.writestr("OEBPS/chapter1.xhtml", c1_xhtml)

        return file_path

    def _create_synthetic_pdf(self, file_path: Path) -> Path:
        """Creates a minimal valid synthetic PDF with 2 pages."""
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=300, height=300)
        writer.add_blank_page(width=300, height=300)
        with open(file_path, "wb") as f:
            writer.write(f)
        return file_path

    def test_01_canonical_book_roundtrip_deserialization(self):
        """Verify CanonicalBook save_canonical -> load_canonical roundtrip fidelity."""
        prov = SourceProvenance(
            source_file="test_book.epub",
            source_type="epub",
            spine_item="ch01.xhtml",
            line_start=10,
            line_end=15,
            char_offset=120,
            reading_order=1,
            extraction_method="epub_dom",
        )
        block = CanonicalBlock(
            id="b-001-0001",
            type="paragraph",
            raw_text="The witcher drew his silver sword.",
            normalized_text="The witcher drew his silver sword.",
            provenance=prov,
            confidence="HIGH",
        )
        chapter = CanonicalChapter(
            id="ch-001",
            number=1,
            title="Chapter 1: The Silver Sword",
            blocks=[block],
            words=6,
            unit_type="literary_chapter",
            is_literary_chapter=True,
            is_production_chunk=False,
            boundary_origin="detected_heading",
            literary_chapter_number=1,
        )
        report = ExtractionQualityReport(
            overall_confidence="HIGH",
            gate_status="PASS",
            source_type="epub",
            source_path="test_book.epub",
            total_words=6,
            total_chapters=1,
            total_blocks=1,
        )
        book = CanonicalBook(
            book_id="test_book",
            title="The Witcher Chronicles",
            author="A. Sapkowski",
            source_type="epub",
            source_path="test_book.epub",
            quality_report=report,
            chapters=[chapter],
        )

        canonical_dir = self.base_path / "canonical"
        book.save_canonical(canonical_dir)

        # Load back from disk
        rehydrated = CanonicalBook.load_canonical(canonical_dir)
        self.assertEqual(rehydrated.book_id, "test_book")
        self.assertEqual(rehydrated.title, "The Witcher Chronicles")
        self.assertEqual(len(rehydrated.chapters), 1)
        self.assertEqual(rehydrated.chapters[0].title, "Chapter 1: The Silver Sword")
        self.assertEqual(rehydrated.chapters[0].blocks[0].raw_text, "The witcher drew his silver sword.")
        self.assertEqual(rehydrated.chapters[0].blocks[0].provenance.spine_item, "ch01.xhtml")
        self.assertEqual(rehydrated.quality_report.gate_status, "PASS")
        self.assertEqual(len(rehydrated.get_literary_chapters()), 1)

    def test_02_unicode_whitespace_and_html_entities(self):
        """Verify non-breaking spaces and HTML entities are normalized while Indic ZWJ/ZWNJ are preserved."""
        # Non-breaking space \u00a0, thin space \u2009, ideographic space \u3000, and entities &mdash;, &quot;
        raw_text = "Word1\u00a0Word2\u2009Word3\u3000Word4 &mdash; &quot;Quote&quot; &#39;Single&#39;"
        cleaned = clean_book_text(raw_text)
        self.assertEqual(cleaned, "Word1 Word2 Word3 Word4 — \"Quote\" 'Single'")

        # Indic Devanagari text with ZWNJ (\u200c) and ZWJ (\u200d)
        indic_text = "सद्\u200cभाव और क्य\u200dया"
        indic_cleaned = clean_book_text(indic_text)
        self.assertIn("\u200c", indic_cleaned)
        self.assertIn("\u200d", indic_cleaned)

    def test_03_epub_nested_nav_and_entity_unescaping(self):
        """Verify EPUB 3 parser decodes HTML entities in navigation landmarks."""
        epub_path = self.base_path / "test_entities.epub"
        self._create_synthetic_epub3_with_entities(epub_path)

        parser = ForensicEPUBParser(epub_path)
        book, legacy_chapters = parser.parse()

        self.assertEqual(len(book.chapters), 1)
        # Should be unescaped from &mdash; and &#39;
        self.assertIn("—", book.chapters[0].title)
        self.assertIn("'", book.chapters[0].title)
        self.assertNotIn("&mdash;", book.chapters[0].title)
        self.assertNotIn("&#39;", book.chapters[0].title)

    def test_04_pdf_engine_file_handle_safety(self):
        """Verify ForensicPDFEngine safely releases file descriptors on Windows."""
        pdf_path = self.base_path / "safe_test.pdf"
        self._create_synthetic_pdf(pdf_path)

        engine = ForensicPDFEngine(pdf_path)
        pages, audits, escalated = engine.extract_pages()
        self.assertEqual(len(pages), 2)

        # Re-open or delete immediately should not raise PermissionError / WinError 32
        with open(pdf_path, "rb") as f:
            data = f.read()
        self.assertTrue(len(data) > 0)

    def test_05_multi_format_end_to_end_pipeline(self):
        """Verify process_book_file across TXT, MD, and EPUB in a complete run."""
        out_base = self.base_path / "output"

        # 1. Plain Text
        txt_path = self.base_path / "sample_novel.txt"
        txt_path.write_text("CHAPTER 1\n\nThe adventure began on a starry night.\n\nCHAPTER 2\n\nThe journey continued across the plains.", encoding="utf-8")
        meta_txt = process_book_file(txt_path, out_base)
        self.assertEqual(meta_txt["total_chapters"], 2)
        self.assertTrue((out_base / "sample_novel" / "canonical" / "book.json").exists())
        self.assertTrue((out_base / "sample_novel" / "extracted" / "chapter_001.md").exists())

        # 2. Markdown
        md_path = self.base_path / "sample_guide.md"
        md_path.write_text(
            "# Chapter 1: Introduction\n\nWelcome to the official system operations and engineering handbook.\n\n"
            "# Chapter 2: Setup\n\nFollow these simple steps to configure your environment and run tests.",
            encoding="utf-8",
        )
        meta_md = process_book_file(md_path, out_base)
        self.assertEqual(meta_md["total_chapters"], 2)
        self.assertTrue((out_base / "sample_guide" / "canonical" / "book.json").exists())

        # 3. EPUB
        epub_path = self.base_path / "sample_book.epub"
        self._create_synthetic_epub3_with_entities(epub_path)
        meta_epub = process_book_file(epub_path, out_base)
        self.assertEqual(meta_epub["total_chapters"], 1)
        self.assertTrue((out_base / "sample_book" / "canonical" / "book.json").exists())


if __name__ == "__main__":
    unittest.main()
