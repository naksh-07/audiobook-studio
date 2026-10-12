#!/usr/bin/env python3
"""
Audiobook Factory - Room 3 Agent B: Stanislavski Subtext Director.
Directs voice acting subtext, transitive actioning verbs, concealed inner emotions,
acting delivery styles, and dynamic intensity headroom.
"""

from __future__ import annotations
import json
import logging
from typing import List, Dict, Any, Optional, Callable

from audiobook_factory.dramaturgy.gateway_bridge import execute_dramaturgy_llm
from audiobook_factory.model_manager import get_model_manager, TaskType
from audiobook_factory.safety import get_dramatic_fiction_framing

logger = logging.getLogger("AudiobookFactory")


class StanislavskiSubtextDirector:
    """Agent B: Psychological Actioning & Acting Delivery Specialist."""

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def _resolve_model(self) -> str:
        if self.model:
            return self.model
        return get_model_manager().resolve_active_model(TaskType.SCREENPLAY)

    def direct_subtext(
        self,
        segments: List[Dict[str, Any]],
        dramatic_context: str = "",
        is_hindi: bool = False,
        call_llm_fn: Optional[Callable[..., Any]] = None,
        director_card: Optional[Any] = None,
        playbook: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Enriches segments with Stanislavski psychological subtext and acting directives."""
        if not segments:
            return segments

        compact_turns = [
            {
                "index": s.get("index", 1),
                "speaker": str(s.get("speaker") or "Narrator"),
                "type": s.get("type", "narration"),
                "text": str(s.get("text") or "")[:300],
            }
            for s in segments
        ]

        # Dynamic scene & beat context from dramatic_plan or director_card
        eff_context = dramatic_context
        if not eff_context and director_card:
            if isinstance(director_card, dict):
                try:
                    from audiobook_factory.contracts.playbook import ChapterDirectorCard
                    director_card = ChapterDirectorCard.model_validate(director_card)
                except Exception:
                    pass
            eff_context = director_card.to_prompt_context() if hasattr(director_card, "to_prompt_context") else str(director_card)
        if not eff_context:
            eff_context = "Standard narrative encounter."

        playbook_guidance = ""
        sc_prompt = None
        if isinstance(playbook, dict):
            sc_prompt = playbook.get("screenplay_system_prompt")
        elif hasattr(playbook, "screenplay_system_prompt"):
            sc_prompt = getattr(playbook, "screenplay_system_prompt")
        if sc_prompt and str(sc_prompt).strip():
            playbook_guidance = f"\n\nAuthorial Style & Dialogue Subtext Guidance:\n{str(sc_prompt).strip()}\n"

        sys_prompt = (
            get_dramatic_fiction_framing()
            + "You are an Academy-Award winning Audio Drama Director and Stanislavski Performance Coach.\n"
            "Enrich each dialogue turn with deep psychological subtext, transitive actioning verbs, "
            "concealed inner emotions, dynamic intensity headroom, and acting delivery style.\n\n"
            + playbook_guidance +
            "Guidelines:\n"
            "- 'actioning': transitive dramatic intent verb (e.g. 'threaten', 'deflect', 'reassure', 'confess', 'probe', 'comfort', 'intimidate', 'negotiate', 'mock', 'persuade', 'seduce').\n"
            "- 'subtext': unsaid psychological motivation or truth beneath the spoken words.\n"
            "- 'underlying_emotion': concealed emotional state conflicting with surface presentation.\n"
            "- 'intensity_level': 'low' (whispered/intimate/stealth), 'medium' (standard conversational), 'high' (confrontation/panic), 'explosive' (climactic screams/battle cries).\n"
            "- 'acting': {'delivery_style': 'whispering_fear' | 'cold_menace' | 'breathless_exhaustion' | 'ironic_mockery' | 'bellowing_rage' | 'combat_strain' | 'calm_authoritative' | 'gentle_tender' | 'neutral', 'pacing': float between 0.8 and 1.25}."
        )

        prompt = f"""{get_dramatic_fiction_framing()}Dramatic Scene & Beat Context:
{eff_context}


Dialogue Turns to Direct (JSON):
```json
{json.dumps(compact_turns, ensure_ascii=False, indent=2)}
```

Output JSON: A list of objects matching by "index":
[
  {{
    "index": int,
    "actioning": string,
    "subtext": string,
    "underlying_emotion": string,
    "intensity_level": "low" | "medium" | "high" | "explosive",
    "acting": {{"delivery_style": string, "pacing": float}}
  }}
]
"""
        model = self._resolve_model()
        logger.info(f"  [StanislavskiSubtextDirector] Directing {len(segments)} segments with {model}...")

        try:
            if call_llm_fn:
                enriched = call_llm_fn(prompt=prompt, system_instruction=sys_prompt, model=model, json_mode=True)
                if isinstance(enriched, str):
                    import json_repair
                    enriched = json_repair.loads(enriched)
            else:
                enriched = execute_dramaturgy_llm(
                    prompt=prompt,
                    system_instruction=sys_prompt,
                    task="screenplay",
                    model=model,
                    json_mode=True,
                    max_output_tokens=16384,
                    thinking_budget=1024,
                )
        except Exception as e:
            logger.warning(f"  [!] StanislavskiSubtextDirector notice: {e}. Preserving input baseline.")
            return segments

        if isinstance(enriched, dict):
            for k in ("turns", "enriched", "segments", "items", "results"):
                if k in enriched and isinstance(enriched[k], list):
                    enriched = enriched[k]
                    break

        if not isinstance(enriched, list):
            return segments

        enrich_map = {item.get("index"): item for item in enriched if isinstance(item, dict) and "index" in item}
        for seg in segments:
            idx = seg.get("index")
            if idx in enrich_map:
                e = enrich_map[idx]
                # Preserve pre-existing DramaticPlan objectives to eliminate representation drift
                if e.get("actioning") and not seg.get("actioning"):
                    seg["actioning"] = e["actioning"]
                if e.get("subtext") and not seg.get("subtext"):
                    seg["subtext"] = e["subtext"]
                if e.get("underlying_emotion") and not seg.get("underlying_emotion"):
                    seg["underlying_emotion"] = e["underlying_emotion"]
                if e.get("intensity_level") and (not seg.get("intensity_level") or seg.get("intensity_level") == "medium"):
                    seg["intensity_level"] = e["intensity_level"]
                if isinstance(e.get("acting"), dict):
                    seg.setdefault("acting", {})
                    seg["acting"].update(e["acting"])

        # Narrator Transparency Invariant: Narrator is strictly calm and measured, zero melodrama
        for seg in segments:
            spk_name = str(seg.get("speaker") or "").strip().lower()
            if spk_name in ("narrator", "narration", ""):
                seg["actioning"] = "narrate"
                seg["acting"] = {"delivery_style": "calm_authoritative"}
                seg["intensity_level"] = "medium"
                seg["subtext"] = ""
                seg["underlying_emotion"] = "neutral"

        return segments
