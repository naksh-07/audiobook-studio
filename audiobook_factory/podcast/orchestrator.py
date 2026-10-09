#!/usr/bin/env python3
"""
Audiobook Studio - Unified Podcast & Technical Whitepaper Orchestrator.
=====================================================================
Pipelines any scientific research paper (arXiv), technical whitepaper,
report, or markdown document directly into a broadcast-mastered podcast:
1. Ingestion: DocumentExtractionEngine -> CanonicalBook AST.
2. Scripting: PodcastScriptBuilder -> Dual-Host Screenplay (podcast_script.json).
3. Production: PodcastAudioProducer -> Multi-Voice TTS, Hann Micro-fades & EBU R128 Mastering.
"""

from __future__ import annotations
import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from audiobook_factory.logger import logger
from audiobook_factory.extraction.engine import ExtractionEngine
from audiobook_factory.extraction.contracts import CanonicalBook
from audiobook_factory.podcast.contracts import (
    PodcastScript,
    HostProfile,
    VerbalizationStyle,
    PodcastProductionResult,
)
from audiobook_factory.podcast.script_builder import PodcastScriptBuilder
from audiobook_factory.podcast.producer import PodcastAudioProducer


class PodcastOrchestrator:
    """
    Unified end-to-end orchestration coordinator for technical paper
    and research document podcast synthesis.
    """

    def __init__(
        self,
        projects_dir: Optional[Path] = None,
        producer: Optional[PodcastAudioProducer] = None,
    ):
        self.projects_dir = (
            Path(projects_dir).resolve()
            if projects_dir
            else Path.cwd() / "audiobooks" / "projects"
        )
        self.producer = producer or PodcastAudioProducer()

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

        # -------------------------------------------------------------
        # Step 1: Forensic Ingestion -> CanonicalBook AST
        # -------------------------------------------------------------
        logger.info(f"[*] Step 1/3: Ingesting source document '{source_path.name}'...")
        canonical_book = ExtractionEngine.extract(
            input_file=source_path,
            output_base_dir=base_dir,
            book_id=book_id,
            force_gate=force_gate,
        )
        canonical_json_path = project_dir / "canonical" / "book.json"

        # -------------------------------------------------------------
        # Step 2: Technical Verbalization & Dual-Host Scripting
        # -------------------------------------------------------------
        logger.info(f"[*] Step 2/3: Generating dual-host podcast script for '{canonical_book.title}'...")
        hosts = [
            HostProfile(
                id="host_a",
                name=host_a_name,
                role="lead_explainer",
                default_voice=host_a_voice,
                acting_style="engaging, articulate, measured, clear",
            ),
            HostProfile(
                id="host_b",
                name=host_b_name,
                role="inquisitive_cohost",
                default_voice=host_b_voice,
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

        # -------------------------------------------------------------
        # Step 3: Multi-Voice TTS Synthesis & Broadcast Mastering
        # -------------------------------------------------------------
        logger.info(f"[*] Step 3/3: Synthesizing voices & mastering audio to EBU R128 (-19.0 LUFS)...")
        prod_dir = project_dir / "production"
        result = self.producer.produce_podcast_audio(
            script_or_path=script,
            output_dir=prod_dir,
            mock_mode=mock_mode,
        )

        # Enrich result with AST and script paths
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
