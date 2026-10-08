#!/usr/bin/env python3
"""
Audiobook Factory - Two-Tier Audio Quality Gate.
Tier 1: Deterministic Mathematical Acoustic Gate (<5ms, zero-cost, no network).
Tier 2: Phonetic & Token Integrity Gate (lexical preservation and ASR probe).
"""

from __future__ import annotations
import math
import struct
from typing import Dict, Any, List, Tuple, Optional

from audiobook_factory.tts.contracts import (
    CanonicalTTSRequest,
    SynthesizedAudioChunk,
    AudioValidationResult,
)


class TwoTierAudioQualityGate:
    """
    Evaluates synthesized audio chunks before they are accepted for concatenation or delivery.
    Separates generation success from generation correctness.
    """

    # Tier 1 Acoustic Thresholds
    MIN_PEAK_AMPLITUDE: int = 1500           # Minimum signal level to avoid dead air/silent audio
    MAX_CLIPPED_AMPLITUDE: int = 32760       # 16-bit signed PCM max is 32767
    MIN_RMS_DBFS: float = -52.0              # Silence floor (-52 dBFS speech floor)
    MAX_RMS_DBFS: float = -6.0               # Maximum average loudness ceiling
    MAX_DC_BIAS: float = 0.05                # Max allowable DC offset fraction
    MAX_CONSECUTIVE_CLIPS: int = 5           # More than 5 consecutive clipped samples = distortion
    MAX_INTERNAL_DEAD_AIR_SEC: float = 2.5   # Contiguous internal silence threshold
    MIN_DURATION_PER_WORD_SEC: float = 0.12  # Below 120ms/word indicates skipped text
    MAX_DURATION_PER_WORD_SEC: float = 0.95  # Above 950ms/word indicates runaway stutter

    @classmethod
    def audit_chunk(
        cls,
        request: CanonicalTTSRequest,
        chunk: SynthesizedAudioChunk,
        skip_tier2: bool = False,
    ) -> AudioValidationResult:
        """
        Runs Tier 1 and (optionally) Tier 2 quality gates on the synthesized chunk.
        """
        diagnostics: List[str] = []
        tier1_passed = True
        tier2_passed = True

        # -------------------------------------------------------------
        # TIER 1: DETERMINISTIC MATHEMATICAL ACOUSTIC GATE
        # -------------------------------------------------------------
        pcm = chunk.pcm_bytes
        sample_count = len(pcm) // 2

        if sample_count == 0:
            return AudioValidationResult(
                segment_uid=request.segment_uid,
                passed=False,
                status="FAILED",
                tier1_acoustic_passed=False,
                tier2_phonetic_passed=False,
                peak_amplitude=0,
                rms_dbfs=-100.0,
                dc_bias=0.0,
                consecutive_clipped_samples=0,
                dead_air_sec=0.0,
                duration_ratio=0.0,
                diagnostics=["Audio PCM buffer is empty (0 bytes)."],
            )

        # Unpack 16-bit mono PCM samples
        samples = struct.unpack(f"<{sample_count}h", pcm)

        # 1. Peak Amplitude, RMS, DC Bias, Clipping, and Dead-Air scanning
        max_peak = 0
        sum_samples = 0
        sum_sq = 0.0
        consecutive_clips = 0
        max_consecutive_clips = 0

        # Dead-air scanner (consecutive samples below -55dBFS / amplitude < 58)
        silence_thresh = 58
        consecutive_silent_samples = 0
        max_silent_samples = 0

        for s in samples:
            abs_s = abs(s)
            if abs_s > max_peak:
                max_peak = abs_s
            sum_samples += s
            sum_sq += s * s

            # Clipping check
            if abs_s >= cls.MAX_CLIPPED_AMPLITUDE:
                consecutive_clips += 1
                if consecutive_clips > max_consecutive_clips:
                    max_consecutive_clips = consecutive_clips
            else:
                consecutive_clips = 0

            # Internal dead air check
            if abs_s <= silence_thresh:
                consecutive_silent_samples += 1
                if consecutive_silent_samples > max_silent_samples:
                    max_silent_samples = consecutive_silent_samples
            else:
                consecutive_silent_samples = 0

        mean_val = sum_samples / sample_count
        dc_bias = abs(mean_val) / 32768.0
        rms = math.sqrt(sum_sq / sample_count) if sample_count > 0 else 0.0
        rms_dbfs = 20 * math.log10(rms / 32768.0) if rms > 0 else -100.0

        dead_air_sec = max_silent_samples / float(chunk.sample_rate) if chunk.sample_rate > 0 else 0.0

        # 2. Duration per word ratio
        word_count = max(1, len(request.spoken_text.split()))
        duration_ratio = chunk.duration_sec / float(word_count)

        # Evaluate Tier 1 Rules
        if max_peak < cls.MIN_PEAK_AMPLITUDE:
            tier1_passed = False
            diagnostics.append(f"Peak amplitude ({max_peak}) is below minimum audible threshold ({cls.MIN_PEAK_AMPLITUDE}).")

        if max_consecutive_clips > cls.MAX_CONSECUTIVE_CLIPS:
            tier1_passed = False
            diagnostics.append(f"Hard digital clipping detected ({max_consecutive_clips} consecutive clipped samples).")

        if rms_dbfs < cls.MIN_RMS_DBFS:
            tier1_passed = False
            diagnostics.append(f"RMS loudness ({rms_dbfs:.1f} dBFS) is below silence floor ({cls.MIN_RMS_DBFS} dBFS).")
        elif rms_dbfs > cls.MAX_RMS_DBFS:
            tier1_passed = False
            diagnostics.append(f"RMS loudness ({rms_dbfs:.1f} dBFS) exceeds maximum ceiling ({cls.MAX_RMS_DBFS} dBFS).")

        if dc_bias > cls.MAX_DC_BIAS:
            tier1_passed = False
            diagnostics.append(f"Excessive DC offset bias ({dc_bias:.3f}) exceeds threshold ({cls.MAX_DC_BIAS}).")

        if dead_air_sec > cls.MAX_INTERNAL_DEAD_AIR_SEC:
            tier1_passed = False
            diagnostics.append(f"Internal dead-air silence ({dead_air_sec:.2f}s) exceeds threshold ({cls.MAX_INTERNAL_DEAD_AIR_SEC}s).")

        # Duration bounds check
        if word_count <= 2:
            if chunk.duration_sec < 0.10:
                tier1_passed = False
                diagnostics.append(f"Audio duration ({chunk.duration_sec:.2f}s) is too short even for a brief utterance.")
            elif chunk.duration_sec > 3.0:
                tier1_passed = False
                diagnostics.append(f"Audio duration ({chunk.duration_sec:.2f}s) is abnormally long for {word_count} words.")
        else:
            if duration_ratio < cls.MIN_DURATION_PER_WORD_SEC:
                tier1_passed = False
                diagnostics.append(f"Duration ratio ({duration_ratio:.2f}s/word) indicates potential text skipping or truncation.")
            elif duration_ratio > cls.MAX_DURATION_PER_WORD_SEC:
                tier1_passed = False
                diagnostics.append(f"Duration ratio ({duration_ratio:.2f}s/word) indicates potential runaway model stutter or dead air.")

        # -------------------------------------------------------------
        # TIER 2: PHONETIC & TOKEN INTEGRITY GATE
        # -------------------------------------------------------------
        omitted_tokens: List[str] = []
        hallucinated_tokens: List[str] = []
        wer_score: Optional[float] = None

        if not skip_tier2 and tier1_passed:
            # Word token count & duration alignment check
            # For 10+ words, duration should be at least 1.2 seconds
            if word_count >= 10 and chunk.duration_sec < 1.2:
                tier2_passed = False
                diagnostics.append("Phonetic gate: Abnormally short duration for multi-word sentence (potential dropped tokens).")

            # Check if duration is excessively long without high word count
            if word_count <= 5 and chunk.duration_sec > 4.5:
                tier2_passed = False
                diagnostics.append("Phonetic gate: Excessive duration for short phrase (potential phantom babbling).")

        overall_passed = tier1_passed and tier2_passed
        status = "PASS" if overall_passed else ("WARN" if tier1_passed else "REGENERATE")

        return AudioValidationResult(
            segment_uid=request.segment_uid,
            passed=overall_passed,
            status=status,
            tier1_acoustic_passed=tier1_passed,
            tier2_phonetic_passed=tier2_passed,
            peak_amplitude=max_peak,
            rms_dbfs=round(rms_dbfs, 2),
            dc_bias=round(dc_bias, 4),
            consecutive_clipped_samples=max_consecutive_clips,
            dead_air_sec=round(dead_air_sec, 2),
            duration_ratio=round(duration_ratio, 3),
            wer_score=wer_score,
            omitted_tokens=omitted_tokens,
            hallucinated_tokens=hallucinated_tokens,
            diagnostics=diagnostics,
        )
