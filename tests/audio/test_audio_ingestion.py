#!/usr/bin/env python3
"""
Unit and Integration Tests for Tier A Audio Ingestion & Normalization Engine (Phase 1).
Validates:
1. Sample rate standardization (24kHz Mono -> 48kHz Stereo).
2. Bit depth resolution (24-bit and 16-bit uncompressed PCM).
3. The Single 5.0ms Hann Micro-Taper invariant (zero-boundary sample pinning).
4. C2PA digital watermark static elimination.
5. Subsonic 30Hz highpass DC bias rejection.
6. Ingestion idempotency and cryptographic SHA-256 integrity.
"""

import io
import math
import wave
import struct
import shutil
import tempfile
import unittest
import numpy as np
from pathlib import Path

from audiobook_factory.audio.contracts import (
    SegmentAudioContract,
    IngestionConfig,
)
from audiobook_factory.audio.ingestion import AudioIngestionManager


def create_synthetic_wav(
    file_path: Path,
    duration_sec: float = 1.0,
    sample_rate: int = 24000,
    frequency_hz: float = 440.0,
    channels: int = 1,
    dc_offset: float = 0.0,
    append_c2pa_garbage: bool = False,
) -> Path:
    """Helper to synthesize uncompressed 16-bit test WAV files with optional C2PA tail."""
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    sine = (0.5 * np.sin(2.0 * np.pi * frequency_hz * t) + dc_offset).astype(np.float32)
    int16_samples = np.clip(np.round(sine * 32767.0), -32768, 32767).astype(np.int16)

    if channels == 2:
        stereo_samples = np.column_stack((int16_samples, int16_samples)).flatten()
        raw_pcm = stereo_samples.tobytes()
    else:
        raw_pcm = int16_samples.tobytes()

    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(raw_pcm)

    wav_bytes = bio.getvalue()
    if append_c2pa_garbage:
        # Simulate 6,020 bytes of trailing C2PA digital watermark static
        c2pa_static = b"C2PA_WATERMARK_DATA" + bytes([i % 256 for i in range(6001)])
        wav_bytes += c2pa_static

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(wav_bytes)
    return file_path


class TestAudioIngestionManager(unittest.TestCase):
    """Test suite for Tier A Audio Ingestion Engine."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.td.name)
        self.config = IngestionConfig(
            target_sample_rate=48000,
            target_channels=2,
            target_bit_depth=24,
            highpass_hz=30,
            micro_taper_ms=5.0,
        )
        self.manager = AudioIngestionManager(config=self.config, project_dir=self.tmp_dir)

    def tearDown(self):
        self.td.cleanup()

    def test_ingest_synthetic_pcm_standardization(self):
        """Verifies 24kHz mono input is standardized to 48kHz 24-bit stereo."""
        src_wav = self.tmp_dir / "raw_tts_24k_mono.wav"
        create_synthetic_wav(src_wav, duration_sec=1.5, sample_rate=24000, channels=1)

        contract = self.manager.ingest_segment(
            source=src_wav,
            chapter_id=1,
            segment_index=1,
            speaker="Narrator",
            voice_name="Aoede",
            literary_text="The morning mist was cold.",
        )

        # 1. Verify Contract Specifications
        self.assertIsInstance(contract, SegmentAudioContract)
        self.assertEqual(contract.chapter_id, 1)
        self.assertEqual(contract.segment_index, 1)
        self.assertEqual(contract.sample_rate, 48000)
        self.assertEqual(contract.channels, 2)
        self.assertEqual(contract.bit_depth, 24)
        self.assertAlmostEqual(contract.duration_ms, 1500, delta=15)
        self.assertTrue(contract.audio_path.exists())

        # 2. Inspect physical WAV header on disk
        with wave.open(str(contract.audio_path), "rb") as wf:
            self.assertEqual(wf.getframerate(), 48000)
            self.assertEqual(wf.getnchannels(), 2)
            self.assertEqual(wf.getsampwidth(), 3)  # 24-bit = 3 bytes
            self.assertEqual(wf.getnframes(), int(48000 * 1.5))

    def test_single_hann_micro_taper_zero_boundary(self):
        """Verifies the Single 5.0ms Hann Micro-Taper pins boundary samples strictly to 0.0."""
        src_wav = self.tmp_dir / "step_discontinuity.wav"
        # Start immediately at full scale (0.9 amplitude) without natural fade
        create_synthetic_wav(src_wav, duration_sec=0.5, sample_rate=24000, channels=1)

        contract = self.manager.ingest_segment(
            source=src_wav,
            chapter_id=2,
            segment_index=5,
            speaker="Geralt",
            voice_name="Fenrir",
            literary_text="Halt!",
        )

        with wave.open(str(contract.audio_path), "rb") as wf:
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        # Unpack 24-bit PCM
        raw_arr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        padded = np.pad(raw_arr, ((0, 0), (1, 0)), mode="constant", constant_values=0)
        samples = (padded.view("<i4").flatten() >> 8).astype(np.float32) / 8388607.0
        stereo_samples = samples.reshape(-1, 2)

        # First and last sample strictly zero
        self.assertAlmostEqual(stereo_samples[0, 0], 0.0, places=5)
        self.assertAlmostEqual(stereo_samples[0, 1], 0.0, places=5)
        self.assertAlmostEqual(stereo_samples[-1, 0], 0.0, places=5)
        self.assertAlmostEqual(stereo_samples[-1, 1], 0.0, places=5)

        # Smooth curve across 5ms window (240 samples at 48kHz)
        taper_len = int(48000 * (5.0 / 1000.0))
        self.assertLess(abs(stereo_samples[1, 0]), abs(stereo_samples[taper_len, 0]))

    def test_c2pa_watermark_static_elimination(self):
        """Verifies trailing 6,020-byte C2PA metadata static is completely stripped."""
        src_wav = self.tmp_dir / "gemini_with_c2pa.wav"
        create_synthetic_wav(src_wav, duration_sec=1.0, sample_rate=24000, append_c2pa_garbage=True)

        contract = self.manager.ingest_segment(
            source=src_wav,
            chapter_id=3,
            segment_index=12,
            speaker="Yennefer",
            voice_name="Kore",
            literary_text="Magic is chaos and order.",
        )

        # Duration must strictly reflect 1.0 second, not bloated by C2PA tail
        self.assertAlmostEqual(contract.duration_ms, 1000, delta=20)

    def test_dc_bias_highpass_filtering(self):
        """Verifies 30Hz highpass filter rejects DC bias offset."""
        src_wav = self.tmp_dir / "dc_drift.wav"
        # Injected heavy DC offset (+0.30)
        create_synthetic_wav(src_wav, duration_sec=1.0, sample_rate=24000, dc_offset=0.30)

        contract = self.manager.ingest_segment(
            source=src_wav,
            chapter_id=4,
            segment_index=1,
            speaker="Narrator",
            voice_name="Aoede",
        )

        with wave.open(str(contract.audio_path), "rb") as wf:
            raw = wf.readframes(wf.getnframes())

        raw_arr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        padded = np.pad(raw_arr, ((0, 0), (1, 0)), mode="constant", constant_values=0)
        samples = (padded.view("<i4").flatten() >> 8).astype(np.float32) / 8388607.0

        # Mean offset after 30Hz highpass should be near 0.0 (DC rejected)
        mean_dc = float(np.mean(samples[int(48000 * 0.1):]))
        self.assertLess(abs(mean_dc), 0.02)

    def test_16bit_configuration_mode(self):
        """Verifies IngestionConfig supports 16-bit PCM output when requested."""
        cfg16 = IngestionConfig(target_sample_rate=48000, target_channels=2, target_bit_depth=16)
        mgr16 = AudioIngestionManager(config=cfg16, project_dir=self.tmp_dir)

        src_wav = self.tmp_dir / "test_16b.wav"
        create_synthetic_wav(src_wav, duration_sec=0.5, sample_rate=24000)

        contract = mgr16.ingest_segment(
            source=src_wav,
            chapter_id=5,
            segment_index=1,
            speaker="Narrator",
            voice_name="Aoede",
        )

        self.assertEqual(contract.bit_depth, 16)
        with wave.open(str(contract.audio_path), "rb") as wf:
            self.assertEqual(wf.getsampwidth(), 2)  # 16-bit = 2 bytes

    def test_ingestion_idempotency_and_hash(self):
        """Verifies identical inputs produce identical cryptographic SHA-256 hashes."""
        src_wav = self.tmp_dir / "idempotent.wav"
        create_synthetic_wav(src_wav, duration_sec=0.8, sample_rate=24000)

        c1 = self.manager.ingest_segment(
            source=src_wav,
            chapter_id=1,
            segment_index=99,
            speaker="Narrator",
            voice_name="Aoede",
            segment_uid="uid_fixed_001",
        )
        c2 = self.manager.ingest_segment(
            source=src_wav,
            chapter_id=1,
            segment_index=99,
            speaker="Narrator",
            voice_name="Aoede",
            segment_uid="uid_fixed_001",
        )

        self.assertEqual(c1.audio_sha256, c2.audio_sha256)
        self.assertEqual(c1.duration_ms, c2.duration_ms)


if __name__ == "__main__":
    unittest.main()
