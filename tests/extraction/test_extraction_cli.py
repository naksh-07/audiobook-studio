#!/usr/bin/env python3
"""
Unit and integration tests for the standalone extraction CLI (audiobook_factory.extraction.cli).
Verifies subcommands: extract, audit, and inspect across success and error conditions.
"""

import unittest
import tempfile
import json
import io
import sys
from pathlib import Path
from unittest.mock import patch

from audiobook_factory.extraction.cli import main
from audiobook_factory.extraction.contracts import CanonicalBook, CanonicalChapter, CanonicalBlock, SourceProvenance


class TestExtractionCLI(unittest.TestCase):
    """Test suite for extraction CLI commands."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_cli_extract_text_file(self):
        """Verifies 'extract' subcommand succeeds on a plain text novel."""
        novel_txt = self.base_path / "test_novel.txt"
        novel_txt.write_text(
            "Chapter 1: The Dark Forest\n\n" + "The journey through the woods began in earnest as shadows lengthened across the path.\n\n" * 5,
            encoding="utf-8",
        )
        out_dir = self.base_path / "projects"

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            exit_code = main(["extract", str(novel_txt), "--out", str(out_dir), "--json"])

        self.assertEqual(exit_code, 0)
        output_str = mock_stdout.getvalue()
        meta = json.loads(output_str)
        self.assertIn("book_id", meta)
        self.assertEqual(meta["total_chapters"], 1)
        self.assertTrue((out_dir / "test_novel" / "canonical" / "book.json").exists())

    def test_02_cli_extract_file_not_found(self):
        """Verifies 'extract' subcommand returns code 1 if source file is missing."""
        missing = self.base_path / "non_existent_novel.epub"
        with patch("sys.stderr", new_callable=io.StringIO):
            exit_code = main(["extract", str(missing)])
        self.assertEqual(exit_code, 1)

    def test_03_cli_audit_and_inspect_subcommands(self):
        """Verifies 'audit' and 'inspect' subcommands on valid canonical book."""
        # 1. Create a minimal valid canonical book directory
        canon_dir = self.base_path / "projects" / "my_book" / "canonical"
        canon_dir.mkdir(parents=True, exist_ok=True)

        prov = SourceProvenance(source_file="test.txt", source_type="txt", extraction_method="test")
        block = CanonicalBlock(id="b-01", raw_text="Sample text content for testing purposes.", normalized_text="Sample text content for testing purposes.", provenance=prov)
        chap = CanonicalChapter(id="ch-01", number=1, title="Chapter 1", blocks=[block], words=6)
        book = CanonicalBook(book_id="my_book", title="My Book", source_type="txt", source_path="test.txt", chapters=[chap])
        book.save_canonical(canon_dir)

        # 2. Test audit subcommand with --force-gate (since word count < 50)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            exit_code = main(["audit", str(canon_dir), "--force-gate", "--json"])
        self.assertEqual(exit_code, 0)
        audit_rep = json.loads(mock_stdout.getvalue())
        self.assertIn("gate_status", audit_rep)

        # 3. Test inspect subcommand
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            exit_code = main(["inspect", str(canon_dir), "--json"])
        self.assertEqual(exit_code, 0)
        inspect_data = json.loads(mock_stdout.getvalue())
        self.assertEqual(inspect_data["book_id"], "my_book")
        self.assertEqual(inspect_data["total_units"], 1)


if __name__ == "__main__":
    unittest.main()
