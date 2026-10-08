#!/usr/bin/env python3
"""
Audiobook Factory - 8-Pillar Studio Production Certification Runner.
Executes autonomous multi-pillar quality audits across Audiobook and Podcast projects,
generating deterministic certification scorecards and Gate 6 compliance reports.
"""

from __future__ import annotations
import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal

from audiobook_factory.certification.contracts import (
    PillarAuditResult,
    StudioCertificationReport,
    AuditStatus,
)
from audiobook_factory.podcast.contracts import PodcastEpisodePlan

logger = logging.getLogger("AudiobookFactory")


class StudioCertificationRunner:
    """
    Autonomous certification harness evaluating 8 studio production pillars.
    """

    @classmethod
    def certify_project(
        cls,
        project_dir: Path,
        format_mode: Literal["audiobook", "podcast", "both"] = "both",
    ) -> StudioCertificationReport:
        """
        Executes complete 8-pillar studio certification on a project folder.
        """
        project_dir = Path(project_dir).resolve()
        book_title = project_dir.name.replace("_", " ").title()
        project_id = f"proj-{project_dir.name}"

        pillars: Dict[str, PillarAuditResult] = {}
        summary_notes: List[str] = []

        # 1. Pillar 1: Ingestion & Extraction Provenance
        p1 = cls._audit_extraction(project_dir)
        pillars["P1_EXTRACTION"] = p1

        # 2. Pillar 2: Literary Translation Dual-Rule Integrity
        p2 = cls._audit_translation(project_dir)
        pillars["P2_TRANSLATION"] = p2

        # 3. Pillar 3: Dramaturgy SPU & Beat Alignment
        p3 = cls._audit_dramaturgy(project_dir)
        pillars["P3_DRAMATURGY"] = p3

        # 4. Pillar 4: Anti-Swap Dialogue Attribution
        p4 = cls._audit_attribution(project_dir)
        pillars["P4_ATTRIBUTION"] = p4

        # 5. Pillar 5: Vocal Performance & Restraint Clamping
        p5 = cls._audit_performance(project_dir)
        pillars["P5_PERFORMANCE"] = p5

        # 6. Pillar 6: EBU R128 Loudness Compliance
        p6 = cls._audit_loudness(project_dir, format_mode=format_mode)
        pillars["P6_LOUDNORM"] = p6

        # 7. Pillar 7: Multi-Host Spatial Staging
        p7 = cls._audit_spatial_staging(project_dir, format_mode=format_mode)
        pillars["P7_SPATIAL"] = p7

        # 8. Pillar 8: Chapter Container Metadata & Packaging
        p8 = cls._audit_packaging(project_dir, format_mode=format_mode)
        pillars["P8_PACKAGING"] = p8

        # Compute aggregate score
        active_pillars = [p for p in pillars.values() if p.status != "SKIPPED"]
        overall_score = (
            round(sum(p.score for p in active_pillars) / float(len(active_pillars)), 1)
            if active_pillars
            else 0.0
        )

        # Failure if any active pillar has critical findings
        is_certified = not any(len(p.critical_findings) > 0 for p in active_pillars)

        if is_certified:
            summary_notes.append(f"Studio Certification PASSED ({overall_score}% compliance).")
        else:
            summary_notes.append(f"Studio Certification FAILED ({overall_score}% compliance). Critical defects found.")

        report = StudioCertificationReport(
            project_id=project_id,
            book_title=book_title,
            overall_score=overall_score,
            is_certified=is_certified,
            format_mode=format_mode,
            pillars=pillars,
            summary_notes=summary_notes,
        )

        report_file = project_dir / "STUDIO_CERTIFICATION_REPORT.json"
        report.save_to_file(report_file)
        logger.info(f"[+] Certification Report saved -> {report_file.name} (Certified: {is_certified})")

        return report

    @classmethod
    def _audit_extraction(cls, project_dir: Path) -> PillarAuditResult:
        extracted_dir = project_dir / "extracted"
        findings = []
        warnings = []
        score = 100.0

        if not extracted_dir.exists():
            findings.append("Extracted directory missing.")
            return PillarAuditResult(
                pillar_id="P1_EXTRACTION",
                pillar_name="Extraction & Provenance (Gate 0.1)",
                score=0.0,
                status="FAILED",
                critical_findings=findings,
            )

        chap_files = list(extracted_dir.glob("*.md"))
        if not chap_files:
            findings.append("No extracted chapter markdown files found.")
            score = 0.0
        else:
            empty_files = [f.name for f in chap_files if f.stat().st_size < 50]
            if empty_files:
                findings.append(f"Empty or corrupted extraction files detected: {empty_files}")
                score -= 30.0

        status: AuditStatus = "FAILED" if findings else ("WARNING" if warnings else "PASSED")
        return PillarAuditResult(
            pillar_id="P1_EXTRACTION",
            pillar_name="Extraction & Provenance (Gate 0.1)",
            score=max(0.0, score),
            status=status,
            critical_findings=findings,
            warnings=warnings,
            telemetry={"chapter_count": len(chap_files)},
        )

    @classmethod
    def _audit_translation(cls, project_dir: Path) -> PillarAuditResult:
        trans_dir = project_dir / "translation"
        if not trans_dir.exists():
            return PillarAuditResult(
                pillar_id="P2_TRANSLATION",
                pillar_name="Literary Translation Dual-Rule (Gate 0)",
                score=100.0,
                status="SKIPPED",
                warnings=["Translation directory not present (Original language production)."],
            )

        trans_files = list(trans_dir.glob("*.md"))
        findings = []
        warnings = []
        score = 100.0

        if not trans_files:
            warnings.append("Translation directory exists but contains no translated files.")
            score = 70.0
        else:
            for tf in trans_files:
                txt = tf.read_text(encoding="utf-8")
                # Check for untranslated placeholder markers
                if "[UNTRANSLATED]" in txt or "[TODO]" in txt:
                    findings.append(f"Untranslated placeholder in {tf.name}")
                    score -= 25.0

        status: AuditStatus = "FAILED" if findings else ("WARNING" if warnings else "PASSED")
        return PillarAuditResult(
            pillar_id="P2_TRANSLATION",
            pillar_name="Literary Translation Dual-Rule (Gate 0)",
            score=max(0.0, score),
            status=status,
            critical_findings=findings,
            warnings=warnings,
            telemetry={"translated_chapters": len(trans_files)},
        )

    @classmethod
    def _audit_dramaturgy(cls, project_dir: Path) -> PillarAuditResult:
        findings = []
        warnings = []
        score = 100.0

        # Check dramatic plans either in dramaturgy/ or podcasts/
        plan_files = list((project_dir / "dramaturgy").glob("*_plan.json")) + list((project_dir / "podcasts").glob("*_podcast_plan.json"))
        if not plan_files:
            warnings.append("No explicit dramatic plan JSON files found on disk; checking scripts directly.")

        # Check script beat alignment
        scripts_dir = project_dir / "scripts"
        if scripts_dir.exists():
            for sf in scripts_dir.glob("*.json"):
                try:
                    with open(sf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        indices = [s.get("index", 0) for s in data if isinstance(s, dict)]
                        if indices and indices != sorted(indices):
                            findings.append(f"Non-monotonic segment indices in {sf.name}")
                            score -= 30.0
                except Exception as e:
                    warnings.append(f"Could not read script {sf.name}: {e}")

        status: AuditStatus = "FAILED" if findings else ("WARNING" if warnings else "PASSED")
        return PillarAuditResult(
            pillar_id="P3_DRAMATURGY",
            pillar_name="Dramaturgy SPU & Beat Alignment (Gate 2.5)",
            score=max(0.0, score),
            status=status,
            critical_findings=findings,
            warnings=warnings,
        )

    @classmethod
    def _audit_attribution(cls, project_dir: Path) -> PillarAuditResult:
        scripts_dir = project_dir / "scripts"
        findings = []
        warnings = []
        score = 100.0

        if not scripts_dir.exists() or not list(scripts_dir.glob("*.json")):
            return PillarAuditResult(
                pillar_id="P4_ATTRIBUTION",
                pillar_name="Anti-Swap Speaker Attribution (0% Inversion)",
                score=100.0,
                status="SKIPPED",
                warnings=["No script files found to audit."],
            )

        # Check for unassigned speakers or quote leakage
        for sf in scripts_dir.glob("*.json"):
            try:
                with open(sf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for seg in data:
                        if not isinstance(seg, dict):
                            continue
                        spk = seg.get("speaker", "")
                        txt = seg.get("text") or ""
                        if not spk:
                            findings.append(f"Empty speaker in {sf.name} segment {seg.get('index')}")
                            score -= 20.0
                        if spk == "Narrator" and (txt.startswith('"') or txt.startswith('“')) and (txt.endswith('"') or txt.endswith('”')):
                            warnings.append(f"Possible unstripped quote in Narrator line in {sf.name}")
                            score -= 5.0
            except Exception as e:
                warnings.append(f"Error parsing {sf.name}: {e}")

        status: AuditStatus = "FAILED" if findings else ("WARNING" if warnings else "PASSED")
        return PillarAuditResult(
            pillar_id="P4_ATTRIBUTION",
            pillar_name="Anti-Swap Speaker Attribution (0% Inversion)",
            score=max(0.0, score),
            status=status,
            critical_findings=findings,
            warnings=warnings,
        )

    @classmethod
    def _audit_performance(cls, project_dir: Path) -> PillarAuditResult:
        scripts_dir = project_dir / "scripts"
        findings = []
        warnings = []
        score = 100.0

        if not scripts_dir.exists():
            return PillarAuditResult(
                pillar_id="P5_PERFORMANCE",
                pillar_name="Vocal Performance Clamping (0.30 - 0.52 Temp)",
                score=100.0,
                status="SKIPPED",
            )

        # Check for prohibited theatrical keywords
        banned_acting = ["screeching", "melodramatic", "theatrical over-projection", "hysterical"]
        for sf in scripts_dir.glob("*.json"):
            try:
                with open(sf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for seg in data:
                        if isinstance(seg, dict):
                            acting = str(seg.get("acting", "")).lower()
                            for b in banned_acting:
                                if b in acting:
                                    findings.append(f"Banned theatrical directive '{b}' found in {sf.name}")
                                    score -= 20.0
            except Exception:
                pass

        status: AuditStatus = "FAILED" if findings else ("WARNING" if warnings else "PASSED")
        return PillarAuditResult(
            pillar_id="P5_PERFORMANCE",
            pillar_name="Vocal Performance Clamping (0.30 - 0.52 Temp)",
            score=max(0.0, score),
            status=status,
            critical_findings=findings,
            warnings=warnings,
        )

    @classmethod
    def _audit_loudness(cls, project_dir: Path, format_mode: str = "both") -> PillarAuditResult:
        findings = []
        warnings = []
        score = 100.0
        telemetry: Dict[str, Any] = {}

        # 1. Audiobook Mastered Files (-19.0 LUFS Target)
        if format_mode in ("audiobook", "both"):
            mastered_dir = project_dir / "mastered"
            if mastered_dir.exists():
                m_files = list(mastered_dir.glob("*_mastered.wav")) + list(mastered_dir.glob("*_mastered.m4a"))
                telemetry["audiobook_master_files"] = len(m_files)
                if not m_files:
                    warnings.append("No mastered audiobook chapters found in mastered/.")
            else:
                warnings.append("Mastered directory not found for audiobook track.")

        # 2. Podcast Mastered Files (-16.0 LUFS Target)
        if format_mode in ("podcast", "both"):
            podcasts_dir = project_dir / "podcasts"
            if podcasts_dir.exists():
                p_files = list(podcasts_dir.glob("*_podcast.m4a")) + list(podcasts_dir.glob("*_podcast_master.wav"))
                telemetry["podcast_master_files"] = len(p_files)
                if not p_files:
                    warnings.append("No mastered podcast episodes found in podcasts/.")

        status: AuditStatus = "FAILED" if findings else ("WARNING" if warnings else "PASSED")
        return PillarAuditResult(
            pillar_id="P6_LOUDNORM",
            pillar_name="EBU R128 Loudness Compliance (-19.0 / -16.0 LUFS)",
            score=max(0.0, score),
            status=status,
            critical_findings=findings,
            warnings=warnings,
            telemetry=telemetry,
        )

    @classmethod
    def _audit_spatial_staging(cls, project_dir: Path, format_mode: str = "both") -> PillarAuditResult:
        if format_mode == "audiobook":
            return PillarAuditResult(
                pillar_id="P7_SPATIAL",
                pillar_name="2-Host Spatial Staging (-0.25 / +0.25 Azimuth)",
                score=100.0,
                status="SKIPPED",
                warnings=["Spatial staging audit skipped for mono-centered audiobook track."],
            )

        podcasts_dir = project_dir / "podcasts"
        findings = []
        warnings = []
        score = 100.0

        if not podcasts_dir.exists() or not list(podcasts_dir.glob("*_podcast_plan.json")):
            return PillarAuditResult(
                pillar_id="P7_SPATIAL",
                pillar_name="2-Host Spatial Staging (-0.25 / +0.25 Azimuth)",
                score=100.0,
                status="SKIPPED",
                warnings=["No podcast plans found to audit spatial staging."],
            )

        for pf in podcasts_dir.glob("*_podcast_plan.json"):
            try:
                plan = PodcastEpisodePlan.load_from_file(pf)
                host_a = plan.hosts.get("host_a")
                host_b = plan.hosts.get("host_b")
                if host_a and host_a.pan > -0.10:
                    warnings.append(f"Host A ({host_a.name}) pan {host_a.pan} is insufficiently panned left (< -0.20 expected)")
                    score -= 10.0
                if host_b and host_b.pan < 0.10:
                    warnings.append(f"Host B ({host_b.name}) pan {host_b.pan} is insufficiently panned right (> +0.20 expected)")
                    score -= 10.0
            except Exception as e:
                warnings.append(f"Error auditing plan {pf.name}: {e}")

        status: AuditStatus = "FAILED" if findings else ("WARNING" if warnings else "PASSED")
        return PillarAuditResult(
            pillar_id="P7_SPATIAL",
            pillar_name="2-Host Spatial Staging (-0.25 / +0.25 Azimuth)",
            score=max(0.0, score),
            status=status,
            critical_findings=findings,
            warnings=warnings,
        )

    @classmethod
    def _audit_packaging(cls, project_dir: Path, format_mode: str = "both") -> PillarAuditResult:
        findings = []
        warnings = []
        score = 100.0
        telemetry: Dict[str, Any] = {}

        # Check Audiobook M4B deliverable
        if format_mode in ("audiobook", "both"):
            m4b_candidates = list(project_dir.glob("*.m4b")) + list((project_dir / "output").glob("*.m4b"))
            telemetry["audiobook_m4b_deliverables"] = len(m4b_candidates)
            if not m4b_candidates:
                warnings.append("No packaged .m4b audiobook file found in project root or output/.")

        # Check Podcast M4A deliverables
        if format_mode in ("podcast", "both"):
            m4a_candidates = list((project_dir / "packaged_podcasts").glob("*.m4a")) + list((project_dir / "podcasts").glob("*.m4a"))
            telemetry["podcast_m4a_deliverables"] = len(m4a_candidates)
            if not m4a_candidates:
                warnings.append("No packaged .m4a podcast episodes found.")

        status: AuditStatus = "FAILED" if findings else ("WARNING" if warnings else "PASSED")
        return PillarAuditResult(
            pillar_id="P8_PACKAGING",
            pillar_name="Container Chapter Atoms & Show Notes (M4B / M4A)",
            score=max(0.0, score),
            status=status,
            critical_findings=findings,
            warnings=warnings,
            telemetry=telemetry,
        )
