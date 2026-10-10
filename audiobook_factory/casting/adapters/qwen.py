#!/usr/bin/env python3
"""
Audiobook Factory - Room 3.5: Qwen3-TTS / CosyVoice Voice Adapter.
==================================================================
Adapts universal character casting and calibration into Qwen3-TTS / CosyVoice
synthesis payloads: native speed float multipliers, instruction prompts,
and reference audio samples for zero-shot voice cloning.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from audiobook_factory.logger import logger
from audiobook_factory.casting.contracts import (
    CharacterCastAssignment,
    SpectralFormantProfile,
    ProviderCapabilities,
)
from audiobook_factory.casting.adapters.base import BaseVoiceAdapter

logger = logging.getLogger("AudiobookFactory")


class QwenVoiceAdapter(BaseVoiceAdapter):
    """
    Adapter for Qwen3-TTS / CosyVoice / F5-TTS zero-shot voice cloning and speech synthesis.
    """

    def __init__(self, reference_bank_dir: Optional[Path | str] = None):
        self.reference_bank_dir = Path(reference_bank_dir) if reference_bank_dir else None

    def get_provider_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name="qwen3_tts",
            supports_reference_audio=True,
            supports_style_prompt=True,
            supports_native_speed=True,
            native_sample_rate_hz=24000,
            supported_controls=["speed", "reference_audio", "prompt_text", "instruction"],
        )

    def adapt_segment_to_provider(
        self,
        segment: Dict[str, Any],
        character_cast: Optional[CharacterCastAssignment] = None,
    ) -> Dict[str, Any]:
        """
        Translates calibrated segment into Qwen3-TTS payload dict.
        """
        speaker = (segment.get("speaker") or "Narrator").strip()
        is_narrator = speaker.lower() in ("narrator", "narration", "")

        # Extract calibrated tempo multiplier (native speed float)
        formants = SpectralFormantProfile.model_validate(segment.get("formant_profile", {}))
        native_speed = round(formants.target_tempo_multiplier, 3)

        # Resolve reference audio WAV path
        ref_wav: Optional[str] = None
        ref_text: Optional[str] = None

        if character_cast and character_cast.pronunciation_overrides:
            ref_text = character_cast.pronunciation_overrides.get("prompt_text")

        if character_cast and hasattr(character_cast, "reference_audio_path") and character_cast.reference_audio_path:
            ref_wav = str(character_cast.reference_audio_path)
        elif self.reference_bank_dir:
            cand = self.reference_bank_dir / f"{speaker.lower().replace(' ', '_')}_ref.wav"
            if cand.exists():
                ref_wav = str(cand)

        emotion = segment.get("emotion") or segment.get("underlying_emotion", "neutral")
        instruction = "Deliver in a calm, steady narrative cadence." if is_narrator else f"Expressive dialogue with {emotion} emotion."

        payload = {
            "provider": "qwen3_tts",
            "speaker": speaker,
            "text": segment.get("text", ""),
            "speed": native_speed,
            "instruction": instruction,
            "prompt_wav": ref_wav,
            "prompt_text": ref_text or "",
            "sample_rate": 24000,
        }
        return payload
