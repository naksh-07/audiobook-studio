#!/usr/bin/env python3
"""
Audiobook Factory - Room 3: Dramaturgy & Screenplay ModelGateway Bridge.
========================================================================
The authoritative control-plane routing bridge for Room 3 Dramaturgy, Adapters,
and Dual-Track Podcast Generation.
Strictly routes all LLM requests through Phase 1 ModelGateway:
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


def execute_dramaturgy_llm(
    prompt: str,
    system_instruction: Optional[str] = None,
    task: str = "screenplay",
    model: Optional[str] = None,
    temperature: float = 0.35,
    max_output_tokens: Optional[int] = 16384,
    thinking_budget: Optional[int] = 1024,
    session_id: Optional[str] = None,
    user_id: str = "dramaturgy_worker",
    json_mode: bool = True,
    **kwargs: Any,
) -> Union[Dict[str, Any], List[Any], str]:
    """
    Executes a Room 3 Dramaturgy / Podcast LLM request strictly through ModelGateway.
    Returns parsed JSON object/list or raw string, with automatic json_repair.
    """
    is_mock = os.environ.get("MOCK_OFFLINE", "").lower() in ("true", "1")
    if is_mock or os.environ.get("GEMINI_API_KEY", "").startswith("mock"):
        logger.info("[-] MOCK_OFFLINE active in execute_dramaturgy_llm. Returning offline mock.")
        if json_mode:
            return [
                {
                    "index": 1,
                    "speaker": "Host_A",
                    "text": "Welcome to the discussion.",
                    "type": "dialogue",
                    "actioning": "welcome",
                    "acting": {"delivery_style": "warm", "pacing": 1.0},
                }
            ]
        return "Offline mock screenplay response."

    # Inject dramatic fiction framing for creative literature
    framing = get_dramatic_fiction_framing()
    effective_sys_prompt = system_instruction or ""
    if framing and "DRAMATIC LITERARY CONTEXT" not in effective_sys_prompt:
        effective_sys_prompt = f"{framing}\n{effective_sys_prompt}".strip()

    # Filter legacy kwargs from old llm_client interfaces
    task_type = kwargs.pop("task_type", None)
    task_name = getattr(task_type, "value", str(task_type)) if task_type else task
    kwargs.pop("response_mime_type", None)
    kwargs.pop("return_raw_text", None)
    retries = kwargs.pop("max_retries", 3)

    try:
        from audiobook_factory.core.models.gateway import get_model_gateway
        gateway = get_model_gateway()

        response = gateway.generate_text(
            prompt=prompt,
            system_instruction=effective_sys_prompt,
            task=task_name,
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            thinking_budget=thinking_budget,
            response_json=json_mode,
            session_id=session_id or "dramaturgy_session",
            user_id=user_id,
            max_retries=retries,
            **kwargs,
        )
        raw_text = (response.text or "").strip()
    except ImportError as err:
        logger.error("  [!] ModelGateway not available in environment. Fails closed to eliminate unmetered rogue HTTP calls.")
        raise RuntimeError(
            "ModelGateway from audiobook_factory.core.models.gateway is required for dramaturgy LLM calls. "
            "Direct unmetered HTTP calls are strictly forbidden."
        ) from err
    except Exception as e:
        logger.error(f"  [!] Dramaturgy ModelGateway dispatch failed: {e}")
        raise

    if not json_mode:
        # Clean markdown fences
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:markdown|json|md|text)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        return cleaned.strip()

    # Deserialization via resilient json_repair
    try:
        cleaned_json = raw_text.strip()
        cleaned_json = re.sub(r"^```(?:json)?\s*\n?", "", cleaned_json, flags=re.IGNORECASE)
        cleaned_json = re.sub(r"\n?```\s*$", "", cleaned_json)

        parsed = json_repair.loads(cleaned_json)
        return parsed
    except Exception as e:
        logger.warning(f"  [!] json_repair failed on LLM output ({e}). Falling back to standard json.loads.")
        try:
            return json.loads(cleaned_json)
        except Exception:
            return raw_text
