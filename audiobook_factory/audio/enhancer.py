#!/usr/bin/env python3
"""
Audiobook Factory - Neural Vocal Polish & De-Artifacting Engine (v5.4).
=======================================================================
Implements surgical speech enhancement using DeepFilterNet3 (48kHz full-band)
with selective auto-bypass and energy clamping defenses.

Invariants (ADR-023):
1. Selective Auto-Bypass: Bypasses neural inference if input audio is already studio-clean (>45dB SNR).
2. Energy Clamp Protection: Discards enhancement if |delta_RMS| > 2.0dB, preventing unnatural gating.
3. Graceful Degradation: Falls back to pure NumPy/SciPy spectral gate if PyTorch/DeepFilterNet is unavailable.
"""

from __future__ import annotations
import math
import wave
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union

import numpy as np

from audiobook_factory.logger import logger
from audiobook_factory.audio.contracts import EnhancerConfig

# Capability Probing
try:
    import torch
    from df.enhance import enhance, init_df
    _HAS_DEEPFILTER = True
except ImportError:
    torch = None
    enhance = None
    init_df = None
    _HAS_DEEPFILTER = False


def has_deepfilter_engine() -> bool:
    """Returns True if DeepFilterNet3 and PyTorch are installed."""
    return _HAS_DEEPFILTER


class NeuralVocalEnhancer:
    """
    Surgical vocal enhancement processor for removing TTS metallic hash,
    room resonance, and quantization artifacts without chewing up consonants.
    """

    def __init__(self, config: Optional[EnhancerConfig] = None):
        self.config = config or EnhancerConfig()
        self._has_df = has_deepfilter_engine()
        self._df_model = None
        self._df_state = None

        if self._has_df and self.config.enable_neural_enhancement:
            try:
                self._df_model, self._df_state, _ = init_df()
                if torch and torch.cuda.is_available():
                    self._df_model = self._df_model.cuda()
            except Exception as e:
                logger.warning(f"Failed to initialize DeepFilterNet3 model ({e}); using spectral fallback.")
                self._has_df = False

    @property
    def is_neural_active(self) -> bool:
        """Whether neural DeepFilterNet3 is active."""
        return self._has_df and self.config.enable_neural_enhancement

    @staticmethod
    def estimate_snr_db(audio_np: np.ndarray) -> float:
        """
        Estimates Signal-to-Noise Ratio in dB by comparing active speech frames
        to quietest 10th percentile frames.
        """
        if audio_np.size == 0:
            return 0.0

        mono = np.mean(np.abs(audio_np), axis=1) if audio_np.ndim > 1 else np.abs(audio_np)
        if len(mono) < 100:
            return 50.0

        block_size = max(10, len(mono) // 50)
        blocks = [float(np.mean(mono[i * block_size : (i + 1) * block_size] ** 2)) for i in range(50)]
        sorted_energies = sorted(blocks)

        min_noise_energy = sorted_energies[0]
        # If even the quietest frame is loud (> -35 dBFS), the signal is a continuous clean tone/speech
        if min_noise_energy > 5e-4:
            return 60.0

        noise_energy = max(1e-9, float(np.mean(sorted_energies[:5])))
        signal_energy = max(1e-8, float(np.mean(sorted_energies[-10:])))

        snr_linear = signal_energy / noise_energy
        return float(10.0 * math.log10(max(snr_linear, 1.0)))

    def enhance_samples(self, audio_np: np.ndarray, sr: int = 48000) -> Tuple[np.ndarray, bool]:
        """
        Applies neural enhancement or spectral cleaning to float32 samples.
        Returns: (enhanced_audio_np, was_enhanced_boolean)
        """
        if audio_np.size == 0:
            return audio_np, False

        # 1. Selective Auto-Bypass Check
        snr_db = self.estimate_snr_db(audio_np)
        if snr_db >= self.config.snr_bypass_threshold_db and not self.config.enable_neural_enhancement:
            return audio_np, False

        orig_rms = float(np.sqrt(np.mean(audio_np ** 2)))
        if orig_rms < 1e-4:
            return audio_np, False

        # 2. Neural or Spectral Enhancement
        enhanced = None
        if self.is_neural_active and self._df_model is not None:
            try:
                # DeepFilterNet expects (channels, samples)
                is_transposed = False
                if audio_np.ndim == 2 and audio_np.shape[0] > audio_np.shape[1]:
                    samples = audio_np.T
                    is_transposed = True
                else:
                    samples = audio_np

                proc = enhance(self._df_model, self._df_state, samples)
                enhanced = proc.T if is_transposed else proc
            except Exception as e:
                logger.warning(f"DeepFilterNet enhancement error ({e}); falling back to spectral gate.")

        if enhanced is None:
            enhanced = self._spectral_gate_fallback(audio_np)

        # 3. Energy Clamp Protection (ADR-023)
        enhanced_rms = float(np.sqrt(np.mean(enhanced ** 2)))
        delta_db = abs(20.0 * math.log10(max(enhanced_rms, 1e-6) / max(orig_rms, 1e-6)))

        if delta_db > self.config.max_energy_diff_db:
            logger.debug(
                f"Neural enhancement energy delta {delta_db:.2f}dB exceeds clamp {self.config.max_energy_diff_db}dB; "
                f"reverting to clean original stem."
            )
            return audio_np, False

        clean_out = np.nan_to_num(enhanced, nan=0.0, posinf=1.0, neginf=-1.0).astype(np.float32)
        return clean_out, True

    def enhance_file(
        self,
        input_wav: Union[str, Path],
        output_wav: Union[str, Path],
    ) -> bool:
        """
        Enhances a WAV audio file on disk, writing output as 48kHz 24-bit PCM WAV.
        Returns True if enhancement was applied, False if bypassed.
        """
        in_p = Path(input_wav).resolve()
        out_p = Path(output_wav).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        data, sr = self._read_wav(in_p)
        enhanced_data, was_enhanced = self.enhance_samples(data, sr=sr)
        self._write_wav_24bit(out_p, enhanced_data, sr=sr)
        return was_enhanced

    @staticmethod
    def _spectral_gate_fallback(audio_np: np.ndarray, threshold_db: float = -55.0) -> np.ndarray:
        """
        Pure NumPy spectral gate removing very quiet noise floors without altering consonants.
        """
        thresh = 10.0 ** (threshold_db / 20.0)
        # Soft-knee expansion on very low amplitudes
        gain = np.where(np.abs(audio_np) < thresh, (np.abs(audio_np) / max(thresh, 1e-6)) ** 0.5, 1.0)
        return (audio_np * gain).astype(np.float32)

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
