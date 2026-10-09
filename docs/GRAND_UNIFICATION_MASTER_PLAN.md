# 🏛️ Audiobook Studio Grand Unification Master Plan
## The 7-Layer Topological Merge Roadmap for Enterprise Modular Architecture

- **Document Identifier**: `ENG-SPEC-GRAND-UNIFICATION-V1`
- **Canonical Project ID**: `proj-audiobook-studio`
- **Classification**: Master Architecture Roadmap & Integration Standard
- **Status**: ACTIVE & RATIFIED (Zero-Regression Invariant)
- **Baseline Test Suite**: 881/881 Passed (100% Green on `main`)

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

| Layer | Remote Branch | Target Subsystem / Directory | Core Technical Breakthrough | Test Suite |
| :---: | :--- | :--- | :--- | :--- |
| **L1** | `origin/model-and-keys-manager` | `audiobook_factory/core/models/` | **ACID Key Lease Manager**, 7 Iron Shields Anti-Ban Guard, 50+ Model Registry, Polymorphic Adapters (`gemini`, `openai_compat`, `local_gpu`), `ModelGateway` Facade, `keys` CLI | 70/70 Green (100%) |
| **L2** | `origin/extraction-system` | `audiobook_factory/extraction/` | Forensic Ingestion (PDF XY-cut, EPUB aside filter, LaTeX math/table AST blocks, Gate 0.1) | *(Integrated on `main`)* |
| **L3** | `origin/research-system` | `audiobook_factory/preproduction/`<br/>`audiobook_factory/metadata/` | **2-System Decoupled Novel Researcher**: Book DNA, Cast Lock ($\ge 4.0\%$ pitch spacing), Dramatis Personae, Gate NR-GATE-02 bidirectional grounding | 4 test suites |
| **L4** | `origin/translation` | `audiobook_factory/translation/` | **Option D Standalone Translation**: Single-pass deliberative translation (Gemini Flash `thinking_budget=1024`), macro-chunking, full-text deterministic parity gates, zero audio imports | 8 test suites |
| **L5** | `origin/dramaturgy` | `audiobook_factory/dramaturgy/`<br/>`audiobook_factory/adapters/` | **Option C Universal Dramaturgy AST**: `dramatic_plan.json`, `AudiobookAdapter` (verbatim prose & Anti-Swap attribution), `PodcastAdapter` (2-host dynamics), Gate 2.5 Validator | 8 test suites |
| **L6** | `origin/tts-system` | `audiobook_factory/tts/` | **Option C 4-Tier TTS Platform Core**: `GenericTTSClient`, `LongFormTTSClient`, `MultiCastStudioClient`, TakeBank, net-silence stitching, float-domain DSP | 8 test suites |
| **L7** | `origin/audio-mixing-and-production` | `audiobook_factory/audio/` | **v5.4 AI Vocal Mastering Workstation**: Pure Vocals-Only, 30Hz highpass, 5ms Hann taper, dialogue editorial, Spotify Pedalboard/DeepFilterNet fallbacks, EBU R128 (-19 LUFS) | 7 test suites |
| **L8** | `origin/Voculs` | `audiobook_factory/dag/`<br/>`sidecars/studio-panel/` | **v6.0 Enterprise DAG Orchestrator**: SQLite WAL `pipeline_ledger.db`, diff reconciler, modular CLI suite, Antigravity Studio Panel sidecar UI extension | 179/179 Green |

---

## 3. The 7-Layer Topological Merge DAG

To prevent circular dependencies, merge collisions, and test breakages, merging must proceed strictly along this directed dependency graph:

```mermaid
flowchart TD
    subgraph Foundation["LAYER 1: FOUNDATION CONTROL PLANE"]
        L1["origin/model-and-keys-manager<br/>(Key Lease Engine, Anti-Ban Shields, Model Registry, ModelGateway)"]
    end

    subgraph Input_Preprod["LAYER 2: INGESTION & PRE-PRODUCTION"]
        L2A["main extraction<br/>(Already verified: extraction/ + podcast verbalizer)"]
        L2B["origin/research-system<br/>(Book DNA, Cast Lock, Dramatis Personae, Metadata Ledger)"]
    end

    subgraph Room2["LAYER 3: ROOM 2 TRANSLATION COLLECTIVE"]
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
    L1 --> L3
    L1 --> L4
    L1 --> L5
    L2A --> L2B
    L2B --> L3
    L3 --> L4
    L4 --> L5
    L5 --> L6
    L1 & L2B & L3 & L4 & L5 & L6 --> L7
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

## 5. Phase 1 Detailed Blueprint: `model-and-keys-manager`

### 5.1 Objectives
- Ingest [`audiobook_factory/core/models/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/):
  - `db.py`: SQLite WAL database connection and schema initializer.
  - `lease_manager.py`: ACID single-request lease manager (`Concurrency = 1`).
  - `anti_ban_guard.py`: 7 Iron Shields anti-ban traffic shaping.
  - `registry.py`: Canonical 50+ model capability registry.
  - `policy_engine.py`: Normalized API error classification & circuit breakers.
  - `router.py`: Request router & execution planner.
  - `gateway.py`: Unified `ModelGateway` production facade.
  - `adapters/`: `gemini.py`, `openai_compat.py`, `local_gpu.py`.
- Wire `audiobook_cli.py keys` (`status`, `audit`, `reset`).
- Re-export symbols in `audiobook_factory/__init__.py` lazily.
- Run 70 dedicated tests + existing 881 tests $\rightarrow$ Target: **$\ge 950$ tests passing**.

---

## 6. Forward Milestones Summary

| Phase | Subsystem | Target Test Baseline | Key Deliverable |
| :---: | :--- | :---: | :--- |
| **Phase 1** | Model & Keys Manager | ~951 Tests | Production Control Plane & Anti-Ban Guard |
| **Phase 2** | Novel Researcher & Pre-Production | ~980 Tests | Deterministic Cast Lock & World Knowledge |
| **Phase 3** | Standalone Translation (Option D) | ~1,020 Tests | Single-Pass Macro-Chunker & Parity Gates |
| **Phase 4** | Universal Dramaturgy (Option C) | ~1,070 Tests | Chapter Dramatic AST & Dual-Host Adapters |
| **Phase 5** | Studio TTS Platform Core | ~1,150 Tests | 4-Tier TTS Engine, TakeBank & Net-Silence |
| **Phase 6** | Pro-Grade AI Vocal Mastering | ~1,200 Tests | C++ JUCE / FFmpeg Vocal Mastering & M4B |
| **Phase 7** | Enterprise DAG Orchestrator & UI | ~1,250 Tests | SQLite WAL Pipeline Ledger & Studio Panel UI |

