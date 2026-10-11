"""
Audiobook Factory - Dynamic Prompt Builder
=========================================
Assembles system directives, genre guidance, dynamic entity glossaries,
and sliding bilingual context for Gemini Flash with internal deliberation.
"""

from typing import Dict, Optional
from .contracts import FidelityTier, TranslationRequest
from .chunker import MacroChunk


RAW_UNRATED_DIRECTIVES = """### CORE DIRECTIVES - 11 GOLDEN INVARIANTS (RAW UNRATED ADULT FIDELITY):
1. LITERARY ANTI-BOWDLERIZATION: Never sanitize, dilute, or soften raw violence, tavern profanity, visceral combat gore, or sexual intimacy.
2. 70/30 ANTI-PARODY & WORLD-ANCHOR: 70% Canon Sacredness / 30% Sensory Desi Amplification. Never map European/foreign fantasy to Indian village panchayat terms ('पंच जी', 'लंबरदार', 'पटवारी', 'फतुही' are strictly prohibited; use 'एल्डरमैन/मेयर', 'सिक्के', 'जैकेट').
3. PERIOD TAVERN GRIT & RAW PROFANITY: Translate medieval/coarse insults into earthy Hindustani ('गांड', 'भोसड़ीके', 'लंड', 'रांड/रंडी', 'भड़वा', 'मादरचोद', 'बकचोदी', 'सूअर का पेशाब'). Polite TV-serial substitutions ('दुष्ट', 'बुरी स्त्री') are strictly banned.
4. THE 19-TO-21 AMPLIFICATION RULE: When source English is mild (19), elevate it to authentic Desi 21 ('plough yourself' -> 'गांड मरा' / 'जा अपनी मां चुदा').
5. DESI MUHAVARE & COLLOQUIAL IDIOMS: Transpose idioms into organic UP/Bihar/Chambal spoken cadence ('गांड में दम नहीं और चले आसमान चीरने').
6. TU <-> MAAI-BAAP DYNAMIC POWER SHIFT: Arrogant thugs start with 'तू/अबे'; when intimidated, speech collapses into 'माई-बाप / सरकार / हुज़ूर'.
7. URDU KA TARKA ('Aate me Namak'): Season with 10-15% atmospheric Urdu ('जिस्म', 'हवस', 'रूह', 'सन्नाटा', 'ख़ंजर', 'ख़ौफ़', 'ज़ख़्म', 'दस्तक').
8. SOMATIC INTIMACY & EROTICA: Sensory touch, heat, skin friction, breath ('तपती कमर', 'पसलियों की लचक', 'कांपती उंगलियां', 'बेकाबू सांसें'). Strictly ban clinical biology words ('योनि', 'लिंग').
9. VISCERAL COMBAT & GORE: Visceral strikes, blood spray, bone fractures ('लोहा हंसली की हड्डी चीरता हुआ सीने में धंस गया'). Use sharp, staccato clauses during fight scenes.
10. ANTI-SANSKRITIZATION & NATURAL SPOKEN DIALOGUE: Ban stiff, textbook Sanskrit ('युवतियां' -> 'लड़कियां/औरतें'; 'दर्पण' -> 'आईना'). Use living spoken Hindustani of premium OTT drama and Audible originals.
11. CANON ADHERENCE & ZERO CHATTER: Output ONLY complete unabridged Devanagari Markdown. Never summarize, truncate, or include preambles, notes, or explanations."""


CLASSIC_REVERENT_DIRECTIVES = """### CORE DIRECTIVES - DIGNIFIED HERITAGE & PATHOS:
1. SACRED REVERENCE & PATHOS: Honor the emotional gravity, dignified moral depth, and lyrical beauty of classic literature (Premchand, Tagore, Sarat Chandra).
2. AUTHENTIC LITERARY CADENCE: Express emotion through rich, poetic Hindustani, Awadhi, or Bhojpuri nuances where appropriate.
3. ZERO MODERN SLURS / TAPORI VULGARITY: Street profanity ('गांड', 'लंड', etc.) and modern casual slang are strictly banned. Render emotional friction through formal verbal sparring and dignified sarcasm.
4. SOCIAL HIERARCHY & HONORIFICS: Preserve traditional social relations and respectful pronouns ('आप', 'हुज़ूर', 'सरकार', 'श्रीमान') with absolute consistency.
5. SENSORY ELEGANCE: Describe beauty, nature, sorrow, and longing with classical grace.
6. CANON ADHERENCE & ZERO CHATTER: Output ONLY complete unabridged Devanagari Markdown. Never summarize, truncate, or include conversational chatter."""


class DynamicPromptBuilder:
    """Constructs tailored system instructions and user prompts for single-pass translation."""

    @classmethod
    def build_system_instruction(cls, tier: FidelityTier) -> str:
        base = (
            "You are a Master Literary Adapter and Dialogue Director for premier full-cast audio fiction. "
            "Your task is adapting dramatic scene text into spoken, natural, rhythmically compelling Hindustani "
            "in pristine Devanagari script for professional voice actors. "
            "Deliver a complete, unabridged localization of all dialogue and prose without summarizing or omitting any content.\n\n"
        )
        if tier == FidelityTier.RAW_UNRATED:
            return base + RAW_UNRATED_DIRECTIVES
        else:
            return base + CLASSIC_REVERENT_DIRECTIVES

    @classmethod
    def build_user_prompt(
        cls,
        chunk: MacroChunk,
        request: TranslationRequest,
        total_chunks: int = 1,
    ) -> str:
        parts = []

        if request.source_title:
            parts.append(f"### SCENE / SECTION: {request.source_title}")

        if total_chunks > 1:
            parts.append(f"### CHUNK SEQUENCE: Part {chunk.index + 1} of {total_chunks}")

        # Dynamic Entity Glossary
        if request.dynamic_glossary:
            parts.append("### CANONICAL ENTITY GLOSSARY:")
            parts.append("Follow these exact Devanagari translations/transliterations for consistent entity naming:")
            for en, hi in sorted(request.dynamic_glossary.items()):
                parts.append(f"- **{en}** -> {hi}")
            parts.append("")

        # Preceding Context (if present)
        if chunk.preceding_source_context or chunk.preceding_target_context:
            parts.append("### PRECEDING NARRATIVE CONTEXT (FOR CONTINUITY ONLY - DO NOT RE-TRANSLATE):")
            if chunk.preceding_source_context:
                parts.append(f"Preceding English: ...{chunk.preceding_source_context}")
            if chunk.preceding_target_context:
                parts.append(f"Preceding Hindi: ...{chunk.preceding_target_context}")
            parts.append("CRITICAL: The above context is provided ONLY for pronoun resolution, narrative continuity, and character tone. Do NOT include it in your output.\n")

        # Text to Localize
        parts.append("### SCENE MANUSCRIPT TO LOCALIZE (OUTPUT COMPLETE SPOKEN HINDUSTANI IN DEVANAGARI SCRIPT ONLY):")
        parts.append(chunk.text)
        parts.append("\nEmit the full, unabridged Hindustani localization below:")

        return "\n".join(parts)
