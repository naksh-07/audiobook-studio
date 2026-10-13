#!/usr/bin/env python3
"""
Audiobook Factory - Room 3: Screenplay Dramaturgy & Spatial Staging Coordinator.
Orchestrates the screenplay room across the key pool:
1. DialogueTurnIsolator: Verbatim turn extraction & speaker identification.
2. DialogueAttributionAuditor: Anti-swap QA and attribution audit.
3. StanislavskiSubtextDirector: Transitive actioning verbs, psychological subtext, intensity & acoustic reflex tags.
4. PhysicalBlockingDirector: Actor physical posture, proximity & azimuth panning (-0.8 to +0.8).
5. DramaturgyConsistencyJudge: Spatial continuity audit, narrator clamping & intensity calibration.
6. Screenplay Segment Alignment: Canonical character alias preservation, bilingual speaker alignment, 0% speaker turn inversion, and zero quote leakage to Narrator.
"""

from __future__ import annotations
import re
import logging
from typing import List, Dict, Any, Optional, Callable

from .dialogue_isolator import DialogueTurnIsolator
from .dialogue_attribution_auditor import DialogueAttributionAuditor
from .stanislavski_director import StanislavskiSubtextDirector
from .physical_blocking_director import PhysicalBlockingDirector
from .dramaturgy_judge import DramaturgyConsistencyJudge

logger = logging.getLogger("AudiobookFactory")


def build_canonical_alias_map(
    character_roster: Optional[Dict[str, Any]] = None,
    is_hindi: bool = False,
) -> Dict[str, str]:
    """
    Builds a bidirectional alias and bilingual speaker key lookup map
    from character roster metadata (supporting dict, list, or CastLock schemas).
    """
    alias_map: Dict[str, str] = {}
    if not character_roster:
        return alias_map

    def _register_variants(key: str, canonical: str):
        k_clean = str(key).strip()
        if not k_clean:
            return
        k_low = k_clean.lower()
        alias_map[k_low] = canonical
        alias_map[k_low.replace("_", " ")] = canonical
        alias_map[k_low.replace(" ", "_")] = canonical

        # Strip common English and Hindi leading articles
        bare = k_low
        for art in ("the ", "a ", "an ", "वह ", "उस "):
            if bare.startswith(art):
                bare = bare[len(art):].strip()
                break
        alias_map[bare] = canonical
        alias_map[bare.replace("_", " ")] = canonical
        alias_map[bare.replace(" ", "_")] = canonical
        for art in ("the ", "a ", "an "):
            alias_map[art + bare] = canonical
            alias_map[(art + bare).replace(" ", "_")] = canonical

    # 1. Inspect "characters" container (dict or list)
    chars = character_roster.get("characters")
    if isinstance(chars, dict):
        for canon_name, details in chars.items():
            if canon_name in ("Narrator", "Foley"):
                continue
            c_clean = canon_name.strip()
            _register_variants(c_clean, c_clean)
            if isinstance(details, dict):
                # Bilingual name fields
                for k in ("hindi_name", "english_name", "display_name_hi", "hindi"):
                    val = details.get(k)
                    if isinstance(val, str) and val.strip():
                        _register_variants(val.strip(), c_clean)
                for a in details.get("aliases", []):
                    if isinstance(a, str) and a.strip():
                        _register_variants(a.strip(), c_clean)
    elif isinstance(chars, list):
        for c in chars:
            if isinstance(c, dict):
                canon_name = c.get("english_name") or c.get("name") or ""
                if not canon_name or canon_name in ("Narrator", "Foley"):
                    continue
                c_clean = canon_name.strip()
                _register_variants(c_clean, c_clean)
                for k in ("hindi_name", "english_name", "display_name_hi", "hindi"):
                    val = c.get(k)
                    if isinstance(val, str) and val.strip():
                        _register_variants(val.strip(), c_clean)
                for a in c.get("aliases", []):
                    if isinstance(a, str) and a.strip():
                        _register_variants(a.strip(), c_clean)

    # 2. Inspect "locks" (CastLock / CastLockRegistry container)
    locks = character_roster.get("locks")
    if isinstance(locks, dict):
        for lock_key, lock_val in locks.items():
            canon_name = lock_key
            if hasattr(lock_val, "character_name"):
                canon_name = getattr(lock_val, "character_name") or lock_key
            elif isinstance(lock_val, dict):
                canon_name = lock_val.get("character_name") or lock_key
            canon_clean = str(canon_name).strip()
            _register_variants(canon_clean, canon_clean)
            _register_variants(str(lock_key).strip(), canon_clean)
            if hasattr(lock_val, "display_name_hi"):
                dhi = getattr(lock_val, "display_name_hi")
                if dhi:
                    _register_variants(str(dhi).strip(), canon_clean)
            elif isinstance(lock_val, dict) and lock_val.get("display_name_hi"):
                _register_variants(str(lock_val["display_name_hi"]).strip(), canon_clean)
            aliases = getattr(lock_val, "aliases", None) or (lock_val.get("aliases") if isinstance(lock_val, dict) else [])
            for a in aliases:
                if isinstance(a, str) and a.strip():
                    _register_variants(a.strip(), canon_clean)

    # 3. Top-level character dict entries
    for k, v in character_roster.items():
        if k not in ("characters", "locks", "metadata", "roster_version", "created_at") and isinstance(v, dict):
            c_clean = str(k).strip()
            _register_variants(c_clean, c_clean)
            for f in ("hindi_name", "english_name", "display_name_hi", "hindi"):
                val = v.get(f)
                if isinstance(val, str) and val.strip():
                    _register_variants(val.strip(), c_clean)
            for a in v.get("aliases", []):
                if isinstance(a, str) and a.strip():
                    _register_variants(a.strip(), c_clean)

    return alias_map


def format_and_align_segments(
    segments: List[Dict[str, Any]],
    character_roster: Optional[Dict[str, Any]] = None,
    is_hindi: bool = False,
) -> List[Dict[str, Any]]:
    """
    Guarantees screenplay segment formatting consistency:
    1. Preserves canonical character aliases and aligns bilingual speaker keys.
    2. Enforces 0% speaker turn inversion and zero quote leakage to Narrator.
    3. Normalizes 1-based continuous indexing and Narrator transparency.
    """
    if not segments:
        return []

    alias_map = build_canonical_alias_map(character_roster, is_hindi=is_hindi)

    def _resolve_speaker(spk: str) -> str:
        if not spk:
            return "Narrator"
        clean = str(spk).strip(" \"':()[]")
        if not clean:
            return "Narrator"
        low = clean.lower()
        if low in ("narrator", "narration", "सूत्रधार", "वाचक"):
            return "Narrator"
        if low in alias_map:
            return alias_map[low]
        # Article stripping
        for art in ("the ", "a ", "an ", "वह ", "उस "):
            if low.startswith(art):
                bare = low[len(art):].strip()
                if bare in alias_map:
                    return alias_map[bare]
                if bare.replace("_", " ") in alias_map:
                    return alias_map[bare.replace("_", " ")]
        norm_sp = low.replace("_", " ")
        if norm_sp in alias_map:
            return alias_map[norm_sp]
        norm_un = low.replace(" ", "_")
        if norm_un in alias_map:
            return alias_map[norm_un]
        return clean

    formatted: List[Dict[str, Any]] = []

    for seg in segments:
        s = dict(seg)
        spk = s.get("speaker", "Narrator")
        seg_type = s.get("type", "narration")
        text = str(s.get("text") or "").strip()

        # Resolve canonical speaker name
        resolved_spk = _resolve_speaker(spk)
        s["speaker"] = resolved_spk

        # Zero Quote Leakage to Narrator:
        # If segment is dialogue, speaker cannot be Narrator or empty
        if seg_type == "dialogue" and resolved_spk in ("Narrator", "Foley", ""):
            # Re-attribute: find active interlocutor from formatted history
            interlocutor = None
            for prev in reversed(formatted):
                if prev.get("type") == "dialogue" and prev.get("speaker") not in ("Narrator", "Foley"):
                    interlocutor = prev.get("speaker")
                    break
            if interlocutor:
                s["speaker"] = interlocutor
            elif alias_map:
                s["speaker"] = next(iter(alias_map.values()))
            else:
                s["speaker"] = "Speaker"

        # If segment is narration:
        if seg_type == "narration" or s["speaker"] in ("Narrator", "narration", ""):
            s["speaker"] = "Narrator"
            # Check if pure quoted speech dialogue leaked into narrator turn
            m_quote = re.match(r"^[\"“'«]([^\"“”'»]+)[\"”'»]$", text)
            if m_quote and len(m_quote.group(1).strip()) > 3:
                # This was an unextracted dialogue line that leaked to Narrator!
                s["type"] = "dialogue"
                s["text"] = m_quote.group(1).strip()
                cand = None
                for prev in reversed(formatted):
                    if prev.get("type") == "dialogue" and prev.get("speaker") not in ("Narrator", "Foley"):
                        cand = prev.get("speaker")
                        break
                s["speaker"] = cand if cand else (next(iter(alias_map.values())) if alias_map else "Speaker")
            else:
                s["type"] = "narration"
                # Narrator Transparency Invariant: Narrator lines must NEVER contain acoustic reflex tags
                cleaned_narr, _, _ = StanislavskiSubtextDirector.process_acoustic_reflexes_and_acting_cues(
                    text=text,
                    is_dialogue=False,
                )
                s["text"] = cleaned_narr
                s["actioning"] = "narrate"
                s["acting"] = {"delivery_style": "calm_authoritative"}
                s["intensity_level"] = "medium"
                s["subtext"] = ""
                s["underlying_emotion"] = "neutral"

        formatted.append(s)

    # Stitch split dialogue turns (Audible Flow Standard)
    try:
        from audiobook_factory.script.screenplay_cleaner import stitch_split_dialogue_turns
        formatted = stitch_split_dialogue_turns(formatted)
    except Exception:
        pass

    # Ensure continuous 1-based indexing
    for idx, item in enumerate(formatted, 1):
        item["index"] = idx

    return formatted


class ScreenplayDramaturgyRoom:
    """Coordinates the screenplay dramaturgy, anti-swap attribution, and spatial staging agents."""

    def __init__(self, model: Optional[str] = None):
        self.model = model
        self.isolator = DialogueTurnIsolator(model=model)
        self.auditor = DialogueAttributionAuditor(model=model)
        self.stanislavski = StanislavskiSubtextDirector(model=model)
        self.blocking_director = PhysicalBlockingDirector(model=model)
        self.judge = DramaturgyConsistencyJudge()

    def format_and_align_segments(
        self,
        segments: List[Dict[str, Any]],
        character_roster: Optional[Dict[str, Any]] = None,
        is_hindi: bool = False,
    ) -> List[Dict[str, Any]]:
        """Public helper to format and align screenplay segments."""
        return format_and_align_segments(segments, character_roster=character_roster, is_hindi=is_hindi)

    def process_chunk(
        self,
        chunk_text: str,
        preceding_context: str = "",
        dramatic_context: str = "",
        is_hindi: bool = False,
        character_roster: Optional[Dict[str, Any]] = None,
        call_llm_fn: Optional[Callable[..., Any]] = None,
        director_card: Optional[Any] = None,
        playbook: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Processes a chunk through the 5-agent Screenplay Room."""
        # Pass 1: Turn Isolation
        turns = self.isolator.isolate_turns(
            chunk_text=chunk_text,
            preceding_context=preceding_context,
            is_hindi=is_hindi,
            character_roster=character_roster,
        )
        if not turns:
            return []

        # Pass 1.5: Forensic Attribution & Speaker Anti-Swap Audit
        audited_turns, audit_report = self.auditor.audit_and_correct(
            turns=turns,
            chunk_text=chunk_text,
            preceding_context=preceding_context,
            is_hindi=is_hindi,
            character_roster=character_roster,
            call_llm_fn=call_llm_fn,
        )

        # Pass 2A: Stanislavski Subtext, Intensity & Acoustic Reflex Directing
        directed_turns = self.stanislavski.direct_subtext(
            segments=audited_turns,
            dramatic_context=dramatic_context,
            is_hindi=is_hindi,
            call_llm_fn=call_llm_fn,
            director_card=director_card,
            playbook=playbook,
        )

        # Pass 2B: Physical Blocking & Azimuth Staging
        staged_turns = self.blocking_director.direct_blocking(
            segments=directed_turns,
            dramatic_context=dramatic_context,
            call_llm_fn=call_llm_fn,
            director_card=director_card,
        )

        # Pass 3: Consistency & Spatial Continuity Audit
        certified_turns, report = self.judge.audit_and_certify(
            segments=staged_turns,
            chunk_title="Screenplay Chunk",
        )

        # Pass 4: Screenplay Formatting, Canonical Alias & Bilingual Alignment
        final_turns = self.format_and_align_segments(
            segments=certified_turns,
            character_roster=character_roster,
            is_hindi=is_hindi,
        )

        return final_turns


_room_instance: Optional[ScreenplayDramaturgyRoom] = None


def get_screenplay_room(model: Optional[str] = None) -> ScreenplayDramaturgyRoom:
    """Returns singleton ScreenplayDramaturgyRoom instance."""
    global _room_instance
    if _room_instance is None or (model and _room_instance.model != model):
        _room_instance = ScreenplayDramaturgyRoom(model=model)
    return _room_instance

