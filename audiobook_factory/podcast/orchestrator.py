#!/usr/bin/env python3
"""
Audiobook Studio - Unified Dual-Track Podcast Orchestrator.
==========================================================
Coordinates end-to-end podcast production across two distinct modalities:
1. Technical Paper Verbalization:
   Pipelines scientific research papers (arXiv), technical whitepapers,
   reports, or markdown documents directly into dual-host broadcast podcasts.
   (DocumentExtractionEngine -> PodcastScriptBuilder -> PodcastAudioProducer).
2. Literary Chapter Narrative 2-Host Podcasting:
   Transforms literary novel chapters into 5-part retention-driven conversational podcasts.
   (Shared Dramaturgy Core -> PodcastAdapter -> TTSDispatcher -> Stereo Spatial Mastering).
"""

from __future__ import annotations
import os
import re
import json
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

from audiobook_factory.logger import logger
from audiobook_factory.extraction.engine import ExtractionEngine
from audiobook_factory.extraction.contracts import CanonicalBook
from audiobook_factory.podcast.contracts import (
    PodcastScript,
    PodcastEpisodePlan,
    HostProfile,
    VerbalizationStyle,
    PodcastProductionResult,
)
from audiobook_factory.podcast.script_builder import PodcastScriptBuilder
from audiobook_factory.podcast.producer import PodcastAudioProducer
from audiobook_factory.dramaturgy.scene_analyzer import SceneAnalyzer
from audiobook_factory.dramaturgy.beat_planner import BeatPlanner
from audiobook_factory.dramaturgy.contracts import DramaticPlan
from audiobook_factory.podcast.persona_engine import HostPersonaEngine
from audiobook_factory.tts_dispatcher import TTSDispatcher
from audiobook_factory.mastering import concatenate_and_master_chapter, get_ffmpeg
from audiobook_factory.soundscape import get_audio_duration


class PodcastOrchestrator:
    """
    Unified end-to-end orchestration coordinator for technical paper verbalization
    and chapter narrative 2-host podcast synthesis.
    """

    def __init__(
        self,
        projects_dir: Optional[Path] = None,
        producer: Optional[PodcastAudioProducer] = None,
        model: Optional[str] = None,
    ):
        self.projects_dir = (
            Path(projects_dir).resolve()
            if projects_dir
            else Path.cwd() / "audiobooks" / "projects"
        )
        self.producer = producer or PodcastAudioProducer()
        self.model = model

    # =========================================================================
    # Modality 1: Technical Whitepaper & Document Verbalization
    # =========================================================================

    def process_document_to_podcast(
        self,
        source_file: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        style: VerbalizationStyle = "conversational_podcast",
        host_a_name: str = "Dr. Vance",
        host_a_voice: str = "Charon",
        host_b_name: str = "Maya",
        host_b_voice: str = "Aoede",
        script_only: bool = False,
        mock_mode: bool = False,
        force_gate: bool = False,
    ) -> PodcastProductionResult:
        """
        Executes the full 3-step autonomous pipeline on a source document:
        Extraction -> Dialogue Verbalization & Scripting -> Multi-Voice Synthesis & Mastering.
        """
        source_path = Path(source_file).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Source document not found: {source_path}")

        if output_dir:
            project_dir = Path(output_dir).resolve()
            base_dir = project_dir.parent
            book_id = project_dir.name
        else:
            slug = source_path.stem.lower().replace(" ", "_").replace("-", "_")
            base_dir = self.projects_dir
            book_id = f"{slug}_podcast"
            project_dir = base_dir / book_id

        project_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"=== [PODCAST ORCHESTRATION START] Document: '{source_path.name}' -> Project: '{project_dir.name}' ===")

        # Step 1: Forensic Ingestion -> CanonicalBook AST
        logger.info(f"[*] Step 1/3: Ingesting source document '{source_path.name}'...")
        canonical_book = ExtractionEngine.extract(
            input_file=source_path,
            output_base_dir=base_dir,
            book_id=book_id,
            force_gate=force_gate,
        )
        canonical_json_path = project_dir / "canonical" / "book.json"

        # Step 2: Technical Verbalization & Dual-Host Scripting
        logger.info(f"[*] Step 2/3: Generating dual-host podcast script for '{canonical_book.title}'...")
        hosts = [
            HostProfile(
                host_id="host_a",
                name=host_a_name,
                role="lead_explainer",
                voice_id=host_a_voice,
                acting_style="engaging, articulate, measured, clear",
            ),
            HostProfile(
                host_id="host_b",
                name=host_b_name,
                role="inquisitive_cohost",
                voice_id=host_b_voice,
                acting_style="curious, enthusiastic, sharp, conversational",
            ),
        ]

        builder = PodcastScriptBuilder(hosts=hosts, style=style)
        script = builder.build_from_book(canonical_book)

        script_json_path = project_dir / "podcast_script.json"
        with open(script_json_path, "w", encoding="utf-8") as f:
            json.dump(script.to_screenplay_json(), f, indent=2, ensure_ascii=False)

        logger.info(
            f"[+] Script generated: {script.total_segments} turns, "
            f"{script.total_words} words (~{script.estimated_duration_sec:.1f}s) -> {script_json_path.name}"
        )

        if script_only:
            logger.info("[*] Script-only flag set. Skipping audio synthesis.")
            return PodcastProductionResult(
                podcast_id=script.podcast_id,
                status="SUCCESS",
                total_segments=script.total_segments,
                total_words=script.total_words,
                duration_sec=script.estimated_duration_sec,
                canonical_book_path=str(canonical_json_path),
                script_path=str(script_json_path),
                metrics={"script_only": True},
            )

        # Step 3: Multi-Voice TTS Synthesis & Broadcast Mastering
        logger.info(f"[*] Step 3/3: Synthesizing voices & mastering audio to EBU R128 (-19.0 LUFS)...")
        prod_dir = project_dir / "production"
        result = self.producer.produce_podcast_audio(
            script_or_path=script,
            output_dir=prod_dir,
            mock_mode=mock_mode,
        )

        result.canonical_book_path = str(canonical_json_path)
        result.script_path = str(script_json_path)

        logger.info(
            f"=== [PODCAST ORCHESTRATION COMPLETE] Status: {result.status} | "
            f"Duration: {result.duration_sec:.1f}s | Mastered Audio: {result.mastered_audio_path} ==="
        )
        return result

    def render_existing_script(
        self,
        script_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        mock_mode: bool = False,
    ) -> PodcastProductionResult:
        """Renders an existing podcast_script.json file to mastered audio."""
        script_file = Path(script_path).resolve()
        if not script_file.exists():
            raise FileNotFoundError(f"Podcast script not found: {script_file}")

        target_dir = Path(output_dir).resolve() if output_dir else script_file.parent / "production"
        return self.producer.produce_podcast_audio(
            script_or_path=script_file,
            output_dir=target_dir,
            mock_mode=mock_mode,
        )

    # =========================================================================
    # Modality 2: Chapter Narrative 2-Host Podcasting (Dramaturgy Driven)
    # =========================================================================

    def generate_episode_script(
        self,
        project_dir: Path | str,
        chapter_num: int,
        use_hindi: bool = True,
        overwrite: bool = False,
        hosts: Optional[Dict[str, HostProfile]] = None,
    ) -> Tuple[Path, Path]:
        """
        Generates 2-Host podcast script and episode plan for a given chapter.
        Returns: (plan_path, script_path)
        """
        proj_dir = Path(project_dir).resolve()
        input_dir = proj_dir / ("translation" if use_hindi else "extracted")
        podcasts_dir = proj_dir / "podcasts"
        podcasts_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = proj_dir / "scripts"
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
            bible = BookBible.load_from_project(proj_dir)
            if bible:
                m_path = MemoryStore.default_store_path(proj_dir)
                if m_path.exists():
                    m_store = MemoryStore.load(m_path, book_bible=bible)
                    mem_ctx = MemoryRetriever.retrieve_for_scene(
                        store=m_store,
                        book_bible=bible,
                        chapter=chapter_num,
                        scene_id=chap_stem,
                        scene_text=content,
                    )
        except Exception as e:
            logger.warning(f"  [-] Optional Memory/BookBible context load skipped for {proj_dir.name}: {e}")

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
        active_hosts = hosts or HostPersonaEngine.load_hosts_from_config(proj_dir / "podcast_config.json")
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
        project_dir: Path | str,
        script_file: Path | str,
        chapter_num: int,
        default_voice: str = "Puck",
        workers: int = 3,
    ) -> List[Path]:
        """
        Synthesizes audio segments for the podcast episode script.
        """
        proj_dir = Path(project_dir).resolve()
        script_p = Path(script_file).resolve()
        dispatcher = TTSDispatcher(
            project_dir=proj_dir,
            default_voice=default_voice,
            max_workers=workers,
            chunk_prefix="p",
        )
        dispatcher.synthesize_chapter_script(script_p, chapter_num)

        audio_dir = proj_dir / "audio_chunks"
        raw_segments = sorted(audio_dir.glob(f"p{chapter_num:03d}_*.wav"))
        return raw_segments

    def master_podcast_episode(
        self,
        project_dir: Path | str,
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
        proj_dir = Path(project_dir).resolve()
        podcasts_dir = proj_dir / "podcasts"
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
        project_dir: Path | str,
        chapter_num: int,
        use_hindi: bool = True,
        target_lufs: float = -16.0,
        workers: int = 3,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Full single-command production: Generation -> Multi-Host TTS -> Stereo Staging -> -16.0 LUFS Mastering.
        """
        proj_dir = Path(project_dir).resolve()
        plan_file, script_file = self.generate_episode_script(
            project_dir=proj_dir,
            chapter_num=chapter_num,
            use_hindi=use_hindi,
            overwrite=overwrite,
        )

        with open(script_file, "r", encoding="utf-8") as f:
            script_data = json.load(f)

        plan = PodcastEpisodePlan.load_from_file(plan_file)

        # Synthesize audio chunks
        segments = self.synthesize_podcast_script(
            project_dir=proj_dir,
            script_file=script_file,
            chapter_num=chapter_num,
            workers=workers,
        )

        # Master to -16.0 LUFS with stereo staging
        chap_stem = script_file.stem.replace("_podcast_script", "").replace("_script", "")
        master_file = self.master_podcast_episode(
            project_dir=proj_dir,
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


def process_document_to_podcast(
    source_file: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    style: VerbalizationStyle = "conversational_podcast",
    host_a_name: str = "Dr. Vance",
    host_a_voice: str = "Charon",
    host_b_name: str = "Maya",
    host_b_voice: str = "Aoede",
    script_only: bool = False,
    mock_mode: bool = False,
    force_gate: bool = False,
) -> PodcastProductionResult:
    """Convenience function to run the full document-to-podcast orchestration pipeline."""
    orchestrator = PodcastOrchestrator()
    return orchestrator.process_document_to_podcast(
        source_file=source_file,
        output_dir=output_dir,
        style=style,
        host_a_name=host_a_name,
        host_a_voice=host_a_voice,
        host_b_name=host_b_name,
        host_b_voice=host_b_voice,
        script_only=script_only,
        mock_mode=mock_mode,
        force_gate=force_gate,
    )
