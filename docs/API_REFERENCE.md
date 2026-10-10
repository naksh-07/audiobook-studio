# 📚 API Reference: Data Contracts & Module Specifications

## Overview

The `audiobook_factory` package provides a strictly-typed, modular architecture powered by **Pydantic v2** models, clean separation of concerns, and zero hardcoded bindings. This document details the authoritative public contracts, engine classes, and core utility signatures.

---

## 📐 Data Contracts ([`audiobook_factory.contracts`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/contracts.py))

### 1. `ProjectConfig` & `CharacterProfile`
*Project setup, adult literary fidelity configuration, and character sociolect profiles.*

```python
class ProjectConfig(BaseModel):
    project_id: str                     # Unique identifier for the project
    title: str                          # Book/Project title
    author: str                         # Author name
    source_language: str                # Source text language code (e.g. 'en', 'hi')
    target_language: str = "hi-IN"      # Target TTS/audiobook language code
    assets_dir: str                     # Root directory path for all project media assets
    ebu_r128_lufs: float = -19.0        # EBU R128 integrated loudness target in LUFS
    true_peak_db: float = -1.5          # Maximum allowable True Peak in dBTP
    adult_literary_mode: bool = Field(
        default=True,
        description="Enables unfiltered Gangs-of-Wasseypur / Manto grade raw adult literary fidelity"
    )

class CharacterProfile(BaseModel):
    character_uuid: str                 # Unique UUID for character persona
    display_name: str                   # Display name of character in screenplay
    gender: str                         # Gender identifier ('male', 'female', 'neutral')
    assigned_voice_id: str              # Voice model identifier ('Charon', 'Aoede', 'Puck', etc.)
    pitch_shift: float = 0.0            # Pitch shift in semitones
    speed_multiplier: float = 1.0       # Speech rate multiplier (0.5 to 2.0)
    sociolect_trait: Optional[str] = Field(
        default=None,
        description="Subtle Desi sociolect trait (e.g. 'COLD_CYNIC', 'CAUSTIC_ARISTOCRAT', 'THARKI_BARD')"
    )

class CharacterRoster(BaseModel):
    project_id: str                     # Associated project identifier
    characters: List[CharacterProfile] = []
    pronunciation_overrides: Dict[str, str] = {}
```

### 2. `CreativeManifest`
*The authoritative creative and acoustic blueprint for a chapter.*

```python
class CreativeManifest(BaseModel):
    manifest_version: str = "3.0"
    project_id: str = ""
    chapter_id: str
    silence_percentage: float = 100.0  # Mandate: Must be >= 60.0%
    mastering: MasteringConfig = MasteringConfig()
    ambience_scenes: List[AmbienceScene] = []
    scene_acoustics: Optional[Any] = None  # Decoupled 4-stem SceneSoundscapeManifest
    music_cues: List[MusicCue] = []
    foley_cues: List[FoleyCue] = []
    total_duration_ms: Optional[int] = 0
    metadata: Dict[str, Any] = {}

    def validate_acoustic_rules(self, total_duration_ms: Optional[int] = None) -> None:
        """Enforces the >= 60.0% acoustic silence mandate against music cue durations."""

    @model_validator(mode="after")
    def parse_scene_acoustics(self) -> "CreativeManifest":
        """Rehydrates raw scene_acoustics dictionary into typed SceneSoundscapeManifest upon JSON load."""

    def to_dict(self) -> Dict[str, Any]: ...
    def to_json(self, indent: int = 2) -> str: ...
    def save_to_file(self, path: Union[str, Path]) -> None:
        """Serialize and save manifest directly to JSON file."""
    @classmethod
    def from_file(cls, path: Union[str, Path]) -> CreativeManifest:
        """Load and deserialize manifest directly from JSON file."""
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CreativeManifest: ...
    @classmethod
    def from_json(cls, json_str: str) -> CreativeManifest: ...
```

### 3. `ScreenplaySegment` & `ScreenplayScript`
*Atomic units of standardized screenplay dialogue, narration, and action.*

```python
class ScreenplaySegment(BaseModel):
    index: int                          # 1-indexed sequential segment number
    type: Literal["dialogue", "narration", "chapter_header", "action"]
    speaker: str = "Narrator"           # Canonical English character name or 'Foley'
    text: str = ""                      # Clean speech text or '[ACTION]' marker
    emotion: str = "neutral"            # Dramatic emotion category
    pause_after_ms: int = 400           # Silence buffer following line
    acting: ActingInstructions          # Delivery style & pacing
    spatial: SpatialCoordinates         # Stereo azimuth pan (-1.0 to +1.0) & proximity
    acoustic_env: str = "open_road"     # Scene IR preset
    sfx_cues: List[str] = []            # Associated physical Foley tags
    music: SegmentMusicParams           # Music atmosphere preferences
    intensity_level: Optional[str] = "medium"  # 'low', 'medium', 'high', 'explosive'
    pre_roll_breath_ms: Optional[int] = 0      # Breath intake Foley duration
    memory_vocal_constraint: Optional[str] = None  # Conservative physical vocal constraint (e.g. 'strained_breath')
    recommended_pronoun: Optional[str] = None      # Recommended Hindi pronoun from RelationshipState ('tu', 'tum', 'aap')
    recommended_register: Optional[str] = None     # Recommended socio-linguistic register from RelationshipState

class ScreenplayScript(BaseModel):
    segments: List[ScreenplaySegment] = []
    pronunciation_overrides: Dict[str, str] = {}

    @classmethod
    def from_file(cls, path: str | Path) -> ScreenplayScript: ...
```

### 4. `MusicCue` & `FoleyCue`
*Surgical musical score and tactile sound effect instructions.*

```python
class MusicCue(BaseModel):
    cue_id: str                         # e.g. 'mc_001'
    cue_type: MusicCueType              # 'EMOTIONAL_UNDERSCORE', 'CLIMACTIC_ACTION_CUE', etc.
    track_id: int = 0                   # Catalog asset identifier
    track_name: str                     # Asset filename or title
    section_name: str                   # 'INTRO_BED', 'CLIMAX_DROP', etc.
    section_start_sec: float = 0.0      # Offset inside source track
    start_ms: int                       # Offset on chapter timeline in ms
    duration_ms: int                    # Duration of cue in ms
    until_segment: Optional[int] = None # Segment boundary where cue terminates (ADR-022)
    fade_in_ms: int = 2000
    fade_out_ms: int = 3000
    volume_db: float = -18.0
    leitmotif_ref: Optional[str] = ""   # Associated Sonic Bible motif ID
    spectral_notch_needed: bool = False # Flag for 2.2kHz vocal notch filter
    target_valence: Optional[float] = None
    target_arousal: Optional[float] = None

class FoleyCue(BaseModel):
    cue_id: str                         # e.g. 'fc_001'
    segment_index: int                  # Triggering dialogue segment index
    anchor_word: str                    # Dialogue word triggering the sound
    pre_roll_ms: int = 100              # Lead-in time in ms
    asset_id: int = 0
    asset_path: str = ""
    gain_dbfs: float = -15.0            # Calibrated peak target
    azimuth_pan: float = 0.0            # Panning [-0.8, +0.8]
    reverb_send: float = 0.15           # Send level to shared reverb
    start_ms: Optional[int] = 0
    duration_ms: Optional[int] = 0
    ucs_category: Optional[str] = "MISCGnl" # Universal Category System (UCS) Category ID
    is_lfe_sub_drop: bool = False       # Triggers 50Hz sub-bass physical impact weight
    trajectory: str = "static"          # 'static', 'left_to_right', 'right_to_left', 'center_zoom'
```

### 5. `AmbienceScene` & `MasteringConfig`
*Continuous environmental background beds and broadcast mastering parameters.*

```python
class AmbienceScene(BaseModel):
    scene_id: int                       # Sequential scene index
    start_ms: int                       # Start offset on chapter timeline in ms
    end_ms: int                         # End offset on chapter timeline in ms
    asset_path: str                     # Filesystem path to ambient bed
    target_lufs: float = -32.0          # Calibrated background loudness in LUFS
    reverb_preset: str = "room"         # Convolution preset ('room', 'cathedral', etc.)

class MasteringConfig(BaseModel):
    target_lufs: float = -19.0          # Integrated loudness in LUFS
    true_peak_dbtp: float = -1.5        # True peak ceiling in dBTP
    ducking_attenuation_db: float = -7.5 # Attenuation gain while dialogue speaks
    ducking_attack_ms: int = 120        # Compressor attack time
    ducking_release_ms: int = 750       # Compressor release time
    spectral_carve_hz: int = 2200       # Center frequency for vocal notch filter
    spectral_carve_gain_db: float = -5.5
```

### 6. `SceneSoundscapeManifest`, `SceneAcousticProfile` & `AmbienceLayer`
*Decoupled 4-stem scene acoustics, spatial barrier occlusion, and stochastic spot transient configuration.*

```python
class AmbienceLayer(BaseModel):
    layer_type: Literal["base_room_tone", "weather_elements", "crowd_wallah", "spot_stochastic"]
    asset_path: str                     # Asset filename or path in sound bank
    target_lufs: float = -32.0          # Loudness target (-60.0 to -15.0 LUFS)
    stereo_width: float = 1.0           # Stereo spread factor (1.0 = native stereo)
    azimuth_pan: float = 0.0            # Spatial pan coordinate (-1.0 to +1.0)
    high_pass_hz: Optional[int] = None  # Low-cut filter frequency in Hz
    low_pass_hz: Optional[int] = None   # High-cut distance damping frequency in Hz
    loop: bool = True                   # Seamlessly loop across scene
    stochastic_interval_sec: Optional[float] = None # Period for spot triggers (e.g. 35.0s)

class SceneAcousticProfile(BaseModel):
    scene_id: str                       # e.g. 'sc_001_great_hall'
    act_index: int = 1                  # Dramatic act grouping
    start_ms: int = 0                   # Timeline start in ms
    end_ms: int = 0                     # Timeline end in ms
    environment_id: str = "default"     # WorldAcousticProfile ID
    ir_preset: str = "room"             # Reverberation impulse response preset
    layers: List[AmbienceLayer] = []    # Up to 4 decoupled ambient stems
    transition_in: Literal["cut", "crossfade", "fade_from_silence"] = "crossfade"
    transition_out: Literal["cut", "crossfade", "fade_to_silence"] = "crossfade"
    crossfade_ms: int = 2500            # Crossfade duration in ms
    occlusion_cutoff_hz: int = 18000    # Low-pass barrier occlusion frequency (e.g. 1400Hz indoor)

class SceneSoundscapeManifest(BaseModel):
    schema_version: str = "2.0"
    chapter_id: str
    scenes: List[SceneAcousticProfile] = []
    metadata: Dict[str, Any] = {}

    def add_scene(self, scene: SceneAcousticProfile) -> None: ...
    def save_to_disk(self, target_path: Union[str, Path]) -> Path: ...
    @classmethod
    def load_from_disk(cls, source_path: Union[str, Path]) -> SceneSoundscapeManifest: ...
    def audit_scene_acoustics_integrity(self, sound_bank: Optional[Any] = None) -> Dict[str, Any]: ...
    def generate_stochastic_cues(
        self,
        timeline_ledger: Optional[Any] = None,
        sound_bank: Optional[Any] = None,
        seed: int = 42,
    ) -> List[Any]:
        """Procedurally places Layer 4 stochastic spot transients in pause gaps (>= 600ms)."""
```

### 7. `TimelineSegment` & `TimelineLedger`
*Gate 4.5 sample-accurate transcript and millisecond timeline ledger.*

```python
class TimelineSegment(BaseModel):
    segment_index: int
    speaker: str
    text: str                           # Full unabridged speech transcript
    audio_file: str                     # Filename of synthesized WAV chunk
    duration_ms: int                    # Sample duration in ms
    start_ms: int                       # Timeline start offset in ms (curr_t + pre_breath)
    end_ms: int                         # Timeline end offset in ms
    pause_after_ms: int = 400
    emotion: str = "neutral"
    spatial_pan: float = 0.0
    acoustic_env: str = "temple_stone_hall"
    sfx_cues: List[str] = []            # Associated physical Foley tags
    music_mood: str = "neutral"         # Underlying musical mood
    pre_roll_breath_ms: int = 0         # Organic breath intake duration (ADR-022)

class TimelineLedger(BaseModel):
    ledger_version: str = "2.0"
    project_id: str = ""
    chapter_id: str
    total_segments: int
    total_dialogue_duration_ms: int
    total_timeline_duration_ms: int
    total_silence_duration_ms: int
    silence_percentage: float
    segments: List[TimelineSegment] = []

    def get_segment(self, index: int) -> Optional[TimelineSegment]: ...
    def find_segment_at_ms(self, timestamp_ms: int) -> Optional[TimelineSegment]: ...
    @classmethod
    def from_file(cls, path: str | Path) -> TimelineLedger: ...
```

### 8. `BookMasterManifest` & Macro Contracts
*Macro-tier book-level contracts aggregating voice roster, lore bible, TOC, and packaging.*

```python
class BookMasterManifest(BaseModel):
    title: str
    author: str
    narrator: str = "Charon"
    translator_credits: Optional[str] = None
    series_title: Optional[str] = None
    book_number: Optional[int] = None
    total_duration_ms: int = 0
    global_integrated_lufs: float = -19.0
    voice_roster: BookVoiceRoster = BookVoiceRoster()
    lore_bible: GlobalLoreBible = GlobalLoreBible()
    toc: BookTableOfContents = BookTableOfContents()
    packaging_specs: BookPackagingSpecs = BookPackagingSpecs()

    @classmethod
    def from_file(cls, path: str | Path) -> BookMasterManifest: ...
```

---

## 🏛️ Core Engine Classes

### `PipelineOrchestrator` ([`audiobook_factory.orchestrator`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/orchestrator.py))
*Coordinates the complete autonomous novel production lifecycle.*

```python
class PipelineOrchestrator:
    def __init__(self, projects_dir: Path): ...

    def run_autonomous_pipeline(
        self,
        input_file: Path,
        hindi: bool = True,
        dramatized: bool = True,
        voice: str = "Aoede",
        cover_image: Optional[Path] = None,
        workers: int = 3,
        duck_db: float = -16.0,
        spatial_staging: bool = False,
        adult_literary_mode: bool = True,
    ) -> Path:
        """
        Runs the 6-stage autonomous novel production pipeline, returning path to final M4B.

        Parameters:
            input_file: Path to input novel file (.epub, .pdf, .txt, .md).
            hindi: Whether to translate text into literary Hindustani (default: True).
            dramatized: Enables multi-cast dialogue attribution and soundscape staging (default: True).
            voice: Lead narrator voice identifier (default: "Aoede").
            cover_image: Optional path to JPEG/PNG cover artwork for M4B packaging.
            workers: Max concurrent synthesis threads for token-bucket pool (default: 3).
            duck_db: Dynamic music sidechain ducking attenuation in dB (default: -16.0).
            spatial_staging: Enables stereo azimuth panning across character cast (default: False).
            adult_literary_mode: bool = True: Enables unfiltered Gangs-of-Wasseypur / Manto grade
                raw adult literary fidelity, 70/30 Anti-Parody Invariant, HBO somatic erotica,
                Cynical Protagonist Grunt Engine, and ASMR intimate close proximity staging.
        """

    def produce_chapter(
        self,
        project_dir: Path,
        chapter_num: int,
        voice: str = "Aoede",
        workers: int = 3,
        duck_db: float = -16.0,
        spatial_staging: bool = False,
    ) -> Dict[str, Any]:
        """Produces a single cinematic chapter with stems, timeline ledger, and quality checks."""
```

### `UniversalExtractor` ([`audiobook_factory.extractor`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/extractor.py))
*Multi-format document parser with native pypdf digital parsing and Gemini multimodal fallback.*

```python
def process_book_file(input_file: Path, output_projects_dir: Path) -> Dict[str, Any]:
    """Ingests EPUB, PDF, TXT, or MD, creates a project folder, and extracts structured chapters."""

def extract_gemini_pdf(file_path: Path, api_key: str | None = None) -> str:
    """Extracts text using local fast pypdf (zero-quota, instant) with fallback to Gemini multimodal document API."""

def extract_chapters(text: str) -> List[Dict[str, Any]]:
    """Detects semantic chapter breaks, Roman numerals, and headings."""

def split_large_chapter_on_semantic_boundary(
    chapter_text: str, max_chars: int = 45000
) -> List[str]:
    """Splits oversized chapters along paragraph boundaries to avoid LLM context overflow."""
```

### `LiteraryTranslator` ([`audiobook_factory.translator`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/translator.py))
*Two-pass literary Hindustani translation engine with glossary synchronization and rolling narrative context.*

```python
def translate_book_project(
    project_dir: Path,
    model: str = "gemini-flash-latest",
    target_lang: str = "hi",
) -> Path:
    """Translates all extracted chapters in a project, threading 250-word rolling context across chapter boundaries."""

def translate_chapter(
    chapter_text: str,
    glossary: Optional[Dict[str, str]] = None,
    chapter_num: int = 1,
    preceding_summary: str = "",
    model: str = "gemini-flash-latest",
) -> str:
    """Translates a chapter in chunks, enforcing canonical lexicon normalization."""

def normalize_translated_lexicon(text: str, glossary: Dict[str, str]) -> str:
    """Applies canonical proper noun substitutions to translated text based on project glossary."""
```

### `LinguisticSanitizer` ([`audiobook_factory.sanitizer`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/sanitizer.py))
*Defense-in-depth linguistic guardrail, TTS vocal tag validator, and profanity preservation engine.*

```python
SUPPORTED_TTS_TAG_PATTERNS: List[str] = [
    r"whispers?", r"shouting", r"shouts?", r"sighs?", r"gasp", r"laughs?",
    r"giggles?", r"crying", r"trembling(?:\s+voice)?", r"cold\s+menace",
    r"intimate(?:,\s*breathy)?", r"growl", r"groan", r"spits?",
    r"bellowing\s+rage", r"breathless[\s_]+exhaustion", r"mocking\s+chuckle", ...
]

def validate_and_sanitize_translation(
    text: str,
    is_hindi: bool = True,
) -> Tuple[bool, str, str]:
    """
    Validates Devanagari purity, strips LLM meta-chatter/markdown fences,
    and guarantees 100% preservation of raw adult profanity and somatic erotica vocabulary.
    Returns: (is_valid: bool, cleaned_text: str, failure_reason: str).
    """

def sanitize_screenplay_segment(
    segment: Dict[str, Any],
    is_hindi: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Sanitizes screenplay segment text, selectively preserving permitted Gemini TTS neural
    vocal tags ([whispers], [growl], [spits], etc.) while stripping leaked non-vocal stage directions.
    Returns None if segment contains LLM refusal or conversational meta-commentary.
    """
```

### `ScriptBuilder` ([`audiobook_factory.script_builder`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/script_builder.py))
*Sliding-window dialogue parsing and character attribution engine.*

```python
def generate_project_scripts(
    project_dir: Path,
    use_hindi: bool = False,
    dramatized: bool = True,
) -> Path:
    """Generates standardized screenplay JSON for all chapters."""

def build_dramatized_script_llm(
    text: str,
    chapter_title: str,
    character_roster: CharacterRoster,
    project_dir: Path,
) -> List[Dict[str, Any]]:
    """Extracts speaker tags, emotions, delivery styles, and spatial pan coordinates."""
```

### `TTSDispatcher` ([`audiobook_factory.tts_dispatcher`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/tts_dispatcher.py))
*Token-Bucket concurrent speech synthesizer, multimodal audio director, and zero-voice-drift orchestrator.*  
*(See comprehensive technical manuals: [`docs/GEMINI_TTS_SYNTHESIS_AND_DIRECTING.md`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/docs/GEMINI_TTS_SYNTHESIS_AND_DIRECTING.md) and [`docs/VOICE_CASTING_DIRECTOR_GUIDE.md`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/docs/VOICE_CASTING_DIRECTOR_GUIDE.md))*

```python
class UnregisteredSpeakerError(KeyError):
    """Raised when a dialogue segment requests an unregistered character voice (ADR-021)."""

class TTSDispatcher:
    def __init__(
        self,
        project_dir: Path,
        default_backend: str = "gemini_tts",
        default_voice: str = "Aoede",
        max_workers: int = 1,
        rpm: float = DEFAULT_RPM,
        audio_dir: Optional[Path] = None,
        strict_speakers: bool = True,
    ):
        """
        Orchestrates concurrent speech synthesis with TokenBucket rate limiting and SQLite ledger state.
        When strict_speakers=True (default), prohibits silent fallback to Narrator for dialogue.
        """

    def get_speaker_config(
        self, speaker: str, seg_type: str = "narration"
    ) -> Dict[str, Any]:
        """Resolves complete speaker configuration, mapping roster aliases and checking whitelist."""

    def synthesize_segment(
        self, segment: Dict[str, Any], chapter_num: int, seg_num: int
    ) -> Tuple[Path, float]:
        """Synthesizes an individual dialogue or narration segment with SNR quality validation."""

    def synthesize_chapter_script(
        self,
        script_file: Path,
        chapter_idx: int,
    ) -> List[Path]:
        """Pre-flights all segments against voice registry, then synthesizes chunks concurrently."""

def resolve_speech_metadata_style(
    acting: Any,
    emotion: str = "neutral",
    intensity: str = "medium",
    memory_vocal_constraint: Optional[str] = None,
) -> str:
    """Transforms screenplay acting directives into natural language descriptors for speechMetadata.style."""

def synthesize_gemini_tts(
    text: str,
    output_file: Path,
    voice: str = DEFAULT_VOICE,
    model: str = "gemini-3.8-flash-tts",
    emotion: str = "neutral",
    acting: Any = None,
    intensity: str = "medium",
    memory_vocal_constraint: Optional[str] = None,
    max_retries: int = 4,
    rate_limiter: Optional[TokenBucketRateLimiter] = None,
) -> Tuple[Path, float]:
    """Synthesizes unary 24kHz WAV speech chunk with explicit BLOCK_NONE safetySettings and SNR gatekeeping."""

def synthesize_gemini_multispeaker_batch(
    batch: BatchPlanItem,
    output_file: Path,
    voice_map: Dict[str, str],
    model: str = "gemini-3.8-flash-tts",
    rate_limiter: Optional[TokenBucketRateLimiter] = None,
) -> Tuple[Path, float]:
    """Synthesizes multi-speaker 2-character dialogue rallies using multiSpeakerVoiceConfig."""

def probe_key_health(api_key: str) -> bool:
    """Verifies API key validity and active quota with Google AI Studio."""
```

### `AgentDirector` ([`audiobook_factory.agent_director`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/agent_director.py))
*Autonomous dramaturgy and acoustic soundscape director.*

```python
class AgentDirector:
    def __init__(self, project_dir: Path): ...

    def direct_chapter_manifest(
        self,
        chapter_id: str,
        script_segments: List[Dict[str, Any]],
        segment_durations_sec: Dict[int, float],
        dialogue_stem_path: Optional[Path] = None,
        timeline_ledger: Optional[TimelineLedger] = None,
        project_dir: Optional[Path] = None,
        sonic_bible: Optional[SonicBible] = None,
    ) -> CreativeManifest:
        """Executes 3-pass dramaturgy (silence carving, FTS5 music matching, foley mining)."""

    def _partition_script_ambience_scenes(
        self,
        script_segments: Optional[List[Dict[str, Any]]],
        seg_starts_ms: Optional[Dict[int, int]],
        segment_durations_sec: Optional[Dict[int, float]],
        total_duration_ms: int,
    ) -> List[Tuple[str, int, int]]:
        """Partitions chapter into contiguous scene blocks based on acoustic_env shifts (ADR-022)."""

    def _compute_word_level_offset(
        self, text: str, anchor_word: str, seg_dur_ms: int, action_verb: str = ""
    ) -> int:
        """Calculates Foley anchor timing with BILINGUAL_ANCHOR_MAP, eliminating 50% dead-center trap (ADR-022)."""

    def _resolve_foley_asset(self, action_verb: str, object_material: str) -> Optional[Path]:
        """Resolves sound asset from sound bank using category guards (e.g. DOMETabl vs WEAPSwd)."""
```

### `SonicBible` ([`audiobook_factory.sonic_bible`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/sonic_bible.py))
*Project-level soundscape and leitmotif registry.*

```python
class SonicBible:
    def __init__(self, book_title: str = "", project_id: str = ""): ...

    def register_leitmotif(self, leitmotif: LeitmotifDefinition) -> None:
        """Registers a recurring musical theme for a character, location, or artifact."""

    def get_leitmotif_for_character(self, character_name: str) -> Optional[LeitmotifDefinition]: ...
    def save_to_disk(self, filepath: Path) -> None: ...
    @classmethod
    def load_from_disk(cls, filepath: Path) -> SonicBible: ...
```

### `SoundBank` ([`audiobook_factory.sound_bank`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/sound_bank.py))
*High-performance SQLite FTS5 audio warehouse.*

```python
class SoundBank:
    def __init__(self, db_path: Optional[Path] = None, bank_root: Optional[Path] = None): ...

    def search_sounds(
        self,
        query: str,
        category: Optional[str] = None,
        mood: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Executes Full-Text Search against the sound catalog with BM25 ranking."""

    def scan_and_index_directory(self, asset_dir: Path) -> int:
        """Scans folder and commits metadata for all valid audio assets."""

    def get_stats(self) -> Dict[str, Any]:
        """Returns track counts, durations, and category distribution."""
```

### `AcousticBusMatrix` ([`audiobook_factory.acoustic_bus_matrix`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/acoustic_bus_matrix.py))
*Dynamic ducking profiles, UCS category resolution, and formant pocketing.*

```python
class DuckingProfile(BaseModel):
    profile_name: Literal["intimate_dialogue", "standard_speech", "combat_shouting", "heavy_impact", "combat_shock"]
    attenuation_db: float = -16.0
    attack_ms: int = 15
    release_ms: int = 350
    spectral_carve_hz: int = 2400
    spectral_carve_depth_db: float = -6.0

PROFILE_COMBAT_SHOCK = DuckingProfile(profile_name="combat_shock", attenuation_db=-24.0, release_ms=4000)
PROFILE_COMBAT = DuckingProfile(profile_name="combat_shouting", attenuation_db=-22.0, release_ms=250)

def get_ducking_profile(name_or_scene_type: str) -> DuckingProfile: ...
def derive_ucs_category(action_verb_or_cue: str, exciter: str = "") -> str:
    """Derives Universal Category System ID (e.g. DOMETabl for dining, WEAPSwd for swords, GOREAnat for flesh/bone)."""
def filter_concurrency_window(
    foley_cues: List[FoleyCue],
    window_ms: int = 200,
    max_concurrency: int = 3,
) -> List[FoleyCue]:
    """Applies voice limiter & priority stealing to prevent transient clumping within 200ms."""
```

### `UniversalSoundBankIngester` ([`audiobook_factory.sound_bank_ingest`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/sound_bank_ingest.py))
*Multi-threaded batch audio ingestion pipeline.*

```python
class UniversalSoundBankIngester:
    def __init__(self, sound_bank: SoundBank, num_workers: int = 4): ...

    def ingest_directory(
        self,
        directory_path: Path,
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """Probes, extracts acoustic metadata, and indexes all audio files concurrently."""
```

### `CinemaAudioEngine` ([`audiobook_factory.cinema_audio_engine`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/cinema_audio_engine.py))
*Film-standard discrete stem renderer and packaging ledger with Music-Only 2.2kHz notch EQ.*

```python
def render_discrete_stems(
    manifest: CinemaAudioManifest,
    dialogue_wav: Path,
    output_dir: Path,
    sound_bank: Optional[SoundBank] = None,
    ffmpeg: Optional[str] = None,
) -> StemLedger:
    """Renders 5 discrete DME stems (DX, MX, FX, AMB, ME) with isolated 2.2kHz notch on Music [0:a] only, and final broadcast master."""
```

### `ManifestRenderer` ([`audiobook_factory.manifest_renderer`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/manifest_renderer.py))
*Dynamic FFmpeg `filter_complex` compiler.*

```python
def render_manifest_soundscape(
    manifest: CreativeManifest,
    vocal_track_path: Path,
    output_master_file: Path,
    sound_bank: Optional[SoundBank] = None,
) -> Path:
    """Assembles and executes multitrack audio graph with ducking, IR reverb, and music-only notch."""

def get_reverb_filter_string(preset: str = "room") -> Tuple[str, float]:
    """Generates FFmpeg aecho parameters and wet mix gain for scene presets."""
```

### `Mastering` ([`audiobook_factory.mastering`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/mastering.py))
*Vocal DSP processing and EBU R128 loudness normalization.*

```python
def concatenate_and_master_chapter(
    audio_segments: List[Path],
    output_chapter_file: Path,
    pause_ms: int = 400,
    loudnorm: bool = True,
    target_lufs: float = -19.0,
    true_peak_db: float = -1.5,
    loudness_range: float = 11.0,
    target_sample_rate: int = 48000,
    script_segments: Optional[List[Dict[str, Any]]] = None,
    spatial_staging: bool = False,
) -> Path:
    """Concatenates speech WAVs, applies 5-stage DSP chain, and normalizes loudness."""
```

### `Packager` ([`audiobook_factory.packager`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/packager.py))
*M4B container packaging with AAC safety validation, faststart atom placement, and artwork embedding.*

```python
def package_m4b_audiobook(
    project_dir: Path,
    cover_image: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    enforce_gate6: bool = False,
) -> Path:
    """Validates AAC streams (is_all_aac); automatically transcodes uncompressed WAV or non-AAC chapters to AAC 192k."""

def _escape_ffmetadata(val: Any) -> str:
    """Escapes special characters (=, ;, #, \\) for FFMETADATA1 specification."""

def generate_ffmetadata(
    metadata: Dict[str, Any],
    chapter_durations: List[Dict[str, Any]],
    output_file: Path,
) -> Path:
    """Generates standard FFMETADATA1 file with escaped title, artist, and chapter timestamps."""
```

### `Foley & Magic Composite Baker` ([`scripts/bake_foley_composites.py`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/scripts/bake_foley_composites.py))
*Offline pre-rendering of multi-phase Harry Potter magic spells and tactile props, indexed into SQLite FTS5.*

```python
def bake_composite(
    output_path: Path,
    filter_complex: str,
    inputs: List[str],
    duration_sec: float = 2.0,
    ffmpeg: str = "ffmpeg",
) -> bool:
    """Renders a single pre-baked composite asset via FFmpeg with zero runtime filter graph bloat."""

def bake_all_magic_and_foley_composites() -> None:
    """Pre-bakes the core Harry Potter & fantasy tactile composite sound set and indexes them into Sound Bank."""
```

---

## 🛡️ Quality Gate Auditor ([`audiobook_factory.gate_auditor`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/gate_auditor.py))

```python
# Result Contract
class AuditResult(BaseModel):
    gate_name: str
    passed: bool
    score: float = 1.0
    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

class GateAuditError(Exception):
    """Raised when an unrecoverable gate constraint is violated."""

# Gate 0: Translation Coverage
def audit_gate0_translation(extracted_file: Path, translation_file: Path) -> Dict[str, Any]: ...

# Gate 1: Voice Collision Elimination & Acoustic Gender Alignment (ADR-021)
def audit_gate1_roster(
    roster_file: Union[Path, Dict],
    registry_file: Union[Path, Dict],
    active_characters: Optional[List[str]] = None,
) -> Dict[str, Any]: ...

# Gate 2: Screenplay Scripting Schema & Canonical Whitelist Enforcement (ADR-021)
def audit_gate2_script(
    script_file: Path,
    allowed_speakers: Optional[Set[str]] = None,
    project_dir: Optional[Path] = None,
) -> Dict[str, Any]: ...

# Gate 3 & 3.5: Acoustic Feasibility & Scene Coverage
def audit_gate3_scenes(scenes_file: Path, script_file: Path) -> Dict[str, Any]: ...
def audit_gate3_5_acoustic_feasibility(manifest: CreativeManifest, sound_bank: Optional[SoundBank] = None) -> AuditResult: ...

# Gate 4.5: Master Timeline & Audio Transcript Ledger
def audit_gate4_ledger(ledger_file: Path, script_file: Path, audio_dir: Path) -> Dict[str, Any]: ...

# Gate 5: Broadcast EBU R128 Master (Standardized 1.0 LU tolerance)
def audit_gate5_master(
    master_file: Path,
    target_lufs: float = -19.0,
    tolerance_lu: float = 1.0,
    max_true_peak: float = -1.4,
) -> Dict[str, Any]: ...

# Gate 5.2: Spectral Masking (DMR)
def audit_gate5_2_spectral_masking(dialogue_stem: Path, music_stem: Path, min_dmr_db: float = 12.0) -> AuditResult: ...

# Gate 5.3: Stereo Phase Correlation
def audit_gate5_3_stereo_phase(audio_file: Path, min_phase_correlation: float = 0.20) -> AuditResult: ...

# Gate 6A: Voice Continuity Across Chapters
def audit_gate6a_voice_continuity(project_dir: Path) -> AuditResult: ...

# Gate 6B: Inter-Chapter Loudness Continuity (1.0 LU max variance)
def audit_gate6b_loudness_continuity(chapter_files: List[Path], target_lufs: float = -19.0, max_variance: float = 1.0, strict: bool = False) -> AuditResult: ...

# Gate 6C: Table of Contents Monotonicity
def audit_gate6c_toc_monotonicity(chapter_files_or_project_dir: Any, toc: Optional[BookTableOfContents] = None) -> AuditResult: ...

# Gate 6D: Container Packaging Specifications
def audit_gate6d_packaging_specs(cover_image: Optional[Path], specs: Optional[BookPackagingSpecs] = None) -> AuditResult: ...

# Multi-Gate Macro Audits (Dynamic Gate 3 handling)
def audit_chapter_gates(project_dir: Path, chapter_num: int, active_speakers: Optional[List[str]] = None) -> Dict[str, Any]: ...
def audit_book_master(project_dir: Path, strict: bool = False) -> Dict[str, Any]: ...
```

---

## 🔬 Novel Researcher & Pre-Production Subsystem ([`audiobook_factory.preproduction`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/) & [`audiobook_factory.metadata`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/))

*(See full architectural specification: [`docs/NOVEL_RESEARCHER_ARCHITECTURE.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/NOVEL_RESEARCHER_ARCHITECTURE.md))*

Room 1 implements a decoupled **2-System Pre-Production Architecture**:
- **System 1: Stateless Novel Researcher Engine** (`audiobook_factory/preproduction/`): Pure stateless compute, deterministic full-corpus lexical analysis, Google Search Grounding with bidirectional validation, and pure vocals-only acoustic design. Zero direct filesystem I/O.
- **System 2: Canonical Metadata & State Maintainer** (`audiobook_factory/metadata/`): Authoritative Pydantic v2 schemas (`BookBible`, `BookEntity`, `EpistemicProvenance`), transactional multi-file persistence (`NovelStateMaintainer`), thread concurrency locking (`_STATE_LOCK = threading.RLock()`), and Windows 11 atomic replace hardening (`_atomic_replace`).

---

### System 1: Stateless Novel Researcher Engine

#### 1. Pre-Production Control Plane Bridge ([`audiobook_factory.preproduction.gateway_bridge`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/gateway_bridge.py))

Authoritative routing bridge ensuring 100% of Pre-Production Room 1 LLM calls route through [`ModelGateway`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py) with Concurrency=1 key leases from [`KeyLeaseManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py), 11.0 RPM rate pacing via `AntiBanGuard`, official stealth SDK headers (`x-goog-api-client`), session affinity sticky binding, permissive `BLOCK_NONE` creative safety framing, and resilient `json_repair`.

```python
def execute_preproduction_llm(
    prompt: str,
    system_instruction: Optional[str] = None,
    task: str = "directing",
    model: Optional[str] = None,
    json_mode: bool = True,
    temperature: float = 0.3,
    max_output_tokens: Optional[int] = None,
    thinking_budget: Optional[int] = None,
    session_id: Optional[str] = None,
    user_id: str = "preproduction_worker",
    tools: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any,
) -> Union[Dict[str, Any], List[Any], str]:
    """
    Executes a Pre-Production Room 1 LLM request strictly through ModelGateway.
    
    Args:
        prompt: Raw prompt text containing book samples and instructions.
        system_instruction: System prompt framing dramatic acting or extraction rules.
        task: ModelGateway task type ('directing', 'extraction', 'translation', 'utility').
        model: Specific model ID override (defaults to active task model).
        json_mode: If True, parses output into JSON (dict or list); else returns raw text.
        temperature: Sampling temperature (clamped 0.2 - 0.4 for factual dramaturgy).
        max_output_tokens: Maximum tokens in response.
        thinking_budget: Gemini Flash thinking budget (default 1024).
        session_id: Context session ID for sticky key affinity binding.
        user_id: Caller identity for single-user quota tracking.
        tools: Optional tool definitions (e.g. [{'googleSearch': {}}]).
        **kwargs: Additional parameters forwarded to ModelGateway.generate_text.

    Returns:
        Parsed JSON dictionary/list or cleaned text response.
    """
```

#### 2. Full-Corpus Lexical Scanner ([`audiobook_factory.preproduction.lexical_scanner`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/lexical_scanner.py))

Deterministic, 0-token, 0ms full-corpus scanner indexing dialogue speaker attributions, proper nouns, and entity frequencies across all novel chapters with UTF-8 replacement defense (`errors="replace"`).

```python
@dataclass
class EntityOccurrence:
    """Statistical and provenance facts for a candidate entity discovered in the text corpus."""
    name: str
    first_chapter: int = 1
    total_mentions: int = 1
    dialogue_speaker_count: int = 0
    chapters_appeared: Set[int] = field(default_factory=set)
    introductory_quote: str = ""
    associated_titles: Set[str] = field(default_factory=set)
    co_occurring_names: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def to_dict(self) -> Dict[str, Any]: ...

class LexicalCorpusIndex:
    """Searchable in-memory index of all entities, dialogue speakers, and citations across the novel."""
    def __init__(self, entities: Dict[str, EntityOccurrence], total_chapters: int, total_words: int): ...
    def get_mention_count(self, name: str, aliases: Optional[List[str]] = None) -> int: ...
    def get_first_chapter(self, name: str) -> int: ...
    def get_intro_sentence(self, name: str) -> str: ...
    def get_top_speaking_characters(self, limit: int = 40) -> List[EntityOccurrence]: ...
    def to_summary_dict(self) -> Dict[str, Any]: ...

class LexicalCorpusScanner:
    """Deterministic Full-Novel Lexical Scanner."""
    @classmethod
    def scan_project_dir(cls, project_dir: Path | str) -> LexicalCorpusIndex: ...
    @classmethod
    def scan_chapters(cls, chapters: List[Dict[str, Any]] | List[str] | List[Tuple[Any, ...]]) -> LexicalCorpusIndex: ...
```

#### 3. Novel DeepSearch Engine ([`audiobook_factory.preproduction.novel_deepsearch`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/novel_deepsearch.py))

Antigravity-native DeepSearch engine conducting multi-angle Google Search Grounded research with bidirectional corpus verification (**NR-GATE-02**).

```python
class LiteraryDNAProfile(BaseModel):
    tradition: str = "UNIVERSAL_CONTEMPORARY"  # e.g. RURAL_REALISM_PATHOS, VICTORIAN_GOTHIC, DARK_FANTASY
    primary_genre: str = "Literary Fiction"
    sub_genres: List[str] = Field(default_factory=list)
    historical_era: str = "contemporary"
    setting_geography: str = "Universal"
    publication_year: Optional[str] = None
    narrative_tone: str = "dramatic and immersive"
    source_fidelity_tier: str = "STANDARD_ADULT"  # 'RAW_UNRATED', 'STANDARD_ADULT', 'FAMILY_FRIENDLY'

class CanonicalCharacter(BaseModel):
    english_name: str
    hindi_name: str = ""                       # Phonetically verified Devanagari transliteration
    role_prominence: str = "major"             # 'lead', 'major', 'minor', 'incidental'
    gender: str = "neutral"                    # 'male', 'female', 'neutral'
    age_group: str = "adult"                   # 'child', 'youth', 'adult', 'elder'
    occupation_status: str = ""
    vocal_weight: str = "balanced"             # 'heavy_deep', 'light_agile', 'authoritative', etc.
    aliases: List[str] = Field(default_factory=list)

class WorldAcousticSetting(BaseModel):
    primary_materials: List[str] = Field(default_factory=lambda: ["wood", "cloth", "stone"])
    architectural_style: str = "domestic interior and natural exterior"
    geography_climate: str = "temperate"
    banned_anachronisms: List[str] = Field(default_factory=list)

class MusicalTradition(BaseModel):
    cultural_tradition: str = "cinematic orchestral and subtle acoustic"
    signature_instruments: List[str] = Field(default_factory=list)
    primary_moods: List[str] = Field(default_factory=list)

class LinguisticDialectProfile(BaseModel):
    recommended_hindustani_register: str = "balanced literary Hindustani"
    regional_cadence: str = "neutral literary"
    acceptable_loanwords: List[str] = Field(default_factory=list)
    proverb_transposition_style: str = "sense-for-sense cultural equivalent"

class DeepSearchNovelDossier(BaseModel):
    book_title: str
    author: str
    project_slug: str = "novel"
    literary_dna: LiteraryDNAProfile = Field(default_factory=LiteraryDNAProfile)
    characters: List[CanonicalCharacter] = Field(default_factory=list)
    world_acoustics: WorldAcousticSetting = Field(default_factory=WorldAcousticSetting)
    musical_tradition: MusicalTradition = Field(default_factory=MusicalTradition)
    linguistic_dialect: LinguisticDialectProfile = Field(default_factory=LinguisticDialectProfile)
    world_lore_entities: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    research_summary: str = ""
    search_citations: List[str] = Field(default_factory=list)

class NovelDeepSearchEngine:
    def __init__(self, model: Optional[str] = None): ...
    @classmethod
    def research_novel(
        cls, title: str, author: str, sample_text: str = "", project_slug: str = "",
        call_llm_fn: Optional[Callable[..., Any]] = None, model: Optional[str] = None
    ) -> DeepSearchNovelDossier: ...
    def conduct_deepsearch(
        self, title: str, author: str, sample_text: str = "", project_slug: str = "",
        call_llm_fn: Optional[Callable[..., Any]] = None, lexical_index: Optional[Any] = None
    ) -> DeepSearchNovelDossier: ...
    @classmethod
    def verify_against_corpus(
        cls, dossier: DeepSearchNovelDossier, lexical_index: Optional[Any] = None
    ) -> Tuple[List[CanonicalCharacter], List[Dict[str, Any]]]: ...
```

#### 4. Vocal Acoustic Director ([`audiobook_factory.preproduction.vocal_acoustic_director`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/vocal_acoustic_director.py))

Pure vocals-only acoustic environment designer, room impulse reverberation modeler, and 4D parametric EQ formant filter complex builder.

```python
class VocalSpaceProfile(BaseModel):
    reverb_type: str = "medium_room"
    wet_mix: float = Field(default=0.12, ge=0.01, le=0.45)
    predelay_ms: int = Field(default=18, ge=2, le=80)
    decay_time_s: float = Field(default=1.2, ge=0.2, le=5.0)
    proximity_staging: Literal[
        "intimate_whisper", "conversational_close", "medium_room",
        "spatial_echo", "distant_shout", "direct_voice", "dry_outdoor"
    ] = "conversational_close"
    high_shelf_damping_db: float = -1.5
    low_shelf_warmth_db: float = 0.0
    dominant_materials: List[str] = Field(default_factory=lambda: ["wood", "stone", "cloth"])

class VocalSpacesManifest(BaseModel):
    project_id: str
    book_title: str
    primary_era: str = "universal_contemporary"
    spaces: Dict[str, VocalSpaceProfile] = Field(default_factory=dict)
    def to_legacy_sonic_bible(self) -> Dict[str, Any]: ...

class VocalAcousticDirector:
    def __init__(self, model: Optional[str] = None): ...
    def design_vocal_spaces(
        self, novel_text_sample: str, book_metadata: Dict[str, Any],
        call_llm_fn: Optional[Callable[..., Any]] = None
    ) -> VocalSpacesManifest: ...
    @classmethod
    def build_vocal_filter_complex(
        cls, character_entity: Optional[Any] = None, space_name: str = "",
        spaces_manifest: Optional[VocalSpacesManifest] = None,
        pitch_shift_pct: Optional[float] = None, tempo_scale: Optional[float] = None,
        eq_formant: Optional[str] = None
    ) -> str: ...
    @classmethod
    def build_room_reverb_filter(cls, space_profile: VocalSpaceProfile) -> str: ...
```

#### 5. Additional Pre-Production Agents & Orchestrator
- [`BookDNAAgent`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/book_dna_agent.py#L29):
  - `analyze_book_dna(novel_text_sample: str, book_metadata: Dict[str, Any], call_llm_fn: Optional[Callable] = None, enable_web_research: bool = True) -> Dict[str, Any]`
- [`DramatisPersonaeAgent`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/dramatis_personae_agent.py#L21):
  - `extract_dramatis_personae(novel_text_sample: str, book_metadata: Dict[str, Any], book_dna: Optional[Dict] = None, call_llm_fn: Optional[Callable] = None) -> List[Dict[str, Any]]`
- [`PhoneticLexiconDramaturge`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/phonetic_lexicon_dramaturge.py#L20):
  - `extract_lexicon_and_phonetics(novel_text_sample: str, book_metadata: Dict[str, Any], call_llm_fn: Optional[Callable] = None) -> Dict[str, Any]`
- [`SonicWorldArchitect`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/sonic_world_architect.py#L21):
  - `design_sonic_bible(novel_text_sample: str, book_metadata: Dict[str, Any], call_llm_fn: Optional[Callable] = None) -> Dict[str, Any]`
- [`PreProductionSupervisor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/preproduction/preproduction_supervisor.py#L36):
  - `execute_preproduction(project_dir: Path | str, force: bool = False, call_llm_fn: Optional[Callable] = None) -> Dict[str, Any]`
  - Helper: `run_preproduction(project_dir: Path | str, force: bool = False, model: Optional[str] = None) -> Dict[str, Any]`

---

### System 2: Canonical Metadata & State Maintainer

#### 1. Centralized Book Bible Models ([`audiobook_factory.metadata.book_bible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py))

```python
class EpistemicProvenance(BaseModel):
    """Forensic provenance tracking entity origin: text-extracted, web-verified, or derived."""
    origin: Literal["CORPUS_EXTRACTED", "WEB_VERIFIED", "INFERRED_DERIVED"] = "CORPUS_EXTRACTED"
    first_chapter: int = 1
    corpus_mention_count: int = 1
    evidence_quote: str = ""
    web_citation: Optional[str] = None

class BookEntity(BaseModel):
    canonical_id: str = ""
    english_name: str
    hindi_name: str = ""
    taxonomy: Literal["PROPER_NAME", "HERALDIC_MONIKER", "OCCUPATIONAL_ROLE"] = "PROPER_NAME"
    aliases: List[str] = Field(default_factory=list)
    category: str = "character"
    gender: Optional[str] = None
    is_child: bool = False
    vocal_weight: str = "authoritative"
    description: str = ""
    first_appearance_chapter: int = 1
    pronunciation_hint: str = ""
    sociolect_archetype: Optional[str] = "NEUTRAL"
    default_honorific_level: Optional[str] = "tum"
    speech_quirks: str = ""
    language_profile: Optional[Dict[str, Any]] = None
    is_canonical: bool = True
    confidence: float = 1.0
    provenance: EpistemicProvenance = Field(default_factory=EpistemicProvenance)

    # 4D Acoustic Voice Allocation
    assigned_voice: Optional[str] = None
    pitch_shift_pct: float = 0.0
    tempo_scale: float = 1.0
    eq_formant: str = ""

# Backward-compatibility type aliases
CharacterEntry = BookEntity
NovelEntity = BookEntity

class DynamicRelationship(BaseModel):
    from_entity: str
    to_entity: str
    default_pronoun: str = "tum"
    current_pronoun: str = "tum"
    respect_level: int = 3
    intimacy_level: int = 2
    hostility_level: int = 0
    authority_level: int = 0
    notes: str = ""
    evidence_log: List[str] = Field(default_factory=list)

class WorldRule(BaseModel):
    rule_id: str
    category: str = "general"
    statement: str
    immutable: bool = True

class FlaggedConflict(BaseModel):
    entity_or_concept: str
    source_chapter: int = 1
    conflict_type: str
    description: str = ""
    candidate_data: Dict[str, Any] = Field(default_factory=dict)
    resolved: bool = False
    resolution_notes: str = ""

class BookBible(BaseModel):
    schema_version: str = "2.0.0"
    book_title: str = "Unknown"
    author: str = "Unknown"
    narrative_voice: str = "Neutral literary dramatic Hindustani"
    characters: Dict[str, BookEntity] = Field(default_factory=dict)
    locations: Dict[str, str] = Field(default_factory=dict)
    organizations: Dict[str, str] = Field(default_factory=dict)
    creatures: Dict[str, str] = Field(default_factory=dict)
    objects: Dict[str, str] = Field(default_factory=dict)
    titles: Dict[str, str] = Field(default_factory=dict)
    terminology: Dict[str, str] = Field(default_factory=dict)
    terminology_variants: Dict[str, str] = Field(default_factory=dict)
    relationships: List[DynamicRelationship] = Field(default_factory=list)
    world_rules: List[WorldRule] = Field(default_factory=list)
    flagged_conflicts: List[FlaggedConflict] = Field(default_factory=list)
    candidate_entities: List[BookEntity] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def find_character(self, name: str) -> Optional[BookEntity]: ...
    def find_place(self, name: str) -> Optional[str]: ...
    def find_language_profile(self, name: str) -> Any: ...
    def is_hard_canon_entity(self, name: str) -> bool: ...
    def get_immutable_world_rules(self) -> List[WorldRule]: ...
    def get_version_hash(self) -> str: ...
    def get_canonical_lexicon(self) -> Dict[str, str]: ...
    def sync_pronunciation_lexicon(self, project_dir: Path) -> Any: ...
    def export_legacy_glossary(self) -> Dict[str, Any]: ...
    def save(self, project_dir: Path) -> None: ...
    @classmethod
    def load_from_project(cls, project_dir: Path) -> BookBible: ...
    def import_legacy_glossary(self, glossary_path: Path) -> None: ...
    def propose_new_entity(self, entity: BookEntity, chapter_num: int) -> bool: ...
```

#### 2. Master State Maintainer ([`audiobook_factory.metadata.state_maintainer`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/state_maintainer.py))

```python
class MasterPreProductionState(BaseModel):
    """Immutable container of all locked novel pre-production assets."""
    project_slug: str
    book_title: str
    book_dna: Dict[str, Any] = Field(default_factory=dict)
    book_bible: BookBible
    vocal_spaces: Any = Field(default=None)
    cast_lock: Dict[str, Any] = Field(default_factory=dict)
    voice_registry: Dict[str, Any] = Field(default_factory=dict)
    character_roster: Dict[str, Any] = Field(default_factory=dict)
    sonic_bible: Dict[str, Any] = Field(default_factory=dict)

class NovelStateMaintainer:
    """
    Central Persistence & Master State Manager for Novel Research & Pre-Production.
    Guarantees atomic multi-file commit and bidirectional synchronization.
    """
    @classmethod
    def commit_master_preproduction(
        cls,
        project_dir: Path | str,
        book_metadata: Dict[str, Any],
        book_dna: Dict[str, Any],
        book_bible: BookBible,
        vocal_spaces: VocalSpacesManifest,
        roster: Dict[str, Any],
        voice_registry: Dict[str, Any],
        cast_lock: Dict[str, Any],
    ) -> MasterPreProductionState:
        """
        Executes a transactional, atomic multi-file commit of all pre-production master assets.
        Implements NR-GATE-06: All files are staged and atomically swapped into place.
        Windows 11 Hardening: 5-attempt retry loop on os.replace eliminates WinError 5/32.
        """
        ...

    @classmethod
    def discover_and_lock_character(
        cls,
        project_dir: Path | str,
        speaker_name: str,
        gender: Optional[str] = None,
        use_hindi: Optional[bool] = None,
        book_bible: Optional[BookBible] = None,
    ) -> Dict[str, Any]:
        """
        Dynamically registers, casts, and locks an emerging novel character under _STATE_LOCK.
        Enforces NR-GATE-03 >= 4% pitch distance and [0.70, 1.30] pitch bounds.
        """
        ...

    @classmethod
    def load_master_state(cls, project_dir: Path | str) -> Optional[MasterPreProductionState]:
        """Loads and validates all preproduction master state files for a project."""
        ...
```

---

## 📚 Standalone Chapter Glossary & Metadata Subsystem ([`audiobook_factory.glossary`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/))

*(See full architectural manual: [`docs/GLOSSARY_AND_METADATA_SUBSYSTEM.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/GLOSSARY_AND_METADATA_SUBSYSTEM.md))*

> [!NOTE]
> **Room 1.5 Architectural Isolation**: The glossary package operates as an independent, single-pass per-chapter lexical analysis hub.
> It maintains **100% zero imports** from downstream audio (`audiobook_factory.audio`), speech synthesis (`audiobook_factory.tts`), screenplay (`audiobook_factory.screenplay`), or unmetered networking (`urllib.request`, `requests`, `httpx`). All LLM operations route exclusively through `ModelGateway` via [`execute_glossary_llm()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/gateway_bridge.py#L26).

### 1. Data Contracts ([`audiobook_factory.glossary.contracts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/contracts.py))

#### `EntityCategory`
```python
EntityCategory = Literal[
    "PROPER_NAME",        # Personal name -> Phonetic Devanagari transliteration
    "HERALDIC_MONIKER",  # Formal title / moniker -> Phonetic Devanagari (Calques strictly banned)
    "OCCUPATIONAL_ROLE", # Situational role / descriptor -> Spoken natural Hindustani translation
    "LOCATION",          # Geographic location -> Devanagari translation / transliteration
    "LORE_TERM",         # Lore / fantasy term -> Devanagari equivalent
]
```

#### `ChapterEntity`
```python
class ChapterEntity(BaseModel):
    """
    Standardized entity record discovered in chapter text.
    """
    model_config = ConfigDict(extra="ignore")

    canonical_id: str = Field(..., description="Unique snake_case identifier (e.g. 'lord_corwin')")
    english_name: str = Field(..., description="Canonical English name or moniker")
    hindi_name: str = Field(..., description="Phonetic Devanagari transliteration or evocative Hindustani translation")
    category: EntityCategory = Field(default="PROPER_NAME", description="Tri-Partite entity classification")
    aliases: List[str] = Field(default_factory=list, description="All situational nicknames, aliases, and titles")
    gender: Literal["male", "female", "neutral", "unknown"] = Field(default="unknown")
    voice_style: str = Field(default="", description="Descriptive vocal acting hint or acoustic demeanor")
    sociolect_archetype: str = Field(default="NEUTRAL", description="Hindustani dialect/social register archetype")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    first_appearance_chapter: int = Field(default=1, ge=1)
    is_canonical: bool = Field(default=True)
```

#### `ChapterGlossary`
```python
class ChapterGlossary(BaseModel):
    """
    Immutable, self-contained glossary snapshot for a single chapter.
    Serves as the single source of truth for:
    - Room 2 (Translation): dynamic_glossary (en -> hi dictionary)
    - Room 3 (Dramaturgy): scene characters & known entity list
    - Room 3 (Scripting): character_roster.json with unified aliases
    - Room 4 (Voice Casting): cast_lock sync candidates
    """
    model_config = ConfigDict(extra="ignore")

    chapter_num: int = Field(..., ge=0, description="1-indexed chapter number (0 for front matter)")
    chapter_id: str = Field(default="", description="Chapter identifier slug (e.g. 'chapter_004')")
    entities: Dict[str, ChapterEntity] = Field(default_factory=dict, description="Active character and person entities")
    locations: Dict[str, str] = Field(default_factory=dict, description="English location name -> Devanagari translation")
    terminology: Dict[str, str] = Field(default_factory=dict, description="English fantasy/lore term -> Devanagari translation")
    version_hash: str = Field(default="", description="Deterministic SHA-256 fingerprint of glossary content")
    total_entities: int = Field(default=0)

    def compute_hash(self) -> str:
        """Computes a deterministic 16-char SHA-256 fingerprint of the glossary content."""

    def to_translation_glossary(self) -> Dict[str, str]:
        """Projects glossary into a clean English -> Hindi mapping for TranslationRequest.dynamic_glossary."""

    def to_scripting_roster(self, use_hindi: bool = True) -> Dict[str, Any]:
        """
        Projects glossary into standard character_roster schema consumed by
        DialogueAttributionAuditor and dialogue_parser. Ensures unified alias maps prevent false speaker flips.
        """

    def to_dramaturgy_characters(self) -> List[str]:
        """Returns list of all active character names for scene segmentation."""

    def save_to_file(self, path: Path | str) -> None:
        """Atomically persists glossary to JSON on disk via temporary UUID file."""

    @classmethod
    def load_from_file(cls, path: Path | str) -> ChapterGlossary:
        """Loads glossary from JSON file."""
```

---

### 2. Chapter Lexical Scanner ([`audiobook_factory.glossary.scanner`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/scanner.py))

#### `CandidateEntity`
```python
class CandidateEntity(BaseModel):
    """Raw entity candidate extracted from chapter text prior to LLM classification."""
    name: str
    frequency: int = 1
    sample_context: str = ""
    suggested_category: str = "character"
    confidence: float = 0.85
    is_multiword: bool = False
    has_mid_sentence: bool = False
```

#### `ChapterLexicalScanner`
```python
class ChapterLexicalScanner:
    """
    Zero-token lexical extraction engine for chapter text.
    Sweeps text in under 15ms, filters 130+ non-entity stopwords, and cross-references
    against BookBible to guarantee zero LLM token consumption on known vocabularies.
    """

    @classmethod
    def scan_chapter_text(
        cls,
        text: str,
        known_lexicon: Optional[Set[str]] = None,
        book_bible: Optional[BookBible] = None,
        min_frequency: int = 2,
    ) -> List[CandidateEntity]:
        """
        Scans chapter text for uncataloged capitalized noun phrases and monikers.
        Filters known entities from book_bible / known_lexicon.
        Returns a sorted list of uncataloged candidate entities.
        """
```

---

### 3. Glossary Classifier & Taxonomy ([`audiobook_factory.glossary.classifier`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/classifier.py))

#### `TRI_PARTITE_SYSTEM_PROMPT`
Authoritative system instruction enforcing the 3-tier entity taxonomy:
1. `PROPER_NAME`: Phonetic Devanagari transliteration (*Edward* $\to$ *एडवर्ड*).
2. `HERALDIC_MONIKER`: Phonetic Devanagari transliteration (*Silver Falcon* $\to$ *सिल्वर फाल्कन*). Literal word-for-word calques (*चांदी का बाज़*) are strictly forbidden.
3. `OCCUPATIONAL_ROLE`: Spoken natural Hindustani translation (*The Stranger* $\to$ *अजनबी*, *The Butcher* $\to$ *कसाई*).
4. Alias Unification: Links situational roles to true names to eliminate multi-actor voice splits.

#### `GlossaryClassifier`
```python
class GlossaryClassifier:
    """
    Classifies raw candidate entities and extracts Devanagari equivalents.
    Handles resilient unwrapping across multiple JSON keys (characters, entities, candidates, data)
    and separates discovered geographic terms from lore terminology.
    """

    @classmethod
    def classify_candidates(
        cls,
        candidates: List[CandidateEntity],
        chapter_text: str,
        chapter_num: int = 1,
        known_characters: Optional[List[str]] = None,
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> Tuple[List[ChapterEntity], Dict[str, str], Dict[str, str]]:
        """
        Classifies candidate entities using ModelGateway.
        Returns:
            (discovered_characters, locations_map, terminology_map)
        """
```

---

### 4. Control Plane Gateway Bridge ([`audiobook_factory.glossary.gateway_bridge`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/gateway_bridge.py))

#### `execute_glossary_llm`
```python
def execute_glossary_llm(
    prompt: str,
    system_instruction: Optional[str] = None,
    task: str = "extraction",
    model: Optional[str] = None,
    temperature: float = 0.10,
    max_output_tokens: Optional[int] = 8192,
    session_id: Optional[str] = None,
    user_id: str = "glossary_worker",
    json_mode: bool = True,
    **kwargs: Any,
) -> Union[Dict[str, Any], List[Any], str]:
    """
    Executes a Room 1.5 Glossary LLM request strictly through ModelGateway.
    Acquires Concurrency=1 atomic key leases via KeyLeaseManager.
    Enforces AntiBanGuard 11.0 RPM pacing, official stealth SDK headers ('x-goog-api-client'),
    session affinity, and BLOCK_NONE creative fiction safety framing.
    Fails closed with RuntimeError if ModelGateway is unavailable.
    Returns parsed JSON object/list or raw string, with automatic json_repair fallback.
    """
```

---

### 5. Unified Glossary Manager ([`audiobook_factory.glossary.manager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/manager.py))

#### `GlossaryManager`
```python
class GlossaryManager:
    """
    Central Coordinator for Chapter-Level Glossary, Metadata & Entity Synchronization.
    Coordinates zero-token lexical scanning, LLM classification, BookBible updates,
    and NovelStateMaintainer dynamic casting in a single pass.
    """

    @classmethod
    def scan_and_sync_chapter(
        cls,
        chapter_text: str,
        project_dir: Optional[Union[Path, str]] = None,
        chapter_num: int = 1,
        chapter_id: Optional[str] = None,
        book_bible: Optional[BookBible] = None,
        call_llm_fn: Optional[Callable[..., Any]] = None,
        min_frequency: int = 2,
        force_classification: bool = False,
    ) -> ChapterGlossary:
        """
        Executes single-pass chapter lexical analysis:
        1. Fast zero-token regex scan against known lexicon in BookBible.
        2. Dispatches uncataloged candidates to GlossaryClassifier via ModelGateway.
        3. Updates BookBible, dynamic voice allocation (cast_lock.json), and persists state.
        4. Writes durable chapter glossary artifact: glossary/chapter_XXX_glossary.json.
        """

    @classmethod
    def get_chapter_glossary(
        cls,
        chapter_num: int,
        project_dir: Union[Path, str],
    ) -> Optional[ChapterGlossary]:
        """Loads existing chapter glossary artifact from disk if present."""

    @classmethod
    def export_for_translation(
        cls,
        chapter_num: int,
        project_dir: Union[Path, str],
        chapter_text: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Exports a flat English -> Hindi translation glossary for
        TranslationRequest.dynamic_glossary.
        """

    @classmethod
    def export_for_scripting(
        cls,
        chapter_num: int,
        project_dir: Union[Path, str],
        use_hindi: bool = True,
    ) -> Dict[str, Any]:
        """
        Exports structured character_roster schema consumed by
        DialogueAttributionAuditor and dialogue_parser.
        """
```

---

## 🧠 Literary Translation Intelligence & Memory 2.0 ([`audiobook_factory.translation`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/))

*(See full architectural manual: [`docs/LITERARY_TRANSLATION_INTELLIGENCE.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/LITERARY_TRANSLATION_INTELLIGENCE.md))*

> [!NOTE]
> Canonical novel data models ([`BookBible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py#L184) and [`BookEntity`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py#L26)) are centrally defined in [`audiobook_factory.metadata.book_bible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py).
> The translation package re-exports them via [`audiobook_factory.translation.book_bible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/book_bible.py) for 100% backward compatibility.

### 1. `BookBible` & `BookEntity` ([`audiobook_factory.translation.book_bible`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/translation/book_bible.py))
*Persistent canonical repository (`book_bible.json`) with SHA-256 versioning and one-way legacy glossary projection.*

```python
class BookEntity(BaseModel):
    canonical_en: str
    canonical_hi: str
    category: Literal["character", "location", "organization", "creature", "object", "title"] = "character"
    gender: Literal["male", "female", "neutral", "unknown"] = "unknown"
    aliases_en: List[str] = []
    aliases_hi: List[str] = []
    forbidden_variants: List[str] = []
    social_class: str = "standard"
    archetype: str = "NEUTRAL"
    speech_register: str = "standard_literary"
    voice_notes: str = ""
    first_seen_chapter: int = 1
    confidence: float = 1.0
    locked: bool = False

class BookBible(BaseModel):
    schema_version: str = "2.0.0"
    book_title: str = ""
    genre: str = "fantasy"
    tone_signature: str = "literary_dramatic"
    characters: Dict[str, BookEntity] = {}
    locations: Dict[str, BookEntity] = {}
    organizations: Dict[str, BookEntity] = {}
    creatures: Dict[str, BookEntity] = {}
    objects: Dict[str, BookEntity] = {}
    titles: Dict[str, BookEntity] = {}
    terminology: Dict[str, str] = {}
    terminology_variants: Dict[str, str] = {}  # Forbidden regex -> Canonical Devanagari
    relationships: List[DynamicRelationship] = []
    world_rules: List[WorldRule] = []
    flagged_conflicts: List[FlaggedConflict] = []

    def get_version_hash(self) -> str:
        """Returns a deterministic 16-char SHA-256 digest of all canonical entities and variants."""

    def propose_new_entity(self, entity: BookEntity, chapter_num: int = 1, context_snippet: str = "") -> bool:
        """Auto-commits non-conflicting entities with confidence >= 0.80; logs FlaggedConflict on mismatch."""

    def export_legacy_glossary(self, output_path: Optional[Path] = None) -> Dict[str, str]:
        """Projects canonical entities into flat translation/glossary.json format."""

    @classmethod
    def load(cls, path: Path) -> "BookBible": ...
    def save(self, path: Path) -> None: ...
```

### 2. `HindustaniRegisterEngine`, `CharacterLanguageProfile` & `RelationshipStateEngine`
*Contextual Urdu seasoning, sociolect archetypes, and 7D pronoun honorific resolution (`आप` / `तुम` / `तू`).*

```python
# audiobook_factory/translation/hindustani_register.py
class HindustaniRegisterEngine:
    @classmethod
    def from_genre(cls, genre: str) -> "HindustaniRegisterEngine": ...
    def build_prompt_directive(self, scene_intensity: Optional[Dict[str, float]] = None) -> str: ...
    def audit_text(self, hindi_text: str) -> HindustaniAuditResult: ...

# audiobook_factory/translation/character_profile.py
class CharacterLanguageProfile(BaseModel):
    character_name: str
    archetype: str = "NEUTRAL"
    sociolect: str = "standard_literary"
    sentence_tempo: Literal["clipped", "measured", "melodic", "hurried"] = "measured"
    discourse_markers_hi: List[str] = []
    signature_expressions_hi: List[str] = []

# audiobook_factory/translation/relationship_state.py
class DynamicRelationshipState(BaseModel):
    speaker: str
    listener: str
    respect: float = 0.0                # [-5.0, +5.0]
    familiarity: float = 0.0            # [0.0, 5.0]
    hostility: float = 0.0              # [0.0, 5.0]
    intimacy: float = 0.0               # [0.0, 5.0]
    authority_differential: float = 0.0 # [-5.0, +5.0]
    fear: float = 0.0                   # [0.0, 5.0]
    trust: float = 0.0                  # [-5.0, +5.0]

class RelationshipStateEngine:
    @staticmethod
    def resolve_pronoun_level(state: DynamicRelationshipState) -> Literal["aap", "tum", "tu"]: ...
    @staticmethod
    def apply_relationship_mutation(
        state: DynamicRelationshipState,
        interaction_type: str,
        event_id: str,
        chapter_num: int,
    ) -> DynamicRelationshipState: ...
```

### 3. `LiteraryIntensityVector`, `ScenePlanner` & `SourceSemanticMap`
*7D maturity vector ("Nothing Above Source"), transition-driven scene segmentation, and frozen proposition maps.*

```python
# audiobook_factory/translation/intensity_model.py
class LiteraryIntensityVector(BaseModel):
    profanity: float = 0.0              # [0.0, 5.0]
    sexual_intimacy: float = 0.0        # [0.0, 5.0]
    violence: float = 0.0               # [0.0, 5.0]
    emotional_intensity: float = 1.0    # [0.0, 5.0]
    formality: float = 2.5              # [0.0, 5.0]
    urdu_register: float = 2.0          # [0.0, 5.0]
    colloquiality: float = 2.0          # [0.0, 5.0]

class IntensityEvaluator:
    SOFT_WARN_DELTA: float = 0.75       # Non-blocking calibration notice
    HARD_FAIL_DELTA: float = 2.00       # Hard Gate T8 rejection threshold

    @classmethod
    def compare_vectors(cls, source: LiteraryIntensityVector, target: LiteraryIntensityVector) -> Dict[str, Any]: ...

# audiobook_factory/translation/scene_planner.py
class ScenePlanner:
    @classmethod
    def plan_chapter(cls, chapter_text: str, chapter_num: int, known_characters: Optional[List[str]] = None) -> ChapterPlan: ...

# audiobook_factory/translation/source_semantic_map.py
class SourceSemanticMapEngine:
    @classmethod
    def extract_semantic_map(cls, scene_id: str, chapter_num: int, source_text: str, known_entities: Optional[List[str]] = None) -> SourceSemanticMap: ...
```

### 4. `TranslationEngine`, `contracts.py` & Deterministic Parity Gates (Option D Standalone Architecture)
*Decoupled text-to-text translation engine, typed Pydantic contracts, bilingual macro-chunker, and full-text parity verification.*

```python
# audiobook_factory/translation/contracts.py
class FidelityTier(str, Enum):
    RAW_UNRATED = "RAW_UNRATED"
    CLASSIC_REVERENT = "CLASSIC_REVERENT"

class TranslationRequest(BaseModel):
    source_text: str
    source_title: str = ""
    tier: FidelityTier = FidelityTier.RAW_UNRATED
    book_bible_path: Optional[str] = None
    dynamic_glossary: Dict[str, str] = {}
    chunk_size_words: int = 1800
    thinking_budget: int = 1024
    source_language: str = "en"
    target_language: str = "hi"

class TranslationResult(BaseModel):
    translated_markdown: str
    alignments: List[ParagraphAlignment] = []
    parity: ParityMetrics
    new_entities_discovered: Dict[str, str] = {}
    total_chunks: int = 1
    llm_calls_made: int = 1
    elapsed_seconds: float = 0.0

# audiobook_factory/translation/engine.py
class TranslationEngine:
    def __init__(
        self,
        llm_fn: Optional[Callable[[str, Optional[int], Optional[float]], str]] = None,
        model_name: str = "gemini-2.5-flash",
    ): ...

    def translate(self, request: TranslationRequest) -> TranslationResult:
        """Executes macro-chunking, single-pass Gemini Flash translation with thinking budget,
        and deterministic parity verification in a completely standalone environment."""
```

### 5. World & Character Memory 2.0 ([`audiobook_factory.translation.memory`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/translation/memory/))
*(See complete specification: [`docs/WORLD_AND_CHARACTER_MEMORY_2_0.md`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/docs/WORLD_AND_CHARACTER_MEMORY_2_0.md))*

*Event-driven narrative continuity, epistemic isolation (`MUST_NOT_KNOW`), dual-chronology validation, and performance guidance.*

```python
# audiobook_factory/translation/memory/state.py
def apply_character_delta(character_states: Dict[str, CharacterState], world_state: WorldState, delta: StateDelta) -> CharacterState: ...
def apply_relationship_delta(relationships: Dict[str, DynamicRelationshipState], delta: StateDelta) -> DynamicRelationshipState: ...
def apply_knowledge_delta(facts_registry: Dict[str, KnowledgeFact], character_states: Dict[str, CharacterState], delta: StateDelta) -> KnowledgeFact: ...
def apply_world_or_narrative_delta(world_state: WorldState, character_states: Dict[str, CharacterState], delta: StateDelta) -> None: ...
def record_events_on_timeline(world_state: WorldState, events: List[StoryEvent], chapter: int, scene: str, location: str = "Unspecified", time_marker: str = "Unspecified") -> None: ...

# audiobook_factory/translation/memory/events.py
class StoryEventType(str, Enum):
    CHARACTER_INTRODUCED = "CHARACTER_INTRODUCED"
    CHARACTER_MOVED = "CHARACTER_MOVED"
    CHARACTER_INJURED = "CHARACTER_INJURED"
    CHARACTER_RECOVERED = "CHARACTER_RECOVERED"
    CHARACTER_DIED = "CHARACTER_DIED"
    SECRET_REVEALED = "SECRET_REVEALED"
    FACT_LEARNED = "FACT_LEARNED"
    FACT_DISPROVEN = "FACT_DISPROVEN"
    RELATIONSHIP_CHANGED = "RELATIONSHIP_CHANGED"
    BETRAYAL = "BETRAYAL"
    RECONCILIATION = "RECONCILIATION"
    ROMANTIC_CONFESSION = "ROMANTIC_CONFESSION"
    SHARED_DANGER = "SHARED_DANGER"
    THREAT_ISSUED = "THREAT_ISSUED"
    OBJECT_ACQUIRED = "OBJECT_ACQUIRED"
    OBJECT_TRANSFERRED = "OBJECT_TRANSFERRED"
    OBJECT_LOST = "OBJECT_LOST"
    LOCATION_CHANGED = "LOCATION_CHANGED"
    PROMISE_CREATED = "PROMISE_CREATED"
    PROMISE_BROKEN = "PROMISE_BROKEN"
    MYSTERY_INTRODUCED = "MYSTERY_INTRODUCED"
    MYSTERY_RESOLVED = "MYSTERY_RESOLVED"
    GOAL_CHANGED = "GOAL_CHANGED"
    BELIEF_CHANGED = "BELIEF_CHANGED"
    WORLD_STATE_CHANGED = "WORLD_STATE_CHANGED"
    OTHER = "OTHER"

class TemporalMode(str, Enum):
    PRESENT = "PRESENT"
    FLASHBACK = "FLASHBACK"
    MEMORY_DREAM = "MEMORY_DREAM"
    HISTORICAL_NARRATION = "HISTORICAL_NARRATION"
    NON_LINEAR = "NON_LINEAR"

class StoryEvent(BaseModel):
    event_id: str = ""
    chapter: int = 1
    scene: str = "scene_001"
    event_type: StoryEventType = StoryEventType.OTHER
    description: str
    participants: List[str] = []
    location: str = "Unspecified"
    source_reference: str = ""
    importance: int = 3
    temporal_mode: TemporalMode = TemporalMode.PRESENT
    salience_score: float = 0.5
    emotional_valence: Any = 0.0
    dramatic_tags: List[str] = []
    is_resolved: bool = False
    metadata: Dict[str, Any] = {}

class SceneChangeDetector:
    @classmethod
    def detect_temporal_mode(cls, text: str) -> Tuple[TemporalMode, Optional[int], str]: ...
    @classmethod
    def assess_scene(cls, scene_text: str, known_characters: Optional[List[str]] = None, chapter: int = 1, scene_id: str = "scene_001", active_characters: Optional[List[str]] = None, location: str = "Unspecified", known_objects: Optional[List[str]] = None, previous_location: Optional[str] = None) -> SceneChangeAssessment: ...

class EventExtractor:
    @classmethod
    def extract_scene_events(cls, scene_text: str, chapter: int = 1, scene_id: str = "scene_001", active_characters: Optional[List[str]] = None, known_characters: Optional[List[str]] = None, location: str = "Unspecified", known_objects: Optional[List[str]] = None, previous_location: Optional[str] = None, call_llm_fn: Optional[Callable[..., str]] = None, model: Optional[str] = None, force_llm: bool = False) -> Tuple[List[StoryEvent], SceneChangeAssessment]: ...
    @classmethod
    def propose_events_llm(cls, scene_text: str, chapter: int, scene_id: str, active_characters: List[str], location: str, default_temporal_mode: TemporalMode, call_llm_fn: Callable[..., str]) -> List[StoryEvent]: ...

# audiobook_factory/translation/memory/character_memory.py
class KnowledgeStatus(str, Enum):
    KNOWN = "KNOWN"
    SUSPECTED = "SUSPECTED"
    FALSE_BELIEF = "FALSE_BELIEF"
    UNKNOWN = "UNKNOWN"
    DISPROVEN = "DISPROVEN"

class KnowledgeFact(BaseModel):
    fact_id: str
    subject: str
    predicate: str
    value: str
    confidence: float = 1.0
    source_event: str
    learned_at: str = "ch001_scene_001"
    known_by: List[str] = []
    status: KnowledgeStatus = KnowledgeStatus.KNOWN
    character_statuses: Dict[str, KnowledgeStatus] = {}

class CharacterState(BaseModel):
    character_name: str
    is_alive: bool = True
    current_location: str = "Unspecified"
    current_emotion: str = "neutral"
    emotion_intensity: float = 0.5
    physical_condition: str = "healthy"
    active_injuries: List[str] = []
    energy: float = 0.8
    immediate_goal: str = ""
    known_facts: List[str] = []
    suspected_facts: List[str] = []
    false_beliefs: List[str] = []
    recent_events: List[str] = []
    arc_state: CharacterArcMemory = Field(default_factory=CharacterArcMemory)

class CharacterKnowledgeEngine:
    @staticmethod
    def register_or_update_fact(facts_registry: Dict[str, KnowledgeFact], character_states: Dict[str, CharacterState], fact_id: str, subject: str, predicate: str, value: str, source_event: str, learned_at: str, learners: List[str], status: KnowledgeStatus = KnowledgeStatus.KNOWN, confidence: float = 1.0) -> KnowledgeFact: ...
    @staticmethod
    def get_character_knowledge_status(character_name: str, fact_id: str, facts_registry: Dict[str, KnowledgeFact], character_states: Optional[Dict[str, CharacterState]] = None) -> KnowledgeStatus: ...
    @staticmethod
    def build_epistemic_constraints_for_scene(active_characters: List[str], facts_registry: Dict[str, KnowledgeFact], character_states: Optional[Dict[str, CharacterState]] = None, max_facts_per_bucket: int = 8) -> Dict[str, Dict[str, List[str]]]: ...

# audiobook_factory/translation/memory/memory_delta.py
class DeltaDomain(str, Enum):
    CHARACTER = "CHARACTER"
    RELATIONSHIP = "RELATIONSHIP"
    KNOWLEDGE = "KNOWLEDGE"
    WORLD = "WORLD"
    NARRATIVE = "NARRATIVE"

class StateMutability(str, Enum):
    HARD_CANON = "HARD_CANON"
    SOFT_STATE = "SOFT_STATE"

class StateDelta(BaseModel):
    delta_id: str = ""
    source_event_id: str
    chapter: int = 1
    scene: str = "scene_001"
    domain: DeltaDomain
    mutability: StateMutability = StateMutability.SOFT_STATE
    target_entity: str
    field_name: str
    operation: Literal["set", "add", "remove", "adjust"] = "set"
    old_value: Optional[Any] = None
    new_value: Any = None
    numeric_delta: Optional[float] = None
    temporal_mode: TemporalMode = TemporalMode.PRESENT
    rationale: str = ""
    metadata: Dict[str, Any] = {}

class StateDeltaEngine:
    @classmethod
    def derive_deltas_from_event(cls, event: StoryEvent, existing_relationships: Optional[Dict[str, DynamicRelationshipState]] = None) -> List[StateDelta]: ...
    @classmethod
    def compute_deltas_for_events(cls, events: List[StoryEvent], character_states: Optional[Dict[str, CharacterState]] = None, relationships: Optional[Dict[str, DynamicRelationshipState]] = None, facts_registry: Optional[Dict[str, KnowledgeFact]] = None, world_state: Optional[WorldState] = None) -> List[StateDelta]: ...

# audiobook_factory/translation/memory/memory_validator.py
class ValidationOutcome(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    CONFLICT = "CONFLICT"

class MemoryValidationReport(BaseModel):
    outcome: ValidationOutcome = ValidationOutcome.PASS
    accepted_deltas: List[StateDelta] = []
    rejected_deltas: List[StateDelta] = []
    rejected_event_ids: List[str] = []
    warnings: List[str] = []
    flagged_conflicts: List[FlaggedConflict] = []
    repair_instructions: List[str] = []

class MemoryValidator:
    @classmethod
    def validate_deltas(cls, deltas: List[StateDelta], book_bible: Optional[BookBible], character_states: Dict[str, CharacterState], relationships: Dict[str, DynamicRelationshipState], facts_registry: Dict[str, KnowledgeFact], world_state: WorldState, events_by_id: Optional[Dict[str, StoryEvent]] = None) -> MemoryValidationReport:
        """Enforces 7 contradiction classes (canon, timeline, dead character, physical impossibility, relationship jump, knowledge leakage, world rule)."""

# audiobook_factory/translation/memory/memory_store.py
class MemoryStore(BaseModel):
    schema_version: str = "2.0"
    memory_version: int = 0
    version_hash: str = "genesis"
    character_states: Dict[str, CharacterState] = {}
    relationships: Dict[str, DynamicRelationshipState] = {}
    facts_registry: Dict[str, KnowledgeFact] = {}
    world_state: WorldState = Field(default_factory=WorldState)
    events: Dict[str, StoryEvent] = {}
    rejected_events: Dict[str, StoryEvent] = {}
    commit_history: List[MemoryCommitRecord] = []
    flagged_conflicts: List[FlaggedConflict] = []

    def seed_from_book_bible(self, bible: BookBible) -> None: ...
    def commit_scene_memory(self, scene_id: str, chapter: int, events: List[StoryEvent], deltas: Optional[List[StateDelta]] = None, source_text: str = "", book_bible: Optional[BookBible] = None, location: str = "Unspecified", time_marker: str = "Unspecified") -> MemoryValidationReport: ...
    def trace_mutations(self, entity_name: Optional[str] = None, chapter: Optional[int] = None, scene_id: Optional[str] = None, domain: Optional[DeltaDomain] = None) -> List[StateDelta]: ...
    def save(self, path: Path) -> None: ...
    @classmethod
    def load(cls, path: Path, book_bible: Optional[BookBible] = None) -> MemoryStore: ...

# audiobook_factory/translation/memory/memory_retriever.py & memory_context.py
class MemoryContext(BaseModel):
    chapter: int = 1
    scene_id: str = "scene_01"
    location_name: str = "Unspecified"
    temporal_mode: TemporalMode = TemporalMode.PRESENT
    canon_identities: List[Dict[str, Any]] = []
    relevant_world_rules: List[str] = []
    active_character_states: Dict[str, CharacterState] = {}
    active_relationships: List[DynamicRelationshipState] = []
    epistemic_constraints: Dict[str, Dict[str, List[str]]] = {}
    location_state: Optional[LocationState] = None
    relevant_objects: List[ObjectState] = []
    recent_events: List[StoryEvent] = []
    salient_events: List[StoryEvent] = []
    unresolved_threads: List[NarrativeThreadState] = []

    @property
    def high_salience_events(self) -> List[StoryEvent]: ...
    def enforce_token_budget(self, max_token_budget: int = 800) -> "MemoryContext": ...
    def get_character_performance_guidance(self, speaker: str, target: Optional[str] = None) -> Dict[str, Any]: ...
    def apply_performance_guidance_to_segment(self, seg_dict: Dict[str, Any], target_speaker: Optional[str] = None) -> Dict[str, Any]: ...
    def get_prompt_context(self) -> str: ...

class MemoryRetriever:
    @classmethod
    def infer_active_entities(cls, scene_text: str, store: MemoryStore, book_bible: Optional[BookBible] = None, explicit_characters: Optional[List[str]] = None, explicit_location: Optional[str] = None) -> Tuple[List[str], str]: ...
    @classmethod
    def retrieve_for_scene(cls, store: MemoryStore, book_bible: Optional[BookBible] = None, chapter: int = 1, scene_id: str = "scene_01", active_characters: Optional[List[str]] = None, location: Optional[str] = None, active_location: Optional[str] = None, scene_text: str = "", max_recent_events: int = 5, max_salient_events: int = 4, max_token_budget: int = 800) -> MemoryContext: ...
```

---

## 🎹 15. Sonic Intelligence Engine (Phases 1–3)

### A. Phase 3 Retrieval Contracts ([`audiobook_factory.contracts`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/contracts.py))

```python
# audiobook_factory/sonic_query_planner.py
class IntentType(str, Enum):
    FOLEY_IMPACT = "foley_impact"
    FOLEY_MOVEMENT = "foley_movement"
    ENVIRONMENT_BED = "environment_bed"
    WEATHER_MACRO = "weather_macro"
    CREATURE_VOCAL = "creature_vocal"
    WEAPON_BLADE = "weapon_blade"
    WEAPON_BLUNT = "weapon_blunt"
    MAGIC_SPELL = "magic_spell"
    DOMESTIC_OBJECT = "domestic_object"
    MUSICAL_UNDERSCORE = "musical_underscore"
    VOCAL_ACTING = "vocal_acting"
    MECHANICAL_CONTRIVANCE = "mechanical_contrivance"
    WATER_LIQUID = "water_liquid"
    EXPLOSION_CONCUSSION = "explosion_concussion"
    GENERAL_SFX = "general_sfx"

class AtomicSoundConcept(BaseModel):
    concept_id: str
    description: str
    primary_intent: IntentType
    keywords: List[str] = []
    category_hint: Optional[str] = None
    exciter_hint: Optional[str] = None
    resonator_hint: Optional[str] = None
    action_hint: Optional[str] = None
    timing_offset_ms: int = 0
    is_transient: bool = True

class SoundQueryPlan(BaseModel):
    raw_query: str
    normalized_query: str
    detected_language: str = "en"
    primary_intent: IntentType
    is_compound: bool = False
    atomic_concepts: List[AtomicSoundConcept] = []
    keyword_terms: List[str] = []
    semantic_search_phrases: List[str] = []
    structured_filters: Dict[str, Any] = {}
    target_classifier_labels: List[str] = []
    acoustic_constraints: AcousticConstraints = Field(default_factory=AcousticConstraints)
    negative_constraints: Dict[str, bool] = {}

# audiobook_factory/sonic_candidate_generators.py
class CandidateEvidence(BaseModel):
    asset_id: int
    sources: List[str] = []
    fts_score: Optional[float] = None
    fts_matched_terms: List[str] = []
    structured_matches: Dict[str, Any] = {}
    classifier_matches: List[Dict[str, Any]] = []
    temporal_event_matches: List[Dict[str, Any]] = []
    clap_similarity: Optional[float] = None
    clap_relative_score: Optional[float] = None
    clap_query_matched: Optional[str] = None
    acoustic_matches: Dict[str, Any] = {}
    metadata_completeness: float = 0.0

class CandidateRecord(BaseModel):
    asset_id: int
    filename: str
    filepath: Optional[str] = None
    title: str = ""
    description: str = ""
    category: str = "SFX"
    subcategory: str = "General"
    mood: str = "default"
    duration_sec: float = 0.0
    is_downloaded: bool = False
    source_collection: str = "SoundBank"
    license: str = "Royalty-Free"
    tags: str = ""
    evidence: CandidateEvidence
    raw_metadata: Dict[str, Any] = {}

# audiobook_factory/sonic_hybrid_reranker.py
class RerankingWeights(BaseModel):
    w_semantic: float = 0.35
    w_classifier: float = 0.20
    w_lexical: float = 0.15
    w_structured: float = 0.15
    w_acoustic: float = 0.10
    w_quality: float = 0.05
    p_speech_penalty: float = 0.45
    p_music_penalty: float = 0.40
    local_cached_bonus: float = 0.02

class ScoredCandidate(BaseModel):
    candidate: CandidateRecord
    final_score: float
    component_scores: Dict[str, float]
    negative_penalties: Dict[str, float]
    why_matched: List[str]

# audiobook_factory/agent_sound_card.py
class AgentSoundCard(BaseModel):
    asset_id: int
    title: str
    filename: str
    source_collection: str = "SoundBank"
    license: str = "Royalty-Free"
    category: str = "SFX"
    subcategory: str = "General"
    physical_action: str = "unspecified"
    exciter: str = "unspecified"
    resonator: str = "unspecified"
    surface: str = "unspecified"
    duration_sec: float = 0.0
    integrated_lufs: Optional[float] = None
    true_peak_dbtp: Optional[float] = None
    spectral_centroid_hz: Optional[float] = None
    spectral_brightness: str = "neutral"
    transient_character: str = "transient"
    energy_profile: str = "medium"
    speech_corridor_density: Optional[float] = None
    tags: List[str] = []
    top_classifier_labels: List[Dict[str, Any]] = []
    vocal_speech_probability: Optional[float] = None
    clap_similarity: Optional[float] = None
    source_mood: Optional[str] = None
    classifier_mood: Optional[str] = None
    mood: str = "UNINTERPRETED"
    emotional_suitability: str = "UNINTERPRETED"
    dramatic_role: str = "UNASSIGNED"
    scene_purpose: str = "UNASSIGNED"
    voice_masking_judgment: str = "UNASSESSED"
    voice_masking_risk: Optional[str] = "UNASSESSED"
    whisper_compatibility: Optional[float] = None
    dialogue_ducking_amount_db: Optional[float] = None
    recommended_ducking_db: Optional[float] = None
    placement_usage: str = "UNASSIGNED"
    final_taxonomy: str = "UNASSIGNED"
    agent_interpretation: Optional[AgentInterpretation] = None
    temporal_events: List[Dict[str, Any]] = []
    metadata_completeness_pct: int = 100
    analysis_status: str = "complete"
    provenance_summary: Dict[str, str] = {}
    is_local_cached: bool = False
    is_virtual_jit_ready: bool = True
    file_path: Optional[str] = None
    retrieval_score: Optional[float] = None
    why_matched: List[str] = []

    def attach_interpretation(self, interp: AgentInterpretation) -> "AgentSoundCard": ...
    def to_agent_markdown(self) -> str: ...
    def to_dict(self) -> Dict[str, Any]: ...

class AgentInterpretation(BaseModel):
    evaluator_agent: str
    evaluated_at: str
    scene_context: Optional[str] = None
    assigned_dramatic_role: Optional[str] = None
    scene_purpose: Optional[str] = None
    emotional_suitability: Optional[str] = None
    assigned_mood: Optional[str] = None
    voice_masking_judgment: Optional[str] = None
    voice_masking_assessment: Optional[str] = None
    dialogue_ducking_amount_db: Optional[float] = None
    contextual_ducking_db: Optional[float] = None
    placement_usage: Optional[str] = None
    final_taxonomy: Optional[str] = None
    mix_notes: Optional[str] = None
    conflict_notes: Optional[str] = None
    creative_confidence: Optional[float] = None

class SoundRetrievalResult(BaseModel):
    query_plan: SoundQueryPlan
    ranked_cards: List[AgentSoundCard]
    total_candidates_evaluated: int
    execution_latency_ms: float
    metadata: Dict[str, Any] = {}
```

### B. Phase 1 & 2 Data Contracts

```python
# audiobook_factory/deterministic_audio_analyzer.py
class MeasuredAcousticProperties(BaseModel):
    duration_sec: float
    integrated_lufs: float
    true_peak_db: float
    rms_db: float
    spectral_centroid_hz: float
    spectral_rolloff_hz: float
    spectral_flux: float
    zero_crossing_rate: float
    attack_time_ms: float
    decay_time_ms: float
    temporal_character: str
    energy_profile: float
    voice_masking_risk: str
    whisper_compatibility: float
    recommended_ducking_db: float
    analysis_version: str = "v2.1"

# audiobook_factory/classifier_adapter.py
class ClassifierPrediction(BaseModel):
    raw_label: str
    normalized_label: str
    probability: float
    logit: float
    rank: int
```

### C. Engine Services & Facades

```python
# audiobook_factory/sonic_intelligence_engine.py
class SonicIntelligenceEngine:
    def __init__(
        self,
        sound_bank: Optional[SoundBank] = None,
        query_cache: Optional[QueryEmbeddingCache] = None,
        reranker: Optional[SonicHybridReranker] = None,
    ): ...

    def search_sounds(
        self,
        intent: str,
        limit: int = 10,
        weights: Optional[RerankingWeights] = None,
        apply_diversity: bool = True,
        diversity_threshold: Optional[float] = None,
    ) -> SoundRetrievalResult: ...

    def find_similar(
        self,
        asset_id: int,
        mode: Literal["semantic", "acoustic", "category", "source"] = "semantic",
        top_k: int = 5,
    ) -> List[AgentSoundCard]: ...

    def explain_match(self, asset_id: int, intent: str) -> Dict[str, Any]: ...
    def get_sound_card(self, asset_id: int) -> AgentSoundCard: ...

# audiobook_factory/query_embedding_cache.py
class QueryEmbeddingCache:
    def __init__(self, max_memory_entries: Union[int, Path, str, Any] = 1000, db_path: Optional[Any] = None): ...
    def get(self, normalized_query: str, model_id: str, model_version: str, preprocessing_version: str = "v1") -> Optional[np.ndarray]: ...
    def put(self, normalized_query: str, model_id: str, model_version: str, vector: np.ndarray, preprocessing_version: str = "v1") -> None: ...
    def get_or_compute(self, normalized_query: str, compute_fn: Any, model_id: str = "laion/clap-htsat-unfused", model_version: str = "2023", preprocessing_version: str = "v1") -> np.ndarray: ...

# audiobook_factory/sonic_model_manager.py
class SonicModelManager:
    @classmethod
    def get_ast_model(cls) -> Tuple[Any, Any]: ...
    @classmethod
    def get_clap_model(cls) -> Tuple[Any, Any]: ...
    @classmethod
    def clear_vram(cls) -> None: ...

# audiobook_factory/deterministic_audio_analyzer.py
class DeterministicAudioAnalyzer:
    def analyze_file(self, audio_path: Union[str, Path]) -> MeasuredAcousticProperties: ...
    def extract_temporal_events(self, audio_path: Union[str, Path]) -> List[Dict[str, Any]]: ...
```

---

## ⚖️ Unified LLM Creative Quality & Audit Judge Protocol ([`audiobook_factory.gates.llm_judge`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/gates/llm_judge.py))

### 1. Verdict Schemas

```python
class TranslationFidelityVerdict(BaseModel):
    """Verdict for literary translation quality, sense-for-sense fidelity, and cadence."""
    status: str                         # 'PASS' or 'FAIL'
    score: float                        # Overall fidelity score [0.0 - 1.0]
    literary_cadence_score: float = 1.0
    action_integrity_score: float = 1.0
    critical_inversions: List[str] = [] # Inverted actions or meanings
    dropped_clauses: List[str] = []     # Omitted narrative beats
    translatese_passages: List[str] = []# Literal calques / robotic phrasing
    reason: str = ""                    # Critique rationale
    recommendations: List[str] = []     # Actionable rewrite guidance

class DialogueAttributionVerdict(BaseModel):
    """Verdict for screenplay speaker attribution and dialogue turn isolation."""
    status: str                         # 'PASS' or 'FAIL'
    score: float                        # Attribution accuracy score [0.0 - 1.0]
    total_lines_inspected: int = 0
    misattributed_segments: List[Dict[str, Any]] = []
    hallucinated_lines: List[str] = []
    swallowed_dialogue: List[str] = []  # Dialogue quotes trapped inside narration
    reason: str = ""

class DramaticArcVerdict(BaseModel):
    """Verdict for scene emotional tension trajectory and anti-emotional teleportation."""
    status: str                         # 'PASS' or 'FAIL'
    score: float
    emotional_teleportation_detected: bool = False
    teleportation_violations: List[Dict[str, Any]] = []
    broken_causality_beats: List[str] = []
    reason: str = ""

class VocalActingVerdict(BaseModel):
    """Verdict for perceptual vocal acting quality and emotional delivery."""
    status: str                         # 'PASS' or 'FAIL'
    overall_acting_score: float         # [0.0 - 1.0]
    dimension_scores: Dict[str, float] = {}
    acting_believability: float = 1.0
    emotional_fidelity: float = 1.0
    subtext_fidelity: float = 1.0
    dialogue_reactivity: float = 1.0
    diagnostics: List[str] = []
    take_selection_approved: bool = True
    acting_redirections: List[str] = []

class SoundDesignAtmosphereVerdict(BaseModel):
    """Verdict for acoustic scene intent, ambience fitness, and foley plausibility."""
    status: str                         # 'PASS' or 'FAIL'
    score: float
    ambience_scene_fitness: bool = True
    music_mood_aligned: bool = True
    foley_narrative_plausible: bool = True
    clashing_elements: List[str] = []
    era_inconsistencies: List[str] = []
    reason: str = ""
```

### 2. Base & Specialized Evaluator Classes

```python
class BaseLLMJudge:
    """Foundational judge resolving active models dynamically via ModelManager."""
    @classmethod
    def resolve_auditing_model(cls) -> str:
        """Resolves TaskType.AUDITING with concurrent health pings and Tier 2 floor."""
    @classmethod
    def evaluate_with_llm(
        cls,
        prompt: str,
        system_instruction: str,
        response_model: Type[T],
        temperature: float = 0.1,
        max_retries: int = 3,
    ) -> T:
        """Executes fail-closed evaluation pass. Raises GateAuditError on schema error or outage."""

class LLMTranslationJudge(BaseLLMJudge):
    """Forensic literary evaluator for translated literature (Gates 0 & T2/T9)."""
    @classmethod
    def audit_translation(
        cls,
        source_text: str,
        hindi_text: str,
        chapter_title: str = "",
        min_score: float = 0.80,
        strict: bool = True,
    ) -> TranslationFidelityVerdict: ...

class LLMScreenplayAuditor(BaseLLMJudge):
    """Forensic dialogue attribution & screenplay structure auditor (Gate 2)."""
    @classmethod
    def audit_screenplay(
        cls,
        source_text: str,
        script_segments: List[Dict[str, Any]],
        character_roster: Optional[Dict[str, Any]] = None,
        strict: bool = True,
    ) -> DialogueAttributionVerdict: ...

class LLMDramaticCritic(BaseLLMJudge):
    """Dramaturgy & dramatic arc continuity judge (Gate 2.5)."""
    @classmethod
    def audit_dramatic_arc(
        cls,
        segments: List[Dict[str, Any]],
        dramatic_plan: Optional[Any] = None,
        source_text: str = "",
        strict: bool = True,
    ) -> DramaticArcVerdict: ...

class LLMPerceptualPerformanceJudge(BaseLLMJudge):
    """Perceptual vocal acting and delivery quality judge (Gate 2.8)."""
    @classmethod
    def critique_performance(
        cls,
        direction: Any,
        acoustic_metrics: Dict[str, Any],
        text: str,
        prev_speaker: Optional[str] = None,
        min_score: float = 0.70,
        strict: bool = False,
    ) -> VocalActingVerdict: ...

class LLMSoundDesignCritic(BaseLLMJudge):
    """Cinematic Sound Design & Narrative Atmosphere Critic (Stage 11 & Gate 3.5)."""
    @classmethod
    def audit_soundscape(
        cls,
        scene_text: str,
        manifest_summary: Dict[str, Any],
        active_env: str = "",
        franchise_era: str = "MEDIEVAL_FANTASY",
        strict: bool = True,
    ) -> SoundDesignAtmosphereVerdict: ...
```

---

## 🛡️ Pre-Mix Reality & Sound Bank Verification Engines

### 1. `AudioRealityAuditor` ([`audiobook_factory.audio_reality_auditor`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/audio_reality_auditor.py))

```python
class AuditedCueRecord(BaseModel):
    cue_id: str
    bus: str                            # 'FX', 'AMB', 'MX', 'DX'
    asset_path: str
    asset_name: str
    start_ms: int
    end_ms: int
    raw_duration_sec: float
    effective_duration_sec: float
    volume_db: float
    was_trimmed: bool = False
    sanity_status: str = "PASS"         # 'PASS', 'REMEDIATED', 'REJECTED'
    remediation_notes: str = ""

class AudioRealityReport(BaseModel):
    chapter_id: str
    total_cues_inspected: int = 0
    passed_count: int = 0
    remediated_count: int = 0
    rejected_count: int = 0
    cues: List[AuditedCueRecord] = []
    era: str = "MEDIEVAL_FANTASY"
    franchise_affinity: Optional[str] = None
    summary: Dict[str, Any] = {}

class AudioRealityAuditor:
    MAX_FOLEY_DURATION_SEC: float = 3.5
    MAX_FOLEY_FILE_CEILING_SEC: float = 6.0
    ANTI_REPETITION_COOLDOWN_MS: int = 180000  # 3 minutes

    def __init__(self, sound_bank: Optional[Any] = None): ...

    def audit_and_remediate(
        self,
        manifest: CreativeManifest,
        output_dir: Optional[Path] = None,
        era: str = "MEDIEVAL_FANTASY",
        franchise_affinity: Optional[str] = None,
    ) -> Tuple[CreativeManifest, AudioRealityReport]:
        """Audits cues, clamps durations, quenches repetition, and purges rogue Foley music."""
```

### 2. `AudioVerificationGate` ([`audiobook_factory.sound_bank.verification_gate`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/sound_bank/verification_gate.py))

```python
@dataclass
class VerificationResult:
    is_valid: bool
    reason: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    conformed_path: Optional[Path] = None
    fallback_recommended: bool = False

class AudioVerificationGate:
    def __init__(self, ffmpeg_bin: Optional[str] = None, ffprobe_bin: Optional[str] = None): ...

    def probe_audio(self, audio_path: Path | str) -> Dict[str, Any]:
        """Probes file container metadata via ffprobe (duration, sample rate, channels, codec)."""

    def verify_asset(
        self,
        audio_path: Path | str,
        category: str = "SFX",
        era: str = "MEDIEVAL_FANTASY",
        auto_conform: bool = True,
    ) -> VerificationResult:
        """Verifies physical headers, duration contracts, era keywords, and synthetic noise absence."""
```

---

## 🌍 Universal Project Classification & Sonic Bible Generation

### 1. `ProjectClassifier` ([`audiobook_factory.project_classifier`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/project_classifier.py))

```python
@dataclass
class ProjectClassification:
    era: str                            # MEDIEVAL_FANTASY, SPACE_OPERA_SCIFI, etc.
    genre: str                          # fantasy, sci_fi, detective_noir, etc.
    franchise_affinity: Optional[str]   # 'the_witcher', 'dune', 'tolkien_middle_earth', None
    primary_acoustic_env: str           # 'stone_ruins_exterior', 'tavern_interior', etc.
    dramatic_theme: str
    confidence: float

class ProjectClassifier:
    @staticmethod
    def classify(
        project_dir: Optional[Path] = None,
        metadata: Optional[Dict[str, Any]] = None,
        sample_prose: Optional[str] = None,
    ) -> ProjectClassification:
        """Classifies era, genre, and world acoustic DNA from metadata and text."""
```

### 2. `SonicBibleGenerator` ([`audiobook_factory.sonic_bible_generator`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/sonic_bible_generator.py))

```python
class SonicBibleGenerator:
    @classmethod
    def generate_for_project(
        cls,
        project_dir: Path,
        sound_bank: Optional[SoundBank] = None,
        force_rebuild: bool = False,
    ) -> SonicBible:
        """Compiles production-ready sound_bible.json registering world acoustic spaces and motifs."""
```

### 3. `CharacterCaster` ([`audiobook_factory.character_caster`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/character_caster.py))

```python
class CharacterCaster:
    """Autonomous character discovery, voice persona allocation, and cast lock manager."""

    @classmethod
    def discover_and_cast_characters(
        cls,
        project_dir: Path,
        novel_title: str = "",
        author: str = "",
        force_rebuild: bool = False,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """
        Executes 5-tier stratified sampling across novel scope (0%, 25%, 50%, 75%, 100%).
        Calls the LLM Casting Director to discover major/minor characters and assigns
        unique, non-colliding Gemini voice models and pitch/speed signatures.
        Emits and persists (character_roster.json, voice_registry.json, cast_lock.json).
        """

    @classmethod
    def cast_single_speaker(
        cls,
        speaker_name: str,
        project_dir: Optional[Path] = None,
        gender: Optional[str] = None,
        default_backend: str = "gemini_tts",
    ) -> Dict[str, Any]:
        """
        Dynamically registers and casts a single newly discovered character mid-production.
        Allocates a non-colliding voice from the gender pool with micro-pitch offsets.
        Persists to voice_registry.json, character_roster.json, and cast_lock.json.
        Guarantees zero voice drift and zero signature collision.
        """
```

---

## 🛡️ Centralized Permissive Safety Protocol ([`audiobook_factory.safety`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/safety.py))

```python
UNIVERSAL_BLOCK_NONE_SAFETY_SETTINGS: List[Dict[str, str]] = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

def get_universal_safety_settings() -> List[Dict[str, str]]:
    """Returns universal BLOCK_NONE safety thresholds."""

def get_dramatic_fiction_framing(title: Optional[str] = None, author: Optional[str] = None) -> str:
    """Constructs explicit literary framing context protecting against false moderation blocks."""
```

---

## 🎛️ Model & Keys Manager Subsystem ([`audiobook_factory.core.models`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/))

The `audiobook_factory.core.models` package provides the production control plane governing LLM generation, speech synthesis (TTS), key leasing, rate-limiting, and error resiliency across all 5 production rooms.

---

### 1. Data Structures & Types

#### [`CallerIdentity`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py#L106)
*Cryptographic and operational tuple identifying a caller process, thread, or user session.*

```python
@dataclass(frozen=True)
class CallerIdentity:
    workstation_id: str = field(default_factory=lambda: os.environ.get("WORKSTATION_ID", "local_workstation"))
    user_id: str = field(default_factory=lambda: os.environ.get("USER", os.environ.get("USERNAME", "default_user")))
    process_id: int = field(default_factory=os.getpid)
    worker_id: str = field(default_factory=lambda: f"thr_{threading.get_ident()}")
    session_id: str = field(default_factory=lambda: os.environ.get("CURRENT_SESSION_ID") or "session_default")
    workload_type: str = "text"  # "text" or "tts"
```

#### [`KeyLease`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py#L117)
*Active lease handle guaranteeing exclusive single-request mutual exclusion.*

```python
@dataclass
class KeyLease:
    lease_id: str
    key_hash: str
    key_alias: str
    api_key: str
    provider: str
    workload_type: str
    leased_at: str
    expires_at: str
    status: str = "ACTIVE"
```

#### [`GenerationResult`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/base.py#L16)
*Standardized payload returned by text generation adapters.*

```python
@dataclass
class GenerationResult:
    text: str
    finish_reason: str
    tokens_used: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    thoughts: str = ""
    raw_response: Dict[str, Any] = field(default_factory=dict)
    model_id: str = ""
    provider: str = ""
```

#### [`SpeechResult`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/base.py#L30)
*Standardized payload returned by speech synthesis adapters.*

```python
@dataclass
class SpeechResult:
    audio_bytes: bytes
    mime_type: str = "audio/wav"
    sample_rate: int = 24000
    duration_sec: float = 0.0
    tokens_used: int = 0
    model_id: str = ""
    provider: str = ""
```

#### [`ModelCapability`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/registry.py#L48)
*Complete technical specification and capability profile for a model.*

```python
@dataclass(frozen=True)
class ModelCapability:
    model_id: str
    provider: str
    tier: ModelTier
    modalities: List[Modality]
    context_window: int
    max_output_tokens: int
    free_rpm: float
    free_tpm: float
    free_rpd: int
    supports_thinking: bool = False
    default_thinking_budget: int = 0
    supports_structured_output: bool = True
    supports_system_instruction: bool = True
    recommended_tasks: List[str] = field(default_factory=list)
    reset_schedule: str = "google_pt"   # "google_pt" or "utc_midnight"
    is_local_gpu: bool = False
    notes: str = ""
```

#### [`ModelTier`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/registry.py#L20), [`Modality`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/registry.py#L29) & [`TaskCategory`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/registry.py#L36)

```python
class ModelTier(Enum):
    TIER_1_FLAGSHIP = "flagship"      # Flagship reasoning (Gemini 3.8/3.7 Flash, Gemini 2.5 Pro)
    TIER_2_BALANCED = "balanced"      # Fast, balanced extraction & QA (Gemini 3.6 Flash, 2.5 Flash)
    TIER_3_UTILITY = "utility"        # High-throughput formatting (Gemini 3.1 Flash-Lite)
    TIER_AUDIO = "audio"              # Speech synthesis models (Gemini 3.8 Flash-TTS)
    TIER_LOCAL = "local"              # Local GPU inference (RTX 4050 6GB)

class Modality(Enum):
    TEXT = "text"
    AUDIO = "audio"
    VISION = "vision"

class TaskCategory(Enum):
    TRANSLATION = "translation"        # Room 2: Hindustani literary translation
    SCREENPLAY = "screenplay"          # Room 3: Screenplay dramatization & beat-splitting
    DRAMATURGY = "dramaturgy"          # Room 3: Character DNA, dialect, anti-swap attribution
    EXTRACTION = "extraction"          # Room 1: PDF/EPUB structure, XY-cut layout
    TTS = "tts"                        # Room 4: 4D Vocal Speech Synthesis
    UTILITY = "utility"                # Fast JSON cleanup, validation, token pings
    ALIGNMENT = "alignment"            # Forced alignment phoneme sync
```

#### [`NormalizedApiError`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/policy_engine.py#L43)
*Normalized error metadata returned by policy classifier.*

```python
class NormalizedApiError(NamedTuple):
    category: str              # DAILY_QUOTA_EXHAUSTED, RPM_RATE_LIMIT, TPM_RATE_LIMIT, CONCURRENCY_LIMIT, etc.
    wait_sec: float            # Recommended backoff in seconds
    message: str               # Diagnostic description
    is_retryable: bool         # Whether retrying could succeed (on same or next key/model)
    suggested_action: str      # "ROTATE_KEY", "ROTATE_MODEL", "COOL_DOWN", "ABORT_PAYLOAD", "HALT_POOL"
```

#### [`ExecutionPlan`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/router.py#L40)
*Execution blueprint emitted by RequestRouter.*

```python
@dataclass
class ExecutionPlan:
    model_capability: ModelCapability
    provider: str
    adapter: BaseProviderAdapter
    lease: KeyLease
    key_alias: str
    api_key: str
    model_id: str
```

---

### 2. Exceptions & Circuit Breaker States

```python
class KeyLeaseError(RuntimeError):
    """Base exception for Key Lease errors."""

class KeyLeaseQuotaExceededError(KeyLeaseError):
    """Raised when a user breaches 'One User = One Key per Workload' policy."""

class NoAvailableKeyError(KeyLeaseError):
    """Raised when all keys are currently leased, cooling down, or busy."""

class AllKeysExhaustedTodayError(KeyLeaseError):
    """Raised when all configured API keys have exhausted their daily quota for today."""

class EmergencyTripwireActiveError(Exception):
    """Raised when Emergency Global Tripwire is active due to edge-wide 429/503 cascades."""

class ApiHttpError(Exception):
    """Raised by provider adapters upon upstream HTTP failure."""
    def __init__(self, status_code: int, error_body: str = "", headers: Optional[Dict[str, str]] = None): ...
```

#### Circuit Breaker Lifecycle ([`CircuitBreaker`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/policy_engine.py#L242))
- `CLOSED`: Normal operation. Requests flow unimpeded.
- `OPEN`: Tripped after 2 consecutive server failures (500/502/503/504). Blocks requests to that `(provider, model)` pair for a 30.0s cooldown.
- `HALF_OPEN`: Cooldown expired. Allows a single canary request to test upstream provider recovery.

---

### 3. Core Engine Classes

#### [`ModelGateway`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py#L61)
*Unified thread-safe production facade used by all 5 rooms.*

```python
class ModelGateway:
    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        lease_manager: Optional[KeyLeaseManager] = None,
        anti_ban_guard: Optional[AntiBanGuard] = None,
        router: Optional[RequestRouter] = None,
    ): ...

    def generate_text(
        self,
        prompt: str,
        task: str = "translation",
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        min_tier: Optional[ModelTier] = None,
        preferred_provider: str = "gemini",
        thinking_budget: Optional[int] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        response_json: bool = False,
        session_id: Optional[str] = None,
        word_count: int = 0,
        user_id: str = "user_default",
        fast_mode: bool = False,
        max_retries: int = 3,
        **kwargs,
    ) -> GenerationResult:
        """
        Executes text generation request through the control plane:
        1. Resolves execution plan & leases key.
        2. Applies Anti-Ban Gate (pacing, rate limit, anti-correlation).
        3. Dispatches request via adapter.
        4. Handles failover on 429 quota exhaustion or server error.
        5. Records metrics and safely releases lease.
        """

    def synthesize_speech(
        self,
        text: str,
        voice_name: str = "Puck",
        model: Optional[str] = None,
        preferred_provider: str = "gemini",
        session_id: Optional[str] = None,
        user_id: str = "user_default",
        fast_mode: bool = False,
        max_retries: int = 3,
        **kwargs,
    ) -> SpeechResult:
        """
        Executes speech synthesis (Room 4) adhering to strict 10 RPD daily quota ceilings:
        1. Resolves audio model (gemini-3.8-flash-tts).
        2. Leases key specifically for TTS workload.
        3. Applies cadence pacing and rate limit.
        4. Synthesizes and decodes audio into raw WAV bytes.
        """

    @contextmanager
    def lease_session(
        self,
        session_id: str,
        task: str = "screenplay",
        user_id: str = "user_default",
        provider: str = "gemini",
    ) -> Generator[str, None, None]:
        """
        Shield 2: Context manager holding sticky session affinity across a whole scene (8-15 segments).
        """

    def get_fleet_status(self) -> Dict[str, Any]:
        """Returns comprehensive diagnostic summary of keys, models, and breakers."""

    def reset_pool(self, provider: str = "gemini") -> None:
        """Administratively resets exhausted keys, quota ledgers, and tripwires for today."""
```

#### [`KeyLeaseManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py#L130)
*High-performance ACID SQLite Key Inventory & Lease Manager.*

```python
class KeyLeaseManager:
    def __init__(self, db_path: Optional[Path] = None, keys: Optional[List[str]] = None): ...

    def register_keys(
        self,
        keys: List[str],
        provider: str = "gemini",
        allowed_services: Optional[List[str]] = None,
        tier: str = "free",
    ) -> None:
        """Registers or syncs API keys in key_inventory without wiping quota history."""

    def acquire_lease(
        self,
        workload_type: str = "text",
        provider: str = "gemini",
        identity: Optional[CallerIdentity] = None,
        ttl_seconds: float = 60.0,
        model: Optional[str] = None,
        allow_multi_lease: bool = False,
        preferred_key_alias: Optional[str] = None,
    ) -> KeyLease:
        """
        Atomically acquires an exclusive lease for an eligible API key.
        Guarantees:
        - Mutual exclusion (0% double-allocations).
        - Dead PID crash reclamation.
        - User quota enforcement.
        - Quota rollover and model isolation.
        """

    def renew_lease(self, lease_id: str, extend_seconds: float = 60.0) -> bool:
        """Extends an active lease expiration timestamp (heartbeat)."""

    def release_lease(self, lease_id: str) -> bool:
        """Releases an active lease handle and records audit completion."""

    def revoke_lease(self, lease_id: str, reason: str = "error") -> bool:
        """Revokes an active lease (e.g. on 429 quota exhaustion or critical failure)."""

    def mark_daily_quota_exhausted(
        self,
        api_key_or_hash: str,
        error_msg: str,
        model: Optional[str] = None,
        provider: str = "gemini",
    ) -> None:
        """Marks a key or model as exhausted for today (e.g. 10 RPD reached on TTS)."""

    def mark_temporary_backoff(
        self,
        api_key_or_hash: str,
        backoff_seconds: float,
        error_msg: str = "",
        model: Optional[str] = None,
        provider: str = "gemini",
    ) -> None:
        """Marks a key for temporary backoff without burning it for the whole day."""

    def mark_invalid(
        self,
        api_key_or_hash: str,
        error_msg: str,
        provider: str = "gemini",
    ) -> None:
        """Marks a key as permanently INVALID."""

    def sweep_stale_and_dead_leases(self, conn: sqlite3.Connection) -> int:
        """Sweeps expired TTL leases and reclaims orphaned leases from dead PIDs."""

    def reset_all_for_today(self, provider: str = "gemini") -> None:
        """Forces administrative reset of all keys and models back to ACTIVE state."""

    def get_status_summary(self, provider: str = "gemini") -> Dict[str, Any]:
        """Returns live statistics of inventory and active leases."""
```

#### [`AntiBanGuard`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/anti_ban_guard.py#L379)
*The Central Control Plane for Anti-Ban Protection (The 7 Iron Shields).*

```python
class AntiBanGuard:
    def __init__(
        self,
        key_switch_min_cooldown: float = 18.0,
        key_switch_max_cooldown: float = 32.0,
        max_rpm: float = 11.0,
    ): ...

    def pre_request_gate(
        self,
        key_alias: str,
        prev_key_alias: Optional[str] = None,
        word_count: int = 0,
        prev_audio_duration_sec: float = 0.0,
        session_id: Optional[str] = None,
        fast_mode: bool = False,
    ) -> Dict[str, float]:
        """
        Executes pre-request validation, pacing, and rate limiting:
        1. Checks Emergency Global Tripwire (Shield 7).
        2. Enforces Anti-Correlation Key-Switch Cooldown if key changed (Shield 3).
        3. Enforces Token Bucket 11.0 RPM clamping (Shield 5).
        4. Applies Content-Aware Human Cadence (Shield 4).
        """

    def post_request_audit(
        self,
        key_alias: str,
        status_code: int,
        error_body: str = "",
        headers: Optional[Dict[str, str]] = None,
        provider: str = "gemini",
        model: str = "",
        session_id: Optional[str] = None,
    ) -> NormalizedApiError:
        """Audits response status, updates Tripwire, Circuit Breaker, and Session Affinity."""

    def enforce_key_switch_cooldown(
        self,
        prev_key_alias: Optional[str],
        new_key_alias: str,
        fast_mode: bool = False,
    ) -> float:
        """Shield 3: Mandatory 18.0s - 32.0s pause when switching keys on the same IP."""

    def get_headers(self, api_key: str, provider: str = "gemini") -> Dict[str, str]:
        """Shield 6: Injects official stealth SDK headers."""

    def reset_all(self) -> None:
        """Resets all internal states, tripwires, and limiters."""
```

#### [`ModelRegistry`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/registry.py#L422)
*Canonical Model Registry & Capability Specification.*

```python
class ModelRegistry:
    def get_model(self, model_id: str) -> Optional[ModelCapability]:
        """Resolves ModelCapability by exact ID or case-insensitive prefix match."""

    def list_models(self, provider: Optional[str] = None) -> List[ModelCapability]:
        """Lists all registered models, optionally filtered by provider."""

    def filter_models(
        self,
        task: Optional[str] = None,
        min_tier: Optional[ModelTier] = None,
        modality: Optional[Modality] = None,
        provider: Optional[str] = None,
    ) -> List[ModelCapability]:
        """Filters models matching required constraints."""

    def resolve_best_model(
        self,
        task: str,
        preferred_provider: str = "gemini",
        min_tier: Optional[ModelTier] = None,
        modality: Modality = Modality.TEXT,
    ) -> ModelCapability:
        """Dynamically resolves the best eligible model for a given task and tier requirement."""

    def register_model(self, capability: ModelCapability) -> None:
        """Registers a new model capability profile."""
```

#### [`RequestRouter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/router.py#L51)
*Intelligent Request Router matching task requirements to eligible healthy resources.*

```python
class RequestRouter:
    def resolve_plan(
        self,
        task: str,
        preferred_provider: str = "gemini",
        min_tier: Optional[ModelTier] = None,
        modality: Modality = Modality.TEXT,
        identity: Optional[CallerIdentity] = None,
        model_override: Optional[str] = None,
        preferred_key_alias: Optional[str] = None,
    ) -> ExecutionPlan:
        """
        Builds an ExecutionPlan:
        1. Selects healthy candidate model matching constraints.
        2. Bypasses models whose Circuit Breaker is OPEN.
        3. Acquires an exclusive ACID lease on a matching key.
        4. Links the correct polymorphic provider adapter.
        """
```

---

## 🛡️ Gate 2.9: Pre-TTS Config & Attribution Sanity ([`audiobook_factory.gates.pre_synthesis`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/pre_synthesis.py))

*Authoritative pre-synthesis verification gate running immediately prior to Room 4 TTS dispatch. Protects both Audiobook and Dual-Track Podcast execution paths from expensive API quota waste and acoustic corruption via a Dual-Tier Hybrid Architecture.*

### 1. Data Contracts & Schemas

#### [`PreSynthesisLLMVerdict`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/pre_synthesis.py#L28-L49)
*Pydantic v2 schema encapsulating the structured verdict returned by the Tier 2 Adversarial LLM Judge.*

```python
class PreSynthesisLLMVerdict(BaseModel):
    """LLM evaluation verdict for pre-synthesis dialogue attribution and sanity."""
    model_config = ConfigDict(extra="ignore")

    status: str = Field(..., description="'PASS' or 'FAIL'")
    score: float = Field(..., ge=0.0, le=1.0, description="Overall sanity score [0.0 - 1.0]")
    attribution_accuracy: float = Field(default=1.0, ge=0.0, le=1.0, description="Attribution accuracy score [0.0 - 1.0]")
    speaker_swaps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of dialogue lines misassigned to wrong character or inverted ($A <-> B$)"
    )
    swallowed_dialogue: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Direct spoken dialogue quotes wrongly embedded inside narrator lines"
    )
    persona_mismatches: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Character voice style or emotional tone severe inconsistencies"
    )
    reason: str = Field(default="", description="High-level narrative reason for the verdict")
    recommendations: List[str] = Field(default_factory=list, description="Actionable directives for repairing detected defects")
```

#### Supporting Contracts ([`audiobook_factory.gates.contracts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/contracts.py))

```python
class AuditResult(BaseModel):
    """Encapsulates the consolidated result of a quality gate evaluation."""
    gate: str
    gate_name: str
    status: Literal["PASS", "FAIL", "WARNING", "SKIPPED"]
    passed: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)

class GateAuditError(Exception):
    """Raised when a fail-closed quality gate detects critical unrecoverable defects."""
```

---

### 2. [`LLMPreSynthesisJudge`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/pre_synthesis.py#L51-L237)
*Tier 2 Adversarial LLM Auditor evaluating pre-synthesis script segments against character profiles, narrative context, and formatting rules. Dispatched via ModelGateway across the 123+ API key round-robin pool.*

```python
class LLMPreSynthesisJudge:
    """
    Adversarial LLM Auditor evaluating pre-synthesis script segments against
    character profiles, dramatic context, and format rules.
    Runs via ModelGateway with 123+ API key round-robin pool.
    """
    SYSTEM_INSTRUCTION: str  # Comprehensive adversarial supervisor prompt

    @classmethod
    def audit_pre_synthesis(
        cls,
        segments: List[Dict[str, Any]],
        project_dir: Path,
        source_text: Optional[str] = None,
        format_mode: str = "audiobook",
        call_llm_fn: Optional[Any] = None,
    ) -> PreSynthesisLLMVerdict:
        """
        Audits dialogue attribution and dramatic sanity across screenplay segments.

        Parameters:
            segments: List of script segment dictionaries (containing 'index', 'speaker', 'type', 'text', 'emotion').
            project_dir: Path to the book project directory (used to load character_roster.json / podcast_config.json).
            source_text: Optional uncompressed source chapter text used for contextual narrative grounding.
            format_mode: "audiobook" or "podcast".
            call_llm_fn: Optional custom callable hook for testing or direct prompt injection.

        Returns:
            PreSynthesisLLMVerdict containing pass/fail status, scores, speaker swaps, and recommendations.

        Behavior:
            - When segments > 40, stratifies a representative 40-segment sample: Head 10, Body 20, Tail 10.
            - When source_text > 8000 characters, extracts Head (2000), Mid (4000), and Tail (2000) excerpts.
            - Automatically parses character_roster.json or podcast_config.json to ground the cast roster.
            - Dispatches prompt through ModelGateway.generate_text() with AntiBanGuard 11.0 RPM pacing,
              sticky session affinity ('gate2_9_pre_tts'), stealth SDK headers, and BLOCK_NONE safety framing.
        """

    @classmethod
    def _call_gateway(cls, prompt: str, system_instruction: str) -> PreSynthesisLLMVerdict:
        """
        Dispatches prompt via ModelGateway.generate_text().
        Handles offline/test execution when MOCK_OFFLINE, UNIT_TEST_MODE, or PYTEST_CURRENT_TEST is set.
        """
```

---

### 3. [`PreSynthesisGate`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/pre_synthesis.py#L239-L691)
*Core gate class executing both Tier 1 deterministic fast checks and Tier 2 LLM judge auditing.*

```python
class PreSynthesisGate:
    """
    Evaluates screenplay segments for acoustic and attribution correctness
    prior to TTS dispatch.
    """

    # Compiled Regular Expression Patterns
    MARKDOWN_FENCE_PATTERN: Pattern[str]  # Matches ```json, ```markdown, ```text, ```
    LLM_CHATTER_PATTERN: Pattern[str]     # Matches "Here is the script:", "Certainly! Below is the...", etc.
    MALE_HINDI_INFLECTIONS: Pattern[str]  # Matches first-person masculine verbs: रहा हूँ, जाऊँगा, करूँगा, etc.
    FEMALE_HINDI_INFLECTIONS: Pattern[str]# Matches first-person feminine verbs: रही हूँ, जाऊँगी, करूँगी, etc.
    SPEECH_VERB_LEAD_IN: Pattern[str]     # Matches dialogue speech verbs: said, asked, ने कहा, बोला, बोली, etc.

    @classmethod
    def audit_script(
        cls,
        script_file_or_data: Union[Path, str, List[Dict[str, Any]]],
        project_dir: Optional[Union[Path, str]] = None,
        source_file: Optional[Union[Path, str]] = None,
        source_text: Optional[str] = None,
        format_mode: Literal["audiobook", "podcast"] = "audiobook",
        call_llm_fn: Optional[Any] = None,
        skip_llm: bool = False,
        strict: bool = True,
    ) -> AuditResult:
        """
        Executes complete Gate 2.9 Pre-TTS validation:
        Tier 1: Deterministic structural, whitelist, and acoustic bounds checks.
        Tier 2: Adversarial LLM Attribution & Dramaturgy Sanity Judge (ModelGateway 123+ key pool).

        Parameters:
            script_file_or_data: Filesystem path to script JSON or in-memory list of segment dictionaries.
            project_dir: Optional project root path (auto-inferred from script path if omitted).
            source_file: Optional path to raw source chapter text file.
            source_text: Optional in-memory source chapter text string.
            format_mode: "audiobook" (ratio pitch [0.65, 1.35]) or "podcast" (semitone pitch [-12, +12]).
            call_llm_fn: Optional custom callable hook for testing LLM verdicts without network calls.
            skip_llm: When True, bypasses Tier 2 LLM judge and evaluates only Tier 1 deterministic checks.
            strict: When True, any critical defect immediately raises GateAuditError (fail-closed).

        Returns:
            AuditResult with gate='GATE_2_9_PRE_TTS', passed=bool, errors, warnings, and details.

        Raises:
            GateAuditError: If strict=True and any critical defect (unregistered speaker, out-of-bounds
                            acoustic parameter, swallowed dialogue, or LLM speaker swap) is detected.
        """
```

#### Private Helper Methods

```python
    @classmethod
    def _audit_segment_acoustic_params(
        cls, idx: int, speaker: str, seg: Dict[str, Any],
        voice_registry: Dict[str, Any], format_mode: str,
        errors: List[str], warnings: List[str]
    ) -> None:
        """Audits pitch_shift, speed_multiplier, and non-null assigned voice IDs."""

    @classmethod
    def _audit_podcast_segment(
        cls, idx: int, speaker: str, seg: Dict[str, Any],
        text: str, errors: List[str], warnings: List[str]
    ) -> None:
        """Audits podcast-specific breathability punctuation and stereo spatial pan staging."""

    @classmethod
    def _resolve_catalogs(
        cls, project_dir: Path, format_mode: str
    ) -> Tuple[Set[str], Dict[str, str], Dict[str, Any]]:
        """Loads allowed speakers, gender mappings, and voice registries from project directory."""

    @classmethod
    def _load_segments(
        cls, script_file_or_data: Union[Path, str, List[Dict[str, Any]]]
    ) -> Tuple[List[Dict[str, Any]], Optional[Path]]:
        """Parses segments from a filesystem JSON file or validates an in-memory list."""

    @classmethod
    def _finalize_result(
        cls, errors: List[str], warnings: List[str], details: Dict[str, Any], strict: bool
    ) -> AuditResult:
        """Constructs AuditResult; if strict=True and errors exist, raises GateAuditError."""

    @staticmethod
    def _norm(s: str) -> str:
        """Normalizes speaker name (lowercased, stripped, underscores replaced with spaces, Devanagari nuktas removed)."""
```

---

### 4. Public Entry Point: [`audit_gate2_9_pre_tts_sanity`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/pre_synthesis.py#L693-L717)

```python
def audit_gate2_9_pre_tts_sanity(
    script_file: Union[Path, str, List[Dict[str, Any]]],
    project_dir: Optional[Union[Path, str]] = None,
    source_file: Optional[Union[Path, str]] = None,
    source_text: Optional[str] = None,
    format_mode: Literal["audiobook", "podcast"] = "audiobook",
    call_llm_fn: Optional[Any] = None,
    skip_llm: bool = False,
    strict: bool = True,
) -> AuditResult:
    """
    Public entry point for Gate 2.9: Pre-TTS Config & Attribution Sanity Gate.
    Combines Tier 1 fast-path local validation with Tier 2 LLM Attribution Judge (ModelGateway 123+ key pool).

    Example Usage:
        from audiobook_factory.gates.pre_synthesis import audit_gate2_9_pre_tts_sanity

        result = audit_gate2_9_pre_tts_sanity(
            script_file="audiobooks/projects/my_project/scripts/chapter_001_hi_script.json",
            project_dir="audiobooks/projects/my_project",
            source_file="audiobooks/projects/my_project/extracted/chapter_001.txt",
            format_mode="audiobook",
            strict=True,
        )
        print(f"Gate 2.9 Status: {result.status}, Errors: {len(result.errors)}")
    """
```

---

## 📊 Production Telemetry Ledger ([`audiobook_factory.telemetry`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/telemetry.py))

```python
class ProductionTelemetryLedger:
    """Thread-safe SQLite production telemetry ledger in audiobooks/telemetry.db."""

    def __init__(self, db_path: Optional[Path] = None): ...

    def start_run(self, run_id: str, project_id: str, book_title: str = "", config: Optional[Dict[str, Any]] = None) -> None: ...

    def record_stage(self, run_id: str, stage_name: str, stage_num: int, duration_sec: float, status: str = "SUCCESS", metadata: Optional[Dict[str, Any]] = None) -> None: ...

    def record_api_call(self, run_id: str, service: str, endpoint: str, status_code: int, latency_sec: float, is_rate_limit: bool = False, prompt_tokens: int = 0, completion_tokens: int = 0, est_cost_usd: float = 0.0) -> None: ...

    def record_acoustic_metrics(self, run_id: str, chapter_num: int, duration_sec: float, integrated_lufs: float, true_peak_dbtp: float, loudness_range_lu: float, phase_correlation: float) -> None: ...

    def record_incident(self, run_id: str, incident_type: str, stage_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None: ...

    def complete_run(self, run_id: str, status: str = "COMPLETED", error_message: Optional[str] = None) -> None: ...

    def export_report_json(self, run_id: Optional[str] = None, output_file: Optional[Path] = None) -> Dict[str, Any]:
        """Generates comprehensive production telemetry summary in TELEMETRY_REPORT.json."""
```

---

## ⚙️ Environment Variables Reference

| Variable | Type | Default | Description |
|---|---|---|---|
| `AUDIOBOOK_RETAIN_CHUNKS` | `bool` | `true` | When `true`, intermediate uncompressed WAV chunks are retained post-certification to shield API quotas for zero-cost DSP remastering. |
| `AUDIOBOOK_PURGE_CHUNKS` | `bool` | `false` | When explicitly `true` AND all quality gates are 100% certified, permits the chapter janitor to purge raw WAV chunks. |
| `SCREENPLAY_CHUNK_WORDS` | `int` | `500` | Word ceiling for screenplay beat chunking. Calibrated to prevent dialogue swallowing during dense multi-character banter. |
| `LLM_SOUND_DESIGN_STRICT` | `bool` | `false` | When `true`, exceptions in `LLMSoundDesignCritic` halt the pipeline (`FAIL`); when `false`, gracefully degrades to `PASS_WITH_WARNINGS` ($0.50$). |
| `TASK_ADAPTIVE_TEMPERATURES` | `bool` | `true` | Enables task-calibrated LLM generation temperatures: 0.82 for dramaturgy/scene planning, 0.88 for creative beats, 0.20 for auditing. |
| `GEMINI_API_KEY` | `str` | `""` | Primary Google Gemini API key fallback. Overridden by SQLite rotating key pool. |
| `GEMINI_TEXT_MODEL` | `str` | `gemini-2.5-flash` | Candidate priority override for text generation and translation intelligence. |
| `GEMINI_TTS_MODEL` | `str` | `gemini-3.8-flash-tts` | Dedicated Google Gemini Cloud speech synthesis model endpoint. |

---

## 🛠️ Resilient System & Casting Utilities ([`audiobook_factory`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/))

### 1. `CharacterCaster.cast_single_speaker`
*Dynamically registers and casts newly discovered characters mid-production with zero voice drift.*

```python
@classmethod
def cast_single_speaker(
    cls,
    speaker_name: str,
    project_dir: Optional[Path] = None,
    gender: Optional[str] = None,
    default_backend: str = "gemini_tts",
) -> Dict[str, Any]:
    """
    Discovers, assigns, and persists an authentic, non-colliding Gemini voice persona
    for a single character. Atomically synchronizes character_roster.json,
    voice_registry.json, and cast_lock.json.
    """
```

### 2. Cross-Platform Executable Resolvers ([`audiobook_factory.tts.constants`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/tts/constants.py))

```python
def get_ffprobe() -> str:
    """Returns resolved path to ffprobe executable via PATH or project fallback."""

def get_ffmpeg() -> str:
    """Returns resolved path to ffmpeg executable via PATH or project fallback."""
```

### 3. Windows Atomic File Promotion ([`audiobook_factory.tts.providers.gemini`](file:///c:/Users/Suraj/Documents/Antigravity/Audiobook/audiobook_factory/tts/providers/gemini.py))

```python
def _atomic_replace(src: Path, dst: Path, max_attempts: int = 8) -> None:
    """
    Atomically promotes src to dst with exponential backoff retry for Windows
    file-locking defense (WinError 32) and copy2 fallback.
    """
```

---

## 🎙️ Room 3.5: Studio Voice Casting & Acoustic Calibration Engine ([`audiobook_factory.casting`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/))

Room 3.5 implements **Option C (Shared Understanding & Voice Registry Core with Specialized Decoupled Subsystems)**.  
*(See complete specification: [`docs/STUDIO_VOICE_CASTING_AND_CALIBRATION.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/STUDIO_VOICE_CASTING_AND_CALIBRATION.md))*

### 1. Data Contracts ([`audiobook_factory.casting.contracts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/contracts.py))

```python
class ProviderCapabilities(BaseModel):
    provider_name: Literal["gemini_tts", "qwen3_tts", "local_winrt"] = "gemini_tts"
    supports_reference_audio: bool = False
    supports_style_prompt: bool = True
    supports_native_speed: bool = False
    native_sample_rate_hz: int = 24000
    supported_controls: List[str] = Field(
        default_factory=lambda: ["speechMetadata.style", "temperature", "parametric_eq"]
    )

class CanonicalVoiceProfile(BaseModel):
    voice_id: str
    display_name: str
    language_code: str = "hi-IN"
    region_code: str = "IN"
    gender: Literal["male", "female", "neutral"] = "neutral"
    perceived_age: Optional[int] = None
    dialect: str = "Standard"
    pitch_tier: Literal["low", "medium_low", "medium", "medium_high", "high"] = "medium"
    timbre: str = ""
    role: str = ""
    persona: str = ""
    archetypes: List[str] = Field(default_factory=list)
    description: str = ""
    default_provider: Literal["gemini_tts", "qwen3_tts"] = "gemini_tts"
    reference_audio_path: Optional[str] = None
    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)

class SpectralFormantProfile(BaseModel):
    chest_resonance_150hz_db: float = Field(default=0.0, ge=-4.0, le=4.0)
    nasal_presence_2800hz_db: float = Field(default=0.0, ge=-3.0, le=4.0)
    throat_clarity_3200hz_db: float = Field(default=0.0, ge=-3.0, le=3.0)
    air_shelf_8000hz_db: float = Field(default=0.0, ge=-4.0, le=4.0)
    target_tempo_multiplier: float = Field(default=1.0, ge=0.85, le=1.15)

    def to_ffmpeg_filters(self) -> List[str]:
        """Generates phase-safe FFmpeg audio filter clauses."""

class SceneContrastMatrix(BaseModel):
    scene_id: str
    active_speakers: List[str] = Field(default_factory=list)
    pairwise_distances: Dict[str, float] = Field(default_factory=dict)
    min_distance: float = 1.0
    is_contrast_sufficient: bool = True
    calibration_adjustments: Dict[str, SpectralFormantProfile] = Field(default_factory=dict)

class CharacterCastAssignment(BaseModel):
    character_id: str
    canonical_name: str
    voice_id: str
    assigned_provider: Literal["gemini_tts", "qwen3_tts"] = "gemini_tts"
    gender: Literal["male", "female", "neutral"] = "neutral"
    dialect: str = "Standard"
    casting_rationale: str = ""
    baseline_formants: SpectralFormantProfile = Field(default_factory=SpectralFormantProfile)
    pronunciation_overrides: Dict[str, str] = Field(default_factory=dict)
    locked: bool = True
    version: str = "1.0.0"

class CastLock(BaseModel):
    character_id: str = ""
    character_name: str = ""
    voice_id: str
    casting_version: str = "1.0.0"
    locked: bool = True
    locked_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    locked_by: str = "Director"
    selection_rank: int = 1
    selection_rationale: str = ""
    casting_evidence: Dict[str, Any] = Field(default_factory=dict)
    calibration_overrides: Dict[str, Any] = Field(default_factory=dict)

class CastLockManifest(BaseModel):
    project_slug: str = Field(default="", validation_alias=AliasChoices("project_slug", "project_id"))
    version: str = "1.0.0"
    locks: Dict[str, CastLock] = Field(default_factory=dict)
    recast_history: List[Dict[str, Any]] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())

    def get_lock(self, character_name_or_id: str) -> Optional[CastLock]: ...
```

### 2. Central Voice Registry ([`audiobook_factory.casting.registry.VoiceProfileRegistry`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/registry.py))

```python
class VoiceProfileRegistry:
    """Central, high-performance voice registry managing 2,089 curated TTS voice assets."""
    @classmethod
    def get_instance(cls, catalog_path: Optional[Path] = None) -> VoiceProfileRegistry: ...

    def get_profile(self, voice_id: str) -> Optional[CanonicalVoiceProfile]: ...

    def query_profiles(
        self,
        language_code: str = "hi-IN",
        gender: Optional[str] = None,
        dialect: Optional[str] = None,
        pitch_tier: Optional[str] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        archetype: Optional[str] = None,
        exclude_voice_ids: Optional[Set[str]] = None,
        limit: int = 50,
    ) -> List[CanonicalVoiceProfile]: ...

    def get_formatted_catalog_for_prompt(
        self,
        language_code: str = "hi-IN",
        gender: Optional[str] = None,
        exclude_voice_ids: Optional[Set[str]] = None,
        limit: int = 30,
    ) -> str: ...
```

### 3. Studio Casting Director ([`audiobook_factory.casting.director.StudioCastingDirector`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/director.py))

```python
class StudioCastingDirector:
    """Intelligent AI Voice Casting Director routing via ModelGateway and 123+ API key pool."""
    def __init__(self, project_dir: Optional[Path | str] = None): ...

    def cast_character(
        self,
        character_name: str,
        gender: Optional[str] = None,
        archetype: str = "",
        dialect_hint: Optional[str] = None,
        is_child: bool = False,
        age_hint: Optional[int] = None,
        use_hindi: bool = True,
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> CastLock:
        """Dynamically casts a single character, enforcing Anime Seiyū child protection and cast locking."""

    def cast_ensemble_from_roster(
        self,
        raw_characters: List[Dict[str, Any]],
        use_hindi: bool = True,
        force_recast: bool = False,
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> CastLockManifest:
        """Casts an entire character roster for a project ensemble."""
```

### 4. Cast Lock Manager ([`audiobook_factory.casting.cast_lock.CastLockManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/cast_lock.py))

```python
class CastLockManager:
    """Manages project-level Cast Locks with audit trails and recast cache invalidation."""
    def __init__(self, project_dir: Path | str): ...
    def save(self) -> None: ...
    def lock_character(
        self,
        character_id: str,
        character_name: str,
        voice_id: str,
        evaluation_record: Optional[CastingEvaluationRecord] = None,
        selection_rationale: str = "",
        calibration_overrides: Optional[Dict[str, Any]] = None,
        locked_by: str = "Director",
    ) -> CastLock: ...
    def get_lock(self, character_name_or_id: str) -> Optional[CastLock]: ...
    def is_locked(self, character_name_or_id: str) -> bool: ...
    def recast_character(
        self,
        character_name_or_id: str,
        new_voice_id: str,
        reason: str,
        recast_by: str = "Director",
        new_calibration: Optional[Dict[str, Any]] = None,
    ) -> CastLock: ...
```

### 5. Scene Acoustic Calibrator ([`audiobook_factory.casting.calibrator.SceneAcousticCalibrator`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/calibrator.py))

```python
class SceneAcousticCalibrator:
    """Calculates pairwise acoustic Euclidean distances (>= 0.65) and generates surgical EQ formants."""
    def __init__(self, registry: Optional[VoiceProfileRegistry] = None): ...

    def calculate_speaker_distance(
        self,
        speaker_a: str,
        speaker_b: str,
        voice_map: Dict[str, Any],
    ) -> float:
        """Calculates mathematical auditory separation distance [0.0, 1.0] between two speakers."""

    def calibrate_scene_segments(
        self,
        scene_id: str,
        segments: List[Dict[str, Any]],
        voice_map: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], SceneContrastMatrix]:
        """Injects complementary parametric EQ curves for co-speakers with distance < 0.65 without digital resampling."""
```

### 6. Provider Voice Adapters ([`audiobook_factory.casting.adapters`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/adapters/))

```python
class BaseVoiceAdapter(ABC):
    """Abstract Provider-Specific Voice Adapter."""
    @abstractmethod
    def adapt_segment_to_provider(
        self,
        segment: Dict[str, Any],
        character_cast: Optional[CharacterCastAssignment] = None,
    ) -> Dict[str, Any]: ...

    @abstractmethod
    def get_provider_capabilities(self) -> ProviderCapabilities: ...

class GeminiVoiceAdapter(BaseVoiceAdapter):
    """Adapter for Google Gemini Flash Speech Synthesis."""
    def adapt_segment_to_provider(
        self,
        segment: Dict[str, Any],
        character_cast: Optional[CharacterCastAssignment] = None,
    ) -> Dict[str, Any]:
        """Translates calibrated segment into Gemini TTS payload dict."""

class QwenVoiceAdapter(BaseVoiceAdapter):
    """Adapter for Qwen3-TTS / CosyVoice zero-shot voice cloning and speech synthesis."""
    def __init__(self, reference_bank_dir: Optional[Path | str] = None): ...
    def adapt_segment_to_provider(
        self,
        segment: Dict[str, Any],
        character_cast: Optional[CharacterCastAssignment] = None,
    ) -> Dict[str, Any]:
        """Translates calibrated segment into Qwen3-TTS payload dict."""
```

### 7. Control Plane Routing Bridge ([`audiobook_factory.casting.gateway_bridge`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/casting/gateway_bridge.py))

```python
def execute_casting_llm(
    prompt: str,
    system_instruction: Optional[str] = None,
    task: str = "directing",
    model: Optional[str] = None,
    temperature: float = 0.20,
    max_output_tokens: Optional[int] = 8192,
    session_id: Optional[str] = None,
    user_id: str = "casting_director",
    json_mode: bool = True,
    **kwargs: Any,
) -> Union[Dict[str, Any], List[Any], str]:
    """
    Executes an AI Casting Director request strictly through ModelGateway.
    Routes via KeyLeaseManager (Concurrency = 1) across the 123+ API key inventory
    with AntiBanGuard 11.0 RPM pacing and BLOCK_NONE creative literature framing.
    """
```

### 8. Quality Gate 2.8: Auditory Distinction Gate ([`audiobook_factory.gates.gate28_distinction.AuditoryDistinctionGate`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/gate28_distinction.py))

```python
class AuditoryDistinctionVerdict(BaseModel):
    passed: bool = True
    min_scene_distance: float = 1.0
    audited_scenes_count: int = 0
    audited_dialogue_turns: int = 0
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    scene_matrices: List[SceneContrastMatrix] = Field(default_factory=list)

class AuditoryDistinctionGate:
    """Authoritative Pre-TTS Auditory Distinction Gatekeeper."""
    @classmethod
    def audit_chapter_script(
        cls,
        segments: List[Dict[str, Any]],
        project_dir: Path | str,
        strict: bool = True,
    ) -> AuditoryDistinctionVerdict:
        """
        Enforces:
        1. Non-null voice assignments and cast locks for every dialogue speaker.
        2. Pairwise acoustic distance >= 0.65 across co-speakers in each scene.
        3. Strict ban on asetrate and atempo filters (Phase-Safe Audio Invariant).
        """
```




