# 💻 CLI Reference: Audiobook Studio Engine

## Overview

The Audiobook Studio Command-Line Interface ([`audiobook_cli.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_cli.py)) provides operational control over the entire studio-grade vocal production pipeline. You can run an autonomous end-to-end novel production run with a single command or execute granular subcommands stage-by-stage.

```bash
# Entrypoint via installed CLI or Python:
audiobook-studio [COMMAND] [OPTIONS]
# or:
python audiobook_cli.py [COMMAND] [OPTIONS]
```

---

## 🧭 Active Production Command Matrix

| Subcommand | Scope | Description |
|---|---|---|
| **[`auto`](#1-autonomous-production-auto)** | Full Book | 1-Click autonomous pipeline (Extract $\rightarrow$ Translate $\rightarrow$ Script $\rightarrow$ Synth $\rightarrow$ Master $\rightarrow$ Package). |
| **[`produce`](#2-chapter-production-produce)** | Chapter / All | Produces high-fidelity vocal chapters with EBU R128 (-19 LUFS) and timeline ledger. |
| **[`extract`](#3-universal-document-extraction-extract)** | Ingestion | Ingests EPUB, PDF, TXT, or MD documents into clean Markdown chapters. |
| **[`translate`](#4-literary-translation-translate)** | Translation | Translates extracted chapters into literary dramatic Hindustani with Translation Collective. |
| **[`script`](#5-screenplay-scripting-script)** | Screenplay | Parses prose into standardized screenplay JSON with speaker attribution and acting tags. |
| **[`synthesize`](#6-speech-synthesis-synthesize)** | Audio (TTS) | Synthesizes dialogue chunks using Google Gemini Flash Cloud TTS and 4D acoustic formants. |
| **[`master`](#7-vocal-dsp-mastering-master)** | Mastering | Concatenates vocal chunks with 5-stage DSP chain and EBU R128 loudness normalization. |
| **[`package`](#8-m4b-container-packaging-package)** | Delivery | Packages all mastered chapters into a chapterized `.m4b` container with cover art. |
| **[`audit`](#9-chapter-quality-audit-audit)** | QA (Chapter) | Runs Multi-Gate Independent Verification (Gates 0, 1, 2, 2.5, 2.8) on a specific chapter. |
| **[`audit-book`](#10-full-book-macro-audit-audit-book)** | QA (Macro) | Runs Macro-Tier Gate 6 certification (Voice Continuity, Loudness, TOC Monotonicity). |
| **[`podcast`](#11-research-paper--whitepaper-podcast-podcast)** | Scientific Paper | Generates dual-host podcast audio from research papers, LaTeX formulas, and Markdown tables. |
| **[`keys`](#12-key-inventory--fleet-monitor-keys)** | Control Plane | Inspects key fleet status, active leases, audit logs, and resets quotas. |
| **[`podcast-cli`](#13-modular-podcast-subsystem-cli)** | Modular Engine | Dedicated CLI for granular podcast workflows (`produce`, `script`, `render`, `inspect`). |

---

## 1. Autonomous Production (`auto`)

Executes the entire pure vocals-only pipeline autonomously in a single command.

```bash
python audiobook_cli.py auto <FILE> [OPTIONS]
```

### Positional Arguments
- `FILE`: Path to input book file (`.epub`, `.pdf`, `.txt`, `.md`).

### Options
| Flag | Type | Default | Description |
|---|:---:|:---:|---|
| `--hindi` | Flag | `False` | Translate English source text to literary Hindustani. |
| `--backend` | Choice | `gemini_tts` | Speech synthesis backend (`gemini_tts`). |
| `--voice` | String | `Aoede` | Lead voice persona (`Aoede`, `Charon`, `Puck`, `Fenrir`, `Zephyr`, `Kore`, `Leda`, `Orpheus`). |
| `--dramatized` | Flag | `False` | Multi-voice character casting vs single narrator reading. |
| `--cover` | Path | `None` | Path to cover artwork image (JPEG/PNG, min $1400 \times 1400$ px). |
| `--workers` | Integer | `3` | Number of concurrent TTS synthesis worker threads. |
| `--force-gate` | Flag | `False` | Bypass Ingestion Quality Gate REVIEW warning and force production. |

### Example
```bash
python audiobook_cli.py auto "C:/path/to/novel.epub" --hindi --dramatized --voice Aoede --workers 3
```

---

## 2. Chapter Production (`produce`)

Produces mastered vocal chapters with EBU R128 (-19 LUFS) and timeline ledgers.

```bash
python audiobook_cli.py produce <BOOK_SLUG> [OPTIONS]
```

### Positional Arguments
- `BOOK_SLUG`: Project folder slug under `audiobooks/projects/`.

### Options
| Flag | Type | Default | Description |
|---|:---:|:---:|---|
| `--chapter` | Integer | `None` | Specific chapter number to produce (e.g. `--chapter 1`). |
| `--all` | Flag | `False` | Produce all chapters in sequence. |
| `--voice` | String | `Aoede` | Lead narrator voice persona. |
| `--workers` | Integer | `3` | Number of concurrent TTS synthesis worker threads. |

---

## 3. Universal Document Extraction (`extract`)

Ingests any digital book or research paper into a structured Canonical AST ([`CanonicalBook`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/extraction/contracts.py#L231)), creates the sacred bit-accurate source archive (`raw/`), runs Gate 0.1 quality audit, and projects clean, segmented Markdown chapters for downstream rooms.

```bash
python audiobook_cli.py extract <FILE> [OPTIONS]
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

## 4. Literary Translation (`translate`)

Translates extracted chapters into literary dramatic Hindustani using the Option D Standalone Translation Engine (single generative pass with `thinking_budget = 1024`, macro-chunking, and deterministic parity verification).

### Audiobook Studio Pipeline (Room 2)
```bash
python audiobook_cli.py translate <BOOK_SLUG> [--model <MODEL>]
```

### Standalone Decoupled CLI (Independent Subsystem)
The translation engine can also be executed completely independently from the audiobook pipeline for standalone books, documents, or scripts:
```bash
python -m audiobook_factory.translation.cli translate input_chapter.txt -o output_hindi.md --tier RAW_UNRATED
```

---

## 5. Screenplay Scripting (`script`)

Parses chapter prose into standardized screenplay JSON with speaker attribution, 4D formant metadata, and Stanislavski acting cues.

```bash
python audiobook_cli.py script <BOOK_SLUG> [--hindi] [--dramatized]
```

---

## 6. Speech Synthesis (`synthesize`)

Synthesizes dialogue segments via Google Gemini Flash TTS with 4D acoustic formant modulation.

```bash
python audiobook_cli.py synthesize <BOOK_SLUG> [--voice <VOICE>] [--backend gemini_tts]
```

---

## 7. Vocal DSP Mastering (`master`)

Concatenates speech segments with Hann micro-fades and normalizes to EBU R128 (-19 LUFS) at 48kHz / 24-bit.

```bash
python audiobook_cli.py master <BOOK_SLUG>
```

---

## 8. M4B Container Packaging (`package`)

Assembles all mastered chapters into a final chapterized `.m4b` container with TOC navigation and embedded cover art.

```bash
python audiobook_cli.py package <BOOK_SLUG> [--cover <IMAGE_PATH>] [--enforce-gate6]
```

---

## 9. Chapter Quality Audit (`audit`)

Executes Multi-Gate Independent Verification on a single chapter.

```bash
python audiobook_cli.py audit <BOOK_SLUG> --chapter <NUM>
```

---

## 10. Full-Book Macro Audit (`audit-book`)

Executes Macro-Tier Gate 6 certification across the entire novel project.

```bash
python audiobook_cli.py audit-book <PROJECT_DIR_OR_SLUG>
```

---

## 11. Research Paper & Whitepaper Podcast (`podcast`)

Ingests any scientific research paper (arXiv), technical whitepaper, financial report, or markdown document with complex tables and LaTeX formulas, generating an engaging NotebookLM-style dual-host podcast mastered to broadcast EBU R128 (-19.0 LUFS / -1.5 dBTP).

```bash
python audiobook_cli.py podcast <FILE> [OPTIONS]
```

### Positional Arguments
- `FILE`: Path to input research paper or technical document (`.pdf`, `.md`, `.txt`, `.epub`).

### Options
| Flag | Type | Default | Description |
|---|:---:|:---:|---|
| `--output-dir` | Path | `None` | Custom target project output directory. Defaults to `audiobooks/projects/<slug>_podcast/`. |
| `--style` | Choice | `conversational_podcast` | Spoken verbalization delivery style (`conversational_podcast`, `formal_lecture`, `narrative_audiobook`). |
| `--host-a-name` | String | `Dr. Vance` | Name of the Lead Explainer host persona. |
| `--host-a-voice` | String | `Charon` | Gemini Flash TTS voice for Host A (`Charon`, `Fenrir`, `Puck`, `Zephyr`, `Orpheus`). |
| `--host-b-name` | String | `Maya` | Name of the Inquisitive Co-host persona. |
| `--host-b-voice` | String | `Aoede` | Gemini Flash TTS voice for Host B (`Aoede`, `Kore`, `Leda`). |
| `--mock` | Flag | `False` | Run in offline/synthetic audio chunk mode (zero Gemini API quota consumed). Ideal for CI and quick testing. |
| `--script-only` | Flag | `False` | Ingests the document and generates `podcast_script.json` without executing audio synthesis. |
| `--force-gate` | Flag | `False` | Force bypass of Extraction Quality Gate REVIEW failure. |

### Examples

#### Full End-to-End Production
```bash
python audiobook_cli.py podcast "papers/attention_mechanism.pdf"
```

#### Custom Host Personas & Voices
```bash
python audiobook_cli.py podcast "papers/qwen2_vl.pdf" \
  --host-a-name "Professor Vance" --host-a-voice Charon \
  --host-b-name "Elena" --host-b-voice Aoede \
  --output-dir "audiobooks/projects/qwen2_podcast"
```

#### Offline Dry-Run (Zero API Quota)
```bash
python audiobook_cli.py podcast "benchmarks/sample_research_paper.md" --mock
```

#### Script-Only Inspection
```bash
python audiobook_cli.py podcast "papers/rlhf_survey.pdf" --script-only
```

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

## 13. Modular Podcast Subsystem CLI

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

## 14. 📦 Archived Subsystems Notice

The legacy subcommands (`direct`, `render`, `bgm`, `stems`, `bank`) belong to the decoupled 5-track cinematic audio engine and are archived in `archive/cinematic_audio/`. They are not part of the active Vocals-Only pipeline.

