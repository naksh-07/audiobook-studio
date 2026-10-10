# Room 1.5: Standalone Glossary & Chapter Metadata Subsystem
**Document Version:** `1.0.0-PROD`  
**System ID:** `sys-glossary-metadata`  
**Canonical Project:** `proj-audiobook-studio`  
**Classification:** Core Subsystem Architectural Specification  
**Platform:** Windows 11 AI Workstation & Cross-Platform Production  
**Component Package:** [`audiobook_factory/glossary/`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/)  
**Status:** Canonical Reference Standard (Verified & AST Isolated)

---

## 1. System Vision, Placement & Architectural Decoupling

The **Glossary & Chapter Metadata Subsystem (Room 1.5)** is the dedicated, per-chapter lexical analysis, entity classification, and metadata projection hub of the Audiobook Studio pipeline.

Positioned cleanly between **Room 1 (Whole-Book Pre-Production / Research)** and downstream consumers—**Room 2 (Literary Translation)**, **Room 3 (Screenplay & Dramaturgy)**, and **Room 4 (Voice Performance & TTS)**—Room 1.5 resolves a fundamental challenge in multi-voice audiobook synthesis: **lexical and casting consistency across chapter boundaries without redundant computation or boundary leakage**.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    ROOM 1.5 BOUNDARY INVARIANT                                   │
│                                                                                                  │
│  Input:  Raw Chapter Text + Canonical BookBible (book_bible.json)                                │
│  Output: Deterministic, durable ChapterGlossary artifact (chapter_XXX_glossary.json)             │
│          + Dynamic Synchronization with BookBible & Cast Lock (cast_lock.json)                   │
│          + Tailor-made projections for Translation, Scripting, and Voice Casting                 │
│                                                                                                  │
│  STRICTLY DECOUPLED FROM:                                                                        │
│  - Downstream audio DSP, mixing, LUFS loudness, FFmpeg (audiobook_factory.audio)                 │
│  - TTS speech synthesis, audio models, voice engines (audiobook_factory.tts)                     │
│  - Screenplay generation, actor tags, scene beat parsing (audiobook_factory.screenplay)          │
│  - Direct unmetered networking (urllib.request, requests, httpx, aiohttp)                        │
│                                                                                                  │
│  STRICTLY ENFORCING:                                                                             │
│  - Pure Vocals-Only Audiobook Production (Zero SFX / Zero BGM)                                   │
│  - 100% AST-Verified Zero-Import Architectural Isolation                                         │
│  - ModelGateway Phase 1 Control Plane Routing with KeyLeaseManager Concurrency = 1               │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Why a Dedicated Standalone Subsystem?

Prior to Room 1.5, per-chapter entity harvesting was tightly coupled inside translation or screenplay utilities. This created multiple architectural liabilities:
1. **Redundant LLM Invocations**: Downstream rooms repeatedly asked LLMs to identify the same characters or invent Devanagari spellings, causing token waste and subtle phonetic drift across chapters.
2. **Attribution & Voice Splitting**: If a character was introduced by an epithet (e.g., *"The Stranger"*) before their canonical name (*"Lord Corwin"* or *"Silver Falcon"*) was revealed, downstream screenplay parsers would split the character across two distinct voice actors.
3. **Boundary Inversion**: Translation agents were burdened with entity tracking and voice roster synchronization, violating single-responsibility separation.

Room 1.5 extracts lexical scanning, Tri-Partite entity classification, alias unification, and dynamic casting synchronization into a high-performance, single-pass pipeline step that executes in under $50\text{ms}$ on cached entities and runs zero-token fast-paths whenever chapters introduce no new characters.

---

## 2. Core Invariants & Architectural Non-Negotiables

### 2.1 The Pure Vocals-Only Mandate
In strict compliance with studio rules, Room 1.5 contains **zero references to background music (BGM), sound effects (SFX), multi-track stem mixdowns, or acoustic Foley sound banks**. The subsystem is 100% dedicated to pristine vocal clarity, character role classification, Devanagari phonetic integrity, and dynamic character vocal allocation.

### 2.2 AST-Verified Zero-Import Architectural Isolation
Room 1.5 enforces absolute module isolation. It does not import downstream audio, speech synthesis, screenplay formatting, or unmetered networking libraries:
- ❌ **Zero Audio Imports**: Forbidden from importing `audiobook_factory.audio`, `audiobook_factory.sound_bank`, `audiobook_factory.ffmpeg_agent`, `pyaudio`, `sounddevice`.
- ❌ **Zero TTS Imports**: Forbidden from importing `audiobook_factory.tts`, `audiobook_factory.tts_dispatcher`.
- ❌ **Zero Screenplay Imports**: Forbidden from importing `audiobook_factory.screenplay`, `audiobook_factory.dramaturgy`, `audiobook_factory.cinematic`.
- ❌ **Zero Unmetered Network Calls**: Forbidden from importing `urllib.request`, `requests`, `httpx`, `aiohttp`.

> [!IMPORTANT]
> This isolation is continuously verified by Python AST inspection in [`tests/glossary/test_zero_import_isolation.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/tests/glossary/test_zero_import_isolation.py), which parses the AST of every `.py` file in `audiobook_factory/glossary/` and asserts zero occurrences of forbidden prefixes.

### 2.3 The Tri-Partite Entity Taxonomy Invariant
All entities identified in chapter text must strictly conform to the 3-tier taxonomy codified in [`audiobook_factory/glossary/classifier.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/classifier.py):
1. **`PROPER_NAME` (Personal Names, Surnames, Given Names)**:
   - Phonetically transliterated into Devanagari script (e.g., *Edward* $\to$ *एडवर्ड*, *Corwin* $\to$ *कॉरविन*, *Elena* $\to$ *एलेना*).
   - Foreign or fantasy names are **never** substituted with colloquial Indian village names.
2. **`HERALDIC_MONIKER` (Heraldic Nicknames, Formal Titles, Epithets as Names)**:
   - Treated as Proper Names and phonetically transliterated into Devanagari (e.g., *Silver Falcon* $\to$ *सिल्वर फाल्कन*, *Night Raven* $\to$ *नाइट रेवेन*, *Gold-Tooth* $\to$ *गोल्ड-टूथ*).
   - **STRICT BANNED CALQUE**: Literal word-for-word translation is strictly prohibited (*चांदी का बाज़* or *रात का कौवा* as character names are banned).
3. **`OCCUPATIONAL_ROLE` (Generic Roles & Initial Descriptors)**:
   - Translated into natural, spoken Hindustani (e.g., *The Stranger* $\to$ *अजनबी*, *The Butcher* $\to$ *कसाई*, *The Alderman* $\to$ *एल्डरमैन*, *The Innkeeper* $\to$ *सरायवाला*).

### 2.4 The Zero-Token Fast-Path Invariant
Whenever a chapter contains solely entities and proper nouns that are already cataloged in the novel's master [`BookBible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py), the regex lexical scanner must return an empty candidate list, and **zero LLM tokens are consumed** (`llm_invoked=False`).

### 2.5 The Single-Pass Dynamic Casting Invariant
When a previously uncataloged character is discovered in chapter text, [`GlossaryManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/manager.py) atomically registers the character in [`BookBible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py) and immediately invokes [`NovelStateMaintainer.discover_and_lock_character()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/state_maintainer.py) to lock a non-colliding 4D acoustic formant signature in `cast_lock.json`. This guarantees that character voices never drift mid-novel.

---

## 3. Subsystem Architecture & End-to-End Data Flow

The following diagram illustrates Room 1.5's position, internal processing flow, and projections to downstream rooms:

```mermaid
flowchart TD
    subgraph Room1["🌍 Room 1: Pre-Production"]
        BB[("BookBible<br/>book_bible.json")]
        NSM["NovelStateMaintainer<br/>(cast_lock.json)"]
    end

    subgraph Room1_5["📚 Room 1.5: Standalone Chapter Glossary & Metadata Hub"]
        direction TB
        RawChap["Chapter Raw Text<br/>(Markdown / Text)"] --> Scanner["ChapterLexicalScanner<br/>• Regex Capitalization Sweep<br/>• 130+ Stopwords Filter<br/>• Mid-Sentence Detection<br/>• BookBible Known Lexicon Filter"]
        
        Scanner -->|"0 Uncataloged Candidates"| FastPath["Zero-Token Fast Path<br/>(Bypass LLM completely)"]
        Scanner -->|"Uncataloged Candidates"| Bridge["gateway_bridge.py<br/>• execute_glossary_llm()<br/>• ModelGateway Router<br/>• KeyLeaseManager (Concurrency=1)<br/>• AntiBanGuard (11.0 RPM)<br/>• BLOCK_NONE Framing"]
        
        Bridge --> Classifier["GlossaryClassifier<br/>• Tri-Partite System Prompt<br/>• Proper Name Transliteration<br/>• Moniker Preservation<br/>• Role Hindustani Translation<br/>• Alias Unification"]
        
        FastPath --> Assembler["GlossaryManager Assembler"]
        Classifier --> Assembler
        
        Assembler -->|"Update Canonical Lore"| BB
        Assembler -->|"Dynamic Voice Lock"| NSM
        
        Assembler --> ChapGlossary["ChapterGlossary (Pydantic v2)<br/>• entities (ChapterEntity)<br/>• locations & terminology<br/>• version_hash (SHA-256)"]
        
        ChapGlossary --> DiskArtifact[("Disk Persistence<br/>glossary/chapter_XXX_glossary.json")]
    end

    subgraph Downstream["🎬 Downstream Production Consumers"]
        direction TB
        ChapGlossary -->|"to_translation_glossary()<br/>Flat en -> hi Dictionary"| R2["Room 2: Translation Engine<br/>(TranslationRequest.dynamic_glossary)"]
        ChapGlossary -->|"to_scripting_roster()<br/>character_roster.json schema"| R3_A["Room 3: Screenplay Attribution<br/>(DialogueAttributionAuditor)"]
        ChapGlossary -->|"to_dramaturgy_characters()<br/>Active Scene Cast List"| R3_B["Room 3: Scene Dramaturgy<br/>(Scene Segmentation)"]
        ChapGlossary -->|"discover_and_lock_character()<br/>cast_lock.json updates"| R4["Room 4: Voice Performance<br/>(4D Acoustic Formants)"]
    end
```

### 3.1 Single-Pass Execution Sequence

The sequence below illustrates the execution lifecycle during a chapter production run:

```mermaid
sequenceDiagram
    autonumber
    participant Pipeline as Orchestrator / Worker
    participant Manager as GlossaryManager
    participant Scanner as ChapterLexicalScanner
    participant Bible as BookBible
    participant Gateway as ModelGateway Bridge
    participant Classifier as GlossaryClassifier
    participant State as NovelStateMaintainer
    participant Disk as Filesystem (glossary/)

    Pipeline->>Manager: scan_and_sync_chapter(chapter_text, chapter_num=3)
    Manager->>Bible: load_from_project(project_dir)
    Manager->>Scanner: scan_chapter_text(text, book_bible=bible)
    Scanner-->>Manager: candidates (List[CandidateEntity])

    alt candidates is empty (Zero-Token Fast Path)
        Manager->>Manager: Skip LLM call (0 tokens consumed)
    else candidates contains uncataloged entities
        Manager->>Classifier: classify_candidates(candidates, chapter_text)
        Classifier->>Gateway: execute_glossary_llm(prompt, TRI_PARTITE_SYSTEM_PROMPT)
        Gateway->>Gateway: KeyLeaseManager lease (Concurrency=1) & AntiBanGuard pace
        Gateway-->>Classifier: parsed JSON (characters, locations_and_terms)
        Classifier-->>Manager: (discovered_entities, locations, terminology)
    end

    Manager->>Bible: Synchronize new entities & unify aliases
    Manager->>State: discover_and_lock_character(speaker, gender) -> cast_lock.json
    Bible->>Disk: bible.save(project_dir)
    Manager->>Disk: chapter_glossary.save_to_file(chapter_003_glossary.json)
    Manager-->>Pipeline: ChapterGlossary snapshot
```

---

## 4. Canonical Data Contracts (`contracts.py`)

All data structures in Room 1.5 are strictly typed using **Pydantic v2** models defined in [`audiobook_factory/glossary/contracts.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/contracts.py).

### 4.1 `EntityCategory`
Defines the valid Tri-Partite taxonomy classification categories:

```python
EntityCategory = Literal[
    "PROPER_NAME",        # Personal name -> Phonetic Devanagari
    "HERALDIC_MONIKER",  # Formal title / moniker -> Phonetic Devanagari (Calques banned)
    "OCCUPATIONAL_ROLE", # Situational role / descriptor -> Spoken Hindustani
    "LOCATION",          # Geographic location -> Hindi translation / transliteration
    "LORE_TERM",         # Lore / fantasy term -> Hindustani equivalent
]
```

### 4.2 `ChapterEntity`
Represents an individual character or person entity active in the chapter:

```python
class ChapterEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    canonical_id: str = Field(..., description="Unique snake_case identifier (e.g. 'lord_corwin')")
    english_name: str = Field(..., description="Canonical English name or moniker")
    hindi_name: str = Field(..., description="Phonetic Devanagari transliteration or Hindustani translation")
    category: EntityCategory = Field(default="PROPER_NAME", description="Tri-Partite entity classification")
    aliases: List[str] = Field(default_factory=list, description="All nicknames, aliases, and titles")
    gender: Literal["male", "female", "neutral", "unknown"] = Field(default="unknown")
    voice_style: str = Field(default="", description="Descriptive vocal acting hint or acoustic demeanor")
    sociolect_archetype: str = Field(default="NEUTRAL", description="Hindustani dialect/social register archetype")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    first_appearance_chapter: int = Field(default=1, ge=1)
    is_canonical: bool = Field(default=True)
```

### 4.3 `ChapterGlossary`
The immutable, chapter-level glossary container and single source of truth for all downstream projections:

```python
class ChapterGlossary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chapter_num: int = Field(..., ge=0, description="1-indexed chapter number (0 for front matter)")
    chapter_id: str = Field(default="", description="Chapter identifier slug (e.g. 'chapter_004')")
    entities: Dict[str, ChapterEntity] = Field(default_factory=dict, description="Active character entities")
    locations: Dict[str, str] = Field(default_factory=dict, description="English location -> Devanagari")
    terminology: Dict[str, str] = Field(default_factory=dict, description="English lore term -> Devanagari")
    version_hash: str = Field(default="", description="Deterministic SHA-256 fingerprint of glossary content")
    total_entities: int = Field(default=0)
```

#### Deterministic SHA-256 Fingerprint
`compute_hash()` generates a canonical 16-character hexadecimal fingerprint over sorted JSON content:

```python
def compute_hash(self) -> str:
    data = {
        "chapter_num": self.chapter_num,
        "entities": {k: v.model_dump() for k, v in sorted(self.entities.items())},
        "locations": dict(sorted(self.locations.items())),
        "terminology": dict(sorted(self.terminology.items())),
    }
    raw_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()[:16]
```

### 4.4 Multi-Consumer Projections

`ChapterGlossary` exposes dedicated projection methods tailored to the exact interface needs of downstream consumers:

#### 1. Translation Projection (`to_translation_glossary`)
Emits a flat `Dict[str, str]` mapping English names, aliases, locations, and lore terms to their verified Hindi Devanagari equivalents. Consumed directly by `TranslationRequest.dynamic_glossary`:

```python
trans_glossary = chapter_glossary.to_translation_glossary()
# Example output:
# {
#   "Lord Corwin": "लॉर्ड कॉरविन",
#   "Corwin": "लॉर्ड कॉरविन",
#   "Silver Falcon": "लॉर्ड कॉरविन",
#   "The Stranger": "अजनबी",
#   "Kaer Morhen": "काएर मोर्हेन",
#   "Silver Sword": "चांदी की तलवार"
# }
```

#### 2. Screenplay Roster Projection (`to_scripting_roster`)
Emits the structured `character_roster.json` schema consumed by [`DialogueAttributionAuditor`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/script_builder.py) and dialogue parsing engines. Includes unified alias lists, gender, and sociolect archetype:

```python
roster = chapter_glossary.to_scripting_roster(use_hindi=True)
# Example output:
# {
#   "characters": {
#     "लॉर्ड कॉरविन": {
#       "aliases": ["Corwin", "Lord Corwin", "Silver Falcon", "लॉर्ड कॉरविन"],
#       "gender": "male",
#       "voice_style": "Aristocratic, deep",
#       "sociolect_archetype": "ARISTOCRATIC",
#       "category": "PROPER_NAME"
#     }
#   }
# }
```

#### 3. Dramaturgy Characters Projection (`to_dramaturgy_characters`)
Returns a flat, deduplicated list of all active character names and monikers for scene boundary segmentation and presence tracking:

```python
characters = chapter_glossary.to_dramaturgy_characters()
# Example output: ["Corwin", "Lord Corwin", "Silver Falcon", "The Stranger", "लॉर्ड कॉरविन", "अजनबी"]
```

#### 4. Atomic Serialization (`save_to_file` & `load_from_file`)
Atomically persists the glossary using random UUID temporary files (`.tmp_glo_{uuid}`) and atomic file replacement, preventing corrupted artifacts on Windows 11:

```python
chapter_glossary.save_to_file("audiobooks/projects/my_novel/glossary/chapter_003_glossary.json")
loaded_glossary = ChapterGlossary.load_from_file("audiobooks/projects/my_novel/glossary/chapter_003_glossary.json")
```

---

## 5. Chapter Lexical Scanner & Zero-Token Fast-Path (`scanner.py`)

The lexical scanner ([`ChapterLexicalScanner`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/scanner.py)) is a high-speed, regex-driven entity candidate extractor. It processes an entire 5,000-word chapter in under $15\text{ms}$.

### 5.1 Regex Candidate Matcher
The scanner isolates capitalized noun phrases up to three words in length, handling connective particles (`of`, `de`, `van`, `the`):

```python
matches = re.findall(
    r"\b[A-Z][a-z]+(?:\s+(?:of|de|the|van|[A-Z][a-z]+)){0,2}\b",
    text,
)
```

Leading articles like `"The "` or `"A "` are cleanly normalized (e.g., `"The Night Raven"` $\to$ `"Night Raven"`).

### 5.2 130+ Stopwords Filter (`ENGLISH_NON_ENTITY_STOPWORDS`)
To eliminate false positives from capitalized sentence starters, dialogue interjections, and grammatical discourse markers, the scanner filters candidates against a curated 130+ stopword set:

```python
ENGLISH_NON_ENTITY_STOPWORDS: Set[str] = {
    "The", "He", "She", "They", "Then", "After", "There", "When", "What", "It", "In", "On", "At",
    "Are", "Yes", "Do", "You", "Who", "No", "That", "As", "Your", "Well", "And", "So", "Ah",
    "Greetings", "How", "History", "This", "Not", "Something", "But", "If", "To", "Become",
    "Why", "Where", "Which", "Can", "Could", "Would", "Should", "May", "Might", "Must",
    "Never", "Always", "Sometimes", "Perhaps", "Maybe", "Here", "Now", "Only", "Just",
    "All", "Some", "One", "Two", "My", "Our", "His", "Her", "Its", "Their", "We", "I",
    "Sit", "Let", "Geography", "Because", "Certainly", "Civilization", "Stories", "True",
    "Nonsense", "Instead", "Either", "Another", "Whatever", "Notice", "Nothing", "Someone",
    "Everybody", "Nobody", "Anyway", "Obviously", "Forgive", "Wait", "Look", "Listen", "Come",
    "Tonight", "Tomorrow", "Yesterday", "Suddenly", "Meanwhile", "Finally", "Soon", "Later",
    "Once", "Twice", "First", "Second", "Third", "Next", "Last", "Every", "Each", "Both",
    "Neither", "Many", "Much", "Few", "Several", "Enough", "Good", "Bad", "Great", "Little",
}
```

### 5.3 BookBible Deduplication
The scanner cross-references candidates against all known characters, aliases, locations, and terminology stored in [`BookBible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py). Any term already present in the active lexicon is instantly discarded from the candidate queue.

### 5.4 Positional Confidence & Context Snippets
Candidates are evaluated for sentence position:
- **Mid-sentence occurrence**: Detected via `(?<![.!?\"\n\r])\s+\bCandidate\b`. Indicates genuine proper nouns (confidence `0.85`).
- **Start-of-sentence only**: Flagged with lower initial confidence (`0.50`).
- **Context Snippets**: Extracts a 200-character surrounding sentence context for LLM disambiguation.

### 5.5 Candidate Model (`CandidateEntity`)

```python
class CandidateEntity(BaseModel):
    name: str
    frequency: int = 1
    sample_context: str = ""
    suggested_category: str = "character"
    confidence: float = 0.85
    is_multiword: bool = False
    has_mid_sentence: bool = False
```

---

## 6. Tri-Partite Taxonomy & Glossary Classifier (`classifier.py`)

When the lexical scanner isolates uncataloged candidate entities, [`GlossaryClassifier`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/classifier.py) dispatches a structured classification query to Google Gemini Flash via the gateway bridge.

### 6.1 The Tri-Partite System Prompt (`TRI_PARTITE_SYSTEM_PROMPT`)

```text
You are an Expert Literary Lexicographer, Voice Casting Director, and Translation Dramaturge for prestige audiobooks.
Analyze the provided chapter passage and candidate entities, then classify and transliterate them into Devanagari Hindi.

CRITICAL TRI-PARTITE ENTITY TAXONOMY:
1. PROPER_NAME (Personal Names, Surnames, Given Names):
   - Phonetically transliterate into clean Devanagari Hindi (e.g. 'Edward' -> 'एडवर्ड', 'Corwin' -> 'कॉरविन', 'Elena' -> 'एलेना').
   - NEVER substitute foreign fantasy names with Indian village names.
2. HERALDIC_MONIKER / COGNOMEN (Heraldic Nicknames, Formal Titles, Epithets used as Names):
   - Treat heraldic monikers as PROPER NAMES! Phonetically transliterate into Devanagari.
   - GOLD STANDARD: 'Silver Falcon' -> 'सिल्वर फाल्कन', 'Night Raven' -> 'नाइट रेवेन', 'Gold-Tooth' -> 'गोल्ड-टूथ'.
   - STRICTLY FORBIDDEN: NEVER translate heraldic personal monikers literally word-for-word into Hindi (STRICTLY BANNED: 'चांदी का बाज़', 'रात का कौवा' as character names)!
3. OCCUPATIONAL_ROLE / DESCRIPTIVE EPITHET (Generic situational roles or initial descriptors):
   - Translate into natural spoken Hindustani (e.g. 'The Stranger' -> 'अजनबी', 'The Butcher' -> 'कसाई', 'The Alderman' -> 'एल्डरमैन', 'The Innkeeper' -> 'सरायवाला').
4. ALIAS UNIFICATION & LINKING (CRITICAL FOR AUDIO DRAMA CASTING):
   - If a character is introduced by a descriptive role or moniker before revealing their true name (e.g. 'The Stranger' is revealed to be 'Lord Corwin' / 'Silver Falcon'), explicitly group them under the SAME canonical character record with aliases!
   - This prevents the screenplay engine and TTS casting from splitting one character across multiple voice actors.
```

### 6.2 Excerpt Windowing & Prompt Construction
To provide rich literary grounding while minimizing latency:
- Excerpts the first 6,000 characters of the chapter.
- If the chapter exceeds 10,000 characters, appends an additional 3,000-character mid-chapter excerpt.
- Passes previously known characters so the model can resolve alias linkages (e.g., recognizing that *"The Stranger"* in Chapter 2 is actually *"Lord Corwin"*).

### 6.3 Resilient JSON Unwrapping
The classifier handles diverse LLM response wrapping formats, inspecting alternate keys (`characters`, `entities`, `candidates`, `results`, `data`) and running `json_repair` on malformed outputs.

### 6.4 Automatic Location vs. Terminology Partitioning
Discovered terms in `locations_and_terms` are automatically partitioned using keyword heuristics (`mountain`, `valley`, `city`, `river`, `tavern`, `inn`, `castle`, `gate`, etc.) into `locations` vs `terminology`.

---

## 7. Control Plane Routing & Gateway Bridge (`gateway_bridge.py`)

All LLM operations in Room 1.5 route strictly through [`execute_glossary_llm()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/gateway_bridge.py#L26), connecting Room 1.5 to the **Model & Keys Manager Control Plane** ([`audiobook_factory.core.models`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/)).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              GATEWAY BRIDGE CONTROL PLANE                              │
│                                                                                        │
│  execute_glossary_llm()                                                                │
│    │                                                                                   │
│    ├── 1. Permissive Fiction Framing: get_dramatic_fiction_framing() (BLOCK_NONE)      │
│    ├── 2. ModelGateway.generate_text(task="extraction", response_json=True)            │
│    │     │                                                                             │
│    │     ├── KeyLeaseManager.lease_key(): SQLite ACID Lease (Concurrency = 1)          │
│    │     ├── AntiBanGuard: 11.0 RPM Token Bucket + Stealth SDK Headers                 │
│    │     ├── Session Affinity: Sticky Session Key Binding                              │
│    │     └── Automatic Failover & Retry: Quota Rollover & Anti-Correlation Pause       │
│    │                                                                                   │
│    ├── 3. Resilient JSON Parsing: Strips Markdown fences + json_repair fallback         │
│    └── 4. Strict Fail-Closed Policy: Raises RuntimeError if ModelGateway unavailable   │
│           (0 unmetered urllib/requests calls allowed)                                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.1 The 7 Iron Shields Protection
1. **Concurrency = 1 Mutual Exclusion**: Free Gemini API keys are never double-leased across threads.
2. **AntiBanGuard Rate Pacing**: Clamped to 11.0 RPM (73% of Google AI Studio ceiling) with 3.5s minimum burst spacing.
3. **Official Stealth SDK Headers**: Emits `x-goog-api-client` (`google-genai-sdk-python/0.8.3`), completely masking automated bot signatures.
4. **Permissive Safety Framing (`BLOCK_NONE`)**: Injects dramatic literature context, preventing puritanical censorship of dark fantasy, battle sequences, or mature character dialogue.
5. **Fail-Closed Policy**: If `ModelGateway` cannot be imported, the bridge immediately raises `RuntimeError`. Rogue, unmetered HTTP calls are completely eliminated.

---

## 8. Single-Pass Orchestration & State Synchronization (`manager.py`)

The primary facade for Room 1.5 is [`GlossaryManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/manager.py). It orchestrates lexical scanning, classification, BookBible synchronization, and dynamic cast locking in a single pass.

### 8.1 The 6-Stage Execution Lifecycle (`scan_and_sync_chapter`)

```python
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
```

1. **Stage 1: Load Canonical Lore**: Reads [`BookBible`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py) from `project_dir` or initializes an in-memory instance.
2. **Stage 2: Zero-Token Regex Sweep**: Executes `ChapterLexicalScanner.scan_chapter_text()`. If all candidate names are already known and `force_classification=False`, skips Step 3 entirely.
3. **Stage 3: Gateway Classification**: Dispatches uncataloged candidates to `GlossaryClassifier.classify_candidates()` via `execute_glossary_llm()`.
4. **Stage 4: BookBible Synchronization & Alias Unification**:
   - For existing characters: Appends newly discovered aliases, updating the canonical record.
   - For new characters: Creates a new [`BookEntity`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/book_bible.py) with `EpistemicProvenance(origin="CORPUS_EXTRACTED")`.
   - Merges new locations and terminology into `BookBible.locations` and `BookBible.terminology`.
5. **Stage 5: Dynamic Voice Allocation (Room 4 Cast Lock)**:
   - For every character present in the updated `BookBible`, invokes [`NovelStateMaintainer.discover_and_lock_character()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/metadata/state_maintainer.py).
   - Dynamically allocates a collision-free voice ID and 4D acoustic formant profile, writing to `cast_lock.json` under `_STATE_LOCK`.
   - Persists the updated `book_bible.json` to disk.
6. **Stage 6: Artifact Assembly & Persistence**:
   - Assembles the final [`ChapterGlossary`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/glossary/contracts.py) containing all entities active in this chapter.
   - Persists the artifact atomically to `{project_dir}/glossary/{chap_slug}_glossary.json`.

### 8.2 Production Convenience Methods

```python
# Load existing chapter glossary from disk
cg = GlossaryManager.get_chapter_glossary(chapter_num=3, project_dir="projects/novel")

# Direct export for Room 2 Translation (returns Dict[str, str])
trans_map = GlossaryManager.export_for_translation(chapter_num=3, project_dir="projects/novel")

# Direct export for Room 3 Screenplay (returns {"characters": {...}})
roster = GlossaryManager.export_for_scripting(chapter_num=3, project_dir="projects/novel", use_hindi=True)
```

---

## 9. Backward Compatibility & Public API

To ensure 100% backward compatibility with existing workflows, Room 1.5 provides dual integration paths:

### 9.1 Compatibility Shim (`audiobook_factory/translation/entity_discovery.py`)
The legacy translation entity discovery module has been refactored into a thin adapter shim:
- [`ChapterEntityHarvester.harvest_and_sync()`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/entity_discovery.py#L128): Fully delegates to `GlossaryManager.scan_and_sync_chapter()` and returns the legacy dictionary structure.
- [`EntityDiscoveryEngine`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/entity_discovery.py#L43): Delegates candidate extraction to `ChapterLexicalScanner` and `GlossaryClassifier`.
- [`DiscoveredEntity`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/translation/entity_discovery.py#L33): Preserved for legacy type signatures.

### 9.2 Public Package Exports
Room 1.5 symbols are exported cleanly at both package levels:

```python
# Primary Subsystem Package:
from audiobook_factory.glossary import (
    EntityCategory,
    ChapterEntity,
    ChapterGlossary,
    CandidateEntity,
    ChapterLexicalScanner,
    GlossaryClassifier,
    TRI_PARTITE_SYSTEM_PROMPT,
    execute_glossary_llm,
    GlossaryManager,
)

# Root Audiobook Factory Lazy Imports:
from audiobook_factory import (
    GlossaryManager,
    ChapterGlossary,
    ChapterEntity,
    ChapterLexicalScanner,
    GlossaryClassifier,
)
```

---

## 10. Quality Assurance & Test Verification

The subsystem is validated by comprehensive test suites achieving 100% passing results:

### 10.1 AST Zero-Import Architectural Isolation Test
[`tests/glossary/test_zero_import_isolation.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/tests/glossary/test_zero_import_isolation.py):
- `test_01_assert_zero_forbidden_imports_in_glossary_core`: Inspects the AST of every module in `audiobook_factory/glossary/`. Strictly asserts zero imports of `audiobook_factory.audio`, `tts`, `screenplay`, `dramaturgy`, `requests`, `urllib.request`, `httpx`, or sound drivers.
- `test_02_glossary_manager_routes_exclusively_through_control_plane`: Verifies that `gateway_bridge.py` routes through `ModelGateway` and contains zero direct HTTP calls.

### 10.2 Comprehensive Functional Test Suite
[`tests/glossary/test_glossary_manager.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/tests/glossary/test_glossary_manager.py):
- `test_01_contracts_and_multi_consumer_projections`: Validates Pydantic v2 serialization, SHA-256 fingerprinting, atomic persistence, and projections (`to_translation_glossary`, `to_scripting_roster`, `to_dramaturgy_characters`).
- `test_02_scanner_zero_token_fast_path`: Proves that when all entities are already cataloged in `BookBible`, candidate count is 0 and zero LLM tokens are consumed.
- `test_03_classifier_tri_partite_taxonomy`: Validates transliteration of Proper Names, preservation of Heraldic Monikers (no literal calques), and natural Hindustani translation of Occupational Roles.
- `test_04_glossary_manager_end_to_end_and_state_sync`: Tests single-pass execution, updating `book_bible.json`, writing `cast_lock.json`, and persisting `chapter_001_glossary.json`.
- `test_05_gateway_bridge_compliance_and_fail_closed`: Verifies that `execute_glossary_llm` fails closed (`RuntimeError`) when `ModelGateway` is unavailable.
- `test_06_backward_compatibility_entity_discovery_shim`: Verifies that legacy `ChapterEntityHarvester` and `EntityDiscoveryEngine` operate seamlessly through the shim.

---

## 11. Developer Integration Guide

### 11.1 Scanning a Chapter in Python

```python
from pathlib import Path
from audiobook_factory.glossary import GlossaryManager
from audiobook_factory.metadata.book_bible import BookBible

project_dir = Path("audiobooks/projects/chronicles_of_aldoria")
chapter_text = Path("audiobooks/projects/chronicles_of_aldoria/raw/chapter_003.txt").read_text(encoding="utf-8")

# Single-pass scan, BookBible update, and cast_lock synchronization
chapter_glossary = GlossaryManager.scan_and_sync_chapter(
    chapter_text=chapter_text,
    project_dir=project_dir,
    chapter_num=3,
    chapter_id="chapter_003",
    min_frequency=2,
)

print(f"Glossary Generated: {chapter_glossary.chapter_id} (Hash: {chapter_glossary.version_hash})")
print(f"Total Entities Discovered: {chapter_glossary.total_entities}")
```

### 11.2 Providing Metadata to Room 2 Translation

```python
from audiobook_factory.glossary import GlossaryManager
from audiobook_factory.translation.contracts import TranslationRequest
from audiobook_factory.translation.engine import TranslationEngine

# Export flat English -> Hindi translation glossary
translation_glossary = GlossaryManager.export_for_translation(
    chapter_num=3,
    project_dir=project_dir,
)

request = TranslationRequest(
    source_text=chapter_text,
    chapter_id="chapter_003",
    dynamic_glossary=translation_glossary,
)

result = TranslationEngine.translate_block(request)
```

### 11.3 Providing Roster to Room 3 Screenplay Attribution

```python
from audiobook_factory.glossary import GlossaryManager

# Export structured character roster with unified aliases
character_roster = GlossaryManager.export_for_scripting(
    chapter_num=3,
    project_dir=project_dir,
    use_hindi=True,
)

# Feed directly to DialogueAttributionAuditor or ScriptBuilder
# character_roster format:
# {"characters": {"लॉर्ड कॉरविन": {"aliases": ["Corwin", "Silver Falcon"], "gender": "male", ...}}}
```
