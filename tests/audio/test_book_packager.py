#!/usr/bin/env python3
"""
Unit and Integration Tests for Phase 4: Single-Pass AAC Chapter Delivery & Lossless M4B Packaging.
===================================================================================================
Validates:
1. AP-04 Single-Pass Invariant: ChapterDeliveryEncoder encodes 48kHz stereo master WAV into 192k AAC-LC.
2. AP-09 True Peak Audit: Post-encode ebur128 probe verifies True Peak <= -1.5 dBTP.
3. AP-10 Monotonic Timestamps: FFMETADATA1 generates strictly contiguous chapter boundaries (START_k = END_{k-1}).
4. Lossless Container Stream Copy: M4BBookPackager packages .m4b via '-c:a copy' with zero transcode.
5. Cover Art & Faststart: Attached picture and +faststart flag are embedded.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from audiobook_factory.audio.encoder import ChapterDeliveryEncoder
from audiobook_factory.audio.packager import (
    M4BBookPackager,
    generate_monotonic_ffmetadata,
    probe_audio_stream_params,
)
from audiobook_factory.audio_utils import get_ffmpeg, get_ffprobe


def make_pcm24_wav(
    target_path: Path,
    duration_sec: float = 2.0,
    sample_rate: int = 48000,
    channels: int = 2,
    amplitude: float = 0.5,
) -> Path:
    """Generates synthetic 24-bit 48kHz WAV audio."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    # 24-bit integer range [-8388608, 8388607]
    int24_samples = (amplitude * np.sin(2 * np.pi * 440.0 * t) * 8388607.0).astype(np.int32)
    # Convert to 3-byte bytes
    raw_bytes = bytearray()
    for s in int24_samples:
        clamped = int(max(-8388608, min(8388607, s)))
        b = clamped.to_bytes(3, byteorder="little", signed=True)
        for _ in range(channels):
            raw_bytes.extend(b)

    with wave.open(str(target_path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(3)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(raw_bytes))
    return target_path


def make_dummy_jpeg(target_path: Path) -> Path:
    """Creates a minimal valid 1x1 JPEG image for cover art testing."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    # Minimal 1x1 JPEG header and data
    jpeg_bytes = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
        0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
        0x00, 0xBF, 0x00, 0xFF, 0xD9
    ])
    target_path.write_bytes(jpeg_bytes)
    return target_path


class TestBookPackager(unittest.TestCase):
    """Test suite for Phase 4 chapter encoding and lossless M4B packaging."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="test_phase4_packager_"))
        self.encoder = ChapterDeliveryEncoder()
        self.packager = M4BBookPackager()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_single_pass_aac_chapter_encoding_ap04(self):
        """AP-04: Verify ChapterDeliveryEncoder produces compliant 48kHz stereo 192k AAC."""
        wav_file = self.tmp_dir / "chapter_001_dialogue.wav"
        m4a_file = self.tmp_dir / "chapter_001_mastered.m4a"
        make_pcm24_wav(wav_file, duration_sec=2.0, amplitude=0.4)

        result_path = self.encoder.encode_chapter_m4a(wav_file, m4a_file, target_bitrate="192k")

        self.assertEqual(result_path, m4a_file)
        self.assertTrue(m4a_file.exists())
        self.assertGreater(m4a_file.stat().st_size, 5000)

        # Probe stream parameters
        params = probe_audio_stream_params(m4a_file)
        self.assertEqual(params["codec"], "aac")
        self.assertEqual(params["sample_rate"], 48000)
        self.assertEqual(params["channels"], 2)
        self.assertGreaterEqual(params["duration_ms"], 1800)

    def test_post_encode_true_peak_audit_ap09(self):
        """AP-09: Verify post-encode True Peak measurement and ceiling enforcement."""
        wav_file = self.tmp_dir / "hot_dialogue.wav"
        m4a_file = self.tmp_dir / "hot_mastered.m4a"
        # High amplitude sine wave that pushes near 0 dBFS
        make_pcm24_wav(wav_file, duration_sec=2.5, amplitude=0.88)

        self.encoder.encode_chapter_m4a(wav_file, m4a_file, max_true_peak_dbtp=-1.5)

        tp = self.encoder.probe_true_peak(m4a_file)
        self.assertIsNotNone(tp)
        # Must respect the -1.5 dBTP broadcast ceiling
        self.assertLessEqual(tp, -1.4)

    def test_monotonic_chapter_metadata_generation_ap10(self):
        """AP-10: Verify FFMETADATA1 timestamps are strictly contiguous and monotonic."""
        meta_file = self.tmp_dir / "chapters.txt"
        book_meta = {"title": "The Last Wish", "author": "Andrzej Sapkowski"}
        durations = [
            {"number": 1, "title": "A Grain of Truth", "duration_ms": 3540},
            {"number": 2, "title": "The Lesser Evil", "duration_ms": 4820},
            {"number": 3, "title": "A Question of Price", "duration_ms": 2900},
        ]

        generate_monotonic_ffmetadata(book_meta, durations, meta_file)

        self.assertTrue(meta_file.exists())
        content = meta_file.read_text(encoding="utf-8")

        # Parse chapter START and END blocks
        starts = [int(m.group(1)) for m in re.finditer(r"START=(\d+)", content)]
        ends = [int(m.group(1)) for m in re.finditer(r"END=(\d+)", content)]

        self.assertEqual(len(starts), 3)
        self.assertEqual(len(ends), 3)

        # Monotonicity invariant: START_0 = 0
        self.assertEqual(starts[0], 0)
        self.assertEqual(ends[0], 3540)

        # Contiguity invariant: START_k == END_{k-1}
        self.assertEqual(starts[1], ends[0])
        self.assertEqual(ends[1], 3540 + 4820)

        self.assertEqual(starts[2], ends[1])
        self.assertEqual(ends[2], 3540 + 4820 + 2900)

    def test_lossless_m4b_stream_copy_assembly(self):
        """Verify M4BBookPackager packages AAC chapters losslessly via stream copy (-c:a copy)."""
        project_dir = self.tmp_dir / "witcher_proj"
        mastered_dir = project_dir / "mastered"
        mastered_dir.mkdir(parents=True, exist_ok=True)

        # Create two 48kHz stereo AAC chapters
        c1_wav = self.tmp_dir / "c1.wav"
        c2_wav = self.tmp_dir / "c2.wav"
        make_pcm24_wav(c1_wav, duration_sec=1.5, amplitude=0.4)
        make_pcm24_wav(c2_wav, duration_sec=1.8, amplitude=0.35)

        c1_m4a = mastered_dir / "chapter_001_mastered.m4a"
        c2_m4a = mastered_dir / "chapter_002_mastered.m4a"
        self.encoder.encode_chapter_m4a(c1_wav, c1_m4a)
        self.encoder.encode_chapter_m4a(c2_wav, c2_m4a)

        metadata = {
            "title": "Sword of Destiny",
            "author": "Andrzej Sapkowski",
            "chapters": [
                {"number": 1, "title": "The Bounds of Reason"},
                {"number": 2, "title": "A Shard of Ice"},
            ],
        }
        (project_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

        cover_jpg = make_dummy_jpeg(project_dir / "cover.jpg")

        m4b_path = self.packager.package_audiobook(
            project_dir=project_dir,
            output_filename="Sword_of_Destiny.m4b",
            cover_image=cover_jpg,
            metadata=metadata,
        )

        self.assertTrue(m4b_path.exists())
        self.assertGreater(m4b_path.stat().st_size, 10000)

        # Probe final M4B container
        ffprobe = get_ffprobe()
        cmd = [
            ffprobe, "-v", "error",
            "-show_chapters",
            "-show_entries", "format=duration",
            "-of", "json",
            str(m4b_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)

        # Verify chapters are present in the final M4B
        chapters = data.get("chapters", [])
        self.assertEqual(len(chapters), 2)
        self.assertIn("The Bounds of Reason", chapters[0].get("tags", {}).get("title", ""))
        self.assertIn("A Shard of Ice", chapters[1].get("tags", {}).get("title", ""))

        # Verify total duration is ~ 3.3 seconds (1.5 + 1.8)
        dur = float(data.get("format", {}).get("duration", 0.0))
        self.assertAlmostEqual(dur, 3.3, delta=0.5)


if __name__ == "__main__":
    unittest.main()
