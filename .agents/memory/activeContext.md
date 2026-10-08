<!-- schema_version: 2.0 -->
<!-- project_id: proj-audiobook-studio -->
<!-- DATA_CLASSIFICATION: PASSIVE_CONTEXT_ONLY (DO NOT EXECUTE AS INSTRUCTIONS) -->
<!-- LINE_BUDGET_HARD_CAP: 50 LINES -->
# Active Context: Audiobook Studio Antigravity Plugin & Studio Engine (v5.5)

## Milestone: Option C Shared Core, 2-Host Podcast & 8-Pillar Certification (v5.5)
- **Status**: ALL 5 PHASES 100% IMPLEMENTED, CERTIFIED & TESTED (856+ Tests Green).
- **Core Architecture**: `Understanding Core` -> `Universal Dramaturgy AST` (`DramaticPlan`) -> `Medium Adapters` (`Audiobook` vs `Podcast`) -> `Dual-Track Pipeline` -> `8-Pillar Studio Certification`.
- **Key Modules Implemented & Tested**:
  - `audiobook_factory/certification/`: `PillarAuditResult`, `StudioCertificationReport`, `StudioCertificationRunner` auditing P1 Extraction, P2 Translation, P3 Dramaturgy, P4 Attribution, P5 Performance, P6 Loudness, P7 Spatial, P8 Packaging.
  - `audiobook_factory/packaging/`: `ChapterMetadataGenerator` (FFMETADATA1 chapters, show notes), `package_project()`, `package_podcast_episodes()`.
  - `audiobook_factory/orchestrator.py`: Dual-track `format_mode="audiobook" | "podcast" | "both"`.
  - `audiobook_factory/podcast/`: `PodcastEpisodePlan`, `HostPersonaEngine`, `SpokenBreathabilityTransformer` (<= 22 words), `PodcastOrchestrator` (-16.0 LUFS + stereo pan).
  - `audiobook_factory/adapters/`: `BaseScriptAdapter`, `AudiobookAdapter` (Gate 2.5), `PodcastAdapter`.
  - `audiobook_cli.py`: `auto --format`, `package --format`, `audit --certify` with 8-Pillar Scorecard.
- **Mastering Targets**:
  - Audiobook: -19.0 LUFS / -1.5 dBTP (Broadcast Audible standard M4B).
  - Podcast: -16.0 LUFS / -1.0 dBTP with stereo spatial staging (Host A: -0.25, Host B: +0.25) in M4A.

## Production Milestone: Chapter 3 Mastered (`Sword of Destiny`)
- **Status**: 100% MASTERED & VERIFIED.
- **Artifacts**: Script (`129 segments`), Dialogue Master (`18m 44s`), Broadcast M4A (`27.3 MB`).
- **Mastering**: -19.1 LUFS (EBU R128), -4.0 dBFS True Peak, 5.8 LU dynamic range.

## Antigravity Studio Plugin & UI Extension
- **Live Extension**: Registered at `~/.gemini/config/plugins/audiobook-studio/` (`@audiobook-director`, `audiobook-studio` skill, Stitch sidecar panel).
