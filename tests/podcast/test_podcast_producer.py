#!/usr/bin/env python3
"""
Unit and integration tests for the Podcast Audio Production Subsystem (Phase 3).
Tests Hann micro-fading, multi-turn dialogue concatenation, EBU R128 vocal mastering,
and end-to-end production on scientific whitepaper podcast scripts.
"""

import json
import wave
import tempfile
import numpy as np
import pytest
from pathlib import Path

from audiobook_factory.podcast.contracts import (
    PodcastScript,
    PodcastSegment,
    HostProfile,
    PodcastProductionResult,
)
from audiobook_factory.podcast.producer import (
    HannMicroFadeProcessor,
    PodcastAudioProducer,
    produce_podcast_audio,
)


@pytest.fixture
def temp_workspace(tmp_path: Path):
    """Provides an isolated workspace directory."""
    ws = tmp_path / "podcast_prod_workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def sample_script() -> PodcastScript:
    """Provides a realistic dual-host podcast script fixture."""
    return PodcastScript(
        podcast_id="test_ep01",
        title="Test Scientific Breakthroughs",
        source_document_id="test_doc_01",
        hosts=[
            HostProfile(id="host_a", name="Dr. Vance", role="lead_explainer", default_voice="Charon"),
            HostProfile(id="host_b", name="Maya", role="inquisitive_cohost", default_voice="Aoede"),
        ],
        segments=[
            PodcastSegment(
                segment_id="seg_01",
                speaker="host_a",
                character_name="Dr. Vance",
                text="Welcome to the deep dive. Today we are unpacking a major algorithmic breakthrough.",
                pause_after_ms=200,
            ),
            PodcastSegment(
                segment_id="seg_02",
                speaker="host_b",
                character_name="Maya",
                text="I saw the benchmark results, and the latency reduction is striking.",
                pause_after_ms=250,
            ),
            PodcastSegment(
                segment_id="seg_03",
                speaker="host_a",
                character_name="Dr. Vance",
                text="Exactly. Energy equals mass times the speed of light squared.",
                pause_after_ms=300,
            ),
        ],
    )


def test_01_hann_micro_fade_processor():
    """Verifies that Hann micro-fades attenuate boundary endpoints without corrupting center body."""
    sr = 48000
    duration_samples = sr  # 1 second
    constant_signal = np.ones(duration_samples, dtype=np.float32)

    faded = HannMicroFadeProcessor.apply_fades(
        constant_signal,
        sample_rate=sr,
        fade_in_ms=12,
        fade_out_ms=18,
    )

    # Fade in: index 0 should be 0.0, rising smoothly
    assert faded[0] == pytest.approx(0.0, abs=1e-4)
    n_in = int(sr * (12 / 1000.0))
    assert faded[n_in - 1] < 1.0
    assert faded[n_in] == pytest.approx(1.0, abs=1e-3)

    # Body: center samples should remain perfectly unattenuated (1.0)
    assert faded[duration_samples // 2] == pytest.approx(1.0, abs=1e-4)

    # Fade out: last index should approach 0.0
    n_out = int(sr * (18 / 1000.0))
    assert faded[-n_out] == pytest.approx(1.0, abs=1e-3)
    assert faded[-1] == pytest.approx(0.0, abs=1e-4)


def test_02_synthetic_chunk_generation(temp_workspace: Path):
    """Verifies generation of 48kHz PCM WAV audio chunks."""
    producer = PodcastAudioProducer(output_dir=temp_workspace)
    chunk_path = temp_workspace / "test_chunk.wav"

    out = producer.generate_synthetic_audio_chunk(
        output_path=chunk_path,
        duration_sec=1.5,
        sample_rate=48000,
        tone_freq=220.0,
    )

    assert out.exists()
    assert out.stat().st_size > 44

    with wave.open(str(out), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 48000
        frames = wf.getnframes()
        duration = frames / 48000.0
        assert duration == pytest.approx(1.5, abs=0.05)


def test_03_dialogue_concatenation_and_pauses(temp_workspace: Path, sample_script: PodcastScript):
    """Verifies that dialogue concatenation stitches segments with correct inter-turn pauses."""
    producer = PodcastAudioProducer(output_dir=temp_workspace)
    chunks_dir = temp_workspace / "chunks"

    chunk_files = producer.synthesize_script(
        script=sample_script,
        chunks_dir=chunks_dir,
        mock_mode=True,
    )

    assert len(chunk_files) == 3
    for f in chunk_files:
        assert f.exists()

    output_raw = temp_workspace / "dialogue_raw.wav"
    stitched_path = producer.concatenate_dialogue(
        segments=sample_script.segments,
        chunk_files=chunk_files,
        output_wav=output_raw,
    )

    assert stitched_path.exists()
    with wave.open(str(stitched_path), "rb") as wf:
        total_duration = wf.getnframes() / float(wf.getframerate())

    # Total duration should exceed sum of chunk durations due to pauses
    total_pause_sec = sum(s.pause_after_ms for s in sample_script.segments) / 1000.0
    assert total_duration > total_pause_sec


def test_04_mastering_pipeline_ebur128(temp_workspace: Path):
    """Verifies two-pass EBU R128 mastering renders broadcast-compliant audio with valid metadata."""
    producer = PodcastAudioProducer(output_dir=temp_workspace)

    # Create unmastered raw audio track
    raw_wav = temp_workspace / "test_raw_track.wav"
    producer.generate_synthetic_audio_chunk(
        output_path=raw_wav,
        duration_sec=3.0,
        sample_rate=48000,
        tone_freq=180.0,
    )

    mastered_wav = temp_workspace / "test_mastered_track.wav"
    mastered_out, metrics = producer.master_podcast_audio(
        input_wav=raw_wav,
        output_audio=mastered_wav,
        target_lufs=-19.0,
        true_peak=-1.5,
    )

    assert mastered_out.exists()
    assert mastered_out.stat().st_size > 44
    assert metrics["target_lufs"] == -19.0
    assert metrics["target_true_peak"] == -1.5
    assert metrics["mastering_standard"] == "EBU_R128_AUDIBLE_COMPLIANT"


def test_05_end_to_end_produce_podcast_audio(temp_workspace: Path, sample_script: PodcastScript):
    """Verifies autonomous end-to-end podcast production from script object to mastered audio."""
    result: PodcastProductionResult = produce_podcast_audio(
        script_or_path=sample_script,
        output_dir=temp_workspace,
        mock_mode=True,
    )

    assert result.status == "SUCCESS"
    assert result.podcast_id == "test_ep01"
    assert result.total_segments == 3
    assert result.dialogue_raw_path is not None
    assert Path(result.dialogue_raw_path).exists()
    assert result.mastered_audio_path is not None
    assert Path(result.mastered_audio_path).exists()
    assert result.integrated_lufs == -19.0
    assert result.true_peak_db == -1.5

    manifest_file = temp_workspace / "test_ep01_production_manifest.json"
    assert manifest_file.exists()
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["status"] == "SUCCESS"
    assert manifest["podcast_id"] == "test_ep01"


def test_06_produce_podcast_from_benchmark_research_paper(temp_workspace: Path):
    """Verifies end-to-end audio production on the benchmark scientific paper podcast script."""
    script_path = Path("audiobooks/projects/sample_research_paper/podcast_script.json")
    if not script_path.exists():
        pytest.skip("sample_research_paper/podcast_script.json not present in repo")

    result = produce_podcast_audio(
        script_or_path=script_path,
        output_dir=temp_workspace / "benchmark_run",
        mock_mode=True,
    )

    assert result.status == "SUCCESS"
    assert result.podcast_id == "pod_sample_research_paper"
    assert result.total_segments == 22
    assert Path(result.dialogue_raw_path).exists()
    assert Path(result.mastered_audio_path).exists()
    assert result.duration_sec > 0.0
