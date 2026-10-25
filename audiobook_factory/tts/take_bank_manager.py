#!/usr/bin/env python3
"""
Audiobook Factory - TakeBank Auditioning Manager.
Coordinates multi-take candidate synthesis and selection for high-priority dramatic screenplay turns:
Standard (1 take), Focused (2 takes), High (3 takes), Climactic (4 takes).
"""

from __future__ import annotations
import math
import struct
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union

from audiobook_factory.logger import logger
from audiobook_factory.tts.contracts import (
    CanonicalTTSRequest,
    DeliveryIntent,
    SynthesizedAudioChunk,
    AudioValidationResult,
    TTSPipelineMode,
)
from audiobook_factory.tts.core_orchestrator import TTSCoreOrchestrator


class CandidateTake:
    """Represents a generated candidate take variant with quality score and selection status."""
    def __init__(
        self,
        take_id: str,
        variant_type: str,
        chunk: SynthesizedAudioChunk,
        validation: Optional[AudioValidationResult] = None,
        score: float = 0.0,
        is_selected: bool = False,
    ):
        self.take_id = take_id
        self.variant_type = variant_type
        self.chunk = chunk
        self.validation = validation
        self.score = score
        self.is_selected = is_selected


class TakeBankManager:
    """
    Manages multi-take generation, evaluation, and selection for studio screenplay synthesis.
    """

    VARIANT_STYLES: Dict[str, Dict[str, Any]] = {
        "standard": {
            "delivery_style": "standard",
            "emotion": "neutral",
            "intensity": "medium",
            "temperature_target": 0.35,
        },
        "restraint": {
            "delivery_style": "restraint",
            "emotion": "suppressed",
            "intensity": "low",
            "temperature_target": 0.32,
        },
        "vulnerable": {
            "delivery_style": "vulnerable",
            "emotion": "fragile",
            "intensity": "medium",
            "temperature_target": 0.38,
        },
        "exposed": {
            "delivery_style": "exposed",
            "emotion": "intense",
            "intensity": "high",
            "temperature_target": 0.45,
        },
    }

    PRIORITY_VARIANTS: Dict[str, List[str]] = {
        "standard": ["standard"],
        "focused": ["standard", "restraint"],
        "high": ["standard", "restraint", "vulnerable"],
        "climactic": ["standard", "restraint", "vulnerable", "exposed"],
    }

    def __init__(self, orchestrator: Optional[TTSCoreOrchestrator] = None):
        self.orchestrator = orchestrator or TTSCoreOrchestrator()

    def generate_candidate_takes(
        self,
        base_request: CanonicalTTSRequest,
        priority: str = "standard",
        model: str = "gemini-3.8-flash-tts",
    ) -> List[CandidateTake]:
        """
        Generates candidate takes based on performance priority and evaluates their quality.
        """
        prio_key = priority.lower().strip()
        variants_to_generate = self.PRIORITY_VARIANTS.get(prio_key, ["standard"])

        candidate_requests: List[Tuple[str, CanonicalTTSRequest]] = []

        for v_type in variants_to_generate:
            cfg = self.VARIANT_STYLES.get(v_type, self.VARIANT_STYLES["standard"])
            intent = DeliveryIntent(
                emotion=cfg["emotion"],
                delivery_style=cfg["delivery_style"],
                intensity=cfg["intensity"],
                pacing_multiplier=base_request.delivery_intent.pacing_multiplier,
                proximity=base_request.delivery_intent.proximity,
            )

            # Build variant request
            variant_uid = f"{base_request.segment_uid}_take_{v_type}"
            req = CanonicalTTSRequest(
                literary_text=base_request.literary_text,
                spoken_text=base_request.spoken_text,
                voice_id=base_request.voice_id,
                segment_uid=variant_uid,
                speaker=base_request.speaker,
                delivery_intent=intent,
                sample_rate=base_request.sample_rate,
                pipeline_mode=TTSPipelineMode.MULTI_CAST,
                chapter_num=base_request.chapter_num,
                scene_num=base_request.scene_num,
            )
            candidate_requests.append((v_type, req))

        # Synthesize all candidate requests concurrently
        raw_requests = [r for _, r in candidate_requests]
        batch_results = self.orchestrator.synthesize_batch(raw_requests, model=model)

        candidate_takes: List[CandidateTake] = []
        for (v_type, req), (_, chunk, validation) in zip(candidate_requests, batch_results):
            score = self._score_take(chunk, validation, v_type)
            candidate_takes.append(
                CandidateTake(
                    take_id=req.segment_uid,
                    variant_type=v_type,
                    chunk=chunk,
                    validation=validation,
                    score=score,
                    is_selected=False,
                )
            )

        # Select the take with highest score
        if candidate_takes:
            best_take = max(candidate_takes, key=lambda t: t.score)
            best_take.is_selected = True

        return candidate_takes

    def select_best_take(
        self,
        base_request: CanonicalTTSRequest,
        priority: str = "standard",
        model: str = "gemini-3.8-flash-tts",
    ) -> Tuple[SynthesizedAudioChunk, Optional[AudioValidationResult], List[CandidateTake]]:
        """
        Convenience method that generates candidate takes and returns the selected best take.
        """
        takes = self.generate_candidate_takes(base_request, priority=priority, model=model)
        if not takes:
            raise RuntimeError(
                f"No candidate takes were successfully generated for request '{base_request.spoken_text[:30]}...'."
            )
        selected = next((t for t in takes if t.is_selected), takes[0])
        return selected.chunk, selected.validation, takes

    @staticmethod
    def _score_take(
        chunk: SynthesizedAudioChunk,
        validation: Optional[AudioValidationResult],
        variant_type: str,
    ) -> float:
        """
        Scores candidate take on 0-100 scale based on quality gate score, duration, and SNR.
        """
        score = 80.0

        if validation:
            if validation.passed:
                score += 15.0
            else:
                score -= 40.0
            if validation.tier1_acoustic_passed and validation.tier2_phonetic_passed:
                score += 5.0

        # Penalize unnaturally short (<0.3s) or excessively long (>60s) takes
        if chunk.duration_sec < 0.3:
            score -= 30.0
        elif chunk.duration_sec > 45.0:
            score -= 10.0

        # Prioritize restraint & standard slightly for stability
        if variant_type in ("standard", "restraint"):
            score += 2.0

        return max(0.0, min(100.0, score))
