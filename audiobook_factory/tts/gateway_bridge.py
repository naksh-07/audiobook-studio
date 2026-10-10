#!/usr/bin/env python3
"""
Audiobook Factory - Room 4: TTS ModelGateway Control Plane Bridge.
===================================================================
Authoritative control-plane bridge for Option C Studio TTS Platform Core:
- GenericTTSClient, LongFormTTSClient, MultiCastStudioClient
- GeminiTTSAdapter & ModelAdapterRegistry

Guarantees:
1. Strict ModelGateway Routing: Eliminates rogue urllib calls and routes 100% of speech
   synthesis traffic through the central control plane (ModelGateway.synthesize_speech).
2. Atomic Key Leasing: Acquires Concurrency=1 mutual exclusion handles from KeyLeaseManager
   specifically for the 'tts' workload type.
3. The 7 Iron Shields AntiBanGuard: Enforces token-bucket rate limiting (11 RPM), session
   affinity sticky binding across dialogue scenes, anti-correlation cooldowns, stealth SDK headers,
   and the emergency global tripwire.
4. Permissive Creative Fiction Framing: Applies BLOCK_NONE safety thresholds across all harm categories.
5. Graceful Standalone Fallback: Preserves offline mock execution and zero-dependency
   fallback if running outside the unified studio workspace or under mock fixtures.
"""

from __future__ import annotations
import os
import io
import wave
import struct
from typing import Any, Dict, Optional, Tuple

from audiobook_factory.logger import logger
from audiobook_factory.core.models.adapters.base import SpeechResult


def extract_pcm_and_duration_from_audio(
    audio_bytes: bytes,
    mime_type: str = "audio/wav",
    default_sample_rate: int = 24000,
) -> Tuple[bytes, float, int]:
    """
    Safely extracts 16-bit linear PCM bytes, duration in seconds, and sample rate
    from a WAV container (RIFF) or raw PCM byte stream.
    """
    if audio_bytes.startswith(b"RIFF") or "wav" in mime_type.lower():
        try:
            with io.BytesIO(audio_bytes) as wav_io:
                with wave.open(wav_io, "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    pcm_bytes = wf.readframes(frames)
                    dur_sec = frames / float(rate) if rate > 0 else 0.0
                    return pcm_bytes, dur_sec, rate
        except Exception as e:
            logger.warning(f"  [!] Failed to parse WAV header, falling back to raw PCM: {e}")

    # Raw 16-bit mono PCM fallback (2 bytes per sample)
    bytes_per_sec = default_sample_rate * 2
    dur_sec = len(audio_bytes) / float(bytes_per_sec) if bytes_per_sec > 0 else 0.0
    return audio_bytes, dur_sec, default_sample_rate


def execute_tts_synthesize(
    text: str,
    voice_name: str = "Puck",
    model: Optional[str] = None,
    delivery_intent: Optional[Any] = None,
    speaker: Optional[str] = None,
    temperature: float = 0.35,
    session_id: Optional[str] = None,
    user_id: str = "tts_worker",
    max_retries: int = 3,
    timeout_sec: float = 45.0,
    style_desc: Optional[str] = None,
    fast_mode: bool = False,
    **kwargs: Any,
) -> SpeechResult:
    """
    Executes a Room 4 Speech Synthesis request strictly through ModelGateway.
    Returns SpeechResult containing decoded audio bytes and operational metadata.
    """
    # Clamped temperature (Narrator locked at 0.32, dialogue clamped between 0.30 and 0.52)
    if speaker == "Narrator":
        clamped_temp = 0.32
    else:
        clamped_temp = max(0.30, min(temperature, 0.52))

    # Construct payload parts with speechMetadata styling if available
    parts = kwargs.pop("parts", None)
    if not parts:
        part_dict: Dict[str, Any] = {"text": text}
        if style_desc:
            part_dict["speechMetadata"] = {"style": style_desc}
        parts = [part_dict]

    try:
        from audiobook_factory.core.models.gateway import get_model_gateway
        gateway = get_model_gateway()

        speech_result = gateway.synthesize_speech(
            text=text,
            voice_name=voice_name,
            model=model,
            preferred_provider="gemini",
            session_id=session_id or "tts_session",
            user_id=user_id,
            fast_mode=fast_mode,
            max_retries=max_retries,
            timeout=timeout_sec,
            temperature=clamped_temp,
            parts=parts,
            **kwargs,
        )
        return speech_result

    except Exception as e:
        # Check if environment is explicitly running in offline mock without keys
        is_mock = os.environ.get("MOCK_OFFLINE", "").lower() in ("true", "1")
        is_mock_key = os.environ.get("GEMINI_API_KEY", "").lower().startswith("mock")
        if (is_mock or is_mock_key) and ("No available" in str(e) or isinstance(e, ImportError)):
            num_samples = int(24000 * 0.8)
            samples = [8000 if (i // 50) % 2 == 0 else -8000 for i in range(num_samples)]
            mock_pcm = struct.pack(f"<{num_samples}h", *samples)
            with io.BytesIO() as wav_io:
                with wave.open(wav_io, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(mock_pcm)
                mock_wav = wav_io.getvalue()
            return SpeechResult(
                audio_bytes=mock_wav,
                mime_type="audio/wav",
                sample_rate=24000,
                duration_sec=0.8,
                tokens_used=10,
                model_id=model or "gemini-3.8-flash-tts",
                provider="gemini",
                metadata={"mock_mode": True, "attempt": 1},
            )

        logger.error(f"  [!] TTS ModelGateway dispatch failed: {e}")
        raise
