#!/usr/bin/env python3
"""
Audiobook Factory - Pillar Certification Data Contracts (Pydantic v2).
Defines strongly typed schemas for 8-Pillar Studio Production Certification,
audit diagnostic findings, compliance thresholds, and certification scorecards.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


AuditStatus = Literal["PASSED", "WARNING", "FAILED", "SKIPPED"]


class PillarAuditResult(BaseModel):
    """
    Audit result for a single studio quality pillar.
    """
    model_config = ConfigDict(extra="ignore")

    pillar_id: str = Field(..., description="Pillar identifier (e.g. 'P1_EXTRACTION', 'P6_LOUDNORM')")
    pillar_name: str = Field(..., description="Human-readable pillar name")
    score: float = Field(..., ge=0.0, le=100.0, description="Compliance score (0-100%)")
    status: AuditStatus = Field(default="PASSED", description="Audit outcome status")
    critical_findings: List[str] = Field(default_factory=list, description="Fatal defects or gate violations")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings or optimization notices")
    telemetry: Dict[str, Any] = Field(default_factory=dict, description="Raw metrics and measurements")


class StudioCertificationReport(BaseModel):
    """
    Comprehensive 8-Pillar Studio Certification Scorecard for an audiobook/podcast project.
    """
    model_config = ConfigDict(extra="ignore")

    project_id: str = Field(..., description="Canonical project ID (e.g. 'proj-sample-book')")
    book_title: str = Field(..., description="Book display title")
    timestamp: float = Field(default_factory=time.time, description="Audit execution epoch timestamp")
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Weighted aggregate compliance score (0-100%)")
    is_certified: bool = Field(..., description="True if all critical gates passed without FATAL defects")
    format_mode: str = Field(default="audiobook", description="Audited format mode: 'audiobook', 'podcast', or 'both'")
    pillars: Dict[str, PillarAuditResult] = Field(
        default_factory=dict,
        description="Audit results mapped by pillar_id"
    )
    summary_notes: List[str] = Field(default_factory=list, description="High-level production summary notes")

    def save_to_file(self, filepath: Path) -> Path:
        """Atomically saves certification report to JSON on disk."""
        import uuid, os
        p = Path(filepath).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(f".tmp_cert_{uuid.uuid4().hex[:8]}")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.model_dump(), f, ensure_ascii=False, indent=2)
            tmp.replace(p)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
        return p

    @classmethod
    def load_from_file(cls, filepath: Path) -> StudioCertificationReport:
        """Loads certification report from JSON file."""
        p = Path(filepath).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Certification report not found: {p}")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)
