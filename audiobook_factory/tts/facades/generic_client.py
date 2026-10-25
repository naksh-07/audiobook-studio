#!/usr/bin/env python3
"""
Audiobook Factory - Generic TTS Client Facade.
Provides simple, low-latency, ad-hoc single-utterance speech synthesis.
Ideal for voice testing, studio auditions, notifications, and interactive CLI prompts.
"""

from __future__ import annotations
import io
import wave
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Union

from audiobook_factory.tts.contracts import (
    CanonicalTTSRequest,
    SynthesizedAudioChunk,
    AudioValidationResult,
    TTSPipelineMode,
    DeliveryIntent,
)
from audiobook_factory.tts.core_orchestrator import TTSCoreOrchestrator


class GenericTTSClient:
    """
    High-level facade for single-utterance speech synthesis.
    """

    def __init__(self, orchestrator: Optional[TTSCoreOrchestrator] = None):
        self.orchestrator = orchestrator or TTSCoreOrchestrator()

    def speak(
        self,
        text_or_request: Union[str, CanonicalTTSRequest],
        voice: str = "Puck",
        model: str = "gemini-3.8-flash-tts",
        output_path: Optional[Union[str, Path]] = None,
        validate: bool = True,
        speaker: str = "Narrator",
        delivery_intent: Optional[DeliveryIntent] = None,
        **guard_kwargs: Any,
    ) -> Tuple[Optional[Path], SynthesizedAudioChunk, Optional[AudioValidationResult]]:
        """
        Synthesizes single text or request, returning raw audio chunk and optional saved file path.
        """
        if delivery_intent and "default_intent" not in guard_kwargs:
            guard_kwargs["default_intent"] = delivery_intent

        chunk, validation = self.orchestrator.synthesize(
            request_or_text=text_or_request,
            voice_id=voice,
            model=model,
            speaker=speaker,
            pipeline_mode=TTSPipelineMode.GENERIC,
            validate_audio=validate,
            **guard_kwargs,
        )

        saved_path: Optional[Path] = None
        if output_path:
            p = Path(output_path).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            self._write_pcm_to_wav(chunk.pcm_bytes, p, chunk.sample_rate)
            saved_path = p

        return saved_path, chunk, validation

    def speak_to_bytes(
        self,
        text_or_request: Union[str, CanonicalTTSRequest],
        voice: str = "Puck",
        model: str = "gemini-3.8-flash-tts",
        validate: bool = True,
        speaker: str = "Narrator",
        delivery_intent: Optional[DeliveryIntent] = None,
        **guard_kwargs: Any,
    ) -> bytes:
        """
        Synthesizes single text or request directly into a complete in-memory WAV byte stream.
        """
        _, chunk, _ = self.speak(
            text_or_request=text_or_request,
            voice=voice,
            model=model,
            output_path=None,
            validate=validate,
            speaker=speaker,
            delivery_intent=delivery_intent,
            **guard_kwargs,
        )
        return self._pcm_to_wav_bytes(chunk.pcm_bytes, chunk.sample_rate)

    @staticmethod
    def _pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = 24000) -> bytes:
        """Encodes raw 16-bit mono PCM bytes into WAV container bytes in-memory."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        return buf.getvalue()

    @staticmethod
    def _write_pcm_to_wav(pcm_bytes: bytes, wav_path: Path, sample_rate: int = 24000) -> None:
        """Writes raw 16-bit mono PCM bytes to standard WAV file."""
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
