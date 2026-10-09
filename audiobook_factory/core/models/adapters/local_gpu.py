#!/usr/bin/env python3
"""
Audiobook Factory - Local GPU Hardware Adapter.
===============================================
Wraps local neural inference (Spark Local LLM, MMS Forced Alignment)
with HardwareVRAMGuard mutex protection to prevent CUDA OOM on NVIDIA RTX 4050 6GB.
"""

from __future__ import annotations
import threading
from typing import Dict, Any, Optional

from audiobook_factory.logger import logger
from audiobook_factory.core.models.adapters.base import (
    BaseProviderAdapter,
    GenerationResult,
    SpeechResult,
)


class HardwareVRAMGuard:
    """
    Workstation Hardware & VRAM Guard for NVIDIA RTX 4050 Laptop GPU (6 GB VRAM).
    Enforces a strict mutual exclusion semaphore across local neural inference
    preventing CUDA OOM and thread collisions.
    """
    _gpu_semaphore = threading.Semaphore(1)
    _active_job: Optional[str] = None
    _lock = threading.Lock()

    @classmethod
    def acquire(cls, job_name: str, timeout: float = 60.0) -> bool:
        """Acquires exclusive hardware GPU lock."""
        acquired = cls._gpu_semaphore.acquire(timeout=timeout)
        if acquired:
            with cls._lock:
                cls._active_job = job_name
            logger.debug(f"  [GPU GUARD] Exclusive lock acquired for: {job_name}")
        else:
            logger.warning(f"  [GPU GUARD] Hardware lock timeout waiting for: {job_name}")
        return acquired

    @classmethod
    def release(cls, job_name: str = ""):
        """Releases hardware lock and triggers CUDA garbage collection."""
        with cls._lock:
            cls._active_job = None
        try:
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
        except Exception:
            pass
        finally:
            cls._gpu_semaphore.release()
            logger.debug("  [GPU GUARD] Hardware lock released. VRAM evacuated.")


class LocalGpuAdapter(BaseProviderAdapter):
    """Adapter for local CUDA neural inference models."""

    def format_payload(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        return {"model": model, "prompt": prompt}

    def generate_text(
        self,
        model: str,
        prompt: str,
        api_key: str = "LOCAL_GPU",
        system_instruction: Optional[str] = None,
        timeout: float = 60.0,
        **kwargs,
    ) -> GenerationResult:
        """Executes local text generation with GPU lock."""
        clean_model = model.strip()
        acquired = HardwareVRAMGuard.acquire(f"generate_text:{clean_model}", timeout=timeout)
        if not acquired:
            raise TimeoutError(f"Could not acquire GPU lock for {clean_model} within {timeout}s.")

        try:
            # Placeholder or local engine invocation
            text = f"[LOCAL_GPU_OUTPUT for {clean_model}]: Processed {len(prompt)} chars."
            return GenerationResult(
                text=text,
                finish_reason="stop",
                tokens_used=len(prompt) // 4,
                model_id=clean_model,
                provider="local",
            )
        finally:
            HardwareVRAMGuard.release(f"generate_text:{clean_model}")

    def synthesize_speech(
        self,
        model: str,
        text: str,
        voice_name: str,
        api_key: str = "LOCAL_GPU",
        timeout: float = 60.0,
        **kwargs,
    ) -> SpeechResult:
        """Executes local audio/alignment generation with GPU lock."""
        clean_model = model.strip()
        acquired = HardwareVRAMGuard.acquire(f"synthesize_speech:{clean_model}", timeout=timeout)
        if not acquired:
            raise TimeoutError(f"Could not acquire GPU lock for {clean_model} within {timeout}s.")

        try:
            # Generates mock audio bytes for test/local
            return SpeechResult(
                audio_bytes=b"RIFF" + b"\x00" * 44,
                mime_type="audio/wav",
                sample_rate=24000,
                duration_sec=1.0,
                tokens_used=len(text) // 4,
                model_id=clean_model,
                provider="local",
            )
        finally:
            HardwareVRAMGuard.release(f"synthesize_speech:{clean_model}")
