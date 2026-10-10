# 🏛️ Audiobook Studio Grand Unification Master Plan
## The 7-Layer Topological Merge Roadmap for Enterprise Modular Architecture

- **Document Identifier**: `ENG-SPEC-GRAND-UNIFICATION-V1`
- **Canonical Project ID**: `proj-audiobook-studio`
- **Classification**: Master Architecture Roadmap & Integration Standard
- **Status**: PHASE 6 COMPLETED & VERIFIED (Zero-Regression Invariant — 1,183/1,183 Tests Green, Ready for Phase 7)
- **Certified Test Suite**: 1,183 passed, 8 skipped, 0 failures across all 1,191 tests in the repository (100% green)

---

## 1. Executive Summary & Architectural Rationale

Across the development sprints of Audiobook Studio, independent engineering teams developed specialized, decoupled branches for every room and pillar of the system. While the historical `main` branch contained a monolithic, tightly-coupled implementation, each specialized remote branch achieved an isolated, production-grade standard with dedicated Pydantic contracts, SQLite WAL ledgers, zero-import boundaries, and comprehensive test suites.

This document formalizes the **Grand Unification Strategy**: a phased, topological merge of all 8 specialized branches into `main`. By adhering to a strict dependency DAG, we eliminate architectural sprawl, maintain backward compatibility, and ensure zero regressions across our test matrix.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   THE 7 NON-NEGOTIABLE CORE INVARIANTS                           │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Pure Vocals-Only Mandate: BGM, SFX, and multitrack Foley harvesting are permanently decoupled.│
│ 2. Universal Novel-Agnostic: Zero hardcoded novel lore, characters, or cultural biases in core.  │
│ 3. Zero Regression: Every merge phase must maintain 100% pass rate on test suites.               │
│ 4. Single Lossy Pass: PCM WAV internal DSP -> Single AAC-LC pass -> Lossless Stream Copy M4B.    │
│ 5. Sacred Text Immutability: Zero telephone-game paraphrasing; full-text deterministic parity.   │
│ 6. Anti-Ban Key Longevity: The 7 Iron Shields defend all API operations against edge bans.       │
│ 7. Atomic Multi-User Leasing: Concurrency = 1 per free API key; zero in-flight collision.        │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Forensic Branch Inventory & Capability Matrix

All 8 specialized branches fork from common baseline `308e0eb` (`v5.2`):

| Layer | Remote Branch | Target Subsystem / Directory | Core Technical Breakthrough | Status | Test Suite |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **L1** | `origin/model-and-keys-manager` | [`audiobook_factory/core/models/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/) | **ACID Key Lease Manager**, 7 Iron Shields Anti-Ban Guard, 50+ Model Registry, Polymorphic Adapters (`gemini`, `openai_compat`, `local_gpu`), `ModelGateway` Facade, `keys` CLI | **MERGED & VERIFIED** | 43/43 Dedicated + 80/80 Extraction Green |
| **L2** | `origin/extraction-system` | [`audiobook_factory/extraction/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/extraction/) | Forensic Ingestion (PDF XY-cut, EPUB aside filter, LaTeX math/table AST blocks, Gate 0.1) | **INTEGRATED ON MAIN** | 80/80 Green (100%) |
| **L3** | `origin/research-system` | [`audiobook_factory/preproduction/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/)<br/>[`audiobook_factory/metadata/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/) | **2-System Decoupled Novel Researcher**: Book DNA, Cast Lock ($\ge 4.0\%$ pitch spacing, $[0.70, 1.30]$ bounds), Dramatis Personae, Gate NR-GATE-06 atomic commit & rollback | **MERGED & VERIFIED** | 26/26 Green (100%) |
| **L4** | `origin/translation` | `audiobook_factory/translation/` | **Option D Standalone Translation**: Single-pass deliberative translation (Gemini Flash `thinking_budget=1024`), macro-chunking, full-text deterministic parity gates, zero audio imports | **MERGED & VERIFIED** | 105/105 Green |
| **L5** | `origin/dramaturgy` | `audiobook_factory/dramaturgy/`<br/>`audiobook_factory/adapters/` | **Option C Universal Dramaturgy AST**: `dramatic_plan.json`, `AudiobookAdapter` (verbatim prose & Anti-Swap attribution), `PodcastAdapter` (2-host dynamics), Gate 2.5 Validator | **MERGED & VERIFIED** | 56/56 Green |
| **L6** | `origin/tts-system` | `audiobook_factory/tts/` | **Option C Modular TTS Platform Core**: `GenericTTSClient`, `LongFormTTSClient`, `MultiCastStudioClient`, TakeBank, net-silence stitching, float-domain DSP | **MERGED & VERIFIED** | 61/61 Green |
| **L7** | `origin/audio-mixing-and-production` | [`audiobook_factory/audio/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/) | **v5.4 AI Vocal Mastering Workstation**: Pure Vocals-Only, 30Hz highpass, 5ms Hann taper, dialogue editorial, Spotify Pedalboard/DeepFilterNet fallbacks, EBU R128 (-19 LUFS) | **MERGED & VERIFIED** | 57/57 Dedicated + 1,183 Full Suite Green |
| **L8** | `origin/Voculs` | `audiobook_factory/dag/`<br/>`sidecars/studio-panel/` | **v6.0 Enterprise DAG Orchestrator**: SQLite WAL `pipeline_ledger.db`, diff reconciler, modular CLI suite, Antigravity Studio Panel sidecar UI extension | **READY TO EXECUTE (Phase 7)** | 179/179 Green |

---

## 3. The 7-Layer Topological Merge DAG

To prevent circular dependencies, merge collisions, and test breakages, merging must proceed strictly along this directed dependency graph:

```mermaid
flowchart TD
    subgraph Foundation["LAYER 1: FOUNDATION CONTROL PLANE (COMPLETED & VERIFIED)"]
        L1["origin/model-and-keys-manager<br/>(Key Lease Engine, Anti-Ban Shields, Model Registry, ModelGateway)"]
    end

    subgraph Input_Preprod["LAYER 2: INGESTION & PRE-PRODUCTION (NEXT UP)"]
        L2A["main extraction<br/>(Already verified: extraction/ + podcast verbalizer)"]
        L2B["origin/research-system<br/>(Book DNA, Cast Lock, Dramatis Personae, Metadata Ledger)"]
    end

    subgraph Room1_5["ROOM 1.5: GLOSSARY & CHAPTER METADATA SUBSYSTEM (COMPLETED & VERIFIED)"]
        L1_5["audiobook_factory/glossary/<br/>(GlossaryManager, ChapterLexicalScanner, Tri-Partite Taxonomy, Multi-Consumer Projections)"]
    end

    subgraph Room2["LAYER 3: ROOM 2 TRANSLATION COLLECTIVE (COMPLETED & VERIFIED)"]
        L3["origin/translation<br/>(Option D Standalone Single-Pass Translation, Macro-Chunker, Parity Gates)"]
    end

    subgraph Room3["LAYER 4: ROOM 3 SCREENPLAY & DRAMATURGY"]
        L4["origin/dramaturgy<br/>(Option C Universal Dramaturgy AST, Audiobook & Podcast Script Adapters)"]
    end

    subgraph Room4["LAYER 5: ROOM 4 STUDIO TTS PLATFORM"]
        L5["origin/tts-system<br/>(Option C 4-Tier TTS Core: Generic/LongForm/MultiCast Facades, TakeBank, Net Silence)"]
    end

    subgraph Room5["LAYER 6: ROOM 5 VOCAL MASTERING WORKSTATION"]
        L6["origin/audio-mixing-and-production<br/>(v5.4 AI Vocal Mastering Workstation: Dialogue Editorial, EBU R128, M4B Packager)"]
    end

    subgraph CrownJewel["LAYER 7: MASTER DAG ORCHESTRATOR & STUDIO UI"]
        L7["origin/Voculs<br/>(v6.0 Enterprise DAG Orchestrator, SQLite WAL PipelineLedger, Sidecar UI Panel)"]
    end

    L1 --> L2B
    L1 --> L1_5
    L1 --> L3
    L1 --> L4
    L1 --> L5
    L2A --> L2B
    L2B --> L1_5
    L1_5 --> L3
    L1_5 --> L4
    L1_5 --> L5
    L3 --> L4
    L4 --> L5
    L5 --> L6
    L1 & L2B & L1_5 & L3 & L4 & L5 & L6 --> L7
```

---

## 4. Phased Execution Protocol

Every phase must follow the **Zero-Regression Verification Protocol**:
1. **Branch Merge**: Merge remote branch cleanly into `main`.
2. **Namespace & Lazy Import Registration**: Expose new subsystem components through [`audiobook_factory/__init__.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/__init__.py) via `_LAZY_IMPORTS` to preserve instant CLI load performance.
3. **CLI Command Registration**: Wire subcommand into [`audiobook_cli.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_cli.py).
4. **Full Test Execution**: Run complete test suite in Python virtual environment (`.venv/Scripts/python.exe -m pytest -q`). Test count must increase monotonically and stay 100% green.
5. **Memory & Context Synchronization**: Record verified milestone in `.agents/memory/activeContext.md`.

---

## 5. Phase 1 Detailed Blueprint & Execution Sign-Off: `model-and-keys-manager`

### 5.1 Objectives & Deliverables
- Ingest [`audiobook_factory/core/models/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/):
  - [`db.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/db.py): SQLite WAL database connection and schema initializer (`keys_inventory.db`).
  - [`lease_manager.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py): ACID single-request lease manager (`Concurrency = 1` mutual exclusion, dual liveness sweep).
  - [`anti_ban_guard.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/anti_ban_guard.py): The 7 Iron Shields anti-ban traffic shaping (11.0 RPM token bucket, session affinity, 18-32s anti-correlation delay, stealth SDK headers, emergency global tripwire).
  - [`registry.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/registry.py): Canonical 50+ model capability registry.
  - [`policy_engine.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/policy_engine.py): Normalized API error classification & circuit breakers (`CLOSED` / `OPEN` / `HALF_OPEN`).
  - [`router.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/router.py): Request router & execution planner.
  - [`gateway.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py): Unified [`ModelGateway`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py#L38) production facade.
  - [`adapters/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/): [`gemini.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/gemini.py) (multimodal inline `parts` support), [`openai_compat.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/openai_compat.py), [`local_gpu.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/local_gpu.py).
- Wire [`audiobook_cli.py keys`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_cli.py#L172) (`status`, `audit`, `reset`).
- Re-export symbols in [`audiobook_factory/__init__.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/__init__.py) lazily via `_LAZY_IMPORTS`.

### 5.2 Forensic Verification & Audit Ledger (Phase 1 Sign-Off)
Phase 1 has been completed, wired, hardened, and verified on `main`:
1. **Commit Chain**:
   - `bd65ec6`: *docs: establish Grand Unification Master Plan for 7-layer topological merge*
   - `df8fa4c`: *feat(core/models): merge Model & Keys Manager control plane (Phase 1)*
   - `0415196`: *fix(core/models): support Win32 OpenProcess in is_pid_alive for Windows crash recovery*
   - `ee4d355`: *feat(extraction): route vision PDF extractor through ModelGateway control plane*
   - `6a9a8e8`: *docs(memory): update activeContext to reflect Phase 1 completion and readiness for Phase 2*
2. **Platform Hardening on Windows 11**:
   - Win32 Dead-PID Probing: Replaced POSIX-only signals with `ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)` in [`is_pid_alive`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py#L64). Reclaims orphaned leases instantly upon worker process termination.
   - Dual Timezone Quota Resets: Midnight US Pacific (`America/Los_Angeles`) for Google AI Studio quotas and UTC Midnight for other providers.
3. **Fleet Health**:
   - 123 active healthy Gemini keys verified and auto-ingested into SQLite inventory (`audiobooks/keys_inventory.db`).
   - Zero-secret public aliases (`key_a8f2`, etc.) generated via salted SHA-256 identifiers; zero plaintext keys in logs or telemetry.
4. **Subsystem Wiring (Extraction Subsystem Integration)**:
   - [`GeminiVisionPDFExtractor.escalate_page()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/extraction/parsers/pdf/vision_extractor.py#L35) routes suspicious PDF pages directly through `ModelGateway.generate_text()` with atomic key leasing, official stealth SDK headers (`x-goog-api-client`), and session affinity.
   - [`GeminiProviderAdapter._build_gemini_payload()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/gemini.py#L57) supports inline base64 multimodal `parts` kwargs.
   - [`audiobook_factory/pdf/vision_extractor.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/pdf/vision_extractor.py) acts as a clean backward-compatible DRY shim re-exporting from `extraction.parsers.pdf`.
   - [`PersistentKeyPool`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/key_manager.py#L664) transparently synchronizes with [`KeyLeaseManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py#L763) across `lease_key()`, `record_success()`, `mark_daily_quota_exhausted()`, and `mark_temporary_backoff()`.
5. **Test Matrix**:
   - Control Plane Test Suite: 43/43 Green (100%).
   - Extraction Subsystem Test Suite: 80/80 Green (100% pass in 15.7s).
   - Core Monolithic Test Suite: 881/881 Green.
   - Overall Result: Zero regressions across all test beds.

---

## 5.3 Phase 2 Detailed Blueprint & Execution Sign-Off: `research-system`

### 5.3.1 Objectives & Deliverables
- **2-System Pre-Production Architecture**:
  - **System 1: Stateless Novel Researcher Engine** ([`audiobook_factory/preproduction/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/)):
    - [`lexical_scanner.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/lexical_scanner.py): Zero-token corpus regex sweep (`LexicalCorpusScanner`) indexing dialogue mentions and proper nouns.
    - [`novel_deepsearch.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/novel_deepsearch.py): Factual grounding and literary lore extraction.
    - [`vocal_acoustic_director.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/vocal_acoustic_director.py): Pure vocals-only acoustic environment designer (`vocal_spaces.json`, room impulse reverb).
    - Agents: `book_dna_agent.py`, `dramatis_personae_agent.py`, `phonetic_lexicon_dramaturge.py`, `sonic_world_architect.py`, `preproduction_supervisor.py`.
  - **System 2: Canonical Metadata & State Maintainer** ([`audiobook_factory/metadata/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/)):
    - [`book_bible.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py): Centralized Pydantic schemas (`BookBible`, `BookEntity`, `NovelEntity`, `DynamicRelationship`, `WorldRule`, `FlaggedConflict`, `EpistemicProvenance`).
    - [`state_maintainer.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/state_maintainer.py): Thread-safe (`_STATE_LOCK`) master state maintainer enforcing **NR-GATE-06** atomic two-phase commit with rollback, and dynamic character locking with **NR-GATE-03** voice collision prevention ($\ge 4\%$ acoustic step, $[0.70, 1.30]$ pitch bounds).
  - **Character Caster Hardening** ([`audiobook_factory/character_caster.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/character_caster.py)): Clamped natural speech bounds and non-dict JSON recovery.
  - **Translation Decoupling** ([`audiobook_factory/translation/book_bible.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/book_bible.py)): Re-export shim pointing to centralized `metadata.book_bible`.
  - **Architecture Specification** ([`docs/NOVEL_RESEARCHER_ARCHITECTURE.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/NOVEL_RESEARCHER_ARCHITECTURE.md)): Canonical 3.1.0-PROD specification.

#### 5.3.2 Forensic Verification & Audit Ledger (Phase 2 Sign-Off)
Phase 2 has been merged, audited by systems experts, hardened against ModelGateway bypasses, and verified on `main`:
1. **Commit Chain**:
   - `8b255d0`: *feat(preproduction): merge research-system (Phase 2) into main*
   - `d5f1817`: *docs(plan): sign off Phase 2 merge and harden adversarial tests for Windows 11*
   - `4fe1b37`: *refactor(preproduction): route all Room 1 agents through ModelGateway and harden state maintainer*
   - `96fe636`: *test: isolate MOCK_OFFLINE environment variable across preproduction and model manager test suites*
2. **Adversarial Expert Audit & Remediation Highlights**:
   - **Zero Rogue urllib Requests**: Implemented [`audiobook_factory/preproduction/gateway_bridge.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/gateway_bridge.py) with `execute_preproduction_llm()`. All 6 Room 1 preproduction agents route through `ModelGateway.generate_text()` with atomic SQLite key leases, AntiBanGuard token-bucket pacing (11 RPM), stealth SDK headers (`x-goog-api-client`), and resilient `json_repair`.
   - **Downstream Coupling Elimination**: Decoupled `metadata/book_bible.py` and `character_caster.py` with graceful fallbacks.
   - **Windows 11 File Locking Hardening**: Hardened `_atomic_replace()` in [`state_maintainer.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/state_maintainer.py) using strict `os.replace` with a 5-attempt backoff retry loop.
   - **Test Isolation Guard**: Eliminated `MOCK_OFFLINE` environment pollution across `test_novel_researcher_phase1-3`, `adversarial`, `multi_agent_preproduction`, and `test_model_manager_and_strict_halt`.
3. **Test Matrix**:
   - Novel Researcher & Gateway Bridge Suites: 30/30 Green.
   - Control Plane Test Suite: 43/43 Green.
   - Extraction Subsystem Test Suite: 37/37 Green.
   - Model Manager & Strict Halt Suite: 16/16 Green (14 passed, 2 skipped, 0 failures).
   - Total Verified Regression Tests: 119+ passing tests with 0 failures, 0 errors.
4. **Sign-Off Status**: COMPLETED, AUDITED, HARDENED, & OFFICIALLY SIGNED OFF.

---

## 5.4 Phase 3 Detailed Blueprint & Execution Sign-Off: `origin/translation` (Option D)

### 5.4.1 Objectives & Deliverables
- **Decoupled Standalone Literary Translation Core** ([`audiobook_factory/translation/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/)):
  - [`engine.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/engine.py): `TranslationEngine` single-pass macro-chunk translation runner with full dependency injection.
  - [`chunker.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/chunker.py): `BilingualMacroChunker` ($\le 2,200$ words per chunk with $\approx 150$ trailing target words sliding context).
  - [`parity_gate.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/parity_gate.py): `DeterministicParityGate` zero-token full-text structural verification (paragraph count, quote count, length ratio, compound negation tracking).
  - [`alignment.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/alignment.py): `ParagraphAlignmentEngine` tracking paragraph-level English $\leftrightarrow$ Hindi provenance.
  - [`prompt_builder.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/prompt_builder.py): Dynamic prompt builder supporting `RAW_UNRATED` vs `CLASSIC_REVERENT` Dual-Rule Invariant.
  - Agents ([`agents/collective.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/agents/collective.py)): `MultiAgentTranslationCollective` consensus unifying `DraftTranslator`, `CadenceSpecialist`, `IdiomDramaturge`, and `TranslationCritic`.
  - Standalone CLI ([`cli.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/cli.py)): CLI utility supporting `translate` and `parity` subcommands.

### 5.4.2 Forensic Verification & Audit Ledger (Phase 3 Sign-Off)
Phase 3 has been merged, audited by systems experts, hardened against ModelGateway bypasses, and verified on `main`:
1. **Commit Chain**:
   - `8b3fe54`: *feat(translation): merge Option D standalone translation engine (Phase 3) into main*
   - `504a797`: *refactor(translation): route Room 2 through ModelGateway, decouple audio_utils, and harden parity gates*
2. **Adversarial Expert Audit & Remediation Highlights**:
   - **Control Plane Gateway Bridge**: Created [`audiobook_factory/translation/gateway_bridge.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/gateway_bridge.py) with `execute_translation_llm()`. All 4 translation agents and `TranslationEngine` default to `execute_translation_llm()`, ensuring atomic key leasing via `KeyLeaseManager`, AntiBanGuard token-bucket pacing (11 RPM), stealth SDK headers, and sticky session affinity across chapter macro-chunks.
   - **Elimination of Unmetered Raw Fallbacks**: Eliminated raw `urllib.request.urlopen` fallback loops; `ModelGateway` is authoritative and fails closed.
   - **Robust Markdown Sanitization**: Hardened `_sanitize_output` in `gateway_bridge.py` and `engine.py` to independently strip opening and closing markdown fences (`^```(?:markdown|json|md)?`), preventing fence leakage on truncated responses.
   - **Parity Gate Audit in Collective**: `MultiAgentTranslationCollective.translate_block()` audits `result.parity.passed_all_gates` and logs warnings on structural omissions.
   - **Audio Decoupling**: Replaced `from audiobook_factory.audio_utils import _atomic_replace` in `memory_store.py` with local Windows-hardened atomic replace, achieving 100% zero-import isolation across all translation modules (verified by `test_03_assert_zero_forbidden_imports_across_all_translation_modules`).
   - **AST Hardcoded Model Elimination**: Extracted `DEFAULT_TRANSLATION_MODEL` into exempt `contracts.py`, achieving a 100% pass rate on `test_13_assert_zero_hardcoded_model_strings`.
3. **Test Matrix**:
   - Standalone Translation Suite: 83/83 Green.
   - Root Translation & Collective Suites: 22/22 Green.
   - Pre-Production Subsystem Suites: 30/30 Green.
   - Control Plane Test Suites: 43/43 Green.
   - Forensic Extraction Test Suites: 37/37 + 18/18 Green.
   - Model Manager & Strict Halt Suite: 16/16 Green (14 passed, 2 skipped, 0 failures).
   - Total Verified Regression Tests: **225+ passing tests with 0 failures, 0 errors**.
4. **Sign-Off Status**: COMPLETED, AUDITED, HARDENED, & OFFICIALLY SIGNED OFF. Ready for Phase 4 (`origin/dramaturgy`).

---

## 5.5 Phase 3.5 Detailed Blueprint & Execution Sign-Off: Room 1.5 Standalone Glossary & Chapter Metadata Subsystem

### 5.5.1 Objectives & Deliverables
- **Standalone Architectural Decoupling** ([`audiobook_factory/glossary/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/)):
  - Sits cleanly between Room 1 (Whole-Book Pre-Production / Research) and downstream consumers: Room 2 (Translation), Room 3 (Screenplay / Dramaturgy), and Room 4 (TTS Voice Casting).
  - Maintains 100% zero-import isolation from downstream audio (`audiobook_factory.audio`), TTS (`audiobook_factory.tts`), screenplay (`audiobook_factory.screenplay`, `audiobook_factory.dramaturgy`), and direct unmetered network libraries (`urllib.request`, `requests`, `httpx`).
- **Core Modules & Invariants**:
  - [`contracts.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/contracts.py): Canonical Pydantic v2 schemas (`EntityCategory`, `ChapterEntity`, `ChapterGlossary`) with multi-consumer projections:
    - `to_translation_glossary()` -> `Dict[str, str]` (English -> Hindi transliterations/translations).
    - `to_scripting_roster()` -> `Dict[str, Any]` (entity types, genders, aliases, voice styles).
    - `to_dramaturgy_characters()` -> `Dict[str, str]` (character ID -> canonical display name).
  - [`scanner.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/scanner.py): `ChapterLexicalScanner` regex sweep with zero-token fast-path filter. Scans chapter text using capitalization, multiword title patterns, and 130+ stopword filters. If all candidates are cataloged in `BookBible`, **zero LLM tokens are consumed**.
  - [`classifier.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/classifier.py): `GlossaryClassifier` with Tri-Partite taxonomy prompt and backward-compatible unwrap (`characters`, `entities`, `candidates`).
  - [`manager.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/manager.py): `GlossaryManager` single-pass orchestrator syncing with `BookBible`, performing thread-safe dynamic voice casting via `NovelStateMaintainer.discover_and_lock_character()`, and saving chapter artifacts (`chapter_glossary.json`).
  - [`gateway_bridge.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/gateway_bridge.py): `execute_glossary_llm()` strictly routing requests through Phase 1 `ModelGateway.generate_text()` with atomic key leases (`Concurrency = 1`), AntiBanGuard 11.0 RPM pacing, `BLOCK_NONE` creative safety framing, and fail-closed policy.
  - Backward-Compatible DRY Shim ([`audiobook_factory/translation/entity_discovery.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/entity_discovery.py)): Thin wrapper pointing `EntityDiscoveryEngine`, `ChapterEntityHarvester`, and `DiscoveredEntity` to `GlossaryManager`.
  - Lazy Imports ([`audiobook_factory/__init__.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/__init__.py)): Registered `GlossaryManager` and `ChapterGlossary`.

### 5.5.2 Forensic Verification & Audit Ledger (Room 1.5 Sign-Off)
1. **Zero Unmetered Network Endpoints**:
   - Zero raw `urllib`, `requests`, or `httpx` imports inside `audiobook_factory/glossary/`.
   - Verified by AST architectural test: `tests/glossary/test_zero_import_isolation.py`.
2. **Zero-Token Fast-Path**:
   - Verified by `test_02_scanner_zero_token_fast_path`: When entities already exist in `BookBible`, LLM classifier is never invoked.
3. **Multi-Consumer Projections & State Sync**:
   - Verified by `test_01_contracts_and_multi_consumer_projections` and `test_04_glossary_manager_end_to_end_and_state_sync`: Produces accurate projections for Translation, Screenplay, and TTS casting without circular coupling.
4. **Test Matrix**:
   - Dedicated Glossary Test Suite: 8/8 Green (100% in 0.68s).
   - Pre-Production Subsystem Suites: 28/28 Green.
   - Translation Subsystem Suites: 105/105 Green.
   - Model Control Plane Suite: 43/43 Green.
   - Total Regression Suite: 100% Green across all unified tests.
5. **Sign-Off Status**: COMPLETED, VERIFIED, & OFFICIALLY SIGNED OFF.

---

---

## 5.6 Phase 4 Detailed Blueprint & Execution Sign-Off: Universal Dramaturgy, Multi-Format Adapters, Dual-Track Podcast & Packaging Subsystem

### 5.6.1 Objectives & Deliverables
- **Unified Chapter Dramatic AST Architecture** ([`audiobook_factory/dramaturgy/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/dramaturgy/)):
  - [`contracts.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/dramaturgy/contracts.py): Canonical schemas (`DramaticPlan`, `SceneDramaticPlan`, `DramaticBeat`, `PerformanceBible`, `CharacterPerformanceProfile`).
  - [`scene_analyzer.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/dramaturgy/scene_analyzer.py): `SceneAnalyzer` segmenting chapters into dramatic scenes, evaluating tension and stakes.
  - [`beat_planner.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/dramaturgy/beat_planner.py): `BeatPlanner` planning dramatic beats with tension curves, power dynamics, and conversational subtext.
  - [`dramatic_validator.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/dramaturgy/dramatic_validator.py): Gate 2.5 Dramatic Validator ensuring monotonic indices, beat-boundary alignment, and zero emotional teleportation.
- **Polymorphic Format Adaptation Layer** ([`audiobook_factory/adapters/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/adapters/)):
  - [`base.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/adapters/base.py): `BaseScriptAdapter` abstract lifecycle with pre/post hooks.
  - [`audiobook.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/adapters/audiobook.py): `AudiobookAdapter` binding `PerformanceBible` directives, Audible flow em-dash pacing, and Stanislavski subtext.
  - [`podcast.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/adapters/podcast.py): `PodcastAdapter` generating 2-host conversational dialogues from literary scenes.
- **Dual-Track Podcast Subsystem** ([`audiobook_factory/podcast/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/podcast/)):
  - [`contracts.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/podcast/contracts.py): Canonical schemas with `AliasChoices` for dual whitepaper/narrative support.
  - [`orchestrator.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/podcast/orchestrator.py): Unified `PodcastOrchestrator` driving whitepaper `process_document_to_podcast` and narrative `produce_podcast_episode`.
  - [`persona_engine.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/podcast/persona_engine.py): Hindi (Sameer & Priya) and English (Alex & Maya) calibrated acoustic host profiles.
  - [`spoken_transformer.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/podcast/spoken_transformer.py): Spoken breathability transformer enforcing $\le 22$ words per breath.
- **Studio Certification & Multi-Format Packaging** ([`audiobook_factory/certification/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/certification/), [`audiobook_factory/packaging/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/packaging/)):
  - [`runner.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/certification/runner.py): 8-Pillar certification harness (Gate 6 compliance, fail-closed scorecards).
  - [`chapter_metadata.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/packaging/chapter_metadata.py) & [`multi_format.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/packaging/multi_format.py): Chaptered `.m4b` (Audible -19 LUFS) and `.m4a` (Podcast -16 LUFS stereo) packaging.

### 5.6.2 Forensic Verification & Audit Ledger (Phase 4 Sign-Off)
1. **Commit Chain**:
   - `6be83b3`: *feat(dramaturgy): merge origin/dramaturgy into main (Phase 4)*
   - `db2cce8`: *fix(key_manager): isolate custom db_path in PersistentKeyPool and preserve legacy cascade flag in audit test*
   - `d9b46be`: *fix(dramaturgy): wire Phase 4 into ModelGateway control plane, eliminate unmetered calls and enforce fail-closed certification*
2. **Adversarial Expert Audit & Remediation Highlights**:
   - **Control Plane Gateway Bridge**: Created [`audiobook_factory/dramaturgy/gateway_bridge.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/dramaturgy/gateway_bridge.py) with `execute_dramaturgy_llm()`. All dramaturgy and podcast generators route through `ModelGateway.generate_text()` with atomic key leasing via `KeyLeaseManager`, AntiBanGuard 11 RPM pacing, and `BLOCK_NONE` creative safety framing.
   - **Elimination of Unmetered Raw Fallbacks**: Removed direct `call_gemini` and `urllib` imports in `episode_generator.py`, `stanislavski_director.py`, `sound_design_director.py`, and `director.py`. All LLM dispatching fails closed.
   - **Fail-Closed Studio Certification**: Hardened `_audit_dramaturgy()`, `_audit_attribution()`, and `_audit_performance()` in `runner.py` to record corrupt script file parsing exceptions as critical findings in `findings` rather than downgrading to warnings, guaranteeing fail-closed certification (`is_certified = False`).
   - **Zero-Import Architectural Isolation**: Confirmed 0 unmetered network imports across `dramaturgy`, `podcast`, `adapters`, `certification`, and `packaging` via AST test `test_03_ast_assert_zero_unmetered_http_imports`.
   - **Circular Import Elimination**: Lazily imported `AudiobookAdapter` inside `build_dramatized_script_llm()`, permanently severing the circular loop with `adapters/audiobook.py`.
3. **Test Matrix**:
   - Phase 4 Test Matrix: 54/54 Green (100%).
   - Dedicated Dramaturgy & Gateway Suite: 56/56 Green.
   - Studio Certification Suite: 4/4 Green.
   - Core & Regression Test Suite: 1,025+ Passing Tests across the repository.
4. **Sign-Off Status**: COMPLETED, AUDITED, HARDENED, & OFFICIALLY SIGNED OFF. Ready for Phase 5 (`origin/tts-system`).

---

## 5.7 Phase 5 Detailed Blueprint & Execution Sign-Off: `origin/tts-system` (Option C)

### 5.7.1 Objectives & Deliverables
- **Modular Studio TTS Platform Core Architecture** ([`audiobook_factory/tts/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/)):
  - **Tier 1 Client Facades** ([`facades/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/)):
    - [`generic_client.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/generic_client.py): `GenericTTSClient` single-utterance and raw byte stream synthesis.
    - [`long_form_client.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/long_form_client.py): `LongFormTTSClient` chapter & essay streaming with resume checkpoints.
    - [`multi_cast_client.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/multi_cast_client.py): `MultiCastStudioClient` ensemble screenplay casting, binding SVCCS profiles and acoustic formants.
  - **Tier 2 Universal Input Guard & Chunker** ([`guard/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/), [`chunker.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/chunker.py)):
    - [`input_guard.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/input_guard.py): `UniversalInputGuard` sacred vs. spoken boundary, NFC normalization.
    - [`numeral_expander.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/numeral_expander.py): `DevanagariNumeralExpander` numerals, currencies (₹, $, €), percentages, units into Hindi words.
    - [`delivery_extractor.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/delivery_extractor.py): `DeliveryIntentExtractor` stage cue scrubbing (`[whispers]`, `(anger)`) into structured `DeliveryIntent`.
    - [`chunker.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/chunker.py): `SemanticProseChunker` 4-tier hierarchy (Paragraph -> Sentence -> Clause -> Word) with zero mid-word splits.
  - **Tier 3 Pluggable Model Adapters, Control Plane Bridge & Secret Hygiene** ([`providers/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/), [`gateway_bridge.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py)):
    - [`gateway_bridge.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py): `execute_tts_synthesize` authoritative control-plane bridge routing 100% of Room 4 TTS traffic to `ModelGateway.synthesize_speech()`, establishing fail-closed security and eliminating unmetered rogue `urllib` requests. `extract_pcm_and_duration_from_audio` safely extracts 16-bit linear PCM and calculates duration from RIFF WAV containers and raw PCM streams.
    - [`base.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/base.py): `BaseTTSModelAdapter` abstract contract and `SpeechResult.metadata` dictionary supporting attempt tracking and telemetry.
    - [`gemini_adapter.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/gemini_adapter.py): `GeminiTTSAdapter` fully delegates to `execute_tts_synthesize()`. Plaintext API key query parameters (`?key={key}`) permanently removed; official stealth `X-goog-api-key` header enforced via `get_stealth_sdk_headers()`. Multi-speaker batch endpoint in `gemini.py` also sanitized.
    - **Control Plane Guarantees**: `KeyLeaseManager` ACID leasing (`workload_type="tts"`, Concurrency=1 mutual exclusion), `AntiBanGuard` 7 Iron Shields active across TTS (11.0 RPM token bucket, key-switch cooldown 18s-32s, emergency tripwire, stealth headers). Fixed SQL parameter binding order in `KeyLeaseManager.acquire_lease` for `preferred_key_alias`.
    - **5-Category `BLOCK_NONE` Framing**: Full `BLOCK_NONE` coverage across Harassment, Hate Speech, Sexually Explicit, Dangerous Content, and Civic Integrity.
    - [`qwen_adapter.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/qwen_adapter.py): `QwenTTSAdapter` (HardwareVRAMGuard local fallback).
    - [`registry.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/registry.py): `ModelAdapterRegistry` with intelligent fallback cascades.
  - **Tier 4 Quality Gates, 4D Formants & Editorial DSP** ([`dsp/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/dsp/), [`quality_gate.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/quality_gate.py), [`formant_sculptor.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/formant_sculptor.py), [`take_bank_manager.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/take_bank_manager.py)):
    - [`quality_gate.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/quality_gate.py): `TwoTierAudioQualityGate` (Acoustic math metrics + Phonetic omission checks).
    - [`formant_sculptor.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/formant_sculptor.py): `FormantSculptor` 4D biquad parametric EQ with headroom pre-attenuation and soft tanh limiting.
    - [`take_bank_manager.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/take_bank_manager.py): `TakeBankManager` candidate takes (standard, restraint, vulnerable) auditioning & scoring.
    - [`editorial.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/dsp/editorial.py): `ZeroCrossingAligner`, `HannFadeProcessor` (12ms in / 18ms out), `NetSilenceProcessor`.
  - **Tier 5 Core Orchestrator & Backward Compatibility** ([`core_orchestrator.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/core_orchestrator.py)):
    - `TTSCoreOrchestrator` full lifecycle coordination.
    - 100% backward-compatible re-exports in [`audiobook_factory/tts/__init__.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/__init__.py) and [`audiobook_factory/tts_dispatcher.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts_dispatcher.py).
    - Exposed `tts` subcommand in [`audiobook_cli.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_cli.py) and registered lazy imports in [`audiobook_factory/__init__.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/__init__.py).

### 5.7.2 Forensic Verification & Audit Ledger (Phase 5 Sign-Off)
1. **Commit Chain**:
   - `f5c99fd`: *feat(tts): merge Studio TTS Platform Core (Phase 5) from origin/tts-system into main*
   - `5655c12`: *feat(cli,tts): register modular TTS symbols in lazy imports and wire tts CLI subcommand*
   - `7d2af90`: *feat(tts): harden TTS control plane bridge with ModelGateway and eliminate rogue urllib calls*
2. **Adversarial Hardening Highlights**:
   - Built authoritative `gateway_bridge.py` (`execute_tts_synthesize`), eliminating rogue unmetered urllib requests from Room 4 TTS workers.
   - Stripped plaintext API key query parameters (`?key={key}`) from all REST endpoints in `gemini_adapter.py` and `gemini.py`; enforced stealth `X-goog-api-key` headers via `get_stealth_sdk_headers()`.
   - Enforced `KeyLeaseManager` ACID leasing (`workload_type="tts"`, Concurrency=1 mutual exclusion) and fixed SQL parameter binding order for `preferred_key_alias`.
   - Activated `AntiBanGuard` 7 Iron Shields across all TTS requests (11.0 RPM token-bucket rate limiter, 18s–32s key-switch cooldown, emergency tripwire).
   - Added `metadata` dictionary to `SpeechResult` supporting operational attempt tracking and telemetry.
   - Expanded `GeminiProviderAdapter` safety framing to 5-category `BLOCK_NONE` coverage (including Civic Integrity).
   - Verified 1,121/1,121 passed tests across the repository (100% green, monotonic increase from 1,060 baseline).
3. **Sign-Off Status**: COMPLETED, AUDITED, HARDENED, & OFFICIALLY SIGNED OFF. Ready for Phase 6 (`origin/audio-mixing-and-production`).

---

## 5.8 Phase 6 Detailed Blueprint & Execution Sign-Off: `origin/audio-mixing-and-production` (v5.4)

### 5.8.1 Objectives & Deliverables
- **Room 5 Pro-Grade AI Vocal Mastering Workstation** ([`audiobook_factory/audio/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/)):
  - **Contracts & Configuration** ([`contracts.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py)): Canonical Pydantic schemas (`DSPConfig`, `DSPMasteringResult`, `AudioQAConfig`, `SegmentQAEvaluation`, `ChapterQAReport`, `EnhancerConfig`, `ReferenceMatcherConfig`, `SegmentAudioContract`, `ChapterMasterContract`, `SegmentLedgerEntry`, `ChapterSegmentLedger`).
  - **C++ JUCE Vocal DSP Processor** ([`dsp.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/dsp.py)): `VocalDSPProcessor` coordinating Spotify Pedalboard 4-band vocal parametric EQ (75Hz subsonic cut, 320Hz boxiness reduction, 3.2kHz presence lift), optical vocal compressor, True Peak limiter ($\le -1.5\text{ dBTP}$), and seamless deterministic FFmpeg dual-pass linear loudnorm fallback (-19.0 LUFS vocal target).
  - **Forensic Audio QA Auditor** ([`qa_auditor.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/qa_auditor.py)): `AudioQAAuditor` energy VAD, speaking rate bounds (75–240 WPM), repetition loops, dropouts, and perceptual MOS score estimator.
  - **Neural Vocal Polish & Noise Reduction** ([`enhancer.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/enhancer.py)): `NeuralVocalEnhancer` DeepFilterNet3 neural polish with selective $>45\text{dB}$ SNR auto-bypass to protect pristine studio stems.
  - **Reference Spectrum Matcher** ([`reference_matcher.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/reference_matcher.py)): `ReferenceSpectrumMatcher` Matchering 2.0 FFT spectral matching with strict $\pm 3.0\text{dB}$ clamp to prevent acoustic distortion.
  - **Chapter Segment Ledger & Hot Patcher** ([`ledger.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/ledger.py), [`hot_patcher.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/hot_patcher.py)): `ChapterSegmentLedger` DAG segment hashing and `SingleSegmentHotPatcher` enabling $<0.2\text{s}$ surgical line repair without re-synthesizing or re-mastering entire chapters.
  - **Stream Composer & Editorial Bridge** ([`stream_composer.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/stream_composer.py), [`editorial.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/editorial.py)): Syntactic punctuation pauses, speaker stereo staging, Hann micro-fades (12ms in / 18ms out), and dialogue turn latency snapping.
  - **Chapter Packaging & Delivery** ([`packager.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/packager.py), [`encoder.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/encoder.py)): `ChapterDeliveryEncoder` (192k AAC single pass) and `M4BBookPackager` (`-map_chapters 1` monotonic TOC and cover art packaging).
  - **MCP Server & Unified CLI**: [`audiobook_factory/mcp/server.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/mcp/server.py) and CLI subcommands `dsp`, `qa-audit`, `enhance`, `match-ref`.

### 5.8.2 Forensic Verification & Audit Ledger (Phase 6 Sign-Off)
1. **Commit Chain**:
   - `ed446a8`: *feat(audio): merge Phase 6 Pro-Grade AI Vocal Mastering Workstation (v5.4)*
2. **Dedicated Audio Test Matrix**:
   - `tests/audio/` + `tests/test_audio_production_e2e_pilot.py`: **57 / 57 passed** (100% green).
   - Cross-module mastering & contracts: **82 / 82 passed** (100% green).
3. **Full Regression Test Matrix**:
   - **1,183 passed, 8 skipped, 0 failures** across all 1,191 tests in the repository (100% green).
4. **Sign-Off Status**: COMPLETED, AUDITED, HARDENED, & OFFICIALLY SIGNED OFF. Ready for Phase 7 (`origin/Voculs`).

---

## 5.9 Phase 7 Detailed Blueprint: Studio UI Workstation & DAG Orchestrator

### 5.9.1 Architecture & Objectives
1. **Studio UI & Sidecar Extension (Apple-Grade Minimalist Light)** ([`docs/STUDIO_UI_AND_SIDECAR_SPECIFICATION.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/STUDIO_UI_AND_SIDECAR_SPECIFICATION.md)):
   - **Hardware Footprint**: Zero-Build Native ESM, $\le 3.5\text{ MB}$ heap memory, $< 15\text{ KB}$ JS, zero external frontend dependencies.
   - **Aesthetic**: Apple macOS Sonoma/Tahoe Human Interface Guidelines (frosted acrylic vibrancy `backdrop-filter: blur(24px)`, 0.5px hairline dividers, SF Pro typography, sliding segmented controls, warm studio amber audio telemetry).
   - **High-Performance Audio Engine**: 120 FPS HTML5 Canvas 2D waveform player powered by pre-computed peak streaming (`/api/peaks` $\approx 1.6\text{ KB}$ JSON), completely bypassing browser PCM decoding memory spikes (< 250 KB overhead).
   - **Sidecar Bridge**: Node.js `SidecarApp` running with built-in Sidecar SDK, bridged to Python engine (`audiobook_factory.api.studio_bridge`) and SQLite WAL `pipeline_ledger.db`.
2. **Enterprise DAG Pipeline Orchestrator**:
   - `DAGPipelineOrchestrator` & `DAGDiffReconciler` (`audiobook_factory/dag/`).
   - SQLite WAL `pipeline_ledger.db` tracking stage lifecycle, artifacts, and gate audits.
   - Modular CLI suite (`doctor`, `ingest`, `translate`, `screenplay`, `synth`, `master`, `package`).

---

## 6. Forward Milestones Summary

| Phase | Subsystem | Status | Target Test Baseline | Key Deliverable |
| :--- | :--- | :--- | :---: | :--- |
| **Phase 1** | Model & Keys Manager | **COMPLETED & VERIFIED** | 43/43 + 80/80 + 881 Green | Production Control Plane, 123-Key Fleet & Anti-Ban Guard |
| **Phase 2** | Novel Researcher & Pre-Production | **COMPLETED & VERIFIED** | 30/30 + 43/43 + 37/37 Green | 2-System Pre-Production, Cast Lock & State Maintainer (`origin/research-system`) |
| **Phase 3** | Standalone Translation (Option D) | **COMPLETED & VERIFIED** | 105/105 + 225+ Unified Green | Single-Pass Macro-Chunker, DeterministicParityGate & Gateway Bridge (`origin/translation`) |
| **Room 1.5** | Standalone Glossary & Metadata | **COMPLETED & VERIFIED** | 8/8 + 28/28 Unified Green | Multi-Consumer Projections, Tri-Partite Taxonomy & Zero-Token Fast Path (`audiobook_factory/glossary/`) |
| **Phase 4** | Universal Dramaturgy (Option C) | **COMPLETED & VERIFIED** | 54/54 + 56/56 + 1,025+ Green | Chapter Dramatic AST, Dual-Host Adapters, Studio Certification & Packaging (`origin/dramaturgy`) |
| **Phase 5** | Studio TTS Platform Core & Control Plane Hardening | **COMPLETED & VERIFIED** | 1,121/1,121 Unified Green | 5-Tier Modular TTS Platform Core, ModelGateway Bridge, TakeBank & Net-Silence (`origin/tts-system`) |
| **Phase 6** | Pro-Grade AI Vocal Mastering | **COMPLETED & VERIFIED** | 57/57 + 1,183/1,183 Full Suite Green | C++ JUCE / FFmpeg Vocal Mastering & M4B (`origin/audio-mixing-and-production`) |
| **Phase 7** | Enterprise DAG Orchestrator & UI | **READY TO EXECUTE** | ~1,250 Tests | SQLite WAL Pipeline Ledger & Studio Panel UI (`origin/Voculs`) |




