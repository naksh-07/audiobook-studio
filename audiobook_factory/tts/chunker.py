#!/usr/bin/env python3
"""
Audiobook Factory - 4-Tier Semantic Prose Chunker.
Splits long-form literary text into natural acoustic chunks using a strict hierarchy:
Level 1: Scene Breaks (---, ***, # headers)
Level 2: Paragraph Breaks (\n\n) -> Target 80-160 words
Level 3: Sentence Boundaries (।, ., ?, !) -> Target 30-75 words
Level 4: Clause Boundaries (,, —, ;) -> Emergency fallback for >45 words
Level 5: Mid-word slicing is strictly prohibited.
"""

from __future__ import annotations
import re
import uuid
import hashlib
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ChunkHierarchyLevel(str, Enum):
    SCENE = "scene"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    CLAUSE = "clause"


class SemanticChunk(BaseModel):
    """Strongly-typed chunk container representing an atomic TTS speech unit."""
    model_config = ConfigDict(frozen=True)

    chunk_uid: str
    text: str
    spoken_text: str
    level: ChunkHierarchyLevel
    word_count: int
    char_count: int
    suggested_pause_before_ms: int = 0
    suggested_pause_after_ms: int = 350
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticProseChunker:
    """
    Splits long-form text into balanced semantic units while preserving
    literary pacing and eliminating autoregressive TTS rate drift.
    """

    SCENE_DELIMITERS = re.compile(r"(?:\n\s*[-*_]{3,}\s*\n|\n\s*#{1,3}\s+[^\n]+\n)", re.UNICODE)
    PARAGRAPH_DELIMITERS = re.compile(r"\n\s*\n", re.UNICODE)
    SENTENCE_DELIMITERS = re.compile(r"(?<=[।॥\.!\?])\s+", re.UNICODE)
    CLAUSE_DELIMITERS = re.compile(r"(?<=[,;—])\s+", re.UNICODE)

    @classmethod
    def chunk_prose(
        cls,
        text: str,
        target_words: int = 120,
        max_words: int = 180,
        min_words: int = 40,
    ) -> List[SemanticChunk]:
        """
        Partitions text into SemanticChunk units adhering to the 4-tier hierarchy.
        """
        if not text or not text.strip():
            return []

        raw_text = text.strip()
        chunks: List[SemanticChunk] = []

        # Level 1: Scene Slicing
        scenes = cls._split_scenes(raw_text)

        for scene_idx, scene_text in enumerate(scenes, start=1):
            scene_chunks = cls._chunk_scene(
                scene_text=scene_text,
                scene_num=scene_idx,
                target_words=target_words,
                max_words=max_words,
                min_words=min_words,
            )
            chunks.extend(scene_chunks)

        return chunks

    @classmethod
    def _split_scenes(cls, text: str) -> List[str]:
        """Splits text on scene breaks or major markdown dividers."""
        scenes = cls.SCENE_DELIMITERS.split(text)
        return [s.strip() for s in scenes if s.strip()]

    @classmethod
    def _chunk_scene(
        cls,
        scene_text: str,
        scene_num: int,
        target_words: int,
        max_words: int,
        min_words: int,
    ) -> List[SemanticChunk]:
        """Chunks a single scene using Paragraph -> Sentence -> Clause hierarchy."""
        paragraphs = cls.PARAGRAPH_DELIMITERS.split(scene_text)
        scene_chunks: List[SemanticChunk] = []

        current_sentences: List[str] = []
        current_word_count = 0
        chunk_idx = 1

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_words = len(para.split())

            # If paragraph fits naturally into target window
            if para_words <= max_words:
                if current_word_count + para_words > max_words and current_sentences:
                    # Flush accumulated sentences
                    scene_chunks.append(
                        cls._build_chunk(
                            sentences=current_sentences,
                            level=ChunkHierarchyLevel.PARAGRAPH,
                            scene_num=scene_num,
                            chunk_idx=chunk_idx,
                        )
                    )
                    chunk_idx += 1
                    current_sentences = [para]
                    current_word_count = para_words
                else:
                    current_sentences.append(para)
                    current_word_count += para_words

                if current_word_count >= target_words:
                    scene_chunks.append(
                        cls._build_chunk(
                            sentences=current_sentences,
                            level=ChunkHierarchyLevel.PARAGRAPH,
                            scene_num=scene_num,
                            chunk_idx=chunk_idx,
                        )
                    )
                    chunk_idx += 1
                    current_sentences = []
                    current_word_count = 0
            else:
                # Paragraph is too long (> max_words) -> Level 3: Sentence splitting
                sentences = cls.SENTENCE_DELIMITERS.split(para)
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue

                    sent_words = len(sent.split())

                    # If single sentence itself is giant (> max_words * 0.75) -> Level 4: Clause splitting
                    if sent_words > int(max_words * 0.75):
                        clauses = cls.CLAUSE_DELIMITERS.split(sent)
                        for clause in clauses:
                            clause = clause.strip()
                            if not clause:
                                continue
                            c_words = len(clause.split())
                            if current_word_count + c_words > max_words and current_sentences:
                                scene_chunks.append(
                                    cls._build_chunk(
                                        sentences=current_sentences,
                                        level=ChunkHierarchyLevel.CLAUSE,
                                        scene_num=scene_num,
                                        chunk_idx=chunk_idx,
                                    )
                                )
                                chunk_idx += 1
                                current_sentences = [clause]
                                current_word_count = c_words
                            else:
                                current_sentences.append(clause)
                                current_word_count += c_words
                    else:
                        if current_word_count + sent_words > max_words and current_sentences:
                            scene_chunks.append(
                                cls._build_chunk(
                                    sentences=current_sentences,
                                    level=ChunkHierarchyLevel.SENTENCE,
                                    scene_num=scene_num,
                                    chunk_idx=chunk_idx,
                                )
                            )
                            chunk_idx += 1
                            current_sentences = [sent]
                            current_word_count = sent_words
                        else:
                            current_sentences.append(sent)
                            current_word_count += sent_words

                    if current_word_count >= target_words:
                        scene_chunks.append(
                            cls._build_chunk(
                                sentences=current_sentences,
                                level=ChunkHierarchyLevel.SENTENCE,
                                scene_num=scene_num,
                                chunk_idx=chunk_idx,
                            )
                        )
                        chunk_idx += 1
                        current_sentences = []
                        current_word_count = 0

        if current_sentences:
            scene_chunks.append(
                cls._build_chunk(
                    sentences=current_sentences,
                    level=ChunkHierarchyLevel.PARAGRAPH,
                    scene_num=scene_num,
                    chunk_idx=chunk_idx,
                )
            )

        return scene_chunks

    @classmethod
    def _build_chunk(
        cls,
        sentences: List[str],
        level: ChunkHierarchyLevel,
        scene_num: int,
        chunk_idx: int,
    ) -> SemanticChunk:
        """Constructs an immutable SemanticChunk object with appropriate pause hints."""
        combined_text = " ".join(sentences).strip()
        words = combined_text.split()
        word_cnt = len(words)

        # Determine pause duration based on hierarchy level
        pause_before = 0
        if level == ChunkHierarchyLevel.SCENE:
            pause_after = 800
        elif level == ChunkHierarchyLevel.PARAGRAPH:
            pause_after = 500
        elif level == ChunkHierarchyLevel.SENTENCE:
            pause_after = 350
        else:
            pause_after = 200

        text_hash = hashlib.md5(combined_text.encode("utf-8")).hexdigest()[:6]
        uid = f"chunk_s{scene_num:02d}_{chunk_idx:04d}_{text_hash}"

        return SemanticChunk(
            chunk_uid=uid,
            text=combined_text,
            spoken_text=combined_text,
            level=level,
            word_count=word_cnt,
            char_count=len(combined_text),
            suggested_pause_before_ms=pause_before,
            suggested_pause_after_ms=pause_after,
            metadata={"scene_num": scene_num, "chunk_index": chunk_idx},
        )
