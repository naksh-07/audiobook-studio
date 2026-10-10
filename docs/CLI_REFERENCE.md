# 💻 CLI Reference: Audiobook Studio & Multi-Format Engine

**Version:** 5.2 (Option C Standard v2.0 Compliant)  
**Entrypoints:** `audiobook-cli` | `audiobook-studio` | `python audiobook_cli.py`  
**Source File:** [`audiobook_cli.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_cli.py)

---

## Overview

The Audiobook Studio Command-Line Interface provides granular, deterministic control over the entire pure vocals-only production pipeline under **Option C Architecture**. It supports 1-click autonomous multi-format generation (`auto`), dedicated 2-host narrative podcast production (`podcast`), specialized script adaptation (`script --adapter`), dual-track packaging (`package --format`), and the **8-Pillar Studio Production Certification Harness** (`audit-book` / `audit --certify`).

```bash
# Entrypoint via installed CLI command or direct Python execution:
audiobook-cli [COMMAND] [OPTIONS]
# or:
python audiobook_cli.py [COMMAND] [OPTIONS]
```

---

## 🧭 Active Production Command Matrix

| Subcommand | Scope | Output Track | Description |
|---|---|---|---|
| **[`auto`](#1-autonomous-multi-format-production-auto)** | Full Book | `audiobook` / `podcast` / `both` | 1-Click end-to-end pipeline from source document to certified deliverables. |
| **[`podcast`](#2-dedicated-2-host-podcast-engine-podcast)** | Chapter / Paper | `podcast` | Dedicated 2-host conversational podcast generator, synthesizer & mastering engine (supports book chapters and technical papers). |
| **[`script`](#3-screenplay--adaptation-scripting-script)** | Screenplay | `audiobook` / `podcast` | Generates screenplay scripts using `audiobook` or `podcast` format adapters. |
| **[`package`](#4-multi-format-container-packaging-package)** | Delivery | `audiobook` / `podcast` / `both` | Assembles final deliverables: chapterized `.m4b` audiobook, `.m4a` podcast episodes, or both. |
| **[`audit-book`](#5-full-book-macro-audit--8-pillar-certification-audit-book)** | QA (Macro) | Master Release | Executes Gate 6 master audit and the complete **8-Pillar Studio Production Certification Scorecard**. |
| **[`audit`](#6-chapter-quality-audit-audit)** | QA (Chapter) | Chapter | Executes Multi-Gate Independent Verification (Gates 0, 1, 2, 2.5, 2.8, 5) on a single chapter. |
| **[`produce`](#7-chapter-vocal-production-produce)** | Chapter / All | `audiobook` | Produces mastered vocal chapters with EBU R128 (-19 LUFS) and timeline ledger. |
| **[`extract`](#8-universal-document-extraction-extract)** | Ingestion | Markdown | Ingests EPUB, PDF, TXT, or MD documents into clean Markdown chapters. |
| **[`translate`](#9-literary-translation-translate)** | Translation | Hindustani | Translates extracted chapters using the Option D Standalone Translation Engine. |
| **[`synthesize`](#10-speech-synthesis-synthesize)** | Audio (TTS) | WAV Chunks | Synthesizes dialogue segments via Gemini Flash TTS with 4D formants. |
| **[`master`](#11-vocal-dsp-mastering-master)** | Mastering | Master WAV | Concatenates segments with Hann micro-fades and normalizes to broadcast EBU R128. |
| **[`keys`](#12-key-inventory--fleet-monitor-keys)** | Control Plane | Fleet Status | Inspects key fleet status, active leases (`Concurrency = 1`), audit logs, and resets quotas. |
| **[`tts`](#13-ad-hoc-speech-synthesis-tts)** | Utterance / Audition | `output.wav` | Ad-hoc speech synthesis via modular TTS Platform Core ([`GenericTTSClient`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/generic_client.py)). |
| **[`dsp`](#15-vocal-dsp-mastering-dsp)** | Standalone Audio | Mastered WAV | Applies C++ JUCE parametric vocal EQ, optical compression, and True-Peak limiting ($\le -1.5\text{ dBTP}$). |
| **[`qa-audit`](#16-forensic-speech-qa-audit-qa-audit)** | QA (Speech) | JSON Telemetry | Forensically audits speech segment for VAD, speaking pace (75-240 WPM), dropouts, loops, and MOS. |
| **[`enhance`](#17-neural-vocal-polish-enhance)** | Polish / Denoise | Cleaned WAV | DeepFilterNet3 neural speech polish with $>45\text{dB}$ SNR auto-bypass. |
| **[`match-ref`](#18-reference-spectrum-matching-match-ref)** | Spectral Match | Matched WAV | Matchering 2.0 reference spectrum matching with $\pm 3.0\text{dB}$ hard clamping. |
| **[`podcast-cli`](#14-modular-podcast-subsystem-cli)** | Modular Engine | Subsystem | Dedicated CLI for granular podcast workflows (`produce`, `script`, `render`, `inspect`). |

---

## 1. Autonomous Multi-Format Production (`auto`)

Executes the complete pipeline autonomously from raw document ingestion through multi-format packaging and certification.

```bash
audiobook-cli auto <FILE> [OPTIONS]
```

### Positional Arguments
- `FILE`: Path to source document (`.epub`, `.pdf`, `.txt`, `.md`).

### Options
| Option | Type | Default | Description |
|---|:---:|:---:|---|
| `--format` | Choice | `audiobook` | Target delivery format: `audiobook`, `podcast`, or `both`. |
| `--hindi` | Flag | `False` | Translate English source text to literary Hindustani. |
| `--backend` | Choice | `gemini_tts` | Speech synthesis engine backend (`gemini_tts`). |
| `--voice` | String | `Aoede` | Lead voice persona (`Aoede`, `Puck`, `Charon`, `Fenrir`, `Zephyr`, `Kore`). |
| `--dramatized` | Flag | `False` | Multi-voice character casting vs single narrator reading. |
| `--cast-mode` | Choice | `ensemble` | Voice casting model: `ensemble` (multi-cast) or `solo` (master narrator). |
| `--flow` | Flag | `True` | Enable Audible Flow mode (preserves prose and tags, eliminates Foley). |
| `--cover` | Path | `None` | Path to square cover artwork image (min $1400 \times 1400$ px). |
| `--workers` | Integer | `3` | Number of concurrent TTS synthesis worker threads. |
| `--force-gate` | Flag | `False` | Bypass Ingestion Quality Gate REVIEW failure and force production. |
| `--chapter` | Integer | `None` | Restrict autonomous production to a specific single chapter. |
| `--chapters` | String | `None` | Comma-separated or range of chapters to produce (e.g. `1-3` or `1,4`). |

### Examples
```bash
# 1. Produce Audible-standard Hindi audiobook (.m4b)
audiobook-cli auto "books/novel.epub" --hindi --dramatized --voice Aoede --format audiobook

# 2. Produce 2-Host Hindi narrative podcast series (.m4a)
audiobook-cli auto "books/novel.epub" --hindi --format podcast --workers 4

# 3. Produce BOTH formats in a single unified run
audiobook-cli auto "books/novel.epub" --hindi --dramatized --format both --cover "cover.jpg"
```

---

## 2. Dedicated 2-Host Podcast Engine (`podcast`)

Controls the dedicated conversational podcast adaptation, verbalization, and mastering engine ([`audiobook_factory/podcast/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/podcast/)). Supports both **narrative novel chapters** and **academic research papers / whitepapers** (LaTeX formulas and Markdown tables).

```bash
audiobook-cli podcast <TARGET> [OPTIONS]
# or:
python audiobook_cli.py podcast <TARGET> [OPTIONS]
```

### Positional Arguments
- `TARGET`: Project folder slug under `audiobooks/projects/` (for book chapters) **OR** path to input technical document (`.pdf`, `.md`, `.txt`, `.epub`).

### Options
| Option | Type | Default | Description |
|---|:---:|:---:|---|
| `--produce` | Flag | `False` | Synthesize audio and master to broadcast podcast standard. |
| `--hindi` | Flag | `True` | Generate Hindustani podcast (Sameer & Priya personas). |
| `--english` | Flag | `False` | Generate English podcast (Alex & Maya personas). |
| `--chapter` | Integer | `None` | Specific chapter number to adapt (narrative mode). |
| `--chapters` | String | `None` | Comma-separated or range of chapters (e.g. `1-3`). |
| `--host-a-name` | String | `Dr. Vance` | Host A name (`Dr. Vance` / `Sameer`). |
| `--host-a-voice` | String | `Charon` | Gemini Flash TTS voice for Host A (`Charon`, `Puck`, `Fenrir`). |
| `--host-b-name` | String | `Maya` | Host B name (`Maya` / `Priya`). |
| `--host-b-voice` | String | `Aoede` | Gemini Flash TTS voice for Host B (`Aoede`, `Kore`, `Leda`). |
| `--workers` | Integer | `3` | Concurrent TTS synthesis worker threads. |
| `--target-lufs` | Float | `-16.0` | Target broadcast integrated loudness (EBU R128 podcast target). |
| `--mock` | Flag | `False` | Run with offline/synthetic audio (zero API quota consumed). |
| `--script-only` | Flag | `False` | Generate `podcast_script.json` without executing audio synthesis. |
| `--force-gate` | Flag | `False` | Bypass Ingestion Quality Gate REVIEW failure. |
| `--overwrite` | Flag | `False` | Overwrite existing podcast scripts and plans on disk. |

### Examples

#### Novel Narrative Chapter Podcast
```bash
# Draft conversational 2-Host script for Chapter 1
audiobook-cli podcast my_project --chapter 1 --hindi

# Full end-to-end podcast production: Draft -> TTS -> Stereo Staging -> -16.0 LUFS Master
audiobook-cli podcast my_project --chapter 1 --produce --workers 3 --target-lufs -16.0
```

#### Research Paper & Whitepaper Verbalization
```bash
# Full end-to-end production from scientific PDF:
python audiobook_cli.py podcast "papers/attention_mechanism.pdf" --produce

# Offline mock audio dry-run (zero quota consumed):
python audiobook_cli.py podcast "papers/rlhf_survey.pdf" --mock
```

---

## 3. Screenplay & Adaptation Scripting (`script`)

Translates chapter source text and the unified `DramaticPlan` into format-specific screenplay JSON using Option C adapters.

```bash
audiobook-cli script <BOOK_SLUG> [OPTIONS]
```

### Options
| Option | Type | Default | Description |
|---|:---:|:---:|---|
| `--adapter` | Choice | `audiobook` | Format script adapter: `audiobook` (Audible Flow) or `podcast` (2-Host). |
| `--hindi` | Flag | `False` | Use translated Hindi chapters from `translation/`. |
| `--dramatized` | Flag | `False` | Multi-voice character attribution mode. |
| `--flow` | Flag | `True` | Enforce Audible Flow standard (em-dash lead-ins, unbroken turns). |
| `--cast-mode` | Choice | `ensemble` | `ensemble` (multi-voice cast) or `solo` (master narrator). |
| `--chapter` | Integer | `None` | Specific chapter number to script. |
| `--chapters` | String | `None` | Comma-separated or range of chapters (e.g. `1-2`). |
| `--overwrite` | Flag | `False` | Overwrite existing screenplay script files. |

### Examples
```bash
# Script using AudiobookAdapter (Audible Flow Standard)
audiobook-cli script my_project --hindi --dramatized --adapter audiobook

# Script using PodcastAdapter (2-Host Spoken Breathability)
audiobook-cli script my_project --hindi --adapter podcast
```

---

## 4. Multi-Format Container Packaging (`package`)

Packages mastered audio into release-ready containers with embedded metadata, chapter atoms, and artwork.

```bash
audiobook-cli package <BOOK_SLUG> [OPTIONS]
```

### Options
| Option | Type | Default | Description |
|---|:---:|:---:|---|
| `--format` | Choice | `audiobook` | Target delivery format: `audiobook` (.m4b), `podcast` (.m4a), or `both`. |
| `--cover` | Path | `None` | Cover artwork image path (JPEG/PNG, min $1400 \times 1400$ px). |
| `--enforce-gate6` | Flag | `False` | Abort packaging immediately if any Gate 6 check fails. |

### Examples
```bash
# Package Audiobook M4B deliverable
audiobook-cli package my_project --format audiobook --cover "cover.jpg" --enforce-gate6

# Package Podcast M4A episodes
audiobook-cli package my_project --format podcast

# Package BOTH formats simultaneously
audiobook-cli package my_project --format both --cover "cover.jpg"
```

---

## 5. Full-Book Macro Audit & 8-Pillar Certification (`audit-book`)

Executes Macro-Tier Gate 6 master audits and the complete **8-Pillar Studio Production Certification Scorecard** ([`StudioCertificationRunner`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/certification/runner.py)).

```bash
audiobook-cli audit-book <PROJECT_DIR_OR_SLUG>
```

### Certification Scorecard Output
```text
=================================================================
📘 MACRO BOOK GATE 6 VERDICT: PASSED
=================================================================
  Gate 6A (Voice Continuity):    PASSED
  Gate 6B (Loudness Continuity): PASSED (avg -19.0 LUFS)
  Gate 6C (TOC Integrity):       PASSED (12 chapters)
  Gate 6D (Packaging Specs):     PASSED

=================================================================
🎖️  8-PILLAR STUDIO PRODUCTION CERTIFICATION SCORECARD
=================================================================
  ✅ Extraction & Provenance (Gate 0.1)                 [100.0% | PASSED]
  ✅ Literary Translation Dual-Rule (Gate 0)           [100.0% | PASSED]
  ✅ Dramaturgy SPU & Beat Alignment (Gate 2.5)         [100.0% | PASSED]
  ✅ Anti-Swap Speaker Attribution (0% Inversion)       [100.0% | PASSED]
  ✅ Vocal Performance Clamping (0.30 - 0.52 Temp)      [100.0% | PASSED]
  ✅ EBU R128 Loudness Compliance (-19.0 / -16.0 LUFS)  [100.0% | PASSED]
  ✅ 2-Host Spatial Staging (-0.25 / +0.25 Azimuth)     [100.0% | PASSED]
  ✅ Container Chapter Atoms & Show Notes (M4B / M4A)   [100.0% | PASSED]
-----------------------------------------------------------------
  OVERALL SCORE: 100.0%  |  VERDICT: 🏆 CERTIFIED
=================================================================
```

---

## 6. Chapter Quality Audit (`audit`)

Runs granular multi-gate verification on a specific chapter before full master packaging:

```bash
audiobook-cli audit <BOOK_SLUG> --chapter <NUM>
```

### Evaluated Gates:
- **Gate 0 (Translation)**: Word count sanity, terminology variants, negation integrity.
- **Gate 1 (Voice Roster)**: Zero voice collisions, acoustic gender alignment.
- **Gate 2 (Screenplay)**: Pydantic v2 schema compliance, prosody tags ($\ge 60\%$), anti-swallow guard.
- **Gate 3 (Scenes Source)**: Act structure and scene segment continuity.
- **Gate 4.5 (Timeline)**: Speech transcript preservation, silence percentage.
- **Gate 5 (Broadcast Master)**: EBU R128 loudness probe (target $-19.0 \pm 1.0$ LUFS, ceiling $-1.4$ dBTP).

---

## 7. Chapter Vocal Production (`produce`)

Synthesizes, edits, and masters a single chapter with timeline ledger logging.

```bash
audiobook-cli produce <BOOK_SLUG> [OPTIONS]
```

### Options
| Option | Type | Default | Description |
|---|:---:|:---:|---|
| `--chapter` | Integer | `None` | Specific chapter number to produce. |
| `--all` | Flag | `False` | Produce all chapters sequentially. |
| `--voice` | String | `Aoede` | Lead voice persona. |
| `--workers` | Integer | `3` | Concurrent TTS synthesis worker threads. |
| `--clean-dsp` | Flag | `True` | Clean studio vocal DSP without pitch shifting. |

---

## 8. Universal Document Extraction (`extract`)

Ingests any digital book or research paper into a structured Canonical AST ([`CanonicalBook`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/extraction/contracts.py#L231)), creates the sacred bit-accurate source archive (`raw/`), runs Gate 0.1 quality audit, and projects clean, segmented Markdown chapters for downstream rooms.

```bash
python audiobook_cli.py extract <FILE> [OPTIONS]
# or:
audiobook-cli extract <FILE> [OPTIONS]
```

### Positional Arguments
- `FILE`: Path to input document (`.epub`, `.pdf`, `.txt`, `.md`).

### Options
| Flag | Type | Default | Description |
|---|:---:|:---:|---|
| `--force-gate` | Flag | `False` | Force bypass of Extraction Quality Gate (Gate 0.1) fail-closed `REVIEW` abort (e.g. for low-word test samples). |

### Output Artifacts
Extraction establishes the project workspace under `audiobooks/projects/<BOOK_SLUG>/`:
```text
audiobooks/projects/<BOOK_SLUG>/
├── raw/                      # Sacred unmutated archive (source_original.ext, source_manifest.json)
├── canonical/                # Strongly-typed Pydantic v2 AST (book.json, quality_report.json)
└── extracted/                # Backward-compatible Markdown chapters (chapter_001.md, ...)
```

### Hybrid 3-Tier PDF Engine & Multimodal Escalation
For `.pdf` files, extraction utilizes a zero-bloat 3-tier hybrid pipeline without requiring 15GB local PyTorch weights:
1. **Tier 1 (Fast Geometric Local Analysis)**: Geometric XY-cut multi-column slicing (`PDFLayoutReconstructor`) and mathematical operator preservation (`PDFQualityAnalyzer`).
2. **Tier 2 (Selective Multimodal Vision Escalation)**: Suspicious, scanned, or multi-column equation pages escalate via [`GeminiVisionPDFExtractor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/extraction/parsers/pdf/vision_extractor.py), routing single-page memory slices directly through [`ModelGateway.generate_text()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py#L48) with atomic key leasing, session affinity, and official stealth SDK headers.
3. **Tier 3 (Canonical Assembly & Gate 0.1)**: Assembles the audited AST and validates word count floors, empty chapter immunity, and noise thresholds.

### Examples
```bash
# Ingest novel EPUB into canonical AST and extracted chapters:
python audiobook_cli.py extract "C:/Books/The_Last_Wish.epub"

# Ingest scientific research paper PDF:
python audiobook_cli.py extract "papers/attention_mechanism.pdf"

# Ingest test sample with gate bypass:
python audiobook_cli.py extract "tests/fixtures/sample_short.pdf" --force-gate
```

---

## 9. Literary Translation (`translate`)

Translates extracted chapters into literary dramatic Hindustani using the Option D Standalone Translation Engine (single generative pass with `thinking_budget = 1024`, macro-chunking, and deterministic parity verification, with 4-Agent Collective fallback).

### Audiobook Studio Pipeline (Room 2)
```bash
audiobook-cli translate <BOOK_SLUG> [OPTIONS]
```

### Options
- `--model`: Translation LLM model (default: `gemini-3.8-flash`).
- `--chapter`: Specific chapter number to translate.
- `--chapters`: Comma-separated or range of chapters (e.g. `1-3`).
- `--force-gate`: Bypasses Gate T0–T15 scene certification failure.

### Standalone Decoupled CLI (Independent Subsystem)
The translation engine can also be executed completely independently from the audiobook pipeline for standalone books, documents, or scripts:
```bash
python -m audiobook_factory.translation.cli translate input_chapter.txt -o output_hindi.md --tier RAW_UNRATED
```

---

## 10. Speech Synthesis (`synthesize`)

Synthesizes screenplay dialogue segments using Google Gemini Flash Cloud TTS and 4D acoustic formants.

```bash
audiobook-cli synthesize <BOOK_SLUG> [OPTIONS]
```

### Options
- `--chapter`: Specific chapter number to synthesize.
- `--chapters`: Comma-separated or range of chapters.
- `--voice`: Default narrator voice persona (default: `Aoede`).
- `--backend`: Speech synthesis engine (default: `gemini_tts`).

---

## 11. Vocal DSP Mastering (`master`)

Concatenates speech segments with Hann micro-fades and normalizes audio to EBU R128 broadcast standards.

```bash
audiobook-cli master <BOOK_SLUG> [OPTIONS]
```

### Options
- `--chapter`: Specific chapter number to master.
- `--chapters`: Comma-separated or range of chapters.

---

## 📦 Decoupled & Archived Commands

The legacy cinematic mix subcommands (`direct`, `render`, `bgm`, `stems`, `bank`) belong to the decoupled 5-track cinematic audio engine and are permanently archived in [`archive/cinematic_audio/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/archive/cinematic_audio/). They are not part of the active Vocals-Only studio engine.

---



## 12. Key Inventory & Fleet Monitor (`keys`)

Inspects and manages the ACID SQLite API key inventory (`audiobooks/keys_inventory.db`), active multi-user concurrency leases (`Concurrency = 1`), tamper-evident audit logs, and provider quota states.

```bash
python audiobook_cli.py keys [ACTION] [OPTIONS]
```

### Positional Action Arguments
- `ACTION`: Choice of action:
  - `status`: Displays live fleet summary, active leases, and registered keys table (default).
  - `list`: Lists registered keys with public aliases, health status, and daily calls.
  - `add`: Registers a new API key into the SQLite inventory ledger (requires `--key`).
  - `sweep`: Reclaims expired TTL leases and orphaned dead-PID process locks (Win32 / POSIX).
  - `test`: Probes key fleet health and active traffic capacity.
  - `audit`: Displays recent tamper-evident audit log events.
  - `reset`: Forces an administrative reset of keys and models back to `ACTIVE` state.

### Options
| Flag | Type | Default | Description |
|---|:---:|:---:|---|
| `--provider` | String | `gemini` | Target provider filter (`gemini`, `cerebras`, `groq`, `openai`, `openrouter`). |
| `--limit` | Integer | `25` | Number of recent audit log events to display (used with `audit`). |
| `--key` | String | `None` | API key string to register (used with `add`). |

---

### Subcommands & Usage

#### A. Fleet Telemetry & Quota Status (`keys status`)
Displays live inventory health, daily quota consumption breakdown, active leases, and circuit breaker status.

```bash
python audiobook_cli.py keys status --provider gemini
```

**Output Telemetry Structure:**
```text
======================================================================
  AUDIOBOOK FACTORY - KEY INVENTORY & FLEET STATUS (GEMINI)
======================================================================
  Date (Quota Period)   : 2026-10-10
  Total Registered Keys : 123
  Active Healthy Keys   : 123
  Exhausted Today       : 0
  Temporary Backoff     : 0
  In-Flight Leases      : 1
----------------------------------------------------------------------

  ACTIVE LEASES (IN-FLIGHT CONCURRENCY):
  LEASE ID             ALIAS        USER           WORKLOAD   EXPIRES
  ------------------------------------------------------------------
  e8f20b31-4c12-...    key_a8f2     naksh-07       text       2026-10-10T00:32:15

  KEY INVENTORY DETAILS:
  ALIAS          STATUS           CALLS TODAY    LAST USED
  ------------------------------------------------------------------
  key_a8f2       ACTIVE           14 ok / 0 fail 2026-10-10T00:31:15
  key_b4c9       ACTIVE           10 ok / 0 fail 2026-10-10T00:28:40
  key_c1d7       ACTIVE           5 ok / 0 fail  2026-10-10T00:30:02
======================================================================
```

#### B. Key Listing (`keys list`)
Outputs a clean inventory list of all registered keys with safe, zero-secret public aliases (`key_XXXX`), current operational status, and daily request metrics:

```bash
python audiobook_cli.py keys list --provider gemini
```

**Output:**
```text
======================================================================
  AUDIOBOOK FACTORY - REGISTERED KEY INVENTORY (GEMINI)
======================================================================
  ALIAS          STATUS           CALLS TODAY    LAST USED
  ------------------------------------------------------------------
  key_a8f2       ACTIVE           14 ok / 0 fail 2026-10-10T00:31:15
  key_b4c9       ACTIVE           10 ok / 0 fail 2026-10-10T00:28:40
  key_c1d7       ACTIVE           5 ok / 0 fail  2026-10-10T00:30:02
======================================================================
```

#### C. Register New Key (`keys add`)
Registers an API key into the ACID inventory ledger without wiping existing daily quota usage:

```bash
python audiobook_cli.py keys add --provider gemini --key "AIzaSy..."
```

**Output:**
```text
[+] Success: Key registered in inventory ledger under provider 'gemini'.
```

#### D. Crash Recovery & Lease Reaping (`keys sweep`)
Manually invokes the dual liveness sweep to reclaim expired TTL leases and probe the OS process table for terminated worker processes (using Win32 `kernel32.OpenProcess` on Windows 11):

```bash
python audiobook_cli.py keys sweep
```

**Output:**
```text
[+] Sweep complete: Reclaimed 0 stale or dead-PID lease(s).
```

#### E. Fleet Health Probe (`keys test`)
Probes key fleet capacity and reports operational readiness:

```bash
python audiobook_cli.py keys test --provider gemini
```

**Output:**
```text
======================================================================
  AUDIOBOOK FACTORY - KEY FLEET HEALTH PROBE (GEMINI)
======================================================================
  Total Keys   : 123
  Active Keys  : 123
  Exhausted    : 0
  Backoff      : 0
  Probe Status : HEALTHY (123/123 keys available for traffic)
======================================================================
```

#### F. Audit Log Inspection (`keys audit`)
Inspects recent tamper-evident lease acquisition, release, and revocation events. Plaintext keys are never logged; only deterministic aliases (`key_XXXX`) and calling PIDs are exposed:

```bash
python audiobook_cli.py keys audit --limit 50
```

**Output Log Structure:**
```text
======================================================================
  AUDIOBOOK FACTORY - KEY LEASE AUDIT LOG (LAST 25 EVENTS)
======================================================================
  TIMESTAMP           EVENT    ALIAS        USER           MODEL
  ------------------------------------------------------------------
  2026-10-10 00:31:15 RELEASE  key_a8f2     naksh-07       gemini-3.8-flash
  2026-10-10 00:30:52 ACQUIRE  key_a8f2     naksh-07       gemini-3.8-flash
  2026-10-10 00:28:40 REVOKE   key_b4c9     naksh-07       gemini-3.8-flash-tts
======================================================================
```

#### G. Administrative Reset (`keys reset`)
Performs an administrative reset of all keys and per-model quota ledgers in `audiobooks/keys_inventory.db` back to `ACTIVE` state:

```bash
python audiobook_cli.py keys reset
```

**Output:**
```text
[+] Success: All keys and model quota ledgers reset to ACTIVE state for today.
```

---

## 13. Ad-Hoc Speech Synthesis (`tts`)

Synthesizes ad-hoc speech from arbitrary text or literary prompts directly via the modular **TTS Platform Core** ([`audiobook_factory.tts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/__init__.py)) using [`GenericTTSClient`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/generic_client.py).

```bash
audiobook-cli tts "<TEXT>" [OPTIONS]
# or:
python audiobook_cli.py tts "<TEXT>" [OPTIONS]
```

### Positional Arguments
- `<TEXT>`: The sentence, dialogue line, or text prompt to synthesize. Supports English prose and Devanagari Hindi text with automatic numeral, currency, and acronym expansion.

### Options
| Option | Type | Default | Description |
|---|:---:|:---:|---|
| `--voice` | String | `Puck` | Neural voice identifier (e.g. `Puck`, `Aoede`, `Charon`, `Fenrir`, `Kore`, `Zephyr`). |
| `--model` | String | `gemini-3.8-flash` | TTS model engine (e.g. `gemini-3.8-flash`, `gemini-2.5-flash`, `qwen3-tts`). |
| `--out` | Path | `output.wav` | Output destination path for the 16-bit PCM RIFF WAV audio file. |

### Technical Architecture & Behavior
1. **Universal Input Guard**: Sanitizes text through [`UniversalInputGuard`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/input_guard.py), eliminating C0 control chars, normalizing Unicode to NFC, and extracting bracketed delivery intent (`[whispering]`).
2. **Deterministic Phonetization**: Automatically converts all inline digits ($0-9, ०-९$), currencies ($\$, ₹, €$), percentages, and units into spoken Hindi words via [`NumeralAndTokenExpander`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/numeral_expander.py) (aliased as `DevanagariNumeralExpander`).
3. **Pluggable Model Dispatch**: Routes request through [`ModelAdapterRegistry`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/registry.py) to [`GeminiTTSAdapter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/gemini_adapter.py) or [`QwenTTSAdapter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/qwen_adapter.py).
4. **Two-Tier Quality Audit**: Audits synthesized waveform via [`TwoTierAudioQualityGate`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/quality_gate.py) (Peak $\ge 1500$, $-52 \le \text{RMS} \le -6\text{ dBFS}$, $|DC| \le 0.05$, zero dead air) before disk write.
5. **Ultra-Low Latency**: Delivers pristine, broadcast-ready 24kHz 16-bit linear PCM WAV output in $< 800\text{ms}$.

### Examples

```bash
# 1. Quick audition of a narrator voice in English
audiobook-cli tts "Welcome to the studio production line." --voice Puck --out welcome.wav

# 2. Devanagari Hindi text with automatic numeral and currency phonetization
audiobook-cli tts "अध्याय ५: व्यापारी ने उसे ₹५०० और $२० दिए।" --voice Aoede --model gemini-3.8-flash --out hindi_sample.wav

# 3. Dramatic character voice audition with Charon
audiobook-cli tts "मैं पीछे नहीं हटूंगा, चाहे जो भी हो जाए।" --voice Charon --out dramatic_test.wav

# 4. Custom output path with alternative model
python audiobook_cli.py tts "System diagnostics fully operational." --voice Fenrir --model gemini-2.5-flash --out tests/audio/diag.wav
```

---

## 14. Modular Podcast Subsystem CLI

For granular control over individual stages of technical document verbalization and production, use the standalone module CLI [`audiobook_factory.podcast.cli`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/podcast/cli.py):

```bash
python -m audiobook_factory.podcast.cli <SUBCOMMAND> [OPTIONS]
```

### Subcommands

#### 1. `produce`
Executes end-to-end ingestion, mathematical/table verbalization, dual-host turn allocation, multi-voice TTS synthesis, Hann micro-fades, and two-pass linear EBU R128 vocal mastering.

```bash
python -m audiobook_factory.podcast.cli produce <FILE> [OPTIONS]
```

Options:
- `<FILE>`: Path to input document (`.pdf`, `.md`, `.txt`, `.epub`).
- `--output-dir <DIR>`: Output directory.
- `--style {conversational_podcast,formal_lecture,narrative_audiobook}`: Dialogue style.
- `--host-a-name <NAME>`: Host A display name (default: `Dr. Vance`).
- `--host-a-voice <VOICE>`: Host A voice (default: `Charon`).
- `--host-b-name <NAME>`: Host B display name (default: `Maya`).
- `--host-b-voice <VOICE>`: Host B voice (default: `Aoede`).
- `--mock`: Run with synthetic sine/harmonic vocal chunks.
- `--force-gate`: Bypass Extraction Quality Gate REVIEW failure.

#### 2. `script`
Ingests document and generates structured `podcast_script.json` only.

```bash
python -m audiobook_factory.podcast.cli script <FILE> [OPTIONS]
```

Options:
- `<FILE>`: Path to input document.
- `--output-dir <DIR>`: Output directory.
- `--style <STYLE>`: Verbalization style.
- `--host-a-name <NAME>`: Host A display name.
- `--host-a-voice <VOICE>`: Host A voice persona.
- `--host-b-name <NAME>`: Host B display name.
- `--host-b-voice <VOICE>`: Host B voice persona.
- `--force-gate`: Bypass extraction gate review failure.

#### 3. `render`
Synthesizes and masters audio from an existing, user-edited `podcast_script.json` file.

```bash
python -m audiobook_factory.podcast.cli render <SCRIPT_FILE> [OPTIONS]
```

Options:
- `<SCRIPT_FILE>`: Path to `podcast_script.json`.
- `--output-dir <DIR>`: Output production directory (defaults to `<script_dir>/production`).
- `--mock`: Synthesize mock audio chunks for rapid local verification.

#### 4. `inspect`
Inspects and prints diagnostics for a `podcast_script.json` or `_production_manifest.json`.

```bash
python -m audiobook_factory.podcast.cli inspect <PATH>
```

Output includes total spoken turns, total word count, estimated runtime, cast configuration with voices and roles, or mastered audio loudness and true peak measurements.

---

## 15. Vocal DSP Mastering (`dsp`)

Applies high-performance C++ JUCE parametric vocal EQ, optical compression, and True-Peak limiting via Spotify Pedalboard and ITU-R BS.1770-4 loudness compliance. Falls back seamlessly to deterministic FFmpeg dual-pass linear mastering if Pedalboard is unavailable.

```bash
python audiobook_cli.py dsp --input <INPUT_WAV> --output <OUTPUT_WAV> [OPTIONS]
```

### Options
| Flag | Short | Type | Default | Description |
|---|:---:|:---:|:---:|---|
| `--input` | `-i` | Path | *Required* | Path to input 48kHz WAV audio file. |
| `--output` | `-o` | Path | *Required* | Target destination for mastered 48kHz 24-bit PCM WAV. |
| `--target-lufs` | | Float | `-19.0` | EBU R128 integrated loudness target in LUFS (-24.0 to -14.0). |
| `--true-peak` | | Float | `-1.5` | Lookahead True Peak limiter ceiling in dBTP (-3.0 to -0.5). |

### Output JSON Telemetry
```json
{
  "status": "SUCCESS",
  "backend_used": "pedalboard_juce_v2",
  "output_path": "C:/audiobooks/masters/chapter_001_master.wav",
  "integrated_lufs": -18.96,
  "true_peak_dbtp": -1.50,
  "loudness_range_lu": 7.42,
  "execution_duration_sec": 0.38
}
```

### Example
```bash
python audiobook_cli.py dsp -i "raw_chapter.wav" -o "mastered_chapter.wav" --target-lufs -19.0 --true-peak -1.5
```

---

## 16. Forensic Speech QA Audit (`qa-audit`)

Forensically audits a single speech audio segment or full take for Voice Activity Detection (VAD) boundaries, text-grounded speaking rate (WPM and char/sec), TTS dropouts, repetition loops, and non-intrusive Speech MOS (Mean Opinion Score).

```bash
python audiobook_cli.py qa-audit --input <INPUT_WAV> [OPTIONS]
```

### Options
| Flag | Short | Type | Default | Description |
|---|:---:|:---:|:---:|---|
| `--input` | `-i` | Path | *Required* | Path to synthesized speech WAV file. |
| `--text` | `-t` | String | `""` | Expected spoken text for script grounding and WPM calculation. |
| `--speaker` | `-s` | String | `Narrator` | Speaker character name or Narrator tag. |

### Output JSON Telemetry
```json
{
  "segment_index": 1,
  "segment_uid": "c01_s001_Aoede",
  "speaker": "Narrator",
  "status": "PASS",
  "duration_ms": 3420,
  "estimated_wpm": 142.1,
  "char_per_sec": 14.8,
  "predicted_mos": 4.65,
  "silence_leading_ms": 40,
  "silence_trailing_ms": 60,
  "issues": [],
  "remediation_advice": null
}
```

### Example
```bash
python audiobook_cli.py qa-audit -i "c01_s001.wav" -t "The old tavern was shrouded in darkness." -s "Narrator"
```

---

## 17. Neural Vocal Polish (`enhance`)

Cleans synthetic TTS metallic hash, high-frequency quantization hiss, and room tone using **DeepFilterNet3** (48kHz full-band). Employs **Selective Auto-Bypass** for pristine takes ($>45\text{ dB}$ SNR) and **Energy Difference Clamping** ($|\Delta\text{RMS}| \le 2.0\text{ dB}$) to preserve delicate consonants without robotic gating.

```bash
python audiobook_cli.py enhance --input <INPUT_WAV> --output <OUTPUT_WAV>
```

### Options
| Flag | Short | Type | Default | Description |
|---|:---:|:---:|:---:|---|
| `--input` | `-i` | Path | *Required* | Input WAV audio file. |
| `--output` | `-o` | Path | *Required* | Output enhanced 48kHz 24-bit PCM WAV. |

### Output JSON Telemetry
```json
{
  "status": "SUCCESS",
  "output_path": "cleaned_vocal.wav",
  "was_enhanced": true
}
```

### Example
```bash
python audiobook_cli.py enhance -i "grainy_take.wav" -o "cleaned_take.wav"
```

---

## 18. Reference Spectrum Matching (`match-ref`)

Transplants the frequency spectrum, tonal balance, and dynamic curve of a golden reference master (e.g. Audible bestseller master) onto target audio using **Matchering 2.0**. Enforces a **hard $\pm 3.0\text{ dB}$ clamp** on spectral correction to prevent unnatural acoustic artifacts or frequency pumping.

```bash
python audiobook_cli.py match-ref --target <TARGET_WAV> --reference <REF_WAV> --output <OUT_WAV> [OPTIONS]
```

### Options
| Flag | Short | Type | Default | Description |
|---|:---:|:---:|:---:|---|
| `--target` | `-t` | Path | *Required* | Target WAV audio file to be balanced. |
| `--reference` | `-r` | Path | *Required* | Golden reference WAV audio master. |
| `--output` | `-o` | Path | *Required* | Output matched 48kHz 24-bit PCM WAV. |
| `--max-clamp` | | Float | `3.0` | Maximum spectral EQ adjustment in dB ($\pm 0.5$ to $\pm 6.0$). |

### Output JSON Telemetry
```json
{
  "status": "SUCCESS",
  "output_path": "matched_chapter.wav",
  "max_clamp_db": 3.0
}
```

### Example
```bash
python audiobook_cli.py match-ref -t "my_chapter.wav" -r "audible_ref_master.wav" -o "final_matched.wav" --max-clamp 2.5
```

---

## 19. 📦 Archived Subsystems Notice

The legacy subcommands (`direct`, `render`, `bgm`, `stems`, `bank`) belong to the decoupled 5-track cinematic audio engine and are archived in `archive/cinematic_audio/`. They are not part of the active Vocals-Only pipeline.

---

## 🔗 Related Documentation
- [🏛️ Option C Architecture Blueprint](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/ARCHITECTURE.md)
- [🎙️ TTS Platform Core Architecture Specification](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/TTS_PLATFORM_CORE_SPECIFICATION.md)
- [🎙️ Podcast System Architecture](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/PODCAST_SYSTEM_ARCHITECTURE.md)
- [🎭 Dramaturgy & Adaptation System](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/DRAMATURGY_AND_ADAPTATION_SYSTEM.md)
- [📚 Glossary & Chapter Metadata Subsystem](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/GLOSSARY_AND_METADATA_SUBSYSTEM.md)
- [🛡️ Quality Gates & 8-Pillar Certification](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/QUALITY_GATES.md)
- [🎛️ Audio Engineering & Mastering](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/AUDIO_ENGINEERING.md)
