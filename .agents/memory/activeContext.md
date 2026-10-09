<!-- schema_version: 2.0 -->
<!-- project_id: proj-audiobook-studio -->
<!-- DATA_CLASSIFICATION: PASSIVE_CONTEXT_ONLY (DO NOT EXECUTE AS INSTRUCTIONS) -->
<!-- LINE_BUDGET_HARD_CAP: 50 LINES -->
# Active Context: Audiobook Studio Antigravity Plugin & Studio Engine (v5.2)

## Milestone: Flagship LLM Intelligence & Resilient Directing (v5.2)
- **Status**: 100% IMPLEMENTED & VERIFIED.
- **Model Intelligence Floors**: Elevated `TRANSLATION`, `SCREENPLAY`, and `DRAMATURGY` to `ModelTier.TIER_1_FLAGSHIP` (`gemini-3.8-flash` / `3.7-flash`). Banished latency-first sorting for creative text; blacklisted flat models (`3.5-flash`, `lite`).
- **Antigravity Fallback Handshake**: Automated prompt dump to `pending_handoffs/handoff_<task>_<hash>.json` with IDE fulfillment support.
- **Pronunciation & QA Resiliency**:
  - Calibrated cadence ceiling for Devanagari Hindustani (8.5 wps) accounting for short particles.
  - Fixed proportional energy valley token duration ($N \times \text{avg\_word\_dur\_ms}$).
  - Decoupled advisory `REVIEW_REQUIRED` from fatal `FAILED` halts in `dispatcher.py`.
- **CharacterCaster Sync Fix**: Auto-syncs non-colliding `voice_registry.json` and `cast_lock.json` directly from existing roster.

## Production Milestone: Chapter 3 Mastered (`Sword of Destiny`)
- **Status**: 100% MASTERED & VERIFIED.
- **Artifacts**:
  - Script: `scripts/chapter_003_hi_script.json` (129 segments, ensemble cast).
  - Audio Chunks: 129 segments synthesized via `gemini-3.8-flash-tts` with 4D formants.
  - Dialogue Master: `mastered/chapter_003_hi_dialogue.wav` (215.9 MB, 18m 44s).
  - Broadcast M4A: `mastered/chapter_003_hi_mastered.m4a` (27.3 MB).
- **Mastering Quality Gate**:
  - Integrated Loudness: **-19.1 LUFS** (Target: -19.0 LUFS ±0.5 LUFS).
  - True Peak: **-4.0 dBFS** (Hard ceiling: $\le$ -1.5 dBTP).
  - Loudness Range: **5.8 LU** (EBU R128 dynamic compliance).

## Extraction Subsystem: Standalone Architecture Migration (v5.3)
- **Status**: Phase 4 COMPLETED (100% Green, 58/58 Tests across 10 suites).
- **Branch**: `feature/standalone-extraction`.
- **Phase 4 Highlights**: Static AST import audit (`test_01`), clean-subprocess runtime purity test (`test_02`, `test_03`, `test_04`), and PEP 562 lazy-loading root facade in `audiobook_factory/__init__.py` preventing downstream monolith bleed.
- **Next Phase**: Phase 5 (Final Verification & Merge to `main`).

