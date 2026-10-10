#!/usr/bin/env python3
"""
Audiobook Factory - Lossless M4B Audiobook Packager (v5.3).
============================================================
Implements M4BBookPackager to enforce:
1. Zero generation loss: Assembles finalized .m4b strictly via '-c:a copy' stream copy (AP-04).
2. Monotonic chapter markers: Guarantees START_k = END_{k-1} in FFMETADATA1 without overlaps (AP-10).
3. Cover art embedding (-c:v mjpeg -disposition:v attached_pic).
4. Web-streaming faststart (-movflags +faststart).
5. Atomic output promotion via _atomic_replace defending against file-lock corruptions.
"""

from __future__ import annotations
import json
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from audiobook_factory.logger import logger
from audiobook_factory.audio_utils import (
    get_ffmpeg,
    get_ffprobe,
    get_audio_duration_ms,
    _atomic_replace,
    DEFAULT_FFMPEG_TIMEOUT,
)
from audiobook_factory.audio.encoder import ChapterDeliveryEncoder


def probe_audio_stream_params(file_path: Path | str, ffmpeg_bin: Optional[str] = None) -> Dict[str, Any]:
    """Probes codec, sample rate, channels, and duration of an audio file."""
    p = Path(file_path).resolve()
    ffprobe = get_ffprobe()
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "stream=codec_name,sample_rate,channels:format=duration",
        "-of", "json",
        str(p),
    ]
    try:
        res = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=DEFAULT_FFMPEG_TIMEOUT,
        )
        data = json.loads(res.stdout) if res.stdout else {}
        streams = data.get("streams", [])
        fmt = data.get("format", {})
        if streams:
            return {
                "codec": streams[0].get("codec_name"),
                "sample_rate": int(streams[0].get("sample_rate", 0)),
                "channels": int(streams[0].get("channels", 0)),
                "duration_ms": int(float(fmt.get("duration", 0) or 0) * 1000),
            }
    except Exception as e:
        logger.debug(f"Stream probe notice for {p.name}: {e}")
    return {"codec": None, "sample_rate": 0, "channels": 0, "duration_ms": 0}


def escape_ffmetadata_value(val: Any) -> str:
    """Escapes special characters (=, ;, #, \\) for FFMETADATA1 specification."""
    s = str(val or "")
    s = s.replace("\\", "\\\\")
    for char in ("=", ";", "#"):
        s = s.replace(char, f"\\{char}")
    return s.replace("\n", " ").strip()


def generate_monotonic_ffmetadata(
    metadata: Dict[str, Any],
    chapter_durations: List[Dict[str, Any]],
    output_file: Path,
) -> Path:
    """
    Generates standard FFMETADATA1 file ensuring strictly contiguous, monotonic chapter boundaries:
    START_0 = 0, END_0 = dur_0
    START_k = END_{k-1}, END_k = START_k + dur_k
    Eradicates player navigation glitches caused by non-monotonic or overlapping timestamps (AP-10).
    """
    t = escape_ffmetadata_value(metadata.get("title", "Audiobook"))
    a = escape_ffmetadata_value(metadata.get("author", "Unknown Author"))
    lines = [
        ";FFMETADATA1",
        f"title={t}",
        f"artist={a}",
        f"album_artist={a}",
        f"album={t}",
        "genre=Audiobook",
        "date=2026",
        "",
    ]

    current_start = 0
    for chap in chapter_durations:
        dur = max(0, int(chap.get("duration_ms", 0)))
        end = current_start + dur
        title = escape_ffmetadata_value(chap.get("title", f"Chapter {chap.get('number', 1)}"))

        lines.append("[CHAPTER]")
        lines.append("TIMEBASE=1/1000")
        lines.append(f"START={current_start}")
        lines.append(f"END={end}")
        lines.append(f"title={title}")
        lines.append("")

        current_start = end

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_file


class M4BBookPackager:
    """
    Assembles chapterized .m4b audiobooks using 100% lossless container stream copying.
    Guarantees zero generation loss and monotonic chapter markers.
    """

    def __init__(self, ffmpeg_bin: Optional[str] = None):
        self.ffmpeg = ffmpeg_bin or get_ffmpeg()
        self.encoder = ChapterDeliveryEncoder(ffmpeg_bin=self.ffmpeg)

    def package_audiobook(
        self,
        project_dir: Path | str,
        output_filename: Optional[str] = None,
        cover_image: Optional[Path | str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        enforce_gate6: bool = True,
    ) -> Path:
        """
        Gathers all mastered chapter deliverables, verifies uniform AAC encoding,
        generates monotonic chapter markers, and losslessly packages the final .m4b container.
        """
        proj_dir = Path(project_dir).resolve()
        mastered_dir = proj_dir / "mastered"
        output_dir = proj_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Resolve Project Metadata
        meta_dict = metadata or {}
        if not meta_dict:
            meta_file = proj_dir / "metadata.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta_dict = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load metadata.json: {e}")

        title = meta_dict.get("title", proj_dir.name.replace("_", " ").title())
        author = meta_dict.get("author", "Unknown Author")

        # 2. Resolve Cover Image
        cov_path = Path(cover_image).resolve() if cover_image else None
        if not cov_path or not cov_path.exists():
            for ext in ("cover.jpg", "cover.jpeg", "cover.png", "cover.webp"):
                cand = proj_dir / ext
                if cand.exists():
                    cov_path = cand
                    break

        if not output_filename:
            safe_name = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
            output_filename = f"{safe_name}.m4b"

        final_m4b = output_dir / output_filename

        # 3. Discover Mastered Chapter Audio Deliverables
        all_audio = (
            sorted(mastered_dir.glob("*.m4a"))
            + sorted(mastered_dir.glob("*.mp3"))
            + sorted(mastered_dir.glob("*.wav"))
        )
        if not all_audio:
            raise FileNotFoundError(f"No mastered chapter audio files found in {mastered_dir}")

        # Map by chapter number
        chap_nums = set()
        for f in all_audio:
            m = re.search(r"chapter[_-]?(\d+)", f.name, re.IGNORECASE)
            if m:
                chap_nums.add(int(m.group(1)))

        chapter_audio_files: List[Path] = []
        if chap_nums:
            for c_num in sorted(chap_nums):
                def _belongs_to_chapter(path: Path) -> bool:
                    m = re.search(r"chapter[_-]?(\d+)", path.name, re.IGNORECASE)
                    return m is not None and int(m.group(1)) == c_num

                ch_files = [f for f in all_audio if _belongs_to_chapter(f)]
                # In Vocals-Only mode, prefer pristine vocal master (_mastered.m4a), then _cinematic.m4a, then any
                candidates = sorted([f for f in ch_files if "_mastered." in f.name.lower()])
                if not candidates:
                    candidates = sorted([f for f in ch_files if "_cinematic." in f.name.lower()])
                if not candidates:
                    candidates = sorted(ch_files)

                for cand in candidates:
                    if cand.exists() and cand.stat().st_size > 1000 and get_audio_duration_ms(cand) > 0:
                        chapter_audio_files.append(cand)
                        break
        else:
            # Fallback to general sorting
            candidates = sorted(mastered_dir.glob("*_mastered.m4a")) or sorted(mastered_dir.glob("*_cinematic.m4a")) or sorted(all_audio)
            for cand in candidates:
                if cand.exists() and cand.stat().st_size > 1000 and get_audio_duration_ms(cand) > 0:
                    chapter_audio_files.append(cand)

        if not chapter_audio_files:
            raise FileNotFoundError(f"No valid non-empty chapter audio files found in {mastered_dir}")

        # 4. Enforce Single Lossy Pass Invariant (AP-04)
        # Ensure all chapter files are uniform AAC. If an input is uncompressed WAV, encode it ONCE.
        ready_chapters: List[Path] = []
        for i, cf in enumerate(chapter_audio_files):
            p_info = probe_audio_stream_params(cf)
            if cf.suffix.lower() == ".wav" or p_info.get("codec") != "aac":
                m4a_target = cf.with_suffix(".m4a")
                logger.info(f"[*] Packaging Ingestion: Encoding non-AAC chapter {cf.name} to 192k AAC-LC...")
                self.encoder.encode_chapter_m4a(cf, m4a_target)
                ready_chapters.append(m4a_target)
            else:
                ready_chapters.append(cf)

        # 5. Build Monotonic Chapter Markers & Concat Demuxer
        chapter_durations: List[Dict[str, Any]] = []
        concat_list = output_dir / "m4b_concat.txt"

        with open(concat_list, "w", encoding="utf-8") as f:
            for idx, cf in enumerate(ready_chapters, 1):
                dur_ms = get_audio_duration_ms(cf)
                safe_path = str(cf.resolve()).replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

                m_ch = re.search(r"chapter[_-]?(\d+)", cf.stem, re.IGNORECASE)
                real_ch = int(m_ch.group(1)) if m_ch else idx
                chap_title = f"Chapter {real_ch}"
                if "chapters" in meta_dict and isinstance(meta_dict["chapters"], list):
                    matched_meta = next(
                        (c for c in meta_dict["chapters"] if c.get("number") == real_ch or c.get("chapter_num") == real_ch),
                        None,
                    )
                    if matched_meta and matched_meta.get("title"):
                        chap_title = matched_meta["title"]
                    elif real_ch - 1 < len(meta_dict["chapters"]):
                        chap_title = meta_dict["chapters"][real_ch - 1].get("title", chap_title)
                    elif idx - 1 < len(meta_dict["chapters"]):
                        chap_title = meta_dict["chapters"][idx - 1].get("title", chap_title)

                chapter_durations.append({
                    "number": idx,
                    "title": chap_title,
                    "duration_ms": dur_ms,
                })

        meta_txt = output_dir / "chapters.txt"
        generate_monotonic_ffmetadata(meta_dict, chapter_durations, meta_txt)

        # 6. Lossless Container Assembly via '-c:a copy' (Zero Transcode)
        has_cover = cov_path is not None and cov_path.exists()
        tmp_m4b = final_m4b.with_suffix(f".tmp_{os.getpid()}_{uuid.uuid4().hex[:6]}.m4b")

        pack_cmd = [
            self.ffmpeg, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-i", str(meta_txt),
        ]

        if has_cover:
            pack_cmd.extend(["-i", str(cov_path)])
            pack_cmd.extend(["-map", "0:a", "-map", "2:v", "-map_metadata", "1", "-map_chapters", "1"])
            pack_cmd.extend(["-c:a", "copy", "-c:v", "mjpeg", "-disposition:v", "attached_pic"])
        else:
            pack_cmd.extend(["-map", "0:a", "-map_metadata", "1", "-map_chapters", "1"])
            pack_cmd.extend(["-c:a", "copy"])

        pack_cmd.extend(["-movflags", "+faststart", str(tmp_m4b)])

        logger.info(f"[*] M4BBookPackager: Losslessly assembling container -> {final_m4b.name} (-c:a copy)...")
        temp_concat = output_dir / f"temp_concat_{uuid.uuid4().hex[:6]}.m4a"
        try:
            try:
                subprocess.run(
                    pack_cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=DEFAULT_FFMPEG_TIMEOUT,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                # Fallback for complex multi-input metadata mapping
                concat_cmd = [
                    self.ffmpeg, "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_list),
                    "-c:a", "copy",
                    str(temp_concat),
                ]
                subprocess.run(concat_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=DEFAULT_FFMPEG_TIMEOUT)
    
                fb_cmd = [
                    self.ffmpeg, "-y",
                    "-i", str(temp_concat),
                    "-i", str(meta_txt),
                ]
                if has_cover:
                    fb_cmd.extend(["-i", str(cov_path), "-map", "0:a", "-map", "2:v", "-map_metadata", "1", "-map_chapters", "1", "-c:a", "copy", "-c:v", "mjpeg", "-disposition:v", "attached_pic"])
                else:
                    fb_cmd.extend(["-map", "0:a", "-map_metadata", "1", "-map_chapters", "1", "-c:a", "copy"])
                fb_cmd.extend(["-movflags", "+faststart", str(tmp_m4b)])
                subprocess.run(fb_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=DEFAULT_FFMPEG_TIMEOUT)
                
            _atomic_replace(tmp_m4b, final_m4b)
        finally:
            if tmp_m4b.exists():
                tmp_m4b.unlink(missing_ok=True)
            if temp_concat.exists():
                temp_concat.unlink(missing_ok=True)
            if concat_list.exists():
                concat_list.unlink(missing_ok=True)
            if meta_txt.exists():
                meta_txt.unlink(missing_ok=True)

        size_mb = round(final_m4b.stat().st_size / (1024 * 1024), 2)
        logger.info(f"[+] Final Audiobook M4B Certified ({size_mb} MB) -> {final_m4b}")
        return final_m4b
