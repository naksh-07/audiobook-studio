#!/usr/bin/env python3
"""
Audiobook Factory - Room 1.5: Glossary ModelGateway Bridge.
===========================================================
The authoritative control-plane routing bridge for Room 1.5 Glossary & Metadata Subsystem.
Strictly routes all LLM entity classification through Phase 1 ModelGateway:
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


def execute_glossary_llm(
    prompt: str,
    system_instruction: Optional[str] = None,
    task: str = "extraction",
    model: Optional[str] = None,
    temperature: float = 0.10,
    max_output_tokens: Optional[int] = 8192,
    session_id: Optional[str] = None,
    user_id: str = "glossary_worker",
    json_mode: bool = True,
    **kwargs: Any,
) -> Union[Dict[str, Any], List[Any], str]:
    """
    Executes a Room 1.5 Glossary LLM request strictly through ModelGateway.
    Returns parsed JSON object/list or raw string, with automatic json_repair.
    """
    is_mock = os.environ.get("MOCK_OFFLINE", "").lower() in ("true", "1")
    if is_mock or os.environ.get("GEMINI_API_KEY", "").startswith("mock"):
        logger.info("[-] MOCK_OFFLINE active in execute_glossary_llm. Returning offline mock.")
        return {
            "characters": [
                {
                    "english_name": "Aldor",
                    "hindi_name": "एल्डोर",
                    "entity_type": "PROPER_NAME",
                    "aliases": ["The Watcher"],
                    "gender": "male",
                    "voice_style": "Calm and measured",
                    "hindustani_archetype": "RUGGED_GRIT",
                }
            ],
            "locations_and_terms": {"Rivergate": "रिवरगेट"},
        }

    # Inject dramatic fiction framing for creative literature
    framing = get_dramatic_fiction_framing()
    effective_sys_prompt = system_instruction or ""
    if framing and "DRAMATIC LITERARY CONTEXT" not in effective_sys_prompt:
        effective_sys_prompt = f"{framing}\n{effective_sys_prompt}".strip()

    # Filter legacy kwargs
    kwargs.pop("response_mime_type", None)
    kwargs.pop("return_raw_text", None)
    retries = kwargs.pop("max_retries", 3)

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
            response_json=json_mode,
            session_id=session_id or "glossary_session",
            user_id=user_id,
            max_retries=retries,
            **kwargs,
        )
        raw_text = (response.text or "").strip()
    except ImportError as err:
        logger.error("  [!] ModelGateway not available in environment. Fails closed to eliminate unmetered rogue HTTP calls.")
        raise RuntimeError(
            "ModelGateway from audiobook_factory.core.models.gateway is required for glossary LLM calls. "
            "Direct unmetered HTTP calls are strictly forbidden."
        ) from err
    except Exception as e:
        logger.error(f"  [!] Glossary ModelGateway dispatch failed: {e}")
        raise

    if not json_mode:
        return raw_text

    # Robust JSON parsing with markdown code fence stripping and json_repair fallback
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json|markdown)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except Exception:
        try:
            return json_repair.loads(cleaned)
        except Exception as parse_err:
            logger.warning(f"  [!] JSON repair failed in execute_glossary_llm: {parse_err}")
            return {}
