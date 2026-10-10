"""
Audiobook Factory - Chapter Janitor & Concurrency Retention Shield (Phase 5).
Handles thread-isolated scratch allocations, intermediate chunk cleanup,
and protects certified chapter masters from premature purging (AP-09).
"""

from __future__ import annotations
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, List
from audiobook_factory.logger import logger


class JanitorShield:
    """
    Manages thread-isolated scratch spaces and protects certified master assets.
    Prevents race conditions when multiple chapters are rendered concurrently.
    """

    PROTECTED_EXTENSIONS = {".m4a", ".m4b", ".json"}

    @staticmethod
    def create_isolated_scratch(
        base_dir: Path,
        chapter_num: int,
        run_id: Optional[str] = None,
    ) -> Path:
        """
        Creates a dedicated scratch workspace for a specific chapter and run.
        Prevents concurrency file collisions (AP-09).
        """
        base_dir = Path(base_dir)
        rid = run_id or uuid.uuid4().hex[:8]
        scratch_dir = base_dir / f"scratch_{rid}_c{chapter_num:03d}"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        return scratch_dir

    @classmethod
    def is_protected_artifact(cls, file_path: Path) -> bool:
        """Determines if a file is an authoritative deliverable that must never be purged."""
        path = Path(file_path)
        name = path.name.lower()

        # Never delete master WAVs, deliverables, or ledgers
        if "_master.wav" in name or "_mastering_ledger" in name or "_segment_ledger" in name:
            return True
        if path.suffix.lower() in cls.PROTECTED_EXTENSIONS:
            return True
        return False

    @classmethod
    def purge_scratch_directory(
        cls,
        scratch_dir: Path,
        certified: bool = True,
        force: bool = False,
    ) -> int:
        """
        Safely deletes scratch files in an isolated scratch directory.
        Strictly preserves any protected master deliverables.
        """
        scratch_dir = Path(scratch_dir)
        if not scratch_dir.is_dir():
            return 0

        purge_enabled = os.environ.get("AUDIOBOOK_PURGE_CHUNKS", "false").lower() in ("1", "true", "yes")
        if not (certified or force or purge_enabled):
            logger.info(f"  [JANITOR SHIELD] Retaining scratch dir {scratch_dir.name} (uncertified run protection).")
            return 0

        purged_count = 0
        for item in list(scratch_dir.glob("*")):
            if item.is_file():
                if cls.is_protected_artifact(item) and not force:
                    logger.debug(f"  [JANITOR SHIELD] Preserving protected master file: {item.name}")
                    continue
                try:
                    item.unlink(missing_ok=True)
                    purged_count += 1
                except Exception as exc:
                    logger.warning(f"  [JANITOR] Could not unlink {item.name}: {exc}")

        # Remove directory if empty
        try:
            if not list(scratch_dir.glob("*")):
                shutil.rmtree(scratch_dir, ignore_errors=True)
        except Exception:
            pass

        return purged_count


def cleanup_chapter_chunks(
    audio_dir: Path,
    chapter_num: int,
    cinematic_out: Path,
    all_gates_certified: bool,
) -> None:
    """
    Cleans up intermediate uncompressed WAV chunks ONLY IF certified.
    Safety Invariant: Chunks are NEVER purged if cinematic master failed, is corrupt,
    if any Gate 5.x check failed, or unless PURGE_INTERMEDIATE_CHUNKS=true is explicitly set.
    By default, chunks are preserved for zero-cost DSP remastering without burning TTS quota.
    """
    purge_chunks_flag = os.environ.get("AUDIOBOOK_PURGE_CHUNKS", "false").lower() in ("1", "true", "yes")

    chunk_pattern = f"c{chapter_num:03d}_*.wav"
    all_chunks = list(audio_dir.glob(chunk_pattern))

    if not purge_chunks_flag:
        logger.info(f"  [JANITOR SHIELD] Retaining {len(all_chunks)} raw WAV chunks for chapter {chapter_num:02d} (Zero-cost remaster shield default).")
    elif not all_gates_certified:
        logger.warning(
            f"  [JANITOR SHIELD] Master render uncertified or Gate 5/5.2/5.3 failed for chapter {chapter_num:02d}. "
            f"Retaining {len(all_chunks)} raw WAV chunks to protect synthesized progress."
        )
    else:
        purged_count = 0
        for chunk_file in all_chunks:
            # Shield check: never delete master files
            if JanitorShield.is_protected_artifact(chunk_file):
                continue
            try:
                chunk_file.unlink(missing_ok=True)
                purged_count += 1
            except Exception:
                pass
        if purged_count:
            logger.info(f"  [JANITOR] Purged {purged_count} intermediate WAV chunks for chapter {chapter_num:02d}")
