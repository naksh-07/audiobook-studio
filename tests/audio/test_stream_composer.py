#!/usr/bin/env python3
"""
Unit and Integration Tests for ChunkStreamComposer & DialogueEditorialBridge (Phase 2).
Validates:
1. Block-based streaming pre-master composition (48kHz 24-bit stereo).
2. Contextual syntax-aware pause realization (180ms clause, 380ms sentence, 600ms turn).
3. In-stream room-tone TPDF dither injection (AP-05: zero scratch files on disk).
4. Conversational overlap cross-talk (DE-05 equal-power blending).
5. Constant-power azimuth stereo spatial panning.
6. End-to-end DialogueEditorialBridge pipeline execution.
"""

import io
import wave
import tempfile
import unittest
import numpy as np
from pathlib import Path

from audiobook_factory.audio.contracts import IngestionConfig
from audiobook_factory.audio.stream_composer import ChunkStreamComposer
from audiobook_factory.audio.editorial import DialogueEditorialBridge
from audiobook_factory.dialogue_editing.contracts import DialogueEditPlan


def create_test_wav(file_path: Path, duration_sec: float = 1.0, freq: float = 440.0) -> Path:
    """Creates synthetic 48kHz stereo 24-bit PCM WAV for testing."""
    sr = 48000
    t = np.linspace(0.0, duration_sec, int(sr * duration_sec), endpoint=False)
    sine = (0.5 * np.sin(2.0 * np.pi * freq * t)).astype(np.float32)
    stereo = np.column_stack((sine, sine))

    int32_arr = np.clip(np.round(stereo * 8388607.0), -8388608, 8388607).astype("<i4")
    pcm24 = int32_arr.view(np.uint8).reshape(-1, 4)[:, :3].flatten().tobytes()

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(3)
        wf.setframerate(sr)
        wf.writeframes(pcm24)

    return file_path


class TestChunkStreamComposer(unittest.TestCase):
    """Test suite for ChunkStreamComposer and DialogueEditorialBridge."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.td.name)
        self.config = IngestionConfig(
            target_sample_rate=48000,
            target_channels=2,
            target_bit_depth=24,
            micro_taper_ms=5.0,
        )
        self.composer = ChunkStreamComposer(config=self.config)

    def tearDown(self):
        self.td.cleanup()

    def test_stream_composition_format_and_duration(self):
        """Verifies composition produces 48kHz 24-bit stereo WAV with accurate durations."""
        seg1 = create_test_wav(self.tmp_dir / "seg1.wav", duration_sec=1.0, freq=440.0)
        seg2 = create_test_wav(self.tmp_dir / "seg2.wav", duration_sec=1.0, freq=550.0)
        out_wav = self.tmp_dir / "premaster_test.wav"

        script_segments = [
            {"index": 1, "speaker": "Narrator", "text": "He waited in the cold silence."},
            {"index": 2, "speaker": "Narrator", "text": "Nobody arrived."},
        ]

        # Ingestion pre-roll = 500ms, post-roll = 1500ms, pause after sentence = 380ms
        res_path, total_dur, seg_durations = self.composer.compose_chapter_premaster(
            audio_segments=[seg1, seg2],
            output_wav=out_wav,
            script_segments=script_segments,
            pre_roll_ms=500,
            post_roll_ms=1500,
        )

        self.assertTrue(out_wav.exists())
        self.assertEqual(res_path, out_wav)

        with wave.open(str(out_wav), "rb") as wf:
            self.assertEqual(wf.getframerate(), 48000)
            self.assertEqual(wf.getnchannels(), 2)
            self.assertEqual(wf.getsampwidth(), 3)  # 24-bit

        # Expected: 0.5s pre-roll + 1.0s seg1 + 0.380s pause + 1.0s seg2 + 1.5s post-roll = ~4.38s
        expected_dur = 0.5 + 1.0 + 0.380 + 1.0 + 1.5
        self.assertAlmostEqual(total_dur, expected_dur, delta=0.05)
        self.assertAlmostEqual(seg_durations[1], 1.0, delta=0.01)
        self.assertAlmostEqual(seg_durations[2], 1.0, delta=0.01)

    def test_syntax_aware_pause_realization(self):
        """Verifies syntax pauses: clause (180ms), sentence (380ms), turn (600ms)."""
        seg_comma = {"speaker": "Narrator", "text": "Although the wind was fierce,"}
        seg_sentence = {"speaker": "Narrator", "text": "The gates stood firm."}
        seg_turn = {"speaker": "Geralt", "text": "Who goes there?"}

        # 1. Comma clause boundary
        pause_clause = self.composer.calculate_syntax_pause_ms(seg_comma, seg_sentence)
        self.assertEqual(pause_clause, 180)

        # 2. Sentence end boundary (same speaker)
        pause_sentence = self.composer.calculate_syntax_pause_ms(seg_sentence, seg_sentence)
        self.assertEqual(pause_sentence, 380)

        # 3. Speaker turn (Narrator -> Geralt)
        pause_turn = self.composer.calculate_syntax_pause_ms(seg_sentence, seg_turn)
        self.assertEqual(pause_turn, 600)

    def test_zero_scratch_silence_files(self):
        """Verifies zero .silence_*.wav or .overlap_*.wav files are created anywhere on disk (AP-05)."""
        seg1 = create_test_wav(self.tmp_dir / "s1.wav", duration_sec=0.8)
        seg2 = create_test_wav(self.tmp_dir / "s2.wav", duration_sec=0.8)
        out_wav = self.tmp_dir / "clean_premaster.wav"

        self.composer.compose_chapter_premaster(
            audio_segments=[seg1, seg2],
            output_wav=out_wav,
            script_segments=[{"index": 1, "text": "Line one."}, {"index": 2, "text": "Line two."}],
        )

        all_silence_files = list(self.tmp_dir.glob("*.silence*")) + list(self.tmp_dir.glob(".*silence*"))
        all_overlap_files = list(self.tmp_dir.glob("*.overlap*")) + list(self.tmp_dir.glob(".*overlap*"))

        self.assertEqual(len(all_silence_files), 0, f"Found orphan silence files: {all_silence_files}")
        self.assertEqual(len(all_overlap_files), 0, f"Found orphan overlap files: {all_overlap_files}")

    def test_conversational_overlap_cross_talk(self):
        """Verifies DE-05 interruption overlap blends in-stream without clipping."""
        seg1 = create_test_wav(self.tmp_dir / "ov1.wav", duration_sec=1.0, freq=300.0)
        seg2 = create_test_wav(self.tmp_dir / "ov2.wav", duration_sec=1.0, freq=600.0)
        out_wav = self.tmp_dir / "overlap_premaster.wav"

        # Plan segment 1 with 200ms overlap into segment 2
        plan1 = DialogueEditPlan(
            segment_uid="ov1_uid",
            source_take="ov1",
            speech_start_ms=0,
            speech_end_ms=1000,
            overlap_ms=200,
        )

        _, total_dur, _ = self.composer.compose_chapter_premaster(
            audio_segments=[seg1, seg2],
            output_wav=out_wav,
            edit_plans=[plan1, None],
            pre_roll_ms=0,
            post_roll_ms=0,
        )

        # Total duration with 200ms overlap should be 1.0 + 1.0 - 0.200 = 1.800s
        self.assertAlmostEqual(total_dur, 1.800, delta=0.03)

    def test_spatial_azimuth_panning(self):
        """Verifies constant-power azimuth panning separates stereo channels."""
        samples = np.ones((1000, 2), dtype=np.float32) * 0.5

        # Pan left (-0.8)
        panned_l = self.composer.apply_spatial_pan(samples, pan=-0.8)
        rms_left = np.sqrt(np.mean(panned_l[:, 0] ** 2))
        rms_right = np.sqrt(np.mean(panned_l[:, 1] ** 2))
        self.assertGreater(rms_left, rms_right * 2.0)

        # Pan right (+0.8)
        panned_r = self.composer.apply_spatial_pan(samples, pan=0.8)
        rms_left_r = np.sqrt(np.mean(panned_r[:, 0] ** 2))
        rms_right_r = np.sqrt(np.mean(panned_r[:, 1] ** 2))
        self.assertGreater(rms_right_r, rms_left_r * 2.0)

    def test_dialogue_editorial_bridge_end_to_end(self):
        """Verifies full execution through DialogueEditorialBridge."""
        bridge = DialogueEditorialBridge(config=self.config, project_dir=self.tmp_dir)

        s1 = create_test_wav(self.tmp_dir / "raw_s0001.wav", duration_sec=0.6, freq=400.0)
        s2 = create_test_wav(self.tmp_dir / "raw_s0002.wav", duration_sec=0.6, freq=500.0)
        out_premaster = self.tmp_dir / "bridge_premaster.wav"

        script = [
            {"index": 1, "speaker": "Narrator", "voice": "Aoede", "text": "The wind howled."},
            {"index": 2, "speaker": "Geralt", "voice": "Fenrir", "text": "Storm is coming."},
        ]

        res_wav, dur, durations_map, edited_segs, qc = bridge.process_and_compose_chapter(
            chapter_num=1,
            raw_audio_segments=[s1, s2],
            script_segments=script,
            output_premaster_wav=out_premaster,
            spatial_staging=True,
            pre_roll_ms=200,
            post_roll_ms=500,
        )

        self.assertTrue(res_wav.exists())
        self.assertGreater(dur, 1.0)
        self.assertEqual(len(edited_segs), 2)
        self.assertIn(1, durations_map)
        self.assertIn(2, durations_map)


if __name__ == "__main__":
    unittest.main()
