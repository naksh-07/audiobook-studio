#!/usr/bin/env python3
"""
Audiobook Factory - Room 3.5: Phonetic Indic & Devanagari Transliteration Engine.
Provides deterministic, authentic phonetic Devanagari transliteration for character names,
aliases, and literary titles, with zero unmetered network calls and zero forbidden imports.
"""

from __future__ import annotations
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def is_devanagari(text: str) -> bool:
    """Checks if a string contains any Devanagari script characters."""
    if not text:
        return False
    return any('\u0900' <= c <= '\u097f' for c in text)


_DEV_CONNECTORS: Set[str] = {
    "ओफ़", "ऑफ़", "का", "की", "के", "से", "में", "और", "थ्री",
    "three", "of", "the", "de", "van", "von",
}

_GENERIC_TITLES: Set[str] = {
    "lord", "sir", "master", "lady", "king", "queen", "baron", "duke",
    "captain", "alderman", "doctor", "dr", "father",
    "brother", "sister", "dame", "count", "duchess", "prince", "princess",
    "elder", "general", "chief", "officer", "inspector", "innkeeper",
    "commander", "emperor", "empress", "mr", "mrs", "miss",
    "chancellor", "leader", "mistress",
    # Hindi honorifics & titles
    "महाराज", "राजा", "रानी", "श्रीमान", "स्वामी", "प्रभु", "ठाकुर",
    "मालिक", "कप्तान", "मुखिया", "चौधरी", "सर", "लॉर्ड", "मास्टर",
    "लोर्ड", "किन्ग", "सिर", "मास्टेर",
    "चान्सेल्लोर", "लीडेर", "मिस्ट्रेस्स",
    # Generic occupations, titles, numbers, and descriptors
    "man", "मान", "fat", "फ़ाट", "फाट", "yellow", "येल्लोव", "येलो",
    "cobbler", "कोब्ब्लेर", "कॉबलर",
    "warrior", "वार्रिोर", "वॉरियर", "वारियर",
    "golden", "गोल्डेन", "गोल्डन",
    "little", "लिट्ट्ले", "लिटिल", "duke", "डुके", "ड्यूक", "baron", "बारोन", "बैरन",
    "queen", "क्वीन", "miss", "मिस्स", "मिस", "mrs", "म्र्स", "मिसेज",
}

_FORBIDDEN_PHRASES: Set[str] = {
    "of the", "ओफ़ थे", "ओफ थे", "ऑफ़ द", "ऑफ द",
    "लीडेर ओफ़", "लीडेर ओफ", "लीडेर ओफ़ थे", "लीडेर ओफ थे",
    "leader of", "leader of the",
}

_CONNECTOR_EDGE_TOKENS: Set[str] = {
    "of", "the", "ओफ़", "ओफ", "ऑफ़", "ऑफ", "थे", "द", "का", "की", "के", "से",
    "de", "van", "von",
}


# Canonical Phonetic Devanagari Vocabulary for universal literary terms
DEV_PHONETIC_VOCAB: Dict[str, str] = {
    # Universal narrator and production anchors
    "narrator": "सूत्रधार",
    "narration": "सूत्रधार",
    "mayor": "मेयर",
    "town mayor": "टाउन मेयर",
}


def rule_based_latin_to_devanagari(word: str) -> str:
    """
    Phonetically transliterates an English/Latin word into Devanagari script.
    Follows standard Indic phonetic mapping rules with consonant conjuncts and matras.
    """
    w = word.strip().lower()
    if not w:
        return ""
    if is_devanagari(w):
        return word.strip()
    if w in DEV_PHONETIC_VOCAB:
        return DEV_PHONETIC_VOCAB[w]

    # Normalize accented characters using NFKD so accented vowels (like é, á, í, ó, ú)
    # become clean ASCII e, a, i, o, u instead of corrupting Devanagari output with Mojibake like 'वéा'
    w_norm = unicodedata.normalize("NFKD", w).encode("ascii", "ignore").decode("ascii")
    if w_norm in DEV_PHONETIC_VOCAB:
        return DEV_PHONETIC_VOCAB[w_norm]
    w = w_norm

    vowels = {"a", "e", "i", "o", "u", "y"}

    initial_vowels = {
        "aa": "आ", "a": "अ", "ai": "ऐ", "au": "औ", "ay": "ए",
        "ee": "ई", "ea": "ई", "e": "ए", "ey": "ए", "ii": "ई",
        "i": "इ", "oo": "ऊ", "ou": "औ", "oa": "ओ", "o": "ओ", "u": "उ"
    }
    matras = {
        "aa": "ा", "a": "ा", "ai": "ै", "au": "ौ", "ay": "े",
        "ee": "ी", "ea": "ी", "e": "े", "ey": "े", "ii": "ी",
        "i": "ि", "oo": "ू", "ou": "ौ", "oa": "ो", "o": "ो", "u": "ु"
    }

    consonants = {
        "ch": "च", "sh": "श", "th": "थ", "ph": "फ़", "kh": "ख",
        "gh": "घ", "bh": "भ", "dh": "ध", "zh": "झ़", "ck": "क",
        "qu": "क्व", "wh": "व",
        "b": "ब", "c": "क", "d": "ड", "f": "फ़", "g": "ग",
        "h": "ह", "j": "ज", "k": "क", "l": "ल", "m": "म",
        "n": "न", "p": "प", "q": "क", "r": "र", "s": "स",
        "t": "ट", "v": "व", "w": "व", "x": "क्स", "y": "य", "z": "ज़"
    }

    res: List[str] = []
    i = 0
    n = len(w)
    is_initial = True

    while i < n:
        # Check vowel chunks
        matched = False
        for l in [2, 1]:
            if i + l <= n:
                chunk = w[i:i+l]
                if is_initial and chunk in initial_vowels:
                    res.append(initial_vowels[chunk])
                    i += l
                    is_initial = False
                    matched = True
                    break
                elif not is_initial and chunk in matras:
                    res.append(matras[chunk])
                    i += l
                    matched = True
                    break
        if matched:
            continue

        # Soft c before e, i, y -> स
        if w[i] == "c" and (i + 1 < n and w[i+1] in ("e", "i", "y")) and not (i + 1 < n and w[i+1] == "h"):
            cons = "स"
            c_len = 1
        elif i + 2 <= n and w[i:i+2] in consonants:
            cons = consonants[w[i:i+2]]
            c_len = 2
        elif w[i] in consonants:
            cons = consonants[w[i]]
            c_len = 1
        else:
            res.append(w[i])
            i += 1
            is_initial = False
            continue

        i += c_len
        is_initial = False

        # If followed by another consonant, add halant for consonant conjunct
        if i < n and w[i] not in vowels and w[i] in consonants and (i + 1 < n or w[i] != "h"):
            res.append(cons + "्")
        else:
            res.append(cons)

    return "".join(res)


def transliterate_to_devanagari(text: str, project_dir: Optional[Path] = None) -> str:
    """
    Transliterates a full character name or phrase from English/Latin to authentic Devanagari.
    Checks project lexicon, canonical phonetic vocabulary, and rule-based transliterator.
    """
    if not text:
        return ""
    clean = text.strip()
    if is_devanagari(clean):
        return clean

    clean_lower = clean.lower()

    # 1. Direct vocabulary lookup (with accent normalization fallback)
    if clean_lower in DEV_PHONETIC_VOCAB:
        return DEV_PHONETIC_VOCAB[clean_lower]
    clean_norm = unicodedata.normalize("NFKD", clean_lower).encode("ascii", "ignore").decode("ascii")
    if clean_norm in DEV_PHONETIC_VOCAB:
        return DEV_PHONETIC_VOCAB[clean_norm]

    # 2. Check project pronunciation_lexicon.json if project_dir provided
    if project_dir:
        p_dir = Path(project_dir).resolve()
        lex_path = p_dir / "pronunciation_lexicon.json"
        if lex_path.exists():
            try:
                with open(lex_path, "r", encoding="utf-8") as f:
                    ldata = json.load(f)
                chars = ldata.get("characters", {})
                if clean in chars and is_devanagari(chars[clean]):
                    return chars[clean]
                if clean_lower in {k.lower(): v for k, v in chars.items() if is_devanagari(v)}:
                    return next(v for k, v in chars.items() if k.lower() == clean_lower and is_devanagari(v))
            except Exception:
                pass

    # 3. Word-by-word transliteration
    words = re.split(r"(\s+)", clean)
    out_words = []
    for word in words:
        if not word.strip():
            out_words.append(word)
            continue
        w_low = word.lower()
        if w_low in DEV_PHONETIC_VOCAB:
            out_words.append(DEV_PHONETIC_VOCAB[w_low])
        else:
            out_words.append(rule_based_latin_to_devanagari(word))

    return "".join(out_words)


def derive_devanagari_name(
    english_name: str,
    project_dir: Optional[Path] = None,
    aliases: Optional[List[str]] = None,
) -> Tuple[str, List[str]]:
    """
    Derives primary Devanagari display name and authentic Devanagari aliases for a character.
    Guarantees every character lock has authentic Devanagari in display_name_hi and aliases.
    """
    eng_clean = (english_name or "").strip()
    eng_lower = eng_clean.lower()
    primary_dev = transliterate_to_devanagari(eng_clean, project_dir=project_dir)

    dev_aliases: Set[str] = set()
    if primary_dev and is_devanagari(primary_dev):
        dev_aliases.add(primary_dev)

    # Transliterate compound components if multi-word name
    if " " in eng_clean:
        for part in eng_clean.split():
            part_dev = transliterate_to_devanagari(part, project_dir=project_dir)
            if is_devanagari(part_dev):
                dev_aliases.add(part_dev)

    # Also transliterate existing aliases
    if aliases:
        for a in aliases:
            if not a:
                continue
            a_str = str(a).strip()
            if is_devanagari(a_str):
                dev_aliases.add(a_str)
            else:
                d_trans = transliterate_to_devanagari(a_str, project_dir=project_dir)
                if is_devanagari(d_trans):
                    dev_aliases.add(d_trans)

    # Purge any standalone connector, generic title, short token (<3 chars), or forbidden common words
    banned_standalone_dev = _DEV_CONNECTORS | _GENERIC_TITLES

    def _is_invalid_alias(alias_str: str) -> bool:
        if not alias_str:
            return True
        a_strip = alias_str.strip()
        a_low = a_strip.lower()
        if a_low in banned_standalone_dev or a_strip in banned_standalone_dev:
            return True
        if a_low in _FORBIDDEN_PHRASES or a_strip in _FORBIDDEN_PHRASES:
            return True
        tokens = [t.strip().lower() for t in a_strip.split() if t.strip()]
        if not tokens:
            return True
        # Reject any alias that starts or ends with a connector (of, the, ओफ़, थे, का, की, के, से, etc.)
        if tokens[0] in _CONNECTOR_EDGE_TOKENS or tokens[-1] in _CONNECTOR_EDGE_TOKENS:
            return True
        return False

    # For compound Devanagari names, split by space, add individual name tokens to dev_aliases
    current_dev_strings = set(dev_aliases)
    if primary_dev and is_devanagari(primary_dev):
        current_dev_strings.add(primary_dev)

    for dev_str in list(current_dev_strings):
        if is_devanagari(dev_str):
            tokens = [t.strip() for t in dev_str.split() if t.strip()]
            # Only full names (exactly 2 tokens) should have name tokens extracted
            if len(tokens) == 2:
                for tok in tokens:
                    if _is_invalid_alias(tok) or len(tok) < 3:
                        continue
                    dev_aliases.add(tok)

    cleaned_dev_aliases = {
        da for da in dev_aliases
        if not _is_invalid_alias(da)
        and len(da) >= 3
    }
    return primary_dev, sorted(list(cleaned_dev_aliases))
