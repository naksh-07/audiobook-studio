# 💻 CLI Reference: Audiobook Studio Engine (v5.4)

## Overview

The Audiobook Studio Command-Line Interface ([`audiobook_cli.py`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_cli.py)) provides operational control over the entire studio-grade vocal production pipeline. You can run an autonomous end-to-end novel production run with a single command or execute granular subcommands stage-by-stage.

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
| **[`dsp`](#11-vocal-dsp-mastering-dsp)** | Pro Audio | Applies C++ JUCE parametric vocal EQ, optical compression, and True-Peak limiting. |
| **[`qa-audit`](#12-forensic-speech-qa-audit-qa-audit)** | Acoustic QA | Forensically audits speech chunks for dead air, WPM bounds, dropouts, loops, and MOS. |
| **[`enhance`](#13-neural-vocal-polish-enhance)** | AI Polish | DeepFilterNet3 neural speech de-artifacting with selective >45dB SNR auto-bypass. |
| **[`match-ref`](#14-reference-spectrum-matching-match-ref)** | Mastering | Matches frequency spectrum to golden master with ±3.0dB hard spectral clamping. |

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
| `--flow` | Flag | `True` | Enable Audible Flow mode (preserves prose and acting tags). |
| `--cast-mode` | Choice | `ensemble` | Cast allocation mode (`ensemble` or `solo`). |
| `--cover` | Path | `None` | Path to cover artwork image (JPEG/PNG, min $1400 \times 1400$ px). |
| `--workers` | Integer | `3` | Number of concurrent TTS synthesis worker threads. |
| `--force-gate` | Flag | `False` | Bypass Ingestion Quality Gate REVIEW warning and force production. |
| `--chapter` | Integer | `None` | Specific chapter number to produce. |
| `--chapters` | String | `None` | Comma-separated or range of chapters (e.g. `1-3` or `1,2`). |

### Example
```bash
python audiobook_cli.py auto "C:/novels/mystic_odyssey.epub" --hindi --dramatized --voice Aoede --workers 3
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
| `--clean-dsp` | Flag | `True` | Clean studio vocal DSP without artificial pitch shifting. |

---

## 3. Universal Document Extraction (`extract`)

Ingests digital book files into clean, segmented Markdown chapters using geometric reading-order layout extraction.

```bash
python audiobook_cli.py extract <FILE> [--force-gate]
```

### Options
| Flag | Type | Default | Description |
|---|:---:|:---:|---|
| `file` | Path | *Required* | Input file path (`.epub`, `.pdf`, `.txt`, `.md`). |
| `--force-gate` | Flag | `False` | Bypass Gate 0.1 extraction warnings and force production. |

---

## 4. Literary Translation (`translate`)

Translates extracted chapters into literary dramatic Hindustani using the 4-Agent Translation Collective.

```bash
python audiobook_cli.py translate <BOOK_SLUG> [OPTIONS]
```

### Options
| Flag | Type | Default | Description |
|---|:---:|:---:|---|
| `book` | String | *Required* | Project book slug. |
| `--model` | String | `gemini-3.8-flash` | Gemini translation LLM model endpoint. |
| `--chapter` | Integer | `None` | Specific chapter number to translate. |
| `--chapters` | String | `None` | Comma-separated or range of chapters (e.g. `1-2`). |
| `--force-gate` | Flag | `False` | Force translation progression if quality review alerts trigger. |

---

## 5. Screenplay Scripting (`script`)

Parses prose into standardized screenplay JSON with speaker attribution, 4D formant metadata, and Stanislavski acting cues.

```bash
python audiobook_cli.py script <BOOK_SLUG> [OPTIONS]
```

### Options
| Flag | Type | Default | Description |
|---|:---:|:---:|---|
| `book` | String | *Required* | Project book slug. |
| `--hindi` | Flag | `False` | Script from translated Hindi chapters. |
| `--dramatized` | Flag | `False` | Multi-voice character attribution mode. |
| `--flow` | Flag | `True` | Preserve narrative flow and acting tags. |
| `--cast-mode` | Choice | `ensemble` | Voice casting allocation: `ensemble` or `solo`. |
| `--chapter` | Integer | `None` | Specific chapter number to script. |
| `--chapters` | String | `None` | Comma-separated or range of chapters. |
| `--overwrite` | Flag | `False` | Overwrite existing screenplay JSON files. |

---

## 6. Speech Synthesis (`synthesize`)

Synthesizes dialogue segments via Google Gemini Flash Cloud TTS with 4D acoustic formant modulation.

```bash
python audiobook_cli.py synthesize <BOOK_SLUG> [OPTIONS]
```

### Options
| Flag | Type | Default | Description |
|---|:---:|:---:|---|
| `book` | String | *Required* | Project book slug. |
| `--chapter` | Integer | `None` | Specific chapter number to synthesize. |
| `--chapters` | String | `None` | Range of chapters to synthesize. |
| `--voice` | String | `Aoede` | Default narrator persona. |
| `--backend` | Choice | `gemini_tts` | Speech synthesis engine backend. |

---

## 7. Vocal DSP Mastering (`master`)

Concatenates speech segments with Hann micro-fades and normalizes to EBU R128 (-19 LUFS) at 48kHz / 24-bit.

```bash
python audiobook_cli.py master <BOOK_SLUG> [OPTIONS]
```

### Options
| Flag | Type | Default | Description |
|---|:---:|:---:|---|
| `book` | String | *Required* | Project book slug. |
| `--chapter` | Integer | `None` | Specific chapter number to master. |
| `--chapters` | String | `None` | Comma-separated or range of chapters. |

---

## 8. M4B Container Packaging (`package`)

Assembles all mastered chapters into a final chapterized `.m4b` container with TOC navigation and embedded cover art.

```bash
python audiobook_cli.py package <BOOK_SLUG_OR_PATH> [OPTIONS]
```

### Options
| Flag | Type | Default | Description |
|---|:---:|:---:|---|
| `book` | String/Path | *Required* | Project book slug or folder path. |
| `--cover` | Path | `None` | Path to cover art image (min $1400 \times 1400$ px). |
| `--enforce-gate6` | Flag | `False` | Abort packaging if any Gate 6 verification check fails. |

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

## 11. Vocal DSP Mastering (`dsp`)

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

## 12. Forensic Speech QA Audit (`qa-audit`)

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

### Error Case Example (Dropout Truncation Detected)
```json
{
  "segment_index": 5,
  "segment_uid": "c01_s005_Charon",
  "speaker": "King",
  "status": "FAIL",
  "duration_ms": 310,
  "estimated_wpm": 412.5,
  "char_per_sec": 48.0,
  "predicted_mos": 3.10,
  "silence_leading_ms": 10,
  "silence_trailing_ms": 10,
  "issues": [
    "TTS_DROPOUT_TRUNCATION: Speaking rate 412.5 WPM (48.0 char/s) is physically impossible; speech was truncated."
  ],
  "remediation_advice": "Trigger automated segment re-synthesis with adjusted TTS temperature."
}
```

### Example
```bash
python audiobook_cli.py qa-audit -i "c01_s001.wav" -t "The old tavern was shrouded in darkness." -s "Narrator"
```

---

## 13. Neural Vocal Polish (`enhance`)

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
*(If input audio is already $>45\text{ dB}$ SNR clean, `was_enhanced` returns `false` indicating auto-bypass).*

### Example
```bash
python audiobook_cli.py enhance -i "grainy_take.wav" -o "cleaned_take.wav"
```

---

## 14. Reference Spectrum Matching (`match-ref`)

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

## 📦 Archived Subsystems Notice

The legacy subcommands (`direct`, `render`, `bgm`, `stems`, `bank`) belong to the decoupled 5-track cinematic audio engine and are archived in `archive/cinematic_audio/`. They are not part of the active Vocals-Only pipeline.
