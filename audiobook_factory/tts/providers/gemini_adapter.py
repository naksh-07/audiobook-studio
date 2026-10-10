#!/usr/bin/env python3
"""
Audiobook Factory - Production-Grade Gemini Flash TTS Model Adapter.
Implements BaseTTSModelAdapter for Google Gemini 3.8 / 2.5 / 2.0 Flash TTS with
120+ SQLite key pool rotation, in-flight lease management, BLOCK_NONE safety thresholds,
stealth SDK headers, human cadence controller, and rich directing NLP.
"""

from __future__ import annotations
import os
import sys
import json
import time
import base64
import struct
import wave
import io
import urllib.request
import urllib.error
import asyncio
from typing import Dict, Any, List, Tuple, Optional, Set

from audiobook_factory.logger import logger
from audiobook_factory.tts.contracts import CanonicalTTSRequest, SynthesizedAudioChunk, DeliveryIntent
from audiobook_factory.tts.providers.base import BaseTTSModelAdapter
from audiobook_factory.key_manager import (
    get_persistent_key_pool,
    classify_gemini_error,
    AllKeysExhaustedTodayError,
)
from audiobook_factory.cadence import get_stealth_sdk_headers, get_human_cadence_controller


# Permissive safety settings for dramatic literary fiction (Zero Moral Policing Invariant)
GEMINI_PERMISSIVE_SAFETY: List[Dict[str, str]] = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},
]

GEMINI_SUPPORTED_VOICES: Set[str] = {
    "Puck", "Charon", "Kore", "Fenrir", "Aoede", "Zephyr", "Leda", "Orus",
    "puck", "charon", "kore", "fenrir", "aoede", "zephyr", "leda", "orus"
}


class GeminiTTSAdapter(BaseTTSModelAdapter):
    """
    Production-grade adapter connecting CanonicalTTSRequest to Google Gemini Flash Speech API.
    """

    def __init__(self, model_name: str = "gemini-3.8-flash", config: Optional[Dict[str, Any]] = None):
        super().__init__(model_name=model_name, config=config)
        self.api_endpoint_template = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        self.max_retries = self.config.get("max_retries", 4)
        self.timeout_sec = self.config.get("timeout_sec", 45)

    def validate_request_compatibility(self, request: CanonicalTTSRequest) -> Tuple[bool, List[str]]:
        """Validates canonical request compatibility against Gemini TTS constraints."""
        warnings: List[str] = []
        is_compat = True

        if request.voice_id not in GEMINI_SUPPORTED_VOICES:
            warnings.append(f"Voice '{request.voice_id}' not in recognized Gemini prebuilt voice roster.")

        if len(request.spoken_text) > 3000:
            warnings.append(f"Spoken text length ({len(request.spoken_text)} chars) exceeds recommended Gemini atomic unit limit.")

        if request.temperature < 0.20 or request.temperature > 0.60:
            warnings.append(f"Temperature {request.temperature:.2f} is outside recommended clamp (0.30 - 0.52).")

        return is_compat, warnings

    def get_model_metadata(self) -> Dict[str, Any]:
        """Returns standard capabilities for Gemini Flash TTS."""
        return {
            "model_name": self.model_name,
            "provider": "google",
            "supported_voices": list(GEMINI_SUPPORTED_VOICES),
            "native_sample_rate": 24000,
            "max_recommended_chars": 2000,
            "temperature_bounds": (0.30, 0.52),
            "supports_speech_metadata": True,
            "supports_reference_audio": False,
        }

    def synthesize_chunk(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk:
        """
        Executes single-request speech synthesis with key pool rotation, stealth headers, and retries.
        """
        pool = get_persistent_key_pool()
        cadence = get_human_cadence_controller()

        # Build style descriptor NLP from DeliveryIntent
        style_desc = self.build_style_descriptor(request.delivery_intent, speaker=request.speaker)

        part_payload: Dict[str, Any] = {"text": request.spoken_text}
        if style_desc:
            part_payload["speechMetadata"] = {"style": style_desc}

        # Temperature clamp (0.30 - 0.52, Narrator locked at 0.32)
        if request.speaker == "Narrator":
            clamped_temp = 0.32
        else:
            clamped_temp = max(0.30, min(request.temperature, 0.52))

        payload = {
            "contents": [{"parts": [part_payload]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": request.voice_id
                        }
                    }
                },
                "temperature": clamped_temp,
            },
            "safetySettings": GEMINI_PERMISSIVE_SAFETY,
        }

        json_data = json.dumps(payload).encode("utf-8")
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                api_key = pool.get_key(service="tts", provider="gemini", model=self.model_name)
            except Exception as e:
                # If key pool throws (e.g. mock test environment or key exhausted)
                api_key = os.environ.get("GEMINI_API_KEY", "MOCK_KEY")

            key_preview = api_key[:8] + "..." if api_key else "UNKNOWN"

            url = self.api_endpoint_template.format(model=self.model_name, key=api_key)
            headers = get_stealth_sdk_headers(api_key=api_key)
            headers["Content-Type"] = "application/json"


            req = urllib.request.Request(url, data=json_data, headers=headers, method="POST")

            try:
                with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
                    res_body = response.read().decode("utf-8")
                    data = json.loads(res_body)

                try:
                    pool.record_success(api_key, model=self.model_name, provider="gemini")
                    cadence.record_success(api_key)
                except Exception:
                    pass

                audio_bytes, dur_sec = self._parse_audio_response(data)

                return SynthesizedAudioChunk(
                    segment_uid=request.segment_uid,
                    pcm_bytes=audio_bytes,
                    sample_rate=request.sample_rate,
                    num_channels=1,
                    duration_sec=dur_sec,
                    provider_model=self.model_name,
                    voice_id=request.voice_id,
                    metadata={
                        "attempt": attempt,
                        "key_preview": key_preview,
                        "style_descriptor": style_desc,
                        "temperature": clamped_temp,
                    },
                )

            except urllib.error.HTTPError as e:
                err_text = ""
                try:
                    err_text = e.read().decode("utf-8")
                except Exception:
                    pass
                classification = classify_gemini_error(e.code, err_text)
                try:
                    if e.code == 429:
                        pool.mark_temporary_backoff(api_key, retry_after=5.0, model=self.model_name, provider="gemini")
                    elif e.code in (400, 403):
                        pool.mark_key_invalid(api_key, error_msg=err_text, provider="gemini")
                    cadence.record_failure(api_key, e.code)
                except Exception:
                    pass

                last_error = RuntimeError(f"Gemini TTS HTTP {e.code}: {err_text}")
                logger.warning(
                    f"[!] Gemini TTS attempt {attempt}/{self.max_retries} failed on key {key_preview}: "
                    f"HTTP {e.code} ({classification})"
                )
                time.sleep(1.0 * attempt)

            except json.JSONDecodeError as e:
                last_error = RuntimeError(f"Gemini TTS returned malformed non-JSON payload: {e}")
                logger.warning(
                    f"[!] Gemini TTS attempt {attempt}/{self.max_retries} received malformed JSON on key {key_preview}: {e}"
                )
                time.sleep(1.0 * attempt)

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[!] Gemini TTS attempt {attempt}/{self.max_retries} unexpected error on key {key_preview}: {e}"
                )
                time.sleep(1.0 * attempt)

        raise last_error or RuntimeError(f"Gemini TTS synthesis failed after {self.max_retries} retries.")

    async def synthesize_chunk_async(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk:
        """Asynchronous synthesis wrapper executing in worker thread pool."""
        return await asyncio.to_thread(self.synthesize_chunk, request)

    @classmethod
    def build_style_descriptor(cls, intent: DeliveryIntent, speaker: str = "Narrator") -> Optional[str]:
        """
        Synthesizes structured DeliveryIntent into a natural language style prompt
        for Gemini speechMetadata.style.
        """
        descriptors: List[str] = []

        if speaker == "Narrator":
            return "calm, steady, articulate, measured audiobook delivery"

        if intent.delivery_style not in ("neutral", "standard"):
            descriptors.append(intent.delivery_style.replace("_", " "))

        if intent.emotion not in ("neutral", "standard"):
            descriptors.append(intent.emotion.replace("_", " "))

        if intent.intensity == "explosive":
            descriptors.append("extreme intensity")
        elif intent.intensity == "high":
            descriptors.append("high intensity")
        elif intent.intensity == "low":
            descriptors.append("subdued quiet intensity")

        if intent.proximity == "intimate":
            descriptors.append("intimate whisper proximity")
        elif intent.proximity == "close_mic":
            descriptors.append("close mic intimate tone")
        elif intent.proximity == "distant":
            descriptors.append("projected distant voice")

        if intent.memory_vocal_constraint:
            descriptors.append(intent.memory_vocal_constraint)

        if intent.extracted_stage_cues:
            for cue in intent.extracted_stage_cues:
                if cue not in descriptors:
                    descriptors.append(cue)

        # Anti-theatricality restraint anchor
        descriptors.append("understated natural dialogue (never theatrical)")

        return ", ".join(descriptors) if descriptors else None

    def _parse_audio_response(self, data: Dict[str, Any]) -> Tuple[bytes, float]:
        """Parses audio bytes and duration from Gemini response candidates."""
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini response contained no candidates.")

        cand = candidates[0]
        content = cand.get("content") or {}
        parts = content.get("parts", [])
        audio_b64 = None
        mime_type = "audio/wav"

        for p in parts:
            if "inlineData" in p:
                audio_b64 = p["inlineData"].get("data")
                mime_type = p["inlineData"].get("mimeType", mime_type)
                break

        if not audio_b64:
            raise ValueError("Gemini response parts contained no inlineData audio content.")

        raw_bytes = base64.b64decode(audio_b64)

        # Extract PCM and calculate duration
        if "wav" in mime_type.lower() or raw_bytes.startswith(b"RIFF"):
            with io.BytesIO(raw_bytes) as wav_io:
                with wave.open(wav_io, "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    pcm_bytes = wf.readframes(frames)
                    dur_sec = frames / float(rate) if rate > 0 else 0.0
                    return pcm_bytes, dur_sec

        # Raw PCM fallback (16-bit 24kHz mono = 48000 bytes/sec)
        dur_sec = len(raw_bytes) / 48000.0
        return raw_bytes, dur_sec
