#!/usr/bin/env python3
"""
Audiobook Factory - Packaging: Chapter Metadata & Atom Formatter.
Generates QuickTime/MP4 3GPP and FFMETADATA1 chapter marker tracks, show notes,
and ID3/MP4 atom metadata for Audiobook (.m4b) and Podcast (.m4a) containers.
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from audiobook_factory.podcast.contracts import PodcastEpisodePlan


def escape_ffmetadata(val: Any) -> str:
    """Escape special characters (=, ;, #, \\) for FFMETADATA1 specification."""
    s = str(val or "")
    s = s.replace("\\", "\\\\")
    for char in ("=", ";", "#"):
        s = s.replace(char, f"\\{char}")
    return s.replace("\n", " ").strip()


class ChapterMetadataGenerator:
    """
    Generates industry-standard FFMETADATA1 tracks with millisecond precision
    for chapter marks in audiobooks and segment marks in podcasts.
    """

    @classmethod
    def generate_audiobook_metadata(
        cls,
        book_title: str,
        author: str,
        chapter_durations: List[Dict[str, Any]],
        narrator: str = "Studio AI Multi-Cast",
        genre: str = "Audiobook",
        year: str = "2026",
    ) -> str:
        """
        Builds FFMETADATA1 text for chaptered M4B audiobook.
        """
        t = escape_ffmetadata(book_title)
        a = escape_ffmetadata(author)
        n = escape_ffmetadata(narrator)
        lines = [
            ";FFMETADATA1",
            f"title={t}",
            f"artist={a}",
            f"album_artist={a}",
            f"composer={n}",
            f"album={t}",
            f"genre={genre}",
            f"date={year}",
            f"comment=Produced by Audiobook Studio (Audible EBU R128 Compliant)",
        ]

        current_ms = 0
        for ch in chapter_durations:
            dur_ms = ch.get("duration_ms", 0)
            ch_num = ch.get("chapter_num", 1)
            ch_title = escape_ffmetadata(ch.get("title", f"Chapter {ch_num}"))
            start_ms = current_ms
            end_ms = current_ms + dur_ms
            current_ms = end_ms

            lines.extend([
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={start_ms}",
                f"END={end_ms}",
                f"title={ch_title}",
            ])

        return "\n".join(lines) + "\n"

    @classmethod
    def generate_podcast_metadata(
        cls,
        episode_plan: PodcastEpisodePlan,
        show_title: str,
        segment_durations: Optional[List[Dict[str, Any]]] = None,
        year: str = "2026",
    ) -> str:
        """
        Builds FFMETADATA1 text with section chapters (Cold Open, Intro, Scene Deep-Dive, Banter, Outro)
        and embedded show notes for Podcast M4A.
        """
        hosts = list(episode_plan.hosts.values())
        host_names = " & ".join(h.name for h in hosts) if hosts else "Studio Hosts"
        ep_title = escape_ffmetadata(episode_plan.episode_title)
        s_title = escape_ffmetadata(show_title)
        show_notes = escape_ffmetadata(
            f"Episode Summary: {episode_plan.hook_statement or 'An in-depth dramatic narrative breakdown.'} "
            f"Featuring: {host_names}. Target Loudness: -16.0 LUFS EBU R128."
        )

        lines = [
            ";FFMETADATA1",
            f"title={ep_title}",
            f"artist={host_names}",
            f"album_artist={host_names}",
            f"album={s_title}",
            "genre=Podcast",
            f"date={year}",
            f"description={show_notes}",
            f"comment={show_notes}",
        ]

        if segment_durations:
            current_ms = 0
            for seg in segment_durations:
                dur_ms = seg.get("duration_ms", 0)
                sec_name = seg.get("section_type", "Segment").replace("_", " ").title()
                start_ms = current_ms
                end_ms = current_ms + dur_ms
                current_ms = end_ms

                lines.extend([
                    "[CHAPTER]",
                    "TIMEBASE=1/1000",
                    f"START={start_ms}",
                    f"END={end_ms}",
                    f"title={sec_name}",
                ])

        return "\n".join(lines) + "\n"
