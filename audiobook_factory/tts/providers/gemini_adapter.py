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
import asyncio
from typing import Dict, Any, List, Tuple, Optional, Set

from audiobook_factory.logger import logger
from audiobook_factory.tts.contracts import CanonicalTTSRequest, SynthesizedAudioChunk, DeliveryIntent
from audiobook_factory.tts.providers.base import BaseTTSModelAdapter
from audiobook_factory.tts.gateway_bridge import (
    execute_tts_synthesize,
    extract_pcm_and_duration_from_audio,
)


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
        self.api_endpoint_template = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
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
        Executes single-request speech synthesis routed through ModelGateway
        with ACID key leasing, stealth headers, and retries.
        """
        # Build style descriptor NLP from DeliveryIntent
        style_desc = self.build_style_descriptor(request.delivery_intent, speaker=request.speaker)

        session_id = f"scene_{request.segment_uid[:8]}" if request.segment_uid else "tts_session"

        speech_result = execute_tts_synthesize(
            text=request.spoken_text,
            voice_name=request.voice_id,
            model=self.model_name,
            speaker=request.speaker,
            temperature=request.temperature,
            session_id=session_id,
            max_retries=self.max_retries,
            timeout_sec=self.timeout_sec,
            style_desc=style_desc,
        )

        # Extract PCM and calculate duration
        pcm_bytes, dur_sec, sample_rate = extract_pcm_and_duration_from_audio(
            speech_result.audio_bytes,
            mime_type=speech_result.mime_type,
            default_sample_rate=speech_result.sample_rate or request.sample_rate or 24000,
        )

        metadata = dict(speech_result.metadata)
        metadata.setdefault("attempt", 1)
        metadata.setdefault("key_preview", "CONTROL_PLANE")
        metadata["style_descriptor"] = style_desc
        metadata["temperature"] = (
            0.32 if request.speaker == "Narrator" else max(0.30, min(request.temperature, 0.52))
        )

        return SynthesizedAudioChunk(
            segment_uid=request.segment_uid,
            pcm_bytes=pcm_bytes,
            sample_rate=sample_rate,
            num_channels=1,
            duration_sec=dur_sec,
            provider_model=self.model_name,
            voice_id=request.voice_id,
            metadata=metadata,
        )

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
