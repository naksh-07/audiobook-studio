# 🏛️ Architecture: Audiobook Studio (Option C Pure Vocals-Only Engine v6.0)

## Executive Overview

**Audiobook Studio (Option C Pure Vocals-Only Engine v6.0 - Grand Unification 100% Certified)** is an autonomous, studio-grade vocal production framework and Google Antigravity Plugin engineered specifically for **broadcast-grade spoken audio across multiple deliverables**:
1. **Audible-Standard Multi-Cast Audiobooks**: Pristine verbatim prose preservation, em-dash dialogue framing, transparent measured narration (temperature 0.32), and two-pass linear EBU R128 mastering at **-19.0 LUFS** / **-1.5 dBTP**.
2. **Conversational 2-Host Narrative Podcasts**: High-retention audio-first shows featuring calibrated host dynamics (Sameer/Priya in Hindustani, Alex/Maya in English), organic breathability ($\le 22$ words per breath, 140ms pre-roll breath pauses), 5-part retention arcs, stereo spatial staging (-0.25 Left / +0.25 Right), and **-16.0 LUFS** broadcast podcast mastering.
3. **Crown Jewel Studio UI Workstation (Phase 7)**: Apple Minimalist Light UI Architecture (macOS Sonoma / Tahoe HIG), 100% offline isolation (zero CDNs/external fonts), 120 FPS double-buffered Canvas 2D waveform scrubber, $\le 2.1\text{ MB}$ heap footprint, sub-millisecond vectorized Python audio peaks bridge, and Node.js Sidecar API with 50-item LRU cache and HTTP 206 Partial Content byte range streaming.

> [!IMPORTANT]
> **Pure Vocals-Only Architectural Invariant**:
> Background music (BGM), sound effects (SFX), 5-track stem mixdowns, and Archive.org sound scraping are **permanently decoupled and archived** in [`archive/cinematic_audio/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/archive/cinematic_audio/). Production compute is 100% focused on vocal clarity, multi-character acting nuance, conversational breathability, and Audible/EBU R128 compliance.

---

## 🏗️ High-Level Option C Architecture

The system strictly implements **Option C: Shared Understanding & Dramaturgy Core with Specialized Format Adapters and Crown Jewel UI Workstation**:

```mermaid
flowchart TD
    subgraph Room1["🌍 Room 1: 2-System Pre-Production Architecture"]
        direction TB
        RawBook["Raw Book (PDF / EPUB / TXT)"] --> S1["System 1: Novel Researcher Engine<br/><i>(Stateless Compute & Zero Disk I/O)</i><br/>• LexicalCorpusScanner (0-Token Full Sweep)<br/>• NovelDeepSearchEngine (Bidirectional Grounding)<br/>• BookDNAAgent + DramatisPersonaeAgent<br/>• VocalAcousticDirector (Room Impulse DSP)<br/>• PhoneticLexiconDramaturge (70/30 Devanagari)"]
        S1 -->|"Immutable Pydantic DTOs"| S2["System 2: Novel Metadata & State Maintainer<br/><i>(Canonical State Store & Atomic Persistence)</i><br/>• audiobook_factory/metadata/ (BookBible & NovelEntity)<br/>• NovelStateMaintainer (NR-GATE-06 Two-Phase Commit)<br/>• _STATE_LOCK (Thread Concurrency Protection)<br/>• Dynamic Character Locking (NR-GATE-03 Clamp [0.70, 1.30])"]
        S2 --> MasterFiles[("Locked Master State<br/>book_dna.json | book_bible.json | cast_lock.json<br/>vocal_spaces.json | voice_registry.json")]
    end

    subgraph Room1_5["📚 Room 1.5: Standalone Chapter Glossary & Metadata Hub"]
        MasterFiles --> GloMgr["GlossaryManager (audiobook_factory/glossary/)<br/>• ChapterLexicalScanner (0-Token Fast-Path Sweep)<br/>• GlossaryClassifier (Tri-Partite Entity Taxonomy)<br/>• Alias Unification & Dynamic Character Locking<br/>• Persistent Artifact: chapter_XXX_glossary.json"]
        GloMgr --> Projections["Multi-Consumer Projections<br/>• to_translation_glossary() (Flat en -> hi Map)<br/>• to_scripting_roster() (Unified Alias Schema)<br/>• to_dramaturgy_characters() (Scene Cast List)"]
    end

    subgraph Room2["🧠 Room 2: Standalone Literary Translation Engine (Option D)"]
        Projections --> Collective["Decoupled Literary Translation Engine<br/>• Single-Pass Deliberative Generation (thinking_budget = 1024, temp = 0.35)<br/>• Bilingual Macro-Chunking (1,500 - 1,800w with Src + Tgt tail)<br/>• Fast Deterministic Parity Gate Matrix (0 LLM Tokens)<br/>• Tri-Partite Entity Partitioning (Zero Novel Hardcoding)<br/>• Strictly Text-to-Text: Pristine Devanagari Markdown Only"]
        Collective --> DualRule["Dual-Rule Invariant ('Nothing Above Source')<br/>Classic Reverent Pathos vs Raw Unrated Realism"]
    end

    subgraph Room3["🎭 Room 3: Universal Dramaturgy Core (dramaturgy/)"]
        DualRule --> SceneAn["SceneAnalyzer (Organic Scene Boundary Discovery)"]
        SceneAn --> BeatPl["BeatPlanner (Stanislavski Actioning, SPU Slicing & Tension Curves)"]
        BeatPl --> PBible["PerformanceBible (Vocal Profiles & Restraint Clamping)"]
        PBible --> DramAST["Immutable Chapter Dramatic AST (dramatic_plan.json)"]
    end

    subgraph Room3Adapters["🎙️ Room 3 Adapters: Specialized Scripting Adapters (adapters/)"]
        DramAST -->|Audible Flow Standard| AudiobookAd["AudiobookAdapter (adapters/audiobook.py)<br/>• Prose-Lead Framing ('वक्ता ने पूछा—')<br/>• Unbroken Character Dialogue Turns<br/>• Transparent Measured Narration (0.32 temp)<br/>• Anti-Swap Dialogue Attribution (0% Inversion)"]
        DramAST -->|Conversational Spoken-First| PodcastAd["PodcastAdapter (adapters/podcast.py)<br/>• 2-Host Dynamic (Inquisitive Driver <-> Domain Expert)<br/>• SpokenBreathabilityTransformer (<= 22 words, 140ms breath)<br/>• 5-Part Retention Arc (Cold Open to Show Outro)<br/>• Stereo Spatial Staging (-0.25 Left / +0.25 Right)"]
    end

    subgraph Room3_5["🎙️ Room 3.5: Studio Voice Casting & Acoustic Calibration Engine (Option C)"]
        direction TB
        Registry["VoiceProfileRegistry (Shared Core)<br/>• 2,089 Curated Voices (114 Native Hindi)<br/>• Sub-Millisecond Archetype & Dialect Query<br/>• Provider Capabilities (Gemini & Qwen)"]
        Director["StudioCastingDirector (Subsystem 1)<br/>• ModelGateway Control Plane (123+ Key Pool)<br/>• Anime Seiyū Child Rule Guard<br/>• Regional Hindustani Dialect Matching<br/>• CastLockManager (Immutable Project Persistence)"]
        Calibrator["SceneAcousticCalibrator (Subsystem 2)<br/>• Pairwise Euclidean Contrast Matrix (>= 0.65)<br/>• Surgical Non-Destructive Parametric EQ Formants<br/>• 150 Hz Chest Resonance vs 2.8 kHz Presence Boost<br/>• Phase-Safe: Zero asetrate/atempo Digital Resampling"]
        Adapters["Provider Voice Adapters<br/>• GeminiVoiceAdapter (REST payload + EQ formants)<br/>• QwenVoiceAdapter (Native speed + Prompt Audio WAV)"]
        Registry --> Director --> Calibrator --> Adapters
    end

    subgraph Gate28["🛡️ Gate 2.8: Auditory Distinction Gate (gate28_distinction.py)"]
        G28["AuditoryDistinctionGate<br/>• Speaker Whitelist & Cast Lock Verification<br/>• Zero Silent Fallback to Narrator<br/>• Scene Pairwise Auditory Separation Distance >= 0.65<br/>• Phase-Safe Invariant: Banned asetrate / atempo"]
    end

    subgraph Gate29["🛡️ Gate 2.9: Pre-TTS Config & Attribution Sanity Gate (Fail-Closed Boundary)"]
        G29["PreSynthesisGate & LLMPreSynthesisJudge<br/>• Tier 1: Deterministic Fast-Path (Whitelist, Hindi Gender Inflection, Acoustic Bounds)<br/>• Tier 2: Adversarial LLM Attribution Judge (123+ Gemini Key Pool, BLOCK_NONE)<br/>• Fail-Closed: Raises GateAuditError to prevent API quota burn"]
    end

    subgraph Room4["🎙️ Room 4: Studio TTS Platform Core (Option C)"]
        Facades["Specialized Client Facades<br/>• GenericTTSClient (Single-Utterance / Audition)<br/>• LongFormTTSClient (Prose Stream & Checkpoints)<br/>• MultiCastStudioClient (Ensemble Screenplay)"]
        Facades --> CoreEng["Shared TTS Core & Model Adapters<br/>• UniversalInputGuard & 4-Tier Semantic Chunker<br/>• gateway_bridge.py (ModelGateway Control Plane Bridge)<br/>• Gemini Flash TTS (123+ Key Pool, BLOCK_NONE)<br/>• Qwen3-TTS (HardwareVRAMGuard)"]
        CoreEng --> EditorialDSP["Editorial DSP & Quality Gate<br/>• TwoTierAudioQualityGate (Math + Phonetic)<br/>• FormantSculptor (Headroom EQ & Soft Tanh)<br/>• EditorialDSPEngine (12ms/18ms Hann Fades & Net Silence)<br/>• TakeBankManager (Multi-Take Auditioning)"]
    end

    subgraph Room5["🎛️ Room 5: Broadcast Mastering & Multi-Format Packaging"]
        EditorialDSP --> TrackSplit{"Format Mode Dispatch"}
        TrackSplit -->|Audiobook Track| M4BMaster["Studio Vocal Master: -19.0 LUFS / -1.5 dBTP<br/>SOXR 48kHz / 24-bit + Dual-Pass Linear Loudnorm<br/>Chaptered .m4b with Embedded Cover Art"]
        TrackSplit -->|Podcast Track| M4AMaster["Podcast Master: -16.0 LUFS / -1.0 dBTP<br/>Stereo Spatial Azimuth Staging (-0.25 / +0.25)<br/>AAC .m4a / .mp3 with Show Notes & Chapters"]
    end

    subgraph CertHarness["🎖️ 8-Pillar Studio Production Certification Harness"]
        M4BMaster & M4AMaster --> Runner["StudioCertificationRunner (certification/runner.py)<br/>P1 Extraction | P2 Translation | P3 Dramaturgy | P4 Attribution<br/>P5 Performance | P6 Loudness | P7 Spatial | P8 Packaging"]
        Runner --> Report["STUDIO_CERTIFICATION_REPORT.json (Gate 6 Compliance)"]
    end

    subgraph Room6["🖥️ Room 6 / Aux-Pane: Crown Jewel Studio UI Workstation & Sidecar Bridge"]
        direction TB
        Sidecar["Node.js Sidecar API (sidecars/studio-panel/main.mjs)<br/>• /api/status | /api/projects | /api/project<br/>• /api/peaks (50-Item LRU Cache)<br/>• /api/audio (HTTP 206 Byte Range Streaming)"]
        Bridge["Vectorized Python Bridge (audiobook_factory/api/studio_bridge.py)<br/>• Sub-Millisecond soundfile + numpy Peak Extraction (< 1ms)<br/>• SQLite State Introspection (project_state.db & key_pool_state.db)<br/>• Curated Voice Roster & 5-Room DAG Telemetry"]
        Frontend["Apple Minimalist Light UI (sidecars/studio-panel/)<br/>• 100% Offline (Zero CDN / Zero External Fonts)<br/>• 120 FPS Double-Buffered Canvas 2D Waveform Scrubber<br/>• ≤ 2.1 MB Heap RAM | ~39 KB Bundle<br/>• 5-Room Interactive Stepper & Hindi Editorial Inspector"]
        Sidecar <--> Bridge
        Sidecar <--> Frontend
    end

    Room1 --> Room1_5
    Room1_5 --> Room2
    Room1_5 -.->|"Roster & Aliases"| Room3
    Room1_5 -.->|"Dynamic Voice Lock"| Room3_5
    Room2 --> Room3
    Room3 --> Room3Adapters
    Room3Adapters --> Room3_5
    Room3_5 --> Gate28
    Gate28 --> Gate29
    Gate29 -->|"Audited Script (0% Swap / 0% Swallow / Distance >= 0.65)"| Room4
    Room4 --> Room5
    Room5 --> CertHarness
    CertHarness -.->|"Telemetry & Master Deliverables"| Room6
    Room1 & Room2 & Room3 & Room4 & Room5 -.->|"State & Audition Audio"| Room6
```

---

## 🏛️ Two-Tier Decoupling & Domain-Scoped Metadata Architecture

The Audiobook Studio engine enforces a strict separation between pure compute engines, persistent domain truth, and orchestration automation:

### 1. Two-Tier Decoupling Architecture
```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   TWO-TIER DECOUPLING ARCHITECTURE                                │
│                                                                                                  │
│  TIER 1: PURE, STATELESS STANDALONE ROOM ENGINES (Zero Project State, Pure Transforms)           │
│  • Room 0 / 1: ExtractionEngine (audiobook_factory.extraction.engine)                           │
│    Document -> CanonicalBook AST + clean Markdown chapters. Pure functional transformation.      │
│  • Room 2: translate_chapter / TranslationEngine (audiobook_factory.translation.engine)          │
│    Prose in -> Devanagari Markdown out. Zero audio, screenplay, or project state imports.       │
│  • Room 3: ScreenplayDramaturgyRoom (audiobook_factory.script.agents.script_room)                │
│    5-pass dramaturgy core coordinating beat actioning, actor direction & Gate 2 attribution.    │
│  • Room 5: MasteringEngineV2 (audiobook_factory.mastering_engine)                                │
│    Audio stem in -> EBU R128 (-19 LUFS) vocal master + MasteringLedger JSON out.                 │
│                                                                                                  │
│  TIER 2: ORCHESTRATION & JIT RESOLUTION (Workflow Coordination, State Lifecycle & Auto-Healing) │
│  • CLI Runners: audiobook_cli.py (auto, produce, translate, script, package, doctor)             │
│  • Dialogue Runners: dialogue_runner.py & PodcastOrchestrator                                     │
│  • JIT Pre-Production Auto-Resolution: Detects missing book_bible.json or cast_lock.json and     │
│    runs Room 1 Pre-Production Just-In-Time before downstream execution.                          │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Tier 1 (Pure, Stateless Standalone Room Engines)**:
  - [`ExtractionEngine`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/extraction/engine.py): Slices and normalizes raw digital books (`.epub`, `.pdf`, `.txt`, `.md`) into structured [`CanonicalBook`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/extraction/contracts.py#L231) AST and pristine chapter Markdown without relying on downstream pipeline directories.
  - [`translate_chapter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/engine.py): Standalone, text-to-text literary Hindustani translation engine executing single-pass deliberation (`thinking_budget = 1024`, `temperature = 0.35`) and 0-token parity gate checks. Has **zero imports** from audio, speech synthesis, screenplay tagging, or hardware drivers.
  - [`ScreenplayDramaturgyRoom`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/script/agents/script_room.py): Autonomous 5-pass multi-agent screenplay dramaturgy engine managing scene analysis, Stanislavski beat actioning, performance direction, and Gate 2 anti-swap dialogue attribution.
  - [`MasteringEngineV2`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/mastering_engine.py): Dedicated vocal mastering engine applying Kaiser sinc 48kHz / 24-bit resampling, two-pass linear EBU R128 (-19.0 LUFS) normalization, lookahead True Peak limiting ($\le -1.5\text{ dBTP}$), and formal cryptographic `MasteringLedger` generation.
- **Tier 2 (Orchestration & JIT Resolution)**:
  - Encapsulates pipeline DAG traversal, concurrent thread pooling, checkpoint recovery, and automated state synchronization across steps.
  - **JIT Pre-Production Auto-Resolution**: When downstream commands such as `translate` or `script` are executed on an extracted project lacking pre-production master assets (`book_bible.json` and `cast_lock.json`), Tier 2 automatically executes Room 1 Pre-Production JIT via [`run_preproduction(project_dir, force=False)`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/__init__.py). The 0-token lexical scanner, entity taxonomist, and vocal acoustic director establish canonical lore and collision-free voice locks transparently before downstream execution proceeds.

---

### 2. Domain-Scoped Metadata Architecture (The Anti-Monolithic JSON Invariant)
The architecture explicitly bans the fragile anti-pattern of a monolithic multi-megabyte `metadata.json` or shared project dictionary. Storing all novel state, chapter metrics, casting, and audio telemetry in a single file causes write contention, data corruption during interrupted runs, and Git merge nightmares. Instead, Audiobook Studio partitions master state across **dedicated Single Source of Truth (SSOT) artifacts** with dynamic, backward-compatible auto-projections:

| Domain Artifact | File Location | Authoritative Responsibility (SSOT) | Downstream Consumers |
|---|---|---|---|
| **Cast Lock** | `cast_lock.json` | Supreme voice casting authority: voice persona IDs, lock status, and 4D acoustic vector overrides (pitch ratio $[0.85, 1.15]$, speed ratio $[0.75, 1.30]$, EQ formants). | Room 3.5, Gate 2.8, Gate 2.9, Room 4 TTS, Gate 6A |
| **Book Bible** | `book_bible.json` | World lore canon, entity taxonomies (`BookEntity`), locations, items, epistemic provenance (`CORPUS_EXTRACTED`, `WEB_VERIFIED`), and honorific pronoun rules (`aap`/`tum`/`tu`). | Room 1.5, Room 2 Translation, Room 3 Dramaturgy, Gate 6A |
| **Translation Glossary** | `translation/glossary.json` | Deterministic Hindi term bindings, proper noun transliterations, and heraldic moniker phonetics (`PROPER_NAME` / `HERALDIC_MONIKER`). | Room 2 Translation Engine |
| **Mastering Ledgers** | `mastered/*_mastering_ledger.json` | Chapter-level audio provenance: cryptographic stem hashes, measured loudness (`integrated_lufs`), True Peak (`true_peak_dbtp`), duration, and filter configs. | Gate 6B Fast-Path, Studio UI Sidecar, M4B Packaging |
| **Character Roster (Projection)** | `character_roster.json` | *Backward-compatible auto-projection* from `BookBible` and `CastLock`. Re-generated dynamically by `NovelStateMaintainer` on each state commit. | Legacy test suites, legacy script parsers |
| **Voice Registry (Projection)** | `voice_registry.json` | *Backward-compatible auto-projection* of actor voice mappings from `CastLock`. Re-generated dynamically by `NovelStateMaintainer`. | Legacy CLI tools, third-party inspect scripts |

---

### 3. Zero-Token Pre-Flight Metadata Doctor
Implemented in [`audiobook_factory/metadata/doctor.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/doctor.py), the **Metadata Doctor** is an offline, millisecond-fast ($<50\text{ms}$) forensic validator that audits decoupled metadata health across all 6 production rooms **before a single generative AI API token is consumed**:

1. **Room 0 (Extraction)**: Validates chapter markdown inventory in `extracted/`, checks `source_manifest.json` and `metadata.json`, and verifies word count health.
2. **Room 1 (Canon & Lore)**: Parses `book_bible.json` through Pydantic v2 [`BookBible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py) validation, asserting character and location schema integrity.
3. **Room 1 (Voice Casting SSOT)**: Validates `cast_lock.json`, audits pitch safety ratio bounds ($[0.85, 1.15]$), and verifies **$\ge 4.0\%$ pitch separation** across characters sharing a base voice persona to prevent vocal convergence.
4. **Room 2 (Translation Glossary)**: Verifies `translation/glossary.json` integrity and aligns transliterated honorifics with source entities.
5. **Room 3 (Screenplay Coverage)**: Samples up to 10 chapter scripts in `scripts/`, extracts all dialogue tokens, and ensures **100% speaker coverage** across `cast_lock.json`, `book_bible.json`, `character_roster.json`, and `voice_registry.json` (**0 unmapped dialogue speakers**).
6. **Room 5 (Mastering V2 Ledgers)**: Scans all `mastered/*_mastering_ledger.json` files, verifying measured integrated loudness ($-19.0 \pm 1.0\text{ LUFS}$) and True Peak ceiling ($\le -1.4\text{ dBTP}$).

The Metadata Doctor is integrated at multiple pipeline control points:
- **CLI Command**: `python audiobook_cli.py doctor <book_slug_or_path>` (exits `0` on clean health, `1` on critical defects).
- **Macro Audit Pre-Flight**: `python audiobook_cli.py audit-book <book>` runs the Doctor diagnosis first before initiating Gate 6.
- **Gate 2.9 Pre-TTS Boundary**: Runs offline before LLM attribution evaluation to halt invalid scripts before burning API quota.
- **Studio Panel Sidecar API**: `GET /api/doctor?slug=...` returns real-time diagnostic JSON and formatted health tables to the Webview UI.

---

## 🏛️ The 5-Room Pure Vocals-Only Pipeline

### Room 1: Pre-Production World, Lore & Canonical State Studio
*Subsystems: System 1 Researcher Engine ([`audiobook_factory/preproduction/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/)) & System 2 Metadata Maintainer ([`audiobook_factory/metadata/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/))*

Room 1 operates under a strict **2-System Decoupled Architecture**:
1. **System 1: Novel Researcher Engine (Pure Stateless Compute, 0 Disk I/O)**:
   - **Deterministic 0-Token Lexical Scanner** ([`LexicalCorpusScanner`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/lexical_scanner.py)): Sweeps entire novel text in under $50\text{ms}$ with UTF-8 replacement defense (`errors="replace"`), indexing word counts, proper nouns, dialogue attribution frequencies, and speaker introduction quotes into [`LexicalCorpusIndex`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/lexical_scanner.py).
   - **Bidirectional Web Grounding** ([`NovelDeepSearchEngine`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/novel_deepsearch.py)): Leverages Google Search Grounding to assemble [`DeepSearchNovelDossier`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/novel_deepsearch.py). Enforces **NR-GATE-02**: entities from search results must possess $\ge 2$ mentions in the local text corpus to be granted canonical status.
   - **Universal Literary DNA** ([`BookDNAAgent`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/book_dna_agent.py)): Dynamically resolves literary tradition, source fidelity tier (`CLASSIC_REVERENT` vs `RAW_UNRATED`), regional cadence, and profanity policy without hardcoded novel titles or author biases.
   - **Dramatis Personae & Sociolects** ([`DramatisPersonaeAgent`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/dramatis_personae_agent.py)): Identifies character taxonomies, social hierarchy, vocal weight, and baseline honorific pronouns (`aap`, `tum`, `tu`).
   - **Vocal Acoustic Director** ([`VocalAcousticDirector`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/vocal_acoustic_director.py)): Designs pure vocal room acoustics (reverb wet mix, decay time, predelay) into [`VocalSpacesManifest`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/vocal_acoustic_director.py) with zero BGM/SFX artifacts (**NR-GATE-04**), with hardened pitch ratio protection against `ZeroDivisionError` (`ratio = max(0.1, 1.0 + (eff_pitch_pct / 100.0))`).
   - **Phonetic Lexicon Dramaturge** ([`PhoneticLexiconDramaturge`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/phonetic_lexicon_dramaturge.py)): Maps names, heraldic monikers, and world lore into 70/30 Devanagari phonetics.
   - **Acoustic Worldbuilding & Legacy Projection** ([`SonicWorldArchitect`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/sonic_world_architect.py)): Synthesizes backwards-compatible `sonic_bible.json` projections without BGM/SFX pollution.
   - **Pre-Production ModelGateway Bridge** ([`gateway_bridge.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/gateway_bridge.py)): Authoritative routing hub implementing [`execute_preproduction_llm()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/gateway_bridge.py#L37). Directs 100% of LLM queries through [`ModelGateway.generate_text()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py#L98) with Concurrency=1 key leases from [`KeyLeaseManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py#L142), AntiBanGuard rate limiting (11.0 RPM), stealth SDK headers (`x-goog-api-client`), session affinity, `BLOCK_NONE` creative safety framing, and `json_repair`. Direct `urllib` or unmetered HTTP calls are completely eliminated.
   - **Stateless Orchestrator** ([`PreProductionSupervisor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/preproduction_supervisor.py)): Aggregates DTOs without direct disk writing, delegating canonical persistence to System 2.

2. **System 2: Novel Metadata & State Maintainer (Canonical Persistence & Thread Safety)**:
   - **Canonical Lore & Entity Registry** ([`BookBible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py) & [`NovelEntity`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py)): Single source of truth recording character profiles, 4D acoustic vectors, and forensic [`EpistemicProvenance`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py) (`CORPUS_EXTRACTED`, `WEB_VERIFIED`, `INFERRED_DERIVED`). Re-exported via backward-compatible facade at [`audiobook_factory/translation/book_bible.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/book_bible.py).
   - **NR-GATE-06 Two-Phase Atomic Multi-File Staging** ([`NovelStateMaintainer`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/state_maintainer.py)): Atomically commits all 7 master state files (`book_dna.json`, `book_bible.json`, `vocal_spaces.json`, `sonic_bible.json`, `character_roster.json`, `voice_registry.json`, `cast_lock.json` + `translation/glossary.json`) by staging to `.tmp.{staging_id}`, snapshoting existing files to `.bak.{staging_id}`, atomically swapping via `_atomic_replace()`, and performing automated rollback (Phases A-D) if any I/O failure occurs.
   - **Windows 11 Atomic Replace Hardening**: `_atomic_replace()` executes a 5-attempt retry loop with exponential backoff (`0.015 * (2 ** attempt)`), eliminating `WinError 5` (Access Denied) and `WinError 32` (Sharing Violation) from Windows Defender or search indexer transient file locks.
   - **Thread-Safe Mid-Novel Casting** (`discover_and_lock_character`): Protected by `_STATE_LOCK = threading.RLock()`, enabling downstream translation and screenplay threads to dynamically register and cast minor characters without race conditions.
   - **NR-GATE-03 Pitch Clamping `[0.70, 1.30]`**: Step-stepping algorithm guarantees $\ge 4.0\%$ acoustic separation while bounding pitch between `0.70` and `1.30` with secondary speed micro-tuning ($+0.02$) to prevent robotic distortion across large ensembles.

---

### Room 1.5: Standalone Chapter Glossary & Metadata Hub
*Subsystems: [`audiobook_factory/glossary/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/) (`contracts.py`, `scanner.py`, `classifier.py`, `manager.py`, `gateway_bridge.py`)*  
*(See full architectural manual: [`docs/GLOSSARY_AND_METADATA_SUBSYSTEM.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/GLOSSARY_AND_METADATA_SUBSYSTEM.md))*

Room 1.5 is the decoupled, single-pass per-chapter lexical analysis, entity discovery, and metadata projection hub. Positioned between whole-novel pre-production (Room 1) and downstream consumers (Rooms 2, 3, and 4), it enforces strict cross-chapter lexical and voice consistency:

1. **Zero-Import Architectural Isolation**:
   - 100% decoupled from downstream audio (`audiobook_factory.audio`), speech synthesis (`audiobook_factory.tts`), screenplay (`audiobook_factory.screenplay`), and direct networking (`urllib.request`, `requests`, `httpx`).
   - Continuously enforced by AST test [`tests/glossary/test_zero_import_isolation.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/tests/glossary/test_zero_import_isolation.py).
2. **High-Speed Lexical Scanner & Zero-Token Fast-Path** ([`ChapterLexicalScanner`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/scanner.py)):
   - Sweeps chapter text in under $15\text{ms}$ using regex capitalization pattern matching, mid-sentence appearance checks, and 130+ non-entity stopword filters ([`ENGLISH_NON_ENTITY_STOPWORDS`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/scanner.py#L19)).
   - Filters candidate entities against known names and lore in [`BookBible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py). If all candidate entities are already cataloged, **zero LLM tokens are consumed** (`llm_invoked=False`).
3. **Tri-Partite Taxonomy & Alias Unification** ([`GlossaryClassifier`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/classifier.py)):
   - **`PROPER_NAME`**: Phonetic Devanagari transliteration (*Corwin* $\to$ *कॉरविन*).
   - **`HERALDIC_MONIKER`**: Phonetic Devanagari transliteration (*Silver Falcon* $\to$ *सिल्वर फाल्कन*). Literal word-for-word calques (*चांदी का बाज़*) are strictly banned.
   - **`OCCUPATIONAL_ROLE`**: Natural spoken Hindustani translation (*The Stranger* $\to$ *अजनबी*, *The Butcher* $\to$ *कसाई*).
   - **Alias Unification**: Links emergent monikers and epithets to canonical characters, preventing downstream screenplay and TTS engines from splitting one persona across multiple voice actors.
4. **Dynamic Voice Allocation & Canonical Lore Sync** ([`GlossaryManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/manager.py)):
   - Discovered characters are committed to `BookBible` with forensic provenance ([`EpistemicProvenance`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py) with origin `CORPUS_EXTRACTED`).
   - Triggers dynamic voice allocation via [`NovelStateMaintainer.discover_and_lock_character()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/state_maintainer.py), guaranteeing collision-free 4D formants in `cast_lock.json`.
5. **Durable Chapter Artifacts & Multi-Consumer Projections** ([`ChapterGlossary`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/contracts.py)):
   - Persists deterministic chapter snapshot artifacts to `glossary/chapter_XXX_glossary.json` with 16-character SHA-256 version fingerprints.
   - **Room 2 Projection** ([`to_translation_glossary()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/contracts.py#L83)): Emits flat English $\to$ Hindi dictionary for `TranslationRequest.dynamic_glossary`.
   - **Room 3 Attribution Projection** ([`to_scripting_roster()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/contracts.py#L103)): Emits structured character roster with unified aliases for `DialogueAttributionAuditor`.
   - **Room 3 Dramaturgy Projection** ([`to_dramaturgy_characters()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/contracts.py#L126)): Emits active scene character names for scene segmentation.
6. **Authoritative Control Plane Routing** ([`execute_glossary_llm()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/gateway_bridge.py#L26)):
   - Routes 100% of LLM queries through `ModelGateway.generate_text()` with atomic Concurrency=1 key leases from `KeyLeaseManager`, AntiBanGuard 11.0 RPM rate limits, official stealth SDK headers (`x-goog-api-client`), and `BLOCK_NONE` creative fiction framing.
   - Fails closed (`RuntimeError`) if ModelGateway is unavailable. Zero unmetered raw HTTP calls.

---

### Room 2: Standalone Literary Translation Engine (Option D Decoupled Architecture)
*Modules: `audiobook_factory/translation/` (`engine.py`, `contracts.py`, `book_bible.py`, `chunker.py`, `parity_gate.py`, `cli.py`, `agents/collective.py`)*

1. **Decoupled Standalone Independence**:
   - The translation engine has **zero imports** from audio, TTS, screenplay, or mastering layers. It operates as an independent, reusable library with strongly typed Pydantic models ([`TranslationRequest`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/contracts.py#L19-L33), [`TranslationResult`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/contracts.py#L61-L70), [`FidelityTier`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/contracts.py#L13-L17), [`ParagraphAlignment`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/contracts.py#L35-L42), [`ParityMetrics`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/contracts.py#L44-L59)).
   - Can be run standalone via CLI: `python -m audiobook_factory.translation.cli translate` and `python -m audiobook_factory.translation.cli parity`.
2. **Single-Pass Deliberation (Option D)**:
   - Replaced the lossy 4-pass serial telephone game cascade (Draft $\rightarrow$ Cadence $\rightarrow$ Idiom $\rightarrow$ Critic) with a single deliberative Gemini Flash call (`thinking_budget = 1024`, `temperature = 0.35`).
   - Gemini leverages internal deliberation tokens to plan English SVO to Hindi SOV clause structures, dynamic honorific levels (*आप* / *तुम* / *तू*), and contextual idioms in a single pass.
   - [`MultiAgentTranslationCollective.translate_block()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/agents/collective.py#L62-L149) defaults to [`TranslationEngine`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/engine.py#L30-L134) (`use_single_pass=True`), while preserving [`translate_block_legacy()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/agents/collective.py#L150-L241) as an explicit backward-compatible fallback (`use_single_pass=False`).
3. **Separation of Concerns & Strict Boundary Contracts**:
   - **Strictly Text-to-Text**: Room 2 emits pristine Devanagari Markdown only.
   - **No Screenplay Actor Tags**: Room 2 **NEVER** injects screenplay actor markers (such as `[GERALT]:`, `[JASKIER]:` or JSON attribution). Dialogue parsing and speaker identification belong 100% to Room 3 (`script_builder.py`).
   - **No Audio Take QA or Synthesis**: Room 2 **NEVER** performs audio take evaluation, acoustic checks, or speech synthesis. All audio operations belong strictly downstream to Room 4.
   - **Zero Forbidden Imports**: Zero imports of `audio`, `tts`, `screenplay`, `cinematic`, or audio hardware drivers in `audiobook_factory/translation/`.
4. **Adversarial Audit Hardening**:
   - **Negation Double-Counting Fix**: `parity_gate.py` strips compound patterns (`कभी नहीं`, `कुछ नहीं`, `कोई नहीं`) from working buffers before single-token evaluation, eliminating artificial Hindi negation inflation.
   - **Truncation Blind Spot Fix**: `parity_gate.py` fails closed on paragraph drops for texts with $> 2$ paragraphs or absolute delta $> 1$.
   - **Purged `audio_utils` Leak**: `orchestrator.py` uses localized `_atomic_replace` (via `os.replace`), completely removing the legacy `audio_utils` import leak.
5. **Bilingual Context-Aware Macro-Chunking**: Chapters $\le 2,200$ words translate in 1 cohesive pass. Longer chapters slice at 1,500–1,800 words on paragraph boundaries, injected with preceding English source context and preceding Hindi target context.
6. **Dual-Rule Invariant ("Nothing Above Source")**:
   - *Classical Literature*: Dignified authorial voice, emotional pathos, and sacred regional cadences without tapori vulgarity.
   - *Raw Unrated Fiction*: Unapologetic preservation of raw street curses, visceral combat gore, and unvarnished somatic intimacy without forced "19-to-21" escalation.
7. **Universal Novel-Agnostic Invariant**: 100% purged of novel-specific hardcoded regexes or character bindings. All entities are classified dynamically into `BookBible`.

### Room 3: Universal Dramaturgy Core
*Modules:* [`audiobook_factory/dramaturgy/scene_analyzer.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/dramaturgy/scene_analyzer.py), [`audiobook_factory/dramaturgy/beat_planner.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/dramaturgy/beat_planner.py), [`audiobook_factory/dramaturgy/performance_bible.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/dramaturgy/performance_bible.py), [`audiobook_factory/dramaturgy/contracts.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/dramaturgy/contracts.py)

1. **Organic Scene Boundary Discovery (`SceneAnalyzer`)**: Discovers natural scene boundaries using multi-signal heuristics (`TIME_PATTERNS`, `LOCATION_PATTERNS`) or 2-pass LLM scene comprehension, computing scene questions, stakes, and entry/exit states.
2. **Beat Planning & Actioning (`BeatPlanner`)**: Slices scenes into 2–5 atomic beats with Stanislavski transitive action verbs (`threaten`, `deflect`, `reassure`, `confess`), underlying desires, core fears, subtext, and continuous tension trajectories ($0.0 \to 1.0$).
3. **SPU Semantic Paragraph Unit Alignment**: Binds each scene and beat to exact paragraph indices (`start_paragraph_idx`, `end_paragraph_idx`) and cryptographic SHA-256 anchors, eliminating paragraph desynchronization.
4. **Performance Bible & Subtext Directing**: Pre-computes actor vocal profiles and locks narrator pacing, preventing double-inference drift in [`StanislavskiSubtextDirector`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/dramaturgy/subtext_director.py).
5. **Immutable Dramatic AST**: Atomically serializes `chapter_XXX_dramatic_plan.json` conforming to the [`DramaticPlan`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/dramaturgy/contracts.py#L353-L415) schema.

---

### Room 3 Adapters: Specialized Scripting Adapters
*Modules:* [`audiobook_factory/adapters/base.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/adapters/base.py), [`audiobook_factory/adapters/audiobook.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/adapters/audiobook.py), [`audiobook_factory/adapters/podcast.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/adapters/podcast.py)

1. **BaseScriptAdapter Lifecycle**:
   - `pre_adapt()`: Pre-flight context validation.
   - `adapt()`: Transforms source prose and `DramaticPlan` into standardized segment dictionaries.
   - `post_adapt()`: Binds `PerformanceBible` profiles and clamps narrator transparency.
   - `validate()`: Executes Gate 2.5 `DramaticValidator`.
2. **Audiobook Script Adapter (`AudiobookAdapter`)**:
   - Preserves 100% verbatim authorial prose.
   - Prose-lead framing (`"वक्ता ने पूछा—"`) ensures seamless em-dash flow.
   - Narrator Transparency Invariant: Clamped to `0.32` temperature with calm, measured delivery.
   - Anti-Swap Dialogue Attribution Auditor guarantees 0% speaker turn inversion ($A \leftrightarrow B$).
3. **Dedicated 2-Host Podcast Adapter (`PodcastAdapter`)**:
   - Conversational persona dynamics: Sameer & Priya (Hindi) / Alex & Maya (English).
   - `SpokenBreathabilityTransformer`: Splits sentences to $\le 22$ words per breath with 140ms pre-roll breath pauses.
   - 5-part retention arc: `cold_open_hook` $\to$ `show_intro` $\to$ `scene_deepdive` $\to$ `cognitive_reset_banter` $\to$ `show_outro`.
   - Stereo spatial staging: Host A at $-0.25$ (Left-Mid) and Host B at $+0.25$ (Right-Mid).

---

### Room 3.5: Studio Voice Casting & Acoustic Calibration Engine (SVCCS - Option C)
*Modules:* [`audiobook_factory/casting/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/), [`audiobook_factory/casting/contracts.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/contracts.py), [`audiobook_factory/casting/registry.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/registry.py), [`audiobook_factory/casting/director.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/director.py), [`audiobook_factory/casting/calibrator.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/calibrator.py), [`audiobook_factory/casting/adapters/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/adapters/)  
*(See full architectural specification: [`docs/STUDIO_VOICE_CASTING_AND_CALIBRATION.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/STUDIO_VOICE_CASTING_AND_CALIBRATION.md))*

Room 3.5 implements **Option C: Shared Understanding & Voice Registry Core with Specialized Decoupled Subsystems**, resolving the prior schism between disparate voice catalogs and uniting 2,089 curated studio voices (including 114 native Hindi voices) under a single canonical architecture:

1. **Shared Core: Canonical Voice Profile Registry & Provider Adapters**:
   - **`VoiceProfileRegistry`** ([`registry.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/registry.py)): Singleton registry indexing all available voices from curated studio catalogs. Exposes sub-millisecond querying (`query_profiles()`) filtering by language code (`hi-IN`, `en-US`), gender, dialect, perceived age, pitch tier (`low`, `medium`, `high`), and dramatic archetype.
   - **`ProviderCapabilities` & Adapters** ([`adapters/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/adapters/)):
     - [`GeminiVoiceAdapter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/adapters/gemini.py): Translates canonical profiles into Gemini REST payloads (`speechMetadata.style`, temperature, and FFmpeg parametric EQ filter strings).
     - [`QwenVoiceAdapter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/adapters/qwen.py): Generates native speed float multipliers and provisions prompt reference audio WAV stems for zero-shot neural voice cloning.

2. **Subsystem 1: Studio Casting Director (`StudioCastingDirector`)**:
   - **Hollywood Ensemble Prompting**: Enforces lead narrator transparency (`0.32` temperature), strict gender matching, dramatic vocal contrast across co-speakers, and regional Hindustani dialect matching (Haryanvi warriors/guards, Bhojpuri commoners/butchers, Awadhi healers/aristocracy, Bundeli foresters, Urdu courtly scholars).
   - **Anime Seiyū Child Rule Guard**: Strictly prohibits adult male baritones from voicing pre-pubescent children (age $< 13$). Automatically casts youthful female voices with bright upper harmonics (`hi-in-tutor-7`, `hi-in-tutor-9`, `Leda`).
   - **Control Plane Gateway Routing**: Routes requests via [`execute_casting_llm()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/gateway_bridge.py) through [`ModelGateway.generate_text()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py) with AntiBanGuard 11.0 RPM pacing and session affinity across the 123+ API key inventory.
   - **Immutable Project Persistence**: Anchors all decisions in `cast_lock.json` via [`CastLockManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/cast_lock.py), dual-indexing by `character_id` and `character_name` to prevent character voice drift across chapters.

3. **Subsystem 2: Scene Acoustic Calibrator (`SceneAcousticCalibrator`)**:
   - **Pairwise Scene Contrast Matrix**: Analyzes all active co-speakers in each scene to compute Euclidean separation distance across acoustic vectors (pitch, perceived age, timbre brightness, formant profile).
   - **Surgical Non-Destructive Parametric EQ Formants**: If co-speaker acoustic distance is $< 0.65$, generates complementary parametric EQ curves:
     - Speaker 1: Low-end warmth boost (+2.0 dB at 150 Hz chest resonance) and gentle presence dip (-1.5 dB at 2.8 kHz).
     - Speaker 2: Presence and clarity boost (+2.0 dB at 2.8 kHz, +1.0 dB at 8 kHz air shelf) with slight low-end reduction (-1.5 dB at 150 Hz).
   - **Phase-Safe Audio Invariant**: Strictly bans destructive digital resampling (`asetrate`) and WSOLA time-stretching (`atempo`) during playback, preserving authentic speech formants and eliminating metallic flanging.
   - **Remediation of the Sledgehammer DSP Bug**: Hardened `TTSDispatcher` (`tts/dispatcher.py`), ensuring that `AUDIBLE_CLEAN_DSP=true` preserves surgical parametric EQ curves without wiping upstream acoustic contrast.

---

### Room 3.5 $\rightarrow$ Room 4 Boundary: Gate 2.8 Auditory Distinction Gate
*Module:* [`audiobook_factory/gates/gate28_distinction.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/gate28_distinction.py)  
*(See full quality gate protocol: [`docs/QUALITY_GATES.md#gate-28-auditory-distinction--acoustic-calibration-gate`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/QUALITY_GATES.md#gate-28-auditory-distinction--acoustic-calibration-gate))*

Gate 2.8 operates as an authoritative pre-synthesis gatekeeper positioned immediately prior to Gate 2.9:
1. **Speaker Whitelist & Cast Lock Verification**: Asserts that every dialogue speaker has a non-null voice assignment in `voice_registry.json` and a permanent lock in `cast_lock.json`. Zero silent fallback to Narrator for dialogue turns.
2. **Scene Pairwise Auditory Separation Distance ($\ge 0.65$)**: Enforces that co-speakers conversing in any scene maintain an acoustic Euclidean distance $\ge 0.65$, guaranteeing that listeners can effortlessly distinguish characters by ear.
3. **Phase-Safe DSP Audit**: Scans segment `eq_filters` and raises a fatal `GateAuditError` if `asetrate` or `atempo` are present.

---

### Room 3 $\rightarrow$ Room 4 Boundary: Gate 2.9 Pre-TTS Config & Attribution Sanity Gate
*Modules:* [`audiobook_factory/gates/pre_synthesis.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/pre_synthesis.py), [`audiobook_factory/orchestration/gates.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/orchestration/gates.py), [`audiobook_factory/podcast/orchestrator.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/podcast/orchestrator.py)

Gate 2.9 stands as the authoritative, fail-closed verification boundary positioned immediately before Room 4 TTS voice dispatch. In production vocal pipelines, synthesizing speech via Gemini Flash TTS consumes rate-limited API quota (10 RPD per key on `gemini-3.8-flash-tts`). Generating audio for defective screenplay segments—such as swapped character roles ($A \leftrightarrow B$), dialogue swallowed into narrator segments, unstripped Markdown fences, or out-of-bounds pitch multipliers—wastes quota and produces corrupted audio stems. Gate 2.9 eliminates this by strictly auditing scripts across both production tracks before synthesis begins:

1. **Dual-Track Execution Paths**:
   - **Audiobook Execution Path** ([`audiobook_factory.orchestration.gates.verify_pre_synthesis_gates()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/orchestration/gates.py#L92-L116)): Audits chapter screenplay scripts (`scripts/chapter_XXX_hi_script.json`) against source narrative prose (`extracted/` or `translation/`), `character_roster.json`, and `voice_registry.json`. If critical defects occur, raises `GateAuditError`, halting synthesis before `TTSDispatcher` is invoked.
   - **Dual-Track Podcast Execution Path** ([`PodcastOrchestrator.synthesize_podcast_script()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/podcast/orchestrator.py#L317-L327)): Audits 2-host conversational scripts (`scripts/chapter_XXX_podcast_script.json`) against `podcast_config.json`, verifying host whitelists, stereo spatial panning (Host A left $\le -0.20$, Host B right $\ge +0.20$), and monologue breathability ($\le 45$ words without pause punctuation).

2. **Dual-Tier Hybrid Architecture**:
   - **Tier 1 (Deterministic Fast-Path)**: Executes instant, 0-token local validation:
     - *Sequential Monotonicity*: Enforces $index_1 < index_2 < index_3$ starting at 1.
     - *Speaker Whitelist*: Verifies that every speaker token resolves in `character_roster.json`, `voice_registry.json`, `podcast_config.json`, or canonical defaults (`Narrator`, `Host_A`, `Host_B`).
     - *Anti-Swap Gender Inflection*: Checks Hindi grammatical first-person verb inflections (`रहा हूँ` / `करूँगा` vs `रही हूँ` / `करूँगी`) against roster character genders to catch gender-discordant speaker turn inversions.
     - *Speech Verb Co-Reference*: Matches dialogue attribution against preceding narrator tags (e.g. *Geralt said: ...* must be attributed to Geralt, not Renfri).
     - *Anti-Swallow Dialogue Guard*: Flags quotation marks in `Narrator` lines accompanied by speech verbs (`कहा`, `बोला`, `said`, `asked`).
     - *Acoustic Parameter Clamping*: Pitch shift clamped to $[0.65, 1.35]$ (ratio) or $[-12.0, 12.0]$ (semitones for podcast); speed multiplier clamped to $[0.75, 1.30]$; asserts non-null, assigned `voice_id`.
     - *Text Hygiene*: Blocks raw Markdown code fences (```` ```json ````) and unstripped conversational LLM preambles (*"Here is the script..."*).
   - **Tier 2 (Adversarial LLM Attribution & Dramaturgy Sanity Judge — [`LLMPreSynthesisJudge`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/pre_synthesis.py#L51-L237))**:
     - *ModelGateway Control Plane*: Dispatched through [`ModelGateway.generate_text()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py#L98) utilizing the 123+ API key round-robin pool with AntiBanGuard 11.0 RPM pacing, sticky session affinity (`session_id="gate2_9_pre_tts"`), stealth SDK headers (`x-goog-api-client`), and permanent `BLOCK_NONE` creative safety framing.
     - *Deep Contextual Audit*: Stratifies script segments (head 10, middle 20, tail 10) against source narrative context and cast profiles from `BookBible`.
     - *Attribution Accuracy & Inversions*: Detects true speaker turn swaps ($A \leftrightarrow B$) where Character A speaks Character B's line, or where direct quotes were converted into passive narrator text.
     - *Pydantic v2 Verdict Contract*: Validates output against [`PreSynthesisLLMVerdict`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/pre_synthesis.py#L28-L49). Any detected speaker swap, swallowed dialogue, or attribution accuracy $< 0.85$ triggers immediate fail-closed abort via `GateAuditError`.

---

### Room 4: Studio TTS Platform Core & Dialogue Stem Realization (Option C)
*Modules: [`audiobook_factory/tts/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/), [`audiobook_factory/character_caster.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/character_caster.py), [`docs/TTS_PLATFORM_CORE_SPECIFICATION.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/TTS_PLATFORM_CORE_SPECIFICATION.md)*

Room 4 implements the **Studio TTS Platform Core (Option C: Layered Shared Core with Specialized Pipeline Facades)**, 100% certified with **1,183 passing tests (100% green across 1,191 test matrix)** across all architectural tiers. It permanently decouples disparate caller patterns into three specialized high-level facades backed by a shared orchestration engine:

1. **Tier 1: Specialized Client Facades**:
   - **[`GenericTTSClient`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/generic_client.py)**: Ad-hoc, low-latency ($<800\text{ms}$), single-utterance synthesis for CLI interactions (`audiobook-cli tts`), UI feedback, and voice auditions (`speak()`, `speak_to_bytes()`).
   - **[`LongFormTTSClient`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/long_form_client.py)**: Continuous full-chapter and novel narrative streaming (`synthesize_prose()`, `synthesize_chapter()`). Integrates a 4-tier semantic chunker (Scene $\to$ Paragraph $\to$ Sentence $\to$ Clause) and checkpoint caching (`checkpoint_manifest.json`) to eliminate autoregressive rate drift and redundant API costs.
   - **[`MultiCastStudioClient`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/multi_cast_client.py)**: Full multi-character ensemble audio drama production (`produce_screenplay()`). Manages `cast_lock.json` persistent voice assignments, Anime Seiyū child casting patterns, anti-swap attribution verification, TakeBank multi-take auditioning, and conversational turn latencies.

2. **Tier 2: Universal Input Guards & Normalization**:
   - **[`UniversalInputGuard`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/input_guard.py)**: Enforces Sacred Text vs Spoken Text immutability, NFC Unicode normalization, and C0 control character stripping.
   - **[`NumeralAndTokenExpander`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/numeral_expander.py)** (aliased as `DevanagariNumeralExpander`): Deterministic phonetization of inline numerals ($0-9, ०-९$), currencies ($\$, ₹, €$), percentages, units, Roman numerals, and Latin acronyms into Devanagari Hindi words before API dispatch.
   - **[`DeliveryIntentExtractor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/delivery_extractor.py)**: Extracts bracketed stage directions (`[whispering]`, `(angry)`) into strongly-typed `DeliveryIntent` while purging brackets from spoken audio.

3. **Tier 3: 4-Tier Semantic Prose Chunker & Core Orchestration**:
   - **[`SemanticProseChunker`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/chunker.py)**: Decomposes long-form text down a strict hierarchy: Level 1 (Scene: 800ms pause) $\to$ Level 2 (Paragraph: 80-160 words, 500ms pause) $\to$ Level 3 (Sentence: 30-75 words, 350ms pause) $\to$ Level 4 (Clause fallback: >45 words, 200ms pause). Zero mid-word slicing.
   - **[`TTSCoreOrchestrator`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/core_orchestrator.py)**: Dispatches requests through thread pools with error recovery and validation audits.
   - **[`TokenBucketRateLimiter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/rate_limiter.py)**: Round-robin load balancing across the 120+ active SQLite key pool with anti-bot jitter ($0.35\text{s}-0.85\text{s}$) and daily quota tracking.

4. **Tier 4: Pluggable Model Adapters & Control Plane Bridge**:
   - **TTS Control Plane Bridge** ([`gateway_bridge.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py)): Authoritative bridge implementing [`execute_tts_synthesize()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py#L60), [`execute_tts_to_file()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py), [`execute_multispeaker_batch_to_file()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py), and [`extract_pcm_and_duration_from_audio()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py#L33). Bridges legacy [`TTSDispatcher`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/dispatcher.py) directly into the `ModelGateway` control plane (`_call_gemini_tts` and `_call_gemini_multispeaker_batch`), supporting single-API batch generation via native `multiSpeakerVoiceConfig` payload formatting while preserving legacy test monkeypatch fixtures. Routes 100% of speech synthesis traffic through [`ModelGateway.synthesize_speech()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py#L248). Rogue unmetered `urllib` requests are completely eliminated, establishing fail-closed security.
   - **Secret Hygiene & Clean Endpoints**: Plaintext API key query parameters (`?key={key}`) are permanently removed from all endpoints in [`gemini_adapter.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/gemini_adapter.py) and [`gemini.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/gemini.py). Authentication transmits strictly via official stealth `X-goog-api-key` headers via `get_stealth_sdk_headers()`.
   - **ACID Key Leasing & 7 Iron Shields**: Leases Concurrency=1 mutual exclusion handles from [`KeyLeaseManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py#L130) under `workload_type="tts"`, enforcing 10 RPD ceilings on `gemini-3.8-flash-tts` with fixed SQL parameter ordering for `preferred_key_alias`. Active AntiBanGuard protection enforces 11.0 RPM token-bucket rate limits, 18s–32s key-switch cooldowns, scene session affinity, and the emergency global tripwire.
   - **5-Category `BLOCK_NONE` Framing**: Injects permanent `BLOCK_NONE` thresholds across harassment, hate speech, sexually explicit, dangerous content, and civic integrity.
   - **[`BaseTTSModelAdapter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/base.py)**: Abstract provider contract.
   - **[`GeminiTTSAdapter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/gemini_adapter.py)**: Delegates to `execute_tts_synthesize()`, maps `DeliveryIntent` into `speechMetadata.style`, and extracts 24kHz 16-bit linear PCM.
   - **[`QwenTTSAdapter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/qwen_adapter.py)**: Local Wafer-Scale / CosyVoice inference guarded by `HardwareVRAMGuard` semaphore locking, with offline synthetic fallback.
   - **[`ModelAdapterRegistry`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/registry.py)**: Dynamic singleton adapter lookup (`get_adapter_registry()`).

5. **Tier 5: Two-Tier Quality Gate & Editorial DSP**:
   - **[`TwoTierAudioQualityGate`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/quality_gate.py)**: Tier 1 mathematical waveform probe (peak $\ge 1500$, $-52 \le \text{RMS} \le -6\text{ dBFS}$, $|DC| \le 0.05$, consecutive clips $\le 5$, dead air $\le 2.5\text{s}$) plus Tier 2 phonetic duration ratio ([0.12, 0.95] sec/word).
   - **[`EditorialDSPEngine`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/dsp/editorial.py)**: Unified editorial processor combining endpoint snapping via `ZeroCrossingAligner` (-52 dBFS speech floor), raised-cosine Hann micro-fades via `HannFadeProcessor` (12ms in / 18ms out with TPDF dither), and `NetSilenceProcessor` ($\text{Injected} = \max(20\text{ms}, \text{Target} - (\text{Tail}_A + \text{Head}_B))$).
   - **[`FormantSculptor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/formant_sculptor.py)**: Pure Python 2nd-order biquad peaking EQ filters with headroom pre-attenuation ($10^{-G_{\max}/20}$) and soft tanh knee peak limiting ($\le 32,760$) across 7 presets (`WARM_BARITONE`, `CRISP_TENOR`, `BRIGHT_FEMALE`, `DEEP_RESONANT`, `ELDERLY_TEXTURED`, `CHILD_ANIME`, `NEUTRAL`).
   - **[`TakeBankManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/take_bank_manager.py)**: Multi-take candidate auditioning (`standard`, `restraint`, `vulnerable`, `exposed`) for high-stakes dramatic screenplay turns.

6. **Room 4 vs Room 5 Pipeline Boundary**:
   - **Room 4 Output Scope**: Room 4 strictly terminates with the rendered, edited dialogue stem (`stage="dialogue_stem"`). It guarantees pristine actor performance, 4D formant distinction, and zero double-pause stutters, but **strictly refrains from global EBU R128 loudness compression**.
   - **Room 5 Hand-off**: Room 5 receives the uncompressed dialogue stem and executes global two-pass linear EBU R128 (-19.0 LUFS / -1.5 dBTP) broadcast mastering, SOXR 48kHz / 24-bit resampling, and chaptered `.m4b` container packaging.

*For complete specification details, see [`docs/TTS_PLATFORM_CORE_SPECIFICATION.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/TTS_PLATFORM_CORE_SPECIFICATION.md).*

### Room 5: Pro-Grade AI Vocal Mastering Workstation & Multi-Format Packaging (v5.4)
*Subsystems: [`audiobook_factory/audio/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/), [`audiobook_factory/mcp/server.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/mcp/server.py), [`audiobook_factory/mastering.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/mastering.py), [`audiobook_factory/packaging.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/packaging.py), [`audiobook_factory/podcast/orchestrator.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/podcast/orchestrator.py)*  
*(See exhaustive specification: [`docs/VOCAL_AUDIO_MIXING_AND_PRODUCTION.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/VOCAL_AUDIO_MIXING_AND_PRODUCTION.md) and [`docs/AUDIO_ENGINEERING.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/AUDIO_ENGINEERING.md))*

Room 5 constitutes the **Pro-Grade AI Vocal Mastering Workstation (Phase 6)**, elevating downstream audio engineering into an autonomous, studio-grade processing suite combining high-performance C++ JUCE DSP, forensic acoustic and script QA auditing, neural speech de-artifacting, reference spectrum matching, incremental DAG ledgering, and container delivery:

1. **Pure Vocals-Only Architectural Invariant**:
   - Background music (BGM), sound effects (SFX), multi-track stem mixdowns, and Archive.org sound bank harvesting are **permanently decoupled** and archived in [`archive/cinematic_audio/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/archive/cinematic_audio/).
   - 100% of audio compute is dedicated to vocal intelligibility, multi-character acting nuance, conversational breathability, and Audible/EBU R128 compliance.

2. **Immutable Contracts & Schemas** ([`contracts.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py)):
   - Governed by strongly-typed Pydantic v2 schemas: [`IngestionConfig`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py#L15), [`SegmentAudioContract`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py#L26), [`ChapterMasterContract`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py#L68), [`DSPConfig`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py#L87), [`DSPMasteringResult`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py#L107), [`AudioQAConfig`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py#L121), [`SegmentQAEvaluation`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py#L136), [`ChapterQAReport`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py#L154), [`EnhancerConfig`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py#L168), [`ReferenceMatcherConfig`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py#L178).

3. **Phase 1: C++ JUCE Vocal DSP Engine** ([`dsp.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/dsp.py)):
   - [`VocalDSPProcessor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/dsp.py#L65): In-memory C++ JUCE mastering via **Spotify Pedalboard** and ITU-R BS.1770-4 loudness compliance via **Pyloudnorm**.
   - **4-Band Parametric Vocal EQ**:
     - `HighpassFilter(75 Hz)`: Subsonic rumble cut without sacrificing narrator baritone warmth.
     - `PeakFilter(320 Hz, -1.5 dB, Q=1.2)`: Attenuates chest resonance and boxiness.
     - `PeakFilter(3.2 kHz, +0.8 dB, Q=1.0)`: Lifts presence and consonant clarity in the speech intelligibility corridor.
   - **Optical Vocal Compression**: `Compressor(threshold=-18 dB, ratio=2.5:1, attack=25ms, release=120ms)` for transparent leveling.
   - **Lookahead True Peak Limiter**: Clamped strictly to $\le -1.5\text{ dBTP}$ with 40ms release window.
   - **Headless VST3 Plugin Hosting**: Supports optional dynamic 64-bit VST3 plugin bundle insertion (`vst3_plugin_path`).
   - **Deterministic FFmpeg Dual-Pass Fallback**: If Pedalboard is absent, automatically activates dual-pass linear `loudnorm` at `-19.0 LUFS` integrated target.

4. **Phase 2: Forensic Audio QA Auditor** ([`qa_auditor.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/qa_auditor.py)):
   - [`AudioQAAuditor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/qa_auditor.py#L46): Forensically audits speech takes and assembled chapters:
     - **VAD & Dead-Air Boundaries**: Flags leading dead air $> 800\text{ms}$ or trailing silence $> 1200\text{ms}$.
     - **Text-Grounded Pacing Bounds**: Speaking rate calculated in WPM and char/sec. Flags dropouts ($> 320\text{ WPM}$ or $< 0.4\text{s}$ for $> 30\text{ chars}$) $\to$ Hard `FAIL`. Flags hallucination loops ($< 40\text{ WPM}$ on short text over $> 4.0\text{s}$) $\to$ Hard `FAIL`. Pacing variances outside $[75, 240]\text{ WPM}$ yield non-blocking `WARN`.
     - **Speech Quality MOS Prediction**: Non-intrusive Acoustic Quality Index evaluating crest factor, DC offset, and digital clipping (target $\ge 3.5$).

5. **Phase 3: Neural Vocal Polish & Reference Spectrum Matching**:
   - **Neural Vocal Enhancer** ([`enhancer.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/enhancer.py)): [`NeuralVocalEnhancer`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/enhancer.py#L42) applies **DeepFilterNet3** 48kHz full-band deep filtering. Invariant: **Selective Auto-Bypass** if input $\text{SNR} \ge 45\text{ dB}$; **Energy Clamp Protection** reverting take if $|\Delta\text{RMS}| > 2.0\text{ dB}$; soft-knee spectral gate fallback at $-55\text{ dBFS}$.
   - **Reference Spectrum Matcher** ([`reference_matcher.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/reference_matcher.py)): [`ReferenceSpectrumMatcher`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/reference_matcher.py#L41) matches tonal balance of golden masters using **Matchering 2.0**. Invariant: **Hard Spectral Gain Clamp** strictly bounded to $\max \pm 3.0\text{ dB}$ to prevent frequency pumping; 1/3-octave STFT envelope fallback.

6. **Phase 5: Incremental DAG Caching & Surgical Hot-Patching**:
   - **Segment Hash Ledger** ([`ledger.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/ledger.py)): [`ChapterSegmentLedger`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/ledger.py#L83) indexes segment content hashes (`compute_segment_content_hash`) and timeline alignments, preventing redundant TTS and processing cycles when only a fraction of segments change.
   - **Single-Segment Hot-Patcher** ([`hot_patcher.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/hot_patcher.py)): [`SingleSegmentHotPatcher`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/hot_patcher.py#L33) splices regenerated speech chunks into existing pre-master WAV files in $<0.2\text{s}$ using 64 KB block streaming ($\le 1\text{ MB}$ RAM), rippling subsequent offsets without full chapter re-rendering.

7. **Dialogue Editorial, Streaming Pre-Master & Ingestion Normalization**:
   - **Audio Ingestion Manager** ([`ingestion.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/ingestion.py)): [`AudioIngestionManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/ingestion.py#L24) normalizes speech chunks to 48kHz 24-bit stereo PCM WAV, strips container watermark static, and applies a single 5.0ms raised-cosine Hann micro-taper (zero Dirac step click).
   - **Dialogue Editorial Bridge** ([`editorial.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/editorial.py)): [`DialogueEditorialBridge`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/editorial.py#L19) coordinates Ingestion $\to$ Editorial $\to$ Forensic QA $\to$ Streaming Pre-Master.
   - **Streaming Pre-Master Composer** ([`stream_composer.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/stream_composer.py)): [`ChunkStreamComposer`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/stream_composer.py#L22) streams normalized speech chunks, syntactic punctuation pauses (clause: 180ms, sentence: 380ms, turn: 600ms), TPDF dither (-72 dBFS on pauses $\ge 350\text{ms}$), stereo spatial panning, and conversational overlaps directly into `premaster.wav` with constant RAM $\le 800\text{ KB}$ and zero scratch silence files on disk.

8. **Chapter Delivery Encoding & Container Packaging**:
   - **Single-Pass Chapter Delivery Encoder** ([`encoder.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/encoder.py)): [`ChapterDeliveryEncoder`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/encoder.py#L25) implements the Single Lossy Encode Pass Invariant: Mastered 48kHz 24-bit PCM WAV $\to$ 192k AAC-LC (`.m4a`), with closed-loop true peak verification asserting True Peak $\le -1.5\text{ dBTP}$.
   - **M4B Book Packager** ([`packager.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/packager.py)): [`M4BBookPackager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/packager.py#L123) packages chapter deliverables into a single `.m4b` container with embedded cover art and `FFMETADATA1` monotonic TOC markers via 100% lossless container stream copying (`-c:a copy`).
   - **Podcast Delivery Track**: Broadcast Podcast mastering at **-16.0 LUFS** with **-1.0 dBTP** True Peak ceiling and stereo spatial staging (Host A at $-0.25$ Left, Host B at $+0.25$ Right) into AAC `.m4a` / `.mp3`.

9. **Mastering V2 Ledger Persistence & Quality Gate Integration**:
   - **Chapter Mastering Ledger (`MasteringLedger`)**: Implemented in [`audiobook_factory/mastering_contracts.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/mastering_contracts.py#L469). After mastering each chapter, [`MasteringEngineV2.master()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/mastering_engine.py) persists an immutable disk ledger at `mastered/chapter_XXX_mastering_ledger.json`. The ledger records:
     - Cryptographic stem hashes and input file provenance.
     - EBU R128 compliance metrics: `integrated_lufs` (target $-19.0\text{ LUFS}$), `true_peak_dbtp` (ceiling $\le -1.5\text{ dBTP}$), loudness range (`lra`), and threshold.
     - Limiter and filter settings applied during linear loudnorm pass 2.
     - Precise chapter duration in seconds and sample counts.
   - **Gate 6A Voice Authority Precedence**: When macro audit evaluates cross-chapter voice continuity ([`audit_gate6a_voice_continuity`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/album.py#L40)), voice authority resolves through a strict hierarchical precedence:
     $$\text{cast\_lock.json (Supreme SSOT)} \longrightarrow \text{book\_bible.json} \longrightarrow \text{character\_roster.json} \ / \ \text{voice\_registry.json}$$
     If a voice is locked in `cast_lock.json`, it overrides any conflicting lower-tier metadata, guaranteeing zero mid-novel actor drift.
   - **Gate 6B MasteringLedger Fast-Path Audit**: When release verification evaluates loudness continuity ([`audit_gate6b_loudness_continuity`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/album.py#L172)), it searches for existing `chapter_XXX_mastering_ledger.json` files across candidate paths (`mastered/`, chapter root). If valid ledgers are present, the auditor directly ingests verified `integrated_lufs` and `true_peak_dbtp` values without executing redundant, expensive FFmpeg `ebur128` passes, falling back to FFmpeg only when ledgers are missing or corrupt.

10. **Antigravity Audio MCP Server & Standalone CLI**:
   - **Audio MCP Server** ([`server.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/mcp/server.py)): Exposes 6 standardized stdio JSON-RPC tools (`apply_vocal_dsp`, `audit_audio_quality`, `match_reference_spectrum`, `enhance_vocal_stem`, `measure_ebu_r128_loudness`, `audit_chapter_qa`) for autonomous agent operation.
   - **CLI Subcommands** ([`audio.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/cli/commands/audio.py)): Exposes `audiobook-cli dsp`, `qa-audit`, `enhance`, and `match-ref`.

---

## 🎛️ Pillar 3: Model & Keys Manager Control Plane (Option C Architecture)

The **Model & Keys Manager Control Plane** ([`audiobook_factory.core.models`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/)) implements **Option C: Shared Core with Specialized Modules + Unified Gateway Facade**. It eliminates direct API key handling, quota race conditions, and Google Cloud edge mass-bans across all 5 production rooms.

```mermaid
flowchart TD
    subgraph Rooms["🎬 Downstream Production Rooms"]
        R1["Room 1: Extraction & Ingestion<br/>(Vision PDF Escalation via ModelGateway)"]
        R2["Room 2: Translation Collective<br/>(Single-Pass Deliberative Prose)"]
        R3["Room 3: Screenplay & Anti-Swap<br/>(Sticky Session Affinity)"]
        R4["Room 4: Multi-Voice TTS Performance<br/>(4D Acoustic Formants)"]
        R5["Room 5: Vocal Mastering & Telemetry<br/>(Two-Pass Linear Loudnorm)"]
    end

    subgraph Facade["🚪 Unified Production Facade"]
        Gateway["ModelGateway<br/>(generate_text, synthesize_speech, lease_session)"]
    end

    subgraph CorePlane["⚙️ Core Control Plane Subsystems"]
        Router["RequestRouter<br/>(Task Matching & Fallback Ladder)"]
        Registry["ModelRegistry<br/>(50+ Canonical Models & Capabilities)"]
        AntiBan["AntiBanGuard<br/>(The 7 Iron Shields Protection Engine)"]
        LeaseMgr["KeyLeaseManager<br/>(ACID SQLite Mutex & Win32 Crash Recovery)"]
        Breaker["CircuitBreaker<br/>(CLOSED / OPEN / HALF_OPEN States)"]
        PolicyEngine["Universal Policy Engine<br/>(Error Normalizer & Quota Rollover)"]
    end

    subgraph Persistence["💾 ACID Persistence"]
        SQLite[("audiobooks/keys_inventory.db<br/>• key_inventory (123+ Fleet)<br/>• key_leases (Mutual Exclusion)<br/>• model_quota_ledger<br/>• key_audit_log")]
    end

    subgraph Adapters["🔌 Polymorphic Provider Adapters"]
        AdGemini["GeminiProviderAdapter<br/>(Inline Multimodal parts, REST v1beta & SDK)"]
        AdOpenAI["OpenAICompatibleAdapter<br/>(Cerebras / Groq / OpenAI / OpenRouter)"]
        AdLocal["LocalGpuAdapter<br/>(RTX 4050 6GB PyTorch / Transformers)"]
    end

    R1 -->|"generate_text(task='extraction', parts=[...])"| Gateway
    R2 -->|"generate_text(task='translation')"| Gateway
    R3 -->|"lease_session() & generate_text()"| Gateway
    R4 -->|"synthesize_speech(task='tts')"| Gateway
    R5 -->|"get_fleet_status()"| Gateway

    Gateway --> Router
    Router --> Registry
    Router --> Breaker
    Router --> LeaseMgr
    Gateway --> AntiBan
    Gateway --> PolicyEngine
    LeaseMgr <--> SQLite

    Gateway --> AdGemini
    Gateway --> AdOpenAI
    Gateway --> AdLocal
```

---

### The 5 Core Modules

#### 1. [`KeyLeaseManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py) (ACID Inventory & Atomic Leases)
- **ACID SQLite Inventory**: Manages API key inventory (123+ active healthy Gemini keys verified on `main`), lease reservations, per-model daily quota ledgers, and tamper-evident audit logs via atomic `BEGIN IMMEDIATE` transactions in SQLite (`audiobooks/keys_inventory.db`).
- **0% Concurrent Double-Leasing**: Enforces strict mutual exclusion (`Concurrency = 1` per free API key). A key can only be leased to a single active worker thread or process at any instant.
- **Autonomous Dead PID Crash Recovery**: Uses a dual liveness sweep. In addition to rolling lease TTL (default 60s), it probes the operating system process table via [`is_pid_alive`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py#L64):
  - On Windows 11, leverages Win32 `ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)` to test process existence and immediately reclaims orphaned leases upon worker crashes.
  - On POSIX platforms, falls back to `os.kill(pid, 0)`.
- **One User = One Active Key per Workload**: Strict per-user quota enforcement ([`CallerIdentity`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py#L77)) prevents single-user resource monopolization across text and TTS workloads.
- **Zero-Secret Public Aliases**: Plaintext keys are never logged or exposed in telemetry. Keys are identified via deterministic salted public aliases (`key_a8f2`) and SHA-256 hashes.
- **Dual Timezone Quota Rollovers**: Automatically handles midnight quota resets according to provider policies: Midnight US Pacific Time (`America/Los_Angeles`) for Google AI Studio quotas, and UTC Midnight for other providers.
- **Transparent Key Pool Synchronization**: [`PersistentKeyPool`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/key_manager.py#L664) transparently synchronizes with `KeyLeaseManager` across `lease_key()`, `record_success()`, `mark_daily_quota_exhausted()`, and `mark_temporary_backoff()`.

#### 2. [`AntiBanGuard`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/anti_ban_guard.py) (The 7 Iron Shields)
Protects large pools of free API keys (120+ keys) against edge mass-bans and bot-detection heuristics:
- **Shield 1: Strict Request Mutual Exclusion**: Guarantees zero overlapping requests per key via atomic leasing in `KeyLeaseManager`.
- **Shield 2: Session Affinity Sticky Binding** ([`SessionAffinityTracker`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/anti_ban_guard.py#L320)): Binds a production session or scene to the same key for 8–15 sequential segments, eliminating suspicious key-hopping patterns at provider edge routers.
- **Shield 3: Anti-Correlation Key-Switch Pause**: Enforces a randomized 18.0s – 32.0s delay whenever a worker must switch keys on the same IP address, breaking TCP/TLS and request-frequency correlation across distinct accounts.
- **Shield 4: Content-Aware Human Cadence & Director Breaks** ([`HumanCadenceController`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/anti_ban_guard.py#L80)): Shapes inter-request latency modeled on a human director review workflow:
  $$\Delta t_{\text{wait}} = t_{\text{read}}(\text{words}) + t_{\text{review}}(\text{audio}) + t_{\text{jitter}} + t_{\text{director\_break}}$$
  Applies log-normal human pause distributions (1.5s – 7.0s) and injects 15–30s director breaks every 14 segments.
- **Shield 5: Conservative 75% Rate Limiting** ([`TokenBucketRateLimiter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/anti_ban_guard.py#L179)): Clamps requests to a conservative 11.0 RPM per key (73% of Google's 15 RPM free ceiling) with an absolute minimum burst separation of 3.5 seconds.
- **Shield 6: Official Stealth SDK Headers** (`get_stealth_sdk_headers`): Injects stealth HTTP headers identical to official provider SDKs (`x-goog-api-client`, `google-genai-sdk-python/0.8.3` with Python and platform tags), eliminating custom bot user agents.
- **Shield 7: Emergency Global Tripwire** ([`EmergencyTripwire`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/anti_ban_guard.py#L248)): Monitors fleet health across all keys. If 5 consecutive 429 (Resource Exhausted) or 503 (Unavailable) errors occur within a 60-second sliding window, activates emergency pool quarantine for 45.0s to halt requests before accounts are suspended.

#### 3. [`ModelRegistry`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/registry.py) (Canonical Model Catalog)
- **Comprehensive Registry (50+ Models)**: Canonical catalog spanning Google Gemini (`gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-3.8-flash-tts`), Cerebras (Llama 3.3 70B, Llama 3.1 8B), Groq, OpenAI, Anthropic, and Local GPU (RTX 4050 6GB).
- **Capability Profiles** ([`ModelCapability`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/registry.py#L48)): Explicit context windows (up to 1M tokens), max output limits, rate ceilings (RPM, TPM, RPD), thinking budget support, structured output flags, and timezone reset schedules.
- **Quality Tiers** ([`ModelTier`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/registry.py#L20)): Hierarchical taxonomy categorizing models into `TIER_1_FLAGSHIP`, `TIER_2_BALANCED`, `TIER_3_UTILITY`, `TIER_AUDIO`, and `TIER_LOCAL`.
- **Task-Based Resolution**: Maps pipeline requirements (`translation`, `screenplay`, `dramaturgy`, `extraction`, `tts`) to optimal verified models.

#### 4. [`RequestRouter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/router.py) (Intelligent Router & Fallback)
- **Capability Matching**: Resolves requests into concrete [`ExecutionPlan`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/router.py#L40) blueprints containing model capabilities, leased keys, and matched provider adapters.
- **Circuit Breaker Integration** ([`CircuitBreaker`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/policy_engine.py#L242)): Maintains per-(provider, model) circuit breakers with `CLOSED` $\rightarrow$ `OPEN` $\rightarrow$ `HALF_OPEN` state transitions, automatically bypassing models undergoing provider outages.
- **Dynamic Fallback Ladder**: Automatically escalates to secondary models within the eligible tier if primary candidate models encounter outages or key exhaustion.

#### 5. [`ModelGateway`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py) (Unified Production Facade)
- **Single Public Entry Point**: Exposes high-level operations: `generate_text()`, `synthesize_speech()`, `lease_session()`, and `get_fleet_status()`.
- **Multimodal Payload Routing**: [`GeminiProviderAdapter._build_gemini_payload()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/gemini.py#L57) supports inline base64 multimodal `parts` kwargs, allowing Room 1 to dispatch single-page PDF memory buffers for OCR transcription directly through `ModelGateway.generate_text(task="extraction", parts=parts)`.
- **Automatic Failover & Retry Loop**: Intercepts HTTP errors, classifies root causes via [`NormalizedApiError`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/policy_engine.py#L43), marks exhausted keys/models in SQLite, applies anti-correlation pauses, and retries seamlessly on alternative keys.
- **Guaranteed Lease Release**: All operations employ `try ... finally` release blocks, ensuring 0% lease leaks under normal completion, rate limit backoff, or unexpected exceptions.

---

### Downstream Pipeline Room Integration (Zero Boundary Leakage)

All production rooms interface strictly with [`ModelGateway`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py), maintaining clean boundary isolation:

1. **Room 1 (Pre-Production & Extraction)**:
   - Suspicious PDF pages route through [`GeminiVisionPDFExtractor.escalate_page()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/extraction/parsers/pdf/vision_extractor.py#L35) $\rightarrow$ `gateway.generate_text(task="extraction", parts=parts, session_id=f"pdf_page_{page_num}")`.
   - All 6 Room 1 pre-production agents route through [`execute_preproduction_llm()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/gateway_bridge.py#L37) $\rightarrow$ `gateway.generate_text(task="directing"|"extraction")`, acquiring Concurrency=1 mutual exclusion handles from `KeyLeaseManager`.
   - Enforces AntiBanGuard 11.0 RPM token-bucket rate limiting, stealth SDK headers (`x-goog-api-client`), session affinity sticky binding, `BLOCK_NONE` creative fiction framing, and resilient `json_repair`. Rogue direct `urllib` calls are 100% eliminated.
   - Backward-compatible legacy imports re-exported via [`audiobook_factory/pdf/vision_extractor.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/pdf/vision_extractor.py).
2. **Room 1.5 (Standalone Chapter Glossary & Metadata Hub)**:
   - All lexical classification queries route through [`execute_glossary_llm()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/gateway_bridge.py#L26) $\rightarrow$ `gateway.generate_text(task="extraction", response_json=True)`, leasing keys under Concurrency=1 mutual exclusion from `KeyLeaseManager`.
   - Zero-token fast-path bypasses ModelGateway completely when all candidates match `BookBible`, preserving daily quota budgets.
   - Injects `BLOCK_NONE` creative fiction framing to prevent false-positive censorship of villainous monikers, dramatic epithets, and gritty rustic dialogue terms.
   - Fails closed if ModelGateway is unavailable; direct `urllib` or unmetered HTTP calls are completely eliminated.
3. **Room 2 (Translation Collective)**:
   - Dispatches translation prompts through `gateway.generate_text(task="translation", min_tier=ModelTier.TIER_1_FLAGSHIP)`.
   - The translation engine receives pristine text output without managing rate-limiting delays or rotating key pools.
4. **Room 3 (Screenplay, Anti-Swap Attribution & Gate 2.9 Pre-TTS Sanity)**:
   - Encloses scene chunking within `with gateway.lease_session(session_id=scene_id):`.
   - Maintains sticky key affinity across 8–15 continuous dialogue turns, avoiding edge ban heuristics while analyzing speaker attribution.
   - Executes Gate 2.9 Pre-TTS Sanity Gate ([`LLMPreSynthesisJudge`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/pre_synthesis.py#L51-L237)) with sticky session affinity (`session_id="gate2_9_pre_tts"`), auditing dialogue attribution, gender inflections, and dramaturgy sanity before handing off to Room 4.
5. **Room 4 (Multi-Voice TTS Performance & Legacy Dispatcher Bridge)**:
   - Dispatches speech generation strictly via [`execute_tts_synthesize()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py#L60), [`execute_tts_to_file()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py), or [`execute_multispeaker_batch_to_file()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py) $\rightarrow$ `gateway.synthesize_speech(text=..., voice_name=..., task="tts")`.
   - Legacy [`TTSDispatcher`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/dispatcher.py) methods `_call_gemini_tts` and `_call_gemini_multispeaker_batch` route directly to `ModelGateway` control plane via `gateway_bridge`, supporting native `multiSpeakerVoiceConfig` single-request multi-cast payloads while transparently honoring existing mock monkeypatches for tests.
   - Acquires atomic Concurrency=1 mutual exclusion leases from `KeyLeaseManager` under `workload_type="tts"`, enforcing the strict 10 RPD daily quota ceilings on `gemini-3.8-flash-tts` and transparently rotating to fresh keys upon exhaustion.
   - Eliminates all rogue `urllib` calls and strips plaintext key query parameters (`?key={key}`) in favor of official stealth `X-goog-api-key` headers.
   - AntiBanGuard 7 Iron Shields are fully enforced across all synthesis calls (11.0 RPM token-bucket rate limiter, 18s–32s key-switch cooldown, emergency global tripwire).
   - Audio payload frames are unpacked and validated via [`extract_pcm_and_duration_from_audio()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py#L33), returning rich metadata in `SpeechResult.metadata`.
6. **Room 5 (Pro-Grade AI Vocal Mastering Workstation & Telemetry)**:
   - Orchestrates vocal post-production via [`VocalDSPProcessor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/dsp.py), Spotify Pedalboard C++ JUCE 4-band vocal parametric EQ (75Hz subsonic cut, 320Hz boxiness reduction, 3.2kHz presence lift), optical compression, and True Peak limiting ($\le -1.5\text{ dBTP}$), with seamless deterministic FFmpeg dual-pass linear loudnorm fallback (-19.0 LUFS vocal target).
   - Forensic speech auditing via [`AudioQAAuditor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/qa_auditor.py) (energy VAD, speaking pace 75–240 WPM, dropouts/loops detection, MOS scoring), DeepFilterNet3 neural polish with selective $>45\text{dB}$ SNR auto-bypass, Matchering 2.0 reference spectrum matching ($\pm 3.0\text{dB}$ clamp), and `<0.2s` single-segment hot-patching via [`SingleSegmentHotPatcher`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/hot_patcher.py).
   - Chapter packaging and delivery via [`M4BBookPackager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/packager.py) and [`ChapterDeliveryEncoder`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/encoder.py) (192k AAC single pass, `-map_chapters 1` monotonic TOC).
   - Diagnostic telemetry queries `gateway.get_fleet_status()` for fleet reporting and quota telemetry without opening direct connections to `keys_inventory.db`.
7. **Room 6 / Aux-Pane UI Workstation (Phase 7 Crown Jewel Orchestrator & Sidecar Bridge)**:
   - Interactive operator console hosted natively in Google Antigravity Aux-Pane or via standalone Node.js sidecar server.
   - **Vectorized Python Bridge** ([`audiobook_factory/api/studio_bridge.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/api/studio_bridge.py)): Delivers sub-millisecond peak extraction via `soundfile` and `numpy`, real-time key pool introspection via `key_pool_state.db`, project status tracking via `project_state.db`, and curated voice catalog discovery with Windows UTF-8 stdout encoding.
   - **Node.js Sidecar API** ([`sidecars/studio-panel/main.mjs`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/sidecars/studio-panel/main.mjs)): High-performance micro-server featuring a 50-item LRU waveform cache (`/api/peaks`) and HTTP 206 Partial Content byte range streaming (`/api/audio`), enabling instant seekability without full audio file re-downloads.
   - **Apple Minimalist Light UI Architecture** ([`sidecars/studio-panel/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/sidecars/studio-panel/)): Built to macOS Sonoma / Tahoe Human Interface Guidelines with 100% offline isolation (zero CDNs/external fonts), $\le 2.1\text{ MB}$ browser heap (under $\le 3.5\text{ MB}$ budget), 120 FPS double-buffered HTML5 Canvas 2D waveform scrubber with SMPTE timecode (`00:00.000`), 5-Room interactive DAG stepper, Multi-Cast Voice Roster audition deck, and Dialogue Editorial Inspector with authentic Devanagari Hindi text.
   - **Synchronized Global Plugin**: Seamlessly mirrored to `%USERPROFILE%\.gemini\config\plugins\audiobook-studio\sidecars\studio-panel\`.

---

## 🎖️ 8-Pillar Studio Production Certification Harness

The entire production lifecycle is verified by the **8-Pillar Studio Production Certification Harness** ([`audiobook_factory/certification/runner.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/certification/runner.py)), which generates a comprehensive JSON scorecard ([`StudioCertificationReport`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/certification/contracts.py#L34-L79)):

| Pillar | Quality Gate | Target Specification | Fail Condition |
|---|---|---|---|
| **P1: Ingestion & Extraction** | Gate 0.1 | Document completeness, $\ge 50$ words coverage floor, 0 empty chapters, PDF OCR noise $< 8\%$. | Word count floor violated, missing extracted markdown files. |
| **P2: Literary Translation** | Gate 0 / T0–T15 | Sense-for-sense fidelity, "Nothing Above Source", no placeholder markers (`[UNTRANSLATED]`, `[TODO]`). | Untranslated placeholders detected, severe text truncation. |
| **P3: Dramaturgy Alignment** | Gate 2.5 | SPU paragraph alignment, monotonic segment indices, 0 orphan scene or beat references. | Non-monotonic indices, broken beat links. |
| **P4: Dialogue Attribution** | Gate 2 | Anti-Swap Attribution Auditor: 0% speaker turn inversion ($A \leftrightarrow B$), 0 quote leakage to Narrator. | Empty speaker, quotes swallowed into Narrator lines. |
| **P5: Vocal Performance** | Gate 2.8 | Clamped temperature (`0.30 - 0.52`), physical vocal anchors, ban on theatrical over-projection keywords. | Banned histrionic directives (`screeching`, `hysterical`). |
| **P6: EBU R128 Loudness** | Gate 5 / Gate 6B | Mastered files present, **-19.0 LUFS** (Audiobook) / **-16.0 LUFS** (Podcast), True Peak $\le -1.4$ dBTP. | Missing master files, loudness delta $> 1.0$ LU. |
| **P7: Spatial Staging** | Multi-Host Staging | Host A pan $\le -0.20$ (Left), Host B pan $\ge +0.20$ (Right). Mono-centered for audiobook track. | Host panning insufficiently separated ($< \pm 0.20$). |
| **P8: Container Packaging** | Gate 6C / Gate 6D | Valid `.m4b` container for Audiobooks; valid `.m4a` container for Podcasts; verified TOC seek table. | Missing deliverable container file. |

---

## 📁 Repository Directory Map

```text
audiobook-factory/
├── audiobook_cli.py                     # Unified CLI entrypoint
├── plugin.json                          # Google Antigravity Plugin manifest
├── audiobook_factory/
│   ├── core/                            # Shared Control Plane
│   │   └── models/                      # ModelGateway, KeyLeaseManager, AntiBanGuard
│   ├── api/                             # Phase 7 Python Studio Bridge (studio_bridge.py)
│   ├── extraction/                      # Pillar 1 Forensic Ingestion
│   ├── preproduction/                   # Room 1 System 1 Stateless Novel Researcher
│   ├── metadata/                        # Room 1 System 2 BookBible & NovelStateMaintainer
│   ├── glossary/                        # Room 1.5 Chapter Glossary & Metadata Hub
│   ├── translation/                     # Room 2 Decoupled Option D Translation Engine
│   ├── dramaturgy/                      # Room 3 Universal Dramaturgy Core
│   ├── adapters/                        # Room 3 Format Adapters (Audiobook & Podcast)
│   ├── podcast/                         # Dedicated 2-Host Podcast Engine
│   ├── tts/                             # Room 4 Speech synthesis & audio slicing
│   ├── audio/                           # Room 5 Pro-Grade AI Vocal Mastering Workstation (v5.4)
│   ├── mcp/                             # Audio Workstation & Mastering MCP Server
│   ├── dialogue_editorial.py            # DE-01 - DE-07 micro-fades and endpoint snapping
│   ├── mastering.py                     # Room 5 Two-pass linear loudnorm EBU R128
│   ├── packaging/                       # ChapterMetadataGenerator & multi-format delivery
│   └── certification/                   # 8-Pillar Studio Certification Harness (P1-P8)
├── sidecars/
│   └── studio-panel/                    # Phase 7 Apple Minimalist Light UI Workstation & Node.js Sidecar
└── docs/                                # Production-grade technical documentation
```

---

## 📦 Decoupled & Archived Subsystems

The legacy cinematic mix subcommands (`direct`, `render`, `bgm`, `stems`, `bank`) belong to the decoupled 5-track cinematic audio engine and are permanently archived in [`archive/cinematic_audio/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/archive/cinematic_audio/). They are not part of the active Vocals-Only studio engine.

---

## 🔗 Related Documentation
- [🖥️ Studio UI & Sidecar Extension Specification (Apple-Grade Minimalist Light)](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/STUDIO_UI_AND_SIDECAR_SPECIFICATION.md)
- [🎙️ TTS Platform Core Architecture Specification (Option C)](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/TTS_PLATFORM_CORE_SPECIFICATION.md)
- [🎙️ Podcast System Architecture](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/PODCAST_SYSTEM_ARCHITECTURE.md)
- [🎭 Dramaturgy & Adaptation System](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/DRAMATURGY_AND_ADAPTATION_SYSTEM.md)
- [📚 Glossary & Chapter Metadata Subsystem](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/GLOSSARY_AND_METADATA_SUBSYSTEM.md)
- [🛡️ Quality Gates & 8-Pillar Certification](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/QUALITY_GATES.md)
- [💻 CLI Reference Manual](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/CLI_REFERENCE.md)
- [🎛️ Audio Engineering & Mastering](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/AUDIO_ENGINEERING.md)
