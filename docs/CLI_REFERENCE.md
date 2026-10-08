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
| **[`podcast`](#2-dedicated-2-host-podcast-engine-podcast)** | Chapter / All | `podcast` | Dedicated 2-host conversational podcast generator, synthesizer & mastering engine. |
| **[`script`](#3-screenplay--adaptation-scripting-script)** | Screenplay | `audiobook` / `podcast` | Generates screenplay scripts using `audiobook` or `podcast` format adapters. |
| **[`package`](#4-multi-format-container-packaging-package)** | Delivery | `audiobook` / `podcast` / `both` | Assembles final deliverables: chapterized `.m4b` audiobook, `.m4a` podcast episodes, or both. |
| **[`audit-book`](#5-full-book-macro-audit--8-pillar-certification-audit-book)** | QA (Macro) | Master Release | Executes Gate 6 master audit and the complete **8-Pillar Studio Production Certification Scorecard**. |
| **[`audit`](#6-chapter-quality-audit-audit)** | QA (Chapter) | Chapter | Executes Multi-Gate Independent Verification (Gates 0, 1, 2, 3, 4.5, 5) on a single chapter. |
| **[`produce`](#7-chapter-vocal-production-produce)** | Chapter / All | `audiobook` | Produces mastered vocal chapters with EBU R128 (-19 LUFS) and timeline ledger. |
| **[`extract`](#8-universal-document-extraction-extract)** | Ingestion | Markdown | Ingests EPUB, PDF, TXT, or MD documents into clean Markdown chapters. |
| **[`translate`](#9-literary-translation-translate)** | Translation | Hindustani | Translates extracted chapters using the 4-Agent Translation Collective. |
| **[`synthesize`](#10-speech-synthesis-synthesize)** | Audio (TTS) | WAV Chunks | Synthesizes dialogue segments via Gemini Flash TTS with 4D formants. |
| **[`master`](#11-vocal-dsp-mastering-master)** | Mastering | Master WAV | Concatenates segments with Hann micro-fades and normalizes to broadcast EBU R128. |

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

Controls the dedicated conversational podcast adaptation and mastering engine ([`audiobook_factory/podcast/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/podcast/)).

```bash
audiobook-cli podcast <BOOK_SLUG> [OPTIONS]
```

### Positional Arguments
- `BOOK_SLUG`: Project folder slug under `audiobooks/projects/`.

### Options
| Option | Type | Default | Description |
|---|:---:|:---:|---|
| `--produce` | Flag | `False` | Synthesize audio and master to broadcast podcast standard. |
| `--hindi` | Flag | `True` | Generate Hindustani podcast (Sameer & Priya personas). |
| `--english` | Flag | `False` | Generate English podcast (Alex & Maya personas). |
| `--chapter` | Integer | `None` | Specific chapter number to adapt. |
| `--chapters` | String | `None` | Comma-separated or range of chapters (e.g. `1-3`). |
| `--workers` | Integer | `3` | Concurrent TTS synthesis worker threads. |
| `--target-lufs` | Float | `-16.0` | Target broadcast integrated loudness (EBU R128 podcast target). |
| `--overwrite` | Flag | `False` | Overwrite existing podcast scripts and plans on disk. |

### Examples
```bash
# Draft conversational 2-Host script for Chapter 1
audiobook-cli podcast my_project --chapter 1 --hindi

# Full end-to-end podcast production: Draft -> TTS -> Stereo Staging -> -16.0 LUFS Master
audiobook-cli podcast my_project --chapter 1 --produce --workers 3 --target-lufs -16.0
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

Ingests any digital book into clean, segmented Markdown chapters.

```bash
audiobook-cli extract <FILE> [--force-gate]
```

### Options
- `--force-gate`: Bypasses Gate 0.1 extraction quality gate `REVIEW` failure and forces markdown generation.

---

## 9. Literary Translation (`translate`)

Translates extracted chapters into literary dramatic Hindustani via the 4-Agent Translation Collective.

```bash
audiobook-cli translate <BOOK_SLUG> [OPTIONS]
```

### Options
- `--model`: Translation LLM model (default: `gemini-3.8-flash`).
- `--chapter`: Specific chapter number to translate.
- `--chapters`: Comma-separated or range of chapters (e.g. `1-3`).
- `--force-gate`: Bypasses Gate T0–T15 scene certification failure.

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

## 🔗 Related Documentation
- [🏛️ Option C Architecture Blueprint](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/ARCHITECTURE.md)
- [🎙️ Podcast System Architecture](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/PODCAST_SYSTEM_ARCHITECTURE.md)
- [🎭 Dramaturgy & Adaptation System](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/DRAMATURGY_AND_ADAPTATION_SYSTEM.md)
- [🛡️ Quality Gates & 8-Pillar Certification](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/QUALITY_GATES.md)
- [🎛️ Audio Engineering & Mastering](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/AUDIO_ENGINEERING.md)
