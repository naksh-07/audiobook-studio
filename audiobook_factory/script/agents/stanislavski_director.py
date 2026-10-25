#!/usr/bin/env python3
"""
Audiobook Factory - Room 3 Agent B: Stanislavski Subtext Director.
Directs voice acting subtext, transitive actioning verbs, concealed inner emotions,
acting delivery styles, dynamic intensity headroom, and certified acoustic reflex tags.
"""

from __future__ import annotations
import json
import logging
import re
from typing import List, Dict, Any, Optional, Callable, Tuple, Set

from audiobook_factory.dramaturgy.gateway_bridge import execute_dramaturgy_llm
from audiobook_factory.model_manager import get_model_manager, TaskType
from audiobook_factory.safety import get_dramatic_fiction_framing

logger = logging.getLogger("AudiobookFactory")

# Certified physical acoustic reflex tags natively synthesized by Gemini 3.8 Flash Audio modality
CERTIFIED_ACOUSTIC_REFLEX_TAGS: Set[str] = {
    "laughs",
    "sighs",
    "whispers",
    "growls",
    "gasp",
    "chuckles",
    "pant",
    "groan",
}

# Normalization mapping for singular/plural/tense variations and Hindi vocal reflex cues
ACOUSTIC_REFLEX_NORMALIZATION: Dict[str, str] = {
    # English variations -> canonical tag
    "laugh": "laughs",
    "laughs": "laughs",
    "laughing": "laughs",
    "chuckle": "chuckles",
    "chuckles": "chuckles",
    "sigh": "sighs",
    "sighs": "sighs",
    "whisper": "whispers",
    "whispers": "whispers",
    "whispering": "whispers",
    "growl": "growls",
    "growls": "growls",
    "gasp": "gasp",
    "gasps": "gasp",
    "pant": "pant",
    "pants": "pant",
    "panting": "pant",
    "groan": "groan",
    "groans": "groan",
    # Hindi acoustic reflex cues -> canonical tag
    "हँसते हुए": "laughs",
    "हंसते हुए": "laughs",
    "मुस्कुराते हुए": "chuckles",
    "आह भरते हुए": "sighs",
    "फुसफुसाते हुए": "whispers",
    "धीमी आवाज़ में": "whispers",
    "धीमी आवाज में": "whispers",
    "गुर्राते हुए": "growls",
    "हाँफते हुए": "pant",
    "हांफते हुए": "pant",
    "कराहते हुए": "groan",
}


class StanislavskiSubtextDirector:
    """Agent B: Psychological Actioning & Acting Delivery Specialist."""

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def _resolve_model(self) -> str:
        if self.model:
            return self.model
        return get_model_manager().resolve_active_model(TaskType.SCREENPLAY)

    @classmethod
    def process_acoustic_reflexes_and_acting_cues(
        cls,
        text: str,
        is_dialogue: bool = True,
    ) -> Tuple[str, List[str], List[str]]:
        """
        Processes spoken text for acoustic reflex tags and acting descriptors:
        - For narration (is_dialogue=False): Strips ALL bracketed tags entirely
          (Narrator Transparency Invariant).
        - For dialogue (is_dialogue=True):
          - Preserves and normalizes certified acoustic reflex tags:
            [laughs], [sighs], [whispers], [growls], [gasp], [chuckles], [pant], [groan]
          - Strips non-acoustic acting descriptors (e.g. [cold menace], [slowly], [व्यंग्य से])
            from spoken text and returns them as extracted acting cues to route into acting metadata.
        Returns:
            (cleaned_text, preserved_reflex_tags, extracted_acting_cues)
        """
        if not text:
            return "", [], []

        raw_text = str(text)
        if not is_dialogue:
            # Narrator lines must NEVER contain bracketed tags or acting descriptors
            cleaned = re.sub(r"\[[^\]]+\]", "", raw_text)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            return cleaned, [], []

        preserved_tags: List[str] = []
        extracted_cues: List[str] = []

        def _tag_handler(m: re.Match) -> str:
            cue = m.group(1).strip()
            if not cue:
                return ""
            cue_lower = cue.lower()

            # 1. Direct normalization match (e.g. "laughs", "हंसते हुए")
            if cue in ACOUSTIC_REFLEX_NORMALIZATION:
                canonical = ACOUSTIC_REFLEX_NORMALIZATION[cue]
                preserved_tags.append(canonical)
                return f"[{canonical}]"
            if cue_lower in ACOUSTIC_REFLEX_NORMALIZATION:
                canonical = ACOUSTIC_REFLEX_NORMALIZATION[cue_lower]
                preserved_tags.append(canonical)
                return f"[{canonical}]"

            # 2. Check if any certified reflex keyword is contained inside
            for ref in sorted(CERTIFIED_ACOUSTIC_REFLEX_TAGS, key=len, reverse=True):
                if ref in cue_lower:
                    canonical = ACOUSTIC_REFLEX_NORMALIZATION.get(ref, ref)
                    preserved_tags.append(canonical)
                    return f"[{canonical}]"

            # 3. Non-acoustic acting descriptor (e.g. [cold menace], [slowly], [व्यंग्य से])
            extracted_cues.append(cue)
            return ""

        cleaned = re.sub(r"\[([^\]]+)\]", _tag_handler, raw_text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Clean spacing around tags so tag is neatly adjacent or separated by 1 space
        cleaned = re.sub(r"(\[[a-z]+\])\s+", r"\1 ", cleaned)
        cleaned = re.sub(r"\s+(\[[a-z]+\])", r" \1", cleaned)

        # Safety fallback: if everything was stripped, preserve original text if non-empty
        if not cleaned and raw_text.strip():
            cleaned = raw_text.strip()

        return cleaned, preserved_tags, extracted_cues


    def _direct_heuristically(self, segments: List[Dict[str, Any]], context: str = "") -> List[Dict[str, Any]]:
        """
        Native Antigravity heuristic directing engine:
        Extracts deep acting subtext, emotions, dynamic intensity, and certified acoustic reflexes
        from narrative context, speech tags, and literary punctuation without external LLM calls.
        """
        enriched_list = []
        for i, seg in enumerate(segments):
            idx = seg.get("index", i + 1)
            speaker = str(seg.get("speaker") or "Narrator").strip()
            is_narrator = speaker.lower() in ("narrator", "narration", "") or seg.get("type") == "narration"
            raw_text = str(seg.get("text") or "").strip()

            if is_narrator:
                enriched_list.append({
                    "index": idx,
                    "actioning": "narrate",
                    "subtext": "",
                    "underlying_emotion": "neutral",
                    "intensity_level": "medium",
                    "acting": {"delivery_style": "calm_authoritative", "pacing": 1.0},
                    "text": raw_text
                })
                continue

            # Look at preceding segment for narrative speech attribution framing
            prev_narr = ""
            if i > 0 and segments[i - 1].get("speaker") == "Narrator":
                prev_narr = str(segments[i - 1].get("text") or "").lower()

            text_lower = raw_text.lower()
            actioning = "converse"
            subtext = "Communicate my thought directly."
            emotion = "neutral"
            intensity = "medium"
            delivery_style = "grounded_dialogue"
            tone = "natural and clear"
            pacing = 1.0
            reflex_prefix = ""

            # Invariant: Respect pre-existing screenplay dramatic intent
            pre_emotion = str(seg.get("emotion") or seg.get("underlying_emotion") or "").strip()
            pre_acting = seg.get("acting") if isinstance(seg.get("acting"), dict) else {}
            pre_delivery = pre_acting.get("delivery_style") or pre_acting.get("tone")
            pre_intensity = str(seg.get("intensity") or seg.get("intensity_level") or "").strip()

            if pre_delivery and str(pre_delivery).lower() not in ("neutral", "standard", "none"):
                delivery_style = str(pre_delivery)
            if pre_emotion and pre_emotion.lower() not in ("neutral", "standard", "none"):
                emotion = pre_emotion
                if "trembl" in pre_emotion.lower():
                    delivery_style = "whispering_fear"
                elif "cold" in pre_emotion.lower() or "menace" in pre_emotion.lower():
                    delivery_style = "cold_menace"
            if pre_intensity and pre_intensity.lower() not in ("medium", "standard", "none"):
                intensity = pre_intensity

            # 1. Preceding narrative tag heuristics
            if any(w in prev_narr for w in ("गुर्राया", "गुर्राते", "दहाड़ा", "धमकाया", "growled", "snarled", "threatened")):
                actioning = "threaten"
                subtext = "Assert lethal dominance and intimidate into submission."
                emotion = "hostile menace"
                intensity = "high"
                delivery_style = "cold_menace"
                tone = "harsh, guttural and guarded"
                pacing = 0.95
                reflex_prefix = "[growls] "
            elif any(w in prev_narr for w in ("हँसा", "हँसते", "हंसते", "ठहाका", "laughed", "chuckled", "snickered")):
                actioning = "mock"
                subtext = "Show effortless superiority and amusement."
                emotion = "sardonic amusement"
                intensity = "medium"
                delivery_style = "ironic_mockery"
                tone = "teasing and amused"
                pacing = 1.05
                reflex_prefix = "[laughs] "
            elif any(w in prev_narr for w in ("मुस्कुराया", "मुस्कुराते", "व्यंग्य", "smiled", "smirked", "amused")):
                actioning = "taunt"
                subtext = "Provoke a reaction through veiled irony."
                emotion = "cynical irony"
                intensity = "medium"
                delivery_style = "ironic_mockery"
                tone = "dry and knowing"
                reflex_prefix = "[chuckles] "
            elif any(w in prev_narr for w in ("फुसफुसाया", "फुसफुसाते", "धीमी आवाज़", "whispered", "hushed")):
                actioning = "confide"
                subtext = "Prevent anyone nearby from overhearing this dangerous truth."
                emotion = "guarded secrecy"
                intensity = "medium"
                delivery_style = "whispering_fear"
                tone = "hushed and urgent"
                pacing = 0.9
                reflex_prefix = "[whispers] "
            elif any(w in prev_narr for w in ("हाँफा", "हाँफते", "साँस फूल", "panted", "out of breath", "gasping")):
                actioning = "recover"
                subtext = "Force out words despite physical exhaustion."
                emotion = "breathless exhaustion"
                intensity = "high"
                delivery_style = "breathless_exhaustion"
                tone = "labored and strained"
                pacing = 0.85
                reflex_prefix = "[pant] "
            elif any(w in prev_narr for w in ("कराहा", "कराहते", "दर्द से", "groaned", "winced", "in pain")):
                actioning = "endure"
                subtext = "Survive the physical agony while speaking."
                emotion = "acute agony"
                intensity = "high"
                delivery_style = "combat_strain"
                tone = "pained and clenched"
                pacing = 0.85
                reflex_prefix = "[groan] "
            elif any(w in prev_narr for w in ("चौंका", "चौंककर", "सकपकाया", "हक्का-बक्का", "gasped", "startled")):
                actioning = "react"
                subtext = "Stunned by an impossible realization."
                emotion = "shocked disbelief"
                intensity = "high"
                delivery_style = "sharp_inquiry"
                tone = "startled and breathless"
                pacing = 1.1
                reflex_prefix = "[gasp] "
            elif any(w in prev_narr for w in ("आह भरी", "ठंडी सांस", "sighed", "weary")):
                actioning = "concede"
                subtext = "Acknowledge the heavy inevitable burden."
                emotion = "weary resignation"
                intensity = "low"
                delivery_style = "weary_composure"
                tone = "heavy and slow"
                pacing = 0.9
                reflex_prefix = "[sighs] "
            # 2. Text punctuation & lexical heuristics
            elif raw_text.endswith("—") or raw_text.endswith("--"):
                actioning = "interrupt"
                subtext = "Cut in abruptly before the other can finish."
                emotion = "urgent impatience"
                intensity = "high"
                delivery_style = "intense_urgency"
                tone = "sharp, cutting and impatient"
                pacing = 1.15
            elif raw_text.endswith("...") or raw_text.endswith("…"):
                actioning = "hesitate"
                subtext = "Struggle with doubt or unspoken consequences."
                emotion = "lingering hesitation"
                intensity = "low"
                delivery_style = "weary_composure"
                tone = "trailing and uncertain"
                pacing = 0.85
            elif "!?" in raw_text or "?!" in raw_text or "क्या?!" in raw_text:
                actioning = "confront"
                subtext = "Refuse to believe the madness I just heard."
                emotion = "explosive indignation"
                intensity = "explosive"
                delivery_style = "intense_urgency"
                tone = "incredulous and piercing"
                pacing = 1.1
            elif any(k in text_lower for k in ("मरोगे", "खाल", "काट", "तलवार", "धमकी", "खून", "चीर", "kill", "die", "blade", "throat")):
                actioning = "intimidate"
                subtext = "Make it clear violence is imminent."
                emotion = "deadly intent"
                intensity = "high"
                delivery_style = "cold_menace"
                tone = "chilling and resolute"
                pacing = 0.9
            elif any(k in text_lower for k in ("दोस्त", "नमस्ते", "स्वागत", "भोजन", "शराब", "drink", "friend", "welcome", "inn")):
                actioning = "welcome"
                subtext = "Disarm tension and establish convivial hospitality."
                emotion = "warm conviviality"
                intensity = "medium"
                delivery_style = "grounded_dialogue"
                tone = "affable, relaxed and resonant"
                pacing = 1.0
            elif "?" in raw_text and delivery_style == "grounded_dialogue" and emotion == "neutral":
                actioning = "probe"
                subtext = "Extract the hidden truth."
                emotion = "sharp suspicion"
                intensity = "medium"
                delivery_style = "sharp_inquiry"
                tone = "pointed and observant"
                pacing = 1.0
            elif "!" in raw_text:
                actioning = "command"
                subtext = "Demand immediate obedience."
                emotion = "commanding urgency"
                intensity = "high"
                delivery_style = "intense_urgency"
                tone = "firm and commanding"
                pacing = 1.05

            formatted_text = raw_text
            if reflex_prefix and not formatted_text.startswith("["):
                formatted_text = f"{reflex_prefix}{formatted_text}"

            enriched_list.append({
                "index": idx,
                "actioning": actioning,
                "subtext": subtext,
                "underlying_emotion": emotion,
                "intensity_level": intensity,
                "acting": {
                    "delivery_style": delivery_style,
                    "tone": tone,
                    "pacing": pacing,
                },
                "text": formatted_text,
            })
        return enriched_list

    def direct_subtext(
        self,
        segments: List[Dict[str, Any]],
        dramatic_context: str = "",
        is_hindi: bool = False,
        call_llm_fn: Optional[Callable[..., Any]] = None,
        director_card: Optional[Any] = None,
        playbook: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Enriches segments with Stanislavski psychological subtext and acting directives."""
        if not segments:
            return segments

        compact_turns = [
            {
                "index": s.get("index", 1),
                "speaker": str(s.get("speaker") or "Narrator"),
                "type": s.get("type", "narration"),
                "text": str(s.get("text") or ""),
                "emotion": s.get("emotion") or s.get("surface_emotion") or (s.get("acting", {}) if isinstance(s.get("acting"), dict) else {}).get("emotion"),
                "acting": s.get("acting", {}) if isinstance(s.get("acting"), dict) else {},
                "intensity": s.get("intensity") or s.get("intensity_level"),
            }
            for s in segments
        ]

        # Dynamic scene & beat context from dramatic_plan or director_card
        eff_context = dramatic_context
        if not eff_context and director_card:
            if isinstance(director_card, dict):
                try:
                    from audiobook_factory.contracts.playbook import ChapterDirectorCard
                    director_card = ChapterDirectorCard.model_validate(director_card)
                except Exception:
                    pass
            eff_context = director_card.to_prompt_context() if hasattr(director_card, "to_prompt_context") else str(director_card)
        if not eff_context:
            eff_context = "Standard narrative encounter."

        playbook_guidance = ""
        sc_prompt = None
        if isinstance(playbook, dict):
            sc_prompt = playbook.get("screenplay_system_prompt")
        elif hasattr(playbook, "screenplay_system_prompt"):
            sc_prompt = getattr(playbook, "screenplay_system_prompt")
        if sc_prompt and str(sc_prompt).strip():
            playbook_guidance = f"\n\nAuthorial Style & Dialogue Subtext Guidance:\n{str(sc_prompt).strip()}\n"

        sys_prompt = (
            get_dramatic_fiction_framing()
            + "You are an Academy-Award winning Audio Drama Director and Stanislavski Performance Coach.\n"
            "Enrich each dialogue turn with deep psychological subtext, transitive actioning verbs, "
            "concealed inner emotions, dynamic intensity headroom, acting delivery style, and certified acoustic reflex tags.\n\n"
            + playbook_guidance +
            "CORE DIRECTING GUIDELINES:\n"
            "- 'actioning': transitive dramatic intent verb targeting the interlocutor (e.g. 'threaten', 'deflect', 'reassure', 'confess', 'probe', 'comfort', 'intimidate', 'negotiate', 'mock', 'persuade', 'seduce', 'interrogate').\n"
            "- 'subtext': unsaid psychological motivation or truth beneath the spoken words.\n"
            "- 'underlying_emotion': concealed emotional state conflicting with surface presentation.\n"
            "- 'intensity_level': 'low' (whispered/intimate/stealth), 'medium' (standard conversational), 'high' (confrontation/panic), 'explosive' (climactic screams/battle cries).\n"
            "- 'acting': {'delivery_style': string (e.g. 'whispering_fear' | 'cold_menace' | 'breathless_exhaustion' | 'ironic_mockery' | 'bellowing_rage' | 'combat_strain' | 'calm_authoritative' | 'gentle_tender' | 'neutral'), 'tone': string, 'pacing': float between 0.8 and 1.25}.\n\n"
            "ACOUSTIC REFLEX TAGS & SPOKEN TEXT RULES:\n"
            "1. CERTIFIED PHYSICAL ACOUSTIC REFLEX TAGS IN SPOKEN TEXT:\n"
            "   For character dialogue turns, you may embed certified physical acoustic reflex tags:\n"
            "   [laughs], [sighs], [whispers], [growls], [gasp], [chuckles], [pant], [groan]\n"
            "   inside dialogue 'text' at natural dramatic boundaries (at phrase start or dramatic caesuras) when the subtext demands visceral vocalization.\n"
            "   - Why: Gemini 3.8 Flash Audio modality natively renders these bracketed acoustic reflex tags as authentic physical human sounds (laughter, sigh, gasp, growl) rather than reading the bracketed word aloud!\n"
            "   - Examples of natural dramatic placement:\n"
            "     * \"[laughs] वह अब बाहर नहीं आने वाला...\"\n"
            "     * \"[sighs] थोड़ा और इंतज़ार कर लेते हैं।\"\n"
            "     * \"रुक जाओ! [gasp] मुझे सांस लेने दो...\"\n"
            "     * \"[growls] अपनी सीमा में रहो।\"\n"
            "     * \"[chuckles] You really think you can stop me?\"\n"
            "     * \"[whispers] Keep your voice down.\"\n"
            "     * \"[pant] We cannot run any further...\"\n"
            "     * \"[groan] The wound is deeper than I thought...\"\n"
            "   - Restraint Rule: Embed tags sparingly (at most 1 tag per turn). Only use when the dramatic beat truly demands physical vocal reflex. Never alter the dialogue's spoken words.\n\n"
            "2. NARRATOR TRANSPARENCY INVARIANT:\n"
            "   - Narrator lines must NEVER contain acoustic reflex tags; always locked to calm, clean, objective delivery.\n"
            "   - For narration turns, preserve 'text' 100% clean and unchanged with ZERO bracketed tags.\n"
            "   - Lock narrator to: 'actioning': 'narrate', 'acting': {'delivery_style': 'calm_authoritative'}, 'intensity_level': 'medium', 'subtext': '', 'underlying_emotion': 'neutral'.\n\n"
            "3. NON-ACOUSTIC ACTING DESCRIPTORS ARE BANNED FROM SPOKEN TEXT:\n"
            "   - Non-acoustic acting descriptors (e.g. [cold menace], [slowly], [व्यंग्य से], [bitterly], [hesitates], [pause]) must NOT be placed in spoken 'text'.\n"
            "   - They belong strictly in 'acting.delivery_style', 'acting.tone', or 'underlying_emotion'.\n"
            "   - The spoken 'text' field must contain ONLY spoken dialogue words and certified acoustic reflex tags.\n"
        )

        prompt = f"""{get_dramatic_fiction_framing()}Dramatic Scene & Beat Context:
{eff_context}


Dialogue Turns to Direct (JSON):
```json
{json.dumps(compact_turns, ensure_ascii=False, indent=2)}
```

Few-Shot Directing Example:
Input:
```json
[
  {{"index": 1, "speaker": "Narrator", "type": "narration", "text": "Night had fallen over the silent camp."}},
  {{"index": 2, "speaker": "The Sentry", "type": "dialogue", "text": "Who is there? Step into the light."}},
  {{"index": 3, "speaker": "The Wanderer", "type": "dialogue", "text": "Put down your spear. I come with news."}}
]
```
Output:
```json
[
  {{
    "index": 1,
    "actioning": "narrate",
    "subtext": "",
    "underlying_emotion": "neutral",
    "intensity_level": "medium",
    "acting": {{"delivery_style": "calm_authoritative", "pacing": 1.0}},
    "text": "Night had fallen over the silent camp."
  }},
  {{
    "index": 2,
    "actioning": "challenge",
    "subtext": "I am frightened by shadows and ready to strike.",
    "underlying_emotion": "alert dread",
    "intensity_level": "high",
    "acting": {{"delivery_style": "combat_strain", "tone": "sharp and guarded", "pacing": 0.95}},
    "text": "[growls] Who is there? Step into the light."
  }},
  {{
    "index": 3,
    "actioning": "disarm",
    "subtext": "I am completely exhausted but must prevent violence.",
    "underlying_emotion": "weary composure",
    "intensity_level": "low",
    "acting": {{"delivery_style": "breathless_exhaustion", "tone": "calm and reassuring", "pacing": 0.9}},
    "text": "[sighs] Put down your spear. I come with news."
  }}
]
```

Output JSON: A list of objects matching by "index":
[
  {{
    "index": int,
    "actioning": string,
    "subtext": string,
    "underlying_emotion": string,
    "intensity_level": "low" | "medium" | "high" | "explosive",
    "acting": {{"delivery_style": string, "tone": string, "pacing": float}},
    "text": string
  }}
]
"""
        model = self._resolve_model()
        logger.info(f"  [StanislavskiSubtextDirector] Directing {len(segments)} segments with {model}...")

        try:
            if call_llm_fn:
                enriched = call_llm_fn(prompt=prompt, system_instruction=sys_prompt, model=model, json_mode=True)
                if isinstance(enriched, str):
                    import json_repair
                    enriched = json_repair.loads(enriched)
            else:
                enriched = execute_dramaturgy_llm(
                    prompt=prompt,
                    system_instruction=sys_prompt,
                    task="screenplay",
                    model=model,
                    json_mode=True,
                    max_output_tokens=16384,
                    thinking_budget=1024,
                )
        except Exception as e:
            logger.info(f"  [*] StanislavskiSubtextDirector: Text LLM bridge offline/disabled ({e}). Activating Native Antigravity Heuristic Directing Engine.")
            enriched = self._direct_heuristically(segments, eff_context)

        if isinstance(enriched, dict):
            for k in ("turns", "enriched", "segments", "items", "results"):
                if k in enriched and isinstance(enriched[k], list):
                    enriched = enriched[k]
                    break

        if not isinstance(enriched, list):
            enriched = []

        enrich_map = {item.get("index"): item for item in enriched if isinstance(item, dict) and "index" in item}
        for seg in segments:
            idx = seg.get("index")
            spk_name = str(seg.get("speaker") or "").strip().lower()
            is_narrator = spk_name in ("narrator", "narration", "") or seg.get("type") == "narration"

            if idx in enrich_map:
                e = enrich_map[idx]
                # Preserve pre-existing DramaticPlan objectives to eliminate representation drift
                if e.get("actioning") and not seg.get("actioning"):
                    seg["actioning"] = e["actioning"]
                if e.get("subtext") and not seg.get("subtext"):
                    seg["subtext"] = e["subtext"]
                if e.get("underlying_emotion") and not seg.get("underlying_emotion"):
                    seg["underlying_emotion"] = e["underlying_emotion"]
                if e.get("intensity_level") and (not seg.get("intensity_level") or seg.get("intensity_level") == "medium"):
                    seg["intensity_level"] = e["intensity_level"]
                if isinstance(e.get("acting"), dict):
                    seg.setdefault("acting", {})
                    seg["acting"].update(e["acting"])

                # If LLM refined text for dialogue, adopt if non-empty
                if not is_narrator and e.get("text") and str(e["text"]).strip():
                    seg["text"] = str(e["text"]).strip()

            # Process acoustic reflex tags & extract any non-acoustic cues
            cleaned_text, preserved_reflexes, extracted_cues = self.process_acoustic_reflexes_and_acting_cues(
                text=str(seg.get("text") or ""),
                is_dialogue=not is_narrator,
            )
            seg["text"] = cleaned_text

            # Route non-acoustic acting descriptors to acting & emotion
            if extracted_cues and not is_narrator:
                seg.setdefault("acting", {})
                cue_str = ", ".join(extracted_cues)
                cur_delivery = seg["acting"].get("delivery_style")
                if not cur_delivery or cur_delivery in ("neutral", "standard"):
                    seg["acting"]["delivery_style"] = cue_str
                elif cue_str not in cur_delivery:
                    seg["acting"].setdefault("tone", cue_str)
                if not seg.get("underlying_emotion") or seg.get("underlying_emotion") == "neutral":
                    seg["underlying_emotion"] = cue_str

        # Enforce Narrator Transparency Invariant: Narrator is strictly calm and measured, zero melodrama
        for seg in segments:
            spk_name = str(seg.get("speaker") or "").strip().lower()
            if spk_name in ("narrator", "narration", "") or seg.get("type") == "narration":
                seg["actioning"] = "narrate"
                seg["acting"] = {"delivery_style": "calm_authoritative"}
                seg["intensity_level"] = "medium"
                seg["subtext"] = ""
                seg["underlying_emotion"] = "neutral"
                # Strictly ensure narrator text has zero bracketed reflex tags
                cleaned_narr, _, _ = self.process_acoustic_reflexes_and_acting_cues(
                    text=str(seg.get("text") or ""),
                    is_dialogue=False,
                )
                seg["text"] = cleaned_narr

        # Fallback for dialogue turns with missing acting directives to prevent flatline performance
        for seg in segments:
            spk_name = str(seg.get("speaker") or "").strip().lower()
            if spk_name not in ("narrator", "narration", "") and seg.get("type") != "narration":
                acting = seg.setdefault("acting", {})
                cur_ds = acting.get("delivery_style")
                if not cur_ds or cur_ds in ("neutral", "standard"):
                    actioning = str(seg.get("actioning") or "").lower()
                    emotion = str(seg.get("underlying_emotion") or seg.get("emotion") or "").lower()
                    text = str(seg.get("text") or "")

                    if any(k in emotion or k in actioning for k in ("rage", "anger", "furious", "threat", "menace", "धमकी", "क्रोध")):
                        acting["delivery_style"] = "cold_menace" if "threat" in actioning or "menace" in actioning else "bellowing_rage"
                    elif any(k in emotion or k in actioning for k in ("mock", "tease", "amuse", "swagger", "irony", "व्यंग्य", "मज़ाक")):
                        acting["delivery_style"] = "ironic_mockery"
                    elif any(k in emotion or k in actioning for k in ("fear", "panic", "plead", "terror", "डर", "घबराहट")):
                        acting["delivery_style"] = "whispering_fear"
                    elif any(k in emotion or k in actioning for k in ("strain", "exhaust", "pain", "combat", "दर्द", "कराह")):
                        acting["delivery_style"] = "combat_strain"
                    elif any(k in emotion or k in actioning for k in ("tender", "gentle", "comfort", "reassure", "प्रेम", "शांत")):
                        acting["delivery_style"] = "gentle_tender"
                    elif "?" in text:
                        acting["delivery_style"] = "sharp_inquiry"
                    elif "!" in text:
                        acting["delivery_style"] = "intense_urgency"
                    else:
                        acting["delivery_style"] = "grounded_dialogue"

        return segments

