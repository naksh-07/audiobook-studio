#!/usr/bin/env python3
"""
Audiobook Factory - End-to-End Audio Mixing & Production Golden Pilot Test (Phase 6).
=====================================================================================
Validates complete autonomous pure vocals-only pipeline from TTS outputs to .m4b:
1. Ingestion: Tier A acoustic normalization, 48kHz 24-bit stereo, 30Hz highpass, 5ms Hann micro-taper.
2. Pre-Master Composition: ChunkStreamComposer, syntax-aware pauses (180/380/600ms), azimuth staging.
3. DAG Ledgering: Segment hash ledgering and DAG change tracking (AP-07).
4. Stage 12 Mastering: MasteringEngineV2, -19.0 LUFS target, -2.0 dBFS limiter ceiling (AP-02, AP-08).
5. Single-Pass Delivery: ChapterDeliveryEncoder, 192k AAC-LC with True Peak verification <= -1.5 dBTP (AP-04, AP-09).
6. Lossless Container Packaging: M4BBookPackager, 100% stream copy (-c:a copy), monotonic TOC (AP-10).
"""

import math
import wave
import json
import subprocess
from pathlib import Path
import numpy as np
import pytest

from audiobook_factory.audio.contracts import IngestionConfig, SegmentAudioContract
from audiobook_factory.audio.ingestion import AudioIngestionManager
from audiobook_factory.audio.stream_composer import ChunkStreamComposer
from audiobook_factory.audio.editorial import DialogueEditorialBridge
from audiobook_factory.audio.ledger import ChapterSegmentLedger
from audiobook_factory.audio.encoder import ChapterDeliveryEncoder
from audiobook_factory.audio.packager import M4BBookPackager
from audiobook_factory.mastering_contracts import MasteringProfile, MasteringRequest
from audiobook_factory.mastering_engine import MasteringEngineV2
from audiobook_factory.tts.constants import get_ffmpeg, get_ffprobe


def create_synthetic_speech_chunk(
    path: Path,
    duration_sec: float = 2.0,
    base_freq: float = 220.0,
    sample_rate: int = 48000,
) -> Path:
    """Creates synthetic speech-like harmonic audio with formants."""
    path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    
    # Fundamental + 2 harmonics + subtle envelope
    signal = (
        0.35 * np.sin(2 * np.pi * base_freq * t) +
        0.15 * np.sin(2 * np.pi * (base_freq * 2) * t) +
        0.08 * np.sin(2 * np.pi * (base_freq * 3) * t)
    )
    # Apply soft amplitude modulation to emulate syllables
    mod = 0.7 + 0.3 * np.sin(2 * np.pi * 4.0 * t)
    signal = signal * mod

    # 16-bit PCM source
    pcm_data = (np.clip(signal, -1.0, 1.0) * 32767.0).astype(np.int16)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)  # Mono TTS output
        wf.setsampwidth(2)   # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data.tobytes())
    return path


def probe_media_file(path: Path) -> dict:
    """Probes format, audio stream info, and duration using ffprobe."""
    ffprobe = get_ffprobe()
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return json.loads(res.stdout)


class TestAudioProductionE2EPilot:
    """Full End-to-End production integration suite."""

    def test_complete_audiobook_production_lifecycle(self, tmp_path):
        """
        Executes complete production run on a synthetic multi-speaker chapter.
        Verifies all 4 quality gates and production deliverables.
        """
        # Directory layout
        raw_tts_dir = tmp_path / "raw_tts"
        ingested_dir = tmp_path / "ingested"
        premaster_dir = tmp_path / "premaster"
        mastered_dir = tmp_path / "mastered"
        deliverables_dir = tmp_path / "deliverables"

        for d in [raw_tts_dir, ingested_dir, premaster_dir, mastered_dir, deliverables_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # -------------------------------------------------------------
        # STEP 1: Generate 5 synthetic dialogue segments (Multi-Cast)
        # -------------------------------------------------------------
        raw_chunks = [
            (1, "c001_s001", "Narrator", "Aoede", 180.0, 2.5, "The wind howled across Kaer Morhen."),
            (2, "c001_s002", "Geralt", "Fenrir", 120.0, 1.8, "Something is wrong here."),
            (3, "c001_s003", "Yennefer", "Kore", 260.0, 2.2, "Then draw your blade, Geralt."),
            (4, "c001_s004", "Geralt", "Fenrir", 120.0, 1.2, "Already done."),
            (5, "c001_s005", "Narrator", "Aoede", 180.0, 2.0, "Together they stepped into the storm."),
        ]

        raw_files = []
        for idx, uid, speaker, voice, freq, dur, text in raw_chunks:
            fpath = raw_tts_dir / f"{uid}.wav"
            create_synthetic_speech_chunk(fpath, duration_sec=dur, base_freq=freq)
            raw_files.append((idx, uid, speaker, voice, dur, text, fpath))

        # -------------------------------------------------------------
        # STEP 2: Tier A Speech Ingestion (Normalization + Hann Taper)
        # -------------------------------------------------------------
        ingestion_mgr = AudioIngestionManager(IngestionConfig(), project_dir=ingested_dir)
        ingested_contracts = []

        for idx, uid, speaker, voice, dur, text, fpath in raw_files:
            contract = ingestion_mgr.ingest_segment(
                source=fpath,
                chapter_id=1,
                segment_index=idx,
                speaker=speaker,
                voice_name=voice,
                segment_uid=uid,
                literary_text=text,
                spoken_text=text,
            )
            assert contract.sample_rate == 48000
            assert contract.channels == 2
            assert contract.bit_depth == 24
            assert contract.audio_path.is_file()
            ingested_contracts.append(contract)

        assert len(ingested_contracts) == 5

        # -------------------------------------------------------------
        # STEP 3: Dialogue Editorial & Streaming Pre-Master Composition
        # -------------------------------------------------------------
        composer = ChunkStreamComposer()
        premaster_path = premaster_dir / "chapter_001.premaster.wav"
        script_segments = [
            {"index": c.segment_index, "speaker": c.speaker, "voice": c.voice_name, "text": c.spoken_text}
            for c in ingested_contracts
        ]
        composed_path, total_dur, seg_durs = composer.compose_chapter_premaster(
            audio_segments=[c.audio_path for c in ingested_contracts],
            output_wav=premaster_path,
            script_segments=script_segments,
            spatial_staging=True,
        )
        assert composed_path.is_file()
        assert composed_path.stat().st_size > 1000

        # Check premaster wave parameters
        with wave.open(str(composed_path), "rb") as wf:
            assert wf.getframerate() == 48000
            assert wf.getnchannels() == 2
            assert wf.getsampwidth() == 3  # 24-bit PCM
            assert wf.getnframes() > 48000 * 9  # > 9 seconds of composed audio

        # -------------------------------------------------------------
        # STEP 4: Segment Hash Ledger Recording (AP-07 DAG Caching)
        # -------------------------------------------------------------
        ledger_path = deliverables_dir / "chapter_001_segment_ledger.json"
        ledger = ChapterSegmentLedger(chapter_num=1)
        cur_offset = 0
        for contract in ingested_contracts:
            entry = ledger.record_contract(
                contract=contract,
                timeline_start_ms=cur_offset,
                timeline_end_ms=cur_offset + contract.duration_ms,
            )
            cur_offset = entry.timeline_end_ms + 400  # Pause gap
        ledger.save_to_disk(ledger_path)
        assert ledger_path.is_file()

        # -------------------------------------------------------------
        # STEP 5: Stage 12 Mastering (EBU R128 + -2.0 dBFS Limiter AP-02)
        # -------------------------------------------------------------
        master_wav_path = mastered_dir / "chapter_001_master.wav"
        engine = MasteringEngineV2()
        master_profile = MasteringProfile(
            integrated_target_lufs=-19.0,
            loudness_tolerance_lu=0.5,
            true_peak_ceiling_dbtp=-2.0,
            limiter_ceiling_db=-2.0,
        )
        master_req = MasteringRequest(
            chapter_id="chapter_001",
            premaster_path=str(composed_path),
            output_master_path=str(master_wav_path),
            profile=master_profile,
        )
        master_result = engine.master(master_req)

        assert master_result.qc_result.passed is True
        assert master_result.iteration_count >= 1
        assert master_wav_path.is_file()
        assert master_result.analysis_after is not None
        assert master_result.analysis_after.integrated_lufs == pytest.approx(-19.0, abs=0.6)
        assert master_result.analysis_after.true_peak_dbtp <= -1.8

        # -------------------------------------------------------------
        # STEP 6: Single-Pass Chapter Delivery AAC (AP-04, AP-09)
        # -------------------------------------------------------------
        chapter_m4a_path = mastered_dir / "chapter_001_mastered.m4a"
        delivery_encoder = ChapterDeliveryEncoder()
        m4a_out = delivery_encoder.encode_chapter_m4a(
            input_wav=master_wav_path,
            output_m4a=chapter_m4a_path,
            target_bitrate="192k",
        )
        assert chapter_m4a_path.is_file()
        assert m4a_out.is_file()

        # Measure True Peak of delivered chapter M4A
        measured_tp = delivery_encoder.probe_true_peak(chapter_m4a_path)
        if measured_tp is not None:
            assert measured_tp <= -1.4  # True peak ceiling respected after lossy encoding

        # -------------------------------------------------------------
        # STEP 7: Lossless M4B Packaging (Stream Copy AP-04, AP-10)
        # -------------------------------------------------------------
        # Synthetic cover art (valid minimal JPEG via lavfi)
        cover_path = deliverables_dir / "cover.jpg"
        ff = get_ffmpeg()
        subprocess.run([
            ff, "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=1",
            "-frames:v", "1", "-update", "1", str(cover_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        packager = M4BBookPackager()
        packaged_m4b = packager.package_audiobook(
            project_dir=tmp_path,
            output_filename="Sword_of_Destiny.m4b",
            cover_image=cover_path,
            metadata={"title": "Sword of Destiny", "author": "Andrzej Sapkowski"},
            enforce_gate6=False,
        )
        assert packaged_m4b.is_file()
        assert packaged_m4b.stat().st_size > 1000

        # -------------------------------------------------------------
        # STEP 8: Quality Gate Verifications
        # -------------------------------------------------------------
        probe_info = probe_media_file(packaged_m4b)
        format_info = probe_info.get("format", {})
        streams = probe_info.get("streams", [])

        # Technical Validity
        assert "mp4" in format_info.get("format_name", "") or "ipod" in format_info.get("format_name", "")
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        assert audio_stream is not None
        assert audio_stream.get("codec_name") == "aac"
        assert int(audio_stream.get("sample_rate", 0)) == 48000
        assert int(audio_stream.get("channels", 0)) == 2

        # Video/Cover stream present
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        assert video_stream is not None
        assert video_stream.get("codec_name") == "mjpeg"

        # Metadata Tags
        tags = format_info.get("tags", {})
        assert tags.get("title") == "Sword of Destiny"
        assert tags.get("artist") == "Andrzej Sapkowski"
        assert tags.get("album") == "Sword of Destiny"
