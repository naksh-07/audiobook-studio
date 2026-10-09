#!/usr/bin/env python3
"""
Audiobook Factory - Audio Mixing & Production Subsystem (Pure Vocals-Only Engine v5.3).
Exporting contracts, ingestion manager, streaming composer, and dialogue editorial bridge.
"""

from .contracts import (
    SegmentAudioContract,
    ChapterMasterContract,
    IngestionConfig,
)
from .ingestion import AudioIngestionManager
from .stream_composer import ChunkStreamComposer
from .editorial import DialogueEditorialBridge
from .encoder import ChapterDeliveryEncoder
from .packager import M4BBookPackager
from .ledger import (
    SegmentLedgerEntry,
    ChapterSegmentLedger,
    LedgerDiffResult,
    compute_segment_content_hash,
)
from .hot_patcher import SingleSegmentHotPatcher, HotPatchResult

__all__ = [
    "SegmentAudioContract",
    "ChapterMasterContract",
    "IngestionConfig",
    "AudioIngestionManager",
    "ChunkStreamComposer",
    "DialogueEditorialBridge",
    "ChapterDeliveryEncoder",
    "M4BBookPackager",
    "SegmentLedgerEntry",
    "ChapterSegmentLedger",
    "LedgerDiffResult",
    "compute_segment_content_hash",
    "SingleSegmentHotPatcher",
    "HotPatchResult",
]

