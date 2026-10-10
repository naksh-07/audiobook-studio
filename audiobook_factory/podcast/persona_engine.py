#!/usr/bin/env python3
"""
Audiobook Factory - Dedicated Podcast Engine: 2-Host Persona Engine.
Manages vocal casting, dynamic roles, behavioral polarity, and prompt engineering
for Host A (Inquisitive Driver) and Host B (Domain Storyteller).
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union, List
from audiobook_factory.podcast.contracts import HostProfile, HostRole


class HostPersonaEngine:
    """
    Manages the 2-Host conversational matrix and behavioral directives.
    Guarantees clear vocal separation, spatial staging, and dynamic chemistry.
    """

    AVAILABLE_PODCAST_VOICES: List[str] = [
        "Puck",    # Default Host A (Inquisitive, energetic)
        "Aoede",   # Default Host B (Warm, articulate, storyteller)
        "Fenrir",  # Deep, resonant male
        "Charon",  # Authoritative, grave male
        "Zephyr",  # Soft, intimate, reflective
        "Kore",    # Bright, youthful female
    ]

    @staticmethod
    def create_custom_host(
        host_id: str,
        name: str,
        role: HostRole = "inquisitive_driver",
        voice_id: str = "Puck",
        pitch_shift: float = 0.0,
        speed_multiplier: float = 1.0,
        pan: float = 0.0,
        interjections: Optional[List[str]] = None,
    ) -> HostProfile:
        """Helper to create a calibrated custom host profile."""
        return HostProfile(
            host_id=host_id,
            name=name,
            role=role,
            voice_id=voice_id,
            pitch_shift=pitch_shift,
            speed_multiplier=speed_multiplier,
            pan=pan,
            interjection_lexicon=interjections or [],
        )

    @staticmethod
    def load_hosts_from_config(config_path: Union[str, Path]) -> Optional[Dict[str, HostProfile]]:
        """Loads custom host profiles from a podcast_config.json file."""
        p = Path(config_path).resolve()
        if not p.exists():
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            hosts_dict = data.get("hosts", data)
            res = {}
            for h_id, h_data in hosts_dict.items():
                if isinstance(h_data, dict):
                    res[h_id] = HostProfile.model_validate(h_data)
            return res if res else None
        except Exception as e:
            logger.warning(f"  [!] Failed to load hosts from config {p}: {e}")
            return None

    @staticmethod
    def get_default_hosts(is_hindi: bool = True) -> Dict[str, HostProfile]:
        """Returns standard calibrated 2-Host pairing."""
        if is_hindi:
            host_a = HostProfile(
                host_id="host_a",
                name="समीर",
                role="inquisitive_driver",
                voice_id="Puck",
                pitch_shift=-0.5,
                speed_multiplier=1.04,
                pan=-0.25,
                energy_baseline=0.88,
                interjection_lexicon=[
                    "अरे सुनो",
                    "सच में?",
                    "रुको ज़रा...",
                    "मतलब क्या?",
                    "ओह भाई!",
                    "ये तो कमाल है!",
                ],
            )
            host_b = HostProfile(
                host_id="host_b",
                name="प्रिया",
                role="domain_expert",
                voice_id="Aoede",
                pitch_shift=+0.5,
                speed_multiplier=0.98,
                pan=+0.25,
                energy_baseline=0.82,
                interjection_lexicon=[
                    "बिल्कुल!",
                    "दरअसल बात ये है कि...",
                    "यही तो सबसे बड़ा मोड़ है!",
                    "हाँ, सही पकड़े हैं।",
                    "ध्यान से समझो...",
                ],
            )
        else:
            host_a = HostProfile(
                host_id="host_a",
                name="Alex",
                role="inquisitive_driver",
                voice_id="Puck",
                pitch_shift=-0.5,
                speed_multiplier=1.05,
                pan=-0.25,
                energy_baseline=0.88,
                interjection_lexicon=[
                    "Wait, hold on...",
                    "Are you serious?",
                    "Wait, what happened next?",
                    "No way!",
                    "That is wild!",
                ],
            )
            host_b = HostProfile(
                host_id="host_b",
                name="Maya",
                role="domain_expert",
                voice_id="Aoede",
                pitch_shift=+0.5,
                speed_multiplier=0.98,
                pan=+0.25,
                energy_baseline=0.82,
                interjection_lexicon=[
                    "Exactly.",
                    "Here's what really happened...",
                    "And that's the turning point.",
                    "Right, and listen to this...",
                    "Here is why that matters...",
                ],
            )

        return {"host_a": host_a, "host_b": host_b}

    @staticmethod
    def build_system_prompt(hosts: Dict[str, HostProfile], is_hindi: bool = True) -> str:
        """Constructs persona system prompt for LLM podcast generation."""
        ha = hosts.get("host_a") or HostProfile(host_id="host_a", name="Host A")
        hb = hosts.get("host_b") or HostProfile(host_id="host_b", name="Host B")

        lang_instruction = (
            "Language: Fluent, conversational, dramatic Hindustani (spontaneous spoken Hindi with natural Urdu and colloquial loanwords). "
            "Never use robotic textbook Sanskritized phrasing."
            if is_hindi
            else "Language: Fluent, engaging, audio-first English (conversational, dynamic, spontaneous)."
        )

        return f"""You are the Executive Producer & Lead Writer for a world-class narrative podcast.
{lang_instruction}

HOST ROLES & CHEMISTRY:
1. {ha.name} (Host A - Inquisitive Driver / Listener Proxy):
   - Fast, energetic, asks the questions every listener wants to ask.
   - Pushes back, reacts with genuine surprise, gasps, laughs, and interrupts naturally.
   - Natural spoken interjections: {', '.join(ha.interjection_lexicon[:4])}.

2. {hb.name} (Host B - Domain Storyteller / Expert):
   - Measured, insightful, sets the dramatic atmosphere, unpacks subtext and motives.
   - Brings the listener into the world of the characters and dissects the stakes.
   - Natural spoken interjections: {', '.join(hb.interjection_lexicon[:4])}.

STRICT SPOKEN-FIRST RULES:
- BREATHABILITY: Maximum 18-22 words per dialogue turn. Break thoughts into punchy back-and-forth exchanges.
- NO SCRIPTED MONOLOGUES: Hosts must NEVER lecture or deliver multi-paragraph essays. Keep the dialogue bouncy and interactive.
- EMOTIONAL POLARITY: One host's curiosity triggers the other host's dramatic reveal.
- IMMERSIVE RE-ENACTMENTS: When quoting characters from the story, hosts either quote them passionately or briefly act them out with emotional color.
"""
