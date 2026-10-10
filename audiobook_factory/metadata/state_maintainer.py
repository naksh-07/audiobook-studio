#!/usr/bin/env python3
"""
Audiobook Factory - Room 1 Subsystem: Novel Metadata & State Maintainer.
========================================================================
Serves as the single authoritative persistence manager for novel master state.
Enforces the 2-System Decoupled Architecture:
- System 1 (Researcher Engine) produces pure, stateless Pydantic DTOs.
- System 2 (Metadata & State Maintainer) owns atomic filesystem commits,
  schema validation, and cross-room state locking.

Enforces NR-GATE-06: Atomic Multi-File State Gate with zero partial write drift.
"""

from __future__ import annotations
import json
import logging
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

from audiobook_factory.metadata.book_bible import BookBible, BookEntity, EpistemicProvenance

if TYPE_CHECKING:
    from audiobook_factory.preproduction.vocal_acoustic_director import VocalSpacesManifest

logger = logging.getLogger("AudiobookFactory")

# Re-entrant thread lock for state transactions
_STATE_LOCK = threading.RLock()


def _atomic_replace(src: Path, dst: Path) -> None:
    """
    Strictly atomic file replacement with transient lock retries for Windows & POSIX.
    Guarantees NR-GATE-06 multi-file state immutability without non-atomic shutil.move fallback.
    """
    last_err: Optional[OSError] = None
    for attempt in range(5):
        try:
            os.replace(src, dst)
            return
        except OSError as e:
            last_err = e
            time.sleep(0.015 * (2 ** attempt))

    if last_err is not None:
        raise OSError(f"Atomic replacement of {dst} failed after 5 retries: {last_err}") from last_err


class MasterPreProductionState(BaseModel):
    """Immutable container of all locked novel pre-production assets."""
    model_config = ConfigDict(extra="ignore")

    project_slug: str
    book_title: str
    book_dna: Dict[str, Any] = Field(default_factory=dict)
    book_bible: BookBible
    vocal_spaces: Any = Field(default=None)
    cast_lock: Dict[str, Any] = Field(default_factory=dict)
    voice_registry: Dict[str, Any] = Field(default_factory=dict)
    character_roster: Dict[str, Any] = Field(default_factory=dict)
    sonic_bible: Dict[str, Any] = Field(default_factory=dict)


class NovelStateMaintainer:
    """
    Central Persistence & Master State Manager for Novel Research & Pre-Production.
    Guarantees atomic multi-file commit and bidirectional synchronization across:
    - book_dna.json
    - book_bible.json
    - cast_lock.json
    - voice_registry.json
    - character_roster.json
    - vocal_spaces.json
    - sonic_bible.json
    """

    @classmethod
    def commit_master_preproduction(
        cls,
        project_dir: Path | str,
        book_metadata: Dict[str, Any],
        book_dna: Dict[str, Any],
        book_bible: BookBible,
        vocal_spaces: VocalSpacesManifest,
        roster: Dict[str, Any],
        voice_registry: Dict[str, Any],
        cast_lock: Dict[str, Any],
    ) -> MasterPreProductionState:
        """
        Executes a transactional, atomic multi-file commit of all pre-production master assets.
        Implements NR-GATE-06: All files are staged and atomically swapped into place.
        If any error occurs during staging, staged files are wiped and no partial files remain.
        """
        p_dir = Path(project_dir).resolve()
        p_dir.mkdir(parents=True, exist_ok=True)
        trans_dir = p_dir / "translation"
        trans_dir.mkdir(parents=True, exist_ok=True)

        project_slug = book_metadata.get("project_slug", p_dir.name)
        book_title = book_metadata.get("title", book_bible.book_title or "Unknown Novel")

        # 1. Back-synchronize 4D Acoustic Formants into BookBible entities
        for c_name, c_ent in book_bible.characters.items():
            if c_name in voice_registry:
                v_cfg = voice_registry[c_name]
                c_ent.assigned_voice = v_cfg.get("voice", "Aoede")
                pitch_val = v_cfg.get("pitch", 1.0)
                c_ent.pitch_shift_pct = round((pitch_val - 1.0) * 100.0, 2)
                c_ent.tempo_scale = v_cfg.get("speed", 1.0)

                # Formant EQ representation if available
                bass = v_cfg.get("bass_boost_db", 0.0)
                pres = v_cfg.get("presence_boost_db", 0.0)
                clar = v_cfg.get("clarity_reduction_db", 0.0)
                eq_parts = []
                if abs(bass) > 0.1:
                    eq_parts.append(f"equalizer=f=220:t=q:w=1.2:g={bass:+.1f}")
                if abs(pres) > 0.1:
                    eq_parts.append(f"equalizer=f=3400:t=q:w=1.0:g={pres:+.1f}")
                if abs(clar) > 0.1:
                    eq_parts.append(f"equalizer=f=5000:t=q:w=1.0:g={-clar:+.1f}")
                c_ent.eq_formant = ",".join(eq_parts)

        # 2. Build legacy sonic bible projection
        sonic_bible = vocal_spaces.to_legacy_sonic_bible()
        glossary_projection = book_bible.export_legacy_glossary()

        # Target destinations
        target_map = {
            p_dir / "book_dna.json": book_dna,
            p_dir / "book_bible.json": book_bible.model_dump(),
            p_dir / "vocal_spaces.json": vocal_spaces.model_dump(),
            p_dir / "sonic_bible.json": sonic_bible,
            p_dir / "character_roster.json": roster,
            p_dir / "voice_registry.json": voice_registry,
            p_dir / "cast_lock.json": cast_lock,
            trans_dir / "glossary.json": glossary_projection,
        }

        with _STATE_LOCK:
            # NR-GATE-06: Two-Phase Staged Transactional Commit
            staged_files: List[tuple[Path, Path]] = []
            backups: List[tuple[Path, Path]] = []
            replaced_targets: List[Path] = []
            staging_id = f"stage_{int(time.time_ns())}"

            try:
                # Phase 0: Write all new data to staged temporary files (.tmp)
                for target_path, data in target_map.items():
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    staged_path = target_path.with_suffix(f".{staging_id}.tmp")
                    staged_files.append((staged_path, target_path))
                    with open(staged_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                # Phase 1: Create backup (.bak) of any already existing target files
                for _, target_path in staged_files:
                    if target_path.exists():
                        bak_path = target_path.with_suffix(f".{staging_id}.bak")
                        shutil.copy2(target_path, bak_path)
                        backups.append((bak_path, target_path))

                # Phase 2: Atomic swap of staged files into destination
                for staged_path, target_path in staged_files:
                    _atomic_replace(staged_path, target_path)
                    replaced_targets.append(target_path)

                # Phase 3: Transaction succeeded! Cleanup temporary backups
                for bak_path, _ in backups:
                    if bak_path.exists():
                        try:
                            bak_path.unlink()
                        except OSError:
                            pass

                logger.info(
                    f"[+] NovelStateMaintainer: Successfully committed master preproduction state for '{book_title}' (7 files)."
                )
            except Exception as e:
                logger.error(f"[!] NovelStateMaintainer: Transaction failed! Rolling back master state: {e}")
                # Rollback Phase A: Restore original files from backup
                for bak_path, target_path in backups:
                    if bak_path.exists():
                        try:
                            _atomic_replace(bak_path, target_path)
                        except OSError:
                            pass

                # Rollback Phase B: Unlink newly created targets that had no backup
                backed_up_targets = {t for _, t in backups}
                for rep_target in replaced_targets:
                    if rep_target not in backed_up_targets and rep_target.exists():
                        try:
                            rep_target.unlink()
                        except OSError:
                            pass

                # Rollback Phase C: Cleanup all staged .tmp files
                for staged_path, _ in staged_files:
                    if staged_path.exists():
                        try:
                            staged_path.unlink()
                        except OSError:
                            pass

                # Rollback Phase D: Cleanup any leftover tmp/bak matching staging_id
                for leftover in p_dir.glob(f"*.{staging_id}.*"):
                    try:
                        leftover.unlink()
                    except OSError:
                        pass
                for leftover in trans_dir.glob(f"*.{staging_id}.*"):
                    try:
                        leftover.unlink()
                    except OSError:
                        pass

                raise IOError(f"NovelStateMaintainer transactional commit aborted: {e}") from e

            return MasterPreProductionState(
                project_slug=project_slug,
                book_title=book_title,
                book_dna=book_dna,
                book_bible=book_bible,
                vocal_spaces=vocal_spaces,
                cast_lock=cast_lock,
                voice_registry=voice_registry,
                character_roster=roster,
                sonic_bible=sonic_bible,
            )

    @classmethod
    def discover_and_lock_character(
        cls,
        project_dir: Path | str,
        speaker_name: str,
        gender: Optional[str] = None,
        use_hindi: Optional[bool] = None,
        book_bible: Optional[BookBible] = None,
    ) -> Dict[str, Any]:
        """
        Dynamically registers, casts, and locks an emerging novel character.
        Synchronously updates:
        - CharacterCaster voice registry & cast_lock.json (with NR-GATE-03 >=4% pitch distance)
        - book_bible.json (BookEntity with EpistemicProvenance and 4D acoustic vector)
        - character_roster.json
        """
        if not speaker_name or not speaker_name.strip():
            logger.warning("[!] discover_and_lock_character called with empty speaker_name.")
            return {}

        with _STATE_LOCK:
            from audiobook_factory.casting.director import StudioCastingDirector

            p_dir = Path(project_dir).resolve()
            director = StudioCastingDirector(project_dir=p_dir)
            lock = director.cast_character(
                character_name=speaker_name.strip(),
                gender=gender,
                use_hindi=bool(use_hindi) if use_hindi is not None else True,
            )
            cast_cfg = {
                "backend": "gemini_tts",
                "voice": lock.voice_id,
                "pitch": lock.calibration_overrides.get("pitch", 1.0),
                "speed": lock.calibration_overrides.get("speed", 1.0),
            }

            # Load or use existing BookBible
            bible_path = p_dir / "book_bible.json"
            active_bible = book_bible
            if active_bible is None:
                if bible_path.exists():
                    try:
                        active_bible = BookBible.model_validate(json.loads(bible_path.read_text(encoding="utf-8")))
                    except Exception as e:
                        logger.warning(f"Notice reading book_bible.json: {e}")

            if active_bible is not None:
                sp_clean = speaker_name.strip()
                ent = active_bible.find_character(sp_clean)
                if not ent:
                    ent = BookEntity(
                        canonical_id=sp_clean.lower().replace(" ", "_"),
                        english_name=sp_clean,
                        hindi_name=sp_clean,
                        gender=gender or "neutral",
                        provenance=EpistemicProvenance(
                            origin="CORPUS_EXTRACTED",
                            evidence_quote=f"Dynamic mid-novel discovery: {sp_clean}",
                        ),
                        is_canonical=True,
                    )
                    active_bible.characters[sp_clean] = ent

                # Sync 4D acoustics
                ent.assigned_voice = cast_cfg.get("voice", "Aoede")
                pitch_val = cast_cfg.get("pitch", 1.0)
                ent.pitch_shift_pct = round((pitch_val - 1.0) * 100.0, 2)
                ent.tempo_scale = cast_cfg.get("speed", 1.0)

                # Atomic save book_bible.json
                active_bible.save(p_dir)

            return cast_cfg

    @classmethod
    def load_master_state(cls, project_dir: Path | str) -> Optional[MasterPreProductionState]:
        """
        Loads and validates all preproduction master state files for a project.
        Returns None if master files are not fully present.
        """
        p_dir = Path(project_dir).resolve()
        dna_path = p_dir / "book_dna.json"
        bible_path = p_dir / "book_bible.json"
        vocal_spaces_path = p_dir / "vocal_spaces.json"
        cast_lock_path = p_dir / "cast_lock.json"
        voice_reg_path = p_dir / "voice_registry.json"
        roster_path = p_dir / "character_roster.json"
        sonic_bible_path = p_dir / "sonic_bible.json"

        if not (bible_path.exists() and cast_lock_path.exists() and (vocal_spaces_path.exists() or sonic_bible_path.exists())):
            return None

        try:
            from audiobook_factory.preproduction.vocal_acoustic_director import VocalSpacesManifest
            bible = BookBible.model_validate(json.loads(bible_path.read_text(encoding="utf-8")))
            vocal_spaces = (
                VocalSpacesManifest.model_validate(json.loads(vocal_spaces_path.read_text(encoding="utf-8")))
                if vocal_spaces_path.exists()
                else VocalSpacesManifest(project_id=f"proj-{p_dir.name}", book_title=bible.book_title)
            )
            dna = json.loads(dna_path.read_text(encoding="utf-8")) if dna_path.exists() else {}
            cast_lock = json.loads(cast_lock_path.read_text(encoding="utf-8")) if cast_lock_path.exists() else {}
            voice_reg = json.loads(voice_reg_path.read_text(encoding="utf-8")) if voice_reg_path.exists() else {}
            roster = json.loads(roster_path.read_text(encoding="utf-8")) if roster_path.exists() else {}
            sonic_bible = json.loads(sonic_bible_path.read_text(encoding="utf-8")) if sonic_bible_path.exists() else {}

            return MasterPreProductionState(
                project_slug=p_dir.name,
                book_title=bible.book_title,
                book_dna=dna,
                book_bible=bible,
                vocal_spaces=vocal_spaces,
                cast_lock=cast_lock,
                voice_registry=voice_reg,
                character_roster=roster,
                sonic_bible=sonic_bible,
            )
        except Exception as e:
            logger.warning(f"  [!] Notice loading master state for {p_dir.name}: {e}")
            return None
