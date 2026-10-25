# Local Agent Guidelines & Context

- **Canonical Project ID**: proj-audiobook-studio
- **Plugin Name**: audiobook-studio
- **Global Config**: Inherits [Global AGENTS.md](file:///C:/Users/Suraj/.gemini/config/AGENTS.md)

## System Freeze & Touch Guard (Certified Stable)
- **FROZEN SYSTEMS (STRICT TOUCH BAN)**:
  - **Room 1**: Forensic Ingestion, Extraction & Pre-Production (`audiobook_factory/extraction/`, `audiobook_factory/pdf/`, `preproduction/`).
  - **Room 2**: Translation Collective & Glossary (`audiobook_factory/translation/`, `glossary/`).
  - **Room 3**: Screenplay Dramaturgy & Anti-Swap Attribution (`audiobook_factory/script/`, `character_caster.py`, `dramaturgy/`).
  - **Room 4**: TTS Platform Core, Heuristic Directing, Gemini Flash Expressive Synthesis & Dialogue Editorial (`audiobook_factory/tts/`, `multi_cast_client.py`).
  > [!IMPORTANT]
  > Agents MUST NOT modify, refactor, or re-engineer code in Rooms 1, 2, 3, or 4. These systems are certified stable and 100% green.
- **ACTIVE OPERATIONAL SCOPE**:
  - **Room 5 ONLY**: Broadcast Vocal Audio Mastering & M4B Packaging (`audiobook_factory/mastering_engine.py`, `mastering_contracts.py`, `audio/dsp.py`).

## Domain Context: Studio Audiobook Production Engine (Pure Vocals-Only)
- **Core Architecture**: 5-Room Pure Vocals-Only Pipeline (`SOURCE -> EXTRACTION -> PRE-PRODUCTION (Room 1) -> TRANSLATION COLLECTIVE (Room 2) -> SCREENPLAY & ANTI-SWAP ATTRIBUTION (Room 3) -> 4D FORMANT MULTI-VOICE TTS & EDITORIAL (Room 4) -> BROADCAST VOCAL MASTERING & M4B PACKAGING (Room 5)`).
- **Vocals-Only Architectural Invariant**: Background music (BGM), sound effects (SFX), Archive.org sound bank scraping, and 5-track multitrack mixdowns are **STRICTLY PROHIBITED AND DECOUPLED** on this branch. Production is 100% focused on Audible-standard vocal excellence, character acting, dialogue nuance, and pristine narration.
- **Vocal & Directing Stack**:
  1. Google Gemini Flash TTS (120+ active API keys, SQLite round-robin pool, token-bucket concurrency).
  2. 4D Acoustic Formants: Phase-safe 2nd-order biquad parametric EQ curves (`FormantSculptor`) without destructive resampling pitch/time warping.
  3. Room 3 Anti-Swap `DialogueAttributionAuditor` ensuring 0% speaker turn inversion ($A \leftrightarrow B$).
  4. Room 2 Translation Collective with Dual-Rule Invariant (`CLASSIC_REVERENT` dignity vs `RAW_UNRATED` visceral combat gore & intimacy).
  5. Dialogue Editorial Layer with Hann micro-fades (12ms/18ms), dynamic punctuation-aware latencies, and -62 dBFS shaped comfort room tone.
  6. Room 5 Multi-Dimensional Dialogue Mastering Engine (ADR-036): Dynamic stem conditioning across 9 vocal registers and 6 delivery intensities, preserving female narration (Aoede) melody, vowel shimmer, and souz while delivering punchy baritone presence; decoupled EBU R128 (-19.0 LUFS, -1.5 dBTP) broadcast master bus and chaptered `.m4b` container with embedded cover art.
- **Universal Novel-Agnostic Invariant**: The factory core (`audiobook_factory`, CLI, quality gates, translation engines) MUST NEVER contain hardcoded novel titles, franchise lore, character rosters, file hashes, or era biases.
- **Environment**: High-performance Windows 11 workstation with CUDA acceleration.
- **Active Memory**: Project memory bank in `.agents/memory/` (`activeContext.md` $\le$ 50 lines).
