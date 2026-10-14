#!/usr/bin/env python3
"""
Audiobook Factory - OpenAI-Compatible Provider Adapter.
=======================================================
Supports:
- Cerebras Wafer-Scale Fast Inference (Llama 3.3 70B, Llama 3.1 8B)
- Groq LPU Ultra-Low Latency Inference
- OpenAI (GPT-4o, GPT-4o-mini)
- OpenRouter Multi-Model Routing
"""

from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List

from audiobook_factory.logger import logger
from audiobook_factory.core.models.adapters.base import (
    BaseProviderAdapter,
    GenerationResult,
    SpeechResult,
)
from audiobook_factory.core.models.adapters.gemini import ApiHttpError
from audiobook_factory.core.models.anti_ban_guard import get_stealth_sdk_headers


PROVIDER_BASE_URLS: Dict[str, str] = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "cerebras": "https://api.cerebras.ai/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}


class OpenAICompatibleAdapter(BaseProviderAdapter):
    """Adapter for OpenAI and OpenAI-compatible REST endpoints."""

    def __init__(self, provider: str = "cerebras"):
        self.provider = provider.lower().strip()
        self.base_url = PROVIDER_BASE_URLS.get(self.provider, PROVIDER_BASE_URLS["openai"])

    def format_payload(
        self,
        model: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        thinking_budget: Optional[int] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        response_json: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Constructs OpenAI-compatible chat completion payload."""
        messages: List[Dict[str, str]] = []

        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_output_tokens is not None:
            payload["max_tokens"] = max_output_tokens

        if response_json:
            payload["response_format"] = {"type": "json_object"}

        return payload

    def generate_text(
        self,
        model: str,
        prompt: str,
        api_key: str,
        system_instruction: Optional[str] = None,
        thinking_budget: Optional[int] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        response_json: bool = False,
        timeout: float = 180.0,
        **kwargs,
    ) -> GenerationResult:
        """[DISABLED BY SYSTEM POLICY] Executes chat completion via OpenAI-compatible API."""
        # ponytail: root deadbolt - adapter-level guard
        raise RuntimeError("External text API calls are disabled. Only Gemini Flash TTS is permitted.")

        payload = self.format_payload(
            model=clean_model,
            prompt=prompt,
            system_instruction=system_instruction,
            thinking_budget=thinking_budget,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_json=response_json,
            **kwargs,
        )

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base_url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=eff_timeout) as response:
                resp_bytes = response.read()
                resp = json.loads(resp_bytes.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise ApiHttpError(status_code=500, error_body=f"Invalid JSON response: {str(e)}") from e
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            resp_headers = dict(e.headers.items()) if e.headers else {}
            raise ApiHttpError(status_code=e.code, error_body=error_body, headers=resp_headers) from e
        except (TimeoutError, urllib.error.URLError) as e:
            err_msg = str(getattr(e, "reason", e))
            status = 504 if ("timed out" in err_msg.lower() or isinstance(e, TimeoutError)) else 503
            raise ApiHttpError(status_code=status, error_body=err_msg) from e

        choices = resp.get("choices", [])
        if not choices:
            return GenerationResult(
                text="",
                finish_reason="NO_CHOICES",
                tokens_used=0,
                raw_response=resp,
                model_id=clean_model,
                provider=self.provider,
            )

        choice = choices[0]
        message = choice.get("message") or {}
        text = message.get("content") or ""
        finish_reason = choice.get("finish_reason", "stop")

        usage = resp.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        return GenerationResult(
            text=text,
            finish_reason=finish_reason,
            tokens_used=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_response=resp,
            model_id=clean_model,
            provider=self.provider,
        )

    def synthesize_speech(
        self,
        model: str,
        text: str,
        voice_name: str,
        api_key: str,
        timeout: float = 60.0,
        **kwargs,
    ) -> SpeechResult:
        """TTS not supported directly on standard OpenAI compatible text endpoints."""
        raise NotImplementedError(f"Speech synthesis not supported on provider '{self.provider}'.")
