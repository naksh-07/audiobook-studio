# Design System: Audiobook Studio UI Extension

- **Canonical Project ID**: `proj-audiobook-studio`
- **Subsystem**: `sidecars/studio-panel` & Antigravity IDE UI Extension
- **Target Aesthetic**: Apple Human Interface Guidelines (macOS Sonoma / Tahoe Minimalist Light Workstation)
- **Standard**: Google Stitch Semantic Design System v2.0

---

## 1. Visual Theme & Atmosphere

A refined, distraction-free audio engineering workstation inspired by Apple pro applications (Logic Pro, Final Cut Pro, Apple Music) rendered in a calm, modern light aesthetic.

The atmosphere is clean, tactile, and highly functional — like an illuminated acoustic mastering suite. It eliminates visual fatigue through a warm neutral backdrop, frosted acrylic translucency, crisp hairline structural boundaries, and typography modeled after San Francisco Pro.

- **Density**: 6 / 10 (Balanced Studio Workstation — high information legibility without cramped clutter)
- **Variance**: 5 / 10 (Structured asymmetry — prominent audio hero with docked voice roster and telemetry inspector)
- **Motion**: 6 / 10 (Apple fluid spring physics with hardware-accelerated 120 FPS canvas playback)

---

## 2. Color Palette & Roles

- **Canvas Mist** (`#F5F5F7`) — Primary window background surface (warm macOS light neutral base).
- **Pure Acrylic** (`#FFFFFF` with 82% opacity) — Floating card and panel fill, layered over canvas.
- **Deep Graphite** (`#1D1D1F`) — Primary text, headings, and high-contrast control glyphs.
- **Muted Stone** (`#86868B`) — Secondary text, chapter labels, inactive icons, and metadata descriptions.
- **Whisper Hairline** (`rgba(0, 0, 0, 0.08)`) — 1px / 0.5px structural container borders and section dividers.
- **Whisper Hairline Strong** (`rgba(0, 0, 0, 0.14)`) — Active input borders, focused boundaries, and hovered cards.
- **Inner Glass Specular** (`inset 0 1px 0 rgba(255, 255, 255, 0.90)`) — Top specular highlight on frosted cards simulating glass thickness.
- **Studio Amber** (`#FF9500`) — Primary acoustic accent: waveform scrub bar, pitch delta tags, -19.0 LUFS target gauge.
- **Apple Emerald** (`#34C759`) — System health indicator: 124+ Gemini keys healthy, Doctor diagnostics nominal.
- **Apple Azure** (`#007AFF`) — Primary call-to-action buttons, active tab indicators, and selection highlights.
- **Crimson Warning** (`#FF3B30`) — Error states, throttled API key signals, and clipping alerts.

*(Strict Constraint: Maximum 1 primary functional accent per component. Saturation strictly kept below 80%. AI neon purple/blue glows are permanently BANNED.)*

---

## 3. Typography Rules

- **Display & Section Titles**: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`
  - Track-tight letter-spacing (`-0.015em`), medium/semibold weights (`font-weight: 600`), scale-controlled hierarchy. Never shouting.
- **Body & Controls**: `-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif`
  - Crisp readability, relaxed leading (`line-height: 1.45`), 65ch maximum width for dialogue preview.
- **Audio Telemetry & Monospace**: `"SF Mono", "JetBrains Mono", ui-monospace, Menlo, monospace`
  - Used for all numerical readouts: loudness levels (`-19.0 LUFS`), true peak (`-1.5 dBTP`), segment IDs, timecode duration (`04:12 / 18:24`), and key pool metrics (`124 Keys Active`).
- **Typography Bans**:
  - `Inter` is strictly BANNED (per taste directives).
  - Generic serif fonts (`Times New Roman`, `Georgia`, `Garamond`) are strictly BANNED in software interfaces.
  - Uppercase yelling on buttons or headings is BANNED.

---

## 4. Component Stylings

### 4.1 Sliding Segmented Controls (macOS Signature)
- Container: Rounded capsule pill (`border-radius: 9999px`), subtle recessed background (`rgba(0, 0, 0, 0.05)`), 2px internal padding.
- Active Indicator: Sliding solid white pill (`background: #FFFFFF`), subtle diffused drop shadow (`0 1px 3px rgba(0, 0, 0, 0.10)`), smooth spring slide animation.

### 4.2 Frosted Acrylic Cards
- Translucent backdrop: `backdrop-filter: blur(24px) saturate(190%)` paired with `background: rgba(255, 255, 255, 0.82)`.
- Border: `1px solid rgba(0, 0, 0, 0.08)` with inner highlight `box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.90)`.
- Border Radius: Generously rounded (`14px` for panels, `10px` for nested cards).

### 4.3 Tactile Cupertino Push Buttons
- Primary Action: Apple Azure (`#007AFF`) or Studio Amber (`#FF9500`) fill with crisp white text.
- Secondary / Ghost Action: Translucent background (`rgba(0, 0, 0, 0.04)`), hairline border, Deep Graphite text.
- Interaction Feedback: Tactile micro-compression (`transform: scale(0.97)`) on `:active` with smooth spring recovery (`transition: all 0.16s cubic-bezier(0.16, 1, 0.3, 1)`). No neon outer glow.

### 4.4 120 FPS Waveform Canvas Player
- Canvas Container: Recessed acoustic tray with subtle hairline stroke.
- Waveform Bars: Pre-computed double-buffered vertical bars with rounded caps (`roundRect`). Inactive bars in `rgba(0, 0, 0, 0.12)`, played bars filled with Studio Amber (`#FF9500`).
- Scrub Cursor: 1.5px vertical line with smooth head position tracking via `requestAnimationFrame`. Zero memory leaks.

### 4.5 5-Room Topological DAG Stepper
- Horizontal progress ribbon across the top of the interface.
- Distinct status pills for each pipeline room:
  - Room 1: Forensic Ingest (Complete)
  - Room 2: Translation Collective (Complete)
  - Room 3: Dramaturgy & Anti-Swap (Complete)
  - Room 4: 4D Formant Multi-Voice TTS (In Progress / Active)
  - Room 5: Broadcast Vocal Mastering (Ready)
- Active room features a subtle pulsing status dot (`#FF9500` or `#34C759`).

### 4.6 Multi-Cast Character Voice Roster
- Individual cards for each dramatic character:
  - Character Name & Dramatic Role (e.g. Lead Narrator, Geralt, Yennefer).
  - Assigned Base Voice profile badge (Puck, Fenrir, Aoede, Kore).
  - 4D Formant pitch offset indicator (`+4.0%`, `-6.0%`).
  - Tactile "Audition" button triggering sample preview.

---

## 5. Layout Principles

- **Header Bar**: Top identity bar with project dropdown selector, Gemini Key Pool indicator (`124 Keys Active`), and Doctor diagnostics pill.
- **Top Ribbon**: 5-Room Topological DAG Stepper showing pipeline stage status.
- **Main Workspace Split**:
  - **Left Section (Audio Workstation)**: Chapter playback hero, interactive 120 FPS waveform scrubber, EBU R128 (-19.0 LUFS) vocal loudness gauge, and transport controls.
  - **Right Section (Voice Roster & Soundboard)**: Multi-cast character list with voice assignment chips, pitch offsets, and instant audition playback.
- **Bottom Section (Dialogue Editorial Inspector)**: Segment review card with Devanagari Hindustani prose preview, speaker attribution tags, and Hann micro-fade indicators (12ms/18ms).
- **Responsive Constraints**:
  - Container width fluidly adapts to Antigravity side pane widths (`340px` up to `900px+`).
  - Below `640px`, the 2-column workspace seamlessly stacks into a clean single-column vertical flow with zero horizontal scrolling.

---

## 6. Motion & Interaction

- **Spring Physics**: All interactive elements utilize Apple's fluid spring curve: `cubic-bezier(0.16, 1, 0.3, 1)`.
- **Perpetual Micro-Interactions**: Active synthesis and key lease states feature a gentle, infinite micro-pulse on status beacons (`animation: pulse 2.4s ease-in-out infinite`).
- **Hardware Acceleration**: Animations strictly operate on `transform` and `opacity` to maintain 60–120 FPS without reflow penalties.

---

## 7. Anti-Patterns (Strictly Forbidden)

- **NO Emojis**: Interface must use clean, professional SVGs (SF Symbols / Feather style), never raw emojis.
- **NO `Inter` Font**: Use native system SF Pro or Geist stacks.
- **NO Pure Black (`#000000`)**: Use Deep Graphite (`#1D1D1F`).
- **NO Neon/Glow Effects**: No purple or blue neon glows around cards or buttons.
- **NO Fabricated Data / Fake Stats**: Do not invent fake metrics (like "99.9% Uptime" or "142ms Latency"). Display only verified, real engine data (e.g. 124 active keys, -19.0 LUFS target).
- **NO AI Copywriting Clichés**: Words like "Elevate", "Next-Gen", "Seamlessly Unleash" are banned. Use direct audio terminology (e.g. "Mastering", "Formant Modulation", "Attribution Audit").
- **NO 3-Column Equal Grids**: Use structured asymmetric hierarchy.
