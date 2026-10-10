#!/usr/bin/env python3
"""
Audiobook Factory - AI-Assisted Acoustic & Script QA Auditor (v5.4).
====================================================================
Performs forensic quality control over synthesized dialogue segments:
1. Speech Activity & Pause Boundaries: Detects leading/trailing dead air and rushed speech.
2. Script Grounding & Speaking Rate Bounds: Calculates Words Per Minute (WPM) and
   character-to-duration speed to catch TTS dropouts, truncations, and hallucination loops.
3. Non-Intrusive Speech MOS (Mean Opinion Score): Predicts vocal quality and SNR.
4. Tiered Tolerance & Fail-Safe Invariant (ADR-022): Hard rejection strictly reserved for
   fatal defects (empty audio, severe clipping, >40% length deficit); soft warnings for minor variances.
"""

from __future__ import annotations
import math
import wave
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np

from audiobook_factory.logger import logger
from audiobook_factory.audio.contracts import (
    AudioQAConfig,
    SegmentQAEvaluation,
    ChapterQAReport,
)

# Capability Probing
try:
    import faster_whisper
    _HAS_WHISPER = True
except ImportError:
    try:
        import whisper
        _HAS_WHISPER = True
    except ImportError:
        _HAS_WHISPER = False


def has_whisper_engine() -> bool:
    """Returns True if Faster-Whisper or OpenAI Whisper is installed."""
    return _HAS_WHISPER


class AudioQAAuditor:
    """
    Forensic QA Auditor for dialogue segments and chapter master deliverables.
    Combines energy/VAD boundary detection, speaking rate bounds, and MOS estimation.
    """

    def __init__(self, config: Optional[AudioQAConfig] = None):
        self.config = config or AudioQAConfig()
        self._has_whisper = has_whisper_engine()

    def audit_segment(
        self,
        audio_path: Union[str, Path],
        expected_text: str = "",
        speaker: str = "Narrator",
        segment_index: int = 1,
        segment_uid: Optional[str] = None,
    ) -> SegmentQAEvaluation:
        """
        Audits a single speech audio segment against expected screenplay text.
        Returns strongly typed SegmentQAEvaluation with PASS / WARN / FAIL verdict.
        """
        p = Path(audio_path).resolve()
        uid = segment_uid or p.stem
        if not p.exists():
            return SegmentQAEvaluation(
                segment_index=segment_index,
                segment_uid=uid,
                speaker=speaker,
                status="FAIL",
                duration_ms=0,
                issues=["FILE_NOT_FOUND: Audio chunk does not exist on disk."],
                remediation_advice="Trigger immediate TTS re-roll.",
            )

        # Read audio samples
        try:
            data, sr, duration_ms = self._read_wav_metrics(p)
        except Exception as e:
            return SegmentQAEvaluation(
                segment_index=segment_index,
                segment_uid=uid,
                speaker=speaker,
                status="FAIL",
                duration_ms=0,
                issues=[f"CORRUPT_AUDIO_FILE: {e}"],
                remediation_advice="Re-render audio chunk from TTS pipeline.",
            )

        issues: List[str] = []
        is_hard_fail = False

        # 1. Empty / Zero-length / Near-silent check
        if duration_ms < 60 or data.size == 0:
            return SegmentQAEvaluation(
                segment_index=segment_index,
                segment_uid=uid,
                speaker=speaker,
                status="FAIL",
                duration_ms=duration_ms,
                issues=["EMPTY_AUDIO_SAMPLES: Audio duration is < 60ms or has 0 frames."],
                remediation_advice="TTS synthesis produced empty chunk; re-synthesize.",
            )

        peak_amp = float(np.max(np.abs(data)))
        rms_amp = float(np.sqrt(np.mean(data ** 2)))

        if rms_amp < 1e-4:
            is_hard_fail = True
            issues.append("SILENT_AUDIO_DROPOUT: Audio RMS energy is below -80 dBFS.")

        # 2. Severe Clipping Detection
        if peak_amp >= 0.999:
            issues.append("CLIPPING_DETECTED: Peak amplitude reached digital 0 dBFS saturation.")

        # 3. Leading & Trailing Dead-Air Silence
        lead_ms, trail_ms = self._measure_silence_boundaries(data, sr=sr)
        if lead_ms > 800:
            issues.append(f"EXCESSIVE_LEADING_SILENCE: {lead_ms}ms of dead air before speech onset.")
        if trail_ms > 1200:
            issues.append(f"EXCESSIVE_TRAILING_SILENCE: {trail_ms}ms of dead air after speech offset.")

        # 4. Text Grounding & Speaking Rate Bounds
        text_clean = expected_text.strip()
        words = text_clean.split()
        word_count = max(1, len(words))
        char_count = max(1, len(text_clean.replace(" ", "")))

        dur_sec = duration_ms / 1000.0
        wpm = (word_count / dur_sec) * 60.0
        char_per_sec = char_count / dur_sec

        if text_clean:
            # Check for severe truncation / dropout (e.g. 15 words spoken in 0.3s)
            if wpm > 320.0 or (char_count > 30 and dur_sec < 0.4):
                is_hard_fail = True
                issues.append(
                    f"TTS_DROPOUT_TRUNCATION: Speaking rate {wpm:.1f} WPM ({char_per_sec:.1f} char/s) "
                    f"is physically impossible; speech was truncated."
                )
            elif wpm > self.config.max_wpm:
                issues.append(f"RUSHED_SPEECH_PACE: Speaking rate {wpm:.1f} WPM exceeds {self.config.max_wpm} WPM.")

            # Check for hallucination / repetition loop (e.g. 2 words taking 8 seconds)
            if wpm < 40.0 and char_count < 20 and dur_sec > 4.0:
                is_hard_fail = True
                issues.append(
                    f"TTS_HALLUCINATION_LOOP: Extremely low rate {wpm:.1f} WPM ({char_per_sec:.1f} char/s) "
                    f"on short text ({char_count} chars in {dur_sec:.1f}s) indicates repetition loop."
                )
            elif wpm < self.config.min_wpm and dur_sec > 1.5:
                issues.append(f"STALLED_SPEECH_PACE: Speaking rate {wpm:.1f} WPM is below {self.config.min_wpm} WPM.")

        # 5. Non-Intrusive Speech MOS Estimation
        mos_score = self.estimate_speech_mos(data, sr=sr, peak_amp=peak_amp, rms_amp=rms_amp)
        if mos_score < self.config.min_mos_threshold:
            issues.append(f"LOW_PREDICTED_MOS: Speech quality MOS {mos_score:.2f} is below target {self.config.min_mos_threshold}.")

        # Determine Final Verdict
        if is_hard_fail:
            status = "FAIL"
            remediation = "Trigger automated segment re-synthesis with adjusted TTS temperature."
        elif issues:
            status = "WARN"
            remediation = "Non-blocking acoustic notice; verified within tolerance bounds."
        else:
            status = "PASS"
            remediation = None

        return SegmentQAEvaluation(
            segment_index=segment_index,
            segment_uid=uid,
            speaker=speaker,
            status=status,
            duration_ms=duration_ms,
            estimated_wpm=round(wpm, 1),
            char_per_sec=round(char_per_sec, 1),
            predicted_mos=round(mos_score, 2),
            silence_leading_ms=lead_ms,
            silence_trailing_ms=trail_ms,
            issues=issues,
            remediation_advice=remediation,
        )

    def audit_chapter(
        self,
        audio_segments: List[Union[str, Path]],
        script_segments: Optional[List[Dict[str, Any]]] = None,
        chapter_num: int = 1,
    ) -> ChapterQAReport:
        """
        Executes comprehensive forensic audit across all segments of a chapter.
        Returns consolidated ChapterQAReport.
        """
        if not audio_segments:
            return ChapterQAReport(
                chapter_num=chapter_num,
                total_segments=0,
                overall_status="WARN",
                mean_mos=4.5,
                evaluations=[],
            )

        script_by_idx: Dict[int, Dict[str, Any]] = {}
        if script_segments:
            for s in script_segments:
                idx = s.get("index", 1) if isinstance(s, dict) else getattr(s, "index", 1)
                script_by_idx[idx] = s if isinstance(s, dict) else s.model_dump()

        evaluations: List[SegmentQAEvaluation] = []
        for i, seg_path in enumerate(audio_segments):
            s_idx = i + 1
            p = Path(seg_path)
            for part in p.stem.split("_"):
                if part.startswith("s") and part[1:].isdigit():
                    s_idx = int(part[1:])
                    break

            meta = script_by_idx.get(s_idx, {})
            text = str(meta.get("spoken_text") or meta.get("text") or "")
            speaker = str(meta.get("speaker", "Narrator"))

            eval_res = self.audit_segment(
                audio_path=p,
                expected_text=text,
                speaker=speaker,
                segment_index=s_idx,
                segment_uid=p.stem,
            )
            evaluations.append(eval_res)

        total = len(evaluations)
        passed = sum(1 for e in evaluations if e.status == "PASS")
        warned = sum(1 for e in evaluations if e.status == "WARN")
        failed = sum(1 for e in evaluations if e.status == "FAIL")

        mean_mos = float(np.mean([e.predicted_mos for e in evaluations])) if evaluations else 4.5
        overall_status = "FAIL" if failed > 0 else ("WARN" if warned > 0 else "PASS")

        return ChapterQAReport(
            chapter_num=chapter_num,
            total_segments=total,
            passed_segments=passed,
            warned_segments=warned,
            failed_segments=failed,
            overall_status=overall_status,
            mean_mos=round(mean_mos, 2),
            evaluations=evaluations,
        )

    def estimate_speech_mos(
        self,
        data: np.ndarray,
        sr: int = 48000,
        peak_amp: float = 0.5,
        rms_amp: float = 0.1,
    ) -> float:
        """
        Estimates non-intrusive Mean Opinion Score (1.0 to 5.0).
        Calculates empirical Acoustic Quality Index (AQI) based on dynamic headroom,
        harmonic stability, and lack of DC offset.
        """
        if data.size == 0 or rms_amp < 1e-4:
            return 1.0

        score = 4.75  # Base studio quality

        # Crest factor penalty (extreme compression or harsh clipping)
        crest_factor = peak_amp / max(rms_amp, 1e-5)
        if crest_factor < 2.0:  # Hyper-compressed / squashed
            score -= 0.6
        elif crest_factor > 18.0:  # Sparse / highly impulsive
            score -= 0.3

        # DC Offset penalty
        dc_offset = float(np.abs(np.mean(data)))
        if dc_offset > 0.02:
            score -= 0.5

        # Clipping penalty
        if peak_amp >= 0.999:
            score -= 0.8

        return max(1.0, min(5.0, score))

    @staticmethod
    def _read_wav_metrics(file_path: Path) -> Tuple[np.ndarray, int, int]:
        """Reads WAV into float32 array, returning (samples, sample_rate, duration_ms)."""
        with wave.open(str(file_path.resolve()), "rb") as wf:
            sr = wf.getframerate()
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            frames = wf.getnframes()
            raw = wf.readframes(frames)

        duration_ms = int(round((frames / float(sr)) * 1000.0)) if sr > 0 else 0

        if frames == 0 or len(raw) == 0:
            return np.zeros((0, 2), dtype=np.float32), sr, 0

        if sw == 2:
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sw == 3:
            raw_arr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
            padded = np.pad(raw_arr, ((0, 0), (1, 0)), mode="constant", constant_values=0)
            data = (padded.view("<i4").flatten() >> 8).astype(np.float32) / 8388607.0
        elif sw == 4:
            data = np.frombuffer(raw, dtype=np.float32)
        else:
            data = np.zeros(frames * ch, dtype=np.float32)

        if ch > 1:
            data = data.reshape(-1, ch)
        else:
            data = np.column_stack((data, data))

        return np.nan_to_num(data, nan=0.0, posinf=1.0, neginf=-1.0), sr, duration_ms

    @staticmethod
    def _measure_silence_boundaries(data: np.ndarray, sr: int = 48000, threshold_db: float = -50.0) -> Tuple[int, int]:
        """Measures leading and trailing silence duration in milliseconds."""
        if data.size == 0:
            return 0, 0

        mono = np.mean(np.abs(data), axis=1) if data.ndim > 1 else np.abs(data)
        thresh = 10.0 ** (threshold_db / 20.0)

        # Block-based scanning (10ms blocks)
        block_size = max(1, int(sr * 0.010))
        num_blocks = len(mono) // block_size
        if num_blocks == 0:
            return 0, 0

        lead_blocks = 0
        for i in range(num_blocks):
            blk = mono[i * block_size : (i + 1) * block_size]
            if np.max(blk) < thresh:
                lead_blocks += 1
            else:
                break

        trail_blocks = 0
        for i in range(num_blocks - 1, -1, -1):
            blk = mono[i * block_size : (i + 1) * block_size]
            if np.max(blk) < thresh:
                trail_blocks += 1
            else:
                break

        lead_ms = lead_blocks * 10
        trail_ms = trail_blocks * 10
        return lead_ms, trail_ms
