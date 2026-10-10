#!/usr/bin/env python3
"""
Audiobook Factory - Tier A Audio Ingestion & Normalization Engine (v5.3).
Normalizes all raw TTS speech segments to uniform broadcast standard
(48,000 Hz 24-bit Stereo PCM WAV), strips container watermark static,
and applies the Single 5.0ms Raised-Cosine Hann Micro-Taper invariant.
"""

from __future__ import annotations
import io
import math
import wave
import hashlib
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Union, Dict, Any
import scipy.signal as sig

from audiobook_factory.logger import logger
from audiobook_factory.restoration import extract_clean_pcm_from_gemini_container
from audiobook_factory.audio.contracts import SegmentAudioContract, IngestionConfig


class AudioIngestionManager:
    """
    Tier A Ingestion Engine.
    Transforms raw, unvalidated speech audio from TTS providers into
    pristine, standardized 48kHz stereo 24-bit PCM WAV chunks.
    """

    def __init__(self, config: Optional[IngestionConfig] = None, project_dir: Optional[Union[Path, str]] = None):
        self.config = config or IngestionConfig()
        self.project_dir = Path(project_dir).resolve() if project_dir else Path(".")
        self.output_dir = self.project_dir / "ingested_chunks"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def demux_and_clean_pcm(raw_bytes: bytes) -> Tuple[np.ndarray, int]:
        """
        Strips RIFF container wrappers and C2PA digital watermark static screeches.
        Returns: (float32_pcm_samples_in_range_minus1_to_plus1, sample_rate)
        """
        if not raw_bytes:
            return np.zeros((0,), dtype=np.float32), 48000

        # Safely parse as valid WAV first to avoid static screech from headers
        if raw_bytes.startswith(b"RIFF"):
            try:
                with wave.open(io.BytesIO(raw_bytes), "rb") as wf:
                    sr = wf.getframerate()
                    ch = wf.getnchannels()
                    sw = wf.getsampwidth()
                    frames = wf.getnframes()
                    raw = wf.readframes(frames)
                    if sw == 2:
                        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                    elif sw == 3:
                        raw_arr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
                        padded = np.pad(raw_arr, ((0, 0), (1, 0)), mode="constant", constant_values=0)
                        samples = (padded.view("<i4").flatten() >> 8).astype(np.float32) / 8388607.0
                    else:
                        samples = np.frombuffer(raw, dtype=np.float32)
                    
                    if ch > 1:
                        # Convert to Mono by averaging channels for standardized processing
                        samples = samples.reshape(-1, ch).mean(axis=1)
                        
                    return samples, sr
            except Exception as e:
                logger.debug(f"WAV parse failed, falling back to PCM extraction: {e}")

        # Layer 1: Extraction of pure PCM frames from Gemini container
        clean_pcm_bytes, src_rate, num_frames = extract_clean_pcm_from_gemini_container(raw_bytes)

        if not clean_pcm_bytes or num_frames == 0:
            # Fallback if raw_bytes was already a pure raw wave or byte stream
            clean_pcm_bytes = raw_bytes
            src_rate = 24000
            num_frames = len(clean_pcm_bytes) // 2

        # Convert 16-bit integer PCM to float32 normalized in [-1.0, 1.0]
        # In case the clean bytes have an odd length, truncate last dangling byte
        usable_bytes = len(clean_pcm_bytes) - (len(clean_pcm_bytes) % 2)
        int16_samples = np.frombuffer(clean_pcm_bytes[:usable_bytes], dtype=np.int16)
        samples = int16_samples.astype(np.float32) / 32768.0

        return samples, src_rate

    @staticmethod
    def apply_single_hann_micro_taper(
        samples: np.ndarray,
        sample_rate: int = 48000,
        taper_ms: float = 5.0,
    ) -> np.ndarray:
        """
        Applies the Single Raised-Cosine (Hann) Micro-Taper (AP-06).
        Guarantees:
        - Exactly one 5.0ms taper window at speech onset and offset.
        - Initial sample strictly 0.0 (Zero Dirac step click).
        - Final sample strictly 0.0 (Zero trailing DC step pop).
        - 100% preservation of initial plosive consonants (p, t, k) and trailing breath tails.
        """
        n_samples = len(samples)
        taper_len = max(2, int(sample_rate * (taper_ms / 1000.0)))
        if n_samples < taper_len * 2:
            # Very short segment: apply proportionate half-windows
            taper_len = max(2, n_samples // 4)

        if taper_len < 2 or n_samples < 4:
            return samples

        fade_in = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, taper_len)))
        fade_out = 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, taper_len)))

        if samples.ndim == 2:
            samples[:taper_len, :] *= fade_in[:, np.newaxis]
            samples[-taper_len:, :] *= fade_out[:, np.newaxis]
            samples[0, :] = 0.0
            samples[-1, :] = 0.0
        else:
            samples[:taper_len] *= fade_in
            samples[-taper_len:] *= fade_out
            samples[0] = 0.0
            samples[-1] = 0.0

        return samples

    def standardize_format(
        self,
        samples: np.ndarray,
        src_rate: int,
    ) -> np.ndarray:
        """
        Standardizes audio to target sample rate, stereo channels, and subsonic DC cut.
        """
        if len(samples) == 0:
            return np.zeros((0, self.config.target_channels), dtype=np.float32)

        # 1. Subsonic Highpass (Butterworth 2nd-order, 30 Hz)
        if self.config.highpass_hz > 0 and len(samples) > 64:
            try:
                sos = sig.butter(2, self.config.highpass_hz, btype="highpass", fs=max(1, src_rate), output="sos")
                samples = sig.sosfilt(sos, samples, axis=0).astype(np.float32)
            except Exception as e:
                logger.debug(f"Highpass filter fallback notice: {e}")

        # 2. Resampling via Kaiser windowed sinc polyphase filter
        target_rate = self.config.target_sample_rate
        if src_rate > 0 and src_rate != target_rate:
            common_divisor = math.gcd(target_rate, src_rate)
            up = target_rate // common_divisor
            down = src_rate // common_divisor
            if down > 0:
                samples = sig.resample_poly(samples, up, down, axis=0).astype(np.float32)

        # 3. Channel Layout Normalization (Mono to Stereo)
        if samples.ndim == 1 and self.config.target_channels == 2:
            samples = np.column_stack((samples, samples))
        elif samples.ndim == 2 and samples.shape[1] == 1 and self.config.target_channels == 2:
            samples = np.column_stack((samples[:, 0], samples[:, 0]))
        elif samples.ndim == 2 and samples.shape[1] > self.config.target_channels:
            samples = samples[:, :self.config.target_channels]

        # 4. Single Raised-Cosine Micro-Taper Application
        samples = self.apply_single_hann_micro_taper(
            samples,
            sample_rate=target_rate,
            taper_ms=self.config.micro_taper_ms,
        )

        return samples

    def write_pcm_wav(self, file_path: Path, samples: np.ndarray) -> Path:
        """
        Writes float32 samples to uncompressed 24-bit or 16-bit PCM WAV.
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        ch = samples.shape[1] if samples.ndim == 2 else 1
        sr = self.config.target_sample_rate
        bit_depth = self.config.target_bit_depth

        clean_samples = np.nan_to_num(samples, nan=0.0, posinf=1.0, neginf=-1.0)
        clean_samples = np.clip(clean_samples, -1.0, 1.0)

        if bit_depth == 24:
            # Scale to 24-bit signed integer [-8388608, 8388607]
            int32_arr = np.clip(np.round(clean_samples * 8388607.0), -8388608, 8388607).astype("<i4")
            raw_pcm = int32_arr.view(np.uint8).reshape(-1, 4)[:, :3].flatten().tobytes()
            samp_width = 3
        else:
            # 16-bit signed integer [-32768, 32767]
            int16_arr = np.clip(np.round(clean_samples * 32767.0), -32768, 32767).astype("<i2")
            raw_pcm = int16_arr.tobytes()
            samp_width = 2

        with wave.open(str(file_path), "wb") as wf:
            wf.setnchannels(ch)
            wf.setsampwidth(samp_width)
            wf.setframerate(sr)
            wf.writeframes(raw_pcm)

        return file_path

    def ingest_segment(
        self,
        source: Union[Path, str, bytes],
        chapter_id: int,
        segment_index: int,
        speaker: str,
        voice_name: str,
        segment_uid: Optional[str] = None,
        segment_type: str = "narration",
        intensity_level: str = "medium",
        delivery_style: Optional[str] = None,
        literary_text: str = "",
        spoken_text: str = "",
        word_alignments: Optional[list] = None,
    ) -> SegmentAudioContract:
        """
        Ingests a raw speech audio chunk, normalizes acoustic format,
        writes uncompressed 48kHz stereo WAV, and emits immutable SegmentAudioContract.
        """
        if isinstance(source, bytes):
            raw_bytes = source
        else:
            p = Path(source).resolve()
            if not p.exists():
                raise FileNotFoundError(f"Source audio file not found: {p}")
            raw_bytes = p.read_bytes()

        # Compute deterministic UID if not passed
        if not segment_uid:
            hash_input = f"{chapter_id}:{segment_index}:{speaker}:{voice_name}:{spoken_text or literary_text}".encode("utf-8")
            segment_uid = hashlib.sha256(hash_input).hexdigest()[:12]
        else:
            segment_uid = "".join(c for c in segment_uid if c.isalnum() or c in ("-", "_"))

        out_filename = f"c{chapter_id:03d}_s{segment_index:04d}_{segment_uid}.wav"
        out_path = self.output_dir / out_filename

        # 1. Demux C2PA & clean PCM
        samples, src_rate = self.demux_and_clean_pcm(raw_bytes)

        # 2. Standardize format (Resample to 48kHz, upmix to stereo, 30Hz highpass, 5ms taper)
        std_samples = self.standardize_format(samples, src_rate=src_rate)

        # 3. Write uncompressed WAV
        self.write_pcm_wav(out_path, std_samples)

        # 4. Measure duration and checksum
        num_frames = len(std_samples)
        duration_ms = max(10, int(num_frames / float(self.config.target_sample_rate) * 1000.0))

        h = hashlib.sha256()
        with open(out_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        audio_sha256 = h.hexdigest()

        return SegmentAudioContract(
            chapter_id=chapter_id,
            segment_index=segment_index,
            segment_uid=segment_uid,
            audio_path=out_path,
            audio_sha256=audio_sha256,
            sample_rate=self.config.target_sample_rate,
            channels=self.config.target_channels,
            bit_depth=self.config.target_bit_depth,
            duration_ms=duration_ms,
            speaker=speaker,
            voice_name=voice_name,
            segment_type=segment_type if segment_type in ("narration", "dialogue", "thought", "action") else "narration",
            intensity_level=intensity_level if intensity_level in ("whisper", "low", "medium", "high", "explosive") else "medium",
            delivery_style=delivery_style,
            literary_text=literary_text,
            spoken_text=spoken_text or literary_text,
            word_alignments=word_alignments,
        )
