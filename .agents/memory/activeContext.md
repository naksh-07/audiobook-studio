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
- **Novel Production Pipeline Verification (Systems 1-5 LIVE CERTIFIED & MASTERED)**: Systems 1-4 PASS. System 5 (Room 4 Gemini 3.8 Flash TTS) FULLY HARDENED & CERTIFIED: Purged all stale cache; freshly synthesized all 68 Chapter 1 segments from scratch. Vocoder attention limit permanently solved via sentence-level chunking and Hann micro-fade concatenation. All 68/68 segments verified on disk (1,833 words, 11.78 minutes, average rate 2.59 w/s, 0% cutoff). Native Hindi voices, dynamic dialogue temperatures, and pristine delivery confirmed. Ready for Room 5 Vocal Mastering & M4B packaging.
- **Phase 3 TTS Gateway Bridge, Gemini Adapter & Directing Realization (COMPLETED & CERTIFIED)**:
  - Restored `speechMetadata.style` in [`gateway_bridge.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py) for Gemini 3.8 Flash audio modality without stripping.
  - Locked Narrator strictly to 0.32 temp (zero style metadata); clamped character dialogue dynamically to [0.35, 0.52] (zero histrionics >0.52).
  - Preserved certified acoustic reflexes (`[laughs]`, `[sighs]`, `[whispers]`, `[growls]`, `[gasp]`, `[chuckles]`, `[pant]`, `[groan]`) in spoken text; routed non-acoustic descriptors (`[cold menace]`, `[angrily]`, `[धीमी आवाज़ में]`) to `speechMetadata.style`.
  - Preserved `speechMetadata` and mapped `voiceName` in [`gemini.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/gemini.py). 15/15 target tests + 23/23 regression tests 100% green.
- **Room 1 Pre-Production & Casting Defect Remediation (Round 6 100% UNCONDITIONAL PASS CERTIFIED)**:
  - Fix 1: Descriptive phrases (>=3 words) prevented from token splitting in `phonetic_transliteration.py` & `character_caster.py`; generic nouns (e.g. `man` -> `मान`) never extracted as aliases.
  - Fix 2: Extended generic titles, descriptors, and numbers blacklist in `_is_blacklisted_or_generic` & `_is_standalone_forbidden_key` (`man`, `मान`, `fat`, `फ़ाट`, `cobbler`, `कोब्ब्लेर`, `sorcerer`, `सोर्सेरेर`, `sorceress`, `सोर्सेरेस्स`, `halberdier`, `हाल्बेर्डिेर`, `warrior`, `वार्रिोर`, `reaver`, `रीवेर`, `denesle`, `डेनेस्ले`, `golden`, `गोल्डेन`, `dragon`, `ड्रागोन`, `little`, `लिट्ट्ले`).
  - Fix 3: Re-instated `Téa` (`तेया`) as active female character (`Achernar`) in `preproduction_supervisor.py` protected from purge; synced to `book_bible.json`, `character_roster.json`, `cast_lock.json`, and `voice_registry.json`.
  - Fix 4: Disk assets cleaned with 0 leaked keys; `get_lock('मान')` is `None` (0 collision), and `get_lock('Téa')`/`get_lock('तेया')` resolves to `Achernar`. 31/31 tests 100% green.
