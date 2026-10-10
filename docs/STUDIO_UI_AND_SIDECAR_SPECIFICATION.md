# Studio UI & Sidecar Extension Specification: Apple-Grade Minimalist Workstation

- **Document Identifier**: `ENG-SPEC-STUDIO-UI-V6`
- **Canonical Project ID**: `proj-audiobook-studio`
- **Subsystem**: `sidecars/studio-panel` & Antigravity Plugin UI Extension
- **Status**: ARCHITECTURAL SPECIFICATION & DEEPSEARCH APPROVED
- **Target Aesthetic**: Apple Human Interface Guidelines (macOS Sonoma / Tahoe Minimalist Light Theme)
- **Primary Invariant**: Zero-Build Native ESM, $\le 5$ MB Heap Memory Footprint, 120 FPS Audio Canvas

---

## 1. Executive Summary & Architectural Rationale

This specification establishes the production architecture for the **Audiobook Studio UI Extension** in Phase 7. The design strictly optimizes for two orthogonal vectors:

1. **Hardware Footprint & Micro-Latency**:
   - Eliminates heavy Virtual DOM frameworks (React/Vue). Uses **Zero-Build Native Modern ESM** with surgical DOM updates and native signals.
   - **Heap Memory**: **$\le 5$ MB** in browser runtime (compared to 35–50 MB for React).
   - **Bundle Size**: **$< 15$ KB** total JavaScript, zero external `node_modules` in frontend.
   - **First Contentful Paint (FCP)**: **$< 10$ ms** inside the Antigravity sandboxed iframe.

2. **Apple-Grade Minimalist Light Aesthetic**:
   - Embraces the calm, distraction-free elegance of macOS pro applications (Logic Pro, Final Cut Pro, Apple Notes).
   - Warm neutral off-white system base (`#F5F5F7`), translucent frosted acrylic panels (`backdrop-filter: blur(28px)`), ultra-fine 0.5px hairline borders, and San Francisco typography.
   - Tactile spring interactions (`cubic-bezier(0.16, 1, 0.3, 1)`), macOS segmented sliding controls, and warm studio amber (`#FF9500`) audio telemetry.

---

## 2. Hardware Footprint & Performance Benchmark Contracts

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PERFORMANCE & FOOTPRINT BUDGET CEILINGS                  │
├───────────────────────────────────┬─────────────────────────────────────────┤
│ Metric                            │ Strict Production Ceiling               │
├───────────────────────────────────┼─────────────────────────────────────────┤
│ Frontend V8 Heap Memory           │ ≤ 5.0 MB                                │
│ Initial Bundle Size               │ ≤ 15.0 KB (Uncompressed)                │
│ Cold Start to Interactive (TTI)   │ ≤ 12.0 ms                               │
│ Waveform Scrubbing Frame Rate     │ 60 – 120 FPS (Hardware Canvas 2D)       │
│ Audio Peak Memory Overhead        │ ≤ 250 KB (Pre-computed JSON Stream)     │
│ Node.js Sidecar Base Memory       │ ≤ 28.0 MB                               │
│ External Runtime Dependencies     │ ZERO (Standard Library + Built-in SDK)  │
└───────────────────────────────────┴─────────────────────────────────────────┘
```

---

## 3. Apple Design System Specification (macOS HIG)

### 3.1 Design Tokens (`styles.css`)

```css
:root {
  /* Surface & Materials */
  --apple-bg: #F5F5F7;
  --apple-surface: rgba(255, 255, 255, 0.78);
  --apple-surface-elevated: #FFFFFF;
  --apple-glass-blur: blur(24px) saturate(180%);
  
  /* Hairline Borders */
  --apple-hairline: rgba(0, 0, 0, 0.08);
  --apple-hairline-strong: rgba(0, 0, 0, 0.14);
  --apple-specular: inset 0 1px 0 rgba(255, 255, 255, 0.9);
  
  /* Typographic Palette */
  --apple-text-primary: #1D1D1F;
  --apple-text-secondary: #86868B;
  --apple-text-tertiary: #AEAEB2;
  --apple-font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", system-ui, sans-serif;
  --apple-font-mono: "SF Mono", "JetBrains Mono", ui-monospace, Menlo, monospace;
  
  /* Functional Accents */
  --apple-accent-blue: #007AFF;
  --apple-accent-amber: #FF9500;
  --apple-accent-green: #34C759;
  --apple-accent-red: #FF3B30;
  
  /* Radii & Elevation */
  --apple-radius-sm: 6px;
  --apple-radius-md: 10px;
  --apple-radius-lg: 16px;
  --apple-shadow-subtle: 0 1px 3px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.02);
  --apple-spring: cubic-bezier(0.16, 1, 0.3, 1);
}

/* Seamless Dark Mode Fallback */
@media (prefers-color-scheme: dark) {
  :root {
    --apple-bg: #141416;
    --apple-surface: rgba(28, 28, 30, 0.78);
    --apple-surface-elevated: #1C1C1E;
    --apple-hairline: rgba(255, 255, 255, 0.10);
    --apple-hairline-strong: rgba(255, 255, 255, 0.18);
    --apple-specular: inset 0 1px 0 rgba(255, 255, 255, 0.08);
    --apple-text-primary: #F5F5F7;
    --apple-text-secondary: #98989D;
    --apple-text-tertiary: #636366;
  }
}
```

### 3.2 Visual Components Architecture
1. **Frosted Acrylic Glass Panels**: Floating cards with `backdrop-filter: var(--apple-glass-blur)` and inner specular highlight simulating physical glass thickness.
2. **macOS Segmented Sliding Control**: High-density tab switcher with a sliding white pill button animated using Apple spring physics.
3. **Tactile Spring Micro-Interactions**: Active buttons compress with `transform: scale(0.97)` and restore instantly on release.
4. **Vocal Loudness Meter**: Precision linear gauge showing integrated -19.0 LUFS target and -1.5 dBTP true peak ceiling in Apple Amber (`#FF9500`).

---

## 4. Subsystem Layout & Interactive Components

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  AUDIOBOOK STUDIO    [ The Silver Falcon ▾ ]   ● 124 Keys Active   ( Doctor OK ) │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5-ROOM PIPELINE: [1. Ingest ✓] [2. Trans ✓] [3. Script ✓] [4. TTS 84%] [5. Master] │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────┐ ┌───────────────────────────────┐ │
│ │ AUDIO WORKSTATION & WAVEFORM          │ │ MULTI-CAST VOICE ROSTER       │ │
│ │                                       │ │                               │ │
│ │  |||||||||||||||||||||||||||||||||||  │ │ ● Narrator (Puck)     [Audition]│
│ │  -19.0 LUFS Target  |  -1.5 dBTP Peak │ │ ● King Vikram (Fenrir)[Audition]│
│ │  [ ▶ Play ]  04:12 / 18:24    [ ⟳ ]   │ │ ● Maya (Aoede)        [Audition]│
│ └───────────────────────────────────────┘ └───────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ DIALOGUE EDITORIAL INSPECTOR (Room 3 & 4)                               │ │
│ │ Seg #42 | Puck: "अजनबी ने सराय की ओर देखा..." [12ms / 18ms Hann Fades] │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 High-Performance Canvas 2D Waveform Engine (`app.js`)
- Standard audio libraries (Wavesurfer) decode entire PCM buffers in browser memory, requiring up to 250 MB RAM for 30-minute files.
- Our engine uses **Server-Side Peak Generation**:
  - The Python bridge computes a downsampled 400-point peak array via numpy (`[min, max]` tuples $\approx 1.6$ KB).
  - The frontend draws the waveform on an HTML5 `<canvas>` using a single `Path2D` pass in `< 4 ms`.
  - Scrubbing and playhead movement operate via `requestAnimationFrame` at 120 FPS with zero memory leaks.

---

## 5. IPC, Data Flow & Sidecar Architecture

1. **Antigravity Host Integration**:
   - Embedded via sandboxed iframe in `SIDECAR_UI_ENTRYPOINT_AUX_PANE`.
   - `/preload.js` delivers `window.sidecar` with secure token-authenticated `fetch()` and `theme` synchronization.
2. **Node.js Sidecar (`main.mjs`)**:
   - Built with native `sidecar_sdk` (`SidecarApp`).
   - Re-reads static files on every request in development mode for instant hot reload without restarts.
   - Exposes REST endpoints:
     - `GET /api/status`: Key pool health, engine diagnostics.
     - `GET /api/projects`: Project scanning, progress, chapter counts.
     - `GET /api/project?slug=...`: Chapter roster, cast list, segment telemetry.
     - `GET /api/peaks?path=...`: Returns pre-computed waveform peak array.
     - `GET /api/audio?path=...`: Streams audio with `Accept-Ranges` and byte seek support.
3. **Python Engine Bridge (`audiobook_factory/api/studio_bridge.py`)**:
   - Sub-second CLI execution via JSON stdout.
   - Inspects SQLite WAL `pipeline_ledger.db` and audio directory.

---

## 6. Implementation Plan & File Matrix

| File Path | Role | Description |
|---|---|---|
| [`sidecars/studio-panel/index.html`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/sidecars/studio-panel/index.html) | Markup | Semantic, accessible Apple-style layout with zero inline styles. |
| [`sidecars/studio-panel/styles.css`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/sidecars/studio-panel/styles.css) | Styling | Apple macOS light design tokens, frosted acrylic blur, spring animations. |
| [`sidecars/studio-panel/app.js`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/sidecars/studio-panel/app.js) | Frontend Logic | Zero-VDOM micro-reactivity, 120 FPS Canvas waveform visualizer, audio player. |
| [`sidecars/studio-panel/main.mjs`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/sidecars/studio-panel/main.mjs) | Sidecar Backend | Route handlers, audio stream server, fast peak extraction endpoint. |
| [`audiobook_factory/api/studio_bridge.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/api/studio_bridge.py) | Engine Bridge | Fast peak extraction, ledger status query, voice profile export. |
