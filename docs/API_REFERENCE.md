# 📚 API Reference: Data Contracts & Module Specifications

## Overview

The `audiobook_factory` package provides a strictly-typed, modular architecture powered by **Pydantic v2** models, clean separation of concerns, and zero hardcoded bindings. This document details the authoritative public contracts, engine classes, and core utility signatures.

---

## 📐 Data Contracts ([`audiobook_factory.contracts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/contracts.py))

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

### `PipelineOrchestrator` ([`audiobook_factory.orchestrator`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/orchestrator.py))
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

### `UniversalExtractor` ([`audiobook_factory.extractor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/extractor.py))
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

### `LiteraryTranslator` ([`audiobook_factory.translator`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translator.py))
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

### `LinguisticSanitizer` ([`audiobook_factory.sanitizer`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/sanitizer.py))
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

### `ScriptBuilder` ([`audiobook_factory.script_builder`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/script_builder.py))
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

### `TTSDispatcher` ([`audiobook_factory.tts_dispatcher`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts_dispatcher.py))
*Token-Bucket concurrent speech synthesizer, multimodal audio director, and zero-voice-drift orchestrator.*  
*(See comprehensive technical manuals: [`docs/GEMINI_TTS_SYNTHESIS_AND_DIRECTING.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/GEMINI_TTS_SYNTHESIS_AND_DIRECTING.md) and [`docs/VOICE_CASTING_DIRECTOR_GUIDE.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/VOICE_CASTING_DIRECTOR_GUIDE.md))*

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
        Underlying synthesis (`_call_gemini_tts` and `_call_gemini_multispeaker_batch`) routes directly through
        the ModelGateway control plane via `audiobook_factory.tts.gateway_bridge` (supporting native
        multiSpeakerVoiceConfig batching), while transparently preserving monkeypatch fixtures for testing.
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

### `AgentDirector` ([`audiobook_factory.agent_director`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/agent_director.py))
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

### `SonicBible` ([`audiobook_factory.sonic_bible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/sonic_bible.py))
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

### `SoundBank` ([`audiobook_factory.sound_bank`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/sound_bank.py))
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

### `AcousticBusMatrix` ([`audiobook_factory.acoustic_bus_matrix`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/acoustic_bus_matrix.py))
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

### `UniversalSoundBankIngester` ([`audiobook_factory.sound_bank_ingest`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/sound_bank_ingest.py))
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

### `CinemaAudioEngine` ([`audiobook_factory.cinema_audio_engine`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/cinema_audio_engine.py))
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

### `ManifestRenderer` ([`audiobook_factory.manifest_renderer`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/manifest_renderer.py))
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

### `Mastering` ([`audiobook_factory.mastering`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/mastering.py))
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

### `Packager` ([`audiobook_factory.packager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/packager.py))
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

### `Foley & Magic Composite Baker` ([`scripts/bake_foley_composites.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/scripts/bake_foley_composites.py))
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

## 🛡️ Quality Gate Auditor ([`audiobook_factory.gate_auditor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gate_auditor.py))

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

### 1. `BookBible` & `BookEntity` ([`audiobook_factory.translation.book_bible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/book_bible.py))
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

### 5. World & Character Memory 2.0 ([`audiobook_factory.translation.memory`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/memory/))
*(See complete specification: [`docs/WORLD_AND_CHARACTER_MEMORY_2_0.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/WORLD_AND_CHARACTER_MEMORY_2_0.md))*

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

### A. Phase 3 Retrieval Contracts ([`audiobook_factory.contracts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/contracts.py))

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

## ⚖️ Unified LLM Creative Quality & Audit Judge Protocol ([`audiobook_factory.gates.llm_judge`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/gates/llm_judge.py))

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

### 1. `AudioRealityAuditor` ([`audiobook_factory.audio_reality_auditor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio_reality_auditor.py))

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

### 2. `AudioVerificationGate` ([`audiobook_factory.sound_bank.verification_gate`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/sound_bank/verification_gate.py))

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

### 1. `ProjectClassifier` ([`audiobook_factory.project_classifier`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/project_classifier.py))

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

### 2. `SonicBibleGenerator` ([`audiobook_factory.sonic_bible_generator`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/sonic_bible_generator.py))

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

### 3. `CharacterCaster` ([`audiobook_factory.character_caster`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/character_caster.py))

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

## 🛡️ Centralized Permissive Safety Protocol ([`audiobook_factory.safety`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/safety.py))

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
    metadata: Dict[str, Any] = field(default_factory=dict)
```
- `metadata`: Flexible operational telemetry dictionary tracking attempt count (`attempt`), mock execution indicators (`mock_mode`), latency markers, and key previews.


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
        - Mutual exclusion (0% double-allocations, Concurrency = 1 per key).
        - Workload isolation: Dedicated lease tracking for 'tts' (10 RPD audio model ceilings) vs 'text'.
        - Preferred key affinity: Resolves preferred_key_alias with deterministic SQL parameter binding order.
        - Dead PID crash reclamation via Win32 kernel32.OpenProcess / POSIX kill(0).
        - CallerIdentity quota enforcement.
        - Quota rollover (Midnight US Pacific Time for Google AI Studio) and model isolation.
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

#### [`BaseProviderAdapter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/base.py#L44)
*Abstract polymorphic adapter interface implemented by all model providers (Gemini, OpenAI-compatible, Local GPU).*

```python
class BaseProviderAdapter(ABC):
    @abstractmethod
    def generate_text(self, request: ExecutionPlan, prompt: str, **kwargs: Any) -> GenerationResult: ...

    @abstractmethod
    def synthesize_speech(self, request: ExecutionPlan, text: str, voice_name: str = "Puck", **kwargs: Any) -> SpeechResult: ...
```

#### [`GeminiProviderAdapter`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/gemini.py#L32)
*Authoritative adapter for Google Gemini multimodal reasoning, text generation, and speech synthesis.*
- **Secret Hygiene**: Sanitized API calls using official stealth `X-goog-api-key` headers via `get_stealth_sdk_headers()`. Plaintext API key query parameters (`?key={key}`) are permanently removed.
- **5-Category `BLOCK_NONE` Creative Safety Framing**: Operates with maximum permissive developer thresholds across all 5 harm categories to prevent false-positive truncation of legitimate dramatic literature and earthy character dialogue:
  1. `HARM_CATEGORY_HARASSMENT`: `BLOCK_NONE`
  2. `HARM_CATEGORY_HATE_SPEECH`: `BLOCK_NONE`
  3. `HARM_CATEGORY_SEXUALLY_EXPLICIT`: `BLOCK_NONE`
  4. `HARM_CATEGORY_DANGEROUS_CONTENT`: `BLOCK_NONE`
  5. `HARM_CATEGORY_CIVIC_INTEGRITY`: `BLOCK_NONE`
- **Speech Synthesis Support**: Directly decodes base64-encoded linear PCM audio parts returned by `gemini-3.8-flash-tts` into standardized `SpeechResult` structures.


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

## 📊 Production Telemetry Ledger ([`audiobook_factory.telemetry`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/telemetry.py))

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

## 🎙️ Studio TTS Platform Core ([`audiobook_factory.tts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/))

The Studio TTS Platform Core provides a unified 4-tier speech synthesis platform (Option C: Layered Shared Core with Specialized Pipeline Facades). All public interfaces are exported directly from [`audiobook_factory.tts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/__init__.py) and [`audiobook_factory.tts_dispatcher`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts_dispatcher.py).

### 1. `GenericTTSClient` ([`audiobook_factory/tts/facades/generic_client.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/generic_client.py))
*High-level client facade for single-utterance, ad-hoc, low-latency speech synthesis (UI feedback, CLI prompts, voice testing).*

```python
class GenericTTSClient:
    def __init__(self, orchestrator: Optional[TTSCoreOrchestrator] = None): ...

    def speak(
        self,
        text_or_request: Union[str, CanonicalTTSRequest],
        voice: str = "Puck",
        model: str = "gemini-3.8-flash",
        output_path: Optional[Union[str, Path]] = None,
        validate: bool = True,
        speaker: str = "Narrator",
        delivery_intent: Optional[DeliveryIntent] = None,
        **guard_kwargs: Any,
    ) -> Tuple[Optional[Path], SynthesizedAudioChunk, Optional[AudioValidationResult]]:
        """
        Synthesizes a single text or request, returning raw audio chunk and optional saved file path.
        Dispatches directly through UniversalInputGuard and TTSCoreOrchestrator (<800ms latency).
        """

    def speak_to_bytes(
        self,
        text_or_request: Union[str, CanonicalTTSRequest],
        voice: str = "Puck",
        model: str = "gemini-3.8-flash",
        validate: bool = True,
        speaker: str = "Narrator",
        delivery_intent: Optional[DeliveryIntent] = None,
        **guard_kwargs: Any,
    ) -> bytes:
        """
        Synthesizes single text or request directly into a complete in-memory RIFF WAV byte stream.
        """
```

**Usage Example**:
```python
from audiobook_factory.tts import GenericTTSClient

client = GenericTTSClient()

# 1. Synthesize and save directly to file
out_path, chunk, validation = client.speak(
    "प्रणाम! स्टूडियो ऑडिओबुक इंजन में आपका स्वागत है।",
    voice="Puck",
    output_path="output/greeting.wav",
    validate=True,
)
print(f"Generated: {out_path} ({chunk.duration_sec:.2f}s, SR={chunk.sample_rate}Hz)")

# 2. In-memory bytes for streaming API or instant playback
wav_bytes = client.speak_to_bytes("तत्काल ऑडियो स्ट्रीम।", voice="Aoede")
assert wav_bytes.startswith(b"RIFF")
```

---

### 2. `LongFormTTSClient` ([`audiobook_factory/tts/facades/long_form_client.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/long_form_client.py))
*Client facade for continuous long-form narrative prose and novel chapters. Handles 4-tier semantic chunking, concurrent synthesis, checkpoint resumption, and net-silence stitching.*

```python
class LongFormTTSClient:
    def __init__(self, orchestrator: Optional[TTSCoreOrchestrator] = None): ...

    def synthesize_prose(
        self,
        text: str,
        output_path: Union[str, Path],
        voice: str = "Puck",
        model: str = "gemini-3.8-flash",
        speaker: str = "Narrator",
        target_words_per_chunk: int = 120,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> Tuple[Path, float, List[SynthesizedAudioChunk]]:
        """
        Synthesizes arbitrary long-form prose by semantically chunking, synthesizing concurrently,
        and stitching into a seamless master audio file with net silence and Hann micro-fades.
        """

    def synthesize_chapter(
        self,
        chapter_num: int,
        text: str,
        output_file: Optional[Union[str, Path]] = None,
        checkpoint_dir: Optional[Union[str, Path]] = None,
        voice: str = "Puck",
        model: str = "gemini-3.8-flash",
        speaker: str = "Narrator",
        target_words_per_chunk: int = 120,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> ChapterMasterResult:
        """
        Synthesizes a complete chapter with checkpoint caching (checkpoint_manifest.json)
        and returns a structured ChapterMasterResult. Resumes seamlessly from interruptions.
        """
```

**Usage Example**:
```python
from pathlib import Path
from audiobook_factory.tts import LongFormTTSClient

client = LongFormTTSClient()
chapter_text = Path("data/chapter_01.txt").read_text(encoding="utf-8")

result = client.synthesize_chapter(
    chapter_num=1,
    text=chapter_text,
    output_file="output/chapter_001_master.wav",
    checkpoint_dir="checkpoints/ch001",
    voice="Puck",
    target_words_per_chunk=120,
    progress_callback=lambda pct, cur, tot: print(f"Progress: {pct*100:.1f}% ({cur}/{tot})"),
)
print(f"Master created at: {result.master_audio_path} ({result.duration_sec}s, {result.total_segments} chunks)")
```

---

### 3. `MultiCastStudioClient` ([`audiobook_factory/tts/facades/multi_cast_client.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/multi_cast_client.py))
*Client facade for ensemble multi-character screenplay synthesis, character casting maps, anti-swap attribution verification, 4D acoustic formants, TakeBank auditioning, and conversational turn latencies.*

```python
class MultiCastStudioClient:
    def __init__(self, orchestrator: Optional[TTSCoreOrchestrator] = None): ...

    def produce_screenplay(
        self,
        segments: List[Dict[str, Any]],
        character_voices: Dict[str, str],
        chapter_num: int,
        output_dir: Union[str, Path],
        model: str = "gemini-3.8-flash",
        default_narrator_voice: str = "Puck",
        cast_lock_file: Optional[Union[str, Path]] = None,
        character_formants: Optional[Dict[str, Union[str, FormantProfile]]] = None,
        enable_take_bank: bool = False,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> ChapterMasterResult:
        """
        Synthesizes an ensemble multi-character screenplay, applies 4D formants,
        auditions candidate takes via TakeBank, applies conversational turn latency,
        and produces an EBU R128 compliant master audio file.
        """
```

**Usage Example**:
```python
from audiobook_factory.tts import MultiCastStudioClient, FormantProfile

client = MultiCastStudioClient()
segments = [
    {"speaker": "Narrator", "text": "जंगल की गहराई में हवा थम चुकी थी।"},
    {"speaker": "Geralt", "text": "रुको, यहाँ कोई छिपा हुआ है।", "acting": {"emotion": "grave", "delivery_style": "restraint"}},
    {"speaker": "Jaskier", "text": "क्या फिर से कोई पिशाच?", "acting": {"emotion": "anxious"}, "performance_priority": "high"},
]

result = client.produce_screenplay(
    segments=segments,
    character_voices={"Narrator": "Puck", "Geralt": "Charon", "Jaskier": "Fenrir"},
    chapter_num=1,
    output_dir="output/chapter_01",
    cast_lock_file="configs/cast_lock.json",
    character_formants={
        "Geralt": FormantProfile.DEEP_RESONANT,
        "Jaskier": FormantProfile.CRISP_TENOR,
    },
    enable_take_bank=True,
)
```

---

### 4. `UniversalInputGuard` ([`audiobook_factory/tts/guard/input_guard.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/input_guard.py))
*Universal text normalization, Unicode NFC hygiene, control character stripping, delivery intent extraction, and deterministic numeral/currency phonetization.*

```python
class UniversalInputGuard:
    @classmethod
    def guard_and_normalize(
        cls,
        raw_text: str,
        voice_id: str,
        segment_uid: Optional[str] = None,
        speaker: str = "Narrator",
        language: str = "hi-IN",
        temperature: float = 0.40,
        sample_rate: int = 24000,
        pipeline_mode: TTSPipelineMode = TTSPipelineMode.GENERIC,
        chapter_num: Optional[int] = None,
        scene_num: Optional[int] = None,
        default_intent: Optional[DeliveryIntent] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CanonicalTTSRequest:
        """
        Validates, normalizes, and transforms raw input text into an immutable CanonicalTTSRequest.
        Enforces the Sacred Literary Text vs. Spoken Text boundary:
        - raw_text / literary_text is strictly preserved.
        - spoken_text is phonetized (Devanagari numerals, currency words, abbreviations).
        - Neural stage tags [whispers] are extracted to DeliveryIntent and stripped from spoken text.
        (Authoritative method; also aliased as sanitize_and_guard).
        """
```

**Usage Example**:
```python
from audiobook_factory.tts import UniversalInputGuard

req = UniversalInputGuard.guard_and_normalize(
    raw_text="Geralt whispered [whispers], 'We need 500 coins for the contract.'",
    voice_id="Charon",
    speaker="Geralt",
)

# Sacred Literary Text (Immutable for display/subtitles)
assert req.literary_text == "Geralt whispered, 'We need 500 coins for the contract.'"

# Spoken Phonetized Text (Dispatched to neural model)
assert "पाँच सौ" in req.spoken_text
assert "[" not in req.spoken_text  # Zero leaked stage direction brackets!

# Extracted Delivery Intent
assert req.delivery_intent.delivery_style == "whispers"
```

---

### 5. `SemanticProseChunker` ([`audiobook_factory/tts/chunker.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/chunker.py))
*4-Tier semantic chunking engine splitting long prose along natural scene, paragraph, sentence, and clause boundaries to permanently eliminate autoregressive TTS rate drift.*

```python
class SemanticProseChunker:
    @classmethod
    def chunk_prose(
        cls,
        text: str,
        target_words: int = 120,
        max_words: int = 180,
        min_words: int = 40,
    ) -> List[SemanticChunk]:
        """
        Splits long-form text into balanced semantic units using a 4-tier hierarchy:
        Level 1: Scene Breaks (---, ***, # headers)
        Level 2: Paragraph Breaks (\n\n) -> Target 80-160 words
        Level 3: Sentence Boundaries (।, ., ?, !) -> Target 30-75 words
        Level 4: Clause Boundaries (,, —, ;) -> Emergency fallback for >45 words
        Level 5: Mid-word slicing is strictly prohibited.
        """
```

**Usage Example**:
```python
from audiobook_factory.tts import SemanticProseChunker

chunks = SemanticProseChunker.chunk_prose(long_prose_text, target_words=120)
for chunk in chunks:
    print(f"UID: {chunk.chunk_uid} | Level: {chunk.level.value} | Words: {chunk.word_count} | Pause: {chunk.suggested_pause_after_ms}ms")
```

---

### 6. `EditorialDSPEngine` ([`audiobook_factory/tts/dsp/editorial.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/dsp/editorial.py))
*Dialogue Editorial Layer combining zero-crossing endpoint alignment (-52 dBFS speech floor), raised-cosine Hann micro-fades (12ms in / 18ms out), and net silence timeline concatenation.*

```python
class EditorialDSPEngine:
    @classmethod
    def process_and_stitch(
        cls,
        chunks_pcm: List[bytes],
        target_pauses_ms: List[int],
        sample_rate: int = 24000,
    ) -> Tuple[bytes, float]:
        """
        Stitches a sequence of 16-bit mono PCM chunks with zero-crossing alignment,
        Hann micro-fades (12ms in / 18ms out), TPDF dither, and net silence subtraction:
            Injected_Silence = max(20ms, Target_Pause - (Tail_Decay_A + Head_Margin_B))
        Returns:
            (stitched_pcm_bytes, total_duration_sec)
        """
```

**Usage Example**:
```python
from audiobook_factory.tts import EditorialDSPEngine

stitched_pcm, total_dur = EditorialDSPEngine.process_and_stitch(
    chunks_pcm=[chunk1_pcm, chunk2_pcm, chunk3_pcm],
    target_pauses_ms=[350, 450],
    sample_rate=24000,
)
print(f"Seamlessly stitched {len(stitched_pcm)} bytes ({total_dur:.2f}s) with zero clicks.")
```

---

### 7. `FormantSculptor` ([`audiobook_factory/tts/formant_sculptor.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/formant_sculptor.py))
*Parametric EQ and acoustic formant filter ensuring character voice distinctiveness when multiple characters share base neural voices.*

```python
class FormantSculptor:
    @classmethod
    def apply_formant_eq(
        cls,
        pcm_bytes: bytes,
        profile: Union[FormantProfile, str],
        sample_rate: int = 24000,
    ) -> bytes:
        """
        Applies calibrated 2nd-order Peaking EQ Biquad Filters on 16-bit signed PCM.
        Features float-precision calculation, headroom pre-attenuation (10^(-G_max/20)),
        and soft hyperbolic tangent knee peak limiting (<= 32,760) to eliminate clipping.
        """
```

**Available Profiles**: `WARM_BARITONE`, `CRISP_TENOR`, `BRIGHT_FEMALE`, `DEEP_RESONANT`, `ELDERLY_TEXTURED`, `CHILD_ANIME`, `NEUTRAL`.

**Usage Example**:
```python
from audiobook_factory.tts import FormantSculptor, FormantProfile

# Apply deep resonant baritone profile to male warrior character
sculpted_pcm = FormantSculptor.apply_formant_eq(
    pcm_bytes=actor_pcm,
    profile=FormantProfile.DEEP_RESONANT,
    sample_rate=24000,
)
```

---

### 8. `TakeBankManager` ([`audiobook_factory/tts/take_bank_manager.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/take_bank_manager.py))
*Multi-take auditioning and candidate selection manager for high-priority dramatic screenplay turns.*

```python
class TakeBankManager:
    def __init__(self, orchestrator: Optional[TTSCoreOrchestrator] = None): ...

    def generate_candidate_takes(
        self,
        base_request: CanonicalTTSRequest,
        priority: str = "standard",
        model: str = "gemini-3.8-flash",
    ) -> List[CandidateTake]:
        """
        Generates candidate takes based on performance priority:
        - 'standard': 1 take (standard delivery)
        - 'focused': 2 takes (standard, restraint)
        - 'high': 3 takes (standard, restraint, vulnerable)
        - 'climactic': 4 takes (standard, restraint, vulnerable, exposed)
        Scores and ranks all candidate takes.
        """

    def select_best_take(
        self,
        base_request: CanonicalTTSRequest,
        priority: str = "standard",
        model: str = "gemini-3.8-flash",
    ) -> Tuple[SynthesizedAudioChunk, Optional[AudioValidationResult], List[CandidateTake]]:
        """
        Convenience method that generates candidate takes, audits quality,
        and returns the single highest-scoring take.
        """
```

**Usage Example**:
```python
from audiobook_factory.tts import TakeBankManager, CanonicalTTSRequest

manager = TakeBankManager()
best_chunk, validation, takes = manager.select_best_take(
    base_request=dialogue_req,
    priority="climactic",
    model="gemini-3.8-flash",
)
print(f"Selected take {best_chunk.segment_uid} from {len(takes)} candidate variants.")
```

---

### 9. `TwoTierAudioQualityGate` ([`audiobook_factory/tts/quality_gate.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/quality_gate.py))
*Deterministic mathematical acoustic validation and phonetic duration bounds checking.*

```python
class TwoTierAudioQualityGate:
    @classmethod
    def audit_chunk(
        cls,
        request: CanonicalTTSRequest,
        chunk: SynthesizedAudioChunk,
        skip_tier2: bool = False,
    ) -> AudioValidationResult:
        """
        Runs Tier 1 Mathematical Acoustic Probe (<5ms, zero-cost):
        - Peak Amplitude: Peak >= 1500
        - RMS Loudness: -52.0 dBFS <= RMS <= -6.0 dBFS
        - DC Bias Offset: |DC| <= 0.05
        - Consecutive Clipped Samples <= 5
        - Internal Dead Air <= 2.5s
        Runs Tier 2 Phonetic Duration Bounds:
        - Duration ratio: 0.12s/word <= R <= 0.95s/word (rejects skipped lines or runaway stutters).
        """
```

**Usage Example**:
```python
from audiobook_factory.tts import TwoTierAudioQualityGate

val = TwoTierAudioQualityGate.audit_chunk(request, chunk)
if val.passed:
    print(f"Chunk certified: RMS={val.rms_dbfs:.1f} dBFS, Peak={val.peak_amplitude}")
else:
    print(f"Chunk failed quality gate: {val.diagnostics}")
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

## 🛠️ Resilient System & Casting Utilities ([`audiobook_factory`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/))

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

### 2. Cross-Platform Executable Resolvers ([`audiobook_factory.tts.constants`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/constants.py))

```python
def get_ffprobe() -> str:
    """Returns resolved path to ffprobe executable via PATH or project fallback."""

def get_ffmpeg() -> str:
    """Returns resolved path to ffmpeg executable via PATH or project fallback."""
```

### 3. Windows Atomic File Promotion ([`audiobook_factory.tts.providers.gemini`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/gemini.py))

```python
def _atomic_replace(src: Path, dst: Path, max_attempts: int = 8) -> None:
    """
    Atomically promotes src to dst with exponential backoff retry for Windows
    file-locking defense (WinError 32) and copy2 fallback.
    """
```

---

## 🎛️ Pro-Grade AI Vocal Mastering & Audio DSP Subsystem (v5.4)

### 1. Strongly Typed Audio Contracts ([`audiobook_factory.audio.contracts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/contracts.py))

#### `DSPConfig`
*Pydantic v2 configuration schema governing C++ JUCE DSP vocal mastering and optional VST3 hosting.*

```python
class DSPConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enable_pedalboard: bool = Field(default=True, description="Attempt C++ Pedalboard DSP before FFmpeg fallback")
    enable_vst3: bool = Field(default=False, description="Enable headless VST3 plugin insertion")
    vst3_plugin_path: Optional[Path] = Field(default=None, description="Path to .vst3 bundle")
    subsonic_hz: float = Field(default=75.0, ge=20.0, le=120.0, description="Subsonic highpass filter cutoff in Hz")
    boxiness_cut_hz: float = Field(default=320.0, ge=150.0, le=600.0, description="Parametric notch frequency for chest resonance in Hz")
    boxiness_cut_db: float = Field(default=-1.5, ge=-6.0, le=0.0, description="Boxiness attenuation gain in dB")
    presence_lift_hz: float = Field(default=3200.0, ge=1500.0, le=6000.0, description="Speech presence clarity center frequency in Hz")
    presence_lift_db: float = Field(default=0.8, ge=0.0, le=4.0, description="Speech presence boost in dB")
    target_lufs: float = Field(default=-19.0, ge=-24.0, le=-14.0, description="EBU R128 integrated loudness target in LUFS")
    true_peak_ceiling_dbtp: float = Field(default=-1.5, ge=-3.0, le=-0.5, description="Lookahead True-Peak ceiling in dBTP")
    compressor_threshold_db: float = Field(default=-18.0, ge=-30.0, le=-6.0, description="Optical compressor threshold in dB")
    compressor_ratio: float = Field(default=2.5, ge=1.2, le=6.0, description="Optical compressor compression ratio")
    compressor_attack_ms: float = Field(default=25.0, ge=5.0, le=100.0, description="Compressor attack time in ms")
    compressor_release_ms: float = Field(default=120.0, ge=20.0, le=500.0, description="Compressor release time in ms")
```

#### `DSPMasteringResult`
*Immutable telemetry model emitted upon completing vocal DSP mastering.*

```python
class DSPMasteringResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    backend_used: Literal["pedalboard_juce_v2", "ffmpeg_dual_pass_linear", "fallback_linear"] = Field(
        ..., description="Mastering engine backend that rendered the artifact"
    )
    output_path: Path = Field(..., description="Rendered 48kHz 24-bit PCM master WAV")
    integrated_lufs: float = Field(..., description="Measured post-master integrated loudness in LUFS")
    true_peak_dbtp: float = Field(..., description="Measured post-master True Peak in dBTP")
    loudness_range_lu: float = Field(default=7.5, description="Measured Loudness Range in LU")
    execution_duration_sec: float = Field(default=0.0, ge=0.0, description="Processing wall-clock time in seconds")
```

#### `AudioQAConfig`
*Pydantic v2 configuration schema governing acoustic, VAD, and script QA auditing.*

```python
class AudioQAConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enable_vad: bool = Field(default=True, description="Enable Voice Activity Detection for boundary checks")
    enable_whisper_alignment: bool = Field(default=False, description="Enable optional Faster-Whisper script alignment")
    whisper_model_size: str = Field(default="base", description="Whisper model tier: tiny, base, small, medium")
    min_wpm: float = Field(default=75.0, description="Minimum acceptable words per minute")
    max_wpm: float = Field(default=240.0, description="Maximum acceptable words per minute")
    min_pause_ms: int = Field(default=120, description="Minimum natural inter-phrase pause in ms")
    max_pause_ms: int = Field(default=1800, description="Maximum natural pause before dead-air alert in ms")
    duration_tolerance_ratio: float = Field(default=0.40, description="Maximum allowable duration mismatch relative to text length")
    min_mos_threshold: float = Field(default=3.5, description="Minimum Mean Opinion Score before warning")
```

#### `SegmentQAEvaluation`
*Immutable forensic evaluation result for an individual speech segment.*

```python
class SegmentQAEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    segment_index: int = Field(..., ge=1, description="1-indexed sequence order")
    segment_uid: str = Field(..., description="Unique segment identifier")
    speaker: str = Field(default="Narrator", description="Character or narrator name")
    status: Literal["PASS", "WARN", "FAIL"] = Field(default="PASS", description="Audit verdict")
    duration_ms: int = Field(..., ge=0, description="Physical audio duration in milliseconds")
    estimated_wpm: float = Field(default=140.0, description="Estimated speaking rate in words per minute")
    char_per_sec: float = Field(default=15.0, description="Character-to-duration speed in characters per second")
    predicted_mos: float = Field(default=4.5, ge=1.0, le=5.0, description="Predicted Speech Quality MOS")
    silence_leading_ms: int = Field(default=0, ge=0, description="Leading dead air in ms")
    silence_trailing_ms: int = Field(default=0, ge=0, description="Trailing dead air in ms")
    issues: List[str] = Field(default_factory=list, description="Detected anomalies or quality notices")
    remediation_advice: Optional[str] = Field(default=None, description="Actionable correction recommendation")
```

#### `ChapterQAReport`
*Consolidated forensic report covering all speech segments of a chapter.*

```python
class ChapterQAReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    chapter_num: int = Field(..., ge=1, description="Chapter index")
    total_segments: int = Field(default=0, ge=0, description="Total audited speech segments")
    passed_segments: int = Field(default=0, ge=0, description="Count of passed takes")
    warned_segments: int = Field(default=0, ge=0, description="Count of takes with non-blocking warnings")
    failed_segments: int = Field(default=0, ge=0, description="Count of rejected/fatal takes")
    overall_status: Literal["PASS", "WARN", "FAIL"] = Field(default="PASS", description="Overall chapter QA status")
    mean_mos: float = Field(default=4.5, ge=1.0, le=5.0, description="Average predicted speech MOS")
    evaluations: List[SegmentQAEvaluation] = Field(default_factory=list, description="Individual segment evaluations")
```

#### `EnhancerConfig`
*Pydantic v2 configuration governing DeepFilterNet3 neural speech restoration.*

```python
class EnhancerConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enable_neural_enhancement: bool = Field(default=False, description="Enable DeepFilterNet3 neural vocal cleaning")
    snr_bypass_threshold_db: float = Field(default=45.0, description="SNR threshold above which neural filter is bypassed")
    max_energy_diff_db: float = Field(default=2.0, description="Maximum allowable RMS energy difference before rejection")
    model_type: str = Field(default="deepfilternet3", description="Neural enhancer model architecture")
```

#### `ReferenceMatcherConfig`
*Pydantic v2 configuration governing Matchering 2.0 reference spectrum matching.*

```python
class ReferenceMatcherConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enable_reference_matching: bool = Field(default=False, description="Enable reference spectrum matching")
    reference_track_path: Optional[Path] = Field(default=None, description="Path to golden reference WAV master")
    max_spectral_correction_db: float = Field(default=3.0, ge=0.5, le=6.0, description="Hard clamp on spectral EQ adjustment in dB")
```

---

### 2. C++ JUCE Vocal DSP Processor ([`audiobook_factory.audio.dsp`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/dsp.py))

#### `has_pedalboard_engine() -> bool`
Returns `True` if Spotify Pedalboard (C++ JUCE) is installed and loadable in the current runtime environment.

#### `has_pyloudnorm_engine() -> bool`
Returns `True` if Pyloudnorm (ITU-R BS.1770-4) is available.

#### `VocalDSPProcessor`
*Studio-grade vocal audio mastering processor coordinating C++ JUCE DSP, BS.1770-4 loudness compliance, and deterministic FFmpeg fallback.*

```python
class VocalDSPProcessor:
    def __init__(self, dsp_config: Optional[DSPConfig] = None, ffmpeg_bin: Optional[str] = None): ...

    @property
    def is_hardware_accelerated(self) -> bool:
        """Returns True if Spotify Pedalboard C++ JUCE acceleration is active."""

    def measure_loudness(self, audio_np: np.ndarray, sr: int = 48000) -> Tuple[float, float, float]:
        """
        Measures ITU-R BS.1770-4 Integrated LUFS, True Peak (dBTP), and Loudness Range (LRA).
        Returns: (integrated_lufs, true_peak_dbtp, loudness_range_lu)
        """

    def build_pedalboard_chain(self, config: Optional[DSPConfig] = None) -> Optional[Any]:
        """Constructs Spotify Pedalboard C++ DSP chain with EQ, optical comp, VST3, and limiter."""

    def process_samples(self, audio_np: np.ndarray, sr: int = 48000, config: Optional[DSPConfig] = None) -> np.ndarray:
        """Applies in-memory C++ JUCE DSP effects to float32 audio samples [-1.0, 1.0]."""

    def master_chapter(
        self,
        input_wav: Union[str, Path],
        output_wav: Union[str, Path],
        profile: Optional[MasteringProfile] = None,
        dsp_config: Optional[DSPConfig] = None,
    ) -> DSPMasteringResult:
        """
        Executes end-to-end mastering of chapter pre-master audio to 48kHz 24-bit PCM master WAV.
        Employs C++ JUCE Pedalboard DSP when available, otherwise falls back to FFmpeg.
        """
```

---

### 3. Forensic Audio QA Auditor ([`audiobook_factory.audio.qa_auditor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/qa_auditor.py))

#### `has_whisper_engine() -> bool`
Returns `True` if Faster-Whisper or OpenAI Whisper is installed.

#### `AudioQAAuditor`
*Forensic QA Auditor for dialogue segments and chapter master deliverables.*

```python
class AudioQAAuditor:
    def __init__(self, config: Optional[AudioQAConfig] = None): ...

    def audit_segment(
        self,
        audio_path: Union[str, Path],
        expected_text: str = "",
        speaker: str = "Narrator",
        segment_index: int = 1,
        segment_uid: Optional[str] = None,
    ) -> SegmentQAEvaluation:
        """
        Audits a single speech audio segment against expected screenplay text.
        Returns strongly typed SegmentQAEvaluation with PASS / WARN / FAIL verdict.
        """

    def audit_chapter(
        self,
        audio_segments: List[Union[str, Path]],
        script_segments: Optional[List[Dict[str, Any]]] = None,
        chapter_num: int = 1,
    ) -> ChapterQAReport:
        """
        Executes comprehensive forensic audit across all segments of a chapter.
        Returns consolidated ChapterQAReport.
        """

    def estimate_speech_mos(
        self,
        data: np.ndarray,
        sr: int = 48000,
        peak_amp: float = 0.5,
        rms_amp: float = 0.1,
    ) -> float:
        """
        Estimates non-intrusive Mean Opinion Score (1.0 to 5.0) based on crest factor,
        DC offset, and clipping saturation.
        """
```

---

### 4. Neural Vocal Enhancer ([`audiobook_factory.audio.enhancer`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/enhancer.py))

#### `has_deepfilter_engine() -> bool`
Returns `True` if DeepFilterNet3 and PyTorch are installed.

#### `NeuralVocalEnhancer`
*Surgical vocal enhancement processor with selective auto-bypass and energy difference clamping.*

```python
class NeuralVocalEnhancer:
    def __init__(self, config: Optional[EnhancerConfig] = None): ...

    @property
    def is_neural_active(self) -> bool:
        """Returns True if DeepFilterNet3 neural engine is active."""

    @staticmethod
    def estimate_snr_db(audio_np: np.ndarray) -> float:
        """Estimates Signal-to-Noise Ratio in dB from speech energy vs quietest 10th percentile frames."""

    def enhance_samples(self, audio_np: np.ndarray, sr: int = 48000) -> Tuple[np.ndarray, bool]:
        """
        Applies neural enhancement or spectral cleaning to float32 samples.
        Returns: (enhanced_audio_np, was_enhanced_boolean)
        """

    def enhance_file(self, input_wav: Union[str, Path], output_wav: Union[str, Path]) -> bool:
        """Enhances a WAV audio file on disk, writing output as 48kHz 24-bit PCM WAV."""
```

---

### 5. Reference Spectrum Matcher ([`audiobook_factory.audio.reference_matcher`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/audio/reference_matcher.py))

#### `has_matchering_engine() -> bool`
Returns `True` if Matchering 2.0 is installed.

#### `ReferenceSpectrumMatcher`
*Automated reference mastering and spectral envelope matcher with hard ±3.0dB clamping.*

```python
class ReferenceSpectrumMatcher:
    def __init__(self, config: Optional[ReferenceMatcherConfig] = None): ...

    @property
    def is_matchering_active(self) -> bool:
        """Returns True if Matchering 2.0 is active."""

    def match_spectrum(
        self,
        target_np: np.ndarray,
        reference_np: np.ndarray,
        sr: int = 48000,
    ) -> np.ndarray:
        """Applies reference spectrum matching with +/-3dB hard clamping to float32 samples."""

    def match_files(
        self,
        target_wav: Union[str, Path],
        reference_wav: Union[str, Path],
        output_wav: Union[str, Path],
    ) -> Path:
        """Matches target WAV to reference WAV on disk, writing output as 48kHz 24-bit PCM WAV."""
```

---

### 6. Antigravity Audio MCP Server Tools ([`audiobook_factory.mcp.server`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/mcp/server.py))

#### `apply_vocal_dsp_tool`
```python
def apply_vocal_dsp_tool(
    input_wav: str,
    output_wav: str,
    target_lufs: float = -19.0,
    true_peak_ceiling_dbtp: float = -1.5,
    subsonic_hz: float = 75.0,
    boxiness_cut_db: float = -1.5,
    presence_lift_db: float = 0.8,
) -> Dict[str, Any]:
    """Applies C++ JUCE parametric vocal EQ, optical compression, and lookahead True-Peak limiting."""
```

#### `audit_audio_quality_tool`
```python
def audit_audio_quality_tool(
    audio_path: str,
    expected_text: str = "",
    speaker: str = "Narrator",
    segment_index: int = 1,
) -> Dict[str, Any]:
    """Audits a single speech audio segment for dead air, WPM pacing, dropouts, loops, and MOS."""
```

#### `match_reference_spectrum_tool`
```python
def match_reference_spectrum_tool(
    target_wav: str,
    reference_wav: str,
    output_wav: str,
    max_clamp_db: float = 3.0,
) -> Dict[str, Any]:
    """Matches frequency spectrum and tonal envelope of target audio to a golden reference track."""
```

#### `enhance_vocal_stem_tool`
```python
def enhance_vocal_stem_tool(
    input_wav: str,
    output_wav: str,
    snr_bypass_db: float = 45.0,
) -> Dict[str, Any]:
    """Cleans synthetic TTS hash and room noise via DeepFilterNet3 with selective auto-bypass."""
```

#### `measure_ebu_r128_loudness_tool`
```python
def measure_ebu_r128_loudness_tool(audio_path: str) -> Dict[str, Any]:
    """Measures ITU-R BS.1770-4 Integrated Loudness (LUFS), True Peak (dBTP), and LRA."""
```

#### `audit_chapter_qa_tool`
```python
def audit_chapter_qa_tool(
    audio_segments: List[str],
    script_segments: Optional[List[Dict[str, Any]]] = None,
    chapter_num: int = 1,
) -> Dict[str, Any]:
    """Audits an entire chapter timeline and returns aggregated forensic QA report."""
```

#### `run_stdio_server`
```python
def run_stdio_server() -> None:
    """Simple JSON-RPC / Stdio server loop for Antigravity autonomous agent communication."""
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

---

## 🎙️ 9. Modular Studio TTS Platform Core (Option C) ([`audiobook_factory.tts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/__init__.py))

The **Studio TTS Platform Core** implements Option C (*Layered Shared Core with Specialized Pipeline Facades*), fully certified with **882/882 passing tests** and documented in [`TTS_PLATFORM_CORE_SPECIFICATION.md`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/docs/TTS_PLATFORM_CORE_SPECIFICATION.md). It decouples high-level caller workflows into three specialized client facades backed by a unified 5-tier orchestration stack:
1. **Tier 1 (Specialized Facades)**: High-level caller interfaces for ad-hoc speech, long-form novel prose, and multi-character ensemble audio dramas.
2. **Tier 2 (Universal Input Guards & Phonetization)**: Deterministic text normalization preserving sacred authorial prose while phonetizing numerals, currencies, and abbreviations into Devanagari Hindi words and extracting stage directions into delivery intent.
3. **Tier 3 (Semantic Prose Chunker & Core Orchestration)**: 4-tier hierarchical chunking and batch synthesis dispatching with rate-limited key pool management.
4. **Tier 4 (Pluggable Model Adapters & Registry)**: Abstract provider layer supporting Google Gemini Flash TTS and local Qwen3-TTS with dynamic registry lookup.
5. **Tier 5 (Two-Tier Quality Gate & Editorial DSP)**: Mathematical acoustic probe, phonetic duration validation, 4D biquad formant sculpting, TakeBank candidate auditioning, and net-silence dynamic timeline concatenation.

---

### 9.1 Data Contracts ([`audiobook_factory.tts.contracts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/contracts.py))

#### `TTSPipelineMode`
*Enumeration defining execution mode and caller pipeline semantics.*

```python
class TTSPipelineMode(str, Enum):
    GENERIC = "generic"          # Single-line, ad-hoc, or notification synthesis
    LONG_FORM = "long_form"      # Multi-page / full chapter prose streams
    MULTI_CAST = "multi_cast"    # Ensemble multi-character screenplay audio drama
```

#### `DeliveryIntent`
*Strongly-typed emotional, dramatic, and vocal delivery directives parsed from screenplay acting instructions or neural stage direction tags.*

```python
class DeliveryIntent(BaseModel):
    model_config = ConfigDict(frozen=True)

    emotion: str = "neutral"
    delivery_style: str = "standard"
    intensity: str = "medium"               # 'low', 'medium', 'high', 'explosive'
    proximity: str = "normal"               # 'intimate', 'close_mic', 'normal', 'distant'
    pacing_multiplier: float = 1.0          # 0.75 to 1.35
    memory_vocal_constraint: Optional[str] = None
    extracted_stage_cues: List[str] = Field(default_factory=list)
    raw_style_descriptor: Optional[str] = None
```

#### `CanonicalTTSRequest`
*Standardized, immutable request payload passed to the TTS Orchestrator and Model Adapters, strictly enforcing the Sacred Text vs. Spoken Text invariant.*

```python
class CanonicalTTSRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    segment_uid: str                         # Deterministic segment identifier
    literary_text: str                       # Immutable sacred author text for display/subtitles
    spoken_text: str                         # Sanitized, expanded phonetic text for TTS voice model
    voice_id: str                            # Target neural voice persona (e.g. 'Puck', 'Aoede', 'Charon')
    language: str = "hi-IN"                  # BCP-47 language tag
    speaker: str = "Narrator"                # Speaker character name
    delivery_intent: DeliveryIntent = Field(default_factory=DeliveryIntent)
    temperature: float = 0.40                # Clamped generation temperature [0.30 - 0.52]
    sample_rate: int = 24000                 # Native output sample rate in Hz (default: 24kHz)
    pipeline_mode: TTSPipelineMode = TTSPipelineMode.GENERIC
    chapter_num: Optional[int] = None
    scene_num: Optional[int] = None
    suggested_pause_before_ms: int = 0       # Pre-speech silence suggestion
    suggested_pause_after_ms: int = 400      # Post-speech silence suggestion
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### `SynthesizedAudioChunk`
*Standardized raw audio container returned by any TTS Model Adapter.*

```python
class SynthesizedAudioChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    segment_uid: str                         # Corresponds to originating CanonicalTTSRequest
    pcm_bytes: bytes                         # Raw 16-bit signed little-endian linear PCM
    sample_rate: int = 24000                 # Sampling rate (24000 Hz)
    num_channels: int = 1                    # Mono channel count
    duration_sec: float                      # Exact calculated duration: len(pcm_bytes) / (2 * sample_rate)
    provider_model: str                      # Model used (e.g. 'gemini-3.8-flash', 'qwen3-tts')
    voice_id: str                            # Voice persona applied
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### `AudioValidationResult`
*Comprehensive audit result produced by the Two-Tier Audio Quality Gate.*

```python
class AudioValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    segment_uid: str
    passed: bool                             # Combined boolean verdict (Tier 1 & Tier 2)
    status: str = "PASS"                     # 'PASS', 'WARN', 'FAILED', 'REGENERATE'
    tier1_acoustic_passed: bool              # Mathematical waveform acoustic probe result
    tier2_phonetic_passed: bool              # Lexical preservation / duration ratio result
    peak_amplitude: int                      # Peak sample absolute value (must be >= 1500)
    rms_dbfs: float                          # RMS signal level (must be in [-52.0, -6.0] dBFS)
    dc_bias: float                           # DC offset fraction (must be <= 0.05)
    consecutive_clipped_samples: int         # Max consecutive clipped samples (must be <= 5)
    dead_air_sec: float                      # Internal dead air duration (must be <= 2.5s)
    duration_ratio: float                    # duration_sec / word_count (must be in [0.12, 0.95])
    wer_score: Optional[float] = None        # Word Error Rate from ASR probe (if evaluated)
    omitted_tokens: List[str] = Field(default_factory=list)
    hallucinated_tokens: List[str] = Field(default_factory=list)
    diagnostics: List[str] = Field(default_factory=list)
```

#### `ChapterMasterResult`
*Master deliverable output for a synthesized chapter or dialogue stem.*

```python
class ChapterMasterResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    chapter_num: int
    master_audio_path: Path                  # Path to output 16-bit WAV audio file
    duration_sec: float                      # Total duration in seconds
    total_segments: int                      # Number of stitched audio segments
    integrated_lufs: float = -19.0           # Integrated vocal loudness in LUFS
    true_peak_db: float = -1.5               # Maximum True Peak in dBTP
    loudness_range: float = 4.5              # Loudness range (LRA) in LU
    qc_passed: bool = True                   # Gate audit pass verdict
    stage: str = "dialogue_stem"             # 'dialogue_stem' (Room 4) or 'broadcast_master' (Room 5)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

---

### 9.2 Specialized Client Facades ([`audiobook_factory.tts.facades`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/__init__.py))

#### 1. `GenericTTSClient` ([`audiobook_factory/tts/facades/generic_client.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/generic_client.py))
*High-level facade for low-latency, ad-hoc, single-utterance speech synthesis. Ideal for voice auditioning, CLI testing, interactive prompts, and notifications.*

```python
class GenericTTSClient:
    def __init__(self, orchestrator: Optional[TTSCoreOrchestrator] = None): ...

    def speak(
        self,
        text_or_request: Union[str, CanonicalTTSRequest],
        voice: str = "Puck",
        model: str = "gemini-3.8-flash",
        output_path: Optional[Union[str, Path]] = None,
        validate: bool = True,
        speaker: str = "Narrator",
        delivery_intent: Optional[DeliveryIntent] = None,
        **guard_kwargs: Any,
    ) -> Tuple[Optional[Path], SynthesizedAudioChunk, Optional[AudioValidationResult]]:
        """
        Synthesizes a single utterance or CanonicalTTSRequest.
        Sanitizes text via UniversalInputGuard, dispatches to ModelAdapter, validates
        via TwoTierAudioQualityGate, and optionally writes to output_path.
        Returns: (saved_file_path, synthesized_chunk, validation_result)
        """

    def speak_to_bytes(
        self,
        text_or_request: Union[str, CanonicalTTSRequest],
        voice: str = "Puck",
        model: str = "gemini-3.8-flash",
        validate: bool = True,
        speaker: str = "Narrator",
        delivery_intent: Optional[DeliveryIntent] = None,
        **guard_kwargs: Any,
    ) -> bytes:
        """
        Synthesizes text or CanonicalTTSRequest directly into an in-memory RIFF WAV byte stream.
        """
```

#### 2. `LongFormTTSClient` ([`audiobook_factory/tts/facades/long_form_client.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/long_form_client.py))
*Client facade for continuous long-form audiobook prose synthesis. Manages 4-tier semantic chunking, concurrent synthesis, checkpoint resumption, and net-silence timeline concatenation.*

```python
class LongFormTTSClient:
    def __init__(self, orchestrator: Optional[TTSCoreOrchestrator] = None): ...

    def synthesize_prose(
        self,
        text: str,
        output_path: Union[str, Path],
        voice: str = "Puck",
        model: str = "gemini-3.8-flash",
        speaker: str = "Narrator",
        target_words_per_chunk: int = 120,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> Tuple[Path, float, List[SynthesizedAudioChunk]]:
        """
        Segments long-form prose via SemanticProseChunker into 4-tier chunks,
        synthesizes concurrently via TTSCoreOrchestrator, and stitches with
        EditorialDSPEngine (Hann micro-fades and net silence).
        Returns: (output_wav_path, total_duration_sec, list_of_chunks)
        """

    def synthesize_chapter(
        self,
        chapter_num: int,
        text: str,
        output_file: Optional[Union[str, Path]] = None,
        checkpoint_dir: Optional[Union[str, Path]] = None,
        voice: str = "Puck",
        model: str = "gemini-3.8-flash",
        speaker: str = "Narrator",
        target_words_per_chunk: int = 120,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> ChapterMasterResult:
        """
        Synthesizes a full chapter with persistent checkpoint caching (checkpoint_manifest.json).
        Allows resumption from disk upon interruption without re-synthesizing completed chunks.
        Returns: ChapterMasterResult
        """
```

#### 3. `MultiCastStudioClient` ([`audiobook_factory/tts/facades/multi_cast_client.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/facades/multi_cast_client.py))
*Client facade for multi-character ensemble audio dramas. Coordinates cast locks, anti-swap attribution verification, TakeBank multi-take auditioning, 4D acoustic formant sculpting, and conversational turn latencies.*

```python
class MultiCastStudioClient:
    ANIME_SEIYU_VOICES: List[str] = ["Leda", "hi-in-tutor-7", "Kore", "Zephyr"]

    def __init__(self, orchestrator: Optional[TTSCoreOrchestrator] = None): ...

    def produce_screenplay(
        self,
        segments: List[Dict[str, Any]],
        character_voices: Dict[str, str],
        chapter_num: int,
        output_dir: Union[str, Path],
        model: str = "gemini-3.8-flash",
        default_narrator_voice: str = "Puck",
        cast_lock_file: Optional[Union[str, Path]] = None,
        character_formants: Optional[Dict[str, Union[str, FormantProfile]]] = None,
        enable_take_bank: bool = False,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> ChapterMasterResult:
        """
        Executes complete screenplay synthesis:
        1. Loads cast_lock.json overrides and validates speaker assignments.
        2. Audits screenplay attribution (0% speaker swap tolerance).
        3. Normalizes dialogue through UniversalInputGuard into CanonicalTTSRequests.
        4. Synthesizes standard lines concurrently or audits dramatic turns via TakeBankManager.
        5. Sculpt character formants via FormantSculptor biquad peaking EQ filters.
        6. Stitches timeline using EditorialDSPEngine with contextual speaker turn latencies (250-700ms).
        Returns: ChapterMasterResult
        """
```

---

### 9.3 Universal Input Guards & Phonetization ([`audiobook_factory.tts.guard`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/__init__.py))

#### 1. `UniversalInputGuard` ([`audiobook_factory/tts/guard/input_guard.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/input_guard.py))
*Universal sanitization boundary enforcing the Sacred Text vs. Spoken Text invariant across all TTS pathways.*

```python
class UniversalInputGuard:
    CONTROL_CHAR_REGEX: re.Pattern   # Strips C0 controls, delete (0x7F), zero-width characters
    MAX_ATOMIC_CHARS: int = 1500      # Ceiling for unchunked atomic requests

    @classmethod
    def sanitize_and_guard(
        cls,
        raw_text: str,
        voice_id: str,
        segment_uid: Optional[str] = None,
        speaker: str = "Narrator",
        language: str = "hi-IN",
        temperature: float = 0.40,
        sample_rate: int = 24000,
        pipeline_mode: TTSPipelineMode = TTSPipelineMode.GENERIC,
        chapter_num: Optional[int] = None,
        scene_num: Optional[int] = None,
        default_intent: Optional[DeliveryIntent] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CanonicalTTSRequest:
        """
        Transforms raw text into an immutable CanonicalTTSRequest:
        - Normalizes Unicode to NFC.
        - Strips invisible zero-width and C0 control characters.
        - Extracts delivery intent, emotion, and stage cues via DeliveryIntentExtractor.
        - Phonetizes numerals, units, currencies, and acronyms via NumeralAndTokenExpander.
        - Preserves raw literary_text for subtitles while populating spoken_text for TTS.
        """

    @classmethod
    def strip_control_characters(cls, text: str) -> str:
        """Eliminates non-printable ASCII and Unicode zero-width artifacts."""
```

#### 2. `NumeralAndTokenExpander` / `DevanagariNumeralExpander` ([`audiobook_factory/tts/guard/numeral_expander.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/numeral_expander.py))
*Deterministic expansion of inline digits, Devanagari numerals, currencies, units, percentages, Roman numerals, and Latin acronyms into spoken Hindi words.*

```python
class NumeralAndTokenExpander:
    @classmethod
    def expand_text(cls, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Phonetizes text for Devanagari / Hindi speech:
        1. Currencies: $500 -> पाँच सौ डॉलर, ₹1000 -> एक हज़ार रुपये, €50 -> पचास यूरो
        2. Units: 5km -> 5 किलोमीटर, 10kg -> 10 किलोग्राम, 2hr -> 2 घंटे
        3. Percentages: 50% -> पचास प्रतिशत
        4. Numerals: 500 / ५०० -> पाँच सौ (supports 0 to 999,999,999)
        5. Roman numerals: Chapter IV -> चौथा
        6. Acronyms: FBI -> एफ.बी.आई., CIA -> सी.आई.ए., ISRO -> आई.एस.आर.ओ.
        Returns: (expanded_spoken_text, expansion_ledger)
        """

def number_to_hindi_words(n: int) -> str:
    """Recursively converts integers (0 to 999,999,999) into pure Hindi words."""

# Backward and specification compatibility alias:
DevanagariNumeralExpander = NumeralAndTokenExpander
```

#### 3. `DeliveryIntentExtractor` ([`audiobook_factory/tts/guard/delivery_extractor.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/guard/delivery_extractor.py))
*Extracts bracketed stage directions (`[whispering]`, `(angry)`, `[sighs]`) and acting tags from input prose, populating strongly-typed `DeliveryIntent` while purging brackets from spoken audio.*

```python
class DeliveryIntentExtractor:
    @classmethod
    def extract_delivery_intent(
        cls,
        text: str,
        base_intent: Optional[DeliveryIntent] = None,
    ) -> Tuple[str, DeliveryIntent]:
        """
        Parses and strips stage cues:
        - Detects emotions: anger, whisper, fear, sadness, laughter, sarcasm, cold.
        - Detects proximity: intimate, close_mic, distant.
        - Detects intensity: low, medium, high, explosive.
        Returns: (cleaned_prose_without_brackets, delivery_intent)
        """
```

---

### 9.4 4-Tier Semantic Prose Chunker ([`audiobook_factory.tts.chunker`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/chunker.py))

*Splits long-form literary text into natural acoustic chunks using a strict 4-tier hierarchy that permanently eliminates mid-word splitting and autoregressive rate drift.*

```python
class ChunkHierarchyLevel(str, Enum):
    SCENE = "scene"          # Level 1: Scene breaks (---, ***, # headers)
    PARAGRAPH = "paragraph"  # Level 2: Paragraph breaks (\n\n) -> Target 80-160 words
    SENTENCE = "sentence"    # Level 3: Sentence boundaries (।, ., ?, !) -> Target 30-75 words
    CLAUSE = "clause"        # Level 4: Clause boundaries (,, —, ;) -> Emergency fallback (>45w)

class SemanticChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_uid: str
    text: str
    spoken_text: str
    level: ChunkHierarchyLevel
    word_count: int
    char_count: int
    suggested_pause_before_ms: int = 0
    suggested_pause_after_ms: int = 350
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SemanticProseChunker:
    SCENE_DELIMITERS: re.Pattern
    PARAGRAPH_DELIMITERS: re.Pattern
    SENTENCE_DELIMITERS: re.Pattern
    CLAUSE_DELIMITERS: re.Pattern

    @classmethod
    def chunk_prose(
        cls,
        text: str,
        target_words: int = 120,
        max_words: int = 180,
        min_words: int = 40,
    ) -> List[SemanticChunk]:
        """
        Recursively decomposes text down the hierarchy:
        Scene -> Paragraph -> Sentence -> Clause.
        Enforces:
        - Mid-word slicing is strictly prohibited.
        - Devanagari danda (।) and double danda (॥) treated as hard sentence stops.
        - Contextual suggested pauses (scene: 800ms, paragraph: 500ms, sentence: 350ms, clause: 200ms).
        """
```

---

### 9.5 Pluggable Model Adapters & Dynamic Registry ([`audiobook_factory.tts.providers`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/__init__.py))

#### 1. `BaseTTSModelAdapter` ([`audiobook_factory/tts/providers/base.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/base.py))
*Abstract base interface for all TTS provider engines.*

```python
class BaseTTSModelAdapter(ABC):
    def __init__(self, model_name: str, sample_rate: int = 24000): ...

    @abstractmethod
    def synthesize_chunk(
        self,
        request: CanonicalTTSRequest,
    ) -> SynthesizedAudioChunk:
        """Synthesizes an immutable request into a raw SynthesizedAudioChunk."""
```

#### 2. `GeminiTTSAdapter` ([`audiobook_factory/tts/providers/gemini_adapter.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/gemini_adapter.py))
*Production Google Gemini Flash Cloud TTS adapter.*
- **Control Plane Delegation**: `synthesize_chunk()` delegates directly to [`execute_tts_synthesize()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py#L60), enforcing centralized routing through [`ModelGateway`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py#L61) and eliminating rogue unmetered HTTP requests.
- **Secret Hygiene & Header Stealth**: Endpoint template stripped of plaintext key query parameters (`https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`). All authentication exclusively transmits via official stealth `X-goog-api-key` headers generated by `get_stealth_sdk_headers()`.
- **ACID Key Leasing**: Acquires exclusive Concurrency=1 leases for `workload_type="tts"` via [`KeyLeaseManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py#L130), strictly respecting 10 RPD per-key ceilings on `gemini-3.8-flash-tts`.
- **7 Iron Shields Anti-Ban Protection**: Protected by [`AntiBanGuard`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/anti_ban_guard.py#L24) (11.0 RPM token-bucket rate limiter, 18s–32s key-switch cooldown, session affinity, emergency global tripwire).
- **5-Category `BLOCK_NONE` Permissive Safety**: Permanent `BLOCK_NONE` thresholds across harassment, hate speech, sexually explicit, dangerous content, and civic integrity.
- **Linear PCM Extraction**: Unpacks 24kHz 16-bit linear PCM and calculates exact duration via [`extract_pcm_and_duration_from_audio()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py#L33).
- **Style Descriptor NLP**: Transforms structured `DeliveryIntent` into `speechMetadata.style` directives.

```python
class GeminiTTSAdapter(BaseTTSModelAdapter):
    def __init__(self, model_name: str = "gemini-3.8-flash", config: Optional[Dict[str, Any]] = None): ...
    def synthesize_chunk(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk: ...
    async def synthesize_chunk_async(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk: ...
```

#### 3. `QwenTTSAdapter` ([`audiobook_factory/tts/providers/qwen_adapter.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/qwen_adapter.py))
*Local Qwen3-TTS / CosyVoice wafer-scale inference adapter.*
- Communicates via local REST / gRPC endpoint (`http://localhost:9880/tts`).
- Protected by `HardwareVRAMGuard` semaphore locking to prevent GPU VRAM exhaustion.
- Includes synthetic sine/harmonic fallback when local server is offline.

```python
class QwenTTSAdapter(BaseTTSModelAdapter):
    def __init__(self, model_name: str = "qwen3-tts", sample_rate: int = 24000, endpoint_url: str = ...): ...
    def synthesize_chunk(self, request: CanonicalTTSRequest) -> SynthesizedAudioChunk: ...
```

#### 4. `ModelAdapterRegistry` ([`audiobook_factory/tts/providers/registry.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/providers/registry.py))
*Thread-safe singleton registry mapping model identifier strings to instantiated adapters.*

```python
class ModelAdapterRegistry:
    def register(self, model_name: str, adapter: BaseTTSModelAdapter) -> None: ...
    def get(self, model_name: str) -> BaseTTSModelAdapter: ...
    def list_models(self) -> List[str]: ...

def get_adapter_registry() -> ModelAdapterRegistry:
    """Retrieves the global singleton ModelAdapterRegistry."""
```

---

### 9.6 Two-Tier Audio Quality Gate ([`audiobook_factory.tts.quality_gate`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/quality_gate.py))

*Separates generation success from generation correctness, auditing every audio chunk before cache acceptance.*

```python
class TwoTierAudioQualityGate:
    # Tier 1 Acoustic Thresholds
    MIN_PEAK_AMPLITUDE: int = 1500           # Minimum signal level (avoids dead air)
    MAX_CLIPPED_AMPLITUDE: int = 32760       # 16-bit signed PCM max is 32767
    MIN_RMS_DBFS: float = -52.0              # Speech silence floor (-52 dBFS)
    MAX_RMS_DBFS: float = -6.0               # Maximum RMS loudness ceiling
    MAX_DC_BIAS: float = 0.05                # Max allowable DC offset fraction
    MAX_CONSECUTIVE_CLIPS: int = 5           # Maximum consecutive clipped samples
    MAX_INTERNAL_DEAD_AIR_SEC: float = 2.5   # Contiguous internal silence ceiling
    MIN_DURATION_PER_WORD_SEC: float = 0.12  # Below 120ms/word indicates skipped text
    MAX_DURATION_PER_WORD_SEC: float = 0.95  # Above 950ms/word indicates runaway stutter

    @classmethod
    def audit_chunk(
        cls,
        request: CanonicalTTSRequest,
        chunk: SynthesizedAudioChunk,
        skip_tier2: bool = False,
    ) -> AudioValidationResult:
        """
        Executes:
        - Tier 1: Mathematical Waveform Probe (<5ms, zero network cost).
          Audits peak amplitude, RMS loudness, DC bias, consecutive clips, and internal dead air.
        - Tier 2: Phonetic & Token Integrity Probe.
          Audits duration-per-word ratio ([0.12, 0.95] sec/word) and checks for token omission or runaway loops.
        Returns: AudioValidationResult
        """
```

---

### 9.7 4D Formants & TakeBank Auditioning ([`audiobook_factory.tts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/__init__.py))

#### 1. `FormantSculptor` ([`audiobook_factory/tts/formant_sculptor.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/formant_sculptor.py))
*Applies 4D parametric EQ formant curves directly on 16-bit linear PCM bytes using pure-Python 2nd-order biquad peaking filters with headroom pre-attenuation and soft tanh limiting.*

```python
class FormantProfile(str, Enum):
    WARM_BARITONE = "warm_baritone"        # +3dB @ 180Hz (chest), -1.8dB @ 3.2kHz
    CRISP_TENOR = "crisp_tenor"            # -2dB @ 160Hz (de-mud), +2.5dB @ 3.0kHz
    BRIGHT_FEMALE = "bright_female"        # -2.5dB @ 120Hz, +3dB @ 3.5kHz, +1.5dB @ 8kHz
    DEEP_RESONANT = "deep_resonant"        # +4dB @ 100Hz (rumble), +2.5dB @ 220Hz, -2dB @ 4kHz
    ELDERLY_TEXTURED = "elderly_textured"  # +2.8dB @ 750Hz (pharyngeal), -3dB @ 5kHz
    CHILD_ANIME = "child_anime"            # -2dB @ 250Hz, +3.5dB @ 4.2kHz, +2dB @ 9kHz
    NEUTRAL = "neutral"

class FormantSculptor:
    EQ_PRESETS: Dict[FormantProfile, List[Tuple[float, float, float]]]

    @classmethod
    def apply_formant_eq(
        cls,
        pcm_bytes: bytes,
        profile_or_preset: Union[str, FormantProfile, List[Tuple[float, float, float]]],
        sample_rate: int = 24000,
    ) -> bytes:
        """
        Processes 16-bit PCM bytes:
        1. Pre-attenuates signal by headroom factor: 10^(-max_gain_db / 20).
        2. Applies cascaded 2nd-order peaking EQ biquad filters.
        3. Limits peaks through soft tanh knee to strictly prevent digital clipping (<= 32,760).
        """
```

#### 2. `TakeBankManager` ([`audiobook_factory/tts/take_bank_manager.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/take_bank_manager.py))
*Coordinates multi-take candidate synthesis, audition scoring, and selection for dramatic screenplay turns.*

```python
class CandidateTake:
    def __init__(
        self,
        take_id: str,
        variant_type: str,
        chunk: SynthesizedAudioChunk,
        validation: Optional[AudioValidationResult] = None,
        score: float = 0.0,
        is_selected: bool = False,
    ): ...

class TakeBankManager:
    # Priority Take Allocation
    # 'standard'  -> 1 take  (standard delivery)
    # 'focused'   -> 2 takes (standard + restraint)
    # 'high'      -> 3 takes (standard + restraint + vulnerable)
    # 'climactic' -> 4 takes (standard + restraint + vulnerable + exposed)

    def __init__(self, orchestrator: Optional[TTSCoreOrchestrator] = None): ...

    def select_best_take(
        self,
        request: CanonicalTTSRequest,
        priority: str = "standard",
        model: str = "gemini-3.8-flash",
    ) -> Tuple[SynthesizedAudioChunk, AudioValidationResult, List[CandidateTake]]:
        """
        Synthesizes candidate variants, audits each through TwoTierAudioQualityGate,
        scores takes based on acoustic compliance and RMS stability, and selects the winner.
        Returns: (winning_chunk, validation_result, all_candidate_takes)
        """
```

---

### 9.8 Dialogue Editorial Layer & Net-Silence DSP ([`audiobook_factory.tts.dsp`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/dsp/__init__.py))

#### 1. `ZeroCrossingAligner` ([`audiobook_factory/tts/dsp/editorial.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/dsp/editorial.py))
*Snaps chunk boundaries to exact zero-crossing samples ($f(t) = 0, f'(t) \ge 0$) at the -52 dBFS speech floor to eliminate digital switching clicks.*

```python
class ZeroCrossingAligner:
    @classmethod
    def find_nearest_zero_crossing(
        cls,
        samples: List[int],
        start_idx: int,
        search_window: int = 240,  # 10ms search window at 24kHz
        forward: bool = True,
    ) -> int: ...
```

#### 2. `HannFadeProcessor` ([`audiobook_factory/tts/dsp/editorial.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/dsp/editorial.py))
*Applies raised-cosine Hann window micro-fades and TPDF dither to eliminate endpoint transients.*

```python
class HannFadeProcessor:
    FADE_IN_MS: float = 12.0   # w_in(t)  = 0.5 * (1 - cos(pi * t / T_in))
    FADE_OUT_MS: float = 18.0  # w_out(t) = 0.5 * (1 + cos(pi * t / T_out))

    @classmethod
    def apply_hann_micro_fades(
        cls,
        pcm_bytes: bytes,
        sample_rate: int = 24000,
        apply_tpdf_dither: bool = True,
    ) -> bytes: ...
```

#### 3. `NetSilenceProcessor` ([`audiobook_factory/tts/dsp/editorial.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/dsp/editorial.py))
*Dynamically subtracts acoustic room-tone decay tails to prevent double-pause stutter gaps.*

$$\text{Injected Silence} = \max(20\text{ms}, \text{Target Pause} - (\text{Tail Decay}_A + \text{Head Margin}_B))$$

```python
class NetSilenceProcessor:
    SILENCE_FLOOR_AMPLITUDE: int = 150  # ~ -46 dBFS silence floor

    @classmethod
    def measure_tail_decay_ms(cls, pcm_bytes: bytes, sample_rate: int = 24000) -> int: ...

    @classmethod
    def measure_head_margin_ms(cls, pcm_bytes: bytes, sample_rate: int = 24000) -> int: ...

    @classmethod
    def calculate_net_silence_ms(
        cls,
        target_pause_ms: int,
        tail_decay_ms: int,
        head_margin_ms: int,
        min_injected_ms: int = 20,
    ) -> int: ...

    @classmethod
    def generate_silence_pcm(cls, duration_ms: int, sample_rate: int = 24000) -> bytes: ...
```

#### 4. `EditorialDSPEngine` ([`audiobook_factory/tts/dsp/editorial.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/dsp/editorial.py))
*Unified editorial pipeline combining zero-crossing snapping, Hann micro-fades, and net-silence timeline concatenation.*

```python
class EditorialDSPEngine:
    @classmethod
    def process_and_stitch(
        cls,
        chunks_pcm: List[bytes],
        target_pauses_ms: List[int],
        sample_rate: int = 24000,
    ) -> Tuple[bytes, float]:
        """
        Stitches a sequence of PCM audio chunks into a seamless dialogue stem:
        1. Snaps endpoints via ZeroCrossingAligner.
        2. Applies 12ms/18ms Hann micro-fades via HannFadeProcessor with TPDF dither.
        3. Injects dynamically calculated net silence via NetSilenceProcessor.
        Returns: (stitched_pcm_bytes, total_duration_sec)
        """
```

---

### 9.9 Unified TTS Core Orchestrator ([`audiobook_factory.tts.core_orchestrator`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/core_orchestrator.py))

*Central execution engine connecting input guards, model adapters, and quality gates.*

```python
class TTSCoreOrchestrator:
    def __init__(
        self,
        registry: Optional[ModelAdapterRegistry] = None,
        rate_limiter: Optional[TokenBucketRateLimiter] = None,
        max_workers: int = 3,
    ): ...

    def synthesize(
        self,
        request_or_text: Union[str, CanonicalTTSRequest],
        voice_id: str = "Puck",
        model: str = "gemini-3.8-flash",
        speaker: str = "Narrator",
        pipeline_mode: TTSPipelineMode = TTSPipelineMode.GENERIC,
        validate_audio: bool = True,
        **guard_kwargs: Any,
    ) -> Tuple[SynthesizedAudioChunk, Optional[AudioValidationResult]]:
        """
        Executes single chunk synthesis:
        1. Normalizes input via UniversalInputGuard if given raw text.
        2. Resolves model adapter from ModelAdapterRegistry.
        3. Paces requests through TokenBucketRateLimiter with jitter.
        4. Invokes adapter.synthesize_chunk().
        5. Validates audio through TwoTierAudioQualityGate.
        Returns: (synthesized_chunk, validation_result)
        """

    def synthesize_batch(
        self,
        requests: List[CanonicalTTSRequest],
        model: str = "gemini-3.8-flash",
        validate_audio: bool = True,
        max_workers: Optional[int] = None,
    ) -> List[Tuple[CanonicalTTSRequest, SynthesizedAudioChunk, Optional[AudioValidationResult]]]:
        """
        Executes concurrent batch synthesis across worker threads, returning
        in original request order.
        """
```

---

### 9.10 TTS ModelGateway Control Plane Bridge ([`audiobook_factory.tts.gateway_bridge`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py))

*Authoritative control-plane bridge for the Option C Studio TTS Platform Core (`GenericTTSClient`, `LongFormTTSClient`, `MultiCastStudioClient`, `GeminiTTSAdapter`, and `ModelAdapterRegistry`).*

#### 1. Core Functions

##### [`execute_tts_synthesize()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py#L60)

```python
def execute_tts_synthesize(
    text: str,
    voice_name: str = "Puck",
    model: Optional[str] = None,
    delivery_intent: Optional[Any] = None,
    speaker: Optional[str] = None,
    temperature: float = 0.35,
    session_id: Optional[str] = None,
    user_id: str = "tts_worker",
    max_retries: int = 3,
    timeout_sec: float = 45.0,
    style_desc: Optional[str] = None,
    fast_mode: bool = False,
    **kwargs: Any,
) -> SpeechResult:
    """
    Executes a Room 4 Speech Synthesis request strictly through ModelGateway.
    Returns SpeechResult containing decoded audio bytes and operational metadata.
    """
```

**Parameters & Behaviors:**
- `text` (*str*): The phonetically expanded, sanitized Devanagari/Hindustani spoken text to synthesize.
- `voice_name` (*str*): Target neural voice identifier (e.g. `'Puck'`, `'Aoede'`, `'Charon'`, `'Fenrir'`).
- `model` (*Optional[str]*): TTS model identifier (defaults to `'gemini-3.8-flash-tts'`).
- `speaker` (*Optional[str]*): Character speaker name used for temperature clamping logic.
- `temperature` (*float*): Delivery temperature. Clamped according to character role:
  - **Narrator**: Strictly locked to `0.32` (`clamped_temp = 0.32`) to enforce calm, transparent, measured delivery.
  - **Character Dialogue**: Clamped between `0.30` and `0.52` (`max(0.30, min(temperature, 0.52))`) to prevent histrionic screeching.
- `style_desc` (*Optional[str]*): Natural language acting directive packaged into `part_dict["speechMetadata"] = {"style": style_desc}`.
- `session_id` (*Optional[str]*): Session/scene identifier passed to `AntiBanGuard` for sticky key affinity across 8–15 dialogue turns.
- `user_id` (*str*): Workload identity for per-user quota isolation (`CallerIdentity`).
- `fast_mode` (*bool*): Bypasses inter-request sleep delays in test environments or when `PYTEST_CURRENT_TEST` is set.
- **Return Value**: Returns a [`SpeechResult`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/adapters/base.py#L30) with raw audio bytes, MIME type, sample rate, duration, and metadata.
- **Offline Mock Fallback**: If running in an offline mock environment (`MOCK_OFFLINE=1` or `GEMINI_API_KEY=mock*`), generates deterministic 24kHz 16-bit linear PCM WAV fixtures with `metadata={"mock_mode": True, "attempt": 1}`.

##### [`extract_pcm_and_duration_from_audio()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py#L33)

```python
def extract_pcm_and_duration_from_audio(
    audio_bytes: bytes,
    mime_type: str = "audio/wav",
    default_sample_rate: int = 24000,
) -> Tuple[bytes, float, int]:
    """
    Safely extracts 16-bit linear PCM bytes, duration in seconds, and sample rate
    from a WAV container (RIFF) or raw PCM byte stream.
    Returns: (pcm_bytes, dur_sec, sample_rate)
    """
```

**Parameters & Behaviors:**
- `audio_bytes` (*bytes*): Audio payload received from `SpeechResult` or provider response.
- `mime_type` (*str*): MIME type indicator (`"audio/wav"`, `"audio/pcm"`, etc.).
- `default_sample_rate` (*int*): Fallback sampling rate if container header is absent (default: 24,000 Hz).
- **RIFF Parsing**: Safely unpacks RIFF WAV headers via Python `wave.open`, extracting pure frames, frame rate, and calculating duration ($T = N_{\text{frames}} / f_s$).
- **Raw PCM Fallback**: If header is absent or corrupt, falls back to 16-bit mono PCM calculation ($T = \text{len} / (2 \cdot f_s)$).

##### [`execute_tts_to_file()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py#L146)

```python
def execute_tts_to_file(
    text: str,
    output_file: Union[str, Path],
    voice: str = "Puck",
    model: Optional[str] = None,
    emotion: str = "neutral",
    acting: Any = None,
    intensity: str = "medium",
    memory_vocal_constraint: Optional[str] = None,
    performance_direction: Optional[Any] = None,
    variant_type: str = "standard",
    rate_limiter: Optional[Any] = None,
    voice_dna: Optional[Any] = None,
    scene_vector: Optional[Any] = None,
    speaker: Optional[str] = None,
    temperature: Optional[float] = None,
    session_id: Optional[str] = None,
    user_id: str = "tts_worker",
    max_retries: int = 3,
    timeout_sec: float = 60.0,
    **kwargs: Any,
) -> Tuple[Path, float]:
    """
    Synthesizes single-utterance speech strictly routed through ModelGateway
    and writes verified audio into output_file. Returns (output_path, duration_sec).
    """
```

**Parameters & Behaviors:**
- Integrates `GeminiTTSPerformanceAdapter` and `resolve_speech_metadata_style` to resolve acting intent into structured style prompts.
- Clamps temperature according to speaker identity (locked 0.32 for Narrator, 0.30–0.52 for Character Dialogue).
- Synthesizes audio via `execute_tts_synthesize()` through `ModelGateway.synthesize_speech()`.
- Atomically writes verified 24kHz 16-bit linear PCM WAV container to disk via `_atomic_replace`.

##### [`execute_multispeaker_batch_to_file()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/gateway_bridge.py#L254)

```python
def execute_multispeaker_batch_to_file(
    batch: Any,
    output_file: Union[str, Path],
    voice_map: Dict[str, str],
    model: Optional[str] = None,
    rate_limiter: Optional[Any] = None,
    temperature: Optional[float] = None,
    session_id: Optional[str] = None,
    user_id: str = "tts_worker",
    max_retries: int = 3,
    timeout_sec: float = 90.0,
    **kwargs: Any,
) -> Tuple[Path, float]:
    """
    Synthesizes a multi-speaker duo batch strictly routed through ModelGateway
    with multiSpeakerVoiceConfig and writes verified audio into output_file.
    Returns (output_path, duration_sec).
    """
```

**Parameters & Behaviors:**
- Validates duo batch constraint (strictly 2 speakers).
- Constructs Gemini `multiSpeakerVoiceConfig` payload mapping characters to assigned voices.
- Normalizes Devanagari numerals and extracts stage directions across all dialogue segments.
- Synthesizes multi-speaker audio via single-API batch dispatch routed through `ModelGateway`.
- Atomically persists verified multi-speaker WAV container to disk.

#### 2. Control Plane Architectural Guarantees

| Guarantee | Enforcement Mechanism | Architectural Benefit |
| :--- | :--- | :--- |
| **Strict ModelGateway Routing** | 100% of Room 4 synthesis traffic routes through `ModelGateway.synthesize_speech()`. | Eliminates unmetered, rogue `urllib` requests and prevents untracked API costs. |
| **Atomic Key Leasing** | Leases Concurrency=1 mutual exclusion handles from [`KeyLeaseManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py#L130) for `workload_type="tts"`. | Prevents concurrent duplicate leases and enforces 10 RPD daily quota ceilings on `gemini-3.8-flash-tts`. |
| **The 7 Iron Shields AntiBanGuard** | Enforces 11.0 RPM token-bucket rate limiter, 18s–32s key-switch cooldown, scene session affinity, and emergency tripwire. | Protects the 120+ key pool against edge mass-bans and suspicious key-hopping patterns. |
| **Permissive Creative Fiction Framing** | Automatically injects `BLOCK_NONE` thresholds across all 5 harm categories. | Eliminates false-positive censorship of dramatic dialogue, rustic idioms, and gritty combat prose. |
| **Legacy Dispatcher Unification** | Bridges `TTSDispatcher` directly to `ModelGateway` while honoring test monkeypatches. | Zero breaking changes for existing test fixtures with 100% control plane enforcement in production. |
| **Fail-Closed Security** | Raises normalized exceptions when keys or models are exhausted; fails closed if gateway is unavailable. | Prevents silent corruption of audio stems and preserves quota budgets. |

#### 3. Universal Re-exports & Verification

The gateway bridge functions are universally re-exported across the codebase:
- [`audiobook_factory.tts`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts/__init__.py): Primary public export in `__all__` (`execute_tts_synthesize`, `execute_tts_to_file`, `execute_multispeaker_batch_to_file`, `extract_pcm_and_duration_from_audio`).
- [`audiobook_factory.tts_dispatcher`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/tts_dispatcher.py): Backward-compatible legacy re-export in `__all__`.
- [`audiobook_factory`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/__init__.py): Lazy-loaded in `_LAZY_IMPORTS`.
- **Test Verification**: 100% verified across the full repository test suite (**1,126 / 1,126 passed tests, 100% green**).

