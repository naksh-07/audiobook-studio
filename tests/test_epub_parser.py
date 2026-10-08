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
            self.assertNotIn("A dusty ledger was found", act2_text)


if __name__ == "__main__":
    unittest.main()
