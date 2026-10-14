# 🛡️ Model & Keys Manager: Architecture, Google Cloud Knowledge & Anti-Ban Guard Specification

- **Document Version**: 2.0.0 (Production Blueprint)
- **Status**: Official Engineering Specification & Reference Architecture
- **Target Subsystem**: `audiobook_factory` Core Model, Key & Provider Control Plane
- **Target Workstation Context**: Shared PC AI Workstation & Termux Mobile Operations
- **Security Classification**: Internal Production Standard (Zero-Secret, Anti-Abuse Compliant)

---

## 1. Executive Summary & Purpose

The **Model & Keys Manager** is the mission-critical control plane powering all 5 production rooms of the Audiobook Studio engine:
- **Room 1 (Pre-Production)**: Factual lore extraction, Dramatis Personae, and dialect identification.
- **Room 2 (Translation Collective)**: High-subtext literary Hindustani translation.
- **Room 3 (Screenplay & Attribution)**: Dramatic dialogue attribution with 0% speaker flip guarantee.
- **Room 4 (Vocal Performance & TTS)**: 4D formant acoustic voice acting using Google Gemini 3.8 Flash TTS.
- **Room 5 (Mastering & Packaging)**: Loudness verification and chaptered M4B packaging.

### The Core Challenge & Danger
The team operates with a pool of **100+ free Google AI Studio / Gemini API keys** across multiple human developers, background workers, and automated test runners sharing the **same physical workstation and external IP address**.

> [!CAUTION]
> **Operating with 100+ Free Tier Keys is Inherently High-Risk**:
> Without an uncompromising, centralized guard, subtle flaws—such as concurrent requests on the same key, rapid key-hopping from the same IP, burst spikes during batch runs, robotic user agents, or continuous retry loops on HTTP 429—will immediately trigger Google Cloud's automated abuse detection heuristics, resulting in **cascading project suspensions and irreversible account bans across the entire pool**.

This specification defines the canonical architecture, the Google Cloud API technical knowledge base, the multi-user lease state machine, and the **7 Iron Shields of Key Longevity** to ensure zero bans, zero race conditions, and zero silent quality degradation.

---

## 2. Threat Model: Why Free Keys Get Banned & How to Prevent It

To build an impenetrable guard, we must first deeply understand the heuristics Google Cloud and Google AI Studio edge proxies use to detect and ban automated traffic:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        GOOGLE ABUSE DETECTION THREAT VECTORS                           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Vector 1: Concurrent Dogpiling on a Single Key                                         │
│   Free keys are rated for 15 RPM. Firing 3 simultaneous in-flight connections on one   │
│   key immediately triggers HTTP 429 or 403 Concurrency Violations.                    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Vector 2: Rapid Key-Hopping & IP Correlation                                           │
│   Flipping to a new key on every single request from the same IP exposes key-pooling   │
│   heuristics at the edge gateway. Keys get clustered and mass-suspended.               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Vector 3: Robotic Burst Footprints & Mechanical Intervals                              │
│   Requests fired at exact clock intervals (e.g., precisely every 2.0s) match bot       │
│   signatures. Legitimate humans read, listen, and review before submitting lines.      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Vector 4: Retry Death Spirals on 429 / 5xx Outages                                     │
│   When an outage hits, naive scripts rotate through all 100 keys in seconds, burning   │
│   daily quotas and flagging the entire pool as a coordinated scraping swarm.           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Vector 5: Non-Standard SDK User-Agents & Headers                                       │
│   Custom agents like 'AudiobookFactory/2.0' or raw urllib headers signal headless      │
│   scripts. Official SDK signatures bypass bot inspection queues.                       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Vector 6: Midnight Thundering Herd                                                     │
│   When Pacific Midnight resets quotas, all queued workers waking at 00:00:01 PT        │
│   create a localized DDoS spike that edge rate-limiters aggressively choke.            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The 7 Iron Shields of Key Longevity

The Anti-Ban Guard is not an optional utility; it is the **uncompromising center of the system**:

```text
                                  API REQUEST
                                       │
                                       ▼
                   ┌───────────────────────────────────────┐
                   │    SHIELD 1: ATOMIC MUTUAL EXCLUSION  │ ──► Exactly 1 In-Flight Request Per Key
                   └───────────────────┬───────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │   SHIELD 2: SESSION AFFINITY LEASING  │ ──► Stay on 1 Key Per Scene/Batch (No Hopping)
                   └───────────────────┬───────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │  SHIELD 3: ANTI-CORRELATION COOLDOWN  │ ──► Mandatory 18-32s Pause When Switching Keys
                   └───────────────────┬───────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │    SHIELD 4: HUMAN CADENCE SHAPING    │ ──► Log-Normal Jitter + Reading/Listening Time
                   └───────────────────┬───────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │ SHIELD 5: 75% CONSERVATIVE RATE LIMIT │ ──► Cap at 11 RPM (Below 15 RPM Provider Limit)
                   └───────────────────┬───────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │   SHIELD 6: OFFICIAL SDK EMULATION    │ ──► google-genai-sdk-python Header Signatures
                   └───────────────────┬───────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │ SHIELD 7: EMERGENCY GLOBAL TRIPWIRE   │ ──► Halt on 5 Consecutive 429s (Stop Spiral)
                   └───────────────────┬───────────────────┘
                                       ▼
                             TARGET API ENDPOINT
```

### Shield 1: Atomic Mutual Exclusion (Concurrency = 1)
Every free Google API key is treated as a strictly serial resource:
- **Rule**: Exactly **1 active in-flight request** per API key across the entire workstation.
- **Enforcement**: Guaranteed via SQLite atomic transactional reservation (`UPDATE ... RETURNING`). No other process or thread can acquire the key until the previous request completes and is released.

### Shield 2: Session Affinity (Anti-Hopping Pacing)
- **Rule**: A worker process must NOT hop to a different key on every segment.
- **Mechanism**: When a worker starts synthesizing Chapter 3 or translating a scene, it leases Key $K$ with **Session Affinity**. All sequential segments within that scene use Key $K$, spaced by natural delays.
- **Result**: Traffic appears to Google's backend as a single developer interactively working in a development console, completely invisible to multi-key clustering algorithms.

### Shield 3: Anti-Correlation Key-Switch Cooldown
- **Rule**: When a key reaches its daily quota or maximum scene count, the worker must switch to another key.
- **Enforcement**: Prior to making the first call on the *new* key, the worker enters an **anti-correlation cooldown pause of 18.0 to 32.0 seconds**:
  $$T_{\text{switch\_wait}} \sim \text{Uniform}(18.0, 32.0)$$
- **Why It Matters**: This prevents Google's network traffic analysers from correlating sequential HTTP connections from the same IP address across different API keys.

### Shield 4: Human Cadence & Studio Director Simulation
Real audio engineers do not fire requests continuously. The cadence engine calculates content-aware delays before every call:
$$T_{\text{wait}} = T_{\text{read}}(\text{word\_count}) + T_{\text{review}}(\text{prev\_audio\_duration}) + T_{\text{jitter}}$$
1. **Reading Time**: Humans read text at 220–260 WPM ($3.5–4.5$ words/sec) before pressing render:
   $$T_{\text{read}} = \min\left(12.0, \max\left(2.5, \frac{\text{word\_count}}{\text{wps}}\right)\right)$$
2. **Audio Listening Simulation**: An engineer samples 15% to 35% of the previously generated take:
   $$T_{\text{review}} = \min(15.0, \text{prev\_audio\_duration} \times \text{Uniform}(0.15, 0.35))$$
3. **Log-Normal Think Time Jitter**: Realistic human pause distribution:
   $$T_{\text{jitter}} = \text{LogNormal}(\mu=1.2, \sigma=0.35) \quad (\text{clamped to } [1.5, 7.0]\text{s})$$
4. **Director Scene Review Breaks**: Every 12–16 segments, the engine pauses for **15.0 to 30.0 seconds** to simulate a director reviewing scene flow.

### Shield 5: Conservative 75% Rate Limiting
Even though Google specifies 15 RPM for free Gemini Flash models, network latency variations and timestamp rounding at Google's edge can trigger false 429s.
- **Rule**: The local token bucket caps throughput at **11.0 RPM** (73% of capacity).
- **Burst Window**: Enforces a minimum interval of **3.5 seconds** between requests on the same key.

### Shield 6: Official SDK Header Emulation
All HTTP requests strip robotic Python user-agents and inject exact Google GenAI SDK headers:
```python
def get_stealth_sdk_headers(api_key: str) -> Dict[str, str]:
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    platform_tag = "windows/10.0.26100" if sys.platform == "win32" else "linux/x86_64"
    return {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key,
        "User-Agent": f"google-genai-sdk-python/0.8.3 gl-python/{py_ver} ({platform_tag})",
        "x-goog-api-client": f"gl-python/{py_ver} gax/2.24.0 gccl/0.8.3",
    }
```

### Shield 7: Emergency Global Tripwire
If 5 keys fail consecutively with HTTP 429 or 503 within a 60-second window:
- **Action**: The manager activates the **Emergency Pool Quarantine**.
- **Behavior**: All key rotation is halted. No new requests are dispatched for **45 seconds**.
- **Reason**: This prevents an edge network blip or API update from wiping out all 100 keys in a 10-second retry death spiral.

### Shield 8: Strict TTS-Only Workload Isolation & Antigravity Subagent Execution (Ponytail Standard v6.1)
To eliminate 429 daily quota exhaustion, RPM thrashing, and IP clustering caused by heavy text reasoning over free API keys:
- **Zero Outbound Text API Calls**: All text generation tasks (Room 1 Pre-Production research, Room 1.5 Glossary, Room 2 Translation Collective, Room 3 Screenplay Dramaturgy, Casting, Gate Audits) are permanently deadbolted in `ModelGateway.generate_text()`, `GeminiProviderAdapter.generate_text()`, `OpenAICompatibleAdapter.generate_text()`, and `llm_client.call_gemini()`.
- **Antigravity Native Reasoning**: All intelligence, novel research, literary translation, and screenplay construction are performed natively inside Antigravity via subagent invocations.
- **Dedicated TTS Key Pool**: Every active Google AI Studio key is strictly scoped to `allowed_services = '["tts"]'`, reserving 100% of API capacity for `gemini-3.8-flash-tts` vocal speech synthesis.
- **Permanent Quarantine Archival**: Banned, revoked, or disabled keys are physically quarantined in `key_quarantine` with `is_permanent = 1` and never leased or called.
- **Zero Network Pings**: Model discovery and health checks are performed via static offline catalog caching with 0 network pings.

---

## 4. Google Cloud & Gemini API Technical Knowledge Base

The Model Registry and Gateway are grounded in precise, real-world Google AI Studio API specifications:

### 4.1 Canonical Model Landscape & Production Roles

| Model Identifier | Quality Tier | Modalities | Context Window | Max Output | Free RPM | Free TPM | Free RPD | Primary Production Room |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`gemini-3.8-flash`** | Flagship (Tier 1) | Text, Vision | 1,048,576 | 65,536 | 15 | 1,000,000 | 1,500 | Room 2 (Translation), Room 3 (Screenplay) |
| **`gemini-3.7-flash`** | Flagship (Tier 1) | Text, Vision | 1,048,576 | 65,536 | 15 | 1,000,000 | 1,500 | Room 3 (Attribution), Room 1 (DNA) |
| **`gemini-3.6-flash`** | Balanced (Tier 2) | Text, Vision | 1,048,576 | 32,768 | 15 | 1,000,000 | 1,500 | Room 1 (Extraction), Blocking QA |
| **`gemini-2.5-flash`** | Balanced (Tier 2) | Text, Vision | 1,048,576 | 32,768 | 15 | 1,000,000 | 1,500 | Secondary Fallback |
| **`gemini-2.5-pro`** | Flagship (Tier 1) | Text, Vision | 2,097,152 | 8,192 | **2** | **32,000** | **50** | **Quarantined**: Used only for complex forensic audits |
| **`gemini-3.8-flash-tts`**| Flagship Audio | Audio Out | 32,768 | 8,192 | 15 | 500,000 | **10** | Room 4 (Vocal Speech Synthesis) |
| **`gemini-3.1-flash-lite`**| Utility (Tier 3) | Text | 1,048,576 | 8,192 | 30 | 4,000,000 | 1,500 | Fast JSON parsing, token counts |

### 4.2 Key Invariants for Gemini Flash Models

#### 1. The 10 RPD Speech Synthesis Ceiling
- `gemini-3.8-flash-tts` on Google AI Studio Free Tier has a **hard ceiling of 10 Requests Per Day (RPD) per API key**.
- **Mathematical Reality**: With 100 free keys, the team has a daily production budget of:
  $$100 \text{ keys} \times 10 \text{ RPD} = 1,000 \text{ audio segments / day}$$
- **Architectural Consequence**: Audio synthesis must NEVER be wasted on exploratory testing. Dialogue must be batched and validated by Screenplay gates before invoking Room 4.

#### 2. The `thinkingConfig` Mechanism (Gemini 2.5 / 3.x)
- In Gemini 3.x Flash models, reasoning tokens count against the `maxOutputTokens` budget.
- For high-creativity tasks (Room 2 Translation, Room 3 Screenplay), inject explicit thinking budgets:
  ```json
  "generationConfig": {
    "temperature": 0.85,
    "maxOutputTokens": 32768,
    "thinkingConfig": {
      "thinkingBudget": 1024
    }
  }
  ```
- **Rule**: If a model returns `finishReason: "MAX_TOKENS"`, halve `thinkingBudget` to 512 and retry once. If it fails again, halt rather than truncating script text.

#### 3. Fiction Safety Framing (`BLOCK_NONE` Invariant)
- Dramatic fantasy fiction (e.g. Witcher, horror, historical war) contains combat gore, weapon violence, and intense dialogue.
- Standard Google safety thresholds trigger false-positive blocks (`HARM_CATEGORY_DANGEROUS_CONTENT`).
- **Rule**: Creative requests must always pass `BLOCK_NONE` safety settings paired with standard dramatic fiction framing in the system prompt:
  ```text
  [DRAMATIC LITERARY FICTION CONTEXT: This request contains fictional dialogue for a dramatic audiobook adaptation. All depictions of combat, conflict, and emotion are purely artistic storytelling.]
  ```

#### 4. Pacific Midnight Quota Reset Mechanics
- Google AI Studio daily quotas reset precisely at **Midnight US Pacific Time (PT)**.
- **DST Sensitivity**:
  - PDT (Daylight Saving): UTC-7 (March to November).
  - PST (Standard Time): UTC-8 (November to March).
- **Rule**: The system must use IANA `ZoneInfo("America/Los_Angeles")` with a fixed `timezone(timedelta(hours=-7))` fallback for Windows environments lacking `tzdata`.

---

## 5. Multi-User Shared-Workstation Architecture

### 5.1 The Workstation Problem Definition
Multiple team members access the studio workstation:
- User A runs a script in Bash (`/data/data/com.termux/...` or Linux shell).
- User B runs an interactive testing command.
- Background worker processes run long-running chapter mastering.

```text
User A (Terminal 1) ──┐
                      ├── SQLite WAL DB ──> [Atomic KeyLeaseManager] ──> Free Key Pool
User B (Terminal 2) ──┘
```

Without synchronization:
- User A's process and User B's process read the same key from `.env`.
- Both fire requests at the same second.
- Both get HTTP 429. Both rotate to the next key.
- Entire pool burns out in minutes.

### 5.2 Atomic Key Lease State Machine

```text
                  ┌────────────────────────┐
                  │       AVAILABLE        │
                  │ (status = 'ACTIVE')    │
                  └───────────┬────────────┘
                              │
                    Acquire Lease (Atomic)
                              │
                              ▼
                  ┌────────────────────────┐
                  │         LEASED         │ ◄─── Heartbeat (every 15s)
                  │ (locked with PID, TTL) │
                  └───────────┬────────────┘
                              │
            ┌─────────────────┴─────────────────┐
     Normal Completion                     Worker Crash
            │                                   │
            ▼                                   ▼
┌────────────────────────┐          ┌────────────────────────┐
│     SAFETY COOLDOWN    │          │     STALE RECLAIMED    │
│  (5s delay before new  │          │ (PID dead or TTL past; │
│   user can acquire)    │          │  instant auto-release) │
└───────────┬────────────┘          └───────────┬────────────┘
            │                                   │
            └─────────────────┬─────────────────┘
                              ▼
                  ┌────────────────────────┐
                  │       AVAILABLE        │
                  └────────────────────────┘
```

### 5.3 Database Schema (ACID SQLite WAL Mode)

```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;

-- Master Key Inventory
CREATE TABLE IF NOT EXISTS key_inventory (
    key_hash TEXT PRIMARY KEY,               -- SHA-256 (first 16 hex chars)
    key_alias TEXT NOT NULL UNIQUE,          -- Public safe alias (e.g. 'key_a8f2')
    encrypted_key TEXT NOT NULL,             -- Machine-encrypted or obfuscated API key
    provider TEXT NOT NULL DEFAULT 'gemini', -- gemini, cerebras, groq, openai, local
    tier TEXT NOT NULL DEFAULT 'free',       -- free, paid, vertex
    allowed_services TEXT NOT NULL,          -- JSON: ["text", "tts"] or ["text"]
    status TEXT NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE, EXHAUSTED_TODAY, TEMP_BACKOFF, INVALID
    exhausted_date TEXT,                     -- YYYY-MM-DD (Pacific Date for Google)
    backoff_until TIMESTAMP,
    total_calls_today INTEGER DEFAULT 0,
    success_calls_today INTEGER DEFAULT 0,
    failed_calls_today INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    last_reset_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Active Leases Table
CREATE TABLE IF NOT EXISTS key_leases (
    lease_id TEXT PRIMARY KEY,               -- UUIDv4
    key_hash TEXT NOT NULL,
    provider TEXT NOT NULL,
    workstation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    process_id INTEGER NOT NULL,
    worker_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    workload_type TEXT NOT NULL,             -- 'text' or 'tts'
    leased_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,           -- leased_at + ttl_seconds
    heartbeat_at TIMESTAMP NOT NULL,
    status TEXT NOT NULL,                    -- 'ACTIVE', 'RELEASED', 'EXPIRED', 'REVOKED'
    FOREIGN KEY(key_hash) REFERENCES key_inventory(key_hash)
);

CREATE INDEX IF NOT EXISTS idx_leases_lookup 
ON key_leases(key_hash, status, expires_at);

CREATE INDEX IF NOT EXISTS idx_leases_user_gate 
ON key_leases(user_id, workload_type, status);

-- Per-Model Quota Ledger (Model-Level Isolation)
CREATE TABLE IF NOT EXISTS model_quota_ledger (
    key_hash TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'gemini',
    model TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE, EXHAUSTED_TODAY, TEMP_BACKOFF
    exhausted_date TEXT,
    total_calls_today INTEGER DEFAULT 0,
    success_calls_today INTEGER DEFAULT 0,
    failed_calls_today INTEGER DEFAULT 0,
    total_tokens_today INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    backoff_until TIMESTAMP,
    last_error TEXT,
    last_reset_date TEXT,
    PRIMARY KEY(key_hash, model)
);

-- Zero-Secret Audit Trail
CREATE TABLE IF NOT EXISTS key_audit_log (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,                -- ACQUIRE, RENEW, RELEASE, EXPIRE, 429_REVOKE
    lease_id TEXT NOT NULL,
    key_alias TEXT NOT NULL,
    user_id TEXT NOT NULL,
    process_id INTEGER NOT NULL,
    model_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    latency_ms INTEGER,
    status_code INTEGER,
    error_summary TEXT
);
```

### 5.4 "One User = One Active Key" Enforcement Logic

The manager enforces fairness by bounding concurrent leases per user:

$$\text{ActiveLeases}(\text{user\_id}, \text{provider}, \text{workload\_type}) \le 1$$

```python
def check_user_concurrency(conn: sqlite3.Connection, user_id: str, provider: str, workload: str) -> bool:
    """Verifies user does not already hold an active lease for this workload type."""
    row = conn.execute("""
        SELECT COUNT(*) as active_count
        FROM key_leases
        WHERE user_id = ? 
          AND provider = ? 
          AND workload_type = ? 
          AND status = 'ACTIVE' 
          AND expires_at > CURRENT_TIMESTAMP;
    """, (user_id, provider, workload)).fetchone()
    return row["active_count"] == 0
```

---

## 6. Central Model Registry & Task-Based Routing

### 6.1 Unified Architecture

The new system unifies model intelligence and key management under a single, cohesive facade:

```text
audiobook_factory/
└── core/
    ├── models/
    │   ├── __init__.py
    │   ├── gateway.py            # ModelGateway: Universal facade for all rooms
    │   ├── registry.py           # ModelRegistry: Canonical specs & capability matrix
    │   ├── lease_manager.py      # KeyLeaseManager: ACID SQLite lease engine
    │   ├── policy_engine.py      # PolicyEngine: Rate limits, anti-ban guard & circuit breakers
    │   ├── router.py             # RequestRouter: Requirements -> Execution Plan
    │   └── adapters/             # Polymorphic Provider Adapters
    │       ├── base.py           # BaseProviderAdapter interface
    │       ├── gemini.py         # GeminiProviderAdapter (REST, headers, thinking, audio)
    │       ├── openai_compat.py  # Cerebras, Groq, OpenAI, OpenRouter adapter
    │       └── local_gpu.py      # Local CUDA MMS / Spark adapter (VRAM lock)
```

### 6.2 Task Presets & Routing Matrix

| Task Type | Minimum Quality Floor | Default Preferred Model | Creative Fiction Framing | Thinking Budget | Response Format |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`TaskType.TRANSLATION`** | `TIER_1_FLAGSHIP` | `gemini-3.8-flash` | Mandatory | 1024 tokens | `application/json` |
| **`TaskType.SCREENPLAY`** | `TIER_1_FLAGSHIP` | `gemini-3.8-flash` | Mandatory | 1024 tokens | `application/json` |
| **`TaskType.DRAMATURGY`** | `TIER_1_FLAGSHIP` | `gemini-3.7-flash` | Mandatory | 1024 tokens | `application/json` |
| **`TaskType.DIRECTING`** | `TIER_2_BALANCED` | `gemini-3.6-flash` | Mandatory | Optional | `application/json` |
| **`TaskType.TTS`** | `TIER_1_FLAGSHIP` | `gemini-3.8-flash-tts` | Audio Modality | N/A | Raw PCM / WAV |
| **`TaskType.AUDITING`** | `TIER_2_BALANCED` | `gemini-3.6-flash` | Standard | None | `application/json` |
| **`TaskType.EXTRACTION`** | `TIER_2_BALANCED` | `llama3.3-70b` / `gemini-3.6` | Standard | None | `application/json` |
| **`TaskType.UTILITY`** | `TIER_3_UTILITY` | `gemini-3.1-flash-lite` | None | None | Plain Text / JSON |

---

## 7. Stable Interface for Consumer Subsystems

All 5 production rooms interact with models via the `ModelGateway`:

```python
from audiobook_factory.core.models.gateway import get_model_gateway
from audiobook_factory.core.models.registry import TaskType

gateway = get_model_gateway()

# 1. High-Level Text Inference (Used by Translator, Screenplay, Dramaturge)
result = gateway.generate_content(
    prompt="Translate this dialogue beat...",
    system_instruction="You are a master Hindustani dramatist...",
    task=TaskType.TRANSLATION,
    response_schema=BeatTranslationSchema,
)

# 2. High-Level Speech Synthesis (Used by TTSDispatcher)
audio_output_path = gateway.synthesize_speech(
    text="क्या तुम सच में जा रहे हो?",
    voice="Aoede",
    output_path=Path("audiobooks/chapter_001/chunk_005.wav"),
    emotion="grave",
    acting_style="whisper_of_dread",
)

# 3. Context-Managed Multi-Turn Production Session
with gateway.lease_session(task=TaskType.SCREENPLAY) as session:
    draft = session.generate("Generate Scene 1...")
    audited = session.generate("Audit Dialogue Attribution...")
```

---

## 8. Implementation Checklist & Verification Gates

### Phase P0: Foundational Safety & Key Leasing (Immediate)
- [ ] Create SQLite schema in `audiobooks/key_pool_state.db` (`key_inventory`, `key_leases`, `key_audit_log`).
- [ ] Implement `KeyLeaseManager`:
  - [ ] Atomic `UPDATE ... RETURNING` acquisition query.
  - [ ] PID liveness check (`os.kill(pid, 0)`).
  - [ ] Background heartbeat thread (15s interval).
  - [ ] Stale lease auto-reclamation sweep.
  - [ ] One-User-One-Key per workload check.
- [ ] Implement `PolicyEngine & AntiBanGuard`:
  - [ ] Pacific Midnight date calculation (DST-aware).
  - [ ] Anti-correlation key-switch delay (18s-32s).
  - [ ] Human cadence generator ($T_{\text{read}} + T_{\text{listen}} + T_{\text{jitter}}$).
  - [ ] 5-failure emergency pool tripwire.
- [ ] Migrate logging to use deterministic public aliases (`key_a8f2`).

### Phase P1: Model Registry & Provider Adapters
- [x] Implement `ModelRegistry` with canonical metadata for all Gemini and alternative models.
- [x] Implement `GeminiProviderAdapter` with stealth SDK headers and thinkingConfig.
- [x] Implement `OpenAICompatibleAdapter` for Cerebras, Groq, and OpenRouter.
- [x] Wire `llm_client.py` and `tts/providers/gemini.py` to use `KeyLeaseManager`.

### Phase P2: Gateway Facade & Backward Compatibility
- [x] Provide drop-in facades for `get_model_manager()` and `get_persistent_key_pool()` so zero existing code breaks.
- [x] Run full test suite:
  - `tests/test_model_manager_and_strict_halt.py`
  - `tests/test_universal_key_pool_and_guard_shield.py`
  - `tests/test_key_quarantine_and_hang_defenses.py`
  - `tests/test_key_lease_engine.py`
  - `tests/test_key_adversarial_stress_and_coverage.py`
- [x] Multi-user concurrency tests simulating 100 parallel threads under SQLite contention.

---

## 9. Key Quarantine Vault & Physical Segregation Architecture

### 9.1 The Need for Physical Quarantine
In a high-throughput fleet of 100+ free-tier API keys, keys will occasionally encounter permanent revocation or suspension from Google Cloud (HTTP 400 `API_KEY_INVALID`, HTTP 403 `CONSUMER_SUSPENDED`, `API_KEY_REVOKED`, etc.). 

If invalid keys remain in the active `key_inventory` table with a temporary flag:
1. Daily Pacific Midnight rollovers (`reset_all_for_today()`) would wipe the failure status and resurrect dead keys into active rotation.
2. Background worker threads would continually lease dead keys, waste valuable rate-limit windows, and crash synthesis pipelines.
3. Administrative resets (`keys reset`) would re-activate unusable credentials.

To solve this, the **Key Quarantine Vault** ([`KeyQuarantineManager`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/quarantine.py)) enforces **Physical Vault Segregation**: dead keys are moved out of active inventory and into a dedicated `key_quarantine` table in SQLite (`audiobooks/key_pool_state.db`).

### 9.2 Quarantine Table Schema & Data Contract

```sql
CREATE TABLE IF NOT EXISTS key_quarantine (
    key_hash TEXT PRIMARY KEY,
    encrypted_key TEXT NOT NULL,
    key_alias TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'gemini',
    error_code INTEGER,
    quarantine_reason TEXT NOT NULL,
    error_body_snippet TEXT,
    quarantined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quarantined_by TEXT NOT NULL,
    is_permanent INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_quarantine_provider ON key_quarantine(provider);
CREATE INDEX IF NOT EXISTS idx_quarantine_alias ON key_quarantine(key_alias);
```

### 9.3 Zero Zombie Resurrection Invariant
The quarantine architecture enforces four strict guarantees that permanently prevent dead keys from re-entering active rotation:

1. **Physical Segregation**: When a key is quarantined, it is deleted from `key_inventory` and `key_quota_ledger` inside an atomic transaction, leaving zero footprint in active routing.
2. **Rollover Immunity**: `KeyLeaseManager.reset_all_for_today()` and `PersistentKeyPool._check_date_rollover()` query strictly `key_inventory` and `key_quota_ledger`. They possess zero access to `key_quarantine`.
3. **Admin Reset Isolation**: `python audiobook_cli.py keys reset` updates only active inventory ledgers; quarantined keys remain locked in the vault.
4. **Environment Ingestion Shield**: When workers start or reload environment variables (`register_keys()`, `PersistentKeyPool.get_key()`), `KeyQuarantineManager.is_quarantined()` is queried first. If an environment variable key is already in quarantine, ingestion is rejected.

```text
                  API Request Fails with Permanent Error
                  (400 API_KEY_INVALID / 403 CONSUMER_SUSPENDED)
                                    │
                                    ▼
                     PolicyEngine Classifies Error
                     (Permanent API Key Ban Detected)
                                    │
                                    ▼
                Atomic BEGIN IMMEDIATE SQLite Transaction
                ┌─────────────────────────────────────────┐
                │ 1. Insert into key_quarantine           │
                │ 2. Revoke active lease in key_leases    │
                │ 3. Delete row from key_inventory        │
                │ 4. Delete row from key_quota_ledger     │
                │ 5. Log audit event to key_audit_log     │
                └─────────────────────────────────────────┘
                                    │
                                    ▼
                Physical Isolation Complete (0% Resurrection)
```

### 9.4 Standalone Quarantine API

The `KeyQuarantineManager` provides a clean, decoupled programmatic API:

```python
from audiobook_factory.core.models.quarantine import get_key_quarantine_manager

q_mgr = get_key_quarantine_manager()

# 1. Check isolation status
if q_mgr.is_quarantined(key_str_or_hash):
    ...

# 2. Quarantine dead key with forensic diagnostic context
q_mgr.quarantine_key(
    key="AIzaSy...",
    reason="API_KEY_INVALID: API key not valid",
    error_code=400,
    error_body="...",
    quarantined_by="ModelGateway",
)

# 3. List and inspect
records = q_mgr.list_quarantined(provider="gemini")
rec = q_mgr.get_quarantined(alias="key_a162fd4b")

# 4. Export and purge
q_mgr.export_quarantined(Path("quarantined.json"), include_plaintext=False)
purged_count = q_mgr.purge_keys(key_aliases_or_hashes=["key_a162fd4b"])

# 5. Restore (manual operator override)
q_mgr.restore_key("key_a162fd4b")
```

---

## 10. Concurrency Hardening & Forensic Defenses (F-01 through F-06)

Following rigorous adversarial QA auditing and 100-thread multi-process stress testing, six critical runtime defenses were codified into the Model & Key Control Plane:

### F-01: Prompt Payload Echo Defense & Geolocation Cooldown
- **Vulnerability**: Google API echoes back prompt snippets in HTTP 400 Bad Request error responses. Naive substring searches for `"invalid"`, `"forbidden"`, or `"suspended"` caused valid API keys to be permanently quarantined whenever dramatic scripts contained those words. Furthermore, HTTP 403 `USER_LOCATION_NOT_SUPPORTED` (common when VPNs flicker or routes shift) was previously misclassified as a permanent account suspension.
- **Remediation**:
  1. HTTP 400 error classification in [`policy_engine.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/policy_engine.py#L107-L135) and [`guard_shield.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/guard_shield.py#L260-L285) requires explicit API key error tokens: `API_KEY_INVALID`, `API_KEY_SERVICE_BLOCKED`, `API_KEY_REVOKED`, or regex `api key not valid`.
  2. HTTP 403 `USER_LOCATION_NOT_SUPPORTED` is mapped to `LOCATION_UNSUPPORTED`, placing the key in a temporary 5-minute cooldown without burning the key.

### F-02: Multi-Field Deterministic Key Lookup
- **Vulnerability**: Legacy lookups differentiated keys and hashes using length heuristics (`len(id) in (12, 16)`). However, public key aliases generated by `KeyInventoryRecord.key_alias` are formatted as `key_XXXXXXXX` (exactly 12 characters). Passing an alias to quarantine or lease functions caused it to be treated as a legacy hash slice, resulting in silent lookup misses.
- **Remediation**: Replaced length-based branching in [`quarantine.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/quarantine.py#L70-L130) with unified multi-field SQL:
  ```sql
  SELECT * FROM key_quarantine WHERE key_hash = ? OR key_alias = ? OR encrypted_key = ?
  ```

### F-03: Pre-Selection Housekeeping Transaction Isolation
- **Vulnerability**: In [`lease_manager.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/lease_manager.py#L365-L390), stale lease sweeps and expired backoff clears were grouped inside the same transaction block as lease selection. When the key pool was temporarily exhausted, `acquire_lease()` raised `NoAvailableKeyError`, causing Python's `with conn:` context manager to rollback the entire transaction and discarding all housekeeping work.
- **Remediation**: Housekeeping (dead PID sweeps + expired backoff clears) is executed and committed in its own isolated transaction prior to attempting lease candidate queries.

### F-04: Fail-Safe Probe Lease Release
- **Vulnerability**: In [`gateway.py`](file:///c:/Users/Suraj/Documents/antigravity/optimistic-kepler/audiobook_factory/core/models/gateway.py#L125-L138), a temporary probe lease was acquired to inspect capabilities before resolving an execution plan. If `resolve_plan()` threw an exception (e.g. unknown model tier or invalid task), the probe lease was leaked, leaving the key locked until TTL expiration.
- **Remediation**: Wrapped `resolve_plan()` immediately with `try ... finally: lease_mgr.release_lease(probe_lease.lease_id)`, guaranteeing zero probe lease leakage.

### F-05: Session Affinity Fallback Protection
- **Vulnerability**: When an in-flight request on an affinity session failed and the router attempted fallback execution, secondary model resolution could clobber the primary session's affinity mapping in `SessionAffinityTracker`.
- **Remediation**: Scoped affinity updates in `gateway.py` so secondary fallback branches do not overwrite existing caller affinity sessions.

### F-06: Bidirectional State Mirroring & Ingestion Guards
- **Vulnerability**: Legacy `PersistentKeyPool` (`key_quota_ledger`) and modern `KeyLeaseManager` (`key_inventory`) risked state drift if status updates were only applied to one table.
- **Remediation**: `KeyLeaseManager.record_success()`, `mark_daily_quota_exhausted()`, and `mark_temporary_backoff()` maintain bidirectional mirroring to `key_quota_ledger` when present, ensuring both legacy and modern facades view identical key states.

### Concurrency & Deadlock Boundaries
- **SQLite Concurrency**: All database operations use Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), synchronous normal (`PRAGMA synchronous=NORMAL;`), and a 30-second busy timeout (`PRAGMA busy_timeout=30000;`).
- **Immediate Locking**: Critical state mutations (`renew_lease`, `release_lease`, `revoke_lease`, `quarantine_key`) initiate transactions using `BEGIN IMMEDIATE;`, guaranteeing exclusive write locks and eliminating `SQLITE_BUSY` deadlock cascades during multi-threaded contention.
- **Workstation Scoping on Dead PID Sweeps**: On Windows 11 multi-user environments, `sweep_stale_and_dead_leases` scopes dead PID termination checks strictly to leases matching the local machine's `workstation_id`, preventing cross-machine PID collisions.

---
*Document Authorized by Antigravity Studio Architecture Board.*
