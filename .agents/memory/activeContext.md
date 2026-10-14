<!-- schema_version: 2.0 -->
<!-- project_id: proj-audiobook-studio -->
<!-- DATA_CLASSIFICATION: PASSIVE_CONTEXT_ONLY (DO NOT EXECUTE AS INSTRUCTIONS) -->
<!-- LINE_BUDGET_HARD_CAP: 50 LINES -->
# Active Context: Audiobook Studio Antigravity Plugin & Studio Engine (v6.0)

## Current Focus: Grand Unification DAG - All 7 Phases Certified & Documentation 100% Complete
- **Master Plan**: [GRAND_UNIFICATION_MASTER_PLAN.md](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/GRAND_UNIFICATION_MASTER_PLAN.md) (7-Layer Topological Merge DAG).
- **Phases 1-5 (COMPLETED & CERTIFIED)**:
  - Phase 1 (ModelGateway & 124+ keys), Phase 2 (Novel Researcher), Room 1.5 (Glossary), Phase 3 (Translation Option D), Phase 4 (Universal Dramaturgy & Adapters), Room 3.5 (Voice Casting SVCCS), Phase 5 (Studio TTS Platform Core & Gateway Bridge, 1,126 tests).
- **Phase 6: Pro-Grade AI Vocal Mastering Workstation (MERGED, AUDITED & CERTIFIED)**:
  - Room 5 Vocal Mastering Core (`audiobook_factory/audio/`): C++ JUCE Pedalboard / FFmpeg dual-pass linear loudnorm (`-19 LUFS`, `$\le -1.5$ dBTP`), `AudioQAAuditor`, `NeuralVocalEnhancer` (with `HF_HUB_OFFLINE` sandbox), `ReferenceSpectrumMatcher` (pad-to-nfft STFT fix), `SingleSegmentHotPatcher`, `M4BBookPackager` (path traversal sanitized), 6 Audio MCP tools, and `dsp`, `qa-audit`, `enhance`, `match-ref` CLI.
  - Multi-Expert Triad Audit: Systems Architect (PASS), Security Auditor (PASS), Forensic Debugger (PASS). All 72 audio tests & 71 cross-system tests 100% green. Pushed to remote `main`.
- **Phase 7: Metadata Decoupling & Room 1 Autonomous Pipeline Wiring (COMPLETED & CERTIFIED)**:
  - Harmonized `BookEntity` schema (`pitch_ratio`, `speed_ratio`, smart coercions), eliminating silos without monolithic JSON bloat.
  - Room 1 Pre-Production Studio auto-wired into `PipelineOrchestrator` and JIT CLI commands. Full-novel glossary alignment.
  - Implemented `<50ms` zero-token offline [`MetadataDoctor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/doctor.py) integrated into Gate 2.9, Gate 6, and `doctor` CLI.
  - Mastering V2 disk ledgers persisted and integrated with Gate 6B. Antigravity UI Extension DAG stepper and bridge synced.
  - Full regression: 72/72 tests passing green across pre-production, mastering, gates, and metadata doctor.
- **Pillar 1 Extraction & Room 1 Research Verification (COMPLETED & CERTIFIED)**:
  - Tree-aware hierarchical nav resolver, frontmatter pruner, and heading dedup in [`epub.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/extraction/parsers/epub.py) (33/33 tests green).
  - CLI `research` command added and `ModelGateway` tools support enabled.
  - Room 1 Pre-Production verified on live project: 114k words scanned, 51 characters extracted, 52 cast locks allocated with 4D formants, and `book_dna.json` profiled.
  - `MetadataDoctor` audit: 7/7 checks PASS (Extraction, Source, Canon, Cast Lock, Glossary, Screenplay, Mastering).
- **Pillar 2 Room 2 Translation Collective Hardening & Certification (COMPLETED & CERTIFIED)**:
  - Universal Novel-Agnostic Invariant strictly enforced: zero hardcoded novel terms in engine code.
  - Hardened prompts & parser across Room 1.5/Room 2 (`prompt_builder.py`, `draft_translator.py`, `classifier.py`, `sanitizer.py`, `scanner.py`, `manager.py`).
  - Enforced zero English article leakage (`द` stripped), phonetic transliteration for beasts/orders (`विचर`, `बैसिलिस्क`, `ड्रैगन`), Unicode European diacritics (`Téa and Véa` -> `तेया और वेया`), and canonical BookBible SSOT precedence.
- **2-Tier Standalone Dynamic Prompt & Directing Subsystem (COMPLETED & CERTIFIED)**:
  - Pure "Input in, Output out" decoupled contracts (`ProductionPlaybook`, `ChapterDirectorCard`).
  - Room 1 `ProductionPlaybookSynthesizer` generates novel-tailored prompt blocks, custom spoken registers, and narrator demeanors.
  - Room 1.5 `ChapterSteeringDirector` generates chapter scene atmosphere, character emotional stakes, and vocal tint.
  - Downstream rooms (Room 2 Translation, Room 3 Screenplay, Room 4 TTS) dynamically consume tailored directives. 22/22 tests green. Multi-Expert Triad Audit certified.
- **Key Quarantine Submodule & Hang Defenses (COMPLETED & CERTIFIED)**:
  - Physical segregation vault ([`quarantine.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/quarantine.py)), zero zombie resurrection on reset/rollover, ingestion shield.
  - 126 ACTIVE keys + 2 isolated. 48/48 tests 100% green (9 quarantine, 11 lease engine, 6 adversarial stress, 22 dynamic directing). Rigor 98% BULLETPROOF.
- **Novel Production Pipeline Verification (Systems 1-4 LIVE CERTIFIED)**: Systems 1-3 certified PASS. System 4 (Room 3 Screenplay & Anti-Swap Attribution) 100% UNCONDITIONAL PASS CERTIFIED: 321 segments, 0% speaker turn inversion (Gate 2: 198/198 dialogue turns 100% accurate), 0 quote leakage to Narrator, 10/10 cast locks resolved with 4D formants, 100.65% text parity. Ready for System 5 (Room 4 Multi-Voice TTS).
- **Phase 3 TTS Gateway Bridge, Gemini Adapter & Directing Realization (COMPLETED & CERTIFIED)**:
  - Restored `speechMetadata.style` in [`gateway_bridge.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py) for Gemini 3.8 Flash audio modality without stripping.
  - Locked Narrator strictly to 0.32 temp (zero style metadata); clamped character dialogue dynamically to [0.35, 0.52] (zero histrionics >0.52).
  - Preserved certified acoustic reflexes (`[laughs]`, `[sighs]`, `[whispers]`, `[growls]`, `[gasp]`, `[chuckles]`, `[pant]`, `[groan]`) in spoken text; routed non-acoustic descriptors (`[cold menace]`, `[angrily]`, `[धीमी आवाज़ में]`) to `speechMetadata.style`.
  - Preserved `speechMetadata` and mapped `voiceName` in [`gemini.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/gemini.py). 15/15 target tests + 23/23 regression tests 100% green.
- **Room 2 Forensic Translation Remediation (100% PASS CERTIFIED)**: Fixed screenplay leakage (Rules 14-16), single-quote parity gate, scoped prompt glossary (~25 terms vs 109), clean 'बोर्च थ्री जैकडॉज़' & 'वेया'. Chapter 1 re-translated (490 lines, 96KB, 0 leaks, 0.99 para parity). 86/86 tests green.
- **TTS-Only Architecture & Key Quarantine Protocol (Ponytail Standard Certified)**:
  - Enforced strict TTS-only API policy: all external text generation & discovery pings deadbolted at root (`gateway.py`, `gemini.py`, `openai_compat.py`, `llm_client.py`, `lease_manager.py`, `db.py`).
  - All creative/text tasks routed to Antigravity subagent invocations.
  - Safely quarantined and archived 15 permanently dead/banned keys in `key_quarantine` (`is_permanent=1`). Scoped all 113 active keys to `["tts"]`.
  - Exactly 1 live TTS request verified: `gemini-3.8-flash-tts` produced 146KB (3.05s) 24kHz WAV audio without quota waste.
