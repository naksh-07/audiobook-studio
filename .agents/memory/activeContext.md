<!-- schema_version: 2.0 -->
<!-- project_id: proj-audiobook-studio -->
<!-- DATA_CLASSIFICATION: PASSIVE_CONTEXT_ONLY (DO NOT EXECUTE AS INSTRUCTIONS) -->
<!-- LINE_BUDGET_HARD_CAP: 50 LINES -->
# Active Context: Audiobook Studio Antigravity Plugin & Studio Engine (v5.2)

## Production Milestone: Chapter 3 Mastered (`Sword of Destiny`)
- **Status**: 100% MASTERED & VERIFIED.
- **Artifacts**: Script (129 segs), Audio Chunks (129 gemini-3.8-flash-tts with 4D formants), Dialogue Master (`chapter_003_hi_dialogue.wav`, 215.9 MB, 18m 44s), M4A (`chapter_003_hi_mastered.m4a`, 27.3 MB).
- **Mastering**: Integrated: **-19.1 LUFS**, True Peak: **-4.0 dBFS**, Dynamic Range: **5.8 LU** (EBU R128 compliance).

## Milestone: TTS Platform Core (Phases 1 - 5 + Multi-Expert Audit Certified)
- **Status**: 100% GREEN CERTIFIED (**882 / 882 repository tests passed, 0 failures, 0 regressions**).
- **Architecture**: Option C (Layered Shared Core with Specialized Pipeline Facades).
  - **Tier 1 (Facades)**: `GenericTTSClient` (ad-hoc / byte stream), `LongFormTTSClient` (4-tier prose stream, resume checkpoints), `MultiCastStudioClient` (ensemble casting, Anime Seiyū child mapping, anti-swap QA).
  - **Tier 2 (Orchestration & Guards)**: `UniversalInputGuard` (sacred vs spoken text immutability, numeral/token expander), `SemanticProseChunker` (4-tier hierarchy, zero word cuts), `TokenBucketRateLimiter` (120+ key pool round-robin).
  - **Tier 3 (Pluggable Adapters)**: `GeminiTTSAdapter` (120+ keys, `BLOCK_NONE`, directing style NLP), `QwenTTSAdapter` (VRAM guard & simulation fallback), `ModelAdapterRegistry` (3.8 → 2.5 → 2.0 fallback cascade).
  - **Tier 4 (Editorial DSP & QA)**: `TwoTierAudioQualityGate` (-52dBFS RMS, DC bias, clipping rails, dead-air <2.5s, phonetic probe), `EditorialDSPEngine` (Hann micro-fades 12/18ms, Net-Silence gap calculator), `FormantSculptor` (4D parametric EQ biquad curves), `TakeBankManager` (multi-variant auditioning), `audio_master` (EBU R128 -19 LUFS / -1.5 dBTP).
  - **Tier 5 (Wiring & Compatibility)**: `audiobook_factory.tts` and `audiobook_factory.tts_dispatcher` unified exports; zero breaking changes for CLI (`audiobook_cli.py`) and orchestrators.
- **Multi-Expert Audit Remediations Applied**:
  - Boundary: Clarified Room 4 produces `dialogue_stem`; Room 5 executes broadcast EBU R128 mastering.
  - Bug Fixes: `candidates[0].get("content") or {}` NoneType guard, empty takes handling, ZeroCrossing boundary fix (`editorial.py:34`), FormantSculptor headroom pre-attenuation and float-domain preservation.

## Antigravity Studio Plugin & UI Extension
- **Live Extension**: Registered at `~/.gemini/config/plugins/audiobook-studio/` (`@audiobook-director`, `audiobook-studio` skill, Stitch-grade sidecar panel).
