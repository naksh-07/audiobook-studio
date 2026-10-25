#!/usr/bin/env python3
"""
Audiobook Factory - Dialogue Editorial Layer & Net-Silence DSP Engine.
Implements:
1. Zero-Crossing Endpoint Alignment (-52 dBFS speech floor).
2. Raised-Cosine Hann Micro-Fades (12ms in / 18ms out).
3. Net Silence Timeline Concatenation (dynamically subtracting decay margins).
4. TPDF Dithered 16-bit PCM Quantization.
"""

from __future__ import annotations
import math
import struct
import random
from typing import List, Tuple, Optional, Dict, Any


class ZeroCrossingAligner:
    """
    Finds exact zero-crossing samples (f(t) == 0, f'(t) >= 0) at speech endpoints
    to completely eliminate digital switching clicks.
    """

    @classmethod
    def find_nearest_zero_crossing(
        cls,
        samples: List[int],
        start_idx: int,
        search_window: int = 240,  # 10ms at 24kHz
        forward: bool = True,
    ) -> int:
        """Searches for the nearest zero crossing where sample transitions from negative to positive."""
        n = len(samples)
        if start_idx < 0 or start_idx >= n:
            return max(0, min(start_idx, n - 1))

        best_idx = start_idx
        min_diff = abs(samples[start_idx])

        step = 1 if forward else -1
        limit = min(n - 1, start_idx + search_window) if forward else max(0, start_idx - search_window)

        curr = start_idx
        while (curr < limit if forward else curr > limit):
            # Check sign change
            if curr + 1 < n and samples[curr] <= 0 and samples[curr + 1] >= 0:
                return curr

            if abs(samples[curr]) < min_diff:
                min_diff = abs(samples[curr])
                best_idx = curr

            curr += step

        return best_idx


class HannFadeProcessor:
    """
    Applies raised-cosine Hann window micro-fades to audio chunk boundaries:
    - 12ms Fade-In:  w_in(t)  = 0.5 * (1 - cos(pi * t / T_in))
    - 18ms Fade-Out: w_out(t) = 0.5 * (1 + cos(pi * t / T_out))
    """

    FADE_IN_MS: float = 12.0
    FADE_OUT_MS: float = 18.0

    @classmethod
    def apply_hann_micro_fades(
        cls,
        pcm_bytes: bytes,
        sample_rate: int = 24000,
        apply_tpdf_dither: bool = True,
    ) -> bytes:
        """Applies Hann micro-fades and TPDF dither to 16-bit mono PCM bytes."""
        sample_count = len(pcm_bytes) // 2
        if sample_count < 50:
            return pcm_bytes

        samples = list(struct.unpack(f"<{sample_count}h", pcm_bytes))

        fade_in_samples = int(sample_rate * (cls.FADE_IN_MS / 1000.0))
        fade_out_samples = int(sample_rate * (cls.FADE_OUT_MS / 1000.0))

        fade_in_len = min(fade_in_samples, sample_count // 2)
        fade_out_len = min(fade_out_samples, sample_count // 2)

        # 1. Apply Hann Fade-In
        for i in range(fade_in_len):
            gain = 0.5 * (1.0 - math.cos(math.pi * i / float(fade_in_len)))
            val = float(samples[i]) * gain
            if apply_tpdf_dither:
                # Triangular PDF dither: (R1 + R2 - 1.0) * 0.5 LSB
                dither = (random.random() + random.random() - 1.0) * 0.5
                val += dither
            samples[i] = int(max(-32768, min(32767, round(val))))

        # 2. Apply Hann Fade-Out
        for i in range(fade_out_len):
            idx = sample_count - fade_out_len + i
            gain = 0.5 * (1.0 + math.cos(math.pi * i / float(fade_out_len)))
            val = float(samples[idx]) * gain
            if apply_tpdf_dither:
                dither = (random.random() + random.random() - 1.0) * 0.5
                val += dither
            samples[idx] = int(max(-32768, min(32767, round(val))))

        return struct.pack(f"<{sample_count}h", *samples)


class NetSilenceProcessor:
    """
    Calculates net injected silence at chunk boundaries to permanently eliminate
    double-pause stutter gaps and preserve organic pacing.
    Formula:
        Injected = max(min_injected, Target_Pause - (Tail_Decay_A + Head_Margin_B))
    """

    SILENCE_FLOOR_AMPLITUDE: int = 350  # ~ -39.4 dBFS (covers Gemini vocoder dither / room-tone floor)

    @classmethod
    def measure_tail_decay_ms(cls, pcm_bytes: bytes, sample_rate: int = 24000) -> int:
        sample_count = len(pcm_bytes) // 2
        if sample_count == 0 or sample_rate <= 0:
            return 0

        samples = struct.unpack(f"<{sample_count}h", pcm_bytes)
        decay_samples = 0

        for s in reversed(samples):
            if abs(s) <= cls.SILENCE_FLOOR_AMPLITUDE:
                decay_samples += 1
            else:
                break

        return int((decay_samples / float(sample_rate)) * 1000.0)

    @classmethod
    def measure_head_margin_ms(cls, pcm_bytes: bytes, sample_rate: int = 24000) -> int:
        """Measures pre-speech silence margin in milliseconds."""
        sample_count = len(pcm_bytes) // 2
        if sample_count == 0 or sample_rate <= 0:
            return 0

        samples = struct.unpack(f"<{sample_count}h", pcm_bytes)
        head_samples = 0

        for s in samples:
            if abs(s) <= cls.SILENCE_FLOOR_AMPLITUDE:
                head_samples += 1
            else:
                break

        return int((head_samples / float(sample_rate)) * 1000.0)

    @classmethod
    def trim_excess_tail_pcm(
        cls,
        pcm_bytes: bytes,
        trim_ms: int,
        sample_rate: int = 24000,
    ) -> bytes:
        """Trims excessive trailing vocoder silence from PCM bytes."""
        if trim_ms <= 0 or sample_rate <= 0:
            return pcm_bytes
        sample_count = len(pcm_bytes) // 2
        trim_samples = int(sample_rate * (trim_ms / 1000.0))
        if trim_samples >= sample_count - 100:
            return pcm_bytes
        new_sample_count = sample_count - trim_samples
        return pcm_bytes[: new_sample_count * 2]

    @classmethod
    def calculate_net_silence_ms(
        cls,
        target_pause_ms: int,
        tail_decay_ms: int,
        head_margin_ms: int,
        min_injected_ms: int = 20,
    ) -> int:
        """
        Dynamically calculates exact net silence to inject:
        Injected = max(min_injected_ms, target_pause_ms - (tail_decay_ms + head_margin_ms))
        """
        net_ms = target_pause_ms - (tail_decay_ms + head_margin_ms)
        return max(min_injected_ms, net_ms)

    @classmethod
    def generate_silence_pcm(
        cls,
        duration_ms: int,
        sample_rate: int = 24000,
        comfort_noise: bool = True,
    ) -> bytes:
        """
        Generates 16-bit mono silence PCM bytes.
        When comfort_noise=True, injects an ultra-low (-62 dBFS) shaped acoustic room-tone floor
        to eliminate harsh digital zero dropouts and DAC click/pumping artifacts.
        """
        if sample_rate <= 0 or duration_ms <= 0:
            return b""
        num_samples = int(sample_rate * (duration_ms / 1000.0))
        if not comfort_noise:
            return b"\x00\x00" * num_samples

        # -62 dBFS shaped comfort noise (peak amplitude ~26 in 16-bit PCM)
        # Gentle pseudo-random dither with 1st-order low-pass smoothing (room tone)
        samples = []
        prev = 0.0
        for _ in range(num_samples):
            white = (random.random() - random.random()) * 24.0
            val = 0.7 * prev + 0.3 * white
            prev = val
            samples.append(int(max(-40, min(40, round(val)))))

        return struct.pack(f"<{num_samples}h", *samples)


class EditorialDSPEngine:
    """
    Unified Editorial DSP Engine combining Zero-Crossing, Hann Micro-Fades,
    and Net Silence timeline concatenation.
    """

    @classmethod
    def process_and_stitch(
        cls,
        chunks_pcm: List[bytes],
        target_pauses_ms: List[int],
        sample_rate: int = 24000,
    ) -> Tuple[bytes, float]:
        """
        Stitches a sequence of PCM audio chunks with Hann micro-fades and net silence.

        Returns:
            (stitched_pcm_bytes, total_duration_sec)
        """
        if not chunks_pcm:
            return b"", 0.0

        effective_sample_rate = max(1, sample_rate)
        output_buffers: List[bytes] = []
        total_samples = 0

        for idx in range(len(chunks_pcm)):
            raw_pcm = chunks_pcm[idx]

            # 1. If not the last chunk, check boundary silence and trim excessive trailing dead air
            if idx < len(chunks_pcm) - 1:
                target_pause = target_pauses_ms[idx] if idx < len(target_pauses_ms) else 350
                tail_decay = NetSilenceProcessor.measure_tail_decay_ms(raw_pcm, sample_rate=effective_sample_rate)
                next_raw = chunks_pcm[idx + 1]
                head_margin = NetSilenceProcessor.measure_head_margin_ms(next_raw, sample_rate=effective_sample_rate)

                inherent_silence_ms = tail_decay + head_margin
                if inherent_silence_ms > target_pause:
                    # Excess silence already present from vocoder/punctuation: trim trailing dead air
                    # Preserve at least 40ms of tail decay for smooth Hann fade-out
                    excess_ms = inherent_silence_ms - target_pause
                    trim_ms = min(excess_ms, max(0, tail_decay - 40))
                    if trim_ms > 0:
                        raw_pcm = NetSilenceProcessor.trim_excess_tail_pcm(raw_pcm, trim_ms, sample_rate=effective_sample_rate)
                        tail_decay = max(40, tail_decay - trim_ms)

                net_pause_ms = NetSilenceProcessor.calculate_net_silence_ms(
                    target_pause_ms=target_pause,
                    tail_decay_ms=tail_decay,
                    head_margin_ms=head_margin,
                    min_injected_ms=0,
                )
            else:
                net_pause_ms = 0

            # 2. Snap boundary endpoints to nearest zero-crossing if buffer is sufficiently long
            chunk_sample_count = len(raw_pcm) // 2
            if chunk_sample_count > 100:
                s_list = list(struct.unpack(f"<{chunk_sample_count}h", raw_pcm))
                start_z = ZeroCrossingAligner.find_nearest_zero_crossing(
                    s_list, 0, search_window=min(240, chunk_sample_count // 4), forward=True
                )
                end_z = ZeroCrossingAligner.find_nearest_zero_crossing(
                    s_list, chunk_sample_count - 1, search_window=min(240, chunk_sample_count // 4), forward=False
                )
                if 0 <= start_z < end_z < chunk_sample_count:
                    raw_pcm = struct.pack(f"<{end_z - start_z + 1}h", *s_list[start_z : end_z + 1])

            # 3. Apply Hann micro-fades
            faded_pcm = HannFadeProcessor.apply_hann_micro_fades(
                raw_pcm, sample_rate=effective_sample_rate, apply_tpdf_dither=True
            )
            output_buffers.append(faded_pcm)
            total_samples += len(faded_pcm) // 2

            # 4. If not the last chunk and net pause is needed, append net silence
            if idx < len(chunks_pcm) - 1 and net_pause_ms > 0:
                silence_pcm = NetSilenceProcessor.generate_silence_pcm(net_pause_ms, sample_rate=effective_sample_rate)
                output_buffers.append(silence_pcm)
                total_samples += len(silence_pcm) // 2

        full_pcm = b"".join(output_buffers)
        total_dur = total_samples / float(effective_sample_rate)
        return full_pcm, total_dur
