#!/usr/bin/env python3
"""
Audiobook Factory - Dialogue Editorial Bridge (v5.3).
Coordinates Tier A Ingestion, Dialogue Editorial Layer (DE-01 - DE-07),
and Tier B Streaming Pre-Master Composition into premaster.wav.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union

from audiobook_factory.logger import logger
from audiobook_factory.audio.contracts import IngestionConfig, SegmentAudioContract
from audiobook_factory.audio.ingestion import AudioIngestionManager
from audiobook_factory.audio.stream_composer import ChunkStreamComposer


class DialogueEditorialBridge:
    """
    Coordinates Ingestion -> Dialogue Editing (Endpoints, Breaths, Pauses) -> Streaming Pre-Master.
    """

    def __init__(self, config: Optional[IngestionConfig] = None, project_dir: Optional[Union[Path, str]] = None):
        self.config = config or IngestionConfig()
        self.project_dir = Path(project_dir).resolve() if project_dir else Path(".")
        self.ingestion_manager = AudioIngestionManager(config=self.config, project_dir=self.project_dir)
        self.composer = ChunkStreamComposer(config=self.config)

    def prepare_premaster(
        self,
        segments: List[Path],
        output_premaster_wav: Path,
        script_segments: Optional[List[Dict[str, Any]]] = None,
        edit_plans: Optional[List[Any]] = None,
        spatial_staging: bool = False,
        pre_roll_ms: int = 500,
        post_roll_ms: int = 1500,
    ) -> Tuple[Path, float, Dict[int, float]]:
        """
        Directly stream-composes continuous pre-master WAV from given segments and edit plans.
        Returns: (output_premaster_wav, total_dur_sec, segment_durations_map)
        """
        return self.composer.compose_chapter_premaster(
            audio_segments=segments,
            output_wav=output_premaster_wav,
            script_segments=script_segments,
            edit_plans=edit_plans,
            pre_roll_ms=pre_roll_ms,
            post_roll_ms=post_roll_ms,
            spatial_staging=spatial_staging,
        )

    def process_and_compose_chapter(
        self,
        chapter_num: int,
        raw_audio_segments: List[Path],
        script_segments: List[Dict[str, Any]],
        output_premaster_wav: Path,
        spatial_staging: bool = False,
        pre_roll_ms: int = 500,
        post_roll_ms: int = 1500,
    ) -> Tuple[Path, float, Dict[int, float], List[Path], Any]:
        """
        Executes end-to-end Tier A & Tier B:
        1. Ingests raw chunks (standardizing to 48kHz stereo, stripping C2PA, applying single 5ms taper).
        2. Executes Dialogue Editorial Layer (DE-01: endpoints, breaths, pauses, inter-take leveling).
        3. Streams pre-master directly into output_premaster_wav with zero scratch silence files.
        Returns: (premaster_wav, total_dur_sec, seg_durations_map, edited_segments, qc_report)
        """
        if not raw_audio_segments:
            raise ValueError(f"No audio segments provided for Chapter {chapter_num}")

        output_premaster_wav = Path(output_premaster_wav).resolve()
        output_premaster_wav.parent.mkdir(parents=True, exist_ok=True)

        # Index script segments by index
        script_by_idx: Dict[int, Dict[str, Any]] = {}
        for s in script_segments:
            idx = s.get("index", 1) if isinstance(s, dict) else getattr(s, "index", 1)
            script_by_idx[idx] = s if isinstance(s, dict) else s.model_dump()

        # Step 1: Ingest and standardize every raw chunk to 48kHz stereo
        ingested_contracts: List[SegmentAudioContract] = []
        ingested_paths: List[Path] = []

        for i, raw_seg in enumerate(raw_audio_segments):
            s_idx = i + 1
            for part in raw_seg.stem.split("_"):
                if part.startswith("s") and part[1:].isdigit():
                    s_idx = int(part[1:])
                    break

            meta = script_by_idx.get(s_idx, {})
            speaker = str(meta.get("speaker", "Narrator"))
            voice_name = str(meta.get("voice", "Aoede"))
            contract = self.ingestion_manager.ingest_segment(
                source=raw_seg,
                chapter_id=chapter_num,
                segment_index=s_idx,
                speaker=speaker,
                voice_name=voice_name,
                segment_type=meta.get("type", "narration"),
                intensity_level=meta.get("intensity_level", "medium"),
                delivery_style=meta.get("delivery_style"),
                literary_text=meta.get("text", ""),
                spoken_text=meta.get("spoken_text", ""),
                word_alignments=meta.get("word_alignments"),
            )
            ingested_contracts.append(contract)
            ingested_paths.append(contract.audio_path)

        # Step 2: Execute Dialogue Editorial Layer
        edit_plans = None
        qc_report = None
        edited_segments = ingested_paths

        try:
            from audiobook_factory.dialogue_editing import DialogueEditor
            dialogue_editor = DialogueEditor(project_dir=self.project_dir)
            edited_segments, edit_plans, qc_report = dialogue_editor.process_chapter(
                chapter_num=chapter_num,
                audio_segments=ingested_paths,
                script_segments=script_segments,
            )
            if qc_report and (not qc_report.passed or qc_report.has_hard_failures):
                acoustic_fatal_codes = {
                    "NUMERICAL_INSTABILITY_NAN_INF",
                    "SEVERE_CLIPPING_DETECTED",
                    "EMPTY_AUDIO_SAMPLES",
                }
                fatal_issues = [f for f in qc_report.hard_failures if f.code in acoustic_fatal_codes]
                if fatal_issues:
                    raise RuntimeError(
                        f"Dialogue Editorial QC detected critical acoustic defect in Chapter {chapter_num:02d}: "
                        f"{fatal_issues[0].code} - {fatal_issues[0].message}."
                    )
                logger.warning(f"[!] Dialogue Editorial QC notice for Chapter {chapter_num:02d}: falling back to unedited ingested takes.")
                edited_segments = ingested_paths
                edit_plans = None
        except Exception as e:
            logger.warning(f"[!] Dialogue Editorial notice for Chapter {chapter_num:02d}: {e}")
            edited_segments = ingested_paths
            edit_plans = None

        # Step 3: Stream-compose continuous pre-master WAV
        premaster_wav, total_dur, seg_durations = self.composer.compose_chapter_premaster(
            audio_segments=edited_segments,
            output_wav=output_premaster_wav,
            script_segments=script_segments,
            edit_plans=edit_plans,
            pre_roll_ms=pre_roll_ms,
            post_roll_ms=post_roll_ms,
            spatial_staging=spatial_staging,
        )

        return premaster_wav, total_dur, seg_durations, edited_segments, qc_report
