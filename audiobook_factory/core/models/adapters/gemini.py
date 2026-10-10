#!/usr/bin/env python3
"""
Audiobook Factory - Gemini Provider Adapter.
============================================
Handles direct integration with Google GenAI API (v1beta):
1. Applies Gemini 3.8 Thinking Token fix (thinkingBudget=0 for utility, 1024+ for creative text).
2. Fiction Safety Framing with BLOCK_NONE thresholds.
3. Official Stealth SDK Headers (google-genai-sdk-python/0.8.3).
4. Audio inlineData base64 decoding for Gemini Flash TTS.
5. Standardized GenerationResult and SpeechResult mappings.
"""

from __future__ import annotations
import json
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List, Tuple

from audiobook_factory.logger import logger
from audiobook_factory.core.models.adapters.base import (
    BaseProviderAdapter,
    GenerationResult,
    SpeechResult,
)
from audiobook_factory.core.models.anti_ban_guard import get_stealth_sdk_headers


class ApiHttpError(Exception):
    """Raised when provider returns HTTP error response."""
    def __init__(self, status_code: int, error_body: str, headers: Optional[Dict[str, str]] = None):
        super().__init__(f"HTTP {status_code}: {error_body[:200]}")
        self.status_code = status_code
        self.error_body = error_body
        self.headers = headers or {}


class GeminiProviderAdapter(BaseProviderAdapter):
    """Google Gemini API Provider Adapter."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def format_payload(
        self,
        model: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        thinking_budget: Optional[int] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        response_json: bool = False,
        is_audio: bool = False,
        voice_name: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Constructs Google Gemini v1beta JSON request payload."""
        parts = kwargs.get("parts")
        if not parts:
            parts = [{"text": prompt}]

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": parts
                }
            ]
        }

        # 1. System Instruction
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        # 2. Generation Config
        gen_config: Dict[str, Any] = {
            "temperature": temperature,
        }

        if max_output_tokens is not None:
            gen_config["maxOutputTokens"] = max_output_tokens

        if response_json:
            gen_config["responseMimeType"] = "application/json"

        # 3. Critical Gemini 3.8 Thinking Token Configuration
        # If thinking_budget == 0, explicitly disable thinking tokens to avoid empty output on small token limits
        if thinking_budget is not None:
            gen_config["thinkingConfig"] = {
                "thinkingBudget": thinking_budget
            }
        elif "3.8" in model or "3.7" in model:
            # Default thinking budget for 3.8/3.7 if not explicitly specified
            gen_config["thinkingConfig"] = {
                "thinkingBudget": 1024
            }

        # 4. Audio Modality & Voice Config (for Gemini Flash TTS)
        if is_audio:
            gen_config["responseModalities"] = ["AUDIO"]
            if voice_name:
                gen_config["speechConfig"] = {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": voice_name
                        }
                    }
                }

        payload["generationConfig"] = gen_config

        # 5. Fiction Safety Framing (BLOCK_NONE)
        payload["safetySettings"] = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        return payload

    def _execute_http_post(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Executes HTTP POST request via urllib with proper error capturing."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                resp_bytes = response.read()
                return json.loads(resp_bytes.decode("utf-8"))
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
        except urllib.error.URLError as e:
            raise ApiHttpError(status_code=503, error_body=str(e.reason)) from e

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
        timeout: float = 60.0,
        **kwargs,
    ) -> GenerationResult:
        """Generates text using Google Gemini API."""
        clean_model = model.strip()
        url = f"{self.BASE_URL}/{clean_model}:generateContent"
        headers = get_stealth_sdk_headers(api_key, provider="gemini")

        payload = self.format_payload(
            model=clean_model,
            prompt=prompt,
            system_instruction=system_instruction,
            thinking_budget=thinking_budget,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_json=response_json,
            is_audio=False,
            **kwargs,
        )

        resp = self._execute_http_post(url, payload, headers, timeout=timeout)

        # Parse text, thoughts, finish reason, and token usage
        candidates = resp.get("candidates", [])
        if not candidates:
            return GenerationResult(
                text="",
                finish_reason="NO_CANDIDATES",
                tokens_used=0,
                raw_response=resp,
                model_id=clean_model,
                provider="gemini",
            )

        cand = candidates[0]
        finish_reason = cand.get("finishReason", "UNKNOWN")
        content = cand.get("content") or {}
        parts = content.get("parts", [])

        text_parts: List[str] = []
        thought_parts: List[str] = []

        for p in parts:
            if "text" in p:
                if p.get("thought", False):
                    thought_parts.append(p["text"])
                else:
                    text_parts.append(p["text"])

        usage = resp.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)

        return GenerationResult(
            text="".join(text_parts),
            finish_reason=finish_reason,
            tokens_used=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            thoughts="".join(thought_parts),
            raw_response=resp,
            model_id=clean_model,
            provider="gemini",
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
        """Synthesizes speech audio using Gemini Flash TTS."""
        clean_model = model.strip()
        url = f"{self.BASE_URL}/{clean_model}:generateContent"
        headers = get_stealth_sdk_headers(api_key, provider="gemini")

        payload = self.format_payload(
            model=clean_model,
            prompt=text,
            is_audio=True,
            voice_name=voice_name,
            thinking_budget=0,  # TTS models do not use thinking tokens
            **kwargs,
        )

        resp = self._execute_http_post(url, payload, headers, timeout=timeout)

        candidates = resp.get("candidates", [])
        if not candidates:
            raise ValueError(f"Gemini TTS returned no candidates: {resp}")

        cand = candidates[0]
        content = cand.get("content") or {}
        parts = content.get("parts", [])

        audio_bytes = b""
        mime_type = "audio/wav"

        for p in parts:
            inline = p.get("inlineData")
            if inline and "data" in inline:
                import binascii
                try:
                    audio_bytes = base64.b64decode(inline["data"])
                except binascii.Error as e:
                    raise ValueError(f"Malformed base64 audio data: {e}")
                mime_type = inline.get("mimeType", "audio/wav")
                break

        if not audio_bytes:
            raise ValueError("No audio inlineData found in Gemini TTS response.")

        usage = resp.get("usageMetadata", {})
        total_tokens = usage.get("totalTokenCount", 0)

        # Estimate duration if WAV (48 bytes header, 24kHz 16-bit mono = 48,000 bytes/sec)
        dur = 0.0
        if len(audio_bytes) > 44:
            dur = max(0.1, len(audio_bytes) / 48000.0)

        return SpeechResult(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            sample_rate=24000,
            duration_sec=dur,
            tokens_used=total_tokens,
            model_id=clean_model,
            provider="gemini",
        )
