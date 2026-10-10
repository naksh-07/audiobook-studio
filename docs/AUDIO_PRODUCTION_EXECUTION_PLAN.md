# 🚀 Master Execution Plan: Pure Vocals-Only Audio Mixing & Production System (v5.3)

**Canonical Project**: `audiobook-studio`  
**Target Branch**: `audio-mixing-and-production`  
**Execution Environment**: Termux Android ARM64 (Native Python 3.14.6) & High-Performance Workstation  
**Core Invariant**: 100% Pure Vocals-Only (Music & SFX permanently decoupled). Zero generation loss.

---

## 🗺️ Architectural Phase Roadmap Overview

To safely eliminate all 10 audited anti-patterns without breaking working workflows or causing mobile out-of-memory (OOM) crashes, implementation is divided into **6 surgical, test-driven phases**:

```text
Phase 1: Foundation & Ingestion
├── Strongly typed data contracts (SegmentAudioContract, ChapterMasterContract)
├── Tier A Ingestion Engine (RIFF/C2PA strip, 30Hz highpass, 48kHz stereo normalization)
└── Single 5.0ms Hann micro-taper invariant (Eradicating consonant swallow)
        │
        ▼
Phase 2: Streaming Pre-Master Composer
├── ChunkStreamComposer: Block-based streaming WAV writer (Zero RAM bloat)
├── Contextual syntax pause realization (180ms clause, 380ms sentence, 600ms turn)
└── Clean room-tone TPDF dither injection (Eliminating disk .silence_*.wav pollution)
        │
        ▼
Phase 3: Mastering Engine Unification & True Peak Headroom Fix
├── Retire legacy procedural mastering.py runtime path
├── Connect orchestrator.py & dialogue_runner.py to MasteringEngineV2
└── Pin PCM limiter ceiling to -2.0 dBFS with asc=0 (Absorbing AAC peak regrowth <= -1.5 dBTP)
        │
        ▼
Phase 4: Single-Pass Chapter AAC Delivery & Lossless M4B Packaging
├── ChapterDeliveryEncoder: Single-pass 192k AAC (-flags +global_header)
├── M4BBookPackager: Lossless stream copy (-c:a copy) assembly
└── Exact packet timescale chapter markers (Zero TOC navigation desync)
        │
        ▼
Phase 5: Incremental DAG Caching & Single-Chunk Hot-Patching
├── Segment cryptographic hash ledgering (sha256(text + voice + calibration))
├── 1-segment hot-patching (Regenerating 1 chunk avoids 100% chapter re-master)
└── Thread-isolated scratch space & certified janitor retention shield
        │
        ▼
Phase 6: End-to-End Orchestrator Integration & Golden Certification
├── CLI commands update (master, package)
├── Full chapter synthetic verification through all 4 Quality Gates
└── Final sign-off & git commit ready for workstation sync
```

---

## 📋 Phase 1: Foundation, Contracts & Tier A Ingestion

### Objectives:
1. Define the formal, immutable handoff schema between TTS and Audio Production.
2. Build `AudioIngestionManager` to normalize every chunk to **48,000 Hz 24-bit stereo** immediately upon arrival, preventing the concat demuxer chipmunk audio bug (AP-03).
3. Implement the **Single 5.0ms Raised-Cosine Hann Micro-Taper** rule, eradicating plosive consonant swallow (AP-06).

### Tasks & Deliverables:
- [x] **1.1 Create Schema Contracts**:  
  `audiobook_factory/audio/contracts.py`:
  - `SegmentAudioContract` (Immutable segment data from TTS).
  - `ChapterMasterContract` (Chapter master metrics and artifact pointers).
  - `BookPackagingContract` (Full book TOC and container specifications).
- [x] **1.2 Create Ingestion Engine**:  
  `audiobook_factory/audio/ingestion.py`:
  - `AudioIngestionManager.ingest_segment()`: Demuxes container, strips C2PA metadata static, applies 30Hz highpass, resamples to 48kHz, normalizes to stereo, applies single 5.0ms Hann taper.
  - Strict zero-sample boundary pinning: `sample[0] = 0.0` and `sample[-1] = 0.0`.
- [x] **1.3 Unit Test Suite**:  
  `tests/audio/test_audio_ingestion.py`:
  - Test C2PA watermark elimination.
  - Test 5.0ms micro-taper preserves plosives (*p, t, k*) while eliminating Dirac step clicks.
  - Test 24kHz mono $\to$ 48kHz stereo normalization.

### Verification Gate 1:
```bash
pytest tests/audio/test_audio_ingestion.py -v
```
*Acceptance Criteria: 100% tests pass; all ingested chunks strictly have 48000 Hz, 2 channels, and 0.0 boundary samples.*

---

## 📋 Phase 2: Streaming Pre-Master Composer & Editorial Integration

### Objectives:
1. Eradicate temporary on-disk `.silence_*.wav` files that pollute `mastered/` (AP-05).
2. Eradicate RAM memory explosions on mobile Termux by replacing in-memory NumPy concatenations with a block-based streaming WAV writer.
3. Realize the syntax- and character-calibrated pause hierarchy (180ms clause, 380ms sentence, 600ms turn).

### Tasks & Deliverables:
- [x] **2.1 Build Streaming Composer**:  
  `audiobook_factory/audio/stream_composer.py`:
  - `ChunkStreamComposer`: Streams audio chunks in 10-second ring buffers (800 KB RAM) directly into an uncompressed pre-master file (`premaster.wav`) in isolated scratch storage.
  - Generates zero-mean TPDF room-tone dither ($-72\text{ dBFS}$) in-stream for deliberate dramatic pauses ($\ge 350\text{ ms}$).
  - Leaves micro-pauses ($< 150\text{ ms}$) clean with natural phoneme decay tails.
- [x] **2.2 Dialogue Editorial Layer Integration**:  
  `audiobook_factory/audio/editorial.py`:
  - Bridge with existing `DialogueEditor` (from `audiobook_factory/dialogue_editing/`).
  - Read `DialogueEditPlan` to execute endpoint dead-air clamping (head $\le 80$ms, tail $\le 120$ms), gentle breath attenuation ($-6$ dB), and inter-take leveling ($\pm 1.8$ dB).
- [x] **2.3 Unit Test Suite**:  
  `tests/audio/test_stream_composer.py`:
  - Test streaming 100 segments with zero RAM accumulation.
  - Verify syntax pause durations in milliseconds.
  - Verify zero scratch `.silence_*.wav` files created on disk.

### Verification Gate 2:
```bash
pytest tests/audio/test_stream_composer.py -v
```
*Acceptance Criteria: 100% tests pass; continuous 48kHz 24-bit premaster.wav generated with sample-accurate pause lengths.*

---

## 📋 Phase 3: Runtime Mastering Engine Unification & True Peak Headroom Fix

### Objectives:
1. End the "Dual-Engine Schism" (AP-01): Route runtime chapter production in `orchestrator.py` and `dialogue_runner.py` through the contract-hardened `MasteringEngineV2`.
2. Fix the True Peak overshoot defect (AP-02): Pin the mastering brickwall limiter ceiling to **$-2.0\text{ dBFS}$** (`asc=0`) to absorb lossy AAC peak regrowth and guarantee final deliverables stay $\le -1.5\text{ dBTP}$.
3. Ban dynamic loudnorm fallback during dramatic pauses (AP-08).

### Tasks & Deliverables:
- [x] **3.1 Calibrate MasteringEngineV2 Ceiling**:  
  Update `audiobook_factory/mastering_contracts.py` & `audiobook_factory/mastering_engine.py`:
  - Default limiter limit: `limit=-2.0dB:attack=3:release=40:asc=0:level=0`.
  - Measured linear mode strictly enforced (raise error or use static RMS leveling if Pass 1 $I < -60$ LUFS, banning dynamic pumping).
- [x] **3.2 Update Dialogue Runner**:  
  `audiobook_factory/orchestration/dialogue_runner.py`:
  - Replace legacy `concatenate_and_master_chapter()` call with `MasteringEngineV2.master_chapter()`.
  - Emit formal `MasteringLedger` with cryptographic file hashes.
- [x] **3.3 Update Orchestrator Wiring**:  
  `audiobook_factory/orchestrator.py`:
  - Connect chapter mastering to unified `MasteringEngineV2` workflow.
- [x] **3.4 Regression Test Suite**:  
  Run all existing mastering tests:
  - `tests/test_mastering_engine.py`
  - `tests/test_mastering_closed_loop.py`
  - `tests/test_golden_mastering_regression.py`

### Verification Gate 3:
```bash
pytest tests/test_mastering_engine.py tests/test_mastering_closed_loop.py tests/test_golden_mastering_regression.py -v
```
*Acceptance Criteria: All 16 mastering tests pass; mastered PCM WAV conforms to -19.0 LUFS ±0.5 LU and -2.0 dBFS ceiling.*

---

## 📋 Phase 4: Single-Pass Chapter Delivery & Lossless M4B Stream Copy

### Objectives:
1. Eradicate redundant lossy re-encoding loops (AP-04).
2. Implement `ChapterDeliveryEncoder` for single-pass 192k AAC encoding with post-encode True Peak verification ($\le -1.5\text{ dBTP}$).
3. Implement `M4BBookPackager` for 100% lossless container assembly (`-c:a copy`) with monotonic `FFMETADATA1` chapter markers (AP-10).

### Tasks & Deliverables:
- [x] **4.1 Chapter Delivery AAC Encoder**:  
  `audiobook_factory/audio/encoder.py`:
  - `ChapterDeliveryEncoder.encode_chapter_m4a()`: Encodes uncompressed master WAV to 192k AAC-LC with `-profile:a aac_low -flags +global_header`.
  - Runs post-encode `ffprobe / ebur128` True Peak check. If True Peak $> -1.5\text{ dBTP}$, applies a closed-loop $-0.3$ dB gain trim and re-encodes.
- [x] **4.2 Lossless M4B Packager**:  
  `audiobook_factory/audio/packager.py`:
  - `M4BBookPackager.package_audiobook()`:
    - Generates strictly monotonic `FFMETADATA1` file ($\text{START}_k = \text{END}_{k-1}$).
    - Runs FFmpeg with `-c:a copy` (Zero transcode!).
    - Embeds cover art and moves index to beginning with `+faststart`.
  - Update `audiobook_factory/packager.py` facade to delegate to this packager.
- [x] **4.3 Unit & Integration Test Suite**:  
  `tests/audio/test_book_packager.py`:
  - Verify stream copy executes in $< 5$ seconds without re-encoding.
  - Verify chapter markers open cleanly and accurately in standard audiobook players.

### Verification Gate 4:
```bash
pytest tests/audio/test_book_packager.py tests/test_audit_remediation_sprint.py -v
```
*Acceptance Criteria: 100% tests pass; chapter M4A has True Peak <= -1.5 dBTP; final M4B assembled with stream copy.*

---

## 📋 Phase 5: Incremental DAG Caching, Hot-Patching & Janitor Shield

### Objectives:
1. Support single-segment hot-patching: If 1 chunk is regenerated, avoid re-rendering the entire chapter from scratch (AP-07).
2. Isolate concurrency scratch buffers to prevent file locking collisions (AP-09).
3. Protect certified masters while purging intermediate scratch files.

### Tasks & Deliverables:
- [x] **5.1 Segment Hash Ledgering**:  
  `audiobook_factory/audio/ledger.py`:
  - Store segment artifact metadata: `sha256(text + speaker + voice + calibration)`.
  - Detect diffs during chapter build: only process changed or missing segments.
- [x] **5.2 Single-Segment Hot-Patch Engine**:  
  `audiobook_factory/audio/hot_patcher.py`:
  - Splice regenerated segment directly into existing pre-master timeline.
- [x] **5.3 Janitor Shield Enforcement**:  
  `audiobook_factory/orchestration/janitor.py`:
  - Protect `chapter_XXX_master.wav` and `chapter_XXX.m4a` until Gate 6 certifies book.
  - Clean temporary scratch files (`scratch_{run_id}_{chapter_num}/`).
- [x] **5.4 Unit Test Suite**:  
  `tests/audio/test_hot_patch_recovery.py`:
  - Verify modifying 1 segment triggers only single-segment re-processing.

### Verification Gate 5:
```bash
pytest tests/audio/test_hot_patch_recovery.py -v
```
*Acceptance Criteria: Hot-patch test passes; unchanged segments are reused from cache.*

---

## 📋 Phase 6: End-to-End Orchestrator Integration & Golden Production Pilot

### Objectives:
1. Update CLI commands (`master`, `package`) to use the new unified `audio/` subsystem.
2. Run a full end-to-end synthetic chapter production test in Native Termux ARM64.
3. Validate all 4 Quality Gates (Technical, Structural, Forensic Audio, Listener Experience).

### Tasks & Deliverables:
- [x] **6.1 CLI Commands Wiring**:  
  Update `audiobook_factory/cli/commands/pipeline.py` & `audio.py`:
  - `cmd_master`: use unified `MasteringEngineV2`.
  - `cmd_package`: use lossless `M4BBookPackager`.
- [x] **6.2 Full End-to-End Pilot Test**:  
  `tests/test_audio_production_e2e_pilot.py`:
  - Synthesizes 5 dialogue segments (different speakers, emotional states).
  - Runs Ingestion $\to$ Editorial $\to$ Pre-Master $\to$ Master WAV $\to$ AAC M4A $\to$ M4B.
  - Verifies Gate 5.0 ($-19.0\text{ LUFS} \pm 0.5$, $\text{TP} \le -1.5\text{ dBTP}$).
  - Verifies Gate 6 (TOC Monotonicity, Cover Art, Stream Copy).
- [x] **6.3 Memory & Telemetry Finalization**:  
  - Update `activeContext.md` to record completion.
  - Log run telemetry into `session_logs`.

### Verification Gate 6:
```bash
pytest tests/test_audio_production_e2e_pilot.py -v
```
*Acceptance Criteria: End-to-end pilot passes with 100% compliance with EBU R128 and Audible broadcast specs.*

---

## 🛡️ Risk Management & Rollback Matrix

| Risk Scenario | Probability | Impact | Mitigation / Rollback Strategy |
|---|:---:|:---:|---|
| **FFmpeg AAC True Peak Regrowth exceeds -1.5 dBTP** | Low | Medium | Automatic closed-loop -0.3 dB gain trim implemented in Phase 4 encoder before delivery. |
| **Mobile Termux OOM during Concatenation** | Medium | High | Streaming block-based writer (Phase 2) caps memory consumption to 800 KB regardless of chapter duration. |
| **Existing tests break due to interface change** | Medium | High | Phase 3 preserves backwards-compatible facade functions (`concatenate_and_master_chapter`) wrapping `MasteringEngineV2`. |
| **AAC packet timestamp rounding in player** | Low | Low | `-flags +global_header` and millisecond timescale in `FFMETADATA1` enforce seamless chapter transitions. |

---

## ⏱️ Estimated Execution Timeline

- **Phase 1 (Foundation & Ingestion)**: ~1 work session
- **Phase 2 (Streaming Pre-Master)**: ~1 work session
- **Phase 3 (Mastering Engine Unification)**: ~1 work session
- **Phase 4 (Chapter AAC & Lossless M4B)**: ~1 work session
- **Phase 5 (DAG Caching & Hot-Patching)**: ~1 work session
- **Phase 6 (E2E Pilot & Sign-off)**: ~1 work session

*Total: 6 Focused, Surgical Sprints.*
