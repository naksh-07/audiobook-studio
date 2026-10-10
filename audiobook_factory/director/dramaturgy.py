from __future__ import annotations
"""
Backward-compatibility shim for SoundDesignDirectorMixin.
Note: Audio sound design / music spotting / foley planning is now located in sound_design_director.py
to distinguish it from literary dramaturgy in audiobook_factory/dramaturgy/.
"""
from audiobook_factory.director.sound_design_director import SoundDesignDirectorMixin

# Backward compatibility alias
DramaturgyMixin = SoundDesignDirectorMixin

__all__ = ["SoundDesignDirectorMixin", "DramaturgyMixin"]
