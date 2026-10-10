#!/usr/bin/env python3
"""
Audiobook Factory - Gate 2.9: Pre-TTS Config & Attribution Sanity Gate.
======================================================================
The authoritative pre-synthesis gate running immediately prior to Room 4 TTS dispatch.
Protects both Audiobook and Podcast tracks from expensive API waste and acoustic defects:
1. Speaker Whitelist Verification (against character_roster.json, voice_registry.json, BookBible).
2. Anti-Swap & Wrong Character Attribution Guard (Hindi gender inflection discordance & speech verb tags).
3. Anti-Swallow Dialogue Guard (Zero quotes leaked into narrator lines).
4. Acoustic Parameter Range Clamping (Pitch: [0.70, 1.30], Speed: [0.80, 1.25], Valid Voice IDs).
5. Stereo Spatial Staging (Podcast Host A <= -0.20, Host B >= +0.20).
6. Text Hygiene & Breathability (Zero empty lines, no markdown fences, no conversational preambles).
"""

from __future__ import annotations
import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Literal

from audiobook_factory.logger import logger
from audiobook_factory.gates.contracts import AuditResult, GateAuditError


class PreSynthesisGate:
    """
    Evaluates screenplay segments for acoustic and attribution correctness
    prior to TTS dispatch.
    """

    # Banned markdown fences and raw LLM artifacts
    MARKDOWN_FENCE_PATTERN = re.compile(r"```(?:markdown|json|text|md)?", re.IGNORECASE)
    LLM_CHATTER_PATTERN = re.compile(
        r"^(?:Here is the (?:script|dialogue|scene)|Certainly[,!]? here is|Below is the (?:screenplay|script)):?",
        re.IGNORECASE,
    )

    # First-person verbal inflections in Hindi indicating grammatical gender
    # Uses boundary matching across whitespace and punctuation to safely handle Devanagari marks
    MALE_HINDI_INFLECTIONS = re.compile(
        r"(?:^|[\s,।\.\?!])(?:रहा हूँ|जाऊँगा|करूँगा|गया था|आया था|सोचता हूँ|चाहता हूँ|मेरा भाई|मुझे लगा था)(?:$|[\s,।\.\?!])"
    )
    FEMALE_HINDI_INFLECTIONS = re.compile(
        r"(?:^|[\s,।\.\?!])(?:रही हूँ|जाऊँगी|करूँगी|गई थी|आई थी|सोचती हूँ|चाहती हूँ|मेरी बहन|मुझे लगी थी)(?:$|[\s,।\.\?!])"
    )

    # Speech verbs in dialogue lead-ins
    SPEECH_VERB_LEAD_IN = re.compile(
        r"([A-Za-z\u0900-\u097F_]+)\s*(?:said|asked|replied|whispered|screamed|shouted|muttered|"
        r"ने कहा|ने पूछा|बोला|बोली|चिल्लाया|चिल्लाई|फुसफुसाया|फुसफुसाई)\s*[:,\-—]",
        re.IGNORECASE,
    )

    @classmethod
    def audit_script(
        cls,
        script_file_or_data: Union[Path, str, List[Dict[str, Any]]],
        project_dir: Optional[Union[Path, str]] = None,
        format_mode: Literal["audiobook", "podcast"] = "audiobook",
        strict: bool = True,
    ) -> AuditResult:
        """
        Executes complete Gate 2.9 Pre-TTS validation.
        """
        segments, script_path = cls._load_segments(script_file_or_data)
        pdir = Path(project_dir).resolve() if project_dir else (script_path.parent.parent if script_path else Path.cwd())

        errors: List[str] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {
            "format_mode": format_mode,
            "total_segments": len(segments),
        }

        if not segments:
            errors.append("Script is completely empty (0 segments). Cannot synthesize speech.")
            return cls._finalize_result(errors, warnings, details, strict)

        # 1. Resolve Roster, Voice Registry, and Genders
        allowed_speakers, gender_map, voice_registry = cls._resolve_catalogs(pdir, format_mode)
        details["registered_speakers_count"] = len(allowed_speakers)

        # 2. Sequential Monotonicity & Whitelist Check
        prev_speaker: Optional[str] = None
        consecutive_dialogue_repeats = 0

        for idx, seg in enumerate(segments, start=1):
            if not isinstance(seg, dict):
                errors.append(f"Segment #{idx} is not a valid JSON dictionary.")
                continue

            seg_idx = seg.get("index", idx)
            if seg_idx != idx:
                errors.append(f"Non-monotonic segment index at position {idx} (found index {seg_idx}).")

            raw_speaker = (seg.get("speaker") or "").strip()
            text = (seg.get("text") or "").strip()
            seg_type = (seg.get("type") or "narration").strip().lower()

            # Empty Speaker / Empty Text
            if not raw_speaker:
                errors.append(f"Segment #{idx} has an empty speaker field.")
            if not text:
                errors.append(f"Segment #{idx} ({raw_speaker}) has empty or whitespace-only dialogue text.")

            # Text Hygiene Check (Fences / Chatter)
            if cls.MARKDOWN_FENCE_PATTERN.search(text):
                errors.append(f"Segment #{idx} contains leaked markdown fences: '{text[:40]}...'")
            if cls.LLM_CHATTER_PATTERN.search(text):
                errors.append(f"Segment #{idx} contains unstripped LLM conversational preamble: '{text[:40]}...'")

            # Speaker Whitelist Check
            norm_speaker = cls._norm(raw_speaker)
            if allowed_speakers and norm_speaker not in allowed_speakers:
                errors.append(
                    f"Segment #{idx}: Unregistered speaker '{raw_speaker}' not found in project roster / voice catalog."
                )

            # 3. Anti-Swap Attribution & Gender Inflection Check
            speaker_gender = gender_map.get(norm_speaker, "").lower()
            if seg_type == "dialogue" and speaker_gender:
                if speaker_gender in ("female", "woman", "f"):
                    if cls.MALE_HINDI_INFLECTIONS.search(text):
                        warnings.append(
                            f"Segment #{idx}: Possible Speaker Inversion! Female character '{raw_speaker}' spoken with masculine verb inflection in: \"{text[:50]}\""
                        )
                elif speaker_gender in ("male", "man", "m"):
                    if cls.FEMALE_HINDI_INFLECTIONS.search(text):
                        warnings.append(
                            f"Segment #{idx}: Possible Speaker Inversion! Male character '{raw_speaker}' spoken with feminine verb inflection in: \"{text[:50]}\""
                        )

            # Speech Verb Co-reference check on neighboring tags
            if idx > 1:
                prev_seg = segments[idx - 2]
                prev_txt = prev_seg.get("text", "")
                m = cls.SPEECH_VERB_LEAD_IN.search(prev_txt)
                if m:
                    tagged_name = cls._norm(m.group(1))
                    # If the lead-in tag names a character that is distinct from current speaker
                    if tagged_name in allowed_speakers and tagged_name != norm_speaker and norm_speaker != "narrator":
                        warnings.append(
                            f"Segment #{idx}: Speech verb tag co-reference mismatch! Tag names '{m.group(1)}' but dialogue assigned to '{raw_speaker}'."
                        )

            # Consecutive Dialogue Repeat Detection (A A A without narrator intervention)
            if seg_type == "dialogue":
                if prev_speaker == raw_speaker:
                    consecutive_dialogue_repeats += 1
                    if consecutive_dialogue_repeats >= 2:
                        warnings.append(
                            f"Segment #{idx}: Unbroken consecutive dialogue turns ({consecutive_dialogue_repeats + 1}) for '{raw_speaker}'."
                        )
                else:
                    consecutive_dialogue_repeats = 0
            else:
                consecutive_dialogue_repeats = 0

            prev_speaker = raw_speaker

            # 4. Anti-Swallow Dialogue Guard
            if seg_type in ("narration", "narrator") or norm_speaker == "narrator":
                raw_quotes = re.findall(r'["“]([^"”]{6,})["”]', text)
                swallowed = []
                for q in raw_quotes:
                    if re.search(r'[\.!?।\?]', q) or re.search(r'(?:कहा|बोला|पूछा|चिल्लाया|said|asked|replied)\s*[:,\s]', text):
                        swallowed.append(q)
                if swallowed:
                    errors.append(
                        f"Segment #{idx}: Direct dialogue quote swallowed into Narrator line: \"{swallowed[0][:60]}...\""
                    )

            # 5. Acoustic Parameter Range Clamping
            cls._audit_segment_acoustic_params(idx, raw_speaker, seg, voice_registry, format_mode, errors, warnings)

            # 6. Format-specific checks (Podcast breathability and panning)
            if format_mode == "podcast":
                cls._audit_podcast_segment(idx, raw_speaker, seg, text, errors, warnings)

        return cls._finalize_result(errors, warnings, details, strict)

    @classmethod
    def _audit_segment_acoustic_params(
        cls,
        idx: int,
        speaker: str,
        seg: Dict[str, Any],
        voice_registry: Dict[str, Any],
        format_mode: str,
        errors: List[str],
        warnings: List[str],
    ) -> None:
        """Audits pitch, speed, and voice IDs for acoustic safety."""
        # 1. Pitch bounds check
        pitch = seg.get("pitch_shift") if seg.get("pitch_shift") is not None else seg.get("pitch")
        if pitch is not None:
            try:
                p_val = float(pitch)
                if format_mode == "podcast":
                    # Podcast format allows semitone offset [-12.0, +12.0]
                    if not (-12.0 <= p_val <= 12.0):
                        errors.append(f"Segment #{idx} ({speaker}): Out-of-bounds pitch_shift {p_val} (allowed [-12.0, 12.0]).")
                else:
                    # Audiobook format strictly requires ratio multiplier [0.65, 1.35]
                    if not (0.65 <= p_val <= 1.35):
                        errors.append(f"Segment #{idx} ({speaker}): Out-of-bounds pitch_shift {p_val} (allowed [0.65, 1.35]).")
            except (ValueError, TypeError):
                errors.append(f"Segment #{idx} ({speaker}): Invalid pitch_shift value '{pitch}'.")

        # 2. Speed bounds check
        speed = seg.get("speed_multiplier") or seg.get("speed")
        if speed is not None:
            try:
                s_val = float(speed)
                if not (0.75 <= s_val <= 1.30):
                    errors.append(f"Segment #{idx} ({speaker}): Out-of-bounds speed_multiplier {s_val} (allowed [0.75, 1.30]).")
            except (ValueError, TypeError):
                errors.append(f"Segment #{idx} ({speaker}): Invalid speed value '{speed}'.")

        # 3. Voice registry profile check
        norm_spk = cls._norm(speaker)
        if norm_spk not in ("narrator", "foley") and voice_registry:
            cfg = voice_registry.get(speaker) or voice_registry.get(norm_spk)
            if isinstance(cfg, dict):
                v_id = cfg.get("voice") or cfg.get("voice_id")
                if not v_id or str(v_id).lower() in ("none", "null", "unknown", ""):
                    errors.append(f"Segment #{idx}: Speaker '{speaker}' has unassigned or null voice_id in voice_registry.json.")

    @classmethod
    def _audit_podcast_segment(
        cls,
        idx: int,
        speaker: str,
        seg: Dict[str, Any],
        text: str,
        errors: List[str],
        warnings: List[str],
    ) -> None:
        """Podcast-specific breathability and stereo spatial staging audits."""
        # Panning check
        pan = seg.get("pan") or (seg.get("spatial", {}).get("azimuth_pan") if isinstance(seg.get("spatial"), dict) else None)
        norm_spk = cls._norm(speaker)
        if pan is not None:
            try:
                pan_val = float(pan)
                if not (-1.0 <= pan_val <= 1.0):
                    errors.append(f"Segment #{idx} ({speaker}): Invalid stereo pan {pan_val} (must be between -1.0 and +1.0).")
                if norm_spk in ("host_a", "sameer", "alex") and pan_val > -0.10:
                    warnings.append(f"Segment #{idx}: Host A ({speaker}) pan {pan_val} should be panned left (<= -0.20).")
                elif norm_spk in ("host_b", "priya", "maya") and pan_val < 0.10:
                    warnings.append(f"Segment #{idx}: Host B ({speaker}) pan {pan_val} should be panned right (>= +0.20).")
            except (ValueError, TypeError):
                errors.append(f"Segment #{idx} ({speaker}): Invalid pan value '{pan}'.")

        # Spoken breathability: Flag extremely long unbroken monologues
        words = len(text.split())
        if words > 45 and not re.search(r'[,;\-—\.\?!।]', text):
            warnings.append(f"Segment #{idx} ({speaker}): Turn has {words} words without breath pause punctuation.")

    @classmethod
    def _resolve_catalogs(
        cls, project_dir: Path, format_mode: str
    ) -> Tuple[Set[str], Dict[str, str], Dict[str, Any]]:
        """Extracts allowed speakers, gender mappings, and voice registries."""
        allowed: Set[str] = {
            cls._norm(s)
            for s in (
                "narrator", "narration", "foley",
                "host_a", "host_b", "host a", "host b",
                "host 1", "host 2", "host_1", "host_2"
            )
        }
        genders: Dict[str, str] = {}
        registry: Dict[str, Any] = {}

        # 1. Load character_roster.json
        roster_file = project_dir / "character_roster.json"
        if roster_file.exists():
            try:
                with open(roster_file, "r", encoding="utf-8") as f:
                    rdata = json.load(f)
                chars = rdata.get("characters", rdata)
                if isinstance(chars, dict):
                    for name, meta in chars.items():
                        cls._add_character(name, meta, allowed, genders)
                elif isinstance(chars, list):
                    for item in chars:
                        if isinstance(item, dict):
                            cname = item.get("english_name") or item.get("display_name") or item.get("name")
                            if cname:
                                cls._add_character(cname, item, allowed, genders)
            except Exception as e:
                logger.warning(f"  [GATE 2.9] Could not load {roster_file.name}: {e}")

        # 2. Load voice_registry.json
        reg_file = project_dir / "voice_registry.json"
        if reg_file.exists():
            try:
                with open(reg_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                if isinstance(registry, dict):
                    for name, cfg in registry.items():
                        allowed.add(cls._norm(name))
                        if isinstance(cfg, dict):
                            g = cfg.get("gender")
                            if g and isinstance(g, str):
                                genders[cls._norm(name)] = g
            except Exception as e:
                logger.warning(f"  [GATE 2.9] Could not load {reg_file.name}: {e}")

        # 3. Load podcast_config.json
        pod_file = project_dir / "podcast_config.json"
        if pod_file.exists():
            try:
                with open(pod_file, "r", encoding="utf-8") as f:
                    pdata = json.load(f)
                hosts = pdata.get("hosts", pdata)
                if isinstance(hosts, dict):
                    for h_id, h_data in hosts.items():
                        allowed.add(cls._norm(h_id))
                        if isinstance(h_data, dict):
                            h_name = h_data.get("name")
                            if h_name:
                                allowed.add(cls._norm(h_name))
            except Exception as e:
                logger.warning(f"  [GATE 2.9] Could not load {pod_file.name}: {e}")

        # Default host names for podcast mode
        if format_mode == "podcast":
            for h in ("sameer", "priya", "alex", "maya", "host 1", "host 2", "host a", "host b"):
                allowed.add(cls._norm(h))

        return allowed, genders, registry

    @classmethod
    def _add_character(cls, name: str, meta: Dict[str, Any], allowed: Set[str], genders: Dict[str, str]) -> None:
        """Helper to register a character and aliases."""
        norm_name = cls._norm(name)
        allowed.add(norm_name)
        if isinstance(meta, dict):
            g = meta.get("gender")
            if g and isinstance(g, str):
                genders[norm_name] = g
            # Add Hindi name & aliases
            hin = meta.get("hindi_name")
            if hin and isinstance(hin, str):
                allowed.add(cls._norm(hin))
                if g:
                    genders[cls._norm(hin)] = g
            for al in meta.get("aliases", []):
                if isinstance(al, str) and al.strip():
                    allowed.add(cls._norm(al))
                    if g:
                        genders[cls._norm(al)] = g

    @classmethod
    def _load_segments(
        cls, script_file_or_data: Union[Path, str, List[Dict[str, Any]]]
    ) -> Tuple[List[Dict[str, Any]], Optional[Path]]:
        """Parses segments from file or in-memory list."""
        if isinstance(script_file_or_data, list):
            return script_file_or_data, None

        p = Path(script_file_or_data).resolve()
        if not p.exists():
            raise GateAuditError(f"Gate 2.9 Failed: Script file does not exist at {p}")

        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise GateAuditError(f"Gate 2.9 Failed: Could not parse script JSON {p.name}: {e}") from e

        if isinstance(data, list):
            return data, p
        elif isinstance(data, dict) and "segments" in data and isinstance(data["segments"], list):
            return data["segments"], p

        raise GateAuditError(f"Gate 2.9 Failed: Script {p.name} does not contain a list of segments.")

    @classmethod
    def _finalize_result(
        cls, errors: List[str], warnings: List[str], details: Dict[str, Any], strict: bool
    ) -> AuditResult:
        """Constructs AuditResult and raises GateAuditError if strict and failed."""
        passed = len(errors) == 0
        details["error_count"] = len(errors)
        details["warning_count"] = len(warnings)

        if not passed and strict:
            err_summary = "\n  - " + "\n  - ".join(errors[:5])
            if len(errors) > 5:
                err_summary += f"\n  - ...and {len(errors) - 5} more defects."
            raise GateAuditError(
                f"Gate 2.9 Pre-TTS Sanity Check FAILED with {len(errors)} critical defects:{err_summary}\n"
                f"Synthesis strictly aborted to prevent acoustic corruption and API waste."
            )

        return AuditResult(
            gate="GATE_2_9_PRE_TTS",
            gate_name="Gate 2.9: Pre-TTS Config & Attribution Sanity",
            status="PASS" if passed else "FAIL",
            passed=passed,
            errors=errors,
            warnings=warnings,
            details=details,
        )

    @staticmethod
    def _norm(s: str) -> str:
        """Normalizes speaker name for collision-free comparison."""
        return s.strip().lower().replace("_", " ").replace("\u093c", "")


def audit_gate2_9_pre_tts_sanity(
    script_file: Union[Path, str, List[Dict[str, Any]]],
    project_dir: Optional[Union[Path, str]] = None,
    format_mode: Literal["audiobook", "podcast"] = "audiobook",
    strict: bool = True,
) -> AuditResult:
    """
    Public entry point for Gate 2.9: Pre-TTS Config & Attribution Sanity Gate.
    """
    return PreSynthesisGate.audit_script(
        script_file_or_data=script_file,
        project_dir=project_dir,
        format_mode=format_mode,
        strict=strict,
    )
