#!/usr/bin/env python3
"""
Unit tests for NumeralAndTokenExpander.
Tests Devanagari numerals, Latin integers, currencies, compound units,
percentages, Roman numerals, and acronym phonetization.
"""

from audiobook_factory.tts.guard.numeral_expander import (
    NumeralAndTokenExpander,
    number_to_hindi_words,
)


def test_number_to_hindi_words_basic():
    assert number_to_hindi_words(0) == "शून्य"
    assert number_to_hindi_words(1) == "एक"
    assert number_to_hindi_words(15) == "पंद्रह"
    assert number_to_hindi_words(25) == "पच्चीस"
    assert number_to_hindi_words(99) == "निन्यानवे"
    assert number_to_hindi_words(100) == "सौ"
    assert number_to_hindi_words(105) == "एक सौ पाँच"
    assert number_to_hindi_words(500) == "पाँच सौ"
    assert number_to_hindi_words(1500) == "एक हज़ार पाँच सौ"
    assert number_to_hindi_words(25000) == "पच्चीस हज़ार"
    assert number_to_hindi_words(100000) == "एक लाख"
    assert number_to_hindi_words(2500000) == "पच्चीस लाख"
    assert number_to_hindi_words(10000000) == "एक करोड़"


def test_expand_currencies():
    text1 = "उसने ₹500 दिए।"
    expanded1, recs1 = NumeralAndTokenExpander.expand_text(text1)
    assert "पाँच सौ रुपये" in expanded1
    assert len(recs1) == 1
    assert recs1[0]["type"] == "currency"

    text2 = "इसकी कीमत $50 है।"
    expanded2, recs2 = NumeralAndTokenExpander.expand_text(text2)
    assert "पचास डॉलर" in expanded2
    assert len(recs2) == 1

    text3 = "कुल रु. २५० लगे।"
    expanded3, _ = NumeralAndTokenExpander.expand_text(text3)
    assert "दो सौ पचास रुपये" in expanded3


def test_expand_compound_units():
    text = "वह 5km दौड़ा और 200g खाना खाया।"
    expanded, recs = NumeralAndTokenExpander.expand_text(text)
    assert "पाँच किलोमीटर" in expanded
    assert "दो सौ ग्राम" in expanded
    assert len(recs) == 2


def test_expand_percentages():
    text = "काम 50% पूरा हो गया है।"
    expanded, recs = NumeralAndTokenExpander.expand_text(text)
    assert "पचास प्रतिशत" in expanded
    assert len(recs) == 1


def test_expand_standalone_numbers():
    text = "कमरे में 42 लोग थे और बाहर ५ लोग खड़े थे।"
    expanded, recs = NumeralAndTokenExpander.expand_text(text)
    assert "बयालीस" in expanded
    assert "पाँच" in expanded


def test_expand_roman_numerals():
    text = "अध्याय IV समाप्त हुआ और भाग IX शुरू हुआ।"
    expanded, recs = NumeralAndTokenExpander.expand_text(text)
    assert "चौथा" in expanded
    assert "नौवाँ" in expanded


def test_expand_acronyms():
    text = "RAW और FBI के अधिकारी पहुँचे।"
    expanded, recs = NumeralAndTokenExpander.expand_text(text)
    assert "आर.ए.डब्ल्यू." in expanded
    assert "एफ़.बी.आई." in expanded
