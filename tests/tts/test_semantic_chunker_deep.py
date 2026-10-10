#!/usr/bin/env python3
"""
Deep unit tests for SemanticProseChunker.
Tests 4-tier hierarchy splitting (Scene -> Paragraph -> Sentence -> Clause),
large prose streams, and mid-word cut prevention.
"""

import pytest
from audiobook_factory.tts.chunker import (
    SemanticProseChunker,
    SemanticChunk,
    ChunkHierarchyLevel,
)


def test_chunker_scene_level_splitting():
    prose = (
        "पहला दृश्य शुरू होता है। राजा अपने महल में बैठा था।\n"
        "---\n"
        "दूसरा दृश्य जंगल में शुरू होता है। सिपाही चारों तरफ पहरा दे रहे थे।"
    )
    chunks = SemanticProseChunker.chunk_prose(prose, target_words=100)
    assert len(chunks) == 2
    assert "पहला दृश्य" in chunks[0].text
    assert "दूसरा दृश्य" in chunks[1].text


def test_chunker_paragraph_level_splitting():
    p1 = "यह पहला पैराग्राफ है जिसमें कुछ सामान्य विवरण दिए गए हैं। " * 5  # ~50 words
    p2 = "यह दूसरा पैराग्राफ है जिसमें कुछ और जानकारी जोड़ी गई है। " * 5   # ~50 words
    full_text = f"{p1}\n\n{p2}"

    chunks = SemanticProseChunker.chunk_prose(full_text, target_words=50, max_words=80)
    assert len(chunks) == 2
    assert chunks[0].level == ChunkHierarchyLevel.PARAGRAPH
    assert chunks[1].level == ChunkHierarchyLevel.PARAGRAPH


def test_chunker_sentence_level_splitting_on_long_paragraphs():
    # Long paragraph without \n\n but with multiple Hindi sentences (।)
    sentences = [f"यह वाक्य क्रमांक {i} है जो कहानी को आगे बढ़ाता है।" for i in range(1, 20)]
    long_para = " ".join(sentences)

    chunks = SemanticProseChunker.chunk_prose(long_para, target_words=30, max_words=50)
    assert len(chunks) >= 3
    for c in chunks:
        assert c.word_count <= 60
        # Verify no mid-sentence cuts where punctuation is dropped
        assert any(c.text.endswith(punct) for punct in ["।", "॥", ".", "!", "?"])


def test_chunker_large_5000_word_prose_stream():
    # Generate 5,000 words of synthetic Hindi prose
    base_sentence = "विक्रम ने तलवार उठाई और आगे बढ़ा क्योंकि समय बहुत कम बचा था। "
    large_prose = "\n\n".join([base_sentence * 10 for _ in range(45)])  # ~5,400 words

    chunks = SemanticProseChunker.chunk_prose(large_prose, target_words=120, max_words=180)
    assert len(chunks) >= 30

    total_words = sum(c.word_count for c in chunks)
    assert total_words > 4500

    # Ensure every chunk is within safe bounds
    for c in chunks:
        assert c.word_count >= 10
        assert c.word_count <= 220
        assert len(c.text.strip()) > 0
