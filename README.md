# 🎙️ Audiobook Studio (Antigravity Plugin & Studio Engine v5.3)

> **Autonomous Studio-Grade Multi-Voice Audiobook Production Engine & Google Antigravity Plugin with Gemini Flash TTS, 4D Formant Actor Performance, Two-Pass Linear EBU R128 Mastering, Anti-Swap Dialogue Attribution & Interactive Sidecar Studio Panel.**

[![Antigravity Plugin](https://img.shields.io/badge/Antigravity-Plugin%20v1.0.0-blueviolet.svg)](plugin.json)
[![Pillar 1 Engine](https://img.shields.io/badge/Pillar%201-Forensic%20Ingestion%20v5.3-blue.svg)](docs/FORENSIC_DOCUMENT_INGESTION.md)
[![Ingestion Tests](https://img.shields.io/badge/Ingestion%20Tests-50%2F50%20Passing-brightgreen.svg)](docs/SOURCE_EXTRACTION_HARDENING_SPEC.md)
[![Python](https://img.shields.io/badge/Python-3.10%2B%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-6.0%2B%20%7C%208.0-red.svg)](https://ffmpeg.org/)
[![TTS Engine](https://img.shields.io/badge/TTS-Google%20Gemini%20Flash%20TTS-green.svg)](docs/GEMINI_TTS_SYNTHESIS_AND_DIRECTING.md)
[![Voice Casting](https://img.shields.io/badge/Voice%20Casting-4D%20Acoustic%20Formant%20Matrix-blue.svg)](docs/VOICE_CASTING_DIRECTOR_GUIDE.md)
[![Broadcast Standard](https://img.shields.io/badge/Broadcast-Two--Pass%20Linear%20EBU%20R128%20(-19%20LUFS)-purple.svg)](docs/AUDIO_ENGINEERING.md)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## 📖 Overview

**Audiobook Studio** is an enterprise-grade, autonomous audiobook production system and a first-class **Google Antigravity Plugin**. Engineered specifically for **grounded, natural multi-voice character acting and pristine vocal narration** modeled after the benchmark standards of **Audible Studios**, it transforms raw literature (**EPUB 2/3, PDF, TXT, Markdown**) into chapterized, broadcast-compliant `.m4b` audiobooks with zero corporate fluff or tedious manual editing.

Audiobook Studio operates both as:
1. **A Native Antigravity Plugin**: Direct conversational directing via the `@audiobook-director` agent, interactive Webview Studio Panel sidecar, and full multi-skill workflows.
2. **A Standalone CLI & Python Framework**: Programmatic scripting, batch processing, and headless production pipelines.

---

## 🚫 The Pure Vocals-Only Mandate

Background music (BGM), sound effects (SFX), 5-track stem mixdowns, and external sound scraping are **permanently decoupled and archived** in `archive/cinematic_audio/`.

Rather than masking spoken dialogue with noisy background beds or suffering from broken external sound downloaders, this engine channels 100% of its compute into:
- **Pillar 1 Forensic Document Ingestion (v5.3)**: Zero data-loss parsing, EPUB 3 HTML5 nav, multi-column XY-cut PDF layout reconstruction, and fail-closed Gate 0.1 quality verification.
- **Google Gemini Flash TTS**: High-speed, natural neural performance with token-bucket rotating key pools (120+ active keys).
- **4D Acoustic Formant Modulation**: Pitch ($\pm 4-12\%$), tempo, and 4D parametric EQ curves (`equalizer=f=...`) eliminating vocal convergence across large ensemble casts.
- **Stanislavski Directing Anchors & Restraint**: Clamped temperatures (`0.30 - 0.52`) and physical vocal anchors to eliminate melodramatic screeching or histrionics.
- **Dialogue Editorial Snapping (DE-01 – DE-07)**: Endpoint zero-crossing snapping, Hann micro-fades (12ms/18ms), and contextual turn latency.
- **Broadcast EBU R128 Vocal Mastering**: Integrated loudness of **-19.0 LUFS** ($\pm 0.5$ LUFS) with a hard True Peak ceiling of **-1.5 dBTP**.

---

## 🏛️ The 5-Room Pure Vocals-Only Architecture

```mermaid
flowchart TD
    subgraph Room1["🌍 Room 1: Forensic Ingestion & Pre-Production Intelligence"]
        RawBook["Raw Book (EPUB 2/3, PDF, TXT, MD)"] --> ForensicIngest["Forensic Ingestion Engine (Pillar 1 v5.3)<br/>• EPUB 3 HTML5 Nav & Node-Level Slicing<br/>• PDF Multi-Column XY-Cut & Vision Escalation<br/>• Non-Destructive Normalizer & Provenance Map"]
        ForensicIngest --> Gate01["Gate 0.1: Extraction Quality Gate<br/>• Fail-Closed Word Floors & Scanned Page Audit"]
        Gate01 --> CanAST["Canonical AST (canonical/book.json)<br/>• load_canonical() Rehydration"]
        CanAST --> DeepSearch["Novel DeepSearch Engine (Factual Grounding)"]
        DeepSearch --> BookDNA["Book DNA Agent (Literary Tradition, Era & Dialect)"]
        BookDNA --> Personae["Dramatis Personae & Phonetic Lexicon (cast_lock.json)"]
    end

    subgraph Room2["🧠 Room 2: Sense-for-Sense Translation Collective"]
        Personae --> Collective["4-Agent Translation Collective<br/>• LiteraryDraftTranslator (70/30 Canon Sacredness)<br/>• HindustaniCadenceSpecialist (Spoken Flow & Pauses)<br/>• SubtextAndIdiomDramaturge (Earthy Desi Grit & 19-to-21)<br/>• TranslationQualityCritic (Anti-Omission & Terminology)"]
        Collective --> DualRule["Dual-Rule Invariant ('Nothing Above Source')<br/>Classic Reverent Pathos vs Raw Unrated Realism"]
    end

    subgraph Room3["🎭 Room 3: Screenplay & Forensic Attribution"]
        DualRule --> Screenplay["Sliding-Window Screenplay Dramaturgy"]
        Screenplay --> Auditor["DialogueAttributionAuditor (Anti-Swap QA)<br/>0% Speaker Flips & Quote Disentanglement"]
        Auditor --> Blocking["Physical Blocking & Spatial Headroom"]
    end

    subgraph Room4["🎙️ Room 4: 4D Formants & Voice Performance"]
        Blocking --> Caster["Character Caster (4D Acoustic Formants)<br/>Pitch Δ, Tempo, Bass Boost & Parametric EQ Profiles"]
        Caster --> TTS["Gemini Flash TTS Key Pool (120+ Active Keys)<br/>Prosodic Acting, Speech Tags & Breath Marks"]
        TTS --> Critic["TakeAuditionCritic (Climax Scene Take Selection)"]
        Critic --> Editorial["Dialogue Editorial Layer (DE-01 - DE-07)<br/>Endpoint Snapping, Hann Micro-Fades & Turn Latency"]
    end

    subgraph Room5["🎛️ Room 5: Broadcast Vocal Mastering & Packaging"]
        Editorial --> VocalMaster["Studio Vocal Mastering Engine<br/>SOXR 48kHz / 24-bit + Dual-Pass Loudnorm EBU R128 (-19 LUFS)"]
        VocalMaster --> Packager["FFMETADATA1 Chapter Generator & AAC Packager"]
        Packager --> Deliverable["Deliverable M4B Audiobook (Chapter Markers & Cover Art)"]
    end

    Room1 --> Room2
    Room2 --> Room3
    Room3 --> Room4
    Room4 --> Room5
```

---

## 📜 Pillar 1: Forensic Document Ingestion Engine (v5.3)

Ingestion is the bedrock of the entire studio pipeline. Hardened through a rigorous 3-phase audit, the Pillar 1 engine guarantees **Zero Data Loss**, **Unbroken Forensic Provenance**, and **100% Format-Agnostic Structural Fidelity**:

### Key Architectural Capabilities
- **Dual-Layer Lean Storage**: Preserves sacred unmutated source text in strongly typed Pydantic v2 ASTs (`canonical/book.json`) alongside deterministic backward-compatible Markdown projections (`extracted/chapter_XXX.md`).
- **EPUB 3 HTML5 Navigation & Node-Level Slicing**: Prioritizes modern `<nav epub:type="toc">` landmarks with EPUB 2 NCX fallback. Anchor slicing operates strictly at the parsed `CanonicalBlock` level (`provenance.html_id == anchor_id`), eliminating broken tag bleeding.
- **Resilient XML Parsing (`_safe_xml_fromstring`)**: Automatically catches XML parse errors and dynamically converts unescaped HTML entities (`&mdash;`, `&quot;`, `&hellip;`) to numeric character references.
- **Layout-Aware PDF Engine & Multi-Column XY-Cut**: Reconstructs human reading order across multi-column pages, welds cross-column wrapped sentences, and prevents false column splits on centered poetry or indented dialogue.
- **Scanned PDF 0-Word Escalation**: Identifies 0-word scanned pages (`word_count == 0` with raster images or font defects) and triggers selective vision OCR escalation via `GeminiVisionPDFExtractor`.
- **Non-Destructive Normalizer**: Normalizes Unicode space variants (`\u00A0`, `\u2009`, `\u3000`), unescapes HTML entities, welds wrapped words across Latin and Devanagari scripts, and safely preserves narrative coordinates (`Sector [4]`, `Unit [12]`) and Indic conjuncts (`\u200c`, `\u200d`).
- **Heading Disambiguation & Meso-Tier Abbreviation Guard**: Eliminates standalone `'I'` false chapters, accepts quoted titles (`Chapter 1: "The Voice"`), lookahead-assembles 2-line subtitles, and prevents splitting inside honorifics/abbreviations (`Dr. Watson`, `Capt. Miller`).
- **Passive-Voice Semantic Extraction**: Guarantees correct actor/patient role alignment for passive sentences (`"X was struck by Y"` $\rightarrow$ actor: `Y`, recipient: `X`).
- **100% Full Chapter Entity Harvesting**: Scans up to 100,000 characters per chapter, ensuring late-introduced cast are recorded in `BookBible`.
- **AST Roundtrip Rehydration (`CanonicalBook.load_canonical`)**: Allows downstream rooms to reload the canonical AST directly from disk without re-extracting source files.
- **Windows File Safety & Crash Isolation**: Uses strict context managers (`with open(...)`) eliminating Windows Error 32; persists diagnostic ledgers to `extraction_error.json` on failure.
- **Independent Fail-Closed Gate 0.1**: Halts extraction with [`ExtractionGateAuditError`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/book_model.py) if word floors or chapter thresholds fail.

For full technical specifications, consult [Forensic Document Ingestion Guide](docs/FORENSIC_DOCUMENT_INGESTION.md) and [Source Extraction Hardening Specification](docs/SOURCE_EXTRACTION_HARDENING_SPEC.md).

---

## 🔌 Antigravity Plugin Ecosystem

Audiobook Studio installs seamlessly into Google Antigravity as an all-in-one production plugin:

```text
audiobook-studio/
├── plugin.json                 # Core Antigravity plugin manifest
├── assets/
│   └── logo.svg                # Studio branding icon
├── rules/
│   └── AGENTS.md               # Studio domain invariants & vocal engineering guardrails
├── agents/
│   └── audiobook-director.md   # Studio Audiobook Director persona (@audiobook-director)
├── skills/
│   ├── audiobook-studio/       # Operational directs, project DB inspect, zero-CLI API
│   ├── audio-engineer-ffmpeg/  # FFmpeg DSP, 4D formants, EBU R128 mastering curves
│   └── novel-audiobook-factory/# Autonomous novel ingestion, translation & production
└── sidecars/
    └── studio-panel/           # Webview Aux-Pane UI Extension & Soundboard
        ├── sidecar.json        # Sidecar lifecycle & UI entrypoint
        ├── main.mjs            # Express server + SSE event hub
        ├── index.html          # Clean dark studio interface
        ├── app.js              # State streaming, live waveform, casting board
        └── styles.css          # Studio theme typography and layout
```

### 1. The `@audiobook-director` Agent
Eliminate memorizing CLI flags. Speak directly to the director:
- *"Ingest novel from EPUB and verify Gate 0.1 quality audit"*
- *"Produce next chapter with multi-cast Gemini Flash voices"*
- *"Show active audiobook projects and progress"*
- *"Audition character voices and verify cast roster"*
- *"Run Gate 6 loudness and speech attribution audit on chapter 3"*

### 2. The Interactive Studio Panel (Sidecar Webview)
The embedded Webview runs in Antigravity's auxiliary side pane, providing:
- **Live SSE Event Stream**: Real-time progress bars for ingestion, translation, scripting, TTS chunking, and mastering.
- **Character Casting Matrix**: Visual character roster, assigned acoustic formants (pitch shift, tempo, EQ contour), and 0% collision verification.
- **Waveform Audition Soundboard**: Preview raw takes vs mastered speech segments directly inside the IDE.

---

## 🎛️ Studio Vocal Engineering & Mastering (EBU R128)

Audiobook Studio strictly adheres to international broadcast and Audible production standards:

| Parameter | Benchmark Target | Engine Implementation |
|---|---|---|
| **Integrated Loudness** | **-19.0 LUFS** ($\pm 0.5$ LUFS) | Two-pass measured linear loudnorm (`-f null -` pass 1, `linear=true` pass 2). |
| **True Peak Ceiling** | $\le$ **-1.5 dBTP** | Hard limiter ceiling with Kaiser Sinc 48kHz / 24-bit post-loudnorm resampling. |
| **Consonant Clarity** | Zero de-esser degradation | Dynamic sibilance de-essers are banned; crisp Hindi dental/aspirated consonants (स, श, छ, थ, ध) are preserved. |
| **Phase Coherence** | Natural tempo phrasing | WSOLA time-stretching banned during playback; pacing modulated naturally via punctuation. |
| **Micro-Fades** | Zero-crossing snapping | 12ms pre-speech fade-in and 18ms post-speech fade-out at -52 dBFS noise floor. |
| **Output Container** | Audible-compatible `.m4b` | AAC-LC 128-192 kbps, embedded chapters (`FFMETADATA1`), and high-res cover art. |

---

## 🚀 Quickstart & Installation

### Requirements
- **Python**: 3.10+ (tested on Python 3.10 – 3.13)
- **FFmpeg**: 6.0+ with SOXR support (installed and available in `PATH`)
- **Node.js**: 18+ (for the Webview sidecar panel)
- **Google Gemini API Key(s)**: 1 or more Gemini API keys (supports 120+ key pool)

### 1. Clone & Set Up Python Environment
```bash
git clone https://github.com/naksh-07/audiobook-studio.git
cd audiobook-studio

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Configure Credentials
Create a `.env` file in the root directory:
```env
# Primary API key or comma-separated pool
GEMINI_API_KEY=your_gemini_api_key_here
# Optional multiple keys for rotating pool:
# GEMINI_API_KEYS=key1,key2,key3
```

### 3. Install into Google Antigravity
To install as a local Antigravity plugin:
```bash
# Link or copy to Antigravity plugin directory:
# On Windows:
xcopy /E /I /Y . "%USERPROFILE%\.gemini\config\plugins\audiobook-studio"
# On Linux / macOS:
# cp -r . ~/.gemini/config/plugins/audiobook-studio
```

---

## 💻 Command-Line Interface (`audiobook_cli.py`)

Run autonomous end-to-end production with a single command or execute granular stages step-by-step:

```bash
# 1-Click Autonomous End-to-End Production:
audiobook-studio auto "path/to/novel.epub" --hindi --dramatized --voice Aoede --workers 3

# Step-by-Step Modular Pipeline:
audiobook-studio extract "path/to/novel.epub"
audiobook-studio translate <book_slug>
audiobook-studio script <book_slug> --hindi --dramatized
audiobook-studio synthesize <book_slug> --voice Aoede --workers 3
audiobook-studio master <book_slug>
audiobook-studio package <book_slug> --cover "cover.jpg"
```

### Command Matrix

| Subcommand | Scope | Description |
|---|---|---|
| **`auto`** | Full Book | 1-Click autonomous pipeline (Extract $\rightarrow$ Translate $\rightarrow$ Script $\rightarrow$ Synth $\rightarrow$ Master $\rightarrow$ Package). |
| **`produce`** | Chapter / All | Produces mastered vocal chapters with EBU R128 (-19 LUFS) loudness and timeline ledger. |
| **`extract`** | Ingestion | Ingests EPUB, PDF, TXT, or MD documents into the canonical AST, projects markdown, and enforces Gate 0.1. |
| **`translate`** | Translation | Translates extracted chapters into literary dramatic Hindustani via Translation Collective. |
| **`script`** | Screenplay | Parses prose into standardized screenplay JSON with speaker attribution and acting tags. |
| **`synthesize`** | Audio (TTS) | Synthesizes dialogue chunks using Google Gemini Flash Cloud TTS and 4D formants. |
| **`master`** | Mastering | Concatenates vocal chunks with 5-stage DSP chain and EBU R128 loudness normalization. |
| **`package`** | Delivery | Packages all mastered chapters into a chapterized `.m4b` container with cover art. |
| **`audit`** | QA (Chapter) | Runs Multi-Gate Independent Verification (Gates 0, 1, 2, 2.5, 2.8) on a specific chapter. |
| **`audit-book`** | QA (Macro) | Runs Macro-Tier Gate 6 certification (Voice Continuity, Loudness, TOC Monotonicity). |

---

## 🧪 Verification & Quality Testing

Audiobook Studio maintains strict architectural anti-tamper and regression suites:

```bash
# Run complete test suite (800+ isolated tests)
pytest tests/ -v

# Run Pillar 1 Forensic Ingestion test matrix (50/50 passing)
pytest tests/test_document_extractor_upgraded.py tests/test_epub_parser.py tests/test_pdf_engine.py tests/test_extraction_phase3.py tests/test_chapter_segmenter.py tests/test_normalizer.py tests/translation/test_semantic_map.py tests/translation/test_book_bible.py tests/test_book_model.py -v
```

All quality gates are fail-closed:
- **Gate 0.1**: Forensic Ingestion & Reading Order AST Validation (Word floors, empty chapters, scanned page escalation).
- **Gate 1**: Dramatis Personae & 0% Voice Collision Casting.
- **Gate 2**: DialogueAttributionAuditor (0% Speaker Turn Swaps).
- **Gate 2.5**: Stanislavski Acting Restraint (clamped temp, physical vocal anchors).
- **Gate 5**: Dialogue Editorial Snapping & Hann Micro-fades.
- **Gate 6**: Two-Pass Linear Loudnorm Certification (-19.0 LUFS, -1.5 dBTP).

---

## 📚 Documentation Index

For exhaustive technical guides, visit the [`docs/`](docs/) directory:
- [📜 Forensic Document Ingestion Engine (Pillar 1)](docs/FORENSIC_DOCUMENT_INGESTION.md)
- [🛡️ Source Extraction Hardening Specification (Pillar 1 v5.3)](docs/SOURCE_EXTRACTION_HARDENING_SPEC.md)
- [🏛️ Architecture Blueprint](docs/ARCHITECTURE.md)
- [🎛️ Audio Engineering & Mastering](docs/AUDIO_ENGINEERING.md)
- [🎙️ Gemini Flash TTS Synthesis & Directing](docs/GEMINI_TTS_SYNTHESIS_AND_DIRECTING.md)
- [🎭 Voice Casting Director Guide](docs/VOICE_CASTING_DIRECTOR_GUIDE.md)
- [🇮🇳 Complete Hindi Voice Catalog](docs/HINDI_VOICE_CATALOG.md)
- [🧠 Literary Translation Intelligence](docs/LITERARY_TRANSLATION_INTELLIGENCE.md)
- [🎭 Dramatic Adaptation & Screenplay](docs/DRAMATIC_ADAPTATION_AND_SCREENPLAY.md)
- [✂️ Dialogue Editorial Layer](docs/DIALOGUE_EDITORIAL_LAYER.md)
- [💻 CLI Reference Manual](docs/CLI_REFERENCE.md)
- [🛡️ Quality Gates Specifications](docs/QUALITY_GATES.md)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

*Built with ❤️ for Google Antigravity by Suraj ([@naksh-07](https://github.com/naksh-07))*
