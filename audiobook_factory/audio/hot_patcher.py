#!/usr/bin/env python3
"""
Audiobook Factory - Single-Segment Hot-Patcher (Phase 5: Incremental DAG Caching).
Allows sample-accurate splicing of regenerated speech chunks into existing pre-master WAV files.
Eliminates full chapter re-rendering when a single chunk is tweaked or regenerated (AP-07).
"""

from __future__ import annotations
import wave
import shutil
from pathlib import Path
from typing import Optional, Tuple
from pydantic import BaseModel, Field, ConfigDict

from audiobook_factory.logger import logger
from .contracts import SegmentAudioContract
from .ledger import ChapterSegmentLedger, SegmentLedgerEntry


class HotPatchResult(BaseModel):
    """Result of a single-segment hot-patch operation."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    success: bool
    segment_uid: str
    premaster_path: Path
    delta_ms: int
    new_total_duration_ms: int
    is_in_place_duration: bool
    message: str


class SingleSegmentHotPatcher:
    """
    Surgically splices a regenerated speech segment into an existing chapter pre-master WAV.
    Stream-processes audio in 64 KB blocks to maintain <= 1 MB RAM usage in Termux ARM64.
    """

    def __init__(self, block_size_frames: int = 4096):
        self.block_size_frames = block_size_frames

    def hot_patch_premaster(
        self,
        premaster_path: Path,
        output_path: Path,
        ledger: ChapterSegmentLedger,
        new_contract: SegmentAudioContract,
        pitch_pct: float = 0.0,
        speed: float = 1.0,
    ) -> HotPatchResult:
        """
        Splices new_contract audio into premaster_path at the position recorded in ledger.
        If durations match, it is a sample-exact replacement.
        If durations differ, subsequent audio is rippled and timeline offsets in ledger are updated.
        """
        premaster_path = Path(premaster_path)
        output_path = Path(output_path)
        new_audio_path = Path(new_contract.audio_path)

        if premaster_path.resolve() == output_path.resolve():
            raise ValueError("output_path cannot be the same as premaster_path for hot-patching to prevent truncation/locking")

        if not premaster_path.is_file():
            raise FileNotFoundError(f"Source pre-master WAV not found: {premaster_path}")
        if not new_audio_path.is_file():
            raise FileNotFoundError(f"New segment audio WAV not found: {new_audio_path}")

        seg_uid = new_contract.segment_uid
        if seg_uid not in ledger.entries:
            raise KeyError(f"Segment UID {seg_uid} not present in chapter ledger")

        old_entry = ledger.entries[seg_uid]
        old_dur_ms = old_entry.duration_ms
        new_dur_ms = new_contract.duration_ms
        delta_ms = new_dur_ms - old_dur_ms
        is_in_place = abs(delta_ms) <= 5  # Within 5ms is considered duration-matched

        logger.info(
            f"[HOT-PATCH] Splicing {seg_uid} (old: {old_dur_ms}ms, new: {new_dur_ms}ms, delta: {delta_ms}ms) "
            f"into {premaster_path.name}"
        )

        with wave.open(str(premaster_path), "rb") as w_pre, \
             wave.open(str(new_audio_path), "rb") as w_new:

            framerate = w_pre.getframerate()
            nchannels = w_pre.getnchannels()
            sampwidth = w_pre.getsampwidth()
            total_pre_frames = w_pre.getnframes()

            # Invariant check: sampling rate and channel match
            if w_new.getframerate() != framerate:
                raise ValueError(
                    f"Sample rate mismatch: premaster={framerate}Hz vs new_audio={w_new.getframerate()}Hz"
                )
            if w_new.getnchannels() != nchannels:
                raise ValueError(
                    f"Channel mismatch: premaster={nchannels} vs new_audio={w_new.getnchannels()}"
                )
            if w_new.getsampwidth() != sampwidth:
                raise ValueError(
                    f"Sample width mismatch: premaster={sampwidth} vs new_audio={w_new.getsampwidth()}"
                )

            # Calculate frame boundaries
            start_frame = int((old_entry.timeline_start_ms / 1000.0) * framerate)
            old_end_frame = int((old_entry.timeline_end_ms / 1000.0) * framerate)
            start_frame = min(start_frame, total_pre_frames)
            old_end_frame = min(old_end_frame, total_pre_frames)
            new_frames_total = w_new.getnframes()

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(output_path), "wb") as w_out:
                w_out.setnchannels(nchannels)
                w_out.setsampwidth(sampwidth)
                w_out.setframerate(framerate)

                # Part 1: Stream pre-master audio preceding the segment
                frames_written = 0
                while frames_written < start_frame:
                    chunk_to_read = min(self.block_size_frames, start_frame - frames_written)
                    data = w_pre.readframes(chunk_to_read)
                    if not data:
                        break
                    frames_read = len(data) // (nchannels * sampwidth)
                    w_out.writeframes(data)
                    frames_written += frames_read

                # Part 2: Stream the new segment audio
                while True:
                    data = w_new.readframes(self.block_size_frames)
                    if not data:
                        break
                    w_out.writeframes(data)

                # Part 3: Seek pre-master past old segment and stream remainder
                w_pre.setpos(old_end_frame)
                while True:
                    data = w_pre.readframes(self.block_size_frames)
                    if not data:
                        break
                    w_out.writeframes(data)

        # Update ledger
        new_timeline_end_ms = old_entry.timeline_start_ms + new_dur_ms
        ledger.record_contract(
            contract=new_contract,
            timeline_start_ms=old_entry.timeline_start_ms,
            timeline_end_ms=new_timeline_end_ms,
            pitch_pct=pitch_pct,
            speed=speed,
        )

        # If duration shifted, ripple subsequent segment timeline offsets
        if delta_ms != 0:
            for uid, entry in sorted(ledger.entries.items(), key=lambda x: x[1].segment_index):
                if entry.segment_index > old_entry.segment_index:
                    entry.timeline_start_ms += delta_ms
                    entry.timeline_end_ms += delta_ms
            ledger.total_duration_ms += delta_ms

        logger.info(
            f"[HOT-PATCH] Successfully spliced {seg_uid}. Output saved to {output_path.name} "
            f"(new total: {ledger.total_duration_ms}ms)"
        )

        return HotPatchResult(
            success=True,
            segment_uid=seg_uid,
            premaster_path=output_path,
            delta_ms=delta_ms,
            new_total_duration_ms=ledger.total_duration_ms,
            is_in_place_duration=is_in_place,
            message="Hot-patch successfully applied to pre-master timeline.",
        )
