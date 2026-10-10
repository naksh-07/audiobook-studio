"""
Audiobook Factory - Chapter Dialogue Production Runner.
Handles dialogue editing QC, dialogue bus mastering, and duration/word alignment mapping.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import json
import re

from audiobook_factory.logger import logger
from audiobook_factory.soundscape import get_audio_duration
from audiobook_factory.audio.editorial import DialogueEditorialBridge
from audiobook_factory.mastering_contracts import MasteringRequest, MasteringProfile
from audiobook_factory.mastering_engine import MasteringEngineV2



def process_and_master_dialogue_stem(
    project_dir: Path,
    chapter_num: int,
    chap_stem: str,
    script_data: List[Dict[str, Any]],
    audio_dir: Path,
    mastered_dir: Path,
    spatial_staging: bool = False,
    segment_files: Optional[List[Path]] = None,
) -> Tuple[Path, float, Dict[int, float], List[Path]]:
    """
    Executes the dialogue editorial layer, masters vocal bus via MasteringEngineV2,
    and maps exact segment durations and word alignments.
    Returns: (vocal_wav, vocal_dur, seg_durations, segments)
    """
    if segment_files:
        segments = segment_files
    else:
        raw_segments = sorted(audio_dir.glob(f"c{chapter_num:03d}_*.wav"))
        if not raw_segments:
            raise RuntimeError(f"No audio segments found for Chapter {chapter_num}")

        # Deduplicate multiple takes per segment index, retaining the latest modified take
        seg_dict = {}
        for p in raw_segments:
            m_s = re.search(r"_s(\d{4})_", p.name)
            if m_s:
                s_idx = int(m_s.group(1))
                if s_idx not in seg_dict or p.stat().st_mtime > seg_dict[s_idx].stat().st_mtime:
                    seg_dict[s_idx] = p
        segments = [seg_dict[k] for k in sorted(seg_dict.keys())] if seg_dict else raw_segments

    edit_plans = None
    edited_segments = segments
    try:
        from audiobook_factory.dialogue_editing import DialogueEditor
        dialogue_editor = DialogueEditor(project_dir=project_dir)
        edited_segments, edit_plans, qc_rep = dialogue_editor.process_chapter(
            chapter_num=chapter_num,
            audio_segments=segments,
            script_segments=script_data,
        )
        if not qc_rep.passed or qc_rep.has_hard_failures:
            acoustic_fatal_codes = {
                "NUMERICAL_INSTABILITY_NAN_INF",
                "SEVERE_CLIPPING_DETECTED",
                "EMPTY_AUDIO_SAMPLES",
            }
            fatal_issues = [f for f in qc_rep.hard_failures if f.code in acoustic_fatal_codes]
            if fatal_issues:
                raise RuntimeError(
                    f"Dialogue Editorial QC detected critical acoustic defect in Chapter {chapter_num:02d}: "
                    f"{fatal_issues[0].code} - {fatal_issues[0].message}. Halting to prevent defective master."
                )
            logger.warning(f"[!] Dialogue Editorial QC notice for Chapter {chapter_num:02d}: using unedited fallback.")
            edited_segments = segments
            edit_plans = None
    except Exception as e:
        logger.warning(f"[!] Dialogue Editorial notice for Chapter {chapter_num:02d}: {e}")
        edited_segments = segments
        edit_plans = None

    vocal_wav = mastered_dir / f"{chap_stem}_dialogue.wav"
    premaster_wav = mastered_dir / f"{chap_stem}_dialogue.premaster.wav"

    try:
        bridge = DialogueEditorialBridge()
        bridge.prepare_premaster(
            segments=edited_segments,
            output_premaster_wav=premaster_wav,
            script_segments=script_data,
            edit_plans=edit_plans,
            spatial_staging=spatial_staging,
        )

        master_profile = MasteringProfile(
            target_lufs=-19.0,
            tolerance_lu=0.5,
            true_peak_ceiling_dbtp=-2.0,
            limiter_ceiling_db=-2.0,
            limiter_release_ms=40,
            output_sample_rate=48000,
            output_channels=2,
        )
        master_req = MasteringRequest(
            chapter_id=chap_stem,
            premaster_path=str(premaster_wav),
            output_master_path=str(vocal_wav),
            profile=master_profile,
            metadata={"chapter_num": chapter_num, "spatial_staging": spatial_staging},
        )
        engine = MasteringEngineV2()
        master_res = engine.master(master_req)

        if master_res.status not in ("SUCCESS", "REVIEW_REQUIRED"):
            raise RuntimeError(
                f"MasteringEngineV2 returned status {master_res.status}: {master_res.error_message}"
            )
        lufs_val = master_res.analysis_after.integrated_lufs if master_res.analysis_after else -19.0
        tp_val = master_res.analysis_after.true_peak_dbtp if master_res.analysis_after else -2.0
        logger.info(
            f"[+] Dialogue Stem Mastered via MasteringEngineV2 for Chapter {chapter_num:02d} "
            f"(LUFS: {lufs_val:.2f}, TP: {tp_val} dBTP)"
        )
    finally:
        if premaster_wav.exists():
            try:
                premaster_wav.unlink()
            except OSError:
                pass

    vocal_dur = get_audio_duration(vocal_wav)

    # Map exact segment durations strictly from segments passed to vocal mastering
    seg_durations: Dict[int, float] = {}
    for seg in script_data:
        s_idx = seg.get("index", 1)
        matched = [s for s in edited_segments if f"_s{s_idx:04d}_" in s.name]
        if matched:
            chunk_path = matched[0]
            seg_durations[s_idx] = get_audio_duration(chunk_path)
            words_json = chunk_path.with_suffix(".words.json")
            if words_json.exists():
                with open(words_json, "r", encoding="utf-8") as wf:
                    seg["word_alignments"] = json.load(wf)
        else:
            seg_matches = sorted(audio_dir.glob(f"c{chapter_num:03d}_s{s_idx:04d}_*.wav"))
            if seg_matches:
                chunk_path = seg_matches[0]
                seg_durations[s_idx] = get_audio_duration(chunk_path)
                words_json = chunk_path.with_suffix(".words.json")
                if words_json.exists():
                    with open(words_json, "r", encoding="utf-8") as wf:
                        seg["word_alignments"] = json.load(wf)
            else:
                seg_durations[s_idx] = 4.0

    final_segments = edited_segments if edited_segments else segments
    return vocal_wav, vocal_dur, seg_durations, final_segments
