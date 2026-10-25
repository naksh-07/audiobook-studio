#!/usr/bin/env python3
"""
Unit and Integration Tests for Phase 1: Foundation C++ JUCE DSP Engine (dsp.py).
================================================================================
Validates:
1. DSPConfig and DSPMasteringResult Pydantic v2 data contract integrity and bounding.
2. VocalDSPProcessor initialization, runtime capability probing, and graceful fallback.
3. Accurate loudness measurement (Integrated LUFS, dBTP, LRA).
4. End-to-end chapter mastering producing valid 48kHz 24-bit stereo PCM WAV deliverables.
5. True Peak compliance (<= -1.5 dBTP) and seamless integration with MasteringEngineV2.
"""

import shutil
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from audiobook_factory.audio.contracts import DSPConfig, DSPMasteringResult
from audiobook_factory.audio.dsp import (
    VocalDSPProcessor,
    has_pedalboard_engine,
    has_pyloudnorm_engine,
)
from audiobook_factory.mastering_contracts import MasteringProfile, MasteringRequest
from audiobook_factory.mastering_engine import MasteringEngineV2


def make_synthetic_speech_wav(
    target_path: Path,
    duration_sec: float = 1.5,
    sample_rate: int = 48000,
    amplitude: float = 0.6,
) -> Path:
    """Generates synthetic harmonic test audio mimicking vocal speech fundamentals."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    # Vocal fundamental (220 Hz) + Formants (440 Hz, 880 Hz, 3200 Hz)
    vocal = (
        0.5 * np.sin(2 * np.pi * 220.0 * t)
        + 0.3 * np.sin(2 * np.pi * 440.0 * t)
        + 0.15 * np.sin(2 * np.pi * 880.0 * t)
        + 0.05 * np.sin(2 * np.pi * 3200.0 * t)
    )
    vocal = vocal / np.max(np.abs(vocal)) * amplitude
    data = (vocal * 32767.0).astype(np.int16)
    stereo_data = np.column_stack((data, data)).flatten()

    with wave.open(str(target_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(stereo_data.tobytes())
    return target_path


class TestAudioDSPProcessor(unittest.TestCase):
    """Test suite for VocalDSPProcessor and C++ JUCE DSP mastering."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="test_audio_dsp_"))
        self.dsp = VocalDSPProcessor()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_dsp_config_contract_validation(self):
        """Validates DSPConfig default parameters and constraints."""
        cfg = DSPConfig()
        self.assertTrue(cfg.enable_pedalboard)
        self.assertEqual(cfg.subsonic_hz, 75.0)
        self.assertEqual(cfg.boxiness_cut_hz, 320.0)
        self.assertEqual(cfg.boxiness_cut_db, -1.0)
        self.assertEqual(cfg.presence_lift_hz, 3200.0)
        self.assertEqual(cfg.presence_lift_db, 0.8)
        self.assertEqual(cfg.target_lufs, -19.0)
        self.assertEqual(cfg.true_peak_ceiling_dbtp, -1.5)

    def test_runtime_capability_probing(self):
        """Verifies runtime probe returns boolean without throwing exceptions."""
        has_pb = has_pedalboard_engine()
        has_pl = has_pyloudnorm_engine()
        self.assertIsInstance(has_pb, bool)
        self.assertIsInstance(has_pl, bool)
        self.assertIsInstance(self.dsp.is_hardware_accelerated, bool)

    def test_measure_loudness_accuracy(self):
        """Verifies loudness measurement on synthetic signal."""
        t = np.linspace(0, 1.0, 48000, endpoint=False)
        sig = (0.5 * np.sin(2 * np.pi * 1000.0 * t)).astype(np.float32)
        stereo_sig = np.column_stack((sig, sig))

        lufs, tp, lra = self.dsp.measure_loudness(stereo_sig, sr=48000)
        self.assertIsInstance(lufs, float)
        self.assertIsInstance(tp, float)
        self.assertIsInstance(lra, float)
        # Peak of 0.5 amplitude corresponds to -6.02 dBTP
        self.assertAlmostEqual(tp, -6.02, delta=0.5)

    def test_sample_processing_preserves_shape(self):
        """Verifies process_samples preserves array shape and clean values."""
        samples = np.random.uniform(-0.5, 0.5, (48000, 2)).astype(np.float32)
        out = self.dsp.process_samples(samples, sr=48000)
        self.assertEqual(out.shape, samples.shape)
        self.assertFalse(np.isnan(out).any())
        self.assertFalse(np.isinf(out).any())

    def test_master_chapter_end_to_end(self):
        """Verifies end-to-end master_chapter producing 48kHz 24-bit WAV deliverable."""
        input_wav = self.tmp_dir / "premaster_input.wav"
        output_wav = self.tmp_dir / "chapter_master.wav"
        make_synthetic_speech_wav(input_wav, duration_sec=2.0)

        result = self.dsp.master_chapter(
            input_wav=input_wav,
            output_wav=output_wav,
            dsp_config=DSPConfig(target_lufs=-19.0, true_peak_ceiling_dbtp=-1.5),
        )

        self.assertIsInstance(result, DSPMasteringResult)
        self.assertTrue(output_wav.exists())
        self.assertIn(result.backend_used, ["pedalboard_juce_v2", "ffmpeg_dual_pass_linear"])

        # Validate master audio format
        with wave.open(str(output_wav), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 2)
            self.assertEqual(wf.getsampwidth(), 3)  # 24-bit PCM
            self.assertEqual(wf.getframerate(), 48000)
            frames = wf.getnframes()
            self.assertGreater(frames, 0)

        # True Peak ceiling verification
        self.assertLessEqual(result.true_peak_dbtp, -1.4)

    def test_mastering_engine_v2_integration(self):
        """Verifies MasteringEngineV2 seamlessly integrates with VocalDSPProcessor."""
        engine = MasteringEngineV2(dsp_processor=self.dsp)
        self.assertIsNotNone(engine.dsp)

        input_wav = self.tmp_dir / "engine_input.wav"
        output_wav = self.tmp_dir / "engine_master.wav"
        make_synthetic_speech_wav(input_wav, duration_sec=2.0)

        req = MasteringRequest(
            premaster_path=str(input_wav),
            chapter_id="chapter_001",
            output_master_path=str(output_wav),
            profile=MasteringProfile(target_lufs=-19.0, true_peak_ceiling_dbtp=-1.5),
        )
        res = engine.master(req)

        self.assertEqual(res.status, "SUCCESS")
        self.assertTrue(output_wav.exists())
        self.assertLessEqual(res.analysis_after.true_peak_dbtp, -1.4)


if __name__ == "__main__":
    unittest.main()
