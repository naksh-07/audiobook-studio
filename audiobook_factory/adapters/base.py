#!/usr/bin/env python3
"""
Audiobook Factory - Script Adapters: Base Abstract Adapter Contract.
Defines the standard interface for converting literary Dramaturgy ASTs into
format-specific script representations (Audiobook, Podcast, Audio Drama, etc.).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from audiobook_factory.dramaturgy.contracts import DramaticPlan, DramaticValidationResult


class BaseScriptAdapter(ABC):
    """
    Abstract contract for Format-Specific Script Adapters in Option C Architecture.
    Adapters consume the shared literary Dramaturgy AST (DramaticPlan) and generate
    specialized, broadcast-ready script segments for downstream TTS and mastering.
    """
    adapter_id: str = "base"
    format_name: str = "Base Script Format"

    def pre_adapt(
        self,
        chapter_text: str,
        dramatic_plan: DramaticPlan,
        **kwargs,
    ) -> Dict[str, Any]:
        """Lifecycle hook executed immediately prior to format transformation."""
        return kwargs

    @abstractmethod
    def adapt(
        self,
        chapter_text: str,
        dramatic_plan: DramaticPlan,
        character_roster: Optional[Dict[str, Any]] = None,
        memory_context: Optional[Any] = None,
        is_hindi: bool = False,
        chapter_num: int = 1,
        chapter_id: str = "chapter_001",
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Transforms source chapter text and dramatic plan into format-specific script segments.

        Args:
            chapter_text: Full raw or normalized chapter source text.
            dramatic_plan: The unified chapter Dramaturgy AST.
            character_roster: Optional character dictionary or entity registry.
            memory_context: Optional episodic/long-term memory bank.
            is_hindi: Flag indicating target delivery language.
            chapter_num: 1-indexed chapter integer.
            chapter_id: Unique chapter string identifier.

        Returns:
            List of standardized screenplay/podcast segment dictionaries.
        """
        pass

    def post_adapt(
        self,
        segments: List[Dict[str, Any]],
        dramatic_plan: DramaticPlan,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Lifecycle hook executed immediately following format transformation."""
        return segments

    def validate(
        self,
        segments: List[Dict[str, Any]],
        dramatic_plan: DramaticPlan,
        source_text: str = "",
        known_characters: Optional[List[str]] = None,
        memory_context: Optional[Any] = None,
        **kwargs,
    ) -> DramaticValidationResult:
        """Runs Gate 2.5 DramaticValidator to verify screenplay integrity."""
        from audiobook_factory.dramaturgy.dramatic_validator import DramaticValidator
        return DramaticValidator.validate_screenplay_and_plan(
            segments=segments,
            dramatic_plan=dramatic_plan,
            source_text=source_text,
            known_characters=known_characters,
            memory_context=memory_context,
        )
