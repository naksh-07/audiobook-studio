#!/usr/bin/env python3
"""
Audiobook Factory - Reference Spectrum Matching Engine (v5.4).
==============================================================
Transplants the acoustic profile, frequency balance, and dynamic curve
of a golden reference master (e.g. Audible bestseller) onto synthesized chapters.

Invariants (ADR-023):
1. Spectral Clamping Invariant: Hard-clamps spectral gain corrections to max +/-3.0dB
   to eliminate unnatural EQ artifacts or frequency pumping.
2. Graceful Degradation: Falls back to 1/3-octave FFT spectral envelope matching if
   'matchering' is not installed.
"""

from __future__ import annotations
import math
import wave
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union

import numpy as np
import scipy.signal as sig

from audiobook_factory.logger import logger
from audiobook_factory.audio.contracts import ReferenceMatcherConfig

# Capability Probing
try:
    import matchering as mg
    _HAS_MATCHERING = True
except ImportError:
    mg = None
    _HAS_MATCHERING = False


def has_matchering_engine() -> bool:
    """Returns True if Matchering 2.0 is installed."""
    return _HAS_MATCHERING


class ReferenceSpectrumMatcher:
    """
    Automated reference mastering and spectral envelope matcher.
    Matches target chapter audio to a golden reference track within strict safety bounds.
    """

    def __init__(self, config: Optional[ReferenceMatcherConfig] = None):
        self.config = config or ReferenceMatcherConfig()
        self._has_mg = has_matchering_engine()

    @property
    def is_matchering_active(self) -> bool:
        """Whether Matchering 2.0 is active."""
        return self._has_mg and self.config.enable_reference_matching

    def match_spectrum(
        self,
        target_np: np.ndarray,
        reference_np: np.ndarray,
        sr: int = 48000,
    ) -> np.ndarray:
        """
        Applies reference spectrum matching with +/-3dB hard clamping.
        Input: target_np (samples, channels), reference_np (samples, channels).
        Output: matched float32 numpy array with identical shape.
        """
        if target_np.size == 0 or reference_np.size == 0:
            return target_np

        clamp_db = float(self.config.max_spectral_correction_db)

        # Fallback / Built-in FFT 1/3-Octave Envelope Matcher
        return self._fft_octave_spectral_matcher(target_np, reference_np, sr=sr, max_clamp_db=clamp_db)

    def match_files(
        self,
        target_wav: Union[str, Path],
        reference_wav: Union[str, Path],
        output_wav: Union[str, Path],
    ) -> Path:
        """
        Matches target WAV to reference WAV on disk, writing output as 48kHz 24-bit PCM WAV.
        """
        target_p = Path(target_wav).resolve()
        ref_p = Path(reference_wav).resolve()
        out_p = Path(output_wav).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if not target_p.exists():
            raise FileNotFoundError(f"Target WAV not found: {target_p}")
        if not ref_p.exists():
            raise FileNotFoundError(f"Reference WAV not found: {ref_p}")

        # Attempt Matchering 2.0 native if active
        if self.is_matchering_active and mg is not None:
            try:
                mg.process(
                    target=str(target_p),
                    reference=str(ref_p),
                    results=[mg.pcm24(str(out_p))],
                )
                logger.info(f"[+] Matchering 2.0 reference spectrum applied: {out_p.name}")
                return out_p
            except Exception as e:
                logger.warning(f"Matchering 2.0 execution error ({e}); using FFT spectral fallback.")

        # Built-in FFT Clamped Matcher
        target_data, sr_t = self._read_wav(target_p)
        ref_data, _ = self._read_wav(ref_p)

        matched = self.match_spectrum(target_data, ref_data, sr=sr_t)
        self._write_wav_24bit(out_p, matched, sr=sr_t)
        return out_p

    @staticmethod
    def _fft_octave_spectral_matcher(
        target: np.ndarray,
        reference: np.ndarray,
        sr: int = 48000,
        max_clamp_db: float = 3.0,
    ) -> np.ndarray:
        """
        Calculates 1/3-octave smoothed spectral difference between target & reference,
        applies hard +/-max_clamp_db clamping, and filters target in frequency domain.
        """
        t_mono = np.mean(target, axis=1) if target.ndim > 1 else target
        r_mono = np.mean(reference, axis=1) if reference.ndim > 1 else reference

        n_fft = 4096
        hop = 2048

        def pad_to_nfft(arr: np.ndarray) -> np.ndarray:
            return np.pad(arr, (0, max(0, n_fft - len(arr)))) if len(arr) < n_fft else arr

        t_mono_padded = pad_to_nfft(t_mono)
        r_mono_padded = pad_to_nfft(r_mono)

        _, _, t_spec = sig.stft(t_mono_padded, fs=sr, nperseg=n_fft, noverlap=hop)
        _, _, r_spec = sig.stft(r_mono_padded, fs=sr, nperseg=n_fft, noverlap=hop)

        t_mag = np.mean(np.abs(t_spec), axis=1) + 1e-8
        r_mag = np.mean(np.abs(r_spec), axis=1) + 1e-8

        # Normalize RMS
        t_mag = t_mag / np.mean(t_mag)
        r_mag = r_mag / np.mean(r_mag)

        # Calculate raw gain curve in dB
        gain_db = 20.0 * np.log10(r_mag / t_mag)
        # Smooth gain curve with 1D Gaussian filter
        gain_db_smoothed = sig.medfilt(gain_db, kernel_size=15)
        # Apply hard +/- clamp (ADR-023)
        gain_db_clamped = np.clip(gain_db_smoothed, -max_clamp_db, max_clamp_db)
        linear_filter_gains = 10.0 ** (gain_db_clamped / 20.0)

        # Apply filter to each channel in STFT domain
        out_channels = []
        for ch in range(target.shape[1] if target.ndim > 1 else 1):
            ch_data = target[:, ch] if target.ndim > 1 else target
            ch_data_padded = pad_to_nfft(ch_data)
            
            f, t_bins, zxx = sig.stft(ch_data_padded, fs=sr, nperseg=n_fft, noverlap=hop)
            zxx_filtered = zxx * linear_filter_gains[:, np.newaxis]
            _, reconstructed = sig.istft(zxx_filtered, fs=sr, nperseg=n_fft, noverlap=hop)
            
            # Match original length
            if len(reconstructed) < len(ch_data):
                reconstructed = np.pad(reconstructed, (0, len(ch_data) - len(reconstructed)))
            else:
                reconstructed = reconstructed[:len(ch_data)]
            out_channels.append(reconstructed.astype(np.float32))

        if target.ndim > 1:
            return np.column_stack(out_channels)
        return out_channels[0]

    @staticmethod
    def _read_wav(file_path: Path) -> Tuple[np.ndarray, int]:
        """Reads WAV into float32 array [-1.0, 1.0]."""
        with wave.open(str(file_path.resolve()), "rb") as wf:
            sr = wf.getframerate()
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            frames = wf.getnframes()
            raw = wf.readframes(frames)

        if frames == 0 or len(raw) == 0:
            return np.zeros((0, 2), dtype=np.float32), sr

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
            if ch > 2:
                data = data[:, :2]
        else:
            data = np.column_stack((data, data))

        return np.nan_to_num(data, nan=0.0, posinf=1.0, neginf=-1.0), sr

    @staticmethod
    def _write_wav_24bit(file_path: Path, data: np.ndarray, sr: int = 48000) -> None:
        """Writes float32 array to 48kHz 24-bit PCM WAV."""
        clean = np.clip(data, -1.0, 1.0)
        int32_arr = np.clip(np.round(clean * 8388607.0), -8388608, 8388607).astype("<i4")
        pcm_bytes = int32_arr.view(np.uint8).reshape(-1, 4)[:, :3].flatten().tobytes()

        with wave.open(str(file_path.resolve()), "wb") as wf:
            wf.setnchannels(2 if data.ndim > 1 else 1)
            wf.setsampwidth(3)
            wf.setframerate(sr)
            wf.writeframes(pcm_bytes)
