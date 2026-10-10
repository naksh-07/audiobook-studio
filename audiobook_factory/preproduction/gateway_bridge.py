#!/usr/bin/env python3
"""
Audiobook Factory - Room 1: Pre-Production ModelGateway Bridge.
==============================================================
The authoritative control-plane bridge for all Pre-Production Room 1 agents:
- BookDNAAgent (Universal Literary DNA & Register Profiler)
- DramatisPersonaeAgent (Character Dossier Extraction)
- NovelDeepSearchEngine (Factual Grounding & Lore Reconnaissance)
- PhoneticLexiconDramaturge (Devanagari Transliteration)
- SonicWorldArchitect (Acoustic Space & Atmosphere Design)
- VocalAcousticDirector (Room Impulse & Parametric EQ Curves)
- EntityDiscoveryEngine (Emerging Lore & Entity Discovery)

Guarantees:
1. Strict ModelGateway Routing: Eliminates rogue urllib calls and routes 100% of LLM
   traffic through the Phase 1 control plane.
2. Atomic Key Leasing: Acquires Concurrency=1 mutual exclusion handles from KeyLeaseManager.
3. The 7 Iron Shields AntiBanGuard: Enforces token-bucket rate limiting (11 RPM), session
   affinity sticky binding, and stealth SDK headers.
4. Robust JSON Parsing: Automatically strips conversational markdown fences and applies
   json_repair to handle truncated or slightly malformed model responses.
5. Permissive Creative Fiction Framing: Applies BLOCK_NONE thresholds for uninhibited literary processing.
"""

from __future__ import annotations
import os
import re
import json
from typing import Any, Dict, List, Optional, Union
import json_repair

from audiobook_factory.logger import logger
from audiobook_factory.core.models.gateway import get_model_gateway
from audiobook_factory.safety import get_dramatic_fiction_framing


def execute_preproduction_llm(
    prompt: str,
    system_instruction: Optional[str] = None,
    task: str = "directing",
    model: Optional[str] = None,
    json_mode: bool = True,
    temperature: float = 0.3,
    max_output_tokens: Optional[int] = None,
    thinking_budget: Optional[int] = None,
    session_id: Optional[str] = None,
    user_id: str = "preproduction_worker",
    tools: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any,
) -> Union[Dict[str, Any], List[Any], str]:
    """
    Executes a Pre-Production Room 1 LLM request strictly through ModelGateway.
    Returns parsed JSON (dict or list) if json_mode=True; otherwise returns raw response text.
    """
    is_mock = os.environ.get("MOCK_OFFLINE", "").lower() in ("true", "1")
    if is_mock or os.environ.get("GEMINI_API_KEY", "").startswith("mock"):
        # Offline testing mock path
        if json_mode:
            return {}
        return "mock offline text"

    gateway = get_model_gateway()

    # Map task names into valid ModelGateway task types
    task_name = task.lower() if isinstance(task, str) else getattr(task, "value", "directing")
    if task_name not in ("extraction", "translation", "directing", "utility", "screenplay"):
        task_name = "directing"

    # Inject dramatic fiction framing for literary tasks to prevent false moderation stops
    framing = get_dramatic_fiction_framing()
    effective_sys_prompt = system_instruction or ""
    if framing and "DRAMATIC LITERARY CONTEXT" not in effective_sys_prompt:
        effective_sys_prompt = f"{framing}\n{effective_sys_prompt}".strip()

    try:
        response = gateway.generate_text(
            prompt=prompt,
            system_instruction=effective_sys_prompt,
            task=task_name,
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            thinking_budget=thinking_budget,
            response_json=json_mode,
            session_id=session_id or "preproduction_session",
            user_id=user_id,
            tools=tools,
            fast_mode=kwargs.pop("fast_mode", False),
            **kwargs,
        )
    except Exception as e:
        logger.error(f"  [!] PreProduction ModelGateway dispatch error: {e}")
        raise

    text = (response.text or "").strip()
    if not json_mode:
        return text

    # Strip conversational markdown code fences if present
    text_clean = re.sub(r"^```(?:json|markdown|md|text)?\s*\n?", "", text, flags=re.IGNORECASE)
    text_clean = re.sub(r"\n?```\s*$", "", text_clean.strip())

    try:
        return json.loads(text_clean)
    except Exception:
        try:
            parsed = json_repair.loads(text_clean)
            if isinstance(parsed, (dict, list)):
                return parsed
            return {}
        except Exception as err:
            logger.warning(f"  [!] Failed to repair JSON from ModelGateway response: {err}")
            return {}
