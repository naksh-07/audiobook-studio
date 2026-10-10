#!/usr/bin/env python3
"""
Audiobook Factory - Room 2: Translation ModelGateway Bridge.
=============================================================
The authoritative control-plane bridge for Option D Standalone Translation:
- TranslationEngine (Single-Pass Macro-Chunker & Parity Gate Runner)
- MultiAgentTranslationCollective (Deliberative Translation Room)
- LiteraryDraftTranslator, HindustaniCadenceSpecialist, SubtextAndIdiomDramaturge

Guarantees:
1. Strict ModelGateway Routing: Eliminates rogue urllib calls and routes 100% of LLM
   traffic through the Phase 1 control plane (ModelGateway.generate_text).
2. Atomic Key Leasing: Acquires Concurrency=1 mutual exclusion handles from KeyLeaseManager.
3. The 7 Iron Shields AntiBanGuard: Enforces token-bucket rate limiting (11 RPM), session
   affinity sticky binding across chunks of a chapter, and stealth SDK headers.
4. Permissive Creative Fiction Framing: Applies BLOCK_NONE safety thresholds for uninhibited
   literary translation, dramatic intensity, and earthy Hindustani dialect realism.
5. Graceful Standalone Fallback: Preserves offline mock execution and zero-dependency
   fallback if running outside the unified studio workspace.
"""

from __future__ import annotations
import os
import re
from typing import Any, Dict, List, Optional, Union

from audiobook_factory.logger import logger
from audiobook_factory.safety import get_dramatic_fiction_framing


def execute_translation_llm(
    prompt: str,
    system_instruction: Optional[str] = None,
    task: str = "translation",
    model: Optional[str] = None,
    temperature: float = 0.35,
    max_output_tokens: Optional[int] = 16384,
    thinking_budget: Optional[int] = 1024,
    session_id: Optional[str] = None,
    user_id: str = "translation_worker",
    **kwargs: Any,
) -> str:
    """
    Executes a Room 2 Translation LLM request strictly through ModelGateway.
    Returns clean translated Devanagari Hindi text.
    """
    is_mock = os.environ.get("MOCK_OFFLINE", "").lower() in ("true", "1")
    if is_mock or os.environ.get("GEMINI_API_KEY", "").startswith("mock"):
        return "यह एक ऑफ़लाइन मॉक अनुवादित पाठ है।"

    # Inject dramatic fiction framing to ensure BLOCK_NONE safety across models
    framing = get_dramatic_fiction_framing()
    effective_sys_prompt = system_instruction or ""
    if framing and "DRAMATIC LITERARY CONTEXT" not in effective_sys_prompt:
        effective_sys_prompt = f"{framing}\n{effective_sys_prompt}".strip()

    # Filter and normalize legacy kwargs from old llm_client interfaces
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
            response_json=False,
            session_id=session_id or "translation_session",
            user_id=user_id,
            max_retries=retries,
            **kwargs,
        )
        raw_text = (response.text or "").strip()
    except ImportError:
        logger.warning("  [!] ModelGateway not available in standalone environment. Using direct HTTP fallback.")
        from audiobook_factory.translation.engine import TranslationEngine
        raw_text = TranslationEngine(model_name=model)._direct_gemini_call(
            user_prompt=prompt,
            system_instruction=effective_sys_prompt,
            thinking_budget=thinking_budget or 1024,
            temperature=temperature,
        )
    except Exception as e:
        logger.error(f"  [!] Translation ModelGateway dispatch failed: {e}")
        raise

    # Robustly sanitize markdown fences and preambles (handles truncated responses)
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:markdown|json|md|text)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = re.sub(
        r"^(?:Here is the translation:?|Certainly,? here is the translation:?|Below is the translated text:?)\s*\n+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()
