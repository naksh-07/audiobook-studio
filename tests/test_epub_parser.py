#!/usr/bin/env python3
"""
Unit and Integration Tests for Forensic Structural EPUB Parser.
Tests synthetic structural EPUBs, NCX navigation, and spine fallbacks.
"""

import io
import zipfile
import tempfile
import unittest
from pathlib import Path

from audiobook_factory.epub_parser import (
    EPUBStructuralHTMLParser,
    ForensicEPUBParser,
    extract_epub,
    _is_subsection_label,
    _flatten_nav_tree,
    NavItem,
    NavTarget,
)


def create_synthetic_epub(epub_path: Path) -> Path:
    """Creates a well-formed synthetic EPUB for structural testing."""
    container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

    content_opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Synthetic Test Novel</dc:title>
    <dc:creator>Jane Doe</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="ch1" href="ch01.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="ch02.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="ch1"/>
    <itemref idref="ch2"/>
  </spine>
</package>"""

    toc_ncx = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="nav1" playOrder="1">
      <navLabel><text>Chapter 1: The Gathering</text></navLabel>
      <content src="ch01.xhtml#ch1_start"/>
    </navPoint>
    <navPoint id="nav2" playOrder="2">
      <navLabel><text>Chapter 2: The Crossroads</text></navLabel>
      <content src="ch02.xhtml"/>
    </navPoint>
  </navMap>
</ncx>"""

    ch01_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body>
  <div id="ch1_start">
    <h1>Chapter 1: The Gathering</h1>
    <p>The dawn broke over the misty hills, cold and grey.</p>
    <hr/>
    <blockquote>“Beware the shadow at the pass,” she whispered softly.</blockquote>
    <p>He nodded in silence, gripping his hilt tightly.</p>
    <p class="scenebreak">* * *</p>
    <p>By midday, they had reached the crossroads of the northern vales.</p>
  </div>
</body>
</html>"""

    ch02_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 2</title></head>
<body>
  <h2>Chapter 2: The Crossroads</h2>
  <p>Four stone markers pointed toward different realms of the ancient world.</p>
  <p>The wind began to howl fiercely through the pines and barren rocks.</p>
  <p>They prepared their encampment as dusk fell upon the wild frontier.</p>
</body>
</html>"""

    with zipfile.ZipFile(epub_path, "w") as zf:
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OEBPS/content.opf", content_opf)
        zf.writestr("OEBPS/toc.ncx", toc_ncx)
        zf.writestr("OEBPS/ch01.xhtml", ch01_xhtml)
        zf.writestr("OEBPS/ch02.xhtml", ch02_xhtml)

    return epub_path


def create_synthetic_epub3_with_nav(epub_path: Path) -> Path:
    """Creates a well-formed synthetic EPUB 3 archive with HTML5 <nav epub:type="toc">."""
    container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

    package_opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>EPUB 3 Nav Specimen</dc:title>
    <dc:creator>Arthur Pendelton</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ch1" href="ch01.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="ch02.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="ch1"/>
    <itemref idref="ch2"/>
  </spine>
</package>"""

    nav_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
      <li><a href="ch01.xhtml#sec1">Chapter 1: The Silver Citadel</a></li>
      <li><a href="ch02.xhtml#sec2">Chapter 2: The Whispering Sea</a></li>
    </ol>
  </nav>
</body>
</html>"""

    ch01_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body>
  <div id="sec1">
    <h1>Chapter 1: The Silver Citadel</h1>
    <p>The spires gleamed in the twilight against the crimson horizon.</p>
    <p>Guards in polished plate armor watched the northern gates intently with drawn bows.</p>
  </div>
</body>
</html>"""

    ch02_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 2</title></head>
<body>
  <div id="sec2">
    <h1>Chapter 2: The Whispering Sea</h1>
    <p>Waves crashed relentlessly against the jagged basalt cliffs below.</p>
    <p>A solitary lantern burned inside the watchman's lonely coastal cottage.</p>
  </div>
</body>
</html>"""

    with zipfile.ZipFile(epub_path, "w") as zf:
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("EPUB/package.opf", package_opf)
        zf.writestr("EPUB/nav.xhtml", nav_xhtml)
        zf.writestr("EPUB/ch01.xhtml", ch01_xhtml)
        zf.writestr("EPUB/ch02.xhtml", ch02_xhtml)

    return epub_path


class TestForensicEPUBParser(unittest.TestCase):

    def test_structural_html_parser(self):
        sample_html = """
        <div id="start">
          <h1>Prologue</h1>
          <p>The night was still.</p>
          <hr/>
          <blockquote>“Silence is golden.”</blockquote>
          <p>* * *</p>
          <p>And then came the thunder.</p>
        </div>
        """
        parser = EPUBStructuralHTMLParser(source_file="test.epub", spine_item="ch01.xhtml")
        parser.feed(sample_html)
        blocks = parser.finalize()

        types = [b.type for b in blocks]
        self.assertIn("heading", types)
        self.assertIn("paragraph", types)
        self.assertIn("scene_break", types)
        self.assertIn("quote", types)

        # Check provenance
        h_block = next(b for b in blocks if b.type == "heading")
        self.assertEqual(h_block.provenance.spine_item, "ch01.xhtml")
        self.assertEqual(h_block.semantic_metadata.get("level"), 1)

    def test_synthetic_epub_extraction(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            epub_path = Path(tmp_dir) / "synthetic.epub"
            create_synthetic_epub(epub_path)

            parser = ForensicEPUBParser(epub_path)
            book, legacy_items = parser.parse()

            self.assertEqual(book.title, "Synthetic Test Novel")
            self.assertEqual(book.author, "Jane Doe")
            self.assertEqual(len(book.chapters), 2)
            self.assertEqual(book.chapters[0].title, "Chapter 1: The Gathering")
            self.assertEqual(book.chapters[1].title, "Chapter 2: The Crossroads")

            # Check blocks inside chapter 1
            ch1_blocks = book.chapters[0].blocks
            self.assertTrue(any(b.type == "heading" for b in ch1_blocks))
            self.assertTrue(any(b.type == "quote" for b in ch1_blocks))
            self.assertTrue(any(b.type == "scene_break" for b in ch1_blocks))

            # Check legacy backward-compatible format
            self.assertEqual(len(legacy_items), 2)
            self.assertIn("Chapter 1: The Gathering", legacy_items[0]["title"])
            self.assertIn("The dawn broke", legacy_items[0]["content"])

    def test_backward_compatible_extract_epub_api(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            epub_path = Path(tmp_dir) / "synthetic.epub"
            create_synthetic_epub(epub_path)

            meta, chapters = extract_epub(epub_path)
            self.assertEqual(meta["title"], "Synthetic Test Novel")
            self.assertEqual(meta["author"], "Jane Doe")
            self.assertEqual(len(chapters), 2)

    def test_epub3_html5_nav_extraction(self):
        """Verify EPUB 3 documents with HTML5 <nav epub:type='toc'> are parsed accurately without NCX."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            epub_path = Path(tmp_dir) / "specimen_epub3.epub"
            create_synthetic_epub3_with_nav(epub_path)

            parser = ForensicEPUBParser(epub_path)
            book, legacy_items = parser.parse()

            self.assertEqual(book.title, "EPUB 3 Nav Specimen")
            self.assertEqual(book.author, "Arthur Pendelton")
            self.assertEqual(len(book.chapters), 2)
            self.assertEqual(book.chapters[0].title, "Chapter 1: The Silver Citadel")
            self.assertEqual(book.chapters[1].title, "Chapter 2: The Whispering Sea")

            # Verify block-level content and provenance
            ch1_text = "\n".join(b.normalized_text for b in book.chapters[0].blocks)
            self.assertIn("The spires gleamed", ch1_text)
            self.assertIn("Guards in polished plate armor", ch1_text)

            ch2_text = "\n".join(b.normalized_text for b in book.chapters[1].blocks)
            self.assertIn("Waves crashed relentlessly", ch2_text)

    def test_node_level_anchor_isolation(self):
        """
        Verify multi-landmark documents with internal anchors in a single spine file
        are isolated cleanly at the CanonicalBlock level without dropping text or breaking DOM tags.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            epub_path = Path(tmp_dir) / "multi_anchor.epub"
            
            container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

            package_opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Single Spine Multi-Section</dc:title>
    <dc:creator>Test Author</dc:creator>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="combined" href="combined.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="combined"/>
  </spine>
</package>"""

            nav_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="combined.xhtml#act1">Act I: The Discovery</a></li>
      <li><a href="combined.xhtml#act2">Act II: The Confrontation</a></li>
    </ol>
  </nav>
</body>
</html>"""

            combined_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Combined Acts</title></head>
<body>
  <div id="act1">
    <h1>Act I: The Discovery</h1>
    <p>A dusty ledger was found hidden beneath the floorboards of the ancient library.</p>
    <p>The names inscribed within matched those of the ruling council members.</p>
  </div>
  <div id="act2">
    <h1>Act II: The Confrontation</h1>
    <p>The council hall fell silent as the magistrate presented the recovered evidence.</p>
    <p>No one dared speak against the authenticity of the ancient seals.</p>
  </div>
</body>
</html>"""

            with zipfile.ZipFile(epub_path, "w") as zf:
                zf.writestr("META-INF/container.xml", container_xml)
                zf.writestr("package.opf", package_opf)
                zf.writestr("nav.xhtml", nav_xhtml)
                zf.writestr("combined.xhtml", combined_xhtml)

            parser = ForensicEPUBParser(epub_path)
            book, _ = parser.parse()

            self.assertEqual(len(book.chapters), 2)
            self.assertEqual(book.chapters[0].title, "Act I: The Discovery")
            self.assertEqual(book.chapters[1].title, "Act II: The Confrontation")

            act1_text = "\n".join(b.normalized_text for b in book.chapters[0].blocks)
            self.assertIn("A dusty ledger was found", act1_text)
            self.assertNotIn("The council hall fell silent", act1_text)

            act2_text = "\n".join(b.normalized_text for b in book.chapters[1].blocks)
            self.assertIn("The council hall fell silent", act2_text)
    def test_is_subsection_label(self):
        """Verify universal sub-section label detection against Roman numerals, digits, and section tags."""
        # Roman numerals (upper and lower, with/without punctuation)
        for label in ["I", "II", "III", "IV", "v", "VIII", "IX", "X", "XI", "XII", "xx", "c", "m", "I.", "II:", "IV."]:
            self.assertTrue(_is_subsection_label(label), f"Expected True for Roman numeral {label!r}")

        # Arabic digits
        for label in ["1", "2", "3", "42", "1.", "2:", "100"]:
            self.assertTrue(_is_subsection_label(label), f"Expected True for digit {label!r}")

        # Short section / part / scene labels
        for label in ["Part I", "part 2", "PART IV", "Section 1", "section IV", "Scene 2", "scene V", "§ 1", "§1", "Part 1.", "Section 2:"]:
            self.assertTrue(_is_subsection_label(label), f"Expected True for section label {label!r}")

        # Negative cases: standalone titles, chapters with titles, frontmatter
        for label in [
            "Chapter 1: The Gathering",
            "Chapter 1",
            "Chapter 2",
            "Book One",
            "Part One: The Journey",
            "The Bounds of Reason",
            "Prologue",
            "Epilogue",
            "A Shard of Ice",
            "",
            "   ",
        ]:
            self.assertFalse(_is_subsection_label(label), f"Expected False for {label!r}")

    def test_flatten_nav_tree_subsection_detection(self):
        """Verify _flatten_nav_tree treats clusters of Roman numeral children as authentic chapters."""
        # Case A: Parent with >= 60% subsection children (3/3 = 100%)
        parent_item = NavItem(
            label="The Bounds of Reason",
            src="story1.xhtml",
            children=[
                NavItem(label="I", src="story1.xhtml#sec1"),
                NavItem(label="II", src="story1.xhtml#sec2"),
                NavItem(label="III", src="story1.xhtml#sec3"),
            ],
        )
        targets = _flatten_nav_tree([parent_item])
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].title, "The Bounds of Reason")
        self.assertEqual(targets[0].src, "story1.xhtml")
        self.assertEqual(len(targets[0].section_breaks), 3)
        self.assertEqual(targets[0].section_breaks[0], ("I", "story1.xhtml#sec1"))
        self.assertEqual(targets[0].section_breaks[1], ("II", "story1.xhtml#sec2"))
        self.assertEqual(targets[0].section_breaks[2], ("III", "story1.xhtml#sec3"))

        # Case B: Parent with standalone chapters (0/2 = 0%)
        book_item = NavItem(
            label="Book One",
            src="book1.xhtml",
            children=[
                NavItem(label="Chapter 1: The Gathering", src="book1.xhtml#ch1"),
                NavItem(label="Chapter 2: The Crossroads", src="book1.xhtml#ch2"),
            ],
        )
        targets_b = _flatten_nav_tree([book_item])
        self.assertEqual(len(targets_b), 2)
        self.assertEqual(targets_b[0].title, "Book One - Chapter 1: The Gathering")
        self.assertEqual(targets_b[1].title, "Book One - Chapter 2: The Crossroads")

    def test_hierarchical_epub_with_roman_subsections(self):
        """
        Verify that EPUBs with Roman numeral sub-sections in the TOC
        are preserved as single authentic literary chapters with internal '## I', '## II' headings,
        instead of being fragmented into tiny micro-chapters.
        """
        container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

        content_opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Anthology of the North</dc:title>
    <dc:creator>Test Author</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="story1" href="story1.xhtml" media-type="application/xhtml+xml"/>
    <item id="story2" href="story2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="story1"/>
    <itemref idref="story2"/>
  </spine>
</package>"""

        toc_ncx = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="np1" playOrder="1">
      <navLabel><text>THE BOUNDS OF REASON</text></navLabel>
      <content src="story1.xhtml"/>
      <navPoint id="np1_1" playOrder="2">
        <navLabel><text>I</text></navLabel>
        <content src="story1.xhtml#sec1"/>
      </navPoint>
      <navPoint id="np1_2" playOrder="3">
        <navLabel><text>II</text></navLabel>
        <content src="story1.xhtml#sec2"/>
      </navPoint>
      <navPoint id="np1_3" playOrder="4">
        <navLabel><text>III</text></navLabel>
        <content src="story1.xhtml#sec3"/>
      </navPoint>
    </navPoint>
    <navPoint id="np2" playOrder="5">
      <navLabel><text>A SHARD OF ICE</text></navLabel>
      <content src="story2.xhtml"/>
      <navPoint id="np2_1" playOrder="6">
        <navLabel><text>I</text></navLabel>
        <content src="story2.xhtml#sec1"/>
      </navPoint>
      <navPoint id="np2_2" playOrder="7">
        <navLabel><text>II</text></navLabel>
        <content src="story2.xhtml#sec2"/>
      </navPoint>
    </navPoint>
  </navMap>
</ncx>"""

        story1_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Story 1</title></head>
<body>
  <h1>THE BOUNDS OF REASON</h1>
  <div id="sec1">
    <h2>I</h2>
    <p>A cold wind blew across the northern docks as the armada gathered at dawn.</p>
    <p>Sailors hoisted heavy canvas sails preparing for the perilous crossing.</p>
  </div>
  <div id="sec2">
    <h2>II</h2>
    <p>By dusk the fleet had reached deep water far beyond the coastal shoals.</p>
    <p>Lookouts watched the horizon for signs of pursuing warships.</p>
  </div>
  <div id="sec3">
    <h2>III</h2>
    <p>The storm struck just before midnight with furious thunder and towering waves.</p>
    <p>Only the flagship held its course through the tempest into calm open waters.</p>
  </div>
</body>
</html>"""

        story2_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Story 2</title></head>
<body>
  <h1>A SHARD OF ICE</h1>
  <div id="sec1">
    <h2>I</h2>
    <p>Snow blanketed the jagged peaks as the scouting party climbed upward.</p>
    <p>The narrow path was treacherous beneath sheets of black ice.</p>
  </div>
  <div id="sec2">
    <h2>II</h2>
    <p>At the mountain crest they discovered the abandoned granite fortress.</p>
    <p>Warm fires were lit within the ancient hall as night settled over the ridge.</p>
  </div>
</body>
</html>"""

        with tempfile.TemporaryDirectory() as tmp_dir:
            epub_path = Path(tmp_dir) / "hierarchical_anthology.epub"
            with zipfile.ZipFile(epub_path, "w") as zf:
                zf.writestr("META-INF/container.xml", container_xml)
                zf.writestr("OEBPS/content.opf", content_opf)
                zf.writestr("OEBPS/toc.ncx", toc_ncx)
                zf.writestr("OEBPS/story1.xhtml", story1_xhtml)
                zf.writestr("OEBPS/story2.xhtml", story2_xhtml)

            parser = ForensicEPUBParser(epub_path)
            book, legacy_items = parser.parse()

            # 1. Exactly 2 authentic literary chapters created (NOT 5 micro-chapters)
            self.assertEqual(len(book.chapters), 2)
            self.assertEqual(book.chapters[0].title, "The Bounds Of Reason")
            self.assertEqual(book.chapters[1].title, "A Shard Of Ice")
            self.assertEqual(len(legacy_items), 2)

            # 2. Authentic literary chapter inspection
            lit_chaps = book.get_literary_chapters()
            self.assertEqual(len(lit_chaps), 2)
            self.assertEqual(lit_chaps[0].title, "The Bounds Of Reason")
            self.assertEqual(lit_chaps[1].title, "A Shard Of Ice")

            # 3. Intra-chapter section heading markdown projection
            md1 = book.chapters[0].to_markdown()
            self.assertIn("# The Bounds Of Reason", md1)
            self.assertIn("## I", md1)
            self.assertIn("## II", md1)
            self.assertIn("## III", md1)
            self.assertIn("A cold wind blew across the northern docks", md1)
            self.assertIn("The storm struck just before midnight", md1)

            md2 = book.chapters[1].to_markdown()
            self.assertIn("# A Shard Of Ice", md2)
            self.assertIn("## I", md2)
            self.assertIn("## II", md2)
            self.assertIn("Snow blanketed the jagged peaks", md2)
            self.assertIn("Warm fires were lit within the ancient hall", md2)

    def test_oversized_hierarchical_chapter_semantic_split(self):
        """
        Verify that an oversized authentic literary chapter (>12,000 words) with Roman numeral sub-sections
        is split cleanly into production chunks (Part 1, Part 2) by the Meso-tier chunker,
        while CanonicalBook.get_literary_chapters() reconstructs the single authentic literary chapter.
        """
        container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

        content_opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Oversized Epic</dc:title>
    <dc:creator>Epic Author</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="ch1" href="epic.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="ch1"/>
  </spine>
</package>"""

        toc_ncx = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="np1" playOrder="1">
      <navLabel><text>The Epic Chronicle</text></navLabel>
      <content src="epic.xhtml"/>
      <navPoint id="np1_1" playOrder="2">
        <navLabel><text>I</text></navLabel>
        <content src="epic.xhtml#sec1"/>
      </navPoint>
      <navPoint id="np1_2" playOrder="3">
        <navLabel><text>II</text></navLabel>
        <content src="epic.xhtml#sec2"/>
      </navPoint>
    </navPoint>
  </navMap>
</ncx>"""

        # Generate ~14,000 words: ~7,700 in section 1 and ~6,600 in section 2
        p_sec1 = " ".join(["The brave knight rode through the enchanted woodland looking for signs of danger."] * 700)
        p_sec2 = " ".join(["Deep inside the mountain caverns the ancient dragon slumbered amidst mountains of gold."] * 600)

        epic_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Epic</title></head>
<body>
  <h1>The Epic Chronicle</h1>
  <div id="sec1">
    <h2>I</h2>
    <p>{p_sec1}</p>
  </div>
  <div id="sec2">
    <h2>II</h2>
    <p>{p_sec2}</p>
  </div>
</body>
</html>"""

        with tempfile.TemporaryDirectory() as tmp_dir:
            epub_path = Path(tmp_dir) / "oversized_epic.epub"
            with zipfile.ZipFile(epub_path, "w") as zf:
                zf.writestr("META-INF/container.xml", container_xml)
                zf.writestr("OEBPS/content.opf", content_opf)
                zf.writestr("OEBPS/toc.ncx", toc_ncx)
                zf.writestr("OEBPS/epic.xhtml", epic_xhtml)

            parser = ForensicEPUBParser(epub_path)
            book, legacy_items = parser.parse()

            # Meso-tier 12k split should divide the 14k-word chapter into 2 production chunks
            self.assertEqual(len(book.chapters), 2)
            self.assertTrue(book.chapters[0].is_production_chunk)
            self.assertTrue(book.chapters[1].is_production_chunk)
            self.assertIn("(Part 1)", book.chapters[0].title)
            self.assertIn("(Part 2)", book.chapters[1].title)
            self.assertEqual(book.chapters[0].parent_chapter_title, "The Epic Chronicle")

            # get_literary_chapters() reconstructs the single authentic literary chapter
            lit_chaps = book.get_literary_chapters()
            self.assertEqual(len(lit_chaps), 1)
            self.assertEqual(lit_chaps[0].title, "The Epic Chronicle")
            self.assertTrue(lit_chaps[0].is_literary_chapter)
            self.assertFalse(lit_chaps[0].is_production_chunk)
            self.assertGreater(lit_chaps[0].words, 12000)

    def test_multi_chapter_same_spine_file_isolation(self):
        """
        Adversarial Test (Flaw 1 Fix):
        Verifies that multiple authentic chapters residing in the EXACT SAME spine file
        (e.g. index_split_000.html) are strictly partitioned by their exact anchors.
        Chapter 2 must NEVER reset match_idx backwards to Chapter 1's start block,
        which previously caused Chapter 1 to slice [5:5] (0 blocks) and disappear.
        """
        container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

        content_opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Single Spine Omnibus</dc:title>
    <dc:creator>Author</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="content" href="index_split_000.html" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="content"/>
  </spine>
</package>"""

        toc_ncx = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="np1" playOrder="1">
      <navLabel><text>First Saga</text></navLabel>
      <content src="index_split_000.html#story1"/>
      <navPoint id="np1_1" playOrder="2">
        <navLabel><text>I</text></navLabel>
        <content src="index_split_000.html#s1_sec1"/>
      </navPoint>
      <navPoint id="np1_2" playOrder="3">
        <navLabel><text>II</text></navLabel>
        <content src="index_split_000.html#s1_sec2"/>
      </navPoint>
    </navPoint>
    <navPoint id="np2" playOrder="4">
      <navLabel><text>Second Saga</text></navLabel>
      <content src="index_split_000.html#story2"/>
      <navPoint id="np2_1" playOrder="5">
        <navLabel><text>I</text></navLabel>
        <content src="index_split_000.html#s2_sec1"/>
      </navPoint>
      <navPoint id="np2_2" playOrder="6">
        <navLabel><text>II</text></navLabel>
        <content src="index_split_000.html#s2_sec2"/>
      </navPoint>
    </navPoint>
  </navMap>
</ncx>"""

        omnibus_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Omnibus</title></head>
<body>
  <div id="story1">
    <h1>FIRST SAGA</h1>
    <div id="s1_sec1">
      <p><b>I</b></p>
      <p>The dawn over the western frontier arrived with heavy obsidian clouds and bitter frost.</p>
      <p>Rangers kept watch along the ancient parapet as scouts returned from the valley.</p>
    </div>
    <div id="s1_sec2">
      <p><b>II</b></p>
      <p>By midday the merchant caravan reached the stone bridge across the swollen river.</p>
      <p>Guards inspected every wooden wagon before granting passage into the citadel.</p>
    </div>
  </div>
  <div id="story2">
    <h1>SECOND SAGA</h1>
    <div id="s2_sec1">
      <p><b>I</b></p>
      <p>Night descended upon the eastern desert with stillness that chilled the shifting dunes.</p>
      <p>Nomads tended flickering campfires beneath an expanse of brilliant desert stars.</p>
    </div>
    <div id="s2_sec2">
      <p><b>II</b></p>
      <p>The morning brought scouring sandstorms that erased the caravan tracks completely.</p>
      <p>Guides navigated by memory of buried granite milestones toward the sanctuary.</p>
    </div>
  </div>
</body>
</html>"""

        with tempfile.TemporaryDirectory() as tmp_dir:
            epub_path = Path(tmp_dir) / "same_spine_omnibus.epub"
            with zipfile.ZipFile(epub_path, "w") as zf:
                zf.writestr("META-INF/container.xml", container_xml)
                zf.writestr("OEBPS/content.opf", content_opf)
                zf.writestr("OEBPS/toc.ncx", toc_ncx)
                zf.writestr("OEBPS/index_split_000.html", omnibus_xhtml)

            parser = ForensicEPUBParser(epub_path)
            book, _ = parser.parse()

            # Both stories must be preserved (0 stories dropped)
            self.assertEqual(len(book.chapters), 2)
            self.assertEqual(book.chapters[0].title, "First Saga")
            self.assertEqual(book.chapters[1].title, "Second Saga")

            # Check that Story 1 was NOT dropped [5:5] (has substantial blocks and words)
            self.assertGreater(len(book.chapters[0].blocks), 2)
            self.assertGreater(book.chapters[0].words, 30)
            self.assertGreater(len(book.chapters[1].blocks), 2)
            self.assertGreater(book.chapters[1].words, 30)

            # Check content isolation (no bleeding or swallowing)
            md1 = book.chapters[0].to_markdown()
            self.assertIn("western frontier", md1)
            self.assertNotIn("eastern desert", md1)

            md2 = book.chapters[1].to_markdown()
            self.assertIn("eastern desert", md2)
            self.assertNotIn("western frontier", md2)

            # Gate verification
            self.assertEqual(book.quality_report.gate_status, "PASS")
            self.assertEqual(book.quality_report.detected_literary_chapters, 2)
            self.assertEqual(book.quality_report.expected_literary_targets, 2)

    def test_intra_chapter_roman_numerals_render_as_h2(self):
        """
        Adversarial Test (Flaw 2 Fix):
        Verifies that intra-chapter Roman numerals (I through X) are reliably
        formatted as heading level 2 (## I, ## II, ## III) in markdown projection,
        even when the EPUB TOC NCX does not explicitly declare sub-section anchors.
        """
        container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

        content_opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Roman Numerals Test</dc:title>
    <dc:creator>Author</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="story" href="story.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="story"/>
  </spine>
</package>"""

        # NCX only points to the main story, NO sub-section breaks declared in TOC!
        toc_ncx = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="np1" playOrder="1">
      <navLabel><text>The Iron Fortress</text></navLabel>
      <content src="story.xhtml#start"/>
    </navPoint>
  </navMap>
</ncx>"""

        story_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Story</title></head>
<body>
  <div id="start">
    <h1>THE IRON FORTRESS</h1>
    <p><b>I</b></p>
    <p>The gates swung wide to admit the returning vanguard into the courtyard.</p>
    <p><b>II</b></p>
    <p>Council convened in the great hall before the hearth fires waned.</p>
    <p><b>III</b></p>
    <p>By midnight a single messenger rode through the shadows toward the capital.</p>
  </div>
</body>
</html>"""

        with tempfile.TemporaryDirectory() as tmp_dir:
            epub_path = Path(tmp_dir) / "roman_num_test.epub"
            with zipfile.ZipFile(epub_path, "w") as zf:
                zf.writestr("META-INF/container.xml", container_xml)
                zf.writestr("OEBPS/content.opf", content_opf)
                zf.writestr("OEBPS/toc.ncx", toc_ncx)
                zf.writestr("OEBPS/story.xhtml", story_xhtml)

            parser = ForensicEPUBParser(epub_path)
            book, _ = parser.parse()

            self.assertEqual(len(book.chapters), 1)
            ch = book.chapters[0]
            md = ch.to_markdown()

            # Ensure all Roman numerals render as ## I, ## II, ## III
            self.assertIn("# The Iron Fortress", md)
            self.assertIn("## I", md)
            self.assertIn("## II", md)
            self.assertIn("## III", md)
            self.assertNotIn("\nI\n", md)
            self.assertNotIn("\nII\n", md)
            self.assertNotIn("\nIII\n", md)

    def test_fail_closed_quality_gate_on_zero_blocks_or_missing_targets(self):
        """
        Adversarial Test (Flaw 3 Fix):
        Verifies that ExtractionQualityAuditor enforces fail-closed gate semantics:
        1. When a resolved literary chapter target has 0 blocks or 0 words, flag CRITICAL_ERROR.
        2. When detected_literary_chapters < expected_literary_targets, flag CRITICAL_ERROR.
        Both must yield gate_status = "REVIEW" and raise ExtractionGateAuditError when force_gate=False.
        """
        from audiobook_factory.extraction.quality_gate import ExtractionQualityAuditor
        from audiobook_factory.extraction.contracts import (
            CanonicalBook,
            CanonicalChapter,
            CanonicalBlock,
            SourceProvenance,
            ExtractionGateAuditError,
        )

        prov = SourceProvenance(source_file="test.epub", source_type="epub")
        dummy_block = CanonicalBlock(
            id="b1",
            type="paragraph",
            raw_text="Valid content block with enough words for parsing.",
            normalized_text="Valid content block with enough words for parsing.",
            provenance=prov,
        )

        # Case 1: Chapter target with 0 blocks / 0 words
        ch1 = CanonicalChapter(
            id="c1",
            number=1,
            title="Empty Chapter Target",
            blocks=[],
            words=0,
            unit_type="literary_chapter",
            is_literary_chapter=True,
            boundary_origin="toc_navigation",
        )
        ch2 = CanonicalChapter(
            id="c2",
            number=2,
            title="Valid Chapter",
            blocks=[dummy_block],
            words=10,
            unit_type="literary_chapter",
            is_literary_chapter=True,
            boundary_origin="toc_navigation",
        )
        book1 = CanonicalBook(
            book_id="test_empty",
            title="Test Empty Target",
            source_type="epub",
            source_path="test.epub",
            chapters=[ch1, ch2],
        )

        with self.assertRaises(ExtractionGateAuditError) as ctx:
            ExtractionQualityAuditor.audit(book1, force_gate=False)
        self.assertEqual(ctx.exception.report.gate_status, "REVIEW")
        self.assertTrue(
            any("CRITICAL_ERROR" in e and "0 blocks or 0 words" in e for e in ctx.exception.report.errors)
        )

        # Case 2: detected_literary_chapters < expected_literary_targets
        book2 = CanonicalBook(
            book_id="test_missing_story",
            title="Test Missing Target",
            source_type="epub",
            source_path="test.epub",
            chapters=[ch2],  # only 1 detected chapter
            raw_metadata={"expected_literary_targets": 2},  # 2 were expected
        )
        with self.assertRaises(ExtractionGateAuditError) as ctx2:
            ExtractionQualityAuditor.audit(book2, force_gate=False)
        self.assertEqual(ctx2.exception.report.gate_status, "REVIEW")
        self.assertTrue(
            any("CRITICAL_ERROR" in e and "expected literary targets" in e for e in ctx2.exception.report.errors)
        )


if __name__ == "__main__":
    unittest.main()
