#!/usr/bin/env python3
"""
Audiobook Factory - Dedicated Podcast Engine: Production Orchestrator.
Coordinates end-to-end 2-Host podcast production:
1. Script Generation & 5-Part Retention Planning.
2. Multi-Host Neural TTS Synthesis with Token-Bucket Concurrency.
3. Stereo Spatial Staging (Host A on Left-Mid, Host B on Right-Mid).
4. Broadcast Vocal Mastering to -16.0 LUFS (EBU R128 podcast standard).
5. AAC M4A Packaging.
"""

from __future__ import annotations
import os
import re
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from audiobook_factory.dramaturgy.scene_analyzer import SceneAnalyzer
from audiobook_factory.dramaturgy.beat_planner import BeatPlanner
from audiobook_factory.dramaturgy.contracts import DramaticPlan
from audiobook_factory.podcast.contracts import PodcastEpisodePlan, HostProfile
from audiobook_factory.podcast.persona_engine import HostPersonaEngine
from audiobook_factory.tts_dispatcher import TTSDispatcher
from audiobook_factory.mastering import concatenate_and_master_chapter, get_ffmpeg
from audiobook_factory.soundscape import get_audio_duration

logger = logging.getLogger("AudiobookFactory")


class PodcastOrchestrator:
    """
    Orchestrates the complete 2-Host narrative podcast production lifecycle.
    """

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def generate_episode_script(
        self,
        project_dir: Path,
        chapter_num: int,
        use_hindi: bool = True,
        overwrite: bool = False,
        hosts: Optional[Dict[str, HostProfile]] = None,
    ) -> Tuple[Path, Path]:
        """
        Generates 2-Host podcast script and episode plan for a given chapter.
        Returns: (plan_path, script_path)
        """
        project_dir = Path(project_dir).resolve()
        input_dir = project_dir / ("translation" if use_hindi else "extracted")
        podcasts_dir = project_dir / "podcasts"
        podcasts_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        target_files = sorted(input_dir.glob("*.md"))
        matched_files = [
            tf for tf in target_files
            if f"_{chapter_num:03d}" in tf.stem or tf.stem.endswith(f"_{chapter_num}") or tf.stem == f"chapter_{chapter_num:03d}" or tf.stem == f"chapter_{chapter_num}"
        ]
        if not matched_files:
            raise FileNotFoundError(f"Chapter {chapter_num} markdown not found in {input_dir}")

        chap_file = matched_files[0]
        chap_stem = chap_file.stem
        plan_file = podcasts_dir / f"{chap_stem}_podcast_plan.json"
        script_file = scripts_dir / f"{chap_stem}_podcast_script.json"

        if not overwrite and plan_file.exists() and plan_file.stat().st_size > 50 and script_file.exists():
            logger.info(f"[-] Using existing podcast plan: {plan_file.name}")
            return plan_file, script_file

        with open(chap_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Load Memory and BookBible if available
        bible = None
        mem_ctx = None
        try:
            from audiobook_factory.translation.book_bible import BookBible
            from audiobook_factory.translation.memory import MemoryStore, MemoryRetriever
            bible = BookBible.load_from_project(project_dir)
            m_store = MemoryStore.load(MemoryStore.default_store_path(project_dir), book_bible=bible)
            mem_ctx = MemoryRetriever.retrieve_for_scene(
                store=m_store,
                book_bible=bible,
                chapter=chapter_num,
                scene_id=chap_stem,
                scene_text=content,
            )
        except Exception:
            pass

        # 1. Synthesize Shared Dramaturgy Core
        known_chars = list(bible.characters.keys()) if bible and bible.characters else None
        scenes = SceneAnalyzer.segment_and_analyze_scenes(
            chapter_text=content,
            chapter_num=chapter_num,
            chapter_title=f"Chapter {chapter_num}",
            known_characters=known_chars,
            memory_context=mem_ctx,
        )
        scenes = BeatPlanner.plan_chapter_beats(
            chapter_text=content,
            scenes=scenes,
            known_characters=known_chars,
            memory_context=mem_ctx,
        )
        dramatic_plan = DramaticPlan(
            chapter_id=chap_stem,
            chapter_num=chapter_num,
            scenes=scenes,
            total_beats=sum(len(s.beats) for s in scenes),
        )

        # 2. Adapt to 2-Host Podcast
        from audiobook_factory.adapters.podcast import PodcastAdapter
        active_hosts = hosts or HostPersonaEngine.load_hosts_from_config(project_dir / "podcast_config.json")
        adapter = PodcastAdapter(model=self.model, hosts=active_hosts)
        standard_segments, episode_plan = adapter.adapt(
            chapter_text=content,
            dramatic_plan=dramatic_plan,
            memory_context=mem_ctx,
            is_hindi=use_hindi,
            chapter_num=chapter_num,
            chapter_id=chap_stem,
            return_plan=True,
        )

        # Save artifacts
        episode_plan.save_to_file(plan_file)
        with open(script_file, "w", encoding="utf-8") as f:
            json.dump(standard_segments, f, ensure_ascii=False, indent=2)

        logger.info(f"[+] Built podcast episode plan -> {plan_file.name} ({len(standard_segments)} turns)")
        return plan_file, script_file

    def synthesize_podcast_script(
        self,
        project_dir: Path,
        script_file: Path,
        chapter_num: int,
        default_voice: str = "Puck",
        workers: int = 3,
    ) -> List[Path]:
        """
        Synthesizes audio segments for the podcast episode script.
        """
        project_dir = Path(project_dir).resolve()
        dispatcher = TTSDispatcher(
            project_dir=project_dir,
            default_voice=default_voice,
            max_workers=workers,
            chunk_prefix="p",
        )
        dispatcher.synthesize_chapter_script(script_file, chapter_num)

        audio_dir = project_dir / "audio_chunks"
        raw_segments = sorted(audio_dir.glob(f"p{chapter_num:03d}_*.wav"))
        return raw_segments

    def master_podcast_episode(
        self,
        project_dir: Path,
        chapter_num: int,
        chap_stem: str,
        script_data: List[Dict[str, Any]],
        audio_segments: List[Path],
        target_lufs: float = -16.0,
        true_peak_db: float = -1.0,
    ) -> Path:
        """
        Masters 2-Host podcast segments with stereo spatial staging to -16.0 LUFS EBU R128.
        """
        project_dir = Path(project_dir).resolve()
        podcasts_dir = project_dir / "podcasts"
        podcasts_dir.mkdir(parents=True, exist_ok=True)

        vocal_wav = podcasts_dir / f"{chap_stem}_podcast_master.wav"
        out_m4a = podcasts_dir / f"{chap_stem}_podcast.m4a"

        # Apply stereo spatial staging (-0.25 Left for Host A, +0.25 Right for Host B)
        concatenate_and_master_chapter(
            audio_segments=audio_segments,
            output_chapter_file=vocal_wav,
            script_segments=script_data,
            target_lufs=target_lufs,
            true_peak_db=true_peak_db,
            spatial_staging=True,
        )

        ffmpeg = get_ffmpeg()
        cmd_enc = [
            ffmpeg, "-y",
            "-i", str(vocal_wav),
            "-c:a", "aac", "-b:a", "192k",
            str(out_m4a),
        ]
        subprocess.run(cmd_enc, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=300.0)
        logger.info(f"[+] Podcast master created: {out_m4a.name} ({target_lufs} LUFS)")
        return out_m4a

    def produce_podcast_episode(
        self,
        project_dir: Path,
        chapter_num: int,
        use_hindi: bool = True,
        target_lufs: float = -16.0,
        workers: int = 3,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Full single-command production: Generation -> Multi-Host TTS -> Stereo Staging -> -16.0 LUFS Mastering.
        """
        project_dir = Path(project_dir).resolve()
        plan_file, script_file = self.generate_episode_script(
            project_dir=project_dir,
            chapter_num=chapter_num,
            use_hindi=use_hindi,
            overwrite=overwrite,
        )

        with open(script_file, "r", encoding="utf-8") as f:
            script_data = json.load(f)

        plan = PodcastEpisodePlan.load_from_file(plan_file)

        # Synthesize audio chunks
        segments = self.synthesize_podcast_script(
            project_dir=project_dir,
            script_file=script_file,
            chapter_num=chapter_num,
            workers=workers,
        )

        # Master to -16.0 LUFS with stereo staging
        chap_stem = script_file.stem.replace("_podcast_script", "").replace("_script", "")
        master_file = self.master_podcast_episode(
            project_dir=project_dir,
            chapter_num=chapter_num,
            chap_stem=chap_stem,
            script_data=script_data,
            audio_segments=segments,
            target_lufs=target_lufs,
        )

        dur_sec = get_audio_duration(master_file) if master_file.exists() else plan.total_duration_estimate_sec

        return {
            "chapter_num": chapter_num,
            "episode_title": plan.episode_title,
            "plan_file": str(plan_file),
            "script_file": str(script_file),
            "master_file": str(master_file),
            "duration_min": round(dur_sec / 60.0, 2),
            "total_turns": len(script_data),
            "target_lufs": target_lufs,
        }
