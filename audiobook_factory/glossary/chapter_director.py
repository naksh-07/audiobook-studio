#!/usr/bin/env python3
"""
Audiobook Factory - Room 1.5: Chapter Steering Director.
========================================================
Extracts chapter-level dramatic atmosphere, character emotional stances,
pacing cadence, and narrator vocal tints.
Pure standalone module with zero cross-room circular dependencies.
"""

from __future__ import annotations
import re
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path

from audiobook_factory.contracts.playbook import ChapterDirectorCard, ProductionPlaybook
from audiobook_factory.model_manager import get_model_manager, TaskType
from audiobook_factory.safety import get_dramatic_fiction_framing

logger = logging.getLogger("AudiobookFactory")


class ChapterSteeringDirector:
    """Standalone Director for extracting chapter-specific dramatic steering cards."""

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def _resolve_model(self) -> str:
        if self.model:
            return self.model
        return get_model_manager().resolve_active_model(TaskType.EXTRACTION)

    def direct_chapter(
        self,
        chapter_text: str,
        chapter_num: int = 1,
        chapter_title: str = "",
        playbook: Optional[ProductionPlaybook] = None,
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> ChapterDirectorCard:
        """
        Directs a single chapter to produce a ChapterDirectorCard.
        Takes chapter text in, returns ChapterDirectorCard out.
        """
        ch_text = (chapter_text or "").strip()
        if not ch_text:
            base_tint = playbook.narrator_master_demeanor if playbook else "calm, observant, grounded delivery"
            return ChapterDirectorCard(
                chapter_num=chapter_num,
                chapter_title=chapter_title,
                narrator_vocal_tint=base_tint,
            )

        # Sample beginning, middle, and climax (max ~6000 chars to keep token cost minimal and fast)
        words = ch_text.split()
        if len(words) <= 1200:
            sample = ch_text
        else:
            first_part = " ".join(words[:400])
            mid_idx = len(words) // 2
            mid_part = " ".join(words[mid_idx - 200 : mid_idx + 200])
            last_part = " ".join(words[-400:])
            sample = f"{first_part}\n\n[...]\n\n{mid_part}\n\n[...]\n\n{last_part}"

        world_tradition = playbook.literary_tradition if playbook else "Contemporary Fiction"
        world_cadence = playbook.regional_dialect_cadence if playbook else "Standard Spoken Hindustani"
        world_atmosphere = playbook.world_atmosphere_summary if playbook else "Dramatic Audio Fiction"

        model = self.model or ("mock-model" if call_llm_fn else self._resolve_model())

        fiction_framing = get_dramatic_fiction_framing(title=f"Chapter {chapter_num}")
        sys_prompt = (
            fiction_framing +
            "You are an elite Audio Drama Director and Stanislavski Performance Supervisor.\n"
            "Analyze the chapter excerpt to extract its dramatic atmosphere, emotional stakes, "
            "pacing trajectory, and narrator vocal tint.\n\n"
            "Invariants:\n"
            "1. Ground all observations strictly in the text sample.\n"
            "2. Identify specific emotional states for active speaking characters.\n"
            "3. Provide actionable, concise descriptors (no verbose fluff).\n"
        )

        user_prompt = f"""Analyze Chapter {chapter_num}{f': {chapter_title}' if chapter_title else ''}
Setting & World Tradition: {world_tradition} ({world_cadence})
World Atmosphere: {world_atmosphere}

Chapter Text Sample:
\"\"\"
{sample[:8000]}
\"\"\"

Output JSON:
{{
  "scene_atmosphere": "Concise 1-2 sentence description of setting, mood, sensory texture, and underlying tension.",
  "dramatic_tension": "The trajectory of dramatic tension (e.g. 'simmering suspicion building to sudden violent climax' or 'melancholic reflection with quiet emotional ache').",
  "character_emotional_states": {{
    "CharacterName": "Current psychological stance, immediate objective, or hidden fear in this chapter"
  }},
  "pacing_cadence": "Rhythm guidance (e.g. 'slow measured exposition quickening to sharp staccato dialogue' or 'steady lyrical flow').",
  "narrator_vocal_tint": "Vocal demeanor descriptor for the lead narrator in this specific chapter (e.g. 'low, tense, watchful delivery' or 'gentle, reflective, poignantly understated').",
  "key_motifs_or_sensory_details": ["list", "of", "concrete", "sensory", "details"]
}}
"""
        logger.info(f"  [ChapterSteeringDirector] Directing Chapter {chapter_num} using {model}...")

        try:
            if call_llm_fn:
                raw = call_llm_fn(prompt=user_prompt, system_instruction=sys_prompt, model=model, json_mode=True)
                if isinstance(raw, str):
                    import json_repair
                    clean_raw = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip(), flags=re.IGNORECASE)
                    clean_raw = re.sub(r"\n?```\s*$", "", clean_raw.strip())
                    res = json_repair.loads(clean_raw)
                else:
                    res = raw
            else:
                from audiobook_factory.glossary.gateway_bridge import execute_glossary_llm
                res = execute_glossary_llm(
                    prompt=user_prompt,
                    system_instruction=sys_prompt,
                    task="extraction",
                    model=model,
                    json_mode=True,
                    max_output_tokens=2048,
                    thinking_budget=512,
                )

            if isinstance(res, dict) and res.get("scene_atmosphere"):
                logger.info(f"[+] ChapterSteeringDirector: Successfully directed Chapter {chapter_num}.")
                raw_states = res.get("character_emotional_states")
                clean_states: Dict[str, str] = (
                    {str(k).strip(): str(v).strip() for k, v in raw_states.items() if k and v}
                    if isinstance(raw_states, dict)
                    else {}
                )
                raw_motifs = res.get("key_motifs_or_sensory_details")
                clean_motifs: List[str] = (
                    [str(m).strip() for m in raw_motifs if m and str(m).strip()]
                    if isinstance(raw_motifs, list)
                    else []
                )

                return ChapterDirectorCard(
                    chapter_num=chapter_num,
                    chapter_title=chapter_title,
                    scene_atmosphere=str(res.get("scene_atmosphere") or "Standard narrative encounter.").strip(),
                    dramatic_tension=str(res.get("dramatic_tension") or "steady narrative progression").strip(),
                    character_emotional_states=clean_states,
                    pacing_cadence=str(res.get("pacing_cadence") or "measured conversational with natural spoken pauses").strip(),
                    narrator_vocal_tint=str(res.get("narrator_vocal_tint") or "calm, observant, grounded delivery").strip(),
                    key_motifs_or_sensory_details=clean_motifs,
                )
        except Exception as e:
            logger.warning(f"  [!] ChapterSteeringDirector LLM notice: {e}. Falling back to heuristic steering.")

        return self._heuristic_fallback(
            chapter_text=ch_text,
            chapter_num=chapter_num,
            chapter_title=chapter_title,
            playbook=playbook,
        )

    def _heuristic_fallback(
        self,
        chapter_text: str,
        chapter_num: int,
        chapter_title: str,
        playbook: Optional[ProductionPlaybook] = None,
    ) -> ChapterDirectorCard:
        """Deterministic heuristic fallback analyzing text signals and sentiment keywords."""
        sample_lower = (chapter_text or "")[:15000].lower()

        has_combat = any(w in sample_lower for w in ("sword", "blade", "blood", "kill", "struck", "slash", "fight", "attack", "wound", "talwar", "chaku", "cheer"))
        has_suspense = any(w in sample_lower for w in ("whisper", "shadow", "dark", "watch", "silence", "creak", "terror", "fear", "darr", "khatra", "sannata"))
        has_intimacy = any(w in sample_lower for w in ("kiss", "touch", "embrace", "skin", "breath", "whispered", "desire", "eyes met", "pyar", "jism"))
        has_grief = any(w in sample_lower for w in ("tears", "wept", "sorrow", "grave", "corpse", "died", "loss", "mourn", "gham", "roya", "maut"))

        if has_combat:
            atmosphere = "High-stakes physical confrontation; imminent danger, metallic friction, and explosive violence."
            tension = "Tense anticipation erupting into rapid, visceral combat."
            pacing = "Sharp, staccato clauses with urgent spoken delivery."
            narrator_tint = "focused, urgent, rhythmic tension with rapid clauses during action"
        elif has_suspense:
            atmosphere = "Shadowed, claustrophobic suspense; watchful silence and simmering unease."
            tension = "Unresolved psychological tension with latent menace."
            pacing = "Deliberate, measured phrasing with lingering pregnant pauses."
            narrator_tint = "low, quiet, watchful dread with suppressed urgency"
        elif has_intimacy:
            atmosphere = "Sensory intimacy, close proximity, somatic warmth, and emotional vulnerability."
            tension = "Simmering romantic or psychological tension."
            pacing = "Soft, fluid, rhythmic cadence with delicate pauses."
            narrator_tint = "soft, understated, tender vocal delivery"
        elif has_grief:
            atmosphere = "Somber, melancholic reflection; weight of loss and solemn stillness."
            tension = "Heavy emotional gravity and pathos."
            pacing = "Slow, resonant, deliberate delivery."
            narrator_tint = "solemn, compassionate, resonant literary gravity"
        else:
            base_demeanor = playbook.narrator_master_demeanor if playbook else "calm, steady, articulate, measured delivery"
            atmosphere = f"Immersive narrative scene in {playbook.literary_tradition if playbook else 'the narrative setting'}."
            tension = "Steady narrative progression."
            pacing = "Measured conversational pacing with natural spoken pauses."
            narrator_tint = base_demeanor

        return ChapterDirectorCard(
            chapter_num=chapter_num,
            chapter_title=chapter_title,
            scene_atmosphere=atmosphere,
            dramatic_tension=tension,
            character_emotional_states={},
            pacing_cadence=pacing,
            narrator_vocal_tint=narrator_tint,
            key_motifs_or_sensory_details=[],
        )

    @classmethod
    def save_director_card(cls, card: ChapterDirectorCard, project_dir: Path | str) -> Path:
        """Persists the ChapterDirectorCard atomically to metadata/chapters/chapter_XXX_director_card.json."""
        import os
        import uuid
        p_dir = Path(project_dir).resolve()
        out_dir = p_dir / "metadata" / "chapters"
        out_dir.mkdir(parents=True, exist_ok=True)
        ch_num = max(0, int(card.chapter_num))
        out_path = out_dir / f"chapter_{ch_num:03d}_director_card.json"
        tmp_path = out_dir / f"chapter_{ch_num:03d}_director_card.tmp.{os.getpid()}_{uuid.uuid4().hex[:6]}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(card.model_dump(), f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, out_path)
        return out_path

    @classmethod
    def load_director_card(cls, project_dir: Path | str, chapter_num: int | str) -> Optional[ChapterDirectorCard]:
        """Loads persistent ChapterDirectorCard if present on disk."""
        try:
            ch_num = max(0, int(chapter_num))
        except (ValueError, TypeError):
            ch_num = 1
        p_dir = Path(project_dir).resolve()
        card_path = p_dir / "metadata" / "chapters" / f"chapter_{ch_num:03d}_director_card.json"
        if card_path.exists() and card_path.stat().st_size > 0:
            try:
                with open(card_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return ChapterDirectorCard.model_validate_json(content)
            except Exception as e:
                logger.warning(f"  [!] Failed to load ChapterDirectorCard from {card_path}: {e}")
        return None
