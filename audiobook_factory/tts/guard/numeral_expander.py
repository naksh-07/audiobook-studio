#!/usr/bin/env python3
"""
Audiobook Factory - Numeral, Currency, Unit, and Acronym Expander.
Provides deterministic phonetization of inline digits, numbers, currencies,
and abbreviations for Hindi / Devanagari TTS synthesis.
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Tuple, Optional


HINDI_NUMERAL_WORDS: Dict[int, str] = {
    0: "शून्य", 1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पाँच",
    6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस",
    11: "ग्यारह", 12: "बारह", 13: "तेरह", 14: "चौदह", 15: "पंद्रह",
    16: "सोलह", 17: "सत्रह", 18: "अठारह", 19: "उन्नीस", 20: "बीस",
    21: "इक्कीस", 22: "बाईस", 23: "तेईस", 24: "चौबीस", 25: "पच्चीस",
    26: "छब्बीस", 27: "सत्ताईस", 28: "अट्ठाईस", 29: "उनतीस", 30: "तीस",
    31: "इकतीस", 32: "बत्तीस", 33: "तैंतीस", 34: "चौंतीस", 35: "पैंतीस",
    36: "छत्तीस", 37: "सैंतीस", 38: "अड़तीस", 39: "उनतालीस", 40: "चालीस",
    41: "इकतालीस", 42: "बयालीस", 43: "तैंतालीस", 44: "चौवालीस", 45: "पैंतालीस",
    46: "छियालीस", 47: "सैंतालीस", 48: "अड़तालीस", 49: "उनचास", 50: "पचास",
    51: "इक्यावन", 52: "बावन", 53: "तिरपन", 54: "चौवन", 55: "पचपन",
    56: "छप्पन", 57: "सत्तावन", 58: "अट्ठावन", 59: "उनसठ", 60: "साठ",
    61: "इकसठ", 62: "बासठ", 63: "तिरसठ", 64: "चौंसठ", 65: "पैंसठ",
    66: "छियासठ", 67: "सरसठ", 68: "अड़सठ", 69: "उनहत्तर", 70: "सत्तर",
    71: "इकहत्तर", 72: "बहत्तर", 73: "तिहत्तर", 74: "चौहत्तर", 75: "पचहत्तर",
    76: "छिहत्तर", 77: "सतहत्तर", 78: "अठहत्तर", 79: "उनासी", 80: "अस्सी",
    81: "इक्यासी", 82: "बयासी", 83: "तिरासी", 84: "चौरासी", 85: "पचासी",
    86: "छियासी", 87: "सत्तासी", 88: "अट्ठासी", 89: "नवासी", 90: "नब्बे",
    91: "इक्यानवे", 92: "बानवे", 93: "तिरानवे", 94: "चौरानवे", 95: "पंचानवे",
    96: "छियानवे", 97: "सत्तानवे", 98: "अट्ठानवे", 99: "निन्यानवे", 100: "सौ",
}


DEVA_DIGIT_MAP: Dict[str, str] = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
}

ROMAN_NUMERALS: Dict[str, str] = {
    "I": "पहला", "II": "दूसरा", "III": "तीसरा", "IV": "चौथा", "V": "पाँचवाँ",
    "VI": "छठा", "VII": "सातवाँ", "VIII": "आठवाँ", "IX": "नौवाँ", "X": "दसवाँ",
    "XI": "ग्यारहवाँ", "XII": "बारहवाँ", "XIII": "तेरहवाँ", "XIV": "चौदहवाँ", "XV": "पंद्रहवाँ",
    "XVI": "सोलहवाँ", "XVII": "सत्रहवाँ", "XVIII": "अठारहवाँ", "XIX": "उन्नीसवाँ", "XX": "बीसवाँ",
}

UNITS_MAP: Dict[str, str] = {
    "km": "किलोमीटर", "किमी": "किलोमीटर", "कि.मी.": "किलोमीटर",
    "m": "मीटर", "मी": "मीटर", "मी.": "मीटर",
    "cm": "सेंटीमीटर", "सेमी": "सेंटीमीटर", "से.मी.": "सेंटीमीटर",
    "mm": "मिलीमीटर", "मिमी": "मिलीमीटर", "मि.मी.": "मिलीमीटर",
    "kg": "किलोग्राम", "किग्रा": "किलोग्राम", "कि.ग्रा.": "किलोग्राम", "किलो": "किलो",
    "g": "ग्राम", "ग्रा": "ग्राम", "ग्रा.": "ग्राम",
    "mg": "मिलीग्राम",
    "l": "लीटर", "ltr": "लीटर", "लीटर": "लीटर",
    "ml": "मिलीलीटर",
    "hr": "घंटे", "hrs": "घंटे", "घंटा": "घंटे", "घंटे": "घंटे",
    "min": "मिनट", "mins": "मिनट", "मिनट": "मिनट",
    "sec": "सेकंड", "secs": "सेकंड", "सेकंड": "सेकंड",
}

LATIN_PHONETICS: Dict[str, str] = {
    'A': 'ए', 'B': 'बी', 'C': 'सी', 'D': 'डी', 'E': 'ई', 'F': 'एफ़',
    'G': 'जी', 'H': 'एच', 'I': 'आई', 'J': 'जे', 'K': 'के', 'L': 'एल',
    'M': 'एम', 'N': 'एन', 'O': 'ओ', 'P': 'पी', 'Q': 'क्यू', 'R': 'आर',
    'S': 'एस', 'T': 'टी', 'U': 'यू', 'V': 'वी', 'W': 'डब्ल्यू', 'X': 'एक्स',
    'Y': 'वाई', 'Z': 'ज़ेड',
}


def number_to_hindi_words(n: int) -> str:
    """
    Converts positive or negative integer up to 999,999,999 into natural spoken Hindi words.
    """
    if n in HINDI_NUMERAL_WORDS:
        return HINDI_NUMERAL_WORDS[n]

    if n < 0:
        return f"माइनस {number_to_hindi_words(-n)}"

    if n < 100:
        tens = (n // 10) * 10
        ones = n % 10
        if tens in HINDI_NUMERAL_WORDS and ones in HINDI_NUMERAL_WORDS:
            return f"{HINDI_NUMERAL_WORDS[tens]} {HINDI_NUMERAL_WORDS[ones]}"
        return str(n)

    if n < 1000:
        hundreds = n // 100
        rem = n % 100
        h_str = f"{number_to_hindi_words(hundreds)} सौ"
        return f"{h_str} {number_to_hindi_words(rem)}" if rem else h_str

    if n < 100000:
        thousands = n // 1000
        rem = n % 1000
        t_str = f"{number_to_hindi_words(thousands)} हज़ार"
        return f"{t_str} {number_to_hindi_words(rem)}" if rem else t_str

    if n < 10000000:
        lakhs = n // 100000
        rem = n % 100000
        l_str = f"{number_to_hindi_words(lakhs)} लाख"
        return f"{l_str} {number_to_hindi_words(rem)}" if rem else l_str

    crores = n // 10000000
    rem = n % 10000000
    c_str = f"{number_to_hindi_words(crores)} करोड़"
    return f"{c_str} {number_to_hindi_words(rem)}" if rem else c_str


class NumeralAndTokenExpander:
    """
    Deterministic expansion of numerals, currencies, units, percentages,
    Roman chapter numerals, and uppercase acronyms.
    """

    @classmethod
    def expand_text(cls, text: str, language: str = "hi-IN") -> Tuple[str, List[Dict[str, Any]]]:
        """
        Scans and expands all numbers, currencies, units, and acronyms in text.
        Returns (expanded_text, list_of_expansion_records).
        """
        if not text or not text.strip():
            return text, []

        expansions: List[Dict[str, Any]] = []
        working = text

        # 1. Currencies: $500, ₹500, Rs. 500, Rs 500
        def _repl_currency(m: re.Match) -> str:
            sym = m.group(1)
            raw_digits = m.group(2)
            digits = cls._normalize_digits_to_ascii(raw_digits)
            if digits.isdigit():
                val = int(digits)
                words = number_to_hindi_words(val)
                curr_name = "डॉलर" if "$" in sym else "रुपये"
                res = f"{words} {curr_name}"
                expansions.append({"original": m.group(0), "expanded": res, "type": "currency"})
                return res
            return m.group(0)

        working = re.sub(r"([₹\$]|Rs\.?|रु\.?)\s*([0-9\u0966-\u096F]+)", _repl_currency, working, flags=re.IGNORECASE)

        # 2. Compound Numbers with Units: 5km, 10 kg, 20किमी, 500g
        def _repl_units(m: re.Match) -> str:
            raw_digits = m.group(1)
            unit_raw = m.group(2).strip().lower()
            digits = cls._normalize_digits_to_ascii(raw_digits)
            if digits.isdigit() and unit_raw in UNITS_MAP:
                val = int(digits)
                words = number_to_hindi_words(val)
                u_word = UNITS_MAP[unit_raw]
                res = f"{words} {u_word}"
                expansions.append({"original": m.group(0), "expanded": res, "type": "unit"})
                return res
            return m.group(0)

        working = re.sub(
            r"\b([0-9\u0966-\u096F]+)\s*([a-zA-Z\u0900-\u097F\.]+)\b",
            _repl_units,
            working,
        )

        # 3. Percentages: 50%, ५०%
        def _repl_percent(m: re.Match) -> str:
            raw_digits = m.group(1)
            digits = cls._normalize_digits_to_ascii(raw_digits)
            if digits.isdigit():
                val = int(digits)
                words = number_to_hindi_words(val)
                res = f"{words} प्रतिशत"
                expansions.append({"original": m.group(0), "expanded": res, "type": "percentage"})
                return res
            return m.group(0)

        working = re.sub(r"\b([0-9\u0966-\u096F]+)%", _repl_percent, working)

        # 4. Standalone Devanagari & Latin Integers: 500, ५००
        def _repl_standalone_number(m: re.Match) -> str:
            raw_digits = m.group(1)
            digits = cls._normalize_digits_to_ascii(raw_digits)
            if digits.isdigit():
                val = int(digits)
                if val <= 999999999:
                    words = number_to_hindi_words(val)
                    expansions.append({"original": m.group(0), "expanded": words, "type": "number"})
                    return words
            return m.group(0)

        working = re.sub(r"(?<![\w\u0900-\u097F])([0-9\u0966-\u096F]+)(?![\w\u0900-\u097F])", _repl_standalone_number, working)

        # 5. Standalone Roman Section Numerals: Chapter IV -> चौथा
        def _repl_roman_numeral(m: re.Match) -> str:
            tok = m.group(1).upper()
            if tok in ROMAN_NUMERALS:
                res = ROMAN_NUMERALS[tok]
                expansions.append({"original": m.group(0), "expanded": res, "type": "roman_numeral"})
                return res
            return m.group(0)

        working = re.sub(r"\b([IVXLCDM]{1,6})\b", _repl_roman_numeral, working)

        # 6. Standalone Uppercase Acronyms: FBI, CIA, CID, ISRO, RAW
        def _repl_acronym(m: re.Match) -> str:
            tok = m.group(1)
            if len(tok) >= 2 and tok.isupper() and tok.isalpha():
                # Avoid expanding English words like "HE", "WE", "IF", "IN", "IS"
                common_english = {"HE", "SHE", "WE", "THEY", "IT", "IN", "ON", "AT", "TO", "FOR", "OF", "AND", "OR", "IF", "AS", "IS", "AM", "ARE", "WAS", "WERE"}
                if tok in common_english:
                    return m.group(0)
                letters = [LATIN_PHONETICS.get(c, c) for c in tok]
                res = ".".join(letters) + "."
                expansions.append({"original": m.group(0), "expanded": res, "type": "acronym"})
                return res
            return m.group(0)

        working = re.sub(r"\b([A-Z]{2,6})\b", _repl_acronym, working)

        return working, expansions

    @staticmethod
    def _normalize_digits_to_ascii(digits_str: str) -> str:
        """Converts Devanagari digits (०-९) to ASCII (0-9)."""
        res = []
        for c in digits_str:
            if c in DEVA_DIGIT_MAP:
                res.append(DEVA_DIGIT_MAP[c])
            else:
                res.append(c)
        return "".join(res)
