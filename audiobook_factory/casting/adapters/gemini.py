#!/usr/bin/env python3
"""
Audiobook Factory - Room 3.5: Google Gemini TTS Voice Adapter.
=============================================================
Adapts universal character casting and spectral formants into Google Gemini
Flash TTS REST payloads: prebuiltVoiceConfig.voiceName, speechMetadata.style,
calibrated temperature clamping (0.30 - 0.55), and non-destructive EQ clauses.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional

from audiobook_factory.logger import logger
from audiobook_factory.casting.contracts import (
    CharacterCastAssignment,
    SpectralFormantProfile,
    ProviderCapabilities,
)
from audiobook_factory.casting.adapters.base import BaseVoiceAdapter

logger = logging.getLogger("AudiobookFactory")


class GeminiVoiceAdapter(BaseVoiceAdapter):
    """
    Adapter for Google Gemini 2.0 / 2.5 / 3.8 Flash Speech Synthesis.
    """

    def get_provider_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name="gemini_tts",
            supports_reference_audio=False,
            supports_style_prompt=True,
            supports_native_speed=False,
            native_sample_rate_hz=24000,
            supported_controls=["speechMetadata.style", "temperature", "parametric_eq"],
        )

    def adapt_segment_to_provider(
        self,
        segment: Dict[str, Any],
        character_cast: Optional[CharacterCastAssignment] = None,
    ) -> Dict[str, Any]:
        """
        Translates calibrated segment into Gemini TTS payload dict.
        """
        speaker = (segment.get("speaker") or "Narrator").strip()
        is_narrator = speaker.lower() in ("narrator", "narration", "")

        voice_id = character_cast.voice_id if character_cast else segment.get("voice_id", "hi-in-advisor-10")
        if is_narrator:
            voice_id = character_cast.voice_id if character_cast else "Aoede"

        # Resolve acting style and emotion
        emotion = segment.get("emotion") or segment.get("underlying_emotion", "neutral")
        acting = segment.get("acting", {})

        # Build style descriptor
        descriptors = []
        if is_narrator:
            style_desc = "calm, steady, articulate, measured audiobook delivery"
            temperature = 0.32
        else:
            if emotion and emotion.lower() not in ("neutral", "standard"):
                descriptors.append(emotion.lower().replace("_", " "))

            if isinstance(acting, dict):
                deliv = acting.get("delivery_style")
                if deliv and deliv not in ("neutral", "standard"):
                    descriptors.append(str(deliv).replace("_", " "))

            # Translate spectral formants to acoustic vocal anchors
            formant_dict = segment.get("formant_profile") or {}
            chest_db = formant_dict.get("chest_resonance_150hz_db", 0.0)
            presence_db = formant_dict.get("nasal_presence_2800hz_db", 0.0)

            if chest_db >= 1.5:
                descriptors.append("deep resonant chest register")
            elif chest_db <= -1.5:
                descriptors.append("light vocal weight")

            if presence_db >= 1.8:
                descriptors.append("forward vocal projection")

            descriptors.append("understated natural dialogue (never theatrical)")
            style_desc = ", ".join(descriptors)
            temperature = 0.38

        # Extract phase-safe post-DSP EQ filters
        formants = SpectralFormantProfile.model_validate(segment.get("formant_profile", {}))
        eq_filters = formants.to_ffmpeg_filters()

        payload = {
            "provider": "gemini_tts",
            "voice_name": voice_id,
            "text": segment.get("text", ""),
            "speechMetadata": {"style": style_desc},
            "temperature": temperature,
            "post_dsp_eq_filters": eq_filters,
            "target_tempo": formants.target_tempo_multiplier,
        }
        return payload
