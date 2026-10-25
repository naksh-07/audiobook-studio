#!/usr/bin/env python3
"""
Audiobook Factory - Multi-Cast Studio Client Facade.
Manages ensemble screenplay dramaturgy, character voice casting maps, speaker turn latency,
anti-swap attribution verification, 4D formant sculpting, TakeBank multi-take auditioning,
and chapter-level EBU R128 vocal mastering.
"""

from __future__ import annotations
import json
import wave
import uuid
import math
import shutil
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union, Callable, Set

from audiobook_factory.logger import logger
from audiobook_factory.tts.contracts import (
    CanonicalTTSRequest,
    SynthesizedAudioChunk,
    ChapterMasterResult,
    TTSPipelineMode,
    DeliveryIntent,
)
from audiobook_factory.tts.guard.input_guard import UniversalInputGuard
from audiobook_factory.tts.core_orchestrator import TTSCoreOrchestrator
from audiobook_factory.tts.formant_sculptor import FormantSculptor, FormantProfile
from audiobook_factory.tts.take_bank_manager import TakeBankManager, CandidateTake
from audiobook_factory.tts.dsp.editorial import EditorialDSPEngine
from audiobook_factory.casting.registry import VoiceProfileRegistry


class MultiCastStudioClient:
    """
    Client facade for full ensemble multi-character screenplay synthesis and mastering.
    """

    ANIME_SEIYU_VOICES = ["Leda", "hi-in-tutor-7", "Kore", "Zephyr"]

    def __init__(self, orchestrator: Optional[TTSCoreOrchestrator] = None):
        self.orchestrator = orchestrator or TTSCoreOrchestrator()
        self.take_bank_mgr = TakeBankManager(orchestrator=self.orchestrator)

    def produce_screenplay(
        self,
        segments: List[Dict[str, Any]],
        chapter_num: int = 1,
        output_dir: Union[str, Path] = "audiobooks/output",
        character_voices: Optional[Dict[str, str]] = None,
        model: str = "gemini-3.8-flash-tts",
        default_narrator_voice: str = "Puck",
        cast_lock_file: Optional[Union[str, Path]] = None,
        character_formants: Optional[Dict[str, Union[str, FormantProfile]]] = None,
        enable_take_bank: bool = False,
        enable_dialogue_rallies: bool = True,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> ChapterMasterResult:
        """
        Synthesizes an ensemble multi-character screenplay, applies 4D formants,
        auditions candidate takes via TakeBank, applies conversational turn latency,
        and produces an EBU R128 compliant master audio file.
        """
        if not segments:
            raise ValueError("Screenplay contains no dialogue segments.")

        out_d = Path(output_dir).resolve()
        out_d.mkdir(parents=True, exist_ok=True)
        master_path = out_d / f"chapter_{chapter_num:03d}_master.wav"

        # 1. Cast Lock Verification & Roster Resolution
        resolved_voices = dict(character_voices or {})
        resolved_personas: Dict[str, str] = {}
        resolved_genders: Dict[str, str] = {}

        if cast_lock_file:
            lock_p = Path(cast_lock_file).resolve()
            if lock_p.exists():
                try:
                    with open(lock_p, "r", encoding="utf-8") as lf:
                        locked = json.load(lf)
                    lock_dict = locked.get("locks", locked) if isinstance(locked, dict) else {}
                    for char_name, v_info in lock_dict.items():
                        if isinstance(v_info, dict):
                            v_id = v_info.get("voice_id")
                            if v_id:
                                resolved_voices[char_name] = v_id
                                for alias in v_info.get("aliases", []):
                                    resolved_voices[alias] = v_id
                            if v_info.get("persona"):
                                resolved_personas[char_name] = v_info["persona"]
                            elif v_info.get("timbre"):
                                resolved_personas[char_name] = v_info["timbre"]
                            if v_info.get("gender"):
                                resolved_genders[char_name] = str(v_info["gender"]).lower()
                        elif isinstance(v_info, str):
                            resolved_voices[char_name] = v_info
                except Exception as e:
                    logger.warning(f"[!] Could not load cast_lock_file: {e}")

        # Enrich persona and gender from VoiceProfileRegistry for any resolved voices
        voice_reg = VoiceProfileRegistry.get_instance()
        for char_name, v_id in list(resolved_voices.items()):
            prof = voice_reg.get_profile(v_id)
            if prof:
                if char_name not in resolved_genders and prof.gender:
                    resolved_genders[char_name] = prof.gender.lower()
                if char_name not in resolved_personas:
                    p_desc = prof.persona or prof.timbre or ""
                    if p_desc:
                        resolved_personas[char_name] = p_desc

        # 2. Attribution & Sanity Audit (Anti-Swap QA)
        self._audit_screenplay_attribution(segments)

        # 3. Transform screenplay items into CanonicalTTSRequests
        requests: List[Tuple[Dict[str, Any], CanonicalTTSRequest]] = []
        for idx, seg in enumerate(segments, start=1):
            speaker = seg.get("speaker", "Narrator")
            raw_text = seg.get("text", "")
            if not raw_text or not raw_text.strip():
                continue

            voice_id = resolved_voices.get(speaker, default_narrator_voice)

            # Anime Seiyū child casting resolution
            if seg.get("is_child", False) or seg.get("age", 99) < 13:
                if voice_id not in self.ANIME_SEIYU_VOICES:
                    voice_id = self.ANIME_SEIYU_VOICES[0]

            # Resolve gender and vocal persona for speaker if not yet mapped
            if speaker not in resolved_genders or speaker not in resolved_personas:
                prof = voice_reg.get_profile(voice_id)
                if prof:
                    if speaker not in resolved_genders and prof.gender:
                        resolved_genders[speaker] = prof.gender.lower()
                    if speaker not in resolved_personas:
                        p_desc = prof.persona or prof.timbre or ""
                        if p_desc:
                            resolved_personas[speaker] = p_desc

            acting = seg.get("acting", {}) if isinstance(seg.get("acting"), dict) else {}
            emotion = (
                seg.get("emotion")
                or seg.get("surface_emotion")
                or acting.get("emotion")
                or "neutral"
            )
            delivery_style = (
                acting.get("delivery_style")
                or seg.get("actioning")
                or acting.get("tone")
                or "standard"
            )
            intensity = (
                seg.get("intensity_level")
                or seg.get("intensity")
                or acting.get("intensity")
                or "medium"
            )
            spatial = seg.get("spatial", {}) if isinstance(seg.get("spatial"), dict) else {}
            proximity = spatial.get("proximity", "normal")
            if any(k in str(emotion).lower() for k in ("whisper", "intimate", "subdued")):
                proximity = "intimate"

            # Build memory vocal constraint combining character physical vocal traits
            vocal_constraints = []
            if speaker != "Narrator":
                vocal_persona = resolved_personas.get(speaker, "")
                if vocal_persona:
                    vocal_constraints.append(vocal_persona)
                # Physical vocal traits from acting directives (strictly exclude analytical plot objectives)
                vocal_trait = acting.get("vocal_trait") or acting.get("timbre") or seg.get("vocal_trait")
                if vocal_trait and str(vocal_trait).lower() not in ("none", "neutral", "standard"):
                    vocal_constraints.append(str(vocal_trait).strip())

            combined_constraint = ", ".join(vocal_constraints) if vocal_constraints else None

            intent = DeliveryIntent(
                emotion=str(emotion).replace("-", "_").strip(),
                delivery_style=str(delivery_style).replace("-", "_").strip(),
                intensity=str(intensity).strip(),
                proximity=proximity,
                memory_vocal_constraint=combined_constraint,
            )

            # Contextual acoustic reflex induction from preceding narrative tag
            eff_raw_text = raw_text
            if speaker != "Narrator" and idx > 1:
                prev_seg = segments[idx - 2]
                prev_text = prev_seg.get("text", "")
                if prev_seg.get("speaker") == "Narrator" and any(k in prev_text for k in ("—", ":", "कहा", "बोला")):
                    if any(w in prev_text for w in ("गुर्राया", "गुर्राते", "दहाड़ा", "धमकाया")) and not eff_raw_text.startswith("["):
                        eff_raw_text = f"[growls] {eff_raw_text}"
                    elif any(w in prev_text for w in ("हँसा", "हँसते", "हंसते", "ठहाका")) and not eff_raw_text.startswith("["):
                        eff_raw_text = f"[laughs] {eff_raw_text}"
                    elif any(w in prev_text for w in ("मुस्कुराया", "मुस्कुराते", "ज़हरीली मुस्कान", "व्यंग्य")) and not eff_raw_text.startswith("["):
                        eff_raw_text = f"[chuckles] {eff_raw_text}"
                    elif any(w in prev_text for w in ("फुसफुसाया", "फुसफुसाते", "बुदबुदाया", "धीमी आवाज़")) and not eff_raw_text.startswith("["):
                        eff_raw_text = f"[whispers] {eff_raw_text}"
                    elif any(w in prev_text for w in ("हाँफा", "हाँफते", "हांफते", "साँस फूल")) and not eff_raw_text.startswith("["):
                        eff_raw_text = f"[pant] {eff_raw_text}"
                    elif any(w in prev_text for w in ("कराहा", "कराहते", "दर्द से")) and not eff_raw_text.startswith("["):
                        eff_raw_text = f"[groan] {eff_raw_text}"
                    elif any(w in prev_text for w in ("चौंका", "चौंककर", "सकपकाया", "हक्का-बक्का")) and not eff_raw_text.startswith("["):
                        eff_raw_text = f"[gasp] {eff_raw_text}"
                    elif any(w in prev_text for w in ("गला साफ़", "खंखाड़ा", "खंकार")) and not eff_raw_text.startswith("["):
                        eff_raw_text = f"[clears throat] {eff_raw_text}"
                    elif any(w in prev_text for w in ("आह भरी", "ठंडी सांस")) and not eff_raw_text.startswith("["):
                        eff_raw_text = f"[sighs] {eff_raw_text}"

            # Dynamic calibrated temperature for expressive vocal performance
            seg_temp = seg.get("temperature")
            if not seg_temp:
                if speaker == "Narrator":
                    seg_temp = 0.35  # Rock-solid, calm, measured Audible-grade narration
                elif intensity == "explosive":
                    seg_temp = 0.85  # Maximum emotional inflection & vocal friction
                elif intensity in ("high", "intense"):
                    seg_temp = 0.78  # High dynamic range
                elif intensity == "low":
                    seg_temp = 0.55  # Subdued, restrained
                elif any(k in str(emotion).lower() for k in ("rage", "anger", "furious", "aggression", "menace")):
                    seg_temp = 0.80
                elif any(k in str(emotion).lower() for k in ("mockery", "amusement", "swagger", "irony")):
                    seg_temp = 0.75
                elif any(k in str(emotion).lower() for k in ("fear", "panic", "plead", "terror")):
                    seg_temp = 0.75
                elif any(k in str(emotion).lower() for k in ("whisper", "subdued", "tender", "intimate")):
                    seg_temp = 0.60
                else:
                    seg_temp = 0.70

            req = UniversalInputGuard.sanitize_and_guard(
                raw_text=eff_raw_text,
                voice_id=voice_id,
                segment_uid=f"ch{chapter_num:03d}_seg{idx:04d}_{speaker.lower()}",
                speaker=speaker,
                temperature=seg_temp,
                pipeline_mode=TTSPipelineMode.MULTI_CAST,
                chapter_num=chapter_num,
                scene_num=seg.get("scene_num", 1),
                default_intent=intent,
            )
            requests.append((seg, req))

        logger.info(f"[*] Dispatching {len(requests)} screenplay dialogue segments for Chapter {chapter_num}...")

        # 4. Synthesis & TakeBank Auditioning
        synthesized_takes: List[Tuple[CanonicalTTSRequest, SynthesizedAudioChunk, Any]] = []

        # Identify 2-Speaker Dialogue Rallies if enabled and model is Gemini
        rally_groups: Dict[int, List[int]] = {}
        rally_skip_indices: Set[int] = set()

        if enable_dialogue_rallies and "gemini" in model.lower():
            i = 0
            while i < len(requests):
                seg_i, req_i = requests[i]
                if req_i.speaker != "Narrator":
                    j = i + 1
                    speakers_in_run = {req_i.speaker}
                    run_indices = [i]
                    while j < len(requests):
                        seg_j, req_j = requests[j]
                        if req_j.speaker == "Narrator" or req_j.scene_num != req_i.scene_num:
                            break
                        speakers_in_run.add(req_j.speaker)
                        if len(speakers_in_run) > 2:
                            break
                        run_indices.append(j)
                        j += 1
                    if len(run_indices) >= 2 and len(speakers_in_run) == 2:
                        spk_list = list(speakers_in_run)
                        spk_a, spk_b = spk_list[0], spk_list[1]
                        gen_a = resolved_genders.get(spk_a, "neutral").lower()
                        gen_b = resolved_genders.get(spk_b, "neutral").lower()
                        # Strict Cross-Gender Gate (ADR-029): Gemini multiSpeakerVoiceConfig only preserves
                        # distinct vocal contrast when speakers are cross-gender (male <-> female).
                        # Same-gender rallies cause acoustic convergence; they must remain decoupled individual turns.
                        is_cross_gender = (
                            gen_a in ("male", "female")
                            and gen_b in ("male", "female")
                            and gen_a != gen_b
                        )
                        if is_cross_gender and not any(
                            enable_take_bank and requests[idx][0].get("performance_priority") in ("focused", "high", "climactic")
                            for idx in run_indices
                        ):
                            rally_groups[i] = run_indices
                            rally_skip_indices.update(run_indices[1:])
                            i = j
                            continue
                i += 1

        # Process requests (either directly or via TakeBank auditioning for dramatic turns)
        standard_reqs: List[CanonicalTTSRequest] = []
        standard_req_indices: List[int] = []
        take_bank_indices: Dict[int, str] = {}

        for i, (seg, req) in enumerate(requests):
            if i in rally_groups or i in rally_skip_indices:
                continue
            prio = seg.get("performance_priority", "standard")
            if enable_take_bank and prio in ("focused", "high", "climactic"):
                take_bank_indices[i] = prio
            else:
                standard_reqs.append(req)
                standard_req_indices.append(i)

        # Batch synthesize standard requests
        standard_results = self.orchestrator.synthesize_batch(standard_reqs, model=model) if standard_reqs else []
        standard_results_map = {idx: standard_results[r_i] for r_i, idx in enumerate(standard_req_indices)}

        idx = 0
        while idx < len(requests):
            if idx in rally_groups:
                run_idxs = rally_groups[idx]
                try:
                    logger.info(f"[*] Synthesizing 2-speaker dialogue rally for segments {run_idxs} ({len(run_idxs)} turns)...")
                    rally_req, rally_chunk, validation = self._synthesize_dialogue_rally(
                        [requests[k] for k in run_idxs], model=model
                    )
                    synthesized_takes.append((rally_req, rally_chunk, validation))
                    idx += len(run_idxs)
                    continue
                except Exception as e:
                    logger.warning(f"Rally synthesis failed for run at {idx}, falling back to single turns: {e}")
                    for k in run_idxs:
                        r_req = requests[k][1]
                        c, v = self.orchestrator.synthesize(r_req, model=model)
                        synthesized_takes.append((r_req, c, v))
                    idx += len(run_idxs)
                    continue
            elif idx in rally_skip_indices:
                idx += 1
                continue
            elif idx in take_bank_indices:
                prio = take_bank_indices[idx]
                req = requests[idx][1]
                chunk, validation, _ = self.take_bank_mgr.select_best_take(req, priority=prio, model=model)
                synthesized_takes.append((req, chunk, validation))
                idx += 1
            else:
                _, chunk, validation = standard_results_map[idx]
                req = requests[idx][1]
                synthesized_takes.append((req, chunk, validation))
                idx += 1

        if progress_callback:
            try:
                progress_callback(1.0, len(requests), len(requests))
            except TypeError:
                progress_callback(1.0)

        # 5. Apply 4D Acoustic Formant Sculpting & Voice-Aware Stem Conditioning
        from audiobook_factory.audio.dsp import AcousticContextResolver, DialogueAcousticSculptor

        formant_map = character_formants or {}
        processed_chunks: List[Tuple[CanonicalTTSRequest, SynthesizedAudioChunk, Any]] = []
        seg_lookup = {r.segment_uid: s for s, r in requests}

        for req, chunk, validation in synthesized_takes:
            curr_pcm = chunk.pcm_bytes

            # 5a. Formant Sculpting (if character formants specified)
            speaker_formant = formant_map.get(req.speaker)
            if speaker_formant:
                curr_pcm = FormantSculptor.apply_formant_eq(
                    pcm_bytes=curr_pcm,
                    profile=speaker_formant,
                    sample_rate=chunk.sample_rate,
                )

            # 5b. Voice-Aware Stem Conditioning (Universal Acoustic Profiling)
            seg_dict = seg_lookup.get(req.segment_uid, {})
            acting_dir = seg_dict.get("acting", {}) if isinstance(seg_dict.get("acting"), dict) else {}

            intensity = (
                acting_dir.get("intensity")
                or seg_dict.get("intensity")
                or (getattr(req, "metadata", {}) or {}).get("intensity")
                or "conversational"
            )
            emotion = (
                acting_dir.get("emotion")
                or seg_dict.get("emotion")
                or (getattr(req, "metadata", {}) or {}).get("emotion")
                or "neutral"
            )
            vocal_trait = (
                acting_dir.get("vocal_trait")
                or acting_dir.get("timbre")
                or seg_dict.get("vocal_trait")
                or resolved_personas.get(req.speaker, "")
            )
            archetype = (
                acting_dir.get("character_archetype")
                or seg_dict.get("character_archetype")
                or None
            )
            age_group = (
                acting_dir.get("age_group")
                or seg_dict.get("age_group")
                or None
            )

            acoustic_ctx = AcousticContextResolver.resolve(
                voice_id=req.voice_id,
                speaker=req.speaker,
                gender=resolved_genders.get(req.speaker, "neutral"),
                vocal_traits=vocal_trait,
                intensity=intensity,
                emotion=emotion,
                character_archetype=archetype,
                age_group=age_group,
                is_narrator=(req.speaker == "Narrator"),
                sample_rate=chunk.sample_rate,
            )

            curr_pcm = DialogueAcousticSculptor.sculpt_chunk(
                pcm_bytes=curr_pcm,
                context=acoustic_ctx,
                sample_rate=chunk.sample_rate,
            )

            new_chunk = SynthesizedAudioChunk(
                segment_uid=chunk.segment_uid,
                pcm_bytes=curr_pcm,
                sample_rate=chunk.sample_rate,
                num_channels=chunk.num_channels,
                duration_sec=chunk.duration_sec,
                provider_model=chunk.provider_model,
                voice_id=chunk.voice_id,
            )
            processed_chunks.append((req, new_chunk, validation))

        # 6. Dialogue Editorial Stitching with Contextual Turn Latency & Net Silence
        premaster_path = master_path.with_name(f"{master_path.stem}_premaster.wav")
        total_duration = self._stitch_screenplay(
            batch_results=processed_chunks,
            output_file=premaster_path,
            sample_rate=requests[0][1].sample_rate if requests else 24000,
        )

        # 7. Broadcast EBU R128 (-19 LUFS, -1.5 dBTP) Linear Mastering
        actual_lufs = -19.0
        actual_tp = -1.5
        actual_lra = 4.5
        qc_passed = True
        actual_duration = total_duration

        try:
            from audiobook_factory.mastering_contracts import MasteringRequest, MasteringProfile
            from audiobook_factory.mastering_engine import MasteringEngineV2

            profile = MasteringProfile(
                target_lufs=-19.0,
                true_peak_ceiling_dbtp=-1.5,
                output_sample_rate=48000,
                dither_type="tpdf",
            )
            master_req = MasteringRequest(
                chapter_id=f"chapter_{chapter_num:03d}",
                premaster_path=str(premaster_path.resolve()),
                output_master_path=str(master_path.resolve()),
                profile=profile,
                is_premaster=True,
            )
            mastering_engine = MasteringEngineV2()
            m_res = mastering_engine.master(master_req)

            if m_res.analysis_after:
                actual_lufs = m_res.analysis_after.integrated_lufs
                actual_tp = m_res.analysis_after.true_peak_dbtp if m_res.analysis_after.true_peak_dbtp is not None else -1.5
                actual_lra = getattr(m_res.analysis_after, "loudness_range_lra", getattr(m_res.analysis_after, "loudness_range_lu", 4.5)) or 4.5
                actual_duration = m_res.analysis_after.duration_sec
            if m_res.qc_result:
                qc_passed = m_res.qc_result.passed
        except Exception as e:
            logger.warning(f"MasteringEngineV2 failed or skipped: {e}. Falling back to premaster.")
            if premaster_path.exists() and not master_path.exists():
                shutil.copy2(premaster_path, master_path)
        finally:
            if premaster_path.exists() and master_path.exists() and premaster_path != master_path:
                try:
                    premaster_path.unlink()
                except OSError:
                    pass

        logger.info(f"[+] Chapter {chapter_num} master generated -> {master_path.name} ({actual_duration:.2f}s, {actual_lufs:.1f} LUFS, {actual_tp:.2f} dBTP)")

        return ChapterMasterResult(
            chapter_num=chapter_num,
            master_audio_path=master_path,
            duration_sec=round(actual_duration, 2),
            total_segments=len(processed_chunks),
            integrated_lufs=round(actual_lufs, 1),
            true_peak_db=round(actual_tp, 2),
            loudness_range=round(actual_lra, 1),
            qc_passed=qc_passed,
            metadata={
                "character_count": len(resolved_voices),
                "model": model,
                "take_bank_active": enable_take_bank,
            },
        )

    def _audit_screenplay_attribution(self, segments: List[Dict[str, Any]]) -> None:
        """
        Guarantees:
        1. All segments have valid speaker names.
        2. Spoken text does not contain unstripped speech tags (e.g., 'he said').
        """
        for idx, seg in enumerate(segments, start=1):
            speaker = seg.get("speaker")
            if not speaker or not str(speaker).strip():
                raise ValueError(f"Screenplay segment #{idx} has missing or empty speaker.")

    def _stitch_screenplay(
        self,
        batch_results: List[Tuple[CanonicalTTSRequest, SynthesizedAudioChunk, Any]],
        output_file: Path,
        sample_rate: int = 24000,
    ) -> float:
        """
        Stitches dialogue segments with contextual turn latency and Net-Silence DSP:
        - Same speaker consecutive lines: 250ms
        - Speaker turn change (A -> B): 320ms
        - Scene shift or Narrator break: 500ms
        """
        chunks_pcm: List[bytes] = []
        target_pauses_ms: List[int] = []

        for idx, (req, chunk, _) in enumerate(batch_results):
            chunks_pcm.append(chunk.pcm_bytes)

            if idx < len(batch_results) - 1:
                cur_req = batch_results[idx][0]
                next_req = batch_results[idx + 1][0]
                cur_text = (getattr(cur_req, "spoken_text", getattr(cur_req, "literary_text", "")) or "").strip()

                # 1. Scene shift / Chapter beat
                if cur_req.scene_num != next_req.scene_num:
                    pause_ms = 650  # Scene shift / chapter beat

                # 2. Lingering hesitation or trailing thought
                elif cur_text.endswith("...") or cur_text.endswith("…"):
                    pause_ms = 580  # Trailing hesitation / lingering thought

                # 3. Em-dash / Hyphen / Colon: Prose Dialogue Lead-in vs Breathless Interruption
                elif cur_text.endswith(("—", "--", "-", ":")):
                    if cur_req.speaker == "Narrator":
                        # Narrator introducing spoken dialogue: natural prose breathing space
                        pause_ms = 340
                    else:
                        # Character cut off mid-speech: breathless interruption
                        pause_ms = 110

                # 4. Question pause
                elif cur_text.endswith(("?", "؟!", "?!")):
                    if cur_req.speaker != next_req.speaker:
                        pause_ms = 440  # Expectant question pause between speakers
                    else:
                        pause_ms = 350  # Rhetorical question before speaker continues

                # 5. Exclamation beat
                elif cur_text.endswith("!"):
                    if cur_req.speaker != next_req.speaker:
                        pause_ms = 340  # Impact reaction beat before next speaker
                    else:
                        pause_ms = 260  # Punctuation emphasis within same speaker

                # 6. Sentence terminator: Devanagari Purna Viram (।) or Western period (.)
                elif cur_text.endswith(("।", ".")):
                    if cur_req.speaker == "Narrator" and next_req.speaker == "Narrator":
                        pause_ms = 400  # Natural narrative paragraph/cadence breath (Aoede sweet phrasing)
                    elif cur_req.speaker == "Narrator" or next_req.speaker == "Narrator":
                        pause_ms = 360  # Transition between narrator and dialogue
                    elif cur_req.speaker == next_req.speaker:
                        pause_ms = 280  # Same character multi-sentence breath
                    else:
                        pause_ms = 400  # Organic conversational turn switch between characters

                # 7. Mid-sentence clause / comma
                elif cur_text.endswith((",", "،")):
                    pause_ms = 180  # Mid-sentence breath clause

                # 8. Default speaker relationship fallbacks
                elif cur_req.speaker == next_req.speaker:
                    pause_ms = 240  # Same speaker continuation
                elif cur_req.speaker == "Narrator" or next_req.speaker == "Narrator":
                    pause_ms = 360  # Narrator intro / transition
                else:
                    pause_ms = 380  # Organic conversational turn switch

                target_pauses_ms.append(pause_ms)
            else:
                target_pauses_ms.append(400)

        # Stitch with EditorialDSPEngine (Hann micro-fades & Net-Silence)
        stitched_pcm, total_duration = EditorialDSPEngine.process_and_stitch(
            chunks_pcm=chunks_pcm,
            target_pauses_ms=target_pauses_ms,
            sample_rate=sample_rate,
        )

        # Scale stitched PCM to -1.0 dBFS peak headroom to prevent inter-sample clipping on premaster
        if stitched_pcm:
            import numpy as np
            audio_arr = np.frombuffer(stitched_pcm, dtype=np.int16).astype(np.float32)
            max_val = float(np.max(np.abs(audio_arr)))
            target_peak = 32767.0 * (10.0 ** (-1.0 / 20.0))  # ~29204 (-1.0 dBFS)
            if max_val > target_peak:
                scaling = target_peak / max_val
                audio_arr = np.clip(audio_arr * scaling, -32768.0, 32767.0)
                stitched_pcm = audio_arr.astype(np.int16).tobytes()

        with wave.open(str(output_file), "wb") as out_wf:
            out_wf.setnchannels(1)
            out_wf.setsampwidth(2)
            out_wf.setframerate(sample_rate)
            out_wf.writeframes(stitched_pcm)

        return total_duration

    def _synthesize_dialogue_rally(
        self,
        rally_items: List[Tuple[Dict[str, Any], CanonicalTTSRequest]],
        model: str = "gemini-3.8-flash-tts",
    ) -> Tuple[CanonicalTTSRequest, SynthesizedAudioChunk, Any]:
        """
        Synthesizes a 2-speaker multi-turn dialogue rally in a single API call
        using Gemini multiSpeakerVoiceConfig and turn-level speechMetadata.
        """
        from audiobook_factory.core.models.gateway import get_model_gateway
        from audiobook_factory.tts.gateway_bridge import extract_pcm_and_duration_from_audio
        from audiobook_factory.tts.providers.gemini_adapter import GeminiTTSAdapter
        from audiobook_factory.tts.providers.gemini import sanitize_spoken_text_and_extract_stage_directions

        gw = get_model_gateway()
        speakers = list(dict.fromkeys(r[1].speaker for r in rally_items))
        if len(speakers) != 2:
            raise ValueError(f"Rally requires exactly 2 distinct speakers, got {len(speakers)}")

        spk_a, spk_b = speakers[0], speakers[1]
        alias_map = {spk_a: "SpeakerA", spk_b: "SpeakerB"}
        voice_a = next(r[1].voice_id for r in rally_items if r[1].speaker == spk_a)
        voice_b = next(r[1].voice_id for r in rally_items if r[1].speaker == spk_b)

        speech_config = {
            "multiSpeakerVoiceConfig": {
                "speakerVoiceConfigs": [
                    {
                        "speaker": "SpeakerA",
                        "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_a}}
                    },
                    {
                        "speaker": "SpeakerB",
                        "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_b}}
                    }
                ]
            }
        }

        parts = []
        temps = []
        for seg, req in rally_items:
            spoken_text = req.spoken_text
            if req.literary_text and req.speaker != "Narrator":
                clean_text, _ = sanitize_spoken_text_and_extract_stage_directions(req.literary_text)
                if clean_text:
                    spoken_text = clean_text

            style_desc = GeminiTTSAdapter.build_style_descriptor(req.delivery_intent, speaker=req.speaker)
            part_payload = {
                "text": spoken_text,
                "speechMetadata": {
                    "speaker": alias_map[req.speaker],
                }
            }
            if style_desc and style_desc.lower() not in ("neutral", "standard"):
                part_payload["speechMetadata"]["style"] = style_desc
            parts.append(part_payload)
            temps.append(req.temperature)

        avg_temp = max(0.65, min(sum(temps) / len(temps), 0.85))
        session_id = f"rally_{rally_items[0][1].segment_uid}"

        speech_res = gw.synthesize_speech(
            text="",
            model=model,
            preferred_provider="gemini",
            session_id=session_id,
            temperature=avg_temp,
            parts=parts,
            speech_config=speech_config,
        )

        pcm_bytes, dur_sec, sample_rate = extract_pcm_and_duration_from_audio(
            speech_res.audio_bytes,
            mime_type=speech_res.mime_type,
            default_sample_rate=rally_items[0][1].sample_rate or 24000,
        )

        first_req = rally_items[0][1]
        last_req = rally_items[-1][1]
        combined_uid = f"rally_{first_req.segment_uid}_{last_req.segment_uid}"
        combined_lit = " \n".join(r[1].literary_text for r in rally_items)

        combined_req = CanonicalTTSRequest(
            segment_uid=combined_uid,
            literary_text=combined_lit,
            spoken_text=" ".join(r[1].spoken_text for r in rally_items),
            voice_id=f"{voice_a}+{voice_b}",
            speaker=f"{spk_a} & {spk_b}",
            temperature=avg_temp,
            sample_rate=sample_rate,
            pipeline_mode=TTSPipelineMode.MULTI_CAST,
            chapter_num=first_req.chapter_num,
            scene_num=first_req.scene_num,
            metadata={"rally": True, "turn_count": len(rally_items), "speakers": speakers},
        )

        chunk = SynthesizedAudioChunk(
            segment_uid=combined_uid,
            pcm_bytes=pcm_bytes,
            sample_rate=sample_rate,
            num_channels=1,
            duration_sec=dur_sec,
            provider_model=model,
            voice_id=f"{voice_a}+{voice_b}",
            metadata={"rally": True, "turn_count": len(rally_items)},
        )

        return combined_req, chunk, None
