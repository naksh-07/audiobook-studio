# Master Architecture & Implementation Plan: Pro-Grade AI Vocal Mastering Workstation

**Document Version**: 1.0.0  
**Target Repository**: `audiobook-studio` / `audio_master`  
**Standard**: Audible / ACX / EBU R128 (-19.0 LUFS, $\le -1.5\text{ dBTP}$, $\le -60\text{ dBFS}$ Noise Floor)  
**Platform**: High-Performance Windows 11 Workstation (CUDA GPU + Multi-Core CPU + Antigravity Agents)

---

## 1. Executive Vision & Core Philosophy

### The Goal
Transform the existing pure vocals-only audiobook engine into an **autonomous, industry-grade AI mastering workstation** that matches or exceeds Audible / BBC Radio Drama vocal production standards — while **strictly avoiding overengineering, memory bloat, and fragile dependencies**.

### The Anti-Overengineering Invariants
1. **Never Replace Fast Streaming with RAM Hogs**: Preserve the $\le 800\text{KB}$ ring buffer in `stream_composer.py`. Long-form audiobooks ($10+\text{ hours}$) must never load giant uncompressed arrays into memory.
2. **Conditional / Surgical Neural Processing**: Do not run heavy neural models blindly on 100% of clean TTS stems. Use neural enhancers (DeepFilterNet3) surgically on noisy/glitched takes or when explicitly enabled.
3. **Fail-Closed Graceful Degradation**: Every advanced tool (Pedalboard VST3, Matchering, WhisperX) **MUST** have an automatic, seamless fallback to our battle-tested deterministic FFmpeg/NumPy pipeline. If a library is missing or a C++ plugin fails, the build **never crashes** — it gracefully completes via standard mastering.
4. **Pure Vocals-Only Mandate**: Zero BGM, zero SFX, zero multitrack Foley mixdowns. 100% laser-focused on voice acting, dialogue dynamics, tonal warmth, and pristine broadcast loudness.

---

## 2. Architectural Topology: Clean Modular Subsystem

Instead of a 3,000-line monolithic file or 10 fragmented external tools, the entire mastering workstation is organized as a cohesive, single-responsibility subsystem inside [`audiobook_factory/audio/`](file:///c:/Users/Suraj/Documents/Antigravity/audio_master/audiobook_factory/audio/):

```text
audiobook_factory/audio/
├── __init__.py               # Public API exports
├── contracts.py              # Strongly typed Pydantic v2 contracts (Segment, Chapter, QC)
├── ingestion.py              # Tier A: 48kHz 24-bit stereo normalization & C2PA stripping
├── enhancer.py               # [P3] Neural de-artifacting & restoration (DeepFilterNet3)
├── dsp.py                    # [P1] C++ JUCE Pedalboard DSP Engine (EQ, Comp, Limiter, VST3)
├── stream_composer.py        # Tier B: Ring-buffer timeline composer with syntax pauses & dither
├── reference_matcher.py      # [P3] Matchering 2.0 reference spectrum matching
├── qa_auditor.py             # [P2] WhisperX CTC alignment + Silero VAD + SQUIM MOS
├── editorial.py              # Dialogue Editorial Layer orchestration (DE-01 - DE-07)
├── encoder.py                # Tier C/D: Broadcast 192k AAC encoding with True Peak remediation
├── packager.py               # Tier D: 64-bit M4B packager with dual chapter TOC & metadata
├── ledger.py                 # Incremental DAG cryptographic segment ledger
└── hot_patcher.py            # Sub-second single-segment re-mastering & container splice
```

---

## 3. Deep Component Analysis: Problem, Solution, Hypothesis & Fallback Defense

### Component 1: Studio C++ DSP Engine & Headless VST3 Hosting (`dsp.py`)
- **Real Problem in Current System**:
  FFmpeg's command-line filters are static. Chaining complex dynamic EQ, optical vocal leveling, lookahead True Peak limiting, and de-essing requires unwieldy subprocess strings that are difficult to inspect, debug, and modulate per speaker.
- **Proposed Solution**:
  `audiobook_factory/audio/dsp.py` wrapping **Spotify Pedalboard (C++ JUCE)**.
  - 4-Band parametric vocal EQ (75Hz highpass rumble cut, 320Hz boxiness dip, 3.2kHz speech clarity lift).
  - Transparent optical compressor (2.5:1 ratio, 25ms attack, 120ms release) for natural dialogue dynamic control.
  - Headless VST3 loader (allows hosting free/commercial plugins like TDR Nova, FabFilter Pro-Q3, Youlean Meter).
  - Lookahead True-Peak brickwall limiter clamped strictly to `-1.5 dBTP`.
- **Hypothesis / Failure Modes ("Kya fail ho sakta hai?")**:
  1. *Risk*: User environment me `pedalboard` package missing ho ya C++ binary compilation issue aye.
  2. *Risk*: Third-party VST3 plugin crash kar jaye ya unavailable ho.
- **Safety Defense (Self-Healing Fallback)**:
  ```python
  # Graceful Degradation Invariant
  try:
      import pedalboard
      HAS_PEDALBOARD = True
  except ImportError:
      HAS_PEDALBOARD = False
  
  def apply_vocal_mastering(input_wav: Path, output_wav: Path, profile: MasteringProfile):
      if HAS_PEDALBOARD:
          try:
              return _pedalboard_mastering_chain(input_wav, output_wav, profile)
          except Exception as e:
              logger.warning(f"Pedalboard DSP failed ({e}); falling back to FFmpeg engine.")
      # Robust Fallback to FFmpeg deterministic pipeline
      return _ffmpeg_mastering_chain(input_wav, output_wav, profile)
  ```

---

### Component 2: Automated Acoustic QA & Hallucination Auditor (`qa_auditor.py`)
- **Real Problem in Current System**:
  Gate 4 verification abhi sirf numerical audio checks karta hai (NaN/Inf, clipping, LUFS). Agar TTS ne dialogue ka 1 sentence chhod diya (dropout) ya loop me repeat kiya (hallucination), toh system ko pata nahi chalta jab tak human 10 ghante na sune.
- **Proposed Solution**:
  `audiobook_factory/audio/qa_auditor.py` integrating **WhisperX + Silero VAD v5 + TorchAudio-SQUIM**.
  - **Silero VAD**: Micro-second speech boundary check (detects unnatural silence $> 1.8\text{s}$ or rushed lines $< 150\text{ms}$).
  - **WhisperX CTC Aligner**: Phoneme-accurate text-to-audio matching against canonical screenplay script.
  - **TorchAudio-SQUIM / DNSMOS**: Calculates non-intrusive Speech MOS (Overall MOS target $\ge 4.2$).
- **Hypothesis / Failure Modes ("Kya fail ho sakta hai?")**:
  1. *Risk*: Devanagari Hindi ya colloquial slang par WhisperX false-positive error dede aur valid chunk reject ho jaye.
  2. *Risk*: Heavy Whisper model inference se production slow ho jaye.
- **Safety Defense (Self-Healing Fallback)**:
  - 1. QA audit runs in **Tiered Tolerance Mode**:
       - *Hard Rejection*: Sirf tab jab audio duration script length se $> 40\%$ mismatch ho (hallucination loop ya severe truncation).
       - *Soft Warning*: Minor phoneme differences par warning log hoti hai, mastering block nahi hoti.
  - 2. Lightweight `tiny` / `base` model or Silero-VAD first-pass ensures speed $< 0.1\text{s}$ per chunk.
  - 3. Can be toggled on/off via CLI flag (`--enable-ai-qa`).

---

### Component 3: Neural De-Artifacting & Vocal Restoration (`enhancer.py`)
- **Real Problem in Current System**:
  Generative neural TTS me kabhi-kabhi subtle metallic hiss, micro-clicks, ya breath quantization artifacts aate hain. FFmpeg ke standard denoisers (`afftdn`) pure frequency bands ko wash out kar dete hain aur Hindi dental consonants (स, श, छ, थ) ko blur kar dete hain.
- **Proposed Solution**:
  `audiobook_factory/audio/enhancer.py` integrating **DeepFilterNet3** (48kHz full-band real-time deep filtering).
- **Hypothesis / Failure Modes ("Kya fail ho sakta hai?")**:
  1. *Risk*: Clean voice ko over-process karke robotic ya muffled bana de.
  2. *Risk*: GPU memory spike on long sessions.
- **Safety Defense (Self-Healing Fallback)**:
  - 1. **Noise Threshold Gate**: Audio stem ka spectral crest factor calculate karo; agar audio already clean hai ($> 45\text{dB}$ SNR), toh neural enhancer bypass ho jata hai (Zero unnecessary processing).
  - 2. **Energy Difference Clamp**: Enhanced audio aur original audio ki RMS energy compare hoti hai. Agar difference $> 2.0\text{dB}$ ho, enhance cancel ho kar original stem use hota hai.

---

### Component 4: Reference Profile Matching (`reference_matcher.py`)
- **Real Problem in Current System**:
  Jab multiple chapters alag-alag din synthesize hote hain, toh character voices me minor acoustic coloration differences aa sakte hain.
- **Proposed Solution**:
  `audiobook_factory/audio/reference_matcher.py` wrapping **Matchering 2.0**.
  - Target chapter ko reference golden master (e.g. Chapter 1 master ya standard Audible profile) se match karke tonal & stereo consistency ensure karta hai.
- **Hypothesis / Failure Modes ("Kya fail ho sakta hai?")**:
  1. *Risk*: Reference me music ho ya bad EQ ho toh pure chapter ka audio kharab ho sakta hai.
- **Safety Defense (Self-Healing Fallback)**:
  - 1. Spectral matching gain curve ko strictly clamp kiya gaya hai: $\max \pm 3.0\text{dB}$ correction.
  - 2. Reference matching is **opt-in / scene-level**, enabled only when a verified `reference_master.wav` is declared in project configuration.

---

### Component 5: 64-bit M4B Packaging & Atom Metadata (`packager.py`)
- **Real Problem in Current System**:
  Standard MP4 containers 32-bit chunk offsets (`stco`) use karte hain jo $2\text{GB}$ ya 12+ ghante ke audiobooks par Apple Books / Android player me fail ho jaate hain.
- **Proposed Solution**:
  `audiobook_factory/audio/packager.py` with 64-bit MP4 chunk offsets (`co64`), dual QuickTime (`chpl`) + Nero chapter tracks, and lossless 3000x3000px artwork embedding via `mutagen`.
- **Hypothesis / Failure Modes**:
  1. *Risk*: Invalid chapter timestamp causing seek errors.
- **Safety Defense**:
  - `packager.py` enforces strictly monotonic TOC validation: Every chapter start time $T_{i+1} > T_i$, gap-free, with sample-accurate boundary alignment.

---

## 4. Phased Implementation Roadmap

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   4-PHASE IMPLEMENTATION ROADMAP                                │
├──────────────────────────┬──────────────────────────┬──────────────────────────┬────────────────┤
│ PHASE 1: FOUNDATION DSP  │ PHASE 2: AI QA AUDITOR   │ PHASE 3: NEURAL POLISH   │ PHASE 4: MCP   │
├──────────────────────────┼──────────────────────────┼──────────────────────────┼────────────────┤
│ • pedalboard + pyloudnorm│ • Silero VAD v5          │ • DeepFilterNet3         │ • mcp-audio-dsp│
│ • C++ Dynamic EQ & Comp  │ • WhisperX CTC Aligner   │ • Matchering 2.0 Ref     │ • mcp-audio-qa │
│ • True Peak Limiter      │ • TorchAudio-SQUIM MOS   │ • Formant Pitch Shifter  │ • Director Agent│
│ • FFmpeg Graceful Fallbk │ • Automated Gate 4 Audit │ • Selective Bypass Gate  │ • Autonomous QA│
└──────────────────────────┴──────────────────────────┴──────────────────────────┴────────────────┘
```

### Phase 1: Foundation DSP & Hybrid Engine (Immediate High ROI / Zero Risk)
- **Deliverables**:
  1. Create `audiobook_factory/audio/dsp.py` with `Pedalboard` + `Pyloudnorm` integration and transparent FFmpeg fallback.
  2. Upgrade `audiobook_factory/mastering_engine.py` to utilize `dsp.py` for dynamic EQ, optical compression, and `-1.5 dBTP` lookahead True Peak limiting.
  3. Update `requirements.txt` / `pyproject.toml` with optional DSP dependencies (`pedalboard`, `pyloudnorm`).
  4. Run full test suite to verify 100% backward compatibility and test passing.

### Phase 2: AI-Assisted Acoustic QA Auditor (Reliability Leap)
- **Deliverables**:
  1. Create `audiobook_factory/audio/qa_auditor.py` combining Silero VAD (pause/breath analysis) and WhisperX/Faster-Whisper (script alignment & dropout detection).
  2. Integrate QA Auditor into Gate 4 of `DialogueRunner` to auto-detect TTS glitches and trigger instant re-rolls.
  3. Add unit & integration tests (`tests/audio/test_qa_auditor.py`).

### Phase 3: Neural Vocal Polish & Reference Matching (Aesthetics & Consistency)
- **Deliverables**:
  1. Create `audiobook_factory/audio/enhancer.py` with DeepFilterNet3 integration, auto-bypass logic, and energy diff checks.
  2. Create `audiobook_factory/audio/reference_matcher.py` with Matchering 2.0 and $\pm 3\text{dB}$ spectral clamping.
  3. Add CLI flags (`--enable-neural-enhance`, `--reference-track <path>`).

### Phase 4: Antigravity MCP Suite & Agentic Directing (Full Autonomy)
- **Deliverables**:
  1. Package `mcp-audio-dsp` and `mcp-audio-qa` MCP servers.
  2. Equip the `audiobook-director` agent with direct tools to audition, inspect, and fine-tune mastering profiles per book genre.

---

## 5. Architectural Verdict & Recommendation

- **Verdict**: Proceed with **Phase 1** first. It delivers 80% of the audio mastering quality upgrade (C++ JUCE DSP, optical compression, true-peak lookahead limiting, and scientific EBU R128 loudness) with **ZERO risk** because the self-healing FFmpeg fallback ensures nothing can break existing pipelines.
- **Modularity**: All sub-modules stay cleanly inside `audiobook_factory/audio/` under strict Pydantic contracts, keeping the codebase clean, lean, and maintainable.
