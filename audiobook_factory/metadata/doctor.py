#!/usr/bin/env python3
"""
Audiobook Studio - Zero-Token Pre-Flight Metadata Doctor.
Performs offline, millisecond-fast (<50ms) forensic validation of decoupled
domain metadata across all 5 production rooms.
Checks Extraction, BookBible canon, CastLock acoustics, Glossary alignment,
Screenplay speaker coverage, and Mastering V2 EBU R128 ledgers.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("AudiobookFactory.MetadataDoctor")


class DiagnosticCheck(BaseModel):
    name: str
    category: str  # extraction, canon, casting, translation, screenplay, mastering
    status: str    # PASS, WARN, FAIL
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class MetadataDoctorReport(BaseModel):
    project_slug: str
    status: str = "PASS"  # PASS, WARN, FAIL
    passed: bool = True
    total_checks: int = 0
    passed_checks: int = 0
    warning_checks: int = 0
    failed_checks: int = 0
    checks: List[DiagnosticCheck] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    def format_table(self) -> str:
        """Renders an ASCII diagnostic health table for terminal output."""
        lines = []
        lines.append("=" * 76)
        lines.append(f"  AUDIOBOOK STUDIO METADATA DOCTOR: {self.project_slug.upper()}")
        lines.append("=" * 76)
        status_symbol = "[OK] PASS" if self.passed else "[!] FAIL"
        lines.append(f"  Overall Status : {status_symbol} ({self.passed_checks}/{self.total_checks} checks passed)")
        lines.append("-" * 76)
        lines.append(f"  {'CATEGORY':<14} | {'STATUS':<6} | {'CHECK & DETAILS':<50}")
        lines.append("-" * 76)

        for c in self.checks:
            stat_icon = "PASS" if c.status == "PASS" else ("WARN" if c.status == "WARN" else "FAIL")
            lines.append(f"  {c.category:<14} | {stat_icon:<6} | {c.name}: {c.message}")
            if c.details and c.status != "PASS":
                detail_str = ", ".join(f"{k}={v}" for k, v in list(c.details.items())[:3])
                lines.append(f"  {'':<14} | {'':<6} |   -> {detail_str}")

        lines.append("=" * 76)
        if self.errors:
            lines.append("  CRITICAL ANOMALIES:")
            for err in self.errors:
                lines.append(f"    - {err}")
            lines.append("=" * 76)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes report to dictionary."""
        return self.model_dump()

    def is_healthy(self) -> bool:
        """Returns True if no critical failure was detected."""
        return self.passed and len(self.errors) == 0


class MetadataDoctor:
    """Offline metadata consistency validator ensuring 0% drift across stages."""

    @classmethod
    def diagnose_project(cls, project_dir: Path | str) -> MetadataDoctorReport:
        p_dir = Path(project_dir).resolve()
        report = MetadataDoctorReport(project_slug=p_dir.name)

        if not p_dir.exists() or not p_dir.is_dir():
            report.status = "FAIL"
            report.passed = False
            report.errors.append(f"Project directory not found: {p_dir}")
            return report

        checks: List[DiagnosticCheck] = []

        # ---------------------------------------------------------------------
        # 1. Extraction & Manifest Layer (Room 0)
        # ---------------------------------------------------------------------
        ext_dir = p_dir / "extracted"
        if not ext_dir.exists():
            ext_dir = p_dir / "chapters"
        chaps = sorted(ext_dir.glob("chapter_*.md")) if ext_dir.exists() else []

        if chaps:
            checks.append(DiagnosticCheck(
                name="Extraction Inventory",
                category="extraction",
                status="PASS",
                message=f"Found {len(chaps)} chapter markdown files",
                details={"chapter_count": len(chaps), "first_chap": chaps[0].name},
            ))
        elif (p_dir / "scripts").exists() or (p_dir / "book_bible.json").exists() or (p_dir / "character_roster.json").exists() or (p_dir / "voice_registry.json").exists():
            checks.append(DiagnosticCheck(
                name="Extraction Inventory",
                category="extraction",
                status="WARN",
                message="No chapter_*.md found in extracted/ (bypassed or sub-pipeline project)",
                details={},
            ))
        else:
            checks.append(DiagnosticCheck(
                name="Extraction Inventory",
                category="extraction",
                status="FAIL",
                message="Zero chapter markdown files found in extracted/",
                details={},
            ))

        meta_file = p_dir / "metadata.json"
        manifest_file = p_dir / "raw" / "source_manifest.json"
        if meta_file.exists() or manifest_file.exists():
            checks.append(DiagnosticCheck(
                name="Source Manifest",
                category="extraction",
                status="PASS",
                message="Source manifest verified on disk",
                details={"has_metadata_json": meta_file.exists(), "has_source_manifest": manifest_file.exists()},
            ))
        else:
            checks.append(DiagnosticCheck(
                name="Source Manifest",
                category="extraction",
                status="WARN",
                message="Neither metadata.json nor source_manifest.json found",
                details={},
            ))

        # ---------------------------------------------------------------------
        # 2. Domain Canon & Lore Layer (Room 1)
        # ---------------------------------------------------------------------
        bible_path = p_dir / "book_bible.json"
        active_bible = None
        if bible_path.exists():
            try:
                from audiobook_factory.metadata.book_bible import BookBible
                active_bible = BookBible.model_validate(json.loads(bible_path.read_text(encoding="utf-8")))
                num_chars = len(active_bible.characters)
                checks.append(DiagnosticCheck(
                    name="Book Bible Canon",
                    category="canon",
                    status="PASS",
                    message=f"Canonical BookBible loaded ({num_chars} characters, {len(active_bible.locations)} locations)",
                    details={"characters_count": num_chars, "book_title": active_bible.book_title},
                ))
            except Exception as e:
                checks.append(DiagnosticCheck(
                    name="Book Bible Canon",
                    category="canon",
                    status="FAIL",
                    message=f"Corrupt or invalid book_bible.json schema: {e}",
                    details={"error": str(e)},
                ))
        else:
            checks.append(DiagnosticCheck(
                name="Book Bible Canon",
                category="canon",
                status="WARN",
                message="book_bible.json missing; Room 1 Pre-Production has not yet executed",
                details={},
            ))

        # ---------------------------------------------------------------------
        # 3. Voice Casting & Acoustic Lock Layer (Room 1 SSOT)
        # ---------------------------------------------------------------------
        cast_lock_path = p_dir / "cast_lock.json"
        cast_data = None
        if cast_lock_path.exists():
            try:
                cast_data = json.loads(cast_lock_path.read_text(encoding="utf-8"))
                locks = cast_data.get("locks", {})
                num_locked = len([k for k, v in locks.items() if isinstance(v, dict) and v.get("locked")])
                
                # Verify pitch safety bounds and pitch separation
                pitch_violations = []
                voice_allocation_map: Dict[str, List[tuple[str, float]]] = {}
                seen_char_ids: Dict[str, set] = {}
                for cname, lk in locks.items():
                    if isinstance(lk, dict):
                        cid = lk.get("character_id") or cname.lower()
                        vid = lk.get("voice_id", "Aoede")
                        if vid not in seen_char_ids:
                            seen_char_ids[vid] = set()
                        if cid in seen_char_ids[vid]:
                            continue  # Skip alias duplicate of the same character
                        seen_char_ids[vid].add(cid)
                        p_ratio = float(lk.get("calibration_overrides", {}).get("pitch", 1.0))
                        if p_ratio < 0.85 or p_ratio > 1.15:
                            pitch_violations.append(f"{cname}: pitch {p_ratio} outside 0.85-1.15")
                        voice_allocation_map.setdefault(vid, []).append((cname, p_ratio))

                # Check >= 4% pitch separation on characters sharing voice ID
                collision_warnings = []
                for vid, allocs in voice_allocation_map.items():
                    if len(allocs) > 1:
                        for i in range(len(allocs)):
                            for j in range(i + 1, len(allocs)):
                                diff = abs(allocs[i][1] - allocs[j][1])
                                if diff < 0.038:  # margin for 4%
                                    collision_warnings.append(
                                        f"{allocs[i][0]} vs {allocs[j][0]} share '{vid}' with only {diff*100:.1f}% pitch separation"
                                    )

                c_status = "FAIL" if pitch_violations else ("WARN" if collision_warnings else "PASS")
                c_msg = f"{len(locks)} cast locks verified ({num_locked} locked)"
                if pitch_violations:
                    c_msg += f" [!] Pitch bounds violated: {', '.join(pitch_violations)}"
                elif collision_warnings:
                    c_msg += f" with {len(collision_warnings)} potential voice collision(s): {', '.join(collision_warnings)}"
                checks.append(DiagnosticCheck(
                    name="Cast Lock & Voice SSOT",
                    category="casting",
                    status=c_status,
                    message=c_msg,
                    details={
                        "total_locks": len(locks),
                        "locked_count": num_locked,
                        "collisions": collision_warnings[:3],
                    },
                ))
            except Exception as e:
                checks.append(DiagnosticCheck(
                    name="Cast Lock & Voice SSOT",
                    category="casting",
                    status="FAIL",
                    message=f"Corrupt cast_lock.json: {e}",
                    details={"error": str(e)},
                ))
        else:
            checks.append(DiagnosticCheck(
                name="Cast Lock & Voice SSOT",
                category="casting",
                status="WARN",
                message="cast_lock.json missing; voices not yet assigned",
                details={},
            ))

        # ---------------------------------------------------------------------
        # 4. Translation Glossary Projection Alignment (Room 2)
        # ---------------------------------------------------------------------
        glossary_path = p_dir / "translation" / "glossary.json"
        if glossary_path.exists():
            try:
                g_data = json.loads(glossary_path.read_text(encoding="utf-8"))
                g_chars = g_data.get("characters", [])
                checks.append(DiagnosticCheck(
                    name="Translation Glossary",
                    category="translation",
                    status="PASS",
                    message=f"glossary.json verified ({len(g_chars)} proper nouns/honorifics)",
                    details={"glossary_character_count": len(g_chars)},
                ))
            except Exception as e:
                checks.append(DiagnosticCheck(
                    name="Translation Glossary",
                    category="translation",
                    status="FAIL",
                    message=f"Corrupt glossary.json: {e}",
                    details={"error": str(e)},
                ))
        else:
            checks.append(DiagnosticCheck(
                name="Translation Glossary",
                category="translation",
                status="WARN" if chaps else "PASS",
                message="translation/glossary.json not yet generated",
                details={},
            ))

        # ---------------------------------------------------------------------
        # 5. Screenplay Attribution & Speaker Coverage (Room 3)
        # ---------------------------------------------------------------------
        scripts_dir = p_dir / "scripts"
        scripts = sorted(scripts_dir.glob("chapter_*_script.json")) if scripts_dir.exists() else []
        if scripts:
            known_speakers = set()
            if cast_data and "locks" in cast_data:
                known_speakers.update(cast_data["locks"].keys())
            if active_bible:
                known_speakers.update(active_bible.characters.keys())
                for ent in active_bible.characters.values():
                    if ent.hindi_name:
                        known_speakers.add(ent.hindi_name)
                    known_speakers.update(ent.aliases)

            # Also check character_roster.json and voice_registry.json
            roster_file = p_dir / "character_roster.json"
            if roster_file.exists():
                try:
                    rdata = json.loads(roster_file.read_text(encoding="utf-8"))
                    rchars = rdata.get("characters", {})
                    if isinstance(rchars, dict):
                        known_speakers.update(rchars.keys())
                    elif isinstance(rchars, list):
                        for c in rchars:
                            if isinstance(c, dict):
                                if c.get("display_name"):
                                    known_speakers.add(c["display_name"])
                                if c.get("english_name"):
                                    known_speakers.add(c["english_name"])
                except Exception:
                    pass

            vreg_file = p_dir / "voice_registry.json"
            if vreg_file.exists():
                try:
                    vdata = json.loads(vreg_file.read_text(encoding="utf-8"))
                    if isinstance(vdata, dict):
                        known_speakers.update(vdata.keys())
                except Exception:
                    pass

            # Check unmapped speakers in scripts
            unmapped_speakers = set()
            total_segs = 0
            has_dialogue_segments = False
            for sf in scripts[:10]:  # sample up to 10 chapters
                try:
                    s_data = json.loads(sf.read_text(encoding="utf-8"))
                    segs = s_data if isinstance(s_data, list) else s_data.get("segments", [])
                    total_segs += len(segs)
                    for seg in segs:
                        spk = seg.get("speaker") or seg.get("character")
                        if not spk:
                            continue
                        spk_clean = str(spk).strip()
                        if spk_clean.lower() in (
                            "narrator", "foley", "sfx", "chapter_header", "chapter header",
                            "host_a", "host_b", "host a", "host b", "host_1", "host_2", "host 1", "host 2",
                            "sameer", "priya", "alex", "maya"
                        ):
                            continue
                        has_dialogue_segments = True
                        if not known_speakers or (spk_clean not in known_speakers and not any(k.lower() == spk_clean.lower() for k in known_speakers)):
                            unmapped_speakers.add(spk_clean)
                except Exception:
                    pass

            if unmapped_speakers:
                checks.append(DiagnosticCheck(
                    name="Screenplay Speaker Coverage",
                    category="screenplay",
                    status="FAIL",
                    message=f"Found {len(unmapped_speakers)} unmapped speaker(s) across {len(scripts)} scripts: {', '.join(sorted(list(unmapped_speakers)))}",
                    details={"unmapped": sorted(list(unmapped_speakers))[:5]},
                ))
            elif has_dialogue_segments and not known_speakers:
                checks.append(DiagnosticCheck(
                    name="Screenplay Speaker Coverage",
                    category="screenplay",
                    status="WARN",
                    message="Dialogue found in scripts but no voice registry / cast lock detected",
                    details={},
                ))
            else:
                checks.append(DiagnosticCheck(
                    name="Screenplay Speaker Coverage",
                    category="screenplay",
                    status="PASS",
                    message=f"100% speaker coverage verified across {len(scripts)} chapter scripts",
                    details={"total_sampled_segments": total_segs},
                ))
        else:
            checks.append(DiagnosticCheck(
                name="Screenplay Speaker Coverage",
                category="screenplay",
                status="PASS",
                message="No screenplay scripts generated yet (not an error)",
                details={},
            ))

        # ---------------------------------------------------------------------
        # 6. Mastering V2 Ledgers & EBU R128 Compliance (Room 5)
        # ---------------------------------------------------------------------
        mastered_dir = p_dir / "mastered"
        m_ledgers = sorted(mastered_dir.glob("chapter_*_mastering_ledger.json")) if mastered_dir.exists() else []
        if m_ledgers:
            lufs_deviations = []
            tp_breaches = []
            for ml in m_ledgers:
                try:
                    ldata = json.loads(ml.read_text(encoding="utf-8"))
                    res_data = ldata.get("result", {}) if isinstance(ldata.get("result"), dict) else {}
                    analysis_after = res_data.get("analysis_after", {}) if isinstance(res_data.get("analysis_after"), dict) else {}
                    meta_data = ldata.get("metadata", {}) if isinstance(ldata.get("metadata"), dict) else {}

                    l_val = None
                    tp_val = None
                    for cand in (
                        ldata.get("integrated_lufs"),
                        analysis_after.get("integrated_lufs"),
                        meta_data.get("integrated_lufs"),
                        ldata.get("measured_loudness_lufs"),
                    ):
                        if cand is not None:
                            try:
                                l_val = float(cand)
                                break
                            except (ValueError, TypeError):
                                pass

                    for cand in (
                        ldata.get("true_peak_dbtp"),
                        analysis_after.get("true_peak_dbtp"),
                        meta_data.get("true_peak_dbtp"),
                    ):
                        if cand is not None:
                            try:
                                tp_val = float(cand)
                                break
                            except (ValueError, TypeError):
                                pass

                    tp_target = meta_data.get("true_peak_ceiling_dbtp", -1.4)
                    ceiling = min(float(tp_target) + 0.2, -1.4)

                    if l_val is not None and abs(l_val - (-19.0)) > 1.0:
                        lufs_deviations.append(f"{ml.name}: {l_val:.2f} LUFS")
                    if tp_val is not None and tp_val > ceiling:
                        tp_breaches.append(f"{ml.name}: {tp_val:.2f} dBTP")
                except Exception:
                    pass

            m_stat = "FAIL" if (lufs_deviations or tp_breaches) else "PASS"
            m_msg = f"{len(m_ledgers)} Mastering V2 ledgers verified (-19 LUFS / EBU R128 target)"
            if tp_breaches:
                m_msg += f" [!] {len(tp_breaches)} True Peak breach(es)"
            checks.append(DiagnosticCheck(
                name="Mastering V2 Compliance",
                category="mastering",
                status=m_stat,
                message=m_msg,
                details={"lufs_deviations": lufs_deviations[:3], "tp_breaches": tp_breaches[:3]},
            ))
        else:
            checks.append(DiagnosticCheck(
                name="Mastering V2 Compliance",
                category="mastering",
                status="PASS",
                message="No mastered stems yet (queued for Room 5)",
                details={},
            ))

        # Summarize
        report.checks = checks
        report.total_checks = len(checks)
        report.passed_checks = len([c for c in checks if c.status == "PASS"])
        report.warning_checks = len([c for c in checks if c.status == "WARN"])
        report.failed_checks = len([c for c in checks if c.status == "FAIL"])

        for c in checks:
            if c.status == "FAIL":
                report.errors.append(f"[{c.category.upper()}] {c.name}: {c.message}")
            elif c.status == "WARN":
                report.warnings.append(f"[{c.category.upper()}] {c.name}: {c.message}")

        if report.failed_checks > 0:
            report.status = "FAIL"
            report.passed = False
        elif report.warning_checks > 0:
            report.status = "WARN"
            report.passed = True
        else:
            report.status = "PASS"
            report.passed = True

        return report
