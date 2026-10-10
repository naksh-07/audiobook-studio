#!/usr/bin/env python3
"""
Deep unit tests for EditorialDSPEngine, HannFadeProcessor, NetSilenceProcessor,
and ZeroCrossingAligner.
"""

import struct
import math
import pytest

from audiobook_factory.tts.dsp.editorial import (
    EditorialDSPEngine,
    HannFadeProcessor,
    NetSilenceProcessor,
    ZeroCrossingAligner,
)


def test_zero_crossing_aligner():
    # Samples crossing zero around index 5: [-100, -80, -50, -20, -5, 10, 40, 80]
    samples = [-100, -80, -50, -20, -5, 10, 40, 80, 100]
    crossing_idx = ZeroCrossingAligner.find_nearest_zero_crossing(samples, start_idx=2, search_window=5)
    assert crossing_idx == 4
    assert samples[crossing_idx] <= 0 and samples[crossing_idx + 1] >= 0


def test_hann_fade_processor_mathematics():
    sample_rate = 24000
    # 1.0 second constant tone of amplitude 20000
    num_samples = sample_rate
    samples = [20000] * num_samples
    pcm = struct.pack(f"<{num_samples}h", *samples)

    faded_pcm = HannFadeProcessor.apply_hann_micro_fades(pcm, sample_rate=sample_rate, apply_tpdf_dither=False)
    faded_samples = struct.unpack(f"<{num_samples}h", faded_pcm)

    # First sample should be attenuated near zero
    assert abs(faded_samples[0]) <= 50

    # Middle sample should retain full amplitude (20000)
    mid_idx = num_samples // 2
    assert faded_samples[mid_idx] == pytest.approx(20000, abs=100)

    # Last sample should be attenuated near zero
    assert abs(faded_samples[-1]) <= 50


def test_net_silence_calculation_formula():
    """
    Verifies that Net Silence dynamically subtracts decay margins from target pauses.
    Target: 400ms, Tail Decay: 120ms, Head Margin: 80ms -> Net Injected: 200ms
    """
    target_pause = 400
    tail_decay = 120
    head_margin = 80

    net_pause = NetSilenceProcessor.calculate_net_silence_ms(
        target_pause_ms=target_pause,
        tail_decay_ms=tail_decay,
        head_margin_ms=head_margin,
        min_injected_ms=20,
    )

    assert net_pause == 200  # 400 - (120 + 80) = 200ms

    # If decay exceeds target pause, clamp to minimum 20ms
    heavy_tail = 350
    heavy_head = 100
    clamped_pause = NetSilenceProcessor.calculate_net_silence_ms(
        target_pause_ms=target_pause,
        tail_decay_ms=heavy_tail,
        head_margin_ms=heavy_head,
        min_injected_ms=20,
    )
    assert clamped_pause == 20


def test_editorial_dsp_engine_stitching():
    sample_rate = 24000
    # Chunk A: 0.5s tone + 0.1s silence tail (0.6s total)
    chunk_a = ([15000 if (i // 40) % 2 == 0 else -15000 for i in range(12000)] + [0] * 2400)
    pcm_a = struct.pack(f"<{len(chunk_a)}h", *chunk_a)

    # Chunk B: 0.1s silence head + 0.5s tone (0.6s total)
    chunk_b = ([0] * 2400 + [15000 if (i // 40) % 2 == 0 else -15000 for i in range(12000)])
    pcm_b = struct.pack(f"<{len(chunk_b)}h", *chunk_b)

    # Target pause: 300ms
    stitched_pcm, total_dur = EditorialDSPEngine.process_and_stitch(
        chunks_pcm=[pcm_a, pcm_b],
        target_pauses_ms=[300],
        sample_rate=sample_rate,
    )

    assert len(stitched_pcm) > 0
    assert total_dur > 1.2
