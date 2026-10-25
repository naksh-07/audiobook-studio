#!/usr/bin/env python3
"""
Audiobook Factory - TTS Core Orchestrator.
Central execution engine coordinating UniversalInputGuard, ModelAdapterRegistry,
model adapters, retries, concurrency limits, and TwoTierAudioQualityGate.
"""

from __future__ import annotations
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple, Optional, Union

from audiobook_factory.logger import logger
from audiobook_factory.tts.contracts import (
    CanonicalTTSRequest,
    SynthesizedAudioChunk,
    AudioValidationResult,
    TTSPipelineMode,
)
from audiobook_factory.tts.guard.input_guard import UniversalInputGuard
from audiobook_factory.tts.providers.registry import get_adapter_registry, ModelAdapterRegistry
from audiobook_factory.tts.quality_gate import TwoTierAudioQualityGate


class TTSCoreOrchestrator:
    """
    Core orchestrator shared across all client facades (Generic, LongForm, MultiCast).
    """

    def __init__(
        self,
        registry: Optional[ModelAdapterRegistry] = None,
        max_workers: int = 6,
        max_retries: int = 3,
    ):
        self.registry = registry or get_adapter_registry()
        self.max_workers = max_workers
        self.max_retries = max_retries

    def synthesize(
        self,
        request_or_text: Union[CanonicalTTSRequest, str],
        voice_id: str = "Puck",
        model: str = "gemini-3.8-flash-tts",
        speaker: str = "Narrator",
        pipeline_mode: TTSPipelineMode = TTSPipelineMode.GENERIC,
        validate_audio: bool = True,
        **guard_kwargs: Any,
    ) -> Tuple[SynthesizedAudioChunk, Optional[AudioValidationResult]]:
        """
        Orchestrates single-chunk synthesis through input guard, model adapter, and quality gate.
        """
        if isinstance(request_or_text, CanonicalTTSRequest):
            canonical_req = request_or_text
        else:
            canonical_req = UniversalInputGuard.sanitize_and_guard(
                raw_text=request_or_text,
                voice_id=voice_id,
                speaker=speaker,
                pipeline_mode=pipeline_mode,
                **guard_kwargs,
            )

        adapter = self.registry.get_adapter(model)
        last_error: Optional[Exception] = None
        last_validation: Optional[AudioValidationResult] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                # 1. Synthesize Audio
                chunk = adapter.synthesize_chunk(canonical_req)

                # 2. Quality Gate Verification
                if validate_audio:
                    validation = TwoTierAudioQualityGate.audit_chunk(canonical_req, chunk)
                    last_validation = validation

                    if not validation.passed and validation.status == "REGENERATE":
                        logger.warning(
                            f"[!] Chunk {canonical_req.segment_uid} failed Quality Gate (attempt {attempt}/{self.max_retries}): "
                            f"{'; '.join(validation.diagnostics)}"
                        )
                        time.sleep(0.5 * attempt)
                        continue

                    return chunk, validation

                return chunk, None

            except Exception as e:
                last_error = e
                logger.warning(f"[!] Synthesis attempt {attempt}/{self.max_retries} failed: {e}")
                time.sleep(0.75 * attempt)

        if last_validation and not last_validation.passed:
            raise RuntimeError(
                f"Audio generation failed Quality Gate after {self.max_retries} attempts: "
                f"{'; '.join(last_validation.diagnostics)}"
            )

        raise last_error or RuntimeError(f"TTS synthesis failed for segment '{canonical_req.segment_uid}'.")

    async def synthesize_async(
        self,
        request: CanonicalTTSRequest,
        model: str = "gemini-3.8-flash-tts",
        validate_audio: bool = True,
    ) -> Tuple[SynthesizedAudioChunk, Optional[AudioValidationResult]]:
        """Async variant of single-chunk synthesis."""
        return await asyncio.to_thread(
            self.synthesize,
            request_or_text=request,
            model=model,
            validate_audio=validate_audio,
        )

    def synthesize_batch(
        self,
        requests: List[CanonicalTTSRequest],
        model: str = "gemini-3.8-flash-tts",
        validate_audio: bool = True,
    ) -> List[Tuple[CanonicalTTSRequest, SynthesizedAudioChunk, Optional[AudioValidationResult]]]:
        """
        Executes concurrent synthesis for a batch of canonical requests, preserving original input ordering.
        """
        if not requests:
            return []

        results: Dict[str, Tuple[SynthesizedAudioChunk, Optional[AudioValidationResult]]] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_req = {
                executor.submit(self.synthesize, req, model=model, validate_audio=validate_audio): req
                for req in requests
            }

            for future in as_completed(future_to_req):
                req = future_to_req[future]
                try:
                    chunk, validation = future.result()
                    results[req.segment_uid] = (chunk, validation)
                except Exception as e:
                    logger.error(f"[X] Batch item {req.segment_uid} failed synthesis: {e}")
                    raise

        # Return results in the exact order of the incoming requests list
        ordered_results = []
        for req in requests:
            chunk, val = results[req.segment_uid]
            ordered_results.append((req, chunk, val))

        return ordered_results
