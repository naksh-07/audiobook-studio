#!/usr/bin/env python3
"""
Audiobook Factory - Script Adapters Package.
Provides format-specific adapters converting Dramaturgy ASTs into broadcast scripts.
"""

from __future__ import annotations
from typing import Dict, Type, Optional, List
from audiobook_factory.adapters.base import BaseScriptAdapter
from audiobook_factory.adapters.audiobook import AudiobookAdapter
from audiobook_factory.adapters.podcast import PodcastAdapter

_ADAPTER_REGISTRY: Dict[str, Type[BaseScriptAdapter]] = {
    "audiobook": AudiobookAdapter,
    "podcast": PodcastAdapter,
}


def register_adapter(adapter_id: str, adapter_cls: Type[BaseScriptAdapter]) -> None:
    """Register a custom script adapter."""
    _ADAPTER_REGISTRY[adapter_id.lower().strip()] = adapter_cls


def unregister_adapter(adapter_id: str) -> Optional[Type[BaseScriptAdapter]]:
    """Unregister an adapter by ID."""
    return _ADAPTER_REGISTRY.pop(adapter_id.lower().strip(), None)


def list_registered_adapters() -> List[str]:
    """Returns a list of all registered adapter identifiers."""
    return sorted(list(_ADAPTER_REGISTRY.keys()))


def get_adapter(adapter_id: str = "audiobook", **kwargs) -> BaseScriptAdapter:
    """Instantiate a registered script adapter by ID."""
    clean_id = adapter_id.lower().strip()
    if clean_id not in _ADAPTER_REGISTRY:
        raise ValueError(f"Unknown script adapter '{adapter_id}'. Registered adapters: {list_registered_adapters()}")
    return _ADAPTER_REGISTRY[clean_id](**kwargs)


__all__ = [
    "BaseScriptAdapter",
    "AudiobookAdapter",
    "PodcastAdapter",
    "register_adapter",
    "unregister_adapter",
    "list_registered_adapters",
    "get_adapter",
]
