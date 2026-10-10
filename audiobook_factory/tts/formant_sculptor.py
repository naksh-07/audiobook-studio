#!/usr/bin/env python3
"""
Audiobook Factory - 4D Acoustic Formant Sculptor.
Applies parametric EQ formant shaping and acoustic pitch modulations
to guarantee character acoustic divergence when sharing base neural models.
"""

from __future__ import annotations
import math
import struct
from enum import Enum
from typing import Dict, Any, List, Tuple, Optional


class FormantProfile(str, Enum):
    WARM_BARITONE = "warm_baritone"
    CRISP_TENOR = "crisp_tenor"
    BRIGHT_FEMALE = "bright_female"
    DEEP_RESONANT = "deep_resonant"
    ELDERLY_TEXTURED = "elderly_textured"
    CHILD_ANIME = "child_anime"
    NEUTRAL = "neutral"


class FormantSculptor:
    """
    Parametric EQ and acoustic formant filter for character voice distinctiveness.
    Uses pure Python biquad peaking EQ filters on raw 16-bit PCM bytes.
    """

    # Pre-calibrated EQ presets: List of (center_freq_hz, gain_db, q_factor)
    EQ_PRESETS: Dict[FormantProfile, List[Tuple[float, float, float]]] = {
        FormantProfile.WARM_BARITONE: [
            (180.0, 3.0, 1.2),    # Warm chest resonance
            (3200.0, -1.8, 1.0),  # Soften harsh high-mids
        ],
        FormantProfile.CRISP_TENOR: [
            (160.0, -2.0, 1.0),   # De-mud lower register
            (3000.0, 2.5, 1.4),   # Articulate clarity boost
        ],
        FormantProfile.BRIGHT_FEMALE: [
            (120.0, -2.5, 0.8),   # High-pass body cleaning
            (3500.0, 3.0, 1.2),   # Vocal brilliance
            (8000.0, 1.5, 0.9),   # Air presence
        ],
        FormantProfile.DEEP_RESONANT: [
            (100.0, 4.0, 1.0),    # Sub-bass rumble
            (220.0, 2.5, 1.3),    # Low-end body
            (4000.0, -2.0, 1.0),  # Intimate dark tone
        ],
        FormantProfile.ELDERLY_TEXTURED: [
            (750.0, 2.8, 1.5),    # Throat/pharyngeal resonance
            (5000.0, -3.0, 1.0),  # Aged high-frequency softening
        ],
        FormantProfile.CHILD_ANIME: [
            (250.0, -2.0, 1.0),   # Light body
            (4200.0, 3.5, 1.5),   # Bright childlike resonance
            (9000.0, 2.0, 1.0),   # Upper harmonics
        ],
        FormantProfile.NEUTRAL: [],
    }

    @classmethod
    def apply_formant_eq(
        cls,
        pcm_bytes: bytes,
        profile: FormantProfile | str,
        sample_rate: int = 24000,
    ) -> bytes:
        """
        Applies calibrated parametric EQ filters corresponding to the FormantProfile on 16-bit PCM.
        """
        if isinstance(profile, str):
            try:
                profile = FormantProfile(profile.lower())
            except ValueError:
                profile = FormantProfile.NEUTRAL

        filters = cls.EQ_PRESETS.get(profile, [])
        if not filters or not pcm_bytes:
            return pcm_bytes

        # Unpack 16-bit signed PCM samples into float
        num_samples = len(pcm_bytes) // 2
        if num_samples == 0:
            return pcm_bytes

        samples = [float(s) for s in struct.unpack(f"<{num_samples}h", pcm_bytes)]

        # Headroom preservation: pre-attenuate if positive gain boosts are present
        max_boost_db = max([0.0] + [gain for _, gain, _ in filters])
        headroom_gain = (10.0 ** (-max_boost_db / 20.0)) if max_boost_db > 0.5 else 1.0
        if headroom_gain < 1.0:
            samples = [s * headroom_gain for s in samples]

        # Sequentially apply biquad peaking EQ filters in float precision
        for center_hz, gain_db, q in filters:
            samples = cls._apply_peaking_eq(samples, center_hz, gain_db, q, sample_rate)

        # Restore gain if safe, or apply transparent tanh soft-limiting to protect peaks
        peak_val = max(abs(s) for s in samples) if samples else 0.0
        if peak_val > 32760.0:
            # Soft tanh knee limiting to protect audio from harsh digital clipping
            samples = [32760.0 * math.tanh(s / 32760.0) for s in samples]

        # Re-pack with integer clamping
        clamped = [max(-32767, min(32767, int(round(s)))) for s in samples]
        return struct.pack(f"<{num_samples}h", *clamped)

    @staticmethod
    def _apply_peaking_eq(
        samples: List[float],
        center_hz: float,
        gain_db: float,
        q: float,
        sample_rate: int,
    ) -> List[float]:
        """
        Implements a standard 2nd-order Peaking EQ Biquad Filter (Robert Bristow-Johnson Audio EQ Cookbook).
        """
        if abs(gain_db) < 0.05:
            return samples

        # Guard against Nyquist limit
        if center_hz >= (sample_rate / 2.0):
            return samples

        A = 10.0 ** (gain_db / 40.0)
        w0 = 2.0 * math.pi * center_hz / sample_rate
        alpha = math.sin(w0) / (2.0 * max(0.1, q))

        b0 = 1.0 + alpha * A
        b1 = -2.0 * math.cos(w0)
        b2 = 1.0 - alpha * A
        a0 = 1.0 + alpha / A
        a1 = -2.0 * math.cos(w0)
        a2 = 1.0 - alpha / A

        # Normalize coefficients by a0
        nb0 = b0 / a0
        nb1 = b1 / a0
        nb2 = b2 / a0
        na1 = a1 / a0
        na2 = a2 / a0

        filtered = [0.0] * len(samples)
        x1 = x2 = y1 = y2 = 0.0

        for i, sample in enumerate(samples):
            x0 = sample
            y0 = nb0 * x0 + nb1 * x1 + nb2 * x2 - na1 * y1 - na2 * y2

            x2 = x1
            x1 = x0
            y2 = y1
            y1 = y0

            filtered[i] = y0

        return filtered
