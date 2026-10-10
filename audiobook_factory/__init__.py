"""
Audiobook Factory: Production-grade End-to-End Audiobook Production System.
Primary TTS: Google Gemini 3.1 Flash TTS Cloud API (Aoede/Charon/Kore/Puck/Fenrir/Zephyr).
Soundscape: Scene Mood Detection, Procedural BGM & Dynamic Sidechain Ducking.
Platform: High-Performance PC Workstation (Windows/Linux).
"""

import os
from pathlib import Path


def _load_env_file():
    """Load .env variables into os.environ with zero external dependencies."""
    cwd = Path.cwd()
    pkg_root = Path(__file__).resolve().parent.parent
    candidates = [cwd / ".env", pkg_root / ".env"]
    for env_path in candidates:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key and key not in os.environ:
                            os.environ[key] = val
            break


_load_env_file()

# Backward-compatible resolution for archived modules
_archive_dir = Path(__file__).resolve().parent.parent / "archive"
for _sub in ("real_audio", "sound_design"):
    _sub_path = _archive_dir / _sub
    if _sub_path.is_dir() and str(_sub_path) not in __path__:
        __path__.append(str(_sub_path))

import importlib
from typing import Any, Dict, Tuple

__version__ = "5.2.0"

# Mapping of symbol names to (submodule_relative_path, symbol_name)
_LAZY_IMPORTS: Dict[str, Tuple[str, str]] = {
    # Control Plane / Models & Keys (Pillar 3)
    "ModelGateway": (".core.models", "ModelGateway"),
    "get_model_gateway": (".core.models", "get_model_gateway"),
    "KeyLeaseManager": (".core.models", "KeyLeaseManager"),
    "get_key_lease_manager": (".core.models", "get_key_lease_manager"),
    "ModelRegistry": (".core.models", "ModelRegistry"),
    "get_model_registry": (".core.models", "get_model_registry"),
    "AntiBanGuard": (".core.models", "AntiBanGuard"),
    "get_anti_ban_guard": (".core.models", "get_anti_ban_guard"),
    "PersistentKeyPool": (".key_manager", "PersistentKeyPool"),
    "get_persistent_key_pool": (".key_manager", "get_persistent_key_pool"),
    "ModelManager": (".model_manager", "ModelManager"),
    "get_model_manager": (".model_manager", "get_model_manager"),

    # Extraction / Pillar 1
    "process_book_file": (".extractor", "process_book_file"),
    "extract_chapters": (".extractor", "extract_chapters"),
    "extract_epub": (".extractor", "extract_epub"),
    "clean_book_text": (".extractor", "clean_book_text"),
    "split_large_chapter_on_semantic_boundary": (".extractor", "split_large_chapter_on_semantic_boundary"),
    "CanonicalBook": (".book_model", "CanonicalBook"),
    "CanonicalChapter": (".book_model", "CanonicalChapter"),
    "CanonicalBlock": (".book_model", "CanonicalBlock"),
    "SourceProvenance": (".book_model", "SourceProvenance"),
    "ExtractionQualityReport": (".book_model", "ExtractionQualityReport"),
    "ExtractionGateAuditError": (".book_model", "ExtractionGateAuditError"),
    
    # Room 1.5: Standalone Glossary & Chapter Metadata
    "GlossaryManager": (".glossary", "GlossaryManager"),
    "ChapterGlossary": (".glossary", "ChapterGlossary"),
    "ChapterEntity": (".glossary", "ChapterEntity"),
    "ChapterLexicalScanner": (".glossary", "ChapterLexicalScanner"),
    "GlossaryClassifier": (".glossary", "GlossaryClassifier"),

    # Translation
    "translate_book_project": (".translator", "translate_book_project"),
    "normalize_translated_lexicon": (".translator", "normalize_translated_lexicon"),
    
    # Dramaturgy / Screenplay
    "generate_project_scripts": (".script_builder", "generate_project_scripts"),
    "build_dramatized_script_llm": (".script_builder", "build_dramatized_script_llm"),
    "build_narrator_script": (".script_builder", "build_narrator_script"),
    
    # TTS
    "TTSDispatcher": (".tts_dispatcher", "TTSDispatcher"),
    "UnregisteredSpeakerError": (".tts_dispatcher", "UnregisteredSpeakerError"),
    "probe_key_health": (".tts_dispatcher", "probe_key_health"),
    
    # Soundscape (Legacy)
    "detect_chapter_mood": (".soundscape", "detect_chapter_mood"),
    "resolve_ambient_score": (".soundscape", "resolve_ambient_score"),
    "generate_chapter_soundscape_plan": (".soundscape", "generate_chapter_soundscape_plan"),
    "render_chapter_soundscape": (".soundscape", "render_chapter_soundscape"),
    "generate_project_soundscapes": (".soundscape", "generate_project_soundscapes"),
    "apply_dynamic_sidechain_ducking": (".soundscape", "apply_dynamic_sidechain_ducking"),
    "render_multitrack_chapter_audio": (".soundscape", "render_multitrack_chapter_audio"),
    "get_sound_bank": (".soundscape", "get_sound_bank"),
    "attenuate_foley_whisper_collisions": (".soundscape", "attenuate_foley_whisper_collisions"),
    
    # Mastering & Packager
    "concatenate_and_master_chapter": (".mastering", "concatenate_and_master_chapter"),
    "package_m4b_audiobook": (".packager", "package_m4b_audiobook"),
    "SoundBank": (".sound_bank", "SoundBank"),
    "logger": (".logger", "logger"),
    "ProjectStateLedger": (".state", "ProjectStateLedger"),
    "PipelineOrchestrator": (".orchestrator", "PipelineOrchestrator"),
    
    # Contracts
    "ProjectConfig": (".contracts", "ProjectConfig"),
    "CharacterProfile": (".contracts", "CharacterProfile"),
    "CharacterRoster": (".contracts", "CharacterRoster"),
    "SceneSource": (".contracts", "SceneSource"),
    "MusicCue": (".contracts", "MusicCue"),
    "FoleyCue": (".contracts", "FoleyCue"),
    "AmbienceScene": (".contracts", "AmbienceScene"),
    "MasteringConfig": (".contracts", "MasteringConfig"),
    "CreativeManifest": (".contracts", "CreativeManifest"),
    "ManifestValidationError": (".contracts", "ManifestValidationError"),
    "BookPackagingSpecs": (".contracts", "BookPackagingSpecs"),
    "BookChapterMarker": (".contracts", "BookChapterMarker"),
    "BookTableOfContents": (".contracts", "BookTableOfContents"),
    "BookVoiceRoster": (".contracts", "BookVoiceRoster"),
    "GlobalLoreBible": (".contracts", "GlobalLoreBible"),
    "BookMasterManifest": (".contracts", "BookMasterManifest"),
    "MasteringSettings": (".contracts", "MasteringSettings"),
    
    # Cinema Audio Engine
    "render_discrete_stems": (".cinema_audio_engine", "render_discrete_stems"),
    "CinemaAudioManifest": (".cinema_audio_engine", "CinemaAudioManifest"),
    "StemMetadata": (".cinema_audio_engine", "StemMetadata"),
    "StemLedger": (".cinema_audio_engine", "StemLedger"),
    
    # Mastering Contracts & Systems
    "MasteringProfile": (".mastering_contracts", "MasteringProfile"),
    "MasteringAnalysisFacts": (".mastering_contracts", "MasteringAnalysisFacts"),
    "MasteringQCResult": (".mastering_contracts", "MasteringQCResult"),
    "MasteringRequest": (".mastering_contracts", "MasteringRequest"),
    "MasteringResult": (".mastering_contracts", "MasteringResult"),
    "MasteringLedger": (".mastering_contracts", "MasteringLedger"),
    "MasteringIssueSeverity": (".mastering_contracts", "MasteringIssueSeverity"),
    "MasteringIssue": (".mastering_contracts", "MasteringIssue"),
    "MasteringActionPlan": (".mastering_contracts", "MasteringActionPlan"),
    "DialogueProtectionReport": (".mastering_contracts", "DialogueProtectionReport"),
    "BookMasterProfile": (".mastering_contracts", "BookMasterProfile"),
    "DimensionDeviation": (".mastering_contracts", "DimensionDeviation"),
    "ChapterConsistencyAudit": (".mastering_contracts", "ChapterConsistencyAudit"),
    "BookConsistencyReport": (".mastering_contracts", "BookConsistencyReport"),
    "MasteringAnalyzer": (".mastering_analyzer", "MasteringAnalyzer"),
    "MasteringQCAgent": (".mastering_qc", "MasteringQCAgent"),
    "MasteringEngineV2": (".mastering_engine", "MasteringEngineV2"),
    "MasteringJudge": (".mastering_judge", "MasteringJudge"),
    "DialogueProtectionAgent": (".dialogue_protection", "DialogueProtectionAgent"),
    "BookMasterProfileBuilder": (".book_master_profile", "BookMasterProfileBuilder"),
    "ChapterConsistencyAuditor": (".chapter_consistency", "ChapterConsistencyAuditor"),
    "BookConsistencyReportBuilder": (".chapter_consistency", "BookConsistencyReportBuilder"),
    "GoldenMasteringSuite": (".golden_mastering_suite", "GoldenMasteringSuite"),
    "PerceptualCritic": (".perceptual_critic", "PerceptualCritic"),
    "ReferenceMasteringAuditor": (".reference_mastering", "ReferenceMasteringAuditor"),
    "CANONICAL_REFERENCE_PROFILES": (".reference_mastering", "CANONICAL_REFERENCE_PROFILES"),
    "SceneAwareDecisionEngine": (".scene_aware_engine", "SceneAwareDecisionEngine"),
    "MasteringCertifier": (".mastering_certification", "MasteringCertifier"),
    
    # Gates
    "AuditResult": (".gate_auditor", "AuditResult"),
    "GateAuditError": (".gate_auditor", "GateAuditError"),
    "audit_chapter_gates": (".gate_auditor", "audit_chapter_gates"),
    "audit_gate0_translation": (".gate_auditor", "audit_gate0_translation"),
    "audit_gate1_roster": (".gate_auditor", "audit_gate1_roster"),
    "audit_gate2_script": (".gate_auditor", "audit_gate2_script"),
    "audit_gate3_5_acoustic_feasibility": (".gate_auditor", "audit_gate3_5_acoustic_feasibility"),
    "audit_gate5_master": (".gate_auditor", "audit_gate5_master"),
    "audit_gate5_2_spectral_masking": (".gate_auditor", "audit_gate5_2_spectral_masking"),
    "audit_gate5_3_stereo_phase": (".gate_auditor", "audit_gate5_3_stereo_phase"),
    "audit_gate6a_voice_continuity": (".gate_auditor", "audit_gate6a_voice_continuity"),
    "audit_gate6b_loudness_continuity": (".gate_auditor", "audit_gate6b_loudness_continuity"),
    "audit_gate6c_toc_integrity": (".gate_auditor", "audit_gate6c_toc_integrity"),
    "audit_gate6c_toc_monotonicity": (".gate_auditor", "audit_gate6c_toc_monotonicity"),
    "audit_gate6d_packaging_specs": (".gate_auditor", "audit_gate6d_packaging_specs"),
    "audit_book_master": (".gate_auditor", "audit_book_master"),
    
    # Dialogue Editing
    "DialogueEditor": (".dialogue_editing", "DialogueEditor"),
    "DialogueEditPlan": (".dialogue_editing", "DialogueEditPlan"),
    "DialogueEditorialConfig": (".dialogue_editing", "DialogueEditorialConfig"),
    "DialogueQCReport": (".dialogue_editing", "DialogueQCReport"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        submod_rel, symbol = _LAZY_IMPORTS[name]
        mod = importlib.import_module(submod_rel, package=__package__)
        val = getattr(mod, symbol)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals().keys()) + list(_LAZY_IMPORTS.keys()))
