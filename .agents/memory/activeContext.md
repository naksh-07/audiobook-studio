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

## Extraction & Podcast Subsystem: Standalone Architecture & Scientific Audio (v5.5)
- **Status**: 100% IMPLEMENTED, VERIFIED & DOCUMENTED (`main`).
- **Pillar 1 Standalone**: Package `audiobook_factory/extraction/` with contracts, engine, parsers (epub, text, pdf), normalizer, segmenter, and quality gate.
- **Scientific & Podcast Ready**: Structured Markdown tables, LaTeX equations ($E=mc^2$), abstracts, and callouts (`BlockType: table, equation, abstract, callout`). Whitelisted Greek/math symbols in `PDFQualityAnalyzer` (0 false OCR halts). Upgraded `GeminiVisionPDFExtractor` multimodal technical prompt.
- **Phase 1 Benchmark Validated**: Ingested `benchmarks/sample_research_paper.md` with 100% AST typing (`table`, `equation`, `abstract`, `callout`), full LaTeX metadata, and Gate 0.1 PASS.
- **Phase 2 Technical Verbalization Bridge**: Implemented `audiobook_factory/podcast/` (`MathVerbalizer`, `TableVerbalizer`, `AbstractCalloutVerbalizer`, `PodcastScriptBuilder`) generating dual-host screenplay JSON with spoken math and auditory table insights.
- **Phase 3 Multi-Voice Audio Production & EBU R128 Mastering**: Implemented `PodcastAudioProducer` (`audiobook_factory/podcast/producer.py`) with 12ms/18ms Hann micro-fading, conversational turn pauses, multi-host casting (Charon/Aoede), and two-pass linear EBU R128 loudnorm mastering (-19.0 LUFS, -1.5 dBTP). Verified on benchmark paper (22 turns, 275.4s audio).
- **Phase 4 Unified CLI & Autonomous Orchestrator**: Implemented `PodcastOrchestrator` (`audiobook_factory/podcast/orchestrator.py`) and dedicated CLI (`audiobook_factory/podcast/cli.py` & `audiobook_cli.py podcast <file>`) for 1-shot document $\to$ mastered podcast production.
- **Verification & Audit**: 96/96 full-suite tests PASSING (100% green). Adversarial bug audit and boundary isolation verified by subagent team.

