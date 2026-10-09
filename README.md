# 🎙️ Audiobook Studio (Antigravity Plugin & Studio Engine v5.4)

> **Autonomous Studio-Grade Multi-Voice Audiobook Production Engine & Google Antigravity Plugin with Gemini Flash TTS, 4D Formant Actor Performance, Pro-Grade AI Vocal Mastering Workstation, Anti-Swap Dialogue Attribution & Interactive Sidecar Studio Panel.**

[![Antigravity Plugin](https://img.shields.io/badge/Antigravity-Plugin%20v1.0.0-blueviolet.svg)](plugin.json)
[![Python](https://img.shields.io/badge/Python-3.10%2B%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-6.0%2B%20%7C%208.0-red.svg)](https://ffmpeg.org/)
[![TTS Engine](https://img.shields.io/badge/TTS-Google%20Gemini%20Flash%20TTS-green.svg)](docs/GEMINI_TTS_SYNTHESIS_AND_DIRECTING.md)
[![Vocal DSP](https://img.shields.io/badge/DSP-Spotify%20Pedalboard%20(C%2B%2B%20JUCE)-orange.svg)](docs/VOCAL_AUDIO_MIXING_AND_PRODUCTION.md)
[![Neural Audio](https://img.shields.io/badge/Neural-DeepFilterNet3%20%7C%20Matchering%202.0-yellow.svg)](docs/VOCAL_AUDIO_MIXING_AND_PRODUCTION.md)
[![Broadcast Standard](https://img.shields.io/badge/Broadcast-EBU%20R128%20(-19%20LUFS)%20%7C%20-1.5%20dBTP-purple.svg)](docs/AUDIO_ENGINEERING.md)
[![Tests](https://img.shields.io/badge/Tests-100%25%20Passing-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## 📖 Overview

**Audiobook Studio (v5.4)** is an enterprise-grade, autonomous audiobook production system and a first-class **Google Antigravity Plugin**. Engineered specifically for **grounded, natural multi-voice character acting and pristine vocal narration** modeled after the benchmark standards of **Audible Studios**, it transforms raw literature (**EPUB, PDF, TXT, Markdown**) into chapterized, broadcast-compliant `.m4b` audiobooks with zero corporate fluff or tedious manual editing.

Version 5.4 introduces the **Pro-Grade AI Vocal Mastering Workstation**:
- **C++ JUCE Vocal DSP Engine (ADR-021)**: Powered by Spotify Pedalboard and Pyloudnorm (BS.1770-4), offering 4-band parametric vocal EQ, optical compression (2.5:1 ratio), lookahead True Peak limiting (-1.5 dBTP), and headless VST3 hosting.
- **Forensic Audio QA Auditor (ADR-022)**: Automated VAD boundary validation, text-grounded speaking rate checking (WPM and char/sec) catching dropouts (>320 WPM) and loops (<40 WPM), and non-intrusive Speech MOS prediction.
- **Neural Vocal Polish & Spectrum Matcher (ADR-023)**: DeepFilterNet3 (48kHz full-band) with >45dB SNR selective auto-bypass and Matchering 2.0 with ±3.0dB hard spectral clamping.
- **Antigravity Audio MCP Server & CLI Bridge (ADR-024)**: Standardized JSON-RPC tools and CLI subcommands (`dsp`, `qa-audit`, `enhance`, `match-ref`).

Audiobook Studio operates both as:
1. **A Native Antigravity Plugin**: Direct conversational directing via the `@audiobook-director` agent, interactive Webview Studio Panel sidecar, and full multi-skill workflows.
2. **A Standalone CLI & Python Framework**: Programmatic scripting, batch processing, and headless production pipelines.

---

## 🚫 The Pure Vocals-Only Mandate

Background music (BGM), sound effects (SFX), 5-track stem mixdowns, and external sound scraping are **permanently decoupled and archived** in `archive/cinematic_audio/`.

Rather than masking spoken dialogue with noisy background beds or suffering from broken external sound downloaders, this engine channels 100% of its compute into:
- **Google Gemini Flash TTS** with token-bucket rotating key pools.
- **4D Acoustic Formant Modulation** (Pitch $\pm 4-12\%$, tempo, and 4D parametric EQ curves) eliminating vocal convergence.
- **Stanislavski Directing Anchors** and temperature clamping (`0.30 - 0.52`) to prevent histrionic screeching.
- **Broadcast EBU R128 Vocal Mastering** (-19.0 LUFS, -1.5 dBTP) with Hann micro-fades.

---

## 🏛️ The 5-Room Pure Vocals-Only Architecture

```mermaid
flowchart TD
    subgraph Room1["🌍 Room 1: Pre-Production Intelligence"]
        RawBook["Raw Book (PDF / EPUB / TXT)"] --> DeepSearch["Novel DeepSearch Engine (Factual Grounding)"]
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

    subgraph Room5["🎛️ Room 5: Pro-Grade AI Vocal Mastering Workstation"]
        Editorial --> StreamComp["ChunkStreamComposer (<= 800 KB RAM Streaming)<br/>Direct premaster.wav Writer + Zero Disk Silence Files"]
        StreamComp --> QAAudit["Phase 2: AudioQAAuditor (VAD, WPM bounds, MOS)"]
        QAAudit --> NeuralEnhance["Phase 3: Neural Vocal Polish & Matchering 2.0"]
        NeuralEnhance --> VocalDSP["Phase 1: VocalDSPProcessor (C++ JUCE Pedalboard)<br/>4-Band Parametric EQ + Optical Comp + Limiter (-1.5 dBTP)"]
        VocalDSP --> AACDeliver["ChapterDeliveryEncoder (Single-Pass 192k AAC-LC)<br/>Post-Encode True Peak Verification (<= -1.5 dBTP)"]
        AACDeliver --> M4BPack["M4BBookPackager (Lossless Stream Copy -c:a copy)<br/>Monotonic FFMETADATA1 Chapter Markers & Cover Art"]
        M4BPack --> Deliverable["Studio Audiobook Deliverable (.m4b)"]
        HotPatch["SingleSegmentHotPatcher & ChapterSegmentLedger<br/>Incremental DAG Caching & < 0.2s Sample-Accurate Splice"] -.-> StreamComp
    end

    Room1 --> Room2
    Room2 --> Room3
    Room3 --> Room4
    Room4 --> Room5
```

### 🎛️ Room 5: Pro-Grade AI Vocal Mastering Workstation ([`audiobook_factory/audio/`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/))

Room 5 houses the broadcast-compliant audio production pipeline engineered to transform raw synthesized speech into Audible-standard `.m4a` chapter deliverables and chapterized `.m4b` containers:

- **Strongly Typed Audio Contracts ([`contracts.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/contracts.py))**: Immutable Pydantic v2 schemas ([`DSPConfig`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/contracts.py#L87-L106), [`AudioQAConfig`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/contracts.py#L121-L135), [`SegmentAudioContract`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/contracts.py#L26-L67), [`ChapterMasterContract`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/contracts.py#L68-L86)) defining strict interfaces across ingestion, editorial, mastering, and container packaging.
- **C++ JUCE Vocal DSP Engine ([`dsp.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/dsp.py))**: [`VocalDSPProcessor`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/dsp.py#L65-L383) wrapping Spotify Pedalboard and Pyloudnorm (BS.1770-4). Applies 4-band parametric EQ (75Hz rumble cut, 320Hz notch, 3.2kHz presence lift), optical compression (2.5:1 ratio), lookahead True-Peak limiting (-1.5 dBTP), and headless VST3 hosting, with automatic fallback to deterministic dual-pass FFmpeg mastering.
- **Forensic Audio QA Auditor ([`qa_auditor.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/qa_auditor.py))**: [`AudioQAAuditor`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/qa_auditor.py#L46-L358) detects dead-air boundaries, verifies speaking rates (WPM and char/sec) against text to catch TTS dropouts (>320 WPM) and hallucination loops (<40 WPM), and predicts Speech MOS.
- **Neural Vocal Polish & Restoration ([`enhancer.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/enhancer.py))**: [`NeuralVocalEnhancer`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/enhancer.py#L42-L220) wrapping DeepFilterNet3 (48kHz full-band) with $>45\text{ dB}$ SNR selective auto-bypass and energy difference clamping ($|\Delta\text{RMS}| \le 2.0\text{ dB}$).
- **Reference Spectrum Matching ([`reference_matcher.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/reference_matcher.py))**: [`ReferenceSpectrumMatcher`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/reference_matcher.py#L41-L214) wrapping Matchering 2.0 with a hard $\pm 3.0\text{ dB}$ spectral clamp.
- **Antigravity Audio MCP Server ([`mcp/server.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/mcp/server.py))**: 6 standardized MCP tools (`apply_vocal_dsp`, `audit_audio_quality`, `match_reference_spectrum`, `enhance_vocal_stem`, `measure_ebu_r128_loudness`, `audit_chapter_qa`).
- **Tier A Speech Ingestion & Normalization ([`ingestion.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/ingestion.py))**: Standardizes incoming speech chunks to uniform **48,000 Hz 24-bit stereo PCM WAV**, strips C2PA digital watermark artifacts, rejects DC bias via 30Hz highpass filter, and enforces a **Single 5.0ms Raised-Cosine Hann Micro-Taper (AP-06)** with boundary samples pinned strictly to 0.0.
- **Streaming Pre-Master Composer ([`stream_composer.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/stream_composer.py))**: Block-based WAV writer streaming speech, syntax pauses, and DE-05 overlaps directly into `premaster.wav` under a **constant $\le 800\text{ KB}$ RAM ceiling**.
- **Single-Pass Chapter Delivery Encoder ([`encoder.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/encoder.py))**: Single-pass 192k AAC-LC delivery (`chapter_XXX.m4a`) with automated post-encode True Peak verification ($\le -1.5\text{ dBTP}$).
- **Lossless Stream Copy M4B Packager ([`packager.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/packager.py))**: Assembles chapter deliverables into `.m4b` via **lossless stream copy (`-c:a copy`)** with monotonic `FFMETADATA1` markers.
- **Incremental DAG Caching & Hot-Patching ([`ledger.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/ledger.py), [`hot_patcher.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/hot_patcher.py))**: Performs sample-accurate timeline splicing in $<0.2\text{s}$ for single-segment repairs without full chapter rebuilds (AP-07).

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
Speak directly to the director:
- *"Produce next chapter with multi-cast Gemini Flash voices"*
- *"Run forensic speech QA audit on synthesized chapter 1 takes"*
- *"Apply C++ JUCE vocal DSP mastering to chapter 2 pre-master"*
- *"Check EBU R128 loudness compliance on deliverable M4A"*

### 2. The Interactive Studio Panel (Sidecar Webview)
The embedded Webview runs in Antigravity's auxiliary side pane, providing real-time progress bars, visual character casting matrix, and live waveform soundboard auditioning.

---

## 🎛️ Studio Vocal Engineering & Mastering (EBU R128)

Audiobook Studio strictly adheres to international broadcast and Audible production standards:

| Parameter | Benchmark Target | Engine Implementation |
|---|---|---|
| **Integrated Loudness** | **-19.0 LUFS** ($\pm 0.5$ LUFS) | `VocalDSPProcessor` (Pedalboard C++ JUCE + Pyloudnorm) or two-pass measured linear loudnorm (`-f null -` pass 1, `linear=true` pass 2); dynamic loudnorm AGC strictly banned during pauses/silence (AP-08). |
| **True Peak Ceiling** | $\le$ **-1.5 dBTP** | Lookahead True Peak limiter ceiling calibrated to **-1.5 dBTP** (or -2.0 dBFS PCM) absorbing AAC codec regrowth; verified via post-encode True Peak audit ($\le -1.5\text{ dBTP}$). |
| **Acoustic QA & MOS** | $\ge \mathbf{4.0}$ Predicted MOS | Forensic `AudioQAAuditor` auditing speech boundaries, WPM bounds, dropouts, and non-intrusive MOS. |
| **Neural Speech Polish** | $>45\text{ dB}$ Auto-Bypass | DeepFilterNet3 neural polish with auto-bypass on clean takes and $|\Delta\text{RMS}| \le 2.0\text{ dB}$ energy clamping. |
| **Reference Matching** | $\pm \mathbf{3.0\text{ dB}}$ Clamped | Matchering 2.0 spectral profile transplantation with hard gain clamping. |
| **Streaming Memory** | $\le \mathbf{800\text{ KB}}$ RAM | Block-based `ChunkStreamComposer` writes directly to `premaster.wav`, eliminating memory bloat. |
| **Incremental DAG Recovery** | $< \mathbf{0.2\text{s}}$ hot-patch | `ChapterSegmentLedger` SHA-256 caching + `SingleSegmentHotPatcher` sample-accurate timeline splicing without full chapter re-rendering (AP-07). |
| **Consonant Clarity** | Zero de-esser degradation | Dynamic sibilance de-essers are banned; crisp Hindi dental/aspirated consonants (स, श, छ, थ, ध) are preserved. |
| **Output Container** | Audible-compatible `.m4b` | Single-pass 192 kbps AAC-LC chapter deliverable (`.m4a`), lossless stream copy assembly (`-c:a copy`), strictly monotonic `FFMETADATA1` markers, and high-res cover art. |

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

# Or step-by-step modular pipeline:
audiobook-studio extract "path/to/novel.epub"
audiobook-studio translate <book_slug>
audiobook-studio script <book_slug> --hindi --dramatized
audiobook-studio synthesize <book_slug> --voice Aoede --workers 3
audiobook-studio master <book_slug>
audiobook-studio package <book_slug> --cover "cover.jpg"

# Pro-Grade AI Vocal Mastering & QA subcommands:
audiobook-studio dsp -i raw_chapter.wav -o mastered_chapter.wav --target-lufs -19.0 --true-peak -1.5
audiobook-studio qa-audit -i c01_s001.wav -t "Spoken text line" -s "Narrator"
audiobook-studio enhance -i noisy_take.wav -o cleaned_take.wav
audiobook-studio match-ref -t my_chapter.wav -r golden_ref.wav -o matched.wav
```

### Command Matrix

| Subcommand | Scope | Description |
|---|---|---|
| **`auto`** | Full Book | 1-Click autonomous pipeline (Extract $\rightarrow$ Translate $\rightarrow$ Script $\rightarrow$ Synth $\rightarrow$ Master $\rightarrow$ Package). |
| **`produce`** | Chapter / All | Produces mastered vocal chapters with EBU R128 (-19 LUFS) loudness and timeline ledger. |
| **`extract`** | Ingestion | Ingests EPUB, PDF, TXT, or MD documents into clean Markdown chapters. |
| **`translate`** | Translation | Translates extracted chapters into literary dramatic Hindustani via Translation Collective. |
| **`script`** | Screenplay | Parses prose into standardized screenplay JSON with speaker attribution and acting tags. |
| **`synthesize`** | Audio (TTS) | Synthesizes dialogue chunks using Google Gemini Flash Cloud TTS and 4D formants. |
| **`master`** | Mastering | Concatenates vocal chunks with 5-stage DSP chain and EBU R128 loudness normalization. |
| **`package`** | Delivery | Packages all mastered chapters into a chapterized `.m4b` container with cover art. |
| **`audit`** | QA (Chapter) | Runs Multi-Gate Independent Verification (Gates 0, 1, 2, 2.5, 2.8) on a specific chapter. |
| **`audit-book`** | QA (Macro) | Runs Macro-Tier Gate 6 certification (Voice Continuity, Loudness, TOC Monotonicity). |
| **`dsp`** | Pro Audio | Applies C++ JUCE parametric vocal EQ, optical compression, and True-Peak limiting. |
| **`qa-audit`** | Acoustic QA | Forensically audits speech chunks for dead air, WPM bounds, dropouts, loops, and MOS. |
| **`enhance`** | AI Polish | DeepFilterNet3 neural speech de-artifacting with selective >45dB SNR auto-bypass. |
| **`match-ref`** | Mastering | Matches frequency spectrum to golden master with ±3.0dB hard spectral clamping. |

---

## 🧪 Verification & Quality Testing

Audiobook Studio maintains strict architectural anti-tamper and regression suites:

```bash
# Run complete test suite (800+ isolated tests)
pytest tests/ -v
```

All quality gates are fail-closed:
- **Gate 0.1**: Forensic Ingestion & Reading Order AST Validation.
- **Gate 1**: Dramatis Personae & 0% Voice Collision Casting.
- **Gate 2**: DialogueAttributionAuditor (0% Speaker Turn Swaps).
- **Gate 2.5**: Stanislavski Acting Restraint (clamped temp, physical vocal anchors).
- **Gate 5**: Dialogue Editorial Snapping & Hann Micro-fades.
- **Gate 6**: Two-Pass Linear Loudnorm Certification (-19.0 LUFS, -1.5 dBTP).

---

## 📚 Documentation Index

For exhaustive technical guides, visit the [`docs/`](docs/) directory:
- [🏛️ Architecture Blueprint](docs/ARCHITECTURE.md)
- [🎛️ Audio Engineering & Mastering](docs/AUDIO_ENGINEERING.md)
- [🎛️ Pro-Grade AI Vocal Mastering & Production (v5.4)](docs/VOCAL_AUDIO_MIXING_AND_PRODUCTION.md)
- [💻 CLI Reference Manual](docs/CLI_REFERENCE.md)
- [🤖 AI Agent & MCP Integration Guide](docs/MCP_AGENT_INTEGRATION.md)
- [📚 API Reference & Data Contracts](docs/API_REFERENCE.md)
- [🎙️ Gemini Flash TTS Synthesis & Directing](docs/GEMINI_TTS_SYNTHESIS_AND_DIRECTING.md)
- [🎭 Voice Casting Director Guide](docs/VOICE_CASTING_DIRECTOR_GUIDE.md)
- [🇮🇳 Complete Hindi Voice Catalog](docs/HINDI_VOICE_CATALOG.md)
- [🧠 Literary Translation Intelligence](docs/LITERARY_TRANSLATION_INTELLIGENCE.md)
- [🎭 Dramatic Adaptation & Screenplay](docs/DRAMATIC_ADAPTATION_AND_SCREENPLAY.md)
- [✂️ Dialogue Editorial Layer](docs/DIALOGUE_EDITORIAL_LAYER.md)
- [🛡️ Quality Gates Specifications](docs/QUALITY_GATES.md)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

*Built with ❤️ for Google Antigravity by Suraj ([@naksh-07](https://github.com/naksh-07))*
