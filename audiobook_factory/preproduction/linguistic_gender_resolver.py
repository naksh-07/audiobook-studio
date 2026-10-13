#!/usr/bin/env python3
"""
Audiobook Factory - Room 1 Subsystem: Deterministic Linguistic Gender Resolver.
==============================================================================
Provides zero-token, deterministic linguistic gender resolution for novel entities.
Analyzes local chapter texts across:
1. English pronoun co-occurrence windows (+/- 20 words around entity mentions).
2. Title honorifics and occupational nouns (Lord/Sir/King vs Lady/Queen/Sorceress).
3. Post-dialogue pronoun attribution tags ("... said the traveler. He smiled").
4. Hindi verb agreement and somatic inflections (रहा था/बोला vs रही थी/बोली).

Eliminates "neutral-gender blindness" and cross-gender voice allocation collisions.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any


# English pronoun dictionaries
ENGLISH_MALE_PRONOUNS = {"he", "him", "his", "himself"}
ENGLISH_FEMALE_PRONOUNS = {"she", "her", "hers", "herself"}

# English title / role markers
ENGLISH_MALE_TITLES = {
    "lord", "sir", "king", "prince", "father", "brother", "baron", "duke",
    "count", "mr", "mr.", "master", "alderman", "innkeeper", "witcher",
    "boy", "man", "gentleman", "butcher", "husband", "son", "emperor",
    "monk", "priest", "uncle", "grandfather", "knight", "commander",
}

ENGLISH_FEMALE_TITLES = {
    "lady", "queen", "princess", "sister", "mother", "duchess", "countess",
    "mrs", "mrs.", "miss", "sorceress", "priestess", "girl", "woman",
    "maiden", "damsel", "matron", "wife", "daughter", "empress", "nun",
    "aunt", "grandmother", "dame", "heroine",
}

# Hindi verbal & somatic gender markers (inflections)
HINDI_MALE_MARKERS = {
    "रहा था", "गया", "आया", "बोला", "कहा", "पूछा", "चीखा", "हंसा", "मुस्कुराया",
    "कसाई", "आदमी", "युवक", "लड़का", "पुरुष", "वृद्ध", "भाई", "पिता", "पति", "बेटा",
}

HINDI_FEMALE_MARKERS = {
    "रही थी", "गई", "आई", "बोली", "कही", "पूछी", "चीखी", "हंसी", "मुस्कुराई",
    "स्त्री", "महिला", "युवती", "लड़की", "कन्या", "माता", "बहन", "पत्नी", "बेटी",
}


@dataclass
class GenderEvidence:
    """Evidence ledger supporting resolved biological/dramatic gender."""
    gender: str = "male"  # strictly 'male' or 'female'
    confidence: float = 0.5
    male_score: int = 0
    female_score: int = 0
    evidence_snippets: List[str] = field(default_factory=list)
    method: str = "corpus_heuristic"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gender": self.gender,
            "confidence": round(self.confidence, 3),
            "male_score": self.male_score,
            "female_score": self.female_score,
            "evidence_snippets": self.evidence_snippets[:5],
            "method": self.method,
        }


class LinguisticGenderResolver:
    """
    Novel-agnostic deterministic gender resolution engine.
    """

    @classmethod
    def resolve_gender(
        cls,
        name: str,
        corpus_text: str,
        associated_titles: Optional[List[str]] = None,
        aliases: Optional[List[str]] = None,
        is_hindi: bool = False,
    ) -> GenderEvidence:
        """
        Resolves gender for an entity name by scanning surrounding context in corpus_text.
        """
        c_clean = name.strip()
        if not c_clean:
            return GenderEvidence(gender="male", confidence=0.5, method="fallback_empty")

        all_names = [c_clean] + [a.strip() for a in (aliases or []) if a.strip()]
        titles = [t.strip().lower() for t in (associated_titles or []) if t.strip()]

        male_score = 0
        female_score = 0
        snippets: List[str] = []

        # 1. Title analysis from target_name (+25) and associated_titles (+15)
        for target_name in all_names:
            if not target_name:
                continue
            for w in target_name.lower().split():
                clean_w = re.sub(r"[^\w]", "", w)
                if clean_w in ENGLISH_MALE_TITLES:
                    male_score += 25
                    snippets.append(f"Target name contains male title: '{clean_w}'")
                elif clean_w in ENGLISH_FEMALE_TITLES:
                    female_score += 25
                    snippets.append(f"Target name contains female title: '{clean_w}'")

        for t in titles:
            for w in t.split():
                clean_w = re.sub(r"[^\w]", "", w)
                if clean_w in ENGLISH_MALE_TITLES:
                    male_score += 15
                    snippets.append(f"Male title marker: '{clean_w}'")
                elif clean_w in ENGLISH_FEMALE_TITLES:
                    female_score += 15
                    snippets.append(f"Female title marker: '{clean_w}'")

        # 2. Mask quoted dialogue to prevent vocative bleeding ('Hello Ciri,' he said)
        unquoted = re.sub(r'["\'”][^"\'”\n]{1,300}["\'”]', ' [DIALOGUE] ', corpus_text)

        # 3. Check each name token across unquoted narrative text
        for target_name in all_names:
            if not target_name or len(target_name) < 2:
                continue

            escaped_name = re.escape(target_name)

            # A. Possessive pronouns in same clause: Name ... her vs Name ... his
            her_pos = len(re.findall(rf'\b{escaped_name}\b[^\.\?!;\n]{{1,60}}\b(?:her)\b', unquoted, re.IGNORECASE))
            his_pos = len(re.findall(rf'\b{escaped_name}\b[^\.\?!;\n]{{1,60}}\b(?:his)\b', unquoted, re.IGNORECASE))
            if her_pos:
                female_score += her_pos * 4
                snippets.append(f"Same-clause possessive 'her' ({her_pos}x)")
            if his_pos:
                male_score += his_pos * 4
                snippets.append(f"Same-clause possessive 'his' ({his_pos}x)")

            # B. Subject pronoun in same clause: Name ... she vs Name ... he
            she_sub = len(re.findall(rf'\b{escaped_name}\b[^\.\?!;\n]{{1,60}}\b(?:she)\b', unquoted, re.IGNORECASE))
            he_sub = len(re.findall(rf'\b{escaped_name}\b[^\.\?!;\n]{{1,60}}\b(?:he)\b', unquoted, re.IGNORECASE))
            if she_sub:
                female_score += she_sub * 5
                snippets.append(f"Same-clause subject 'she' ({she_sub}x)")
            if he_sub:
                male_score += he_sub * 5
                snippets.append(f"Same-clause subject 'he' ({he_sub}x)")

            # B2. Sentence-initial subject pronoun in next sentence: Name ... . She vs Name ... . He
            next_she = len(re.findall(rf'\b{escaped_name}\b[^\.\?!;\n]{{0,60}}[\.\?!]\s*She\b', unquoted))
            next_he = len(re.findall(rf'\b{escaped_name}\b[^\.\?!;\n]{{0,60}}[\.\?!]\s*He\b', unquoted))
            if next_she:
                female_score += next_she * 6
                snippets.append(f"Followed in next sentence by 'She' ({next_she}x)")
            if next_he:
                male_score += next_he * 6
                snippets.append(f"Followed in next sentence by 'He' ({next_he}x)")

            # C. Speech attribution tags where target_name is the speaker:
            spk_she = len(re.findall(rf'\[DIALOGUE\]\s*(?:said|asked|replied|cried|whispered|screamed|muttered)\s+{escaped_name}\b[^\.\?!]*[\.\?!]\s*She\b', unquoted))
            spk_he = len(re.findall(rf'\[DIALOGUE\]\s*(?:said|asked|replied|cried|whispered|screamed|muttered)\s+{escaped_name}\b[^\.\?!]*[\.\?!]\s*He\b', unquoted))
            name_spk_she = len(re.findall(rf'\b{escaped_name}\b\s+(?:said|asked|replied|cried|whispered|screamed|muttered)\s*\[DIALOGUE\][^\.\?!]*[\.\?!]\s*She\b', unquoted))
            name_spk_he = len(re.findall(rf'\b{escaped_name}\b\s+(?:said|asked|replied|cried|whispered|screamed|muttered)\s*\[DIALOGUE\][^\.\?!]*[\.\?!]\s*He\b', unquoted))
            
            if spk_she or name_spk_she:
                cnt = spk_she + name_spk_she
                female_score += cnt * 10
                snippets.append(f"Speech attribution followed by 'She' ({cnt}x)")
            if spk_he or name_spk_he:
                cnt = spk_he + name_spk_he
                male_score += cnt * 10
                snippets.append(f"Speech attribution followed by 'He' ({cnt}x)")

            # D. Appositive and title/role nouns in same clause:
            # Special check for 'wife of [name]' and '[name]'s wife': target is husband (MALE)
            wife_of_cnt = len(re.findall(rf'\bwife\s+of\s+(?:the\s+)?{escaped_name}\b', unquoted, re.IGNORECASE))
            wife_of_cnt += len(re.findall(rf'\b{escaped_name}["\'’]s\s+wife\b', unquoted, re.IGNORECASE))
            if wife_of_cnt:
                male_score += wife_of_cnt * 10
                snippets.append(f"Target has a wife ('wife of / 's wife', target is male) ({wife_of_cnt}x)")

            # Special check for 'husband of [name]' and '[name]'s husband': target is wife (FEMALE)
            husband_of_cnt = len(re.findall(rf'\bhusband\s+of\s+(?:the\s+)?{escaped_name}\b', unquoted, re.IGNORECASE))
            husband_of_cnt += len(re.findall(rf'\b{escaped_name}["\'’]s\s+husband\b', unquoted, re.IGNORECASE))
            if husband_of_cnt:
                female_score += husband_of_cnt * 10
                snippets.append(f"Target has a husband ('husband of / 's husband', target is female) ({husband_of_cnt}x)")

            # General role nouns (excluding 'wife' and 'husband' to prevent misattribution)
            f_nouns = len(re.findall(rf'\b{escaped_name}\b[^\.\?!;\n]{{0,40}}\b(?:woman|girl|lady|maiden|sorceress|queen|princess|priestess|poetess|witch|daughter|mother|sister|empress|duchess)\b', unquoted, re.IGNORECASE))
            f_nouns += len(re.findall(rf'\b(?:woman|girl|lady|maiden|sorceress|queen|princess|priestess|poetess|witch|daughter|mother|sister|empress|duchess)\b[^\.\?!;\n]{{0,40}}\b{escaped_name}\b', unquoted, re.IGNORECASE))
            m_nouns = len(re.findall(rf'\b{escaped_name}\b[^\.\?!;\n]{{0,40}}\b(?:man|boy|fellow|gentleman|witcher|alderman|butcher|bard|king|prince|lord|sir|baron|duke|son|father|brother|emperor)\b', unquoted, re.IGNORECASE))
            m_nouns += len(re.findall(rf'\b(?:man|boy|fellow|gentleman|witcher|alderman|butcher|bard|king|prince|lord|sir|baron|duke|son|father|brother|emperor)\b[^\.\?!;\n]{{0,40}}\b{escaped_name}\b', unquoted, re.IGNORECASE))

            # If explicitly named as the wife or husband in apposition:
            is_wife_cnt = len(re.findall(rf'\b(?:his\s+wife|a\s+wife)[,\s]+{escaped_name}\b', unquoted, re.IGNORECASE))
            is_wife_cnt += len(re.findall(rf'\b{escaped_name}[,\s]+(?:his\s+wife|the\s+wife)\b', unquoted, re.IGNORECASE))
            if is_wife_cnt:
                female_score += is_wife_cnt * 8
                snippets.append(f"Target is identified as wife ({is_wife_cnt}x)")

            is_husband_cnt = len(re.findall(rf'\b(?:her\s+husband|a\s+husband)[,\s]+{escaped_name}\b', unquoted, re.IGNORECASE))
            is_husband_cnt += len(re.findall(rf'\b{escaped_name}[,\s]+(?:her\s+husband|the\s+husband)\b', unquoted, re.IGNORECASE))
            if is_husband_cnt:
                male_score += is_husband_cnt * 8
                snippets.append(f"Target is identified as husband ({is_husband_cnt}x)")

            if f_nouns:
                female_score += f_nouns * 8
                snippets.append(f"Female role noun in clause ({f_nouns}x)")
            if m_nouns:
                male_score += m_nouns * 8
                snippets.append(f"Male role noun in clause ({m_nouns}x)")

            # E. Hindi inflections if Devanagari present in text
            for h_m in HINDI_MALE_MARKERS:
                if h_m in corpus_text:
                    m_cnt = len(re.findall(rf'\b{escaped_name}\b[^\.\?!;\n]{{0,30}}{h_m}', corpus_text))
                    m_cnt += len(re.findall(rf'{h_m}[^\.\?!;\n]{{0,30}}\b{escaped_name}\b', corpus_text))
                    male_score += m_cnt * 5
            for h_f in HINDI_FEMALE_MARKERS:
                if h_f in corpus_text:
                    f_cnt = len(re.findall(rf'\b{escaped_name}\b[^\.\?!;\n]{{0,30}}{h_f}', corpus_text))
                    f_cnt += len(re.findall(rf'{h_f}[^\.\?!;\n]{{0,30}}\b{escaped_name}\b', corpus_text))
                    female_score += f_cnt * 5

        # Final gender decision
        total_evidence = male_score + female_score
        if total_evidence == 0:
            # Fallback to male with neutral confidence flag
            return GenderEvidence(
                gender="male",
                confidence=0.5,
                male_score=0,
                female_score=0,
                method="fallback_default_male",
            )

        if male_score >= female_score:
            conf = min(0.99, round(0.5 + (male_score / (total_evidence + 1.0)) * 0.5, 3))
            return GenderEvidence(
                gender="male",
                confidence=conf,
                male_score=male_score,
                female_score=female_score,
                evidence_snippets=snippets[:5],
                method="corpus_pronoun_resolution",
            )
        else:
            conf = min(0.99, round(0.5 + (female_score / (total_evidence + 1.0)) * 0.5, 3))
            return GenderEvidence(
                gender="female",
                confidence=conf,
                male_score=male_score,
                female_score=female_score,
                evidence_snippets=snippets[:5],
                method="corpus_pronoun_resolution",
            )

    @classmethod
    def resolve_candidates_batch(
        cls,
        candidates: List[Dict[str, Any]],
        corpus_text: str,
    ) -> List[Dict[str, Any]]:
        """
        Resolves gender for an entire candidate list and updates each dictionary in place.
        """
        updated = []
        for c in candidates:
            c_copy = dict(c)
            name = c_copy.get("english_name") or c_copy.get("name") or c_copy.get("canonical_name", "")
            current_g = (c_copy.get("gender") or "").strip().lower()

            # If gender is missing, empty, or 'neutral', resolve deterministically
            if not current_g or current_g in ("neutral", "unknown", "other"):
                evidence = cls.resolve_gender(
                    name=name,
                    corpus_text=corpus_text,
                    associated_titles=c_copy.get("aliases") or [],
                    aliases=c_copy.get("aliases") or [],
                )
                c_copy["gender"] = evidence.gender
                c_copy["gender_confidence"] = evidence.confidence
            else:
                c_copy["gender"] = current_g

            updated.append(c_copy)
        return updated
