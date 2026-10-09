#!/usr/bin/env python3
"""
Unit tests verifying backward-compatibility facades.
Ensures that all legacy modules at audiobook_factory/ root continue to export
all expected classes, functions, and constants without breaking external callers.
"""

import unittest


class TestFacadeCompatibility(unittest.TestCase):
    """Verifies that legacy import paths remain 100% operational."""

    def test_01_book_model_facade(self):
        import audiobook_factory.book_model as bm
        self.assertTrue(hasattr(bm, "CanonicalBook"))
        self.assertTrue(hasattr(bm, "CanonicalChapter"))
        self.assertTrue(hasattr(bm, "CanonicalBlock"))
        self.assertTrue(hasattr(bm, "SourceProvenance"))
        self.assertTrue(hasattr(bm, "ExtractionQualityReport"))
        self.assertTrue(hasattr(bm, "ExtractionGateAuditError"))

    def test_02_normalizer_facade(self):
        import audiobook_factory.normalizer as norm
        self.assertTrue(hasattr(norm, "clean_book_text"))
        self.assertTrue(hasattr(norm, "normalize_block_text"))
        self.assertTrue(hasattr(norm, "TextNormalizer"))
        self.assertTrue(hasattr(norm, "UNICODE_SPACES"))
        self.assertTrue(hasattr(norm, "PUNCTUATION_REPLACEMENTS"))
        # Test clean_book_text directly
        cleaned = norm.clean_book_text("Hello\u00a0World &mdash; Test")
        self.assertEqual(cleaned, 'Hello World — Test')

    def test_03_chapter_segmenter_facade(self):
        import audiobook_factory.chapter_segmenter as cs
        self.assertTrue(hasattr(cs, "CHAPTER_PATTERNS"))
        self.assertTrue(hasattr(cs, "COMBINED_CHAPTER_REGEX"))
        self.assertTrue(hasattr(cs, "segment_chapters_from_text"))
        self.assertTrue(hasattr(cs, "split_large_chapter_on_semantic_boundary"))
        self.assertTrue(hasattr(cs, "ChapterSegmenter"))

    def test_04_epub_parser_facade(self):
        import audiobook_factory.epub_parser as ep
        self.assertTrue(hasattr(ep, "ForensicEPUBParser"))
        self.assertTrue(hasattr(ep, "EPUBStructuralHTMLParser"))
        self.assertTrue(hasattr(ep, "extract_epub"))

    def test_05_extractor_facade(self):
        import audiobook_factory.extractor as ext
        self.assertTrue(hasattr(ext, "process_book_file"))
        self.assertTrue(hasattr(ext, "ExtractionEngine"))
        self.assertTrue(hasattr(ext, "extract_chapters"))
        self.assertTrue(hasattr(ext, "extract_gemini_pdf"))
        self.assertTrue(hasattr(ext, "CanonicalBook"))
        self.assertTrue(hasattr(ext, "clean_book_text"))

    def test_06_pdf_engine_facade(self):
        import audiobook_factory.pdf_engine as pe
        self.assertTrue(hasattr(pe, "ForensicPDFEngine"))
        self.assertTrue(hasattr(pe, "PDFLayoutReconstructor"))
        self.assertTrue(hasattr(pe, "PDFQualityAnalyzer"))
        self.assertTrue(hasattr(pe, "GeminiVisionPDFExtractor"))


if __name__ == "__main__":
    unittest.main()
