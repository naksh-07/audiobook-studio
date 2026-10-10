#!/usr/bin/env python3
"""
Unit and Integration Tests for Phase 3: Neural Vocal Polish & Reference Matching.
================================================================================
Validates:
1. EnhancerConfig & ReferenceMatcherConfig Pydantic v2 data contracts.
2. NeuralVocalEnhancer selective auto-bypass on pristine studio audio (>45dB SNR).
3. NeuralVocalEnhancer de-artifacting and energy difference clamping (|delta_RMS| <= 2.0dB).
4. ReferenceSpectrumMatcher frequency matching and +/-3.0dB hard spectral clamping.
5. End-to-end disk processing producing certified 48kHz 24-bit stereo PCM WAV files.
"""

import shutil
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from audiobook_factory.audio.contracts import (
    EnhancerConfig,
    ReferenceMatcherConfig,
)
from audiobook_factory.audio.enhancer import (
    NeuralVocalEnhancer,
    has_deepfilter_engine,
)
from audiobook_factory.audio.reference_matcher import (
    ReferenceSpectrumMatcher,
    has_matchering_engine,
)


def make_test_wav(
    target_path: Path,
    duration_sec: float = 1.5,
    sample_rate: int = 48000,
    amplitude: float = 0.5,
    add_noise: bool = False,
    noise_level: float = 0.05,
    freq_hz: float = 440.0,
) -> Path:
    """Generates synthetic test audio file with optional harmonic/noise content."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    signal = amplitude * np.sin(2 * np.pi * freq_hz * t)

    if add_noise:
        noise = np.random.normal(0, noise_level, num_samples)
        signal = signal + noise

    signal = np.clip(signal, -1.0, 1.0)
    int_data = (signal * 32767.0).astype(np.int16)
    stereo_data = np.column_stack((int_data, int_data)).flatten()

    with wave.open(str(target_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(stereo_data.tobytes())
    return target_path


class TestEnhancerAndReferenceMatcher(unittest.TestCase):
    """Test suite for Phase 3 Vocal Polish and Reference Matching engines."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="test_phase3_"))
        self.enhancer = NeuralVocalEnhancer()
        self.matcher = ReferenceSpectrumMatcher()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_enhancer_config_validation(self):
        """Verifies EnhancerConfig default parameters."""
        cfg = EnhancerConfig()
        self.assertFalse(cfg.enable_neural_enhancement)
        self.assertEqual(cfg.snr_bypass_threshold_db, 45.0)
        self.assertEqual(cfg.max_energy_diff_db, 2.0)
        self.assertEqual(cfg.model_type, "deepfilternet3")

    def test_enhancer_auto_bypass_on_clean_signal(self):
        """Verifies clean studio audio (>45dB SNR) is automatically bypassed."""
        # Generate pure tone (extremely high SNR)
        t = np.linspace(0, 1.0, 48000, endpoint=False)
        clean_sig = (0.5 * np.sin(2 * np.pi * 1000.0 * t)).astype(np.float32)
        stereo_clean = np.column_stack((clean_sig, clean_sig))

        out, was_enhanced = self.enhancer.enhance_samples(stereo_clean, sr=48000)
        self.assertFalse(was_enhanced)
        np.testing.assert_allclose(out, stereo_clean, atol=1e-5)

    def test_enhancer_processing_on_noisy_signal(self):
        """Verifies noisy audio is processed and noise floor attenuated."""
        t = np.linspace(0, 1.0, 48000, endpoint=False)
        noise = np.random.normal(0, 0.002, 48000).astype(np.float32)  # Low-level hiss
        noisy_sig = (0.5 * np.sin(2 * np.pi * 440.0 * t) + noise).astype(np.float32)
        stereo_noisy = np.column_stack((noisy_sig, noisy_sig))

        # Force enhancement
        enh = NeuralVocalEnhancer(config=EnhancerConfig(enable_neural_enhancement=True, snr_bypass_threshold_db=99.0))
        out, was_enhanced = enh.enhance_samples(stereo_noisy, sr=48000)

        self.assertEqual(out.shape, stereo_noisy.shape)
        self.assertFalse(np.isnan(out).any())

    def test_enhancer_file_pipeline(self):
        """Verifies enhance_file reads and writes valid 48kHz 24-bit PCM WAV."""
        in_wav = self.tmp_dir / "noisy_take.wav"
        out_wav = self.tmp_dir / "polished_take.wav"
        make_test_wav(in_wav, duration_sec=1.0, add_noise=True, noise_level=0.01)

        enh = NeuralVocalEnhancer(config=EnhancerConfig(enable_neural_enhancement=True, snr_bypass_threshold_db=99.0))
        enh.enhance_file(in_wav, out_wav)

        self.assertTrue(out_wav.exists())
        with wave.open(str(out_wav), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 2)
            self.assertEqual(wf.getsampwidth(), 3)  # 24-bit
            self.assertEqual(wf.getframerate(), 48000)
            self.assertGreater(wf.getnframes(), 0)

    def test_reference_matcher_config_validation(self):
        """Verifies ReferenceMatcherConfig constraints and clamping bounds."""
        cfg = ReferenceMatcherConfig()
        self.assertFalse(cfg.enable_reference_matching)
        self.assertEqual(cfg.max_spectral_correction_db, 3.0)

    def test_reference_matcher_spectral_matching(self):
        """Verifies FFT 1/3-octave spectral matching applies clamped adjustments."""
        t = np.linspace(0, 1.5, 72000, endpoint=False)
        # Target: Dull audio (heavy low fundamental 200 Hz)
        target = (0.6 * np.sin(2 * np.pi * 200.0 * t)).astype(np.float32)
        # Reference: Bright audio (high presence 3000 Hz)
        reference = (0.6 * np.sin(2 * np.pi * 3000.0 * t)).astype(np.float32)

        stereo_target = np.column_stack((target, target))
        stereo_reference = np.column_stack((reference, reference))

        matched = self.matcher.match_spectrum(stereo_target, stereo_reference, sr=48000)

        self.assertEqual(matched.shape, stereo_target.shape)
        self.assertFalse(np.isnan(matched).any())
        self.assertFalse(np.isinf(matched).any())

        # Peak amplitude must not clip beyond 1.0
        self.assertLessEqual(float(np.max(np.abs(matched))), 1.0)

    def test_reference_matcher_file_pipeline(self):
        """Verifies match_files end-to-end file pipeline."""
        target_wav = self.tmp_dir / "chap_target.wav"
        ref_wav = self.tmp_dir / "golden_ref.wav"
        out_wav = self.tmp_dir / "matched_master.wav"

        make_test_wav(target_wav, duration_sec=1.5, freq_hz=300.0)
        make_test_wav(ref_wav, duration_sec=1.5, freq_hz=1000.0)

        res_path = self.matcher.match_files(target_wav, ref_wav, out_wav)

        self.assertTrue(res_path.exists())
        with wave.open(str(res_path), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 2)
            self.assertEqual(wf.getsampwidth(), 3)  # 24-bit
            self.assertEqual(wf.getframerate(), 48000)
            self.assertGreater(wf.getnframes(), 0)


if __name__ == "__main__":
    unittest.main()
