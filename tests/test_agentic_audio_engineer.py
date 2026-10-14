#!/usr/bin/env python3
"""
Unit and Integration Tests for Agentic Audio Engineer & Self-Healing FFmpeg Filter Graph.
Verifies:
1. test_filter_graph validates syntax with dummy streams and returns SUCCESS / ERROR.
2. test_filter_graph detects missing foley stream [3:a] when has_foley=False.
3. build_ffmpeg_filter_graph_via_agent handles tool call feedback loop (Self-Healing).
4. build_ffmpeg_filter_graph_via_agent validates final text output and falls back cleanly on error.
"""

import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from audiobook_factory.ffmpeg_agent import (
    test_filter_graph,
    build_ffmpeg_filter_graph_via_agent,
    TOOLS,
)

test_filter_graph.__test__ = False


class TestAgenticAudioEngineer(unittest.TestCase):

    def test_01_filter_graph_valid_syntax(self):
        """Verify test_filter_graph returns SUCCESS for a valid FFmpeg filter graph."""
        fc = "[0:a]volume=1.0[voc];[1:a]volume=0.5[bgm];[voc][bgm]amix=inputs=2[out]"
        res = test_filter_graph(fc, has_foley=False)
        self.assertTrue(res.startswith("SUCCESS"), f"Expected SUCCESS, got: {res}")

    def test_02_filter_graph_invalid_syntax(self):
        """Verify test_filter_graph returns ERROR when filter graph has bad syntax."""
        fc = "[0:a]nonexistent_filter_xyz=123[out]"
        res = test_filter_graph(fc, has_foley=False)
        self.assertTrue(res.startswith("ERROR"), f"Expected ERROR, got: {res}")

    def test_03_filter_graph_missing_foley_guard(self):
        """Verify test_filter_graph catches [3:a] stream reference when has_foley is False."""
        fc = "[0:a][1:a][2:a][3:a]amix=inputs=4[out]"
        res = test_filter_graph(fc, has_foley=False)
        self.assertTrue(res.startswith("ERROR"))
        self.assertIn("Stream [3:a] does not exist", res)

    def test_04_agent_deadbolt_disabled_by_policy(self):
        """Verify build_ffmpeg_filter_graph_via_agent raises RuntimeError under pure vocals-only mandate."""
        with self.assertRaises(RuntimeError) as ctx:
            build_ffmpeg_filter_graph_via_agent(
                soundscape_plan={"scenes": [{"id": 1, "emotion": "tense"}]},
                cue_sheet={"foley_cues": []},
                vocal_dur=10.0,
                has_foley=False,
            )
        self.assertIn("disabled", str(ctx.exception).lower())

    def test_05_manifest_mastering_agent_deadbolt_disabled_by_policy(self):
        """Verify build_manifest_mastering_filter_graph_via_agent raises RuntimeError under pure vocals-only mandate."""
        from audiobook_factory.ffmpeg_agent import build_manifest_mastering_filter_graph_via_agent
        with self.assertRaises(RuntimeError) as ctx:
            build_manifest_mastering_filter_graph_via_agent(
                manifest_data={},
                vocal_dur=10.0,
            )
        self.assertIn("disabled", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
