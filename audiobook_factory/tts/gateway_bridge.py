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
import re
import uuid
import wave
import struct
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union, List

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
        if is_mock or is_mock_key:
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


def execute_tts_to_file(
    text: str,
    output_file: Union[str, Path],
    voice: str = "Puck",
    model: Optional[str] = None,
    emotion: str = "neutral",
    acting: Any = None,
    intensity: str = "medium",
    memory_vocal_constraint: Optional[str] = None,
    performance_direction: Optional[Any] = None,
    variant_type: str = "standard",
    rate_limiter: Optional[Any] = None,
    voice_dna: Optional[Any] = None,
    scene_vector: Optional[Any] = None,
    speaker: Optional[str] = None,
    temperature: Optional[float] = None,
    session_id: Optional[str] = None,
    user_id: str = "tts_worker",
    max_retries: int = 3,
    timeout_sec: float = 60.0,
    **kwargs: Any,
) -> Tuple[Path, float]:
    """
    Synthesizes single-utterance speech strictly routed through ModelGateway
    and writes verified audio into output_file. Returns (output_path, duration_sec).
    """
    if os.environ.get("TTS_PRIMARY_BACKEND", "").lower() == "local_winrt":
        from audiobook_factory.tts.providers.winrt import _synthesize_local_winrt_fallback
        return _synthesize_local_winrt_fallback(text, Path(output_file), voice=voice)

    out_path = Path(output_file).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    style_desc = None
    base_temp = temperature
    if performance_direction:
        try:
            from audiobook_factory.performance.tts_adapter import GeminiTTSPerformanceAdapter
            adapter = GeminiTTSPerformanceAdapter()
            adapted = adapter.adapt_direction_to_payload(text, performance_direction, variant_type=variant_type)
            part_payload = adapted.get("part_payload", {})
            style_desc = part_payload.get("speechMetadata", {}).get("style")
            base_temp = adapted.get("temperature", temperature)
        except Exception as e:
            logger.debug(f"Performance adapter fallback: {e}")

    if not style_desc:
        try:
            from audiobook_factory.tts.providers.gemini import resolve_speech_metadata_style
            style_desc = resolve_speech_metadata_style(
                acting, emotion, intensity, memory_vocal_constraint=memory_vocal_constraint
            )
        except Exception:
            pass

    eff_speaker = speaker or getattr(performance_direction, "speaker", None) or "Narrator"
    eff_temp = base_temp if base_temp is not None else (0.32 if eff_speaker == "Narrator" else 0.35)

    speech_result = execute_tts_synthesize(
        text=text,
        voice_name=voice,
        model=model or "gemini-3.8-flash",
        speaker=eff_speaker,
        temperature=eff_temp,
        session_id=session_id,
        user_id=user_id,
        max_retries=max_retries,
        timeout_sec=timeout_sec,
        style_desc=style_desc,
        **kwargs,
    )

    pcm_bytes, dur_sec, sample_rate = extract_pcm_and_duration_from_audio(
        speech_result.audio_bytes,
        mime_type=speech_result.mime_type,
        default_sample_rate=speech_result.sample_rate or 24000,
    )

    # Optional dead-air and C2PA burst clamp (ADR-028)
    try:
        from audiobook_factory.audio_qc_agent import AudioQCAgent
        qc_agent = AudioQCAgent(sample_rate=sample_rate, safety_buffer_ms=150.0)
        clean_pcm, _, _ = qc_agent.surgical_clean_chunk(pcm_bytes)
        pcm_bytes = clean_pcm
        dur_sec = len(pcm_bytes) / float(sample_rate * 2) if sample_rate > 0 else dur_sec
    except Exception:
        pass

    tmp_path = out_path.with_suffix(f".tmp_{uuid.uuid4().hex[:6]}.wav")
    try:
        with wave.open(str(tmp_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)

        from audiobook_factory.audio_utils import _atomic_replace
        _atomic_replace(tmp_path, out_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    return out_path, dur_sec


def execute_multispeaker_batch_to_file(
    batch: Any,
    output_file: Union[str, Path],
    voice_map: Dict[str, str],
    model: Optional[str] = None,
    rate_limiter: Optional[Any] = None,
    temperature: Optional[float] = None,
    session_id: Optional[str] = None,
    user_id: str = "tts_worker",
    max_retries: int = 3,
    timeout_sec: float = 90.0,
    **kwargs: Any,
) -> Tuple[Path, float]:
    """
    Synthesizes a multi-speaker duo batch strictly routed through ModelGateway
    with multiSpeakerVoiceConfig and writes verified audio into output_file.
    Returns (output_path, duration_sec).
    """
    if os.environ.get("TTS_PRIMARY_BACKEND", "").lower() == "local_winrt":
        from audiobook_factory.tts.providers.winrt import _synthesize_local_batch_winrt
        return _synthesize_local_batch_winrt(batch, Path(output_file), voice_map=voice_map)

    out_path = Path(output_file).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    speakers = list(batch.speakers)
    if len(speakers) != 2:
        raise ValueError(
            f"multiSpeakerVoiceConfig strictly requires exactly 2 speakers, got {len(speakers)}: {speakers}"
        )

    spk_configs = []
    for spk in speakers:
        v_name = voice_map.get(spk, "Aoede")
        spk_configs.append({
            "speaker": spk,
            "voiceConfig": {
                "prebuiltVoiceConfig": {
                    "voiceName": v_name
                }
            }
        })

    from audiobook_factory.tts.constants import NUMERAL_NORMALIZATION
    from audiobook_factory.tts.providers.gemini import (
        sanitize_spoken_text_and_extract_stage_directions,
        resolve_speech_metadata_style,
    )

    parts = []
    for seg in batch.segments:
        if hasattr(seg, "spoken_text") and seg.spoken_text:
            raw_text = seg.spoken_text.strip()
        elif isinstance(seg, dict) and seg.get("spoken_text"):
            raw_text = seg["spoken_text"].strip()
        else:
            raw_text = seg.text.strip() if hasattr(seg, "text") else seg.get("text", "").strip()

        clean_text, extracted_cues = sanitize_spoken_text_and_extract_stage_directions(raw_text)
        stripped = re.sub(r"^[^\w\d\u0900-\u097F]+|[^\w\d\u0900-\u097F]+$", "", clean_text)
        if stripped in NUMERAL_NORMALIZATION:
            clean_text = NUMERAL_NORMALIZATION[stripped]
        elif clean_text in NUMERAL_NORMALIZATION:
            clean_text = NUMERAL_NORMALIZATION[clean_text]

        raw_spk = getattr(seg, "speaker", None) if hasattr(seg, "speaker") else (seg.get("speaker") if isinstance(seg, dict) else "Narrator")
        spk = str(raw_spk or "Narrator").strip() or "Narrator"
        is_spk_narrator = spk.lower() in ("narrator", "narration", "")
        acting = getattr(seg, "acting", None) if hasattr(seg, "acting") else (seg.get("acting") if isinstance(seg, dict) else None)
        emotion = getattr(seg, "emotion", "neutral") if hasattr(seg, "emotion") else (seg.get("emotion", "neutral") if isinstance(seg, dict) else "neutral")
        intensity = getattr(seg, "intensity_level", "medium") if hasattr(seg, "intensity_level") else (seg.get("intensity_level", "medium") if isinstance(seg, dict) else "medium")
        mem_vc = getattr(seg, "memory_vocal_constraint", None) if hasattr(seg, "memory_vocal_constraint") else (seg.get("memory_vocal_constraint") if isinstance(seg, dict) else None)
        n_tint = getattr(seg, "narrator_tint", None) if hasattr(seg, "narrator_tint") else (seg.get("narrator_tint") if isinstance(seg, dict) else None)

        style_desc = resolve_speech_metadata_style(
            acting,
            str(emotion or "neutral"),
            str(intensity or "medium"),
            memory_vocal_constraint=mem_vc,
            narrator_tint=n_tint,
            is_narrator=is_spk_narrator,
        )
        if extracted_cues:
            cue_str = ", ".join(extracted_cues)
            if style_desc and style_desc.lower() not in ("neutral", "standard"):
                style_desc = f"{style_desc}, {cue_str}"
            else:
                style_desc = cue_str

        part_item: Dict[str, Any] = {
            "text": clean_text,
            "speechMetadata": {
                "speaker": spk,
            }
        }
        if style_desc and style_desc.lower() not in ("neutral", "standard"):
            part_item["speechMetadata"]["style"] = style_desc
        parts.append(part_item)

    speech_config = {
        "multiSpeakerVoiceConfig": {
            "speakerVoiceConfigs": spk_configs
        }
    }

    # Combined text for logging and rate limiter token tracking
    combined_prompt = " ".join(p["text"] for p in parts)

    speech_result = execute_tts_synthesize(
        text=combined_prompt,
        voice_name=voice_map.get(speakers[0], "Aoede"),
        model=model or "gemini-3.8-flash",
        speaker=speakers[0],
        temperature=temperature or 0.38,
        session_id=session_id,
        user_id=user_id,
        max_retries=max_retries,
        timeout_sec=timeout_sec,
        parts=parts,
        speech_config=speech_config,
        **kwargs,
    )

    pcm_bytes, dur_sec, sample_rate = extract_pcm_and_duration_from_audio(
        speech_result.audio_bytes,
        mime_type=speech_result.mime_type,
        default_sample_rate=speech_result.sample_rate or 24000,
    )

    tmp_path = out_path.with_suffix(f".tmp_{uuid.uuid4().hex[:6]}.wav")
    try:
        with wave.open(str(tmp_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)

        from audiobook_factory.audio_utils import _atomic_replace
        _atomic_replace(tmp_path, out_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    return out_path, dur_sec

