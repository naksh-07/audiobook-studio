#!/usr/bin/env python3
"""
Unit and Integration Tests for Hierarchical EPUB Navigation,
Frontmatter/Marketing Filtering, and Lead Heading Deduplication (Pillar 1 Refinement).
"""

import tempfile
import zipfile
import unittest
from pathlib import Path

from audiobook_factory.extraction.parsers.epub import ForensicEPUBParser
from audiobook_factory.extraction.engine import ExtractionEngine
from audiobook_factory.extraction.contracts import CanonicalBook


def create_hierarchical_multi_story_epub(epub_path: Path) -> Path:
    """Creates a synthetic EPUB with multi-part stories, subchapters, and commercial frontmatter."""
    container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

    content_opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Tales of Destiny</dc:title>
    <dc:creator>Master Storyteller</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="front" href="front.xhtml" media-type="application/xhtml+xml"/>
    <item id="story1" href="story1.xhtml" media-type="application/xhtml+xml"/>
    <item id="story2" href="story2.xhtml" media-type="application/xhtml+xml"/>
    <item id="back" href="back.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="front"/>
    <itemref idref="story1"/>
    <itemref idref="story2"/>
    <itemref idref="back"/>
  </spine>
</package>"""

    toc_ncx = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="np1" playOrder="1">
      <navLabel><text>TITLE PAGE</text></navLabel>
      <content src="front.xhtml#title_page"/>
    </navPoint>
    <navPoint id="np2" playOrder="2">
      <navLabel><text>WELCOME</text></navLabel>
      <content src="front.xhtml#welcome"/>
    </navPoint>
    <navPoint id="np3" playOrder="3">
      <navLabel><text>THE ANCIENT MOUNTAIN</text></navLabel>
      <content src="story1.xhtml#story1_start"/>
      <navPoint id="np4" playOrder="3">
        <navLabel><text>I</text></navLabel>
        <content src="story1.xhtml#story1_start"/>
      </navPoint>
      <navPoint id="np5" playOrder="4">
        <navLabel><text>II</text></navLabel>
        <content src="story1.xhtml#story1_part2"/>
      </navPoint>
    </navPoint>
    <navPoint id="np6" playOrder="5">
      <navLabel><text>THE FROZEN SHORE</text></navLabel>
      <content src="story2.xhtml#story2_start"/>
      <navPoint id="np7" playOrder="5">
        <navLabel><text>I</text></navLabel>
        <content src="story2.xhtml#story2_start"/>
      </navPoint>
      <navPoint id="np8" playOrder="6">
        <navLabel><text>II</text></navLabel>
        <content src="story2.xhtml#story2_part2"/>
      </navPoint>
    </navPoint>
    <navPoint id="np9" playOrder="7">
      <navLabel><text>ORBIT NEWSLETTER</text></navLabel>
      <content src="back.xhtml#newsletter"/>
    </navPoint>
    <navPoint id="np10" playOrder="8">
      <navLabel><text>ALSO BY THE AUTHOR</text></navLabel>
      <content src="back.xhtml#also_by"/>
    </navPoint>
  </navMap>
</ncx>"""

    front_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
  <div id="title_page">
    <p><b>Tales of Destiny</b></p>
    <p>Published by Fantasy House orbitbooks.net</p>
  </div>
  <div id="welcome">
    <p>Begin reading now. In accordance with piracy laws do not copy.</p>
  </div>
</body>
</html>"""

    story1_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
  <div id="story1_start">
    <p><b>THE ANCIENT MOUNTAIN</b></p>
    <p><b>I</b></p>
    <p>He will not emerge from that cavern alive, the innkeeper warned solemnly.</p>
    <p>The traveler adjusted his leather pack without a word and stared toward the mist-shrouded gorge.</p>
  </div>
  <div id="story1_part2">
    <p><b>II</b></p>
    <p>The dawn brought cold northern rain sweeping over the high timber palisade.</p>
    <p>Horses stamped their iron-shod hooves against the muddy courtyard stones.</p>
  </div>
</body>
</html>"""

    story2_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
  <div id="story2_start">
    <p><b>THE FROZEN SHORE</b></p>
    <p><b>I</b></p>
    <p>Snow fell quietly over the silent roofs of the harbor town.</p>
    <p>The astronomer looked up from her glass with eyes as calm as midnight.</p>
  </div>
  <div id="story2_part2">
    <p><b>II</b></p>
    <p>The journey was set for the hour before noon beside the ancient stone gate.</p>
    <p>A circle of solemn villagers gathered along the frosted cobblestones.</p>
  </div>
</body>
</html>"""

    back_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
  <div id="newsletter">
    <p>Sign up for our newsletter at publisher.com to receive updates and discounts.</p>
  </div>
  <div id="also_by">
    <p>Also by the author: The Previous Quest, The Lost Realm, The Final Battle.</p>
  </div>
</body>
</html>"""

    with zipfile.ZipFile(epub_path, "w") as zf:
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OEBPS/content.opf", content_opf)
        zf.writestr("OEBPS/toc.ncx", toc_ncx)
        zf.writestr("OEBPS/front.xhtml", front_xhtml)
        zf.writestr("OEBPS/story1.xhtml", story1_xhtml)
        zf.writestr("OEBPS/story2.xhtml", story2_xhtml)
        zf.writestr("OEBPS/back.xhtml", back_xhtml)

    return epub_path


class TestHierarchicalEPUBExtraction(unittest.TestCase):

    def test_hierarchical_multi_story_resolution_and_filtering(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            epub_path = Path(tmp_dir) / "Tales of Destiny [Worldfreebooks.com].epub"
            create_hierarchical_multi_story_epub(epub_path)

            out_dir = Path(tmp_dir) / "projects"
            book = ExtractionEngine.extract(epub_path, out_dir)

            # 1. Verify clean slug derivation (watermark stripped)
            self.assertEqual(book.book_id, "tales_of_destiny")

            # 2. Verify all marketing/frontmatter chapters are pruned
            self.assertEqual(len(book.chapters), 4)

            # 3. Verify hierarchical titling and parent linkages
            ch1, ch2, ch3, ch4 = book.chapters
            self.assertEqual(ch1.title, "The Ancient Mountain - Part I")
            self.assertEqual(ch1.parent_chapter_title, "The Ancient Mountain")
            self.assertEqual(ch1.boundary_origin, "toc_navigation")

            self.assertEqual(ch2.title, "The Ancient Mountain - Part II")
            self.assertEqual(ch2.parent_chapter_title, "The Ancient Mountain")

            self.assertEqual(ch3.title, "The Frozen Shore - Part I")
            self.assertEqual(ch3.parent_chapter_title, "The Frozen Shore")

            self.assertEqual(ch4.title, "The Frozen Shore - Part II")
            self.assertEqual(ch4.parent_chapter_title, "The Frozen Shore")

            # 4. Verify heading deduplication in Markdown projection (zero title stuttering)
            ch1_md = ch1.to_markdown()
            lines = [line.strip() for line in ch1_md.splitlines() if line.strip()]
            self.assertEqual(lines[0], "# The Ancient Mountain - Part I")
            # First narrative line must be the actual author prose, NOT duplicate "THE ANCIENT MOUNTAIN" or "I"
            self.assertIn("He will not emerge from that cavern alive", lines[1])
            self.assertNotIn("\nI\n", ch1_md)


if __name__ == "__main__":
    unittest.main()
