#!/usr/bin/env python3
"""
Unit and integration tests for the standalone audiobook_factory.extraction package.
Verifies clean imports, contracts, PlainTextParser, MarkdownParser, ExtractionEngine,
and crash boundary error manifests.
"""

import unittest
import tempfile
import json
import zipfile
from pathlib import Path

from audiobook_factory.extraction import (
    ExtractionEngine,
    process_book_file,
    extract_chapters,
    extract_epub,
    extract_gemini_pdf,
    CanonicalBook,
    CanonicalChapter,
    CanonicalBlock,
    SourceProvenance,
    ExtractionQualityReport,
    ExtractionGateAuditError,
    clean_book_text,
    normalize_block_text,
    TextNormalizer,
    segment_chapters_from_text,
    split_large_chapter_on_semantic_boundary,
    ChapterSegmenter,
    ExtractionQualityAuditor,
    ForensicEPUBParser,
    PlainTextParser,
    MarkdownParser,
    ForensicPDFEngine,
)


class TestExtractionPackage(unittest.TestCase):
    """Verifies standalone extraction package contracts and engines."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_minimal_epub(self, file_path: Path) -> Path:
        """Helper to create a synthetic valid EPUB."""
        container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

        package_opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Synthetic Test Novel</dc:title>
    <dc:creator>Test Author</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapter1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>"""

        nav_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
      <li><a href="ch1.xhtml">Chapter 1: The New Horizon</a></li>
    </ol>
  </nav>
</body>
</html>"""

        c1_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
  <h1>Chapter 1: The New Horizon</h1>
  <p>The dawn broke slowly over the silent forest, sending long amber fingers of sunlight through the ancient pine branches.</p>
  <p>A solitary scout watched from the high ridge, his eyes tracing the distant river winding through the misty valley below.</p>
  <p>He adjusted his leather armor and checked the hilt of his weathered iron blade before beginning the steep descent down the rocky mountain trail toward the encampment.</p>
</body>
</html>"""

        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("mimetype", "application/epub+zip")
            zf.writestr("META-INF/container.xml", container_xml)
            zf.writestr("OEBPS/package.opf", package_opf)
            zf.writestr("OEBPS/nav.xhtml", nav_xhtml)
            zf.writestr("OEBPS/ch1.xhtml", c1_xhtml)

        return file_path

    def test_01_public_exports_and_contracts(self):
        """Verifies all contracts can be instantiated directly from package."""
        prov = SourceProvenance(
            source_file="test.txt",
            source_type="txt",
            line_start=1,
            line_end=5,
            reading_order=1,
            char_offset=0,
            extraction_method="text_parser",
        )
        block = CanonicalBlock(
            id="b-001-0001",
            type="paragraph",
            raw_text="Hello world.",
            normalized_text="Hello world.",
            provenance=prov,
        )
        chapter = CanonicalChapter(
            id="ch-001",
            number=1,
            title="Chapter 1",
            blocks=[block],
            words=2,
        )
        book = CanonicalBook(
            book_id="test_book",
            title="Test Book",
            source_type="txt",
            source_path="test.txt",
            chapters=[chapter],
        )
        self.assertEqual(book.book_id, "test_book")
        self.assertEqual(len(book.chapters), 1)
        self.assertEqual(book.chapters[0].blocks[0].normalized_text, "Hello world.")

    def test_02_plaintext_and_markdown_parsers_standalone(self):
        """Verifies PlainTextParser and MarkdownParser operate directly."""
        txt_path = self.base_path / "book.txt"
        txt_path.write_text("Chapter 1: The Journey\n\nThe road went ever on and on.", encoding="utf-8")
        txt_parser = PlainTextParser(txt_path)
        book_txt = txt_parser.parse()
        self.assertEqual(len(book_txt.chapters), 1)
        self.assertEqual(book_txt.chapters[0].title, "Chapter 1: The Journey")
        self.assertEqual(book_txt.chapters[0].blocks[0].provenance.source_type, "txt")

        md_path = self.base_path / "guide.md"
        md_path.write_text("# Chapter 1: Foundations\n\nThis is a foundational markdown guide.", encoding="utf-8")
        md_parser = MarkdownParser(md_path)
        book_md = md_parser.parse()
        self.assertEqual(len(book_md.chapters), 1)
        self.assertEqual(book_md.chapters[0].title, "Chapter 1: Foundations")
        self.assertEqual(book_md.chapters[0].blocks[0].provenance.source_type, "md")

    def test_03_extraction_engine_end_to_end_epub(self):
        """Verifies ExtractionEngine.extract() on an EPUB generates all canonical and legacy artifacts."""
        epub_file = self.base_path / "sample.epub"
        self._create_minimal_epub(epub_file)

        out_dir = self.base_path / "projects"
        canonical_book = ExtractionEngine.extract(epub_file, out_dir)

        self.assertIsInstance(canonical_book, CanonicalBook)
        self.assertEqual(len(canonical_book.chapters), 1)
        self.assertEqual(canonical_book.chapters[0].title, "Chapter 1: The New Horizon")

        book_proj_dir = out_dir / "sample"
        self.assertTrue((book_proj_dir / "raw" / "source_manifest.json").exists())
        self.assertTrue((book_proj_dir / "canonical" / "book.json").exists())
        self.assertTrue((book_proj_dir / "canonical" / "quality_report.json").exists())
        self.assertTrue((book_proj_dir / "extracted" / "chapter_001.md").exists())
        self.assertTrue((book_proj_dir / "metadata.json").exists())

        # Verify load_canonical roundtrip from disk
        reloaded = CanonicalBook.load_canonical(book_proj_dir / "canonical")
        self.assertEqual(reloaded.book_id, canonical_book.book_id)
        self.assertEqual(len(reloaded.chapters), len(canonical_book.chapters))

    def test_04_process_book_file_wrapper_compatibility(self):
        """Verifies process_book_file() function wrapper returns expected dictionary."""
        txt_path = self.base_path / "sample.txt"
        txt_path.write_text("Chapter 1: Prologue\n\nIt was the best of times, it was the worst of times.", encoding="utf-8")

        out_dir = self.base_path / "projects"
        metadata = process_book_file(txt_path, out_dir)

        self.assertIsInstance(metadata, dict)
        self.assertIn("book_id", metadata)
        self.assertIn("chapters", metadata)
        self.assertIn("total_words", metadata)
        self.assertEqual(metadata["total_chapters"], 1)

    def test_05_crash_boundary_creates_error_manifest(self):
        """Verifies that an unhandled parse error generates extraction_error.json in project dir."""
        bad_file = self.base_path / "corrupt.epub"
        bad_file.write_text("This is definitely not a zip file.", encoding="utf-8")

        out_dir = self.base_path / "projects"
        with self.assertRaises(Exception):
            ExtractionEngine.extract(bad_file, out_dir)

        error_manifest_path = out_dir / "corrupt" / "extraction_error.json"
        self.assertTrue(error_manifest_path.exists())
        with open(error_manifest_path, "r", encoding="utf-8") as ef:
            err_data = json.load(ef)
        self.assertEqual(err_data["status"], "EXTRACTION_FAILED")
        self.assertEqual(err_data["book_id"], "corrupt")

    def test_06_book_id_path_traversal_sanitization(self):
        """Verifies that malicious or path-traversing book_id inputs are sanitized and stay inside output dir."""
        txt_path = self.base_path / "traversal_test.txt"
        words = ["word"] * 60
        txt_path.write_text("Chapter 1: Security\n\n" + " ".join(words), encoding="utf-8")

        out_dir = self.base_path / "projects"
        # Passing malicious traversal sequence in book_id
        canonical = ExtractionEngine.extract(txt_path, out_dir, book_id="../../escaped_slug")
        self.assertEqual(canonical.book_id, "escaped_slug")
        # Ensure project was created strictly inside out_dir
        expected_dir = (out_dir / "escaped_slug").resolve()
        self.assertTrue(expected_dir.exists())
        self.assertTrue(expected_dir.is_relative_to(out_dir.resolve()))

    def test_07_indic_abbreviation_sentence_split_protection(self):
        """Verifies that Devanagari honorific abbreviations do not cause premature sentence fragmentation."""
        from audiobook_factory.extraction.segmenter import _recursive_split_segments
        # Build text that exceeds threshold and has an Indic abbreviation right around split point
        filler = "यह एक वाक्य है जो परीक्षण के लिए बनाया गया है। " * 30
        text = filler + "डॉ. कुमार ने कहा कि सब ठीक है। " + filler
        segments = _recursive_split_segments(text, max_words=50)
        # Verify that 'डॉ.' is never broken away from 'कुमार'
        full_reconstructed = " ".join(s[0] for s in segments)
        self.assertIn("डॉ. कुमार", full_reconstructed)

    def test_08_epub_aside_tag_ignored(self):
        """Verifies that non-narrative <aside> elements in EPUBs are ignored by EPUBStructuralHTMLParser."""
        from audiobook_factory.extraction.parsers.epub import EPUBStructuralHTMLParser
        parser = EPUBStructuralHTMLParser(source_file="test.html", spine_item="item_01", base_reading_order=0)
        sample_html = (
            "<div>"
            "<h1>Chapter 1</h1>"
            "<p>Main literary narrative sentence.</p>"
            "<aside><p>This is a footnote or sidebar note that should be ignored.</p></aside>"
            "<p>Another literary narrative sentence.</p>"
            "</div>"
        )
        parser.feed(sample_html)
        blocks = parser.finalize()
        texts = [b.raw_text for b in blocks]
        self.assertTrue(any("Main literary narrative sentence." in t for t in texts))
        self.assertTrue(any("Another literary narrative sentence." in t for t in texts))
        self.assertFalse(any("This is a footnote or sidebar note" in t for t in texts))

    def test_09_markdown_table_and_equation_block_classification(self):
        """Verifies MarkdownParser accurately tags tables, equations, abstracts, and callouts with semantic metadata."""
        md_text = (
            "# Section 1: Deep Learning Findings\n\n"
            "> **Abstract**: This whitepaper evaluates attention mechanism latency.\n\n"
            "Here is the benchmark summary table:\n\n"
            "| Model | Accuracy | Latency (ms) |\n"
            "| :--- | :--- | :--- |\n"
            "| Flash 2.0 | 94.5% | 120 |\n"
            "| Pro 1.5 | 96.2% | 340 |\n\n"
            "The loss function is defined as:\n\n"
            "$$\\mathcal{L}_{\\text{total}} = \\lambda \\sum_{i=1}^N (y_i - \\hat{y}_i)^2$$\n\n"
            "> [!NOTE]\n"
            "> Lower latency enables real-time podcast audio synthesis.\n"
        )
        md_file = self.base_path / "research_paper.md"
        md_file.write_text(md_text, encoding="utf-8")

        parser = MarkdownParser(md_file)
        book = parser.parse()

        self.assertEqual(len(book.chapters), 1)
        blocks = book.chapters[0].blocks
        block_types = [b.type for b in blocks]

        self.assertIn("abstract", block_types)
        self.assertIn("table", block_types)
        self.assertIn("equation", block_types)
        self.assertIn("callout", block_types)

        # Inspect table block
        table_blocks = [b for b in blocks if b.type == "table"]
        self.assertEqual(len(table_blocks), 1)
        self.assertEqual(table_blocks[0].semantic_metadata.get("format"), "markdown")
        self.assertIn("Flash 2.0", table_blocks[0].raw_text)

        # Inspect equation block
        eq_blocks = [b for b in blocks if b.type == "equation"]
        self.assertEqual(len(eq_blocks), 1)
        self.assertEqual(eq_blocks[0].semantic_metadata.get("display_mode"), "block")
        self.assertEqual(eq_blocks[0].semantic_metadata.get("format"), "latex")

    def test_10_math_symbols_not_flagged_as_ocr_noise(self):
        """Verifies PDFQualityAnalyzer does not misidentify standard math/Greek symbols as OCR noise."""
        from audiobook_factory.extraction.parsers.pdf.quality_analyzer import PDFQualityAnalyzer

        math_dense_page = (
            "We define the gradient as \\nabla f(x) and the integral \\int_{0}^{\\infty} e^{-x^2} dx. "
            "For all \\alpha, \\beta \\in \\mathbb{R}, the condition \\sum_{i=1}^n x_i \\le \\theta holds. "
            "The loss function converges monotonically as t \\to \\infty."
        )
        audits, cleaned = PDFQualityAnalyzer.audit_pages([math_dense_page])
        self.assertEqual(len(audits), 1)
        # Should not flag as symbol noise
        symbol_noise_warnings = [w for w in audits[0].warnings if "symbol/noise ratio" in w.lower()]
        self.assertEqual(len(symbol_noise_warnings), 0)


if __name__ == "__main__":
    unittest.main()

