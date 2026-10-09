# Audiobook Studio: Document Extraction Subsystem (Pillar 1)

Standalone forensic document ingestion, layout reconstruction, text normalization, chapter segmentation, and AST generation engine.

## Overview

The `audiobook_factory.extraction` package converts raw literary documents (`.epub`, `.pdf`, `.txt`, `.md`) into a canonical AST representation (`CanonicalBook`) with zero loss of raw textual fidelity, character-accurate provenance, and fail-closed quality gate auditing.

## Architecture

```
audiobook_factory/extraction/
├── __init__.py           # Clean public API exports
├── contracts.py          # Strongly typed Pydantic v2 AST schemas
├── engine.py             # ExtractionEngine coordinator & process_book_file
├── normalizer.py         # TextNormalizer (Unicode spaces, HTML decoding, bracket protection)
├── segmenter.py          # ChapterSegmenter (regex rules, 2-line title assembler, meso-tier splitting)
├── quality_gate.py       # Gate 0.1 ExtractionQualityAuditor (fail-closed on REVIEW)
└── parsers/              # Dedicated format parsers
    ├── __init__.py
    ├── epub.py           # ForensicEPUBParser (EPUB 3 nav landmarks & node-level anchor isolation)
    ├── text.py           # PlainTextParser & MarkdownParser (line offset tracking)
    └── pdf/              # Forensic PDF subsystem
        ├── __init__.py
        ├── forensic_engine.py
        ├── layout_reconstructor.py
        ├── quality_analyzer.py
        ├── vision_extractor.py
        └── models.py
```

## Data Contracts (AST)

- **`CanonicalBook`**: Top-level single source of truth containing metadata, quality report, and ordered chapters. Provides `save_canonical()`, `load_canonical()`, `project_legacy_extracted()`, and `to_legacy_metadata()`.
- **`CanonicalChapter`**: Ordered collection of `CanonicalBlock` units. Distinguishes authentic `literary_chapter` from artificial `production_chunk`.
- **`CanonicalBlock`**: Atomic paragraph/heading with sacred `raw_text`, speech-ready `normalized_text`, and forensic `SourceProvenance`.
- **`SourceProvenance`**: Coordinates tracing text back to file, line numbers, character offsets, PDF page/columns, or EPUB spine items.
- **`ExtractionQualityReport`**: Quantitative metrics, confidence score, warnings, suspicious pages, and Gate 0.1 status.

## Usage

### Programmatic Ingestion

```python
from pathlib import Path
from audiobook_factory.extraction import ExtractionEngine, process_book_file

# Method 1: Using ExtractionEngine to get CanonicalBook AST
book = ExtractionEngine.extract(
    input_file=Path("novel.epub"),
    output_base_dir=Path("projects"),
    force_gate=False,
)
print(f"Extracted {len(book.chapters)} chapters, {book.quality_report.total_words} words.")

# Method 2: Backward-compatible metadata dictionary
metadata = process_book_file(
    input_file=Path("novel.pdf"),
    output_base_dir=Path("projects"),
)
```

### Direct Parser Access

```python
from pathlib import Path
from audiobook_factory.extraction.parsers.epub import ForensicEPUBParser
from audiobook_factory.extraction.parsers.text import PlainTextParser
from audiobook_factory.extraction.parsers.pdf import ForensicPDFEngine

# EPUB parsing
epub_parser = ForensicEPUBParser(Path("book.epub"))
book, legacy_items = epub_parser.parse()

# Plain text parsing
text_parser = PlainTextParser(Path("book.txt"))
book = text_parser.parse()
```

## Quality Gates (Gate 0.1)

Extraction enforces Gate 0.1 fail-closed protection via `ExtractionQualityAuditor`. Documents with $<50$ words, 0 chapters, or $>25\%$ layout/OCR anomalies trigger an `ExtractionGateAuditError` unless bypassed with `force_gate=True`.
