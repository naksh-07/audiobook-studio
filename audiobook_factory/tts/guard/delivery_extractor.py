#!/usr/bin/env python3
"""
Audiobook Factory - Delivery Intent & Stage Cue Extractor.
Extracts emotional directives, vocal delivery styles, SSML tags, and stage directions
from text prompts, producing a strongly-typed DeliveryIntent while stripping raw tags
from spoken text to prevent TTS vocal leakage.
"""

from __future__ import annotations
import re
from typing import Tuple, List, Dict, Any, Optional

from audiobook_factory.tts.contracts import DeliveryIntent


EMOTION_KEYWORDS: Dict[str, Dict[str, Any]] = {
    "whisper": {"emotion": "whisper", "delivery_style": "whisper", "proximity": "intimate", "intensity": "low", "pacing": 0.95},
    "whispers": {"emotion": "whisper", "delivery_style": "whisper", "proximity": "intimate", "intensity": "low", "pacing": 0.95},
    "फुसफुसाते हुए": {"emotion": "whisper", "delivery_style": "whisper", "proximity": "intimate", "intensity": "low", "pacing": 0.95},
    "धीमी आवाज़": {"emotion": "whisper", "delivery_style": "whisper", "proximity": "intimate", "intensity": "low", "pacing": 0.95},

    "shout": {"emotion": "anger", "delivery_style": "shouting", "proximity": "distant", "intensity": "explosive", "pacing": 1.15},
    "shouts": {"emotion": "anger", "delivery_style": "shouting", "proximity": "distant", "intensity": "explosive", "pacing": 1.15},
    "yell": {"emotion": "anger", "delivery_style": "shouting", "proximity": "distant", "intensity": "explosive", "pacing": 1.15},
    "yells": {"emotion": "anger", "delivery_style": "shouting", "proximity": "distant", "intensity": "explosive", "pacing": 1.15},
    "scream": {"emotion": "fear_terror", "delivery_style": "screaming", "proximity": "distant", "intensity": "explosive", "pacing": 1.20},
    "screams": {"emotion": "fear_terror", "delivery_style": "screaming", "proximity": "distant", "intensity": "explosive", "pacing": 1.20},
    "चिल्लाते हुए": {"emotion": "anger", "delivery_style": "shouting", "proximity": "distant", "intensity": "explosive", "pacing": 1.15},
    "चीखते हुए": {"emotion": "fear_terror", "delivery_style": "screaming", "proximity": "distant", "intensity": "explosive", "pacing": 1.20},

    "angry": {"emotion": "anger", "delivery_style": "harsh_tense", "proximity": "normal", "intensity": "high", "pacing": 1.05},
    "furious": {"emotion": "rage", "delivery_style": "explosive", "proximity": "normal", "intensity": "explosive", "pacing": 1.10},
    "गुस्से में": {"emotion": "anger", "delivery_style": "harsh_tense", "proximity": "normal", "intensity": "high", "pacing": 1.05},
    "क्रोधित": {"emotion": "anger", "delivery_style": "harsh_tense", "proximity": "normal", "intensity": "high", "pacing": 1.05},

    "sad": {"emotion": "sadness", "delivery_style": "somber_heavy", "proximity": "close_mic", "intensity": "low", "pacing": 0.85},
    "crying": {"emotion": "grief", "delivery_style": "weeping_broken", "proximity": "close_mic", "intensity": "medium", "pacing": 0.80},
    "tears": {"emotion": "grief", "delivery_style": "weeping_broken", "proximity": "close_mic", "intensity": "medium", "pacing": 0.85},
    "रोते हुए": {"emotion": "grief", "delivery_style": "weeping_broken", "proximity": "close_mic", "intensity": "medium", "pacing": 0.80},
    "उदास": {"emotion": "sadness", "delivery_style": "somber_heavy", "proximity": "close_mic", "intensity": "low", "pacing": 0.85},

    "fear": {"emotion": "fear", "delivery_style": "trembling_tense", "proximity": "close_mic", "intensity": "high", "pacing": 1.10},
    "scared": {"emotion": "fear", "delivery_style": "trembling_tense", "proximity": "close_mic", "intensity": "high", "pacing": 1.10},
    "terrified": {"emotion": "terror", "delivery_style": "gasping_frantic", "proximity": "close_mic", "intensity": "explosive", "pacing": 1.20},
    "डरते हुए": {"emotion": "fear", "delivery_style": "trembling_tense", "proximity": "close_mic", "intensity": "high", "pacing": 1.10},
    "घबराया हुआ": {"emotion": "anxious", "delivery_style": "breathless_rushed", "proximity": "close_mic", "intensity": "medium", "pacing": 1.15},

    "mocking": {"emotion": "mockery", "delivery_style": "smirking_taunting", "proximity": "normal", "intensity": "medium", "pacing": 1.00},
    "sarcastic": {"emotion": "sarcasm", "delivery_style": "dry_ironic", "proximity": "normal", "intensity": "medium", "pacing": 0.95},
    "हँसते हुए": {"emotion": "amused", "delivery_style": "chuckle_light", "proximity": "normal", "intensity": "medium", "pacing": 1.05},
    "व्यंग्य": {"emotion": "sarcasm", "delivery_style": "dry_ironic", "proximity": "normal", "intensity": "medium", "pacing": 0.95},

    "urgent": {"emotion": "urgency", "delivery_style": "rapid_firm", "proximity": "normal", "intensity": "high", "pacing": 1.20},
    "calm": {"emotion": "calm", "delivery_style": "steady_measured", "proximity": "normal", "intensity": "low", "pacing": 0.95},
    "steady": {"emotion": "calm", "delivery_style": "steady_measured", "proximity": "normal", "intensity": "low", "pacing": 1.00},
    "शांत": {"emotion": "calm", "delivery_style": "steady_measured", "proximity": "normal", "intensity": "low", "pacing": 0.95},
}


class DeliveryIntentExtractor:
    """
    Scans raw text for:
    1. Square-bracketed stage directions: `[whispering]`, `[angry]`, `[screams]`
    2. Parenthetical stage cues at segment starts/ends: `(furious, shouting)`
    3. SSML tags: `<break time="500ms"/>`, `<emphasis level="strong">`, `<prosody rate="fast">`
    4. Neural performance hints and acoustic constraints.

    Returns:
    - Cleaned spoken text ready for TTS synthesis (zero raw tags).
    - Structured DeliveryIntent object.
    - Detected pause hints (e.g. from SSML breaks).
    """

    # Bracketed cues: [whispers], [angry, shouting], [furious]
    BRACKET_CUE_PATTERN = re.compile(r"\[([^\]]+)\]")

    # Parenthetical cues when they represent acting directions (e.g., at boundaries or containing known emotion keywords)
    PAREN_CUE_PATTERN = re.compile(r"\(([^\)]+)\)")

    # SSML Tags: <break time="..."/>, <emphasis ...>, <prosody ...>, etc.
    SSML_BREAK_PATTERN = re.compile(r"<break\s+[^>]*time=[\"'](\d+)(ms|s)[\"'][^>]*\/?>", re.IGNORECASE)
    SSML_GENERIC_TAG_PATTERN = re.compile(r"</?[a-zA-Z][^>]*>", re.IGNORECASE)

    @classmethod
    def extract_intent_and_clean_text(
        cls,
        text: str,
        default_intent: Optional[DeliveryIntent] = None,
    ) -> Tuple[str, DeliveryIntent, Dict[str, Any]]:
        """
        Processes raw text, extracting delivery cues and stripping them from spoken text.

        Returns:
            (clean_spoken_text, delivery_intent, extraction_metadata)
        """
        if not text:
            return "", default_intent or DeliveryIntent(), {}

        working = text
        extracted_cues: List[str] = []
        emotion = default_intent.emotion if default_intent else "neutral"
        delivery_style = default_intent.delivery_style if default_intent else "standard"
        intensity = default_intent.intensity if default_intent else "medium"
        proximity = default_intent.proximity if default_intent else "normal"
        pacing = default_intent.pacing_multiplier if default_intent else 1.0
        vocal_constraint = default_intent.memory_vocal_constraint if default_intent else None
        ssml_break_ms = 0

        # 1. Check SSML <break> tags
        for m in cls.SSML_BREAK_PATTERN.finditer(working):
            val = int(m.group(1))
            unit = m.group(2).lower()
            ms = val if unit == "ms" else val * 1000
            ssml_break_ms += ms
            extracted_cues.append(f"ssml_break_{ms}ms")

        # Strip all SSML tags from spoken text
        working = cls.SSML_GENERIC_TAG_PATTERN.sub(" ", working)

        # 2. Extract Square-Bracketed Stage Cues: [whispers], [angry]
        for m in cls.BRACKET_CUE_PATTERN.finditer(working):
            cue_text = m.group(1).strip()
            extracted_cues.append(cue_text)
            matched_dict = cls._match_cue_keywords(cue_text)
            if matched_dict:
                emotion = matched_dict.get("emotion", emotion)
                delivery_style = matched_dict.get("delivery_style", delivery_style)
                proximity = matched_dict.get("proximity", proximity)
                intensity = matched_dict.get("intensity", intensity)
                pacing = matched_dict.get("pacing", pacing)
            else:
                # Custom constraint or physical anchor
                vocal_constraint = cue_text

        # Strip square bracket tags
        working = cls.BRACKET_CUE_PATTERN.sub(" ", working)

        # 3. Check Parenthetical Cues: (whispering), (गुस्से में)
        def _paren_repl(m: re.Match) -> str:
            nonlocal emotion, delivery_style, proximity, intensity, pacing, vocal_constraint
            content = m.group(1).strip()
            matched = cls._match_cue_keywords(content)
            if matched:
                extracted_cues.append(content)
                emotion = matched.get("emotion", emotion)
                delivery_style = matched.get("delivery_style", delivery_style)
                proximity = matched.get("proximity", proximity)
                intensity = matched.get("intensity", intensity)
                pacing = matched.get("pacing", pacing)
                return " "
            return m.group(0)

        working = cls.PAREN_CUE_PATTERN.sub(_paren_repl, working)

        # 4. Collapse superfluous whitespace
        clean_text = re.sub(r"\s+", " ", working).strip()

        # Build raw style descriptor summary
        raw_descriptor = f"{emotion} ({delivery_style}, {intensity})" if emotion != "neutral" else None

        intent = DeliveryIntent(
            emotion=emotion,
            delivery_style=delivery_style,
            intensity=intensity,
            proximity=proximity,
            pacing_multiplier=pacing,
            memory_vocal_constraint=vocal_constraint,
            extracted_stage_cues=extracted_cues,
            raw_style_descriptor=raw_descriptor,
        )

        metadata = {
            "ssml_break_ms": ssml_break_ms,
            "extracted_cues_count": len(extracted_cues),
        }

        return clean_text, intent, metadata

    @classmethod
    def _match_cue_keywords(cls, cue_text: str) -> Optional[Dict[str, Any]]:
        """Matches keywords inside stage cues against emotion/delivery dictionaries."""
        lower_cue = cue_text.lower()
        for kw, config in EMOTION_KEYWORDS.items():
            if kw.lower() in lower_cue:
                return config
        return None
