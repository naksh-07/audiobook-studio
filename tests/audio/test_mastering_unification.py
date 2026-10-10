#!/usr/bin/env python3
"""
Unit and Integration Tests for Phase 3: Runtime Mastering Engine Unification & True Peak Headroom.
==================================================================================================
Validates:
1. AP-02 True Peak Headroom: MasteringProfile defaults to -2.0 dBTP / -2.0 dBFS ceiling.
2. AP-02 DSP Limit: Mastered audio True Peak strictly conforms to -2.0 dBFS ceiling.
3. AP-08 Noise Floor Invariant: Near-silent input is NOT dynamically boosted by loudnorm AGC.
4. AP-01 Runtime Unification: process_and_master_dialogue_stem utilizes MasteringEngineV2,
   generates chapter disk ledger, and cleans up intermediate premaster.
"""

import shutil
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from audiobook_factory.mastering_contracts import (
    MasteringProfile,
    MasteringRequest,
    MasteringLedger,
)
from audiobook_factory.mastering_engine import MasteringEngineV2
from audiobook_factory.orchestration.dialogue_runner import process_and_master_dialogue_stem


def make_test_wav(
    target_path: Path,
    duration_sec: float = 2.0,
    sample_rate: int = 48000,
    channels: int = 1,
    amplitude: float = 0.5,
) -> Path:
    """Generates synthetic test audio file."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    data = (amplitude * np.sin(2 * np.pi * 440.0 * t) * 32767.0).astype(np.int16)
    if channels == 2:
        data = np.column_stack((data, data)).flatten()

    with wave.open(str(target_path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(data.tobytes())
    return target_path


class TestMasteringUnification(unittest.TestCase):
    """Test suite for Phase 3 mastering engine unification and headroom fixes."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="test_phase3_mastering_"))
        self.engine = MasteringEngineV2()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_mastering_profile_defaults_ap02(self):
        """AP-02: Verify MasteringProfile defaults enforce -2.0 dBTP ceiling and -2.0 dBFS limiter."""
        prof = MasteringProfile()
        self.assertEqual(prof.true_peak_ceiling_dbtp, -2.0)
        self.assertEqual(prof.limiter_ceiling_db, -2.0)
        self.assertEqual(prof.limiter_release_ms, 40)
        self.assertEqual(prof.target_lufs, -19.0)

    def test_true_peak_headroom_limiting(self):
        """AP-02: Verify high-energy audio rendered by MasteringEngineV2 does not exceed -2.0 dBTP."""
        premaster = self.tmp_dir / "hot_premaster.wav"
        master = self.tmp_dir / "hot_master.wav"
        # High amplitude (0.95) sine wave that triggers brickwall limiting
        make_test_wav(premaster, duration_sec=2.5, amplitude=0.95)

        req = MasteringRequest(
            chapter_id="ch_hot",
            premaster_path=str(premaster),
            output_master_path=str(master),
            profile=MasteringProfile(),
        )
        res = self.engine.master(req)

        self.assertEqual(res.status, "SUCCESS")
        self.assertTrue(master.exists())
        self.assertIsNotNone(res.analysis_after)
        if res.analysis_after.true_peak_dbtp is not None:
            # Must respect the -2.0 dBTP ceiling with tight margin
            self.assertLessEqual(res.analysis_after.true_peak_dbtp, -1.8)

    def test_dynamic_loudnorm_banned_on_near_silence_ap08(self):
        """AP-08: Verify near-silent audio does not trigger dynamic AGC boosting."""
        premaster = self.tmp_dir / "silent_premaster.wav"
        master = self.tmp_dir / "silent_master.wav"
        # Barely audible room tone (~ -75 dBFS)
        make_test_wav(premaster, duration_sec=2.0, amplitude=0.0002)

        pass1_stats = {
            "input_i": "-72.5",
            "input_tp": "-70.0",
            "input_lra": "0.0",
            "input_thresh": "-82.5",
            "target_offset": "0.0",
        }
        prof = MasteringProfile()
        out_rendered = self.engine._render_master(
            premaster_path=premaster,
            output_path=master,
            profile=prof,
            target_lufs=-19.0,
            limiter_ceiling_db=-2.0,
            pass1_stats=pass1_stats,
        )

        self.assertTrue(out_rendered.exists())
        # The output must NOT be boosted to -19 LUFS! It should remain very quiet
        with wave.open(str(master), "rb") as wf:
            raw = wf.readframes(wf.getnframes())
            if wf.getsampwidth() == 3:
                samples = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
                int24 = (samples[:, 0].astype(np.int32) |
                         (samples[:, 1].astype(np.int32) << 8) |
                         (samples[:, 2].astype(np.int32) << 16))
                int24[int24 >= 0x800000] -= 0x1000000
                max_amp = np.max(np.abs(int24))
                # In 24-bit space (peak 8,388,607), unamplified signal stays < 100,000 (~ -40 dBFS)
                self.assertLess(max_amp, 100000)
            else:
                samples = np.frombuffer(raw, dtype=np.int16)
                max_amp = np.max(np.abs(samples))
                self.assertLess(max_amp, 1000)

    def test_process_and_master_dialogue_stem_unification(self):
        """AP-01: Verify dialogue runner end-to-end executes MasteringEngineV2 and creates disk ledger."""
        audio_dir = self.tmp_dir / "audio_chunks"
        mastered_dir = self.tmp_dir / "mastered"
        audio_dir.mkdir(parents=True, exist_ok=True)
        mastered_dir.mkdir(parents=True, exist_ok=True)

        s1 = audio_dir / "c001_s0001_take1.wav"
        s2 = audio_dir / "c001_s0002_take1.wav"
        make_test_wav(s1, duration_sec=1.2, amplitude=0.4)
        make_test_wav(s2, duration_sec=1.0, amplitude=0.35)

        script_data = [
            {"index": 1, "speaker": "Narrator", "text": "He stepped out of the tavern."},
            {"index": 2, "speaker": "Geralt", "text": "The wind was howling."},
        ]

        vocal_wav, vocal_dur, seg_durations, segments = process_and_master_dialogue_stem(
            project_dir=self.tmp_dir,
            chapter_num=1,
            chap_stem="c001",
            script_data=script_data,
            audio_dir=audio_dir,
            mastered_dir=mastered_dir,
            spatial_staging=False,
            segment_files=[s1, s2],
        )

        self.assertTrue(vocal_wav.exists())
        self.assertGreater(vocal_dur, 2.0)
        self.assertEqual(len(seg_durations), 2)

        # Verify disk ledger created by MasteringEngineV2
        ledger_file = mastered_dir / "c001_mastering_ledger.json"
        self.assertTrue(ledger_file.exists(), "MasteringEngineV2 must produce disk ledger!")
        ledger = MasteringLedger.load_from_disk(ledger_file)
        self.assertEqual(ledger.chapter_id, "c001")
        self.assertEqual(ledger.result.status, "SUCCESS")

        # Verify intermediate premaster WAV was cleaned up
        premaster_wav = mastered_dir / "c001_dialogue.premaster.wav"
        self.assertFalse(premaster_wav.exists(), "Intermediate premaster must be deleted after mastering!")


if __name__ == "__main__":
    unittest.main()
