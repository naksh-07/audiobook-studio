#!/usr/bin/env python3
"""
Audiobook Factory - Segment Hash Ledger (Phase 5: Incremental DAG Caching).
Provides cryptographic hash tracking of segment content, audio artifacts, and timeline mapping.
Prevents redundant TTS and audio processing cycles when only a fraction of segments change.
"""

from __future__ import annotations
import hashlib
import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from audiobook_factory.logger import logger
from .contracts import SegmentAudioContract


def compute_segment_content_hash(
    segment_uid: str,
    spoken_text: str,
    speaker: str,
    voice_name: str,
    delivery_style: Optional[str] = None,
    pitch_pct: float = 0.0,
    speed: float = 1.0,
) -> str:
    """
    Computes a deterministic cryptographic SHA-256 fingerprint for a speech segment's
    textual and acoustic synthesis parameters.
    """
    hasher = hashlib.sha256()
    hasher.update(segment_uid.strip().encode("utf-8"))
    hasher.update(b"|")
    hasher.update(spoken_text.strip().encode("utf-8"))
    hasher.update(b"|")
    hasher.update(speaker.strip().lower().encode("utf-8"))
    hasher.update(b"|")
    hasher.update(voice_name.strip().lower().encode("utf-8"))
    hasher.update(b"|")
    hasher.update((delivery_style or "neutral").strip().lower().encode("utf-8"))
    hasher.update(b"|")
    hasher.update(f"{pitch_pct:.2f}|{speed:.2f}".encode("utf-8"))
    return hasher.hexdigest()


class SegmentLedgerEntry(BaseModel):
    """Immutable entry in the chapter segment ledger recording state of a single segment."""
    model_config = ConfigDict(extra="ignore")

    segment_uid: str = Field(..., description="Unique segment identifier")
    segment_index: int = Field(..., ge=1, description="1-indexed sequence order within chapter")
    content_hash: str = Field(..., description="Cryptographic SHA-256 of text and synthesis parameters")
    audio_path: str = Field(..., description="Path to physical audio file")
    audio_sha256: str = Field(..., description="SHA-256 of the audio PCM file on disk")
    duration_ms: int = Field(..., ge=0, description="Duration in milliseconds")
    timeline_start_ms: int = Field(default=0, ge=0, description="Start offset on master timeline")
    timeline_end_ms: int = Field(default=0, ge=0, description="End offset on master timeline")
    speaker: str = Field(..., description="Speaker / character name")
    voice_name: str = Field(..., description="Voice model name")
    delivery_style: Optional[str] = Field(default=None, description="Acting style modifier")
    created_at_utc: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class LedgerDiffResult(BaseModel):
    """Result of diffing a set of new segment specifications against an existing ledger."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    unchanged_uids: List[str] = Field(default_factory=list)
    modified_uids: List[str] = Field(default_factory=list)
    added_uids: List[str] = Field(default_factory=list)
    removed_uids: List[str] = Field(default_factory=list)

    @property
    def is_identical(self) -> bool:
        """True if every segment is unchanged with zero additions, modifications, or removals."""
        return not (self.modified_uids or self.added_uids or self.removed_uids)


class ChapterSegmentLedger(BaseModel):
    """
    Chapter-level DAG ledger recording all segment hashes and timeline alignments.
    Enables single-chunk regeneration without rebuilding entire chapters (AP-07).
    """
    model_config = ConfigDict(extra="ignore")

    chapter_num: int = Field(..., ge=1, description="1-indexed chapter number")
    total_duration_ms: int = Field(default=0, ge=0, description="Total chapter duration in ms")
    entries: Dict[str, SegmentLedgerEntry] = Field(
        default_factory=dict, description="Map of segment_uid -> SegmentLedgerEntry"
    )
    created_at_utc: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    updated_at_utc: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def record_contract(
        self,
        contract: SegmentAudioContract,
        timeline_start_ms: int = 0,
        timeline_end_ms: int = 0,
        pitch_pct: float = 0.0,
        speed: float = 1.0,
    ) -> SegmentLedgerEntry:
        """Records or updates a segment entry based on an ingested audio contract."""
        c_hash = compute_segment_content_hash(
            segment_uid=contract.segment_uid,
            spoken_text=contract.spoken_text or contract.literary_text,
            speaker=contract.speaker,
            voice_name=contract.voice_name,
            delivery_style=contract.delivery_style,
            pitch_pct=pitch_pct,
            speed=speed,
        )

        entry = SegmentLedgerEntry(
            segment_uid=contract.segment_uid,
            segment_index=contract.segment_index,
            content_hash=c_hash,
            audio_path=str(contract.audio_path),
            audio_sha256=contract.audio_sha256,
            duration_ms=contract.duration_ms,
            timeline_start_ms=timeline_start_ms,
            timeline_end_ms=timeline_end_ms or (timeline_start_ms + contract.duration_ms),
            speaker=contract.speaker,
            voice_name=contract.voice_name,
            delivery_style=contract.delivery_style,
        )

        self.entries[contract.segment_uid] = entry
        self.updated_at_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if entry.timeline_end_ms > self.total_duration_ms:
            self.total_duration_ms = entry.timeline_end_ms

        return entry

    def diff_contracts(
        self,
        contracts: List[SegmentAudioContract],
        metadata_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> LedgerDiffResult:
        """
        Compares incoming candidate contracts against recorded entries.
        Detects which segments need re-ingestion, which are brand new, and which can be reused.
        """
        metadata_map = metadata_map or {}
        incoming_uids = {c.segment_uid for c in contracts}
        existing_uids = set(self.entries.keys())

        added = list(incoming_uids - existing_uids)
        removed = list(existing_uids - incoming_uids)
        unchanged: List[str] = []
        modified: List[str] = []

        common_uids = incoming_uids & existing_uids
        for c in contracts:
            if c.segment_uid not in common_uids:
                continue
            old_entry = self.entries[c.segment_uid]
            meta = metadata_map.get(c.segment_uid, {})
            current_c_hash = compute_segment_content_hash(
                segment_uid=c.segment_uid,
                spoken_text=c.spoken_text or c.literary_text,
                speaker=c.speaker,
                voice_name=c.voice_name,
                delivery_style=c.delivery_style,
                pitch_pct=meta.get("pitch_pct", 0.0),
                speed=meta.get("speed", 1.0),
            )

            # Check both content specification hash and audio file existence/hash
            audio_file_valid = (
                Path(old_entry.audio_path).is_file() and
                old_entry.audio_sha256 == c.audio_sha256
            )

            if current_c_hash == old_entry.content_hash and audio_file_valid:
                unchanged.append(c.segment_uid)
            else:
                modified.append(c.segment_uid)

        # Sort for deterministic testing
        unchanged.sort()
        modified.sort()
        added.sort()
        removed.sort()

        return LedgerDiffResult(
            unchanged_uids=unchanged,
            modified_uids=modified,
            added_uids=added,
            removed_uids=removed,
        )

    def save_to_disk(self, ledger_path: Path) -> None:
        """Persists the chapter segment ledger as JSON to disk."""
        ledger_path = Path(ledger_path)
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(ledger_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2)
        logger.info(f"[LEDGER] Saved {len(self.entries)} segment entries to {ledger_path.name}")

    @classmethod
    def load_from_disk(cls, ledger_path: Path) -> ChapterSegmentLedger:
        """Loads an existing segment ledger from disk, or initializes an empty one if missing."""
        ledger_path = Path(ledger_path)
        if not ledger_path.is_file():
            # Derive chapter number from filename e.g. chapter_001_segment_ledger.json
            stem = ledger_path.stem
            ch_num = 1
            for part in stem.split("_"):
                if part.isdigit():
                    ch_num = int(part)
                    break
            return cls(chapter_num=ch_num)

        with open(ledger_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
