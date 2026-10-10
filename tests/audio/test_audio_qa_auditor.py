#!/usr/bin/env python3
"""
Unit and Integration Tests for Phase 2: AI-Assisted Acoustic & Script QA Auditor (qa_auditor.py).
=================================================================================================
Validates:
1. AudioQAConfig, SegmentQAEvaluation, and ChapterQAReport Pydantic v2 contracts.
2. Normal speech takes evaluate cleanly as PASS with valid WPM and MOS.
3. Severe silent dropouts trigger hard FAIL verdict.
4. Truncation and physically impossible speech rates trigger TTS_DROPOUT_TRUNCATION.
5. Hallucination and repetition loops trigger TTS_HALLUCINATION_LOOP.
6. Leading/trailing dead air triggers non-blocking WARN notices.
7. Chapter-level QA audit aggregation into ChapterQAReport.
"""

import shutil
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from audiobook_factory.audio.contracts import (
    AudioQAConfig,
    SegmentQAEvaluation,
    ChapterQAReport,
)
from audiobook_factory.audio.qa_auditor import (
    AudioQAAuditor,
    has_whisper_engine,
)


def make_test_speech_wav(
    target_path: Path,
    duration_sec: float = 2.0,
    sample_rate: int = 48000,
    amplitude: float = 0.5,
    leading_silence_sec: float = 0.0,
    trailing_silence_sec: float = 0.0,
) -> Path:
    """Generates synthetic harmonic audio with optional leading/trailing silence."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    active_dur = max(0.05, duration_sec - leading_silence_sec - trailing_silence_sec)
    num_active = int(active_dur * sample_rate)
    num_lead = int(leading_silence_sec * sample_rate)
    num_trail = int(trailing_silence_sec * sample_rate)

    t = np.linspace(0, active_dur, num_active, endpoint=False)
    # Fundamental 220Hz + harmonics
    speech = (
        0.6 * np.sin(2 * np.pi * 220.0 * t)
        + 0.3 * np.sin(2 * np.pi * 440.0 * t)
        + 0.1 * np.sin(2 * np.pi * 880.0 * t)
    )
    speech = (speech / np.max(np.abs(speech))) * amplitude

    full_signal = np.concatenate([
        np.zeros(num_lead, dtype=np.float32),
        speech.astype(np.float32),
        np.zeros(num_trail, dtype=np.float32),
    ])

    int_data = (np.clip(full_signal, -1.0, 1.0) * 32767.0).astype(np.int16)
    stereo_data = np.column_stack((int_data, int_data)).flatten()

    with wave.open(str(target_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(stereo_data.tobytes())
    return target_path


class TestAudioQAAuditor(unittest.TestCase):
    """Test suite for AudioQAAuditor forensic quality control."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="test_audio_qa_"))
        self.auditor = AudioQAAuditor()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_qa_contracts_validation(self):
        """Verifies default values and constraints of AudioQAConfig."""
        cfg = AudioQAConfig()
        self.assertTrue(cfg.enable_vad)
        self.assertEqual(cfg.min_wpm, 75.0)
        self.assertEqual(cfg.max_wpm, 240.0)
        self.assertEqual(cfg.min_pause_ms, 120)
        self.assertEqual(cfg.max_pause_ms, 1800)
        self.assertEqual(cfg.min_mos_threshold, 3.5)

    def test_normal_speech_audit_pass(self):
        """Verifies normal, well-paced dialogue take achieves PASS verdict."""
        wav_path = self.tmp_dir / "normal_speech.wav"
        # 5 words in 2.0s = 150 WPM (normal conversational pace)
        make_test_speech_wav(wav_path, duration_sec=2.0, amplitude=0.5)

        res = self.auditor.audit_segment(
            audio_path=wav_path,
            expected_text="Hello world, this is normal speech.",
            speaker="Aoede",
            segment_index=1,
            segment_uid="seg_001",
        )

        self.assertIsInstance(res, SegmentQAEvaluation)
        self.assertEqual(res.status, "PASS")
        self.assertGreaterEqual(res.predicted_mos, 4.0)
        self.assertGreaterEqual(res.estimated_wpm, 100.0)
        self.assertLessEqual(res.estimated_wpm, 200.0)
        self.assertEqual(len(res.issues), 0)

    def test_silent_audio_dropout_rejection(self):
        """Verifies near-silent audio triggers hard FAIL verdict."""
        wav_path = self.tmp_dir / "silent_dropout.wav"
        make_test_speech_wav(wav_path, duration_sec=2.0, amplitude=0.00001)

        res = self.auditor.audit_segment(
            audio_path=wav_path,
            expected_text="This text should have been spoken loudly.",
            speaker="Narrator",
            segment_index=2,
            segment_uid="seg_002",
        )

        self.assertEqual(res.status, "FAIL")
        self.assertTrue(any("SILENT_AUDIO_DROPOUT" in issue for issue in res.issues))

    def test_truncation_detection(self):
        """Verifies physically impossible rushed speech is flagged as dropout truncation."""
        wav_path = self.tmp_dir / "truncated.wav"
        # 30 words in 0.3s (extreme dropout truncation)
        make_test_speech_wav(wav_path, duration_sec=0.3, amplitude=0.5)

        long_text = "The silver falcon soared across the snowy peaks of the northern kingdom looking for prey in the deep forest valley."
        res = self.auditor.audit_segment(
            audio_path=wav_path,
            expected_text=long_text,
            speaker="Narrator",
            segment_index=3,
            segment_uid="seg_003",
        )

        self.assertEqual(res.status, "FAIL")
        self.assertTrue(any("TTS_DROPOUT_TRUNCATION" in issue for issue in res.issues))

    def test_hallucination_loop_detection(self):
        """Verifies extremely long audio on short text is flagged as hallucination loop."""
        wav_path = self.tmp_dir / "hallucination_loop.wav"
        # 2 words taking 7.0 seconds
        make_test_speech_wav(wav_path, duration_sec=7.0, amplitude=0.5)

        res = self.auditor.audit_segment(
            audio_path=wav_path,
            expected_text="Yes sir.",
            speaker="Geralt",
            segment_index=4,
            segment_uid="seg_004",
        )

        self.assertEqual(res.status, "FAIL")
        self.assertTrue(any("TTS_HALLUCINATION_LOOP" in issue for issue in res.issues))

    def test_excessive_dead_air_warning(self):
        """Verifies excessive leading silence emits non-blocking WARN notice."""
        wav_path = self.tmp_dir / "dead_air.wav"
        # 1.0s leading silence + 1.5s speech
        make_test_speech_wav(wav_path, duration_sec=2.5, amplitude=0.5, leading_silence_sec=1.0)

        res = self.auditor.audit_segment(
            audio_path=wav_path,
            expected_text="Taking my time before speaking.",
            speaker="Narrator",
            segment_index=5,
            segment_uid="seg_005",
        )

        self.assertEqual(res.status, "WARN")
        self.assertTrue(any("EXCESSIVE_LEADING_SILENCE" in issue for issue in res.issues))

    def test_chapter_qa_aggregation(self):
        """Verifies full chapter audit consolidates evaluations into ChapterQAReport."""
        p1 = self.tmp_dir / "chap_seg_1.wav"
        p2 = self.tmp_dir / "chap_seg_2.wav"
        make_test_speech_wav(p1, duration_sec=2.0, amplitude=0.5)
        make_test_speech_wav(p2, duration_sec=2.5, amplitude=0.5, leading_silence_sec=0.9)

        script_segments = [
            {"index": 1, "text": "First normal sentence.", "speaker": "Narrator"},
            {"index": 2, "text": "Second sentence with pause.", "speaker": "Charon"},
        ]

        report = self.auditor.audit_chapter(
            audio_segments=[p1, p2],
            script_segments=script_segments,
            chapter_num=1,
        )

        self.assertIsInstance(report, ChapterQAReport)
        self.assertEqual(report.chapter_num, 1)
        self.assertEqual(report.total_segments, 2)
        self.assertEqual(report.passed_segments, 1)
        self.assertEqual(report.warned_segments, 1)
        self.assertEqual(report.failed_segments, 0)
        self.assertEqual(report.overall_status, "WARN")
        self.assertGreaterEqual(report.mean_mos, 4.0)


if __name__ == "__main__":
    unittest.main()
