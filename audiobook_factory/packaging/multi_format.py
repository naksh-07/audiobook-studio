#!/usr/bin/env python3
"""
Audiobook Factory - Packaging: Unified Multi-Format Packaging Engine.
Coordinates packaging for Audiobooks (.m4b) and Podcasts (.m4a), injecting
chapter markers, cover art, and format-specific metadata atoms.
"""

from __future__ import annotations
import os
import re
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal

from audiobook_factory.packager import package_m4b_audiobook, get_audio_duration_ms
from audiobook_factory.packaging.chapter_metadata import ChapterMetadataGenerator
from audiobook_factory.podcast.contracts import PodcastEpisodePlan
from audiobook_factory.tts.constants import get_ffmpeg

logger = logging.getLogger("AudiobookFactory")


def package_podcast_episodes(
    project_dir: Path,
    cover_image: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> List[Path]:
    """
    Packages all podcast episodes in project_dir/podcasts into chaptered M4A containers
    with embedded cover art, show notes, and section markers.
    """
    project_dir = Path(project_dir).resolve()
    podcasts_dir = project_dir / "podcasts"
    if not podcasts_dir.exists():
        raise FileNotFoundError(f"Podcasts directory missing: {podcasts_dir}")

    dest_dir = Path(output_dir).resolve() if output_dir else (project_dir / "packaged_podcasts")
    dest_dir.mkdir(parents=True, exist_ok=True)

    plan_files = sorted(podcasts_dir.glob("*_podcast_plan.json"))
    if not plan_files:
        raise FileNotFoundError(f"No podcast episode plans found in {podcasts_dir}")

    ffmpeg = get_ffmpeg()
    packaged_files: List[Path] = []
    book_title = project_dir.name.replace("_", " ").title()

    # Discover cover image if not explicitly provided
    eff_cover = cover_image
    if not eff_cover:
        for ext in (".jpg", ".jpeg", ".png"):
            cand = project_dir / f"cover{ext}"
            if cand.exists():
                eff_cover = cand
                break

    for pf in plan_files:
        plan = PodcastEpisodePlan.load_from_file(pf)
        chap_stem = pf.stem.replace("_podcast_plan", "").replace("_plan", "")

        # Look for podcast master audio (.wav or .m4a)
        master_candidates = [
            podcasts_dir / f"{chap_stem}_podcast_master.wav",
            podcasts_dir / f"{chap_stem}_podcast.m4a",
            podcasts_dir / f"{chap_stem}_master.wav",
        ]
        master_audio = next((mc for mc in master_candidates if mc.exists()), None)
        if not master_audio:
            logger.warning(f"  [!] Master audio missing for podcast plan {pf.name}, skipping packaging.")
            continue

        # Generate FFMETADATA file with section chapters
        ffmeta_text = ChapterMetadataGenerator.generate_podcast_metadata(
            episode_plan=plan,
            show_title=book_title,
        )
        ffmeta_path = podcasts_dir / f"{chap_stem}_ffmetadata.txt"
        ffmeta_path.write_text(ffmeta_text, encoding="utf-8")

        out_m4a = dest_dir / f"{chap_stem}_podcast.m4a"

        cmd = [
            ffmpeg, "-y",
            "-i", str(master_audio),
            "-i", str(ffmeta_path),
        ]

        if eff_cover and eff_cover.exists():
            cmd.extend([
                "-i", str(eff_cover),
                "-map", "0:a",
                "-map", "2:v",
                "-c:v", "mjpeg",
                "-disposition:v:0", "attached_pic",
            ])
        else:
            cmd.extend([
                "-map", "0:a",
            ])

        cmd.extend([
            "-map_metadata", "1",
            "-c:a", "aac",
            "-b:a", "192k",
            str(out_m4a),
        ])

        logger.info(f"[*] Packaging Podcast Episode: {out_m4a.name}...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300.0)
        if res.returncode != 0:
            logger.error(f"  [!] FFmpeg podcast packaging failed: {res.stderr[:200]}")
            raise RuntimeError(f"Podcast packaging failed for {out_m4a.name}: {res.stderr[:200]}")

        logger.info(f"[+] Packaged Podcast Episode -> {out_m4a.name}")
        packaged_files.append(out_m4a)

    return packaged_files


def package_project(
    project_dir: Path,
    format_mode: Literal["audiobook", "podcast", "both"] = "audiobook",
    cover_image: Optional[Path] = None,
    enforce_gate6: bool = False,
) -> Dict[str, Any]:
    """
    Unified entrypoint to package Audiobook (.m4b), Podcast (.m4a), or Both.
    """
    project_dir = Path(project_dir).resolve()
    results: Dict[str, Any] = {"format_mode": format_mode, "artifacts": {}}

    if format_mode in ("audiobook", "both"):
        logger.info(f"[*] Packaging Audiobook M4B for {project_dir.name}...")
        m4b_path = package_m4b_audiobook(
            project_dir=project_dir,
            cover_image=cover_image,
            enforce_gate6=enforce_gate6,
        )
        results["artifacts"]["audiobook_m4b"] = str(m4b_path)

    if format_mode in ("podcast", "both"):
        logger.info(f"[*] Packaging Podcast Episodes M4A for {project_dir.name}...")
        m4a_paths = package_podcast_episodes(
            project_dir=project_dir,
            cover_image=cover_image,
        )
        results["artifacts"]["podcast_episodes"] = [str(p) for p in m4a_paths]

    return results
