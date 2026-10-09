#!/usr/bin/env python3
"""
Audiobook Factory - Audio Mixing & Production Subsystem (Pure Vocals-Only Engine v5.3).
Exporting contracts, ingestion manager, streaming composer, and dialogue editorial bridge.
"""

from .contracts import (
    SegmentAudioContract,
    ChapterMasterContract,
    IngestionConfig,
    DSPConfig,
    DSPMasteringResult,
    AudioQAConfig,
    SegmentQAEvaluation,
    ChapterQAReport,
    EnhancerConfig,
    ReferenceMatcherConfig,
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
from .dsp import (
    VocalDSPProcessor,
    has_pedalboard_engine,
    has_pyloudnorm_engine,
)
from .qa_auditor import (
    AudioQAAuditor,
    has_whisper_engine,
)
from .enhancer import (
    NeuralVocalEnhancer,
    has_deepfilter_engine,
)
from .reference_matcher import (
    ReferenceSpectrumMatcher,
    has_matchering_engine,
)

__all__ = [
    "SegmentAudioContract",
    "ChapterMasterContract",
    "IngestionConfig",
    "DSPConfig",
    "DSPMasteringResult",
    "AudioQAConfig",
    "SegmentQAEvaluation",
    "ChapterQAReport",
    "EnhancerConfig",
    "ReferenceMatcherConfig",
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
    "VocalDSPProcessor",
    "has_pedalboard_engine",
    "has_pyloudnorm_engine",
    "AudioQAAuditor",
    "has_whisper_engine",
    "NeuralVocalEnhancer",
    "has_deepfilter_engine",
    "ReferenceSpectrumMatcher",
    "has_matchering_engine",
]

