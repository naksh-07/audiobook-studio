"""
Unit tests for BilingualMacroChunker (Option D)
"""

import unittest
from audiobook_factory.translation.chunker import BilingualMacroChunker, MacroChunk


class TestMacroChunker(unittest.TestCase):
    def setUp(self):
        self.chunker = BilingualMacroChunker(
            target_chunk_words=1800,
            max_single_chunk_words=2200,
            context_words=50,
        )

    def test_01_empty_text(self):
        chunks = self.chunker.chunk_text("")
        self.assertEqual(len(chunks), 0)

        chunks_ws = self.chunker.chunk_text("   \n\n  ")
        self.assertEqual(len(chunks_ws), 0)

    def test_02_short_chapter_single_chunk(self):
        # Chapter with 500 words across 5 paragraphs
        paras = ["This is paragraph one with several words for testing." * 10 for _ in range(5)]
        text = "\n\n".join(paras)
        word_count = len(text.split())
        self.assertLess(word_count, 2200)

        chunks = self.chunker.chunk_text(text)
        self.assertEqual(len(chunks), 1, "Chapters <= 2200 words must be translated in exactly 1 chunk")
        self.assertEqual(chunks[0].index, 0)
        self.assertEqual(chunks[0].word_count, word_count)
        self.assertEqual(chunks[0].preceding_source_context, "")

    def test_03_long_chapter_multi_chunk_segmentation(self):
        # Create a large document with 3,500 words across 35 paragraphs (100 words each)
        single_para = "Word " * 100
        paras = [single_para.strip() for _ in range(35)]
        text = "\n\n".join(paras)
        total_words = len(text.split())
        self.assertEqual(total_words, 3500)

        chunks = self.chunker.chunk_text(text)
        self.assertGreaterEqual(len(chunks), 2, "Chapters > 2200 words must be segmented into multiple chunks")

        # Verify chunk 1 has preceding context from chunk 0
        self.assertEqual(chunks[0].index, 0)
        self.assertEqual(chunks[0].preceding_source_context, "")

        self.assertEqual(chunks[1].index, 1)
        self.assertGreater(len(chunks[1].preceding_source_context), 0)
        # Context words should be around context_words (50)
        ctx_len = len(chunks[1].preceding_source_context.split())
        self.assertLessEqual(ctx_len, 50)

    def test_04_paragraph_boundaries_preserved(self):
        p1 = "First paragraph content."
        p2 = "Second paragraph content."
        text = f"{p1}\n\n{p2}"
        chunks = self.chunker.chunk_text(text)
        self.assertEqual(len(chunks), 1)
        self.assertIn(p1, chunks[0].text)
        self.assertIn(p2, chunks[0].text)


if __name__ == "__main__":
    unittest.main()
