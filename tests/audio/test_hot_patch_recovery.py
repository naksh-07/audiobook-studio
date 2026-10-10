#!/usr/bin/env python3
"""
Audiobook Factory - Unit Tests for Incremental DAG Caching, Hot-Patching, & Janitor Shield (Phase 5).
Verifies:
1. Deterministic segment cryptographic hash calculation and DAG change detection.
2. Sample-accurate single-segment hot-patch splicing without full chapter rebuild (AP-07).
3. Concurrency scratch isolation and certified master retention shield (AP-09).
"""

import math
import wave
import hashlib
from pathlib import Path
import pytest

from audiobook_factory.audio.contracts import SegmentAudioContract
from audiobook_factory.audio.ledger import (
    compute_segment_content_hash,
    SegmentLedgerEntry,
    ChapterSegmentLedger,
    LedgerDiffResult,
)
from audiobook_factory.audio.hot_patcher import SingleSegmentHotPatcher, HotPatchResult
from audiobook_factory.orchestration.janitor import JanitorShield


def create_synthetic_wav(
    path: Path,
    duration_ms: int,
    freq_hz: float = 440.0,
    sample_rate: int = 48000,
) -> Path:
    """Helper to synthesize a standard 48kHz 24-bit stereo WAV tone."""
    num_frames = int((duration_ms / 1000.0) * sample_rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(sample_rate)
        frames = bytearray()
        for i in range(num_frames):
            val = int(8388607 * 0.2 * math.sin(2 * math.pi * freq_hz * i / sample_rate))
            b = val.to_bytes(3, byteorder="little", signed=True)
            frames.extend(b)  # L
            frames.extend(b)  # R
        w.writeframes(frames)
    return path


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestHotPatchRecovery:
    """Test suite for Phase 5 hot-patching and caching capabilities."""

    def test_segment_content_hash_deterministic(self):
        """Verify identical inputs yield identical hash and mutations change hash."""
        h1 = compute_segment_content_hash(
            segment_uid="c001_s001",
            spoken_text="Geralt drew his silver blade.",
            speaker="Narrator",
            voice_name="Aoede",
            delivery_style="somber",
            pitch_pct=0.0,
            speed=1.0,
        )
        h2 = compute_segment_content_hash(
            segment_uid="c001_s001",
            spoken_text="Geralt drew his silver blade.",
            speaker="Narrator",
            voice_name="Aoede",
            delivery_style="somber",
            pitch_pct=0.0,
            speed=1.0,
        )
        assert h1 == h2

        # Mutate text
        h3 = compute_segment_content_hash(
            segment_uid="c001_s001",
            spoken_text="Geralt drew his steel blade.",
            speaker="Narrator",
            voice_name="Aoede",
            delivery_style="somber",
            pitch_pct=0.0,
            speed=1.0,
        )
        assert h1 != h3

        # Mutate pitch
        h4 = compute_segment_content_hash(
            segment_uid="c001_s001",
            spoken_text="Geralt drew his silver blade.",
            speaker="Narrator",
            voice_name="Aoede",
            delivery_style="somber",
            pitch_pct=2.5,
            speed=1.0,
        )
        assert h1 != h4

    def test_chapter_segment_ledger_record_and_diff(self, tmp_path):
        """Verify ledger correctly identifies unchanged, modified, added, and removed segments."""
        ledger_path = tmp_path / "chapter_001_segment_ledger.json"
        ledger = ChapterSegmentLedger(chapter_num=1)

        # Create 3 synthetic audio files
        audio_files = []
        contracts = []
        for i in range(1, 4):
            wav_path = create_synthetic_wav(tmp_path / f"seg_{i}.wav", duration_ms=500, freq_hz=200 * i)
            audio_files.append(wav_path)
            c = SegmentAudioContract(
                chapter_id=1,
                segment_index=i,
                segment_uid=f"c001_s00{i}",
                audio_path=wav_path,
                audio_sha256=compute_file_sha256(wav_path),
                duration_ms=500,
                speaker="Geralt" if i == 2 else "Narrator",
                voice_name="Fenrir" if i == 2 else "Aoede",
                literary_text=f"Text for segment {i}",
                spoken_text=f"Text for segment {i}",
            )
            contracts.append(c)
            ledger.record_contract(c, timeline_start_ms=(i - 1) * 500, timeline_end_ms=i * 500)

        assert ledger.total_duration_ms == 1500
        ledger.save_to_disk(ledger_path)

        # Reload from disk
        loaded_ledger = ChapterSegmentLedger.load_from_disk(ledger_path)
        assert len(loaded_ledger.entries) == 3
        assert loaded_ledger.total_duration_ms == 1500

        # Diff 1: Identical
        diff1 = loaded_ledger.diff_contracts(contracts)
        assert diff1.is_identical is True
        assert len(diff1.unchanged_uids) == 3
        assert len(diff1.modified_uids) == 0

        # Diff 2: Modify segment 2
        mod_contracts = list(contracts)
        mod_contracts[1] = SegmentAudioContract(
            chapter_id=1,
            segment_index=2,
            segment_uid="c001_s002",
            audio_path=audio_files[1],
            audio_sha256=compute_file_sha256(audio_files[1]),
            duration_ms=500,
            speaker="Geralt",
            voice_name="Fenrir",
            literary_text="Modified text for segment 2",
            spoken_text="Modified text for segment 2",
        )
        diff2 = loaded_ledger.diff_contracts(mod_contracts)
        assert diff2.is_identical is False
        assert diff2.modified_uids == ["c001_s002"]
        assert diff2.unchanged_uids == ["c001_s001", "c001_s003"]

        # Diff 3: Add segment 4
        new_wav = create_synthetic_wav(tmp_path / "seg_4.wav", duration_ms=500, freq_hz=800)
        c4 = SegmentAudioContract(
            chapter_id=1,
            segment_index=4,
            segment_uid="c001_s004",
            audio_path=new_wav,
            audio_sha256=compute_file_sha256(new_wav),
            duration_ms=500,
            speaker="Yennefer",
            voice_name="Kore",
            literary_text="New text for segment 4",
            spoken_text="New text for segment 4",
        )
        diff3 = loaded_ledger.diff_contracts(contracts + [c4])
        assert diff3.added_uids == ["c001_s004"]

        # Diff 4: Remove segment 3
        diff4 = loaded_ledger.diff_contracts(contracts[:2])
        assert diff4.removed_uids == ["c001_s003"]

    def test_single_segment_hot_patch_in_place(self, tmp_path):
        """Verify hot-patcher cleanly splices an updated segment into existing pre-master WAV."""
        # Setup 3-segment pre-master WAV (total 1500ms: 500ms + 500ms + 500ms)
        premaster_wav = tmp_path / "chapter_001_premaster.wav"
        seg1_wav = create_synthetic_wav(tmp_path / "seg1.wav", duration_ms=500, freq_hz=300)
        seg2_wav = create_synthetic_wav(tmp_path / "seg2.wav", duration_ms=500, freq_hz=600)
        seg3_wav = create_synthetic_wav(tmp_path / "seg3.wav", duration_ms=500, freq_hz=900)

        # Concatenate into premaster_wav
        with wave.open(str(premaster_wav), "wb") as w_out:
            w_out.setnchannels(2)
            w_out.setsampwidth(3)
            w_out.setframerate(48000)
            for seg in [seg1_wav, seg2_wav, seg3_wav]:
                with wave.open(str(seg), "rb") as w_in:
                    w_out.writeframes(w_in.readframes(w_in.getnframes()))

        # Register in ledger
        ledger = ChapterSegmentLedger(chapter_num=1)
        for i, (seg, freq) in enumerate([(seg1_wav, 300), (seg2_wav, 600), (seg3_wav, 900)], start=1):
            c = SegmentAudioContract(
                chapter_id=1,
                segment_index=i,
                segment_uid=f"c001_s00{i}",
                audio_path=seg,
                audio_sha256=compute_file_sha256(seg),
                duration_ms=500,
                speaker="Speaker",
                voice_name="Voice",
                spoken_text=f"Segment {i}",
            )
            ledger.record_contract(c, timeline_start_ms=(i - 1) * 500, timeline_end_ms=i * 500)

        # Create updated replacement for segment 2 (500ms, freq 1200)
        new_seg2_wav = create_synthetic_wav(tmp_path / "new_seg2.wav", duration_ms=500, freq_hz=1200)
        new_contract2 = SegmentAudioContract(
            chapter_id=1,
            segment_index=2,
            segment_uid="c001_s002",
            audio_path=new_seg2_wav,
            audio_sha256=compute_file_sha256(new_seg2_wav),
            duration_ms=500,
            speaker="Speaker",
            voice_name="Voice",
            spoken_text="Segment 2 regenerated",
        )

        output_wav = tmp_path / "chapter_001_premaster_patched.wav"
        patcher = SingleSegmentHotPatcher()
        result = patcher.hot_patch_premaster(
            premaster_path=premaster_wav,
            output_path=output_wav,
            ledger=ledger,
            new_contract=new_contract2,
        )

        assert result.success is True
        assert result.is_in_place_duration is True
        assert result.delta_ms == 0
        assert result.new_total_duration_ms == 1500
        assert output_wav.is_file()

        # Check audio properties of output WAV
        with wave.open(str(output_wav), "rb") as w:
            assert w.getframerate() == 48000
            assert w.getnchannels() == 2
            assert w.getsampwidth() == 3
            assert w.getnframes() == 48000 * 1500 // 1000

    def test_single_segment_hot_patch_duration_ripple(self, tmp_path):
        """Verify hot-patcher ripples downstream timeline offsets when duration changes."""
        premaster_wav = tmp_path / "chapter_001_premaster.wav"
        seg1_wav = create_synthetic_wav(tmp_path / "seg1.wav", duration_ms=500, freq_hz=300)
        seg2_wav = create_synthetic_wav(tmp_path / "seg2.wav", duration_ms=500, freq_hz=600)
        seg3_wav = create_synthetic_wav(tmp_path / "seg3.wav", duration_ms=500, freq_hz=900)

        with wave.open(str(premaster_wav), "wb") as w_out:
            w_out.setnchannels(2)
            w_out.setsampwidth(3)
            w_out.setframerate(48000)
            for seg in [seg1_wav, seg2_wav, seg3_wav]:
                with wave.open(str(seg), "rb") as w_in:
                    w_out.writeframes(w_in.readframes(w_in.getnframes()))

        ledger = ChapterSegmentLedger(chapter_num=1)
        for i, seg in enumerate([seg1_wav, seg2_wav, seg3_wav], start=1):
            c = SegmentAudioContract(
                chapter_id=1,
                segment_index=i,
                segment_uid=f"c001_s00{i}",
                audio_path=seg,
                audio_sha256=compute_file_sha256(seg),
                duration_ms=500,
                speaker="Speaker",
                voice_name="Voice",
                spoken_text=f"Segment {i}",
            )
            ledger.record_contract(c, timeline_start_ms=(i - 1) * 500, timeline_end_ms=i * 500)

        # New segment 2 is 800ms (+300ms delta)
        new_seg2_wav = create_synthetic_wav(tmp_path / "new_seg2_long.wav", duration_ms=800, freq_hz=1200)
        new_contract2 = SegmentAudioContract(
            chapter_id=1,
            segment_index=2,
            segment_uid="c001_s002",
            audio_path=new_seg2_wav,
            audio_sha256=compute_file_sha256(new_seg2_wav),
            duration_ms=800,
            speaker="Speaker",
            voice_name="Voice",
            spoken_text="Segment 2 longer",
        )

        output_wav = tmp_path / "chapter_001_premaster_rippled.wav"
        patcher = SingleSegmentHotPatcher()
        result = patcher.hot_patch_premaster(
            premaster_path=premaster_wav,
            output_path=output_wav,
            ledger=ledger,
            new_contract=new_contract2,
        )

        assert result.success is True
        assert result.delta_ms == 300
        assert result.new_total_duration_ms == 1800
        assert result.is_in_place_duration is False

        # Segment 3 timeline coordinates in ledger should be shifted by +300ms
        seg3_entry = ledger.entries["c001_s003"]
        assert seg3_entry.timeline_start_ms == 1300
        assert seg3_entry.timeline_end_ms == 1800

        with wave.open(str(output_wav), "rb") as w:
            assert w.getnframes() == 48000 * 1800 // 1000

    def test_janitor_shield_and_isolated_scratch(self, tmp_path):
        """Verify thread-isolated scratch space creation and protected file retention (AP-09)."""
        scratch_dir = JanitorShield.create_isolated_scratch(
            base_dir=tmp_path,
            chapter_num=1,
            run_id="run_alpha",
        )
        assert scratch_dir.is_dir()
        assert "run_alpha" in scratch_dir.name
        assert "c001" in scratch_dir.name

        # Populate scratch dir with transient files and protected files
        scratch_chunk = scratch_dir / "c001_001_temp.wav"
        scratch_chunk.write_bytes(b"temp data")
        
        master_wav = scratch_dir / "chapter_001_master.wav"
        master_wav.write_bytes(b"master wav")

        m4a_deliverable = scratch_dir / "chapter_001.m4a"
        m4a_deliverable.write_bytes(b"aac data")

        ledger_json = scratch_dir / "chapter_001_segment_ledger.json"
        ledger_json.write_text("{}", encoding="utf-8")

        # Run Janitor sweep
        purged = JanitorShield.purge_scratch_directory(
            scratch_dir=scratch_dir,
            certified=True,
            force=False,
        )

        # Transient chunk should be purged
        assert purged == 1
        assert not scratch_chunk.exists()

        # Protected deliverables MUST be retained
        assert master_wav.is_file()
        assert m4a_deliverable.is_file()
        assert ledger_json.is_file()
