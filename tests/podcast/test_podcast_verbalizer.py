#!/usr/bin/env python3
"""
Unit and Integration Tests for the Podcast & Technical Verbalization Subsystem.
Verifies MathVerbalizer, TableVerbalizer, AbstractCalloutVerbalizer, and
PodcastScriptBuilder screenplay generation.
"""

import unittest
import tempfile
from pathlib import Path

from audiobook_factory.extraction.contracts import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalBlock,
    SourceProvenance,
    ExtractionQualityReport,
)
from audiobook_factory.podcast import (
    MathVerbalizer,
    TableVerbalizer,
    AbstractCalloutVerbalizer,
    PodcastScriptBuilder,
    PodcastScript,
    PodcastSegment,
    HostProfile,
    generate_podcast_script_from_file,
)


class TestPodcastVerbalizer(unittest.TestCase):
    """Verifies technical verbalization and podcast screenplay generation."""

    def test_01_math_verbalizer_greek_and_fractions(self):
        """Verifies Greek symbols, fractions, and integrals are translated to spoken words."""
        latex_eq = r"\int_{0}^{\infty} \frac{\alpha + \beta}{\gamma} dx \approx \theta"
        spoken = MathVerbalizer.verbalize_latex(latex_eq)
        self.assertIn("integral from 0 to infinity", spoken)
        self.assertIn("alpha + beta divided by gamma", spoken)
        self.assertIn("is approximately", spoken)
        self.assertIn("theta", spoken)

    def test_02_math_verbalizer_vector_norms_and_loss(self):
        """Verifies vector norms, loss objectives, and summations are translated cleanly."""
        latex_loss = r"\mathcal{L}_{\text{total}} = \lambda \sum_{i=1}^{N} (y_i - \hat{y}_i)^2 + \gamma \|\mathbf{W}\|_2^2"
        spoken = MathVerbalizer.verbalize_latex(latex_loss)
        self.assertIn("total loss objective L", spoken)
        self.assertIn("sum from i equals 1 to N", spoken)
        self.assertIn("squared L2 norm of weight matrix W", spoken)
        self.assertIn("y hat sub i", spoken)

    def test_03_inline_math_verbalization(self):
        """Verifies inline $...$ math within prose sentences is converted to spoken prose."""
        prose = "The energy equivalence satisfies $E = mc^2$ and the gradient bounds satisfy $\\nabla f(x) \\le \\theta$."
        verbalized = MathVerbalizer.verbalize_inline_math(prose)
        self.assertIn("E equals m c squared", verbalized)
        self.assertIn("gradient f(x) is less than or equal to theta", verbalized)
        self.assertNotIn("$", verbalized)

    def test_04_table_verbalizer_benchmark_insights(self):
        """Verifies TableVerbalizer converts structured markdown tables into conversational insights."""
        table_md = (
            "| Model | Accuracy (%) | Latency (ms) |\n"
            "| :--- | :--- | :--- |\n"
            "| Flash 2.0 | 96.8% | 115 |\n"
            "| Pro 1.5 | 98.2% | 320 |\n"
        )
        insight = TableVerbalizer.verbalize_table(table_md, title="Performance Benchmark")
        self.assertIn("Flash 2.0 achieved 96.8% accuracy (%)", insight)
        self.assertIn("115 latency (ms)", insight)
        self.assertIn("Pro 1.5", insight)

    def test_05_abstract_and_callout_verbalizer(self):
        """Verifies abstracts and callout blocks are converted to audio hook and takeaway transitions."""
        abstract = "> **Abstract**: This whitepaper evaluates attention mechanism latency in real-time pipelines."
        spoken_abstract = AbstractCalloutVerbalizer.verbalize_abstract(abstract)
        self.assertIn("To kick things off, the core premise of this research", spoken_abstract)
        self.assertIn("evaluates attention mechanism latency", spoken_abstract)

        callout = "> [!NOTE]\n> Key pooling increases system throughput tenfold."
        spoken_callout = AbstractCalloutVerbalizer.verbalize_callout(callout)
        self.assertIn("An essential takeaway to keep in mind here is that", spoken_callout)
        self.assertIn("Key pooling increases system throughput tenfold", spoken_callout)

    def test_06_podcast_script_builder_end_to_end(self):
        """Verifies PodcastScriptBuilder generates a dual-host screenplay with full TTS metadata."""
        prov = SourceProvenance(source_file="paper.md", source_type="md")
        b1 = CanonicalBlock(
            id="b-01",
            type="abstract",
            raw_text="> **Abstract**: Research on acoustic neural modeling.",
            normalized_text="> **Abstract**: Research on acoustic neural modeling.",
            provenance=prov,
        )
        b2 = CanonicalBlock(
            id="b-02",
            type="equation",
            raw_text="$$E = mc^2$$",
            normalized_text="$$E = mc^2$$",
            provenance=prov,
            semantic_metadata={"latex": "E = mc^2", "display_mode": "block", "format": "latex"},
        )
        ch = CanonicalChapter(id="ch-01", number=1, title="1. Foundations", blocks=[b1, b2], words=25)
        report = ExtractionQualityReport(
            source_type="md",
            source_path="paper.md",
            extraction_engine="text_parser",
            total_pages_or_docs=1,
            total_words=25,
            total_chapters=1,
            total_blocks=2,
        )
        book = CanonicalBook(
            book_id="paper",
            title="Acoustic Neural Modeling",
            source_type="md",
            source_path="paper.md",
            extraction_engine="text_parser",
            quality_report=report,
            chapters=[ch],
        )

        builder = PodcastScriptBuilder()
        script = builder.build_from_book(book)

        self.assertIsInstance(script, PodcastScript)
        self.assertEqual(script.title, "Acoustic Neural Modeling")
        self.assertGreaterEqual(script.total_segments, 4)

        # Verify host speaker allocation
        speakers = {s.speaker for s in script.segments}
        self.assertIn("Host_A", speakers)
        self.assertIn("Host_B", speakers)

        # Verify screenplay format projection
        screenplay = script.to_screenplay_json()
        self.assertIn("chapter_id", screenplay)
        self.assertIn("cast", screenplay)
        self.assertIn("segments", screenplay)
        self.assertEqual(len(screenplay["cast"]), 2)

    def test_07_generate_podcast_script_from_benchmark_file(self):
        """Verifies generate_podcast_script_from_file operates seamlessly on real benchmark files."""
        benchmark_file = Path("benchmarks/sample_research_paper.md")
        if not benchmark_file.exists():
            self.skipTest("Benchmark sample_research_paper.md not found.")

        with tempfile.TemporaryDirectory() as tmp_dir:
            script = generate_podcast_script_from_file(benchmark_file, tmp_dir)
            self.assertIsInstance(script, PodcastScript)
            self.assertGreater(script.total_segments, 15)
            self.assertGreater(script.total_words, 400)
            self.assertTrue((Path(tmp_dir) / "sample_research_paper" / "podcast_script.json").exists())


if __name__ == "__main__":
    unittest.main()
