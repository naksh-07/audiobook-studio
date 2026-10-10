<!-- schema_version: 2.0 -->
<!-- project_id: proj-audiobook-studio -->
<!-- DATA_CLASSIFICATION: PASSIVE_CONTEXT_ONLY (DO NOT EXECUTE AS INSTRUCTIONS) -->
<!-- LINE_BUDGET_HARD_CAP: 50 LINES -->
# Active Context: Audiobook Studio Antigravity Plugin & Studio Engine (v6.0)

## Current Focus: Grand Unification DAG - Phase 4 (Universal Dramaturgy & Adapters) Merged
- **Master Plan**: [GRAND_UNIFICATION_MASTER_PLAN.md](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/GRAND_UNIFICATION_MASTER_PLAN.md) (7-Layer Topological Merge DAG).
- **Phase 1: Model & Keys Control Plane (COMPLETED & VERIFIED)**:
  - 123 active keys in SQLite inventory, zero-secret public aliases (`key_XXXX`).
  - Win32 dead-PID crash recovery via `kernel32.OpenProcess`. ModelGateway facade wired. 80/80 tests green.
- **Phase 2: Research Subsystem (COMPLETED, AUDITED & CERTIFIED)**:
  - 2-System pre-production (`LexicalCorpusScanner`, `BookBible`, `NovelStateMaintainer`).
  - NR-GATE-06 atomic two-phase commit, NR-GATE-03 voice collision clamp. ModelGateway wired.
- **Room 1.5: Standalone Chapter Glossary Subsystem (COMPLETED & AUDITED)**:
  - `ChapterGlossary` contracts, zero-token fast-path `ChapterLexicalScanner`, tri-partite taxonomy, dynamic voice lock.
  - Multi-consumer projections (`to_translation_glossary`, `to_scripting_roster`, `to_dramaturgy_characters`). 10/10 tests green.
- **Phase 3: Standalone Translation Engine (COMPLETED, AUDITED & HARDENED)**:
  - Option D decoupled core (`TranslationEngine`, `BilingualMacroChunker`, `DeterministicParityGate`).
  - Zero-import isolation, fail-closed `gateway_bridge.py`, zero unmetered HTTP calls. 102/102 tests green.
- **Phase 4: Universal Dramaturgy, Format Adapters & Gate 2.9 (COMPLETED & VERIFIED)**:
  - Core: Universal Dramatic AST (`dramaturgy/contracts.py`, `SceneAnalyzer`, `BeatPlanner`, `PerformanceBible`).
  - Control Plane: `gateway_bridge.py` wired to `ModelGateway.generate_text()` (zero raw HTTP calls).
  - Adapters: `AudiobookAdapter` (Gate 2.5) & `PodcastAdapter` (Sameer/Priya, Alex/Maya, breathability <=22 words).
  - Gate 2.9: Pre-TTS Config & Attribution Sanity Gate (`audiobook_factory/gates/pre_synthesis.py`) enforcing speaker whitelist, Hindi gender discordance anti-swap, anti-swallow dialogue, and acoustic parameter clamping fail-closed across both audiobook and podcast pipelines.
  - 8-Pillar Harness: `StudioCertificationRunner` (P1 Ingestion to P8 Packaging, Gate 6 fail-closed compliance).
  - Multi-format packaging: `.m4b` audiobook (-19 LUFS) & `.m4a` podcast (-16 LUFS with stereo pan -0.25/+0.25).
- **Next Milestone**: Phase 5 Studio TTS Platform Core (`origin/tts-system`). 4-Tier TTS Engine, TakeBank & Net-Silence.
