#!/usr/bin/env python3
"""
Audiobook Factory - Room 3.5: Casting ModelGateway Bridge.
==========================================================
The authoritative control-plane routing bridge for Room 3.5 Studio Voice Casting.
Strictly routes all AI Casting Director requests through Phase 1 ModelGateway:
1. Concurrency=1 atomic key leasing via KeyLeaseManager against SQLite inventory.
2. The 7 Iron Shields AntiBanGuard (11.0 RPM token bucket, session affinity, stealth headers).
3. Permissive Creative Fiction Framing (BLOCK_NONE) to prevent puritanical truncation.
4. Resilient json_repair deserialization.
5. Strict fail-closed policy: Zero unmetered urllib / direct HTTP requests allowed.
"""

from __future__ import annotations
import os
import re
import json
from typing import Any, Dict, List, Optional, Union

import json_repair

from audiobook_factory.logger import logger
from audiobook_factory.safety import get_dramatic_fiction_framing


def execute_casting_llm(
    prompt: str,
    system_instruction: Optional[str] = None,
    task: str = "directing",
    model: Optional[str] = None,
    temperature: float = 0.20,
    max_output_tokens: Optional[int] = 8192,
    session_id: Optional[str] = None,
    user_id: str = "casting_director",
    json_mode: bool = True,
    **kwargs: Any,
) -> Union[Dict[str, Any], List[Any], str]:
    """
    Executes an AI Casting Director request strictly through ModelGateway.
    Returns parsed JSON object/list or raw string, with automatic json_repair.
    """
    is_mock = os.environ.get("MOCK_OFFLINE", "").lower() in ("true", "1")
    if is_mock or os.environ.get("GEMINI_API_KEY", "").startswith("mock"):
        logger.info("[-] MOCK_OFFLINE active in execute_casting_llm. Returning offline mock.")
        lang_code = "hi-IN" if "Hindi" in prompt else "en-US"
        m_gender = re.search(r"-\s*Gender:\s*(\w+)", prompt, re.IGNORECASE)
        gender = m_gender.group(1).lower() if m_gender else None

        excluded = set()
        m_excl = re.search(r"Already Cast Voices in Ensemble.*?:.*?(\[.*?\])", prompt, re.DOTALL)
        if m_excl:
            try:
                excluded = set(json.loads(m_excl.group(1)))
            except Exception:
                pass

        try:
            from audiobook_factory.casting.registry import VoiceProfileRegistry
            reg = VoiceProfileRegistry.get_instance()
            cands = reg.query_profiles(
                language_code=lang_code,
                gender=gender if gender in ("male", "female") else None,
                exclude_voice_ids=excluded,
                limit=5,
            )
            if not cands and excluded:
                cands = reg.query_profiles(language_code=lang_code, gender=gender if gender in ("male", "female") else None, limit=5)
            assigned_id = cands[0].voice_id if cands else ("hi-in-advisor-10" if lang_code == "hi-IN" else "Charon")
        except Exception:
            assigned_id = "hi-in-advisor-10" if lang_code == "hi-IN" else "Charon"

        return {
            "assigned_voice_id": assigned_id,
            "dialect": "Standard",
            "casting_rationale": f"Mock assignment matching {gender or 'neutral'} role.",
            "baseline_formants": {
                "chest_resonance_150hz_db": 0.0,
                "nasal_presence_2800hz_db": 0.0,
                "throat_clarity_3200hz_db": 0.0,
                "air_shelf_8000hz_db": 0.0,
                "target_tempo_multiplier": 1.0,
            }
        }

    # Inject dramatic fiction framing for creative literature
    framing = get_dramatic_fiction_framing()
    effective_sys_prompt = system_instruction or ""
    if framing and "DRAMATIC LITERARY CONTEXT" not in effective_sys_prompt:
        effective_sys_prompt = f"{framing}\n{effective_sys_prompt}".strip()

    # Filter legacy kwargs
    kwargs.pop("response_mime_type", None)
    kwargs.pop("return_raw_text", None)
    kwargs.pop("max_retries", None)

    try:
        from audiobook_factory.core.models.gateway import get_model_gateway
        gateway = get_model_gateway()

        response = gateway.generate_text(
            prompt=prompt,
            system_instruction=effective_sys_prompt,
            task=task,
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            session_id=session_id,
            user_id=user_id,
            **kwargs,
        )

        content = response.content if hasattr(response, "content") else str(response)

        if not json_mode:
            return content

        # Strip markdown fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE).strip()

        try:
            return json_repair.loads(cleaned)
        except Exception as pe:
            logger.warning(f"  [Casting Gateway] json_repair parse error: {pe}. Raw: {content[:160]}")
            return {}

    except Exception as e:
        logger.error(f"  [!] Studio Casting LLM execution failed through ModelGateway: {e}")
        raise RuntimeError(f"Studio Casting Gateway failed: {e}") from e
