# 🛡️ Google API Key Guard & Model Intelligence Engineering Guide
## The Production Blueprint for Managing 100+ Free Google AI Studio Keys Without Bans

- **Document Identifier**: `ENG-SPEC-KEY-GUARD-V2`
- **Target System**: `audiobook_factory` Model, Key & Provider Control Plane
- **Status**: Canonical Engineering Manual & Implementation Standard
- **Audience**: Core Developers, System Architects, DevOps & Test Engineers
- **Security Standard**: Zero-Secret Storage, Anti-Ban Traffic Shaping, Multi-User Isolation

---

## Table of Contents
1. [Executive Threat Model: Operating 100+ Free Keys Safely](#1-executive-threat-model-operating-100-free-keys-safely)
2. [The 7 Iron Shields of Key Longevity (The Anti-Ban Bible)](#2-the-7-iron-shields-of-key-longevity-the-anti-ban-bible)
3. [Empirical Google Cloud & Gemini Model Catalog (Live Probed)](#3-empirical-google-cloud--gemini-model-catalog-live-probed)
4. [The Critical Gemini 3.8 Thinking Token Pitfall & Real-World Fix](#4-the-critical-gemini-38-thinking-token-pitfall--real-world-fix)
5. [Multi-User Shared-Workstation Lease Architecture](#5-multi-user-shared-workstation-lease-architecture)
6. [Core Module Specifications & Code Contracts](#6-core-module-specifications--code-contracts)
7. [Step-by-Step Implementation Checklist & Bug Prevention Playbook](#7-step-by-step-implementation-checklist--bug-prevention-playbook)

---

## 1. Executive Threat Model: Operating 100+ Free Keys Safely

### 1.1 The High-Risk Reality
The Audiobook Studio pipeline relies on a pooled fleet of **100+ legitimate Google AI Studio free tier API keys**. On a shared workstation, multiple developers, test runners, and production background workers execute simultaneous or sequential tasks from the **same public IP address**.

> [!CAUTION]
> **Why Free Keys Get Mass-Banned by Google**:
> Google Cloud / AI Studio edge gateways deploy aggressive, automated heuristic abuse filters. If requests exhibit robotic hallmarks—such as concurrent connections on a single key, rapid key-hopping across requests, continuous clock-interval bursts, non-standard user-agents, or fast retry loops during outages—Google's firewalls flag the IP and key cluster as an **automated multi-account scraping botnet**, resulting in:
> 1. Instant HTTP 429 / 403 cascading blocks.
> 2. Project-level API quota revokation.
> 3. Permanent, irreversible account suspension across the entire 100+ key fleet.

### 1.2 The Core Mandate
The **Key Guard is NOT an auxiliary utility; it is the absolute CENTER of the system.** Every single request to any model MUST pass through the Guard's traffic-shaping filters before reaching the network.

---

## 2. The 7 Iron Shields of Key Longevity (The Anti-Ban Bible)

The Key Guard enforces seven non-negotiable defensive invariants:

```text
                                  API REQUEST
                                       │
                                       ▼
                   ┌───────────────────────────────────────┐
                   │    SHIELD 1: ATOMIC MUTUAL EXCLUSION  │ ──► Concurrency = 1 (Zero Dogpiling)
                   └───────────────────┬───────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │   SHIELD 2: SESSION AFFINITY LEASING  │ ──► Stick to 1 Key per Scene (No Rapid Hopping)
                   └───────────────────┬───────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │  SHIELD 3: ANTI-CORRELATION COOLDOWN  │ ──► Mandatory 18-32s Pause on Key Switch
                   └───────────────────┬───────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │    SHIELD 4: HUMAN CADENCE SHAPING    │ ──► Reading + Listening Time + Log-Normal Jitter
                   └───────────────────┬───────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │ SHIELD 5: 75% CONSERVATIVE RATE LIMIT │ ──► Cap at 11 RPM (Below 15 RPM Ceiling)
                   └───────────────────┬───────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │   SHIELD 6: OFFICIAL SDK EMULATION    │ ──► google-genai-sdk-python Header Signatures
                   └───────────────────┬───────────────────┘
                                       ▼
                   ┌───────────────────────────────────────┐
                   │ SHIELD 7: EMERGENCY GLOBAL TRIPWIRE   │ ──► Auto-Quarantine on 5 Consecutive 429s
                   └───────────────────┬───────────────────┘
                                       ▼
                             TARGET API ENDPOINT
```

### Shield 1: Atomic Mutual Exclusion (Concurrency = 1)
- **Principle**: A free Google API key must NEVER have more than **one active HTTP request** in flight at any given millisecond.
- **Enforcement**: ACID SQLite transaction with `UPDATE ... RETURNING` leases. If a thread or process attempts to use a busy key, the lease manager rejects the request or queues it. Two processes can never acquire the same key simultaneously.

### Shield 2: Session Affinity (Anti-Hopping Pacing)
- **Problem**: Flipping to a new key on every segment (Key A -> Key B -> Key C in seconds from the same IP) exposes multi-key pooling heuristics at Google's edge.
- **Principle**: When a worker starts synthesizing or translating a scene, it acquires an **Affinity Lease** on Key $K$ and remains bound to Key $K$ for the entire scene (typically 8–15 segments).
- **Result**: To Google's analytics, the traffic pattern is identical to an individual engineer interactively developing in Google AI Studio.

### Shield 3: Anti-Correlation Key-Switch Cooldown
- **Principle**: When Key $A$ exhausts its quota or a scene finishes, switching to Key $B$ MUST be preceded by a **mandatory delay of 18.0 to 32.0 seconds**:
  $$T_{\text{cooldown}} \sim \text{Uniform}(18.0, 32.0)$$
- **Why It Matters**: This temporal gap breaks TCP/TLS connection grouping and prevents IP-level correlation across different Google accounts.

### Shield 4: Content-Aware Human Cadence & Director Breaks
Automated scripts fire requests continuously. Human sound designers do not. The cadence controller shapes inter-request latency:
$$T_{\text{wait}} = T_{\text{read}}(\text{words}) + T_{\text{review}}(\text{prev\_audio}) + T_{\text{jitter}}$$
1. **Reading Time**: Humans read text at 220–260 WPM ($3.5–4.5$ words/sec) before triggering generation:
   $$T_{\text{read}} = \min\left(12.0, \max\left(2.5, \frac{\text{word\_count}}{\text{wps}}\right)\right)$$
2. **Audio Review Time**: An engineer listens to 15%–35% of the preceding take:
   $$T_{\text{review}} = \min(15.0, \text{prev\_duration} \times \text{Uniform}(0.15, 0.35))$$
3. **Log-Normal Think Time**: Natural, fat-tailed pause distribution:
   $$T_{\text{jitter}} = \text{LogNormal}(\mu=1.2, \sigma=0.35) \quad (\text{clamped: } [1.5, 7.0]\text{s})$$
4. **Director Scene Review Breaks**: Every 12–16 segments, the engine pauses for **15.0 to 30.0 seconds** to simulate director script analysis.

### Shield 5: Conservative 75% Rate Limiting
- **Principle**: While Google lists 15 RPM for free Flash models, edge gateway timestamp rounding causes false 429s if you send at 14–15 RPM.
- **Enforcement**: Token bucket limiter throttles strictly at **11.0 RPM** (73% of maximum), enforcing a minimum interval of **3.5 seconds** between requests on the same key.

### Shield 6: Official SDK Header Emulation
- **Principle**: Strip all custom user agents (`AudiobookFactory/2.0`, Python urllib).
- **Signature**: Inject exact official Google GenAI Python SDK headers:
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
- **Principle**: When a provider edge failure occurs, naive scripts rapidly loop through all 100 keys in seconds, burning daily quotas.
- **Enforcement**: If **5 consecutive keys fail with HTTP 429 or 503 within 60 seconds**, the **Global Tripwire** activates:
  - All automated key rotation halts immediately.
  - The entire engine enters an **Emergency Quarantine of 45–60 seconds**.
  - Prevents pool-wide burnout.

---

## 3. Empirical Google Cloud & Gemini Model Catalog (Live Probed)

Direct probing of the live Google Cloud `v1beta/models` API with active credentials revealed 50 models. Below are the canonical production models and their operational contracts:

### 3.1 Primary Production Models

| Model ID | Quality Tier | Modality | Context Tokens | Max Output | Free RPM | Free TPM | Free RPD | Primary Production Room |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`gemini-3.8-flash`** | Flagship (Tier 1) | Text, Vision | 1,048,576 | 65,536 | 15 | 1,000,000 | 1,500 | Room 2 (Translation), Room 3 (Screenplay) |
| **`gemini-3.7-flash`** | Flagship (Tier 1) | Text, Vision | 1,048,576 | 65,536 | 15 | 1,000,000 | 1,500 | Room 3 (Attribution), Room 1 (DNA) |
| **`gemini-3.6-flash`** | Balanced (Tier 2) | Text, Vision | 1,048,576 | 32,768 | 15 | 1,000,000 | 1,500 | Room 1 (Extraction), Blocking QA |
| **`gemini-2.5-flash`** | Balanced (Tier 2) | Text, Vision | 1,048,576 | 32,768 | 15 | 1,000,000 | 1,500 | Secondary Fallback |
| **`gemini-2.5-pro`** | Flagship (Tier 1) | Text, Vision | 1,048,576 | 65,536 | **2** | **32,000** | **50** | **Quarantined**: Forensic Deep Audits Only |
| **`gemini-3.8-flash-tts`**| Flagship Audio | Audio Out | 8,192 | 16,384 | 15 | 500,000 | **10** | Room 4 (Vocal Speech Synthesis) |
| **`gemini-3.8-flash-lite-tts`**| Balanced Audio| Audio Out | 8,192 | 16,384 | 15 | 500,000 | **10** | Speech Fallback |
| **`gemini-3.1-flash-lite`**| Utility (Tier 3) | Text | 1,048,576 | 65,536 | 30 | 4,000,000 | 1,500 | Fast token counts, parsing |
| **`gemma-4-31b-it`** | Balanced (Tier 2) | Text | 262,144 | 32,768 | 30 | 500,000 | 1,500 | Local & Auxiliary text |
| **`lyria-3.5`** | Music/Audio | Audio Out | 1,048,576 | 65,536 | 5 | 100,000 | 50 | Sonic genome enrichment |

### 3.2 The Strict 10 RPD Speech Synthesis Invariant
`gemini-3.8-flash-tts` on Google AI Studio Free Tier has a **hard daily quota of 10 Requests Per Day (RPD) per key**:
- **Daily Fleet Production Budget**:
  $$100 \text{ keys} \times 10 \text{ RPD} = 1,000 \text{ mastered speech chunks / day}$$
- **Invariant**: Room 4 TTS must NEVER be called for exploratory prompt engineering. Dialogue text must be 100% frozen, audited, and gate-checked by Room 3 before invoking TTS.

---

## 4. The Critical Gemini 3.8 Thinking Token Pitfall & Real-World Fix

### 4.1 The Hidden Trap
During live API testing, sending a minimal prompt with `maxOutputTokens: 20` to `gemini-3.8-flash` resulted in:
```json
{
  "candidates": [
    {
      "content": {},
      "finishReason": "MAX_TOKENS",
      "index": 0
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 1,
    "thoughtsTokenCount": 22,
    "totalTokenCount": 23
  },
  "modelVersion": "gemini-3.8-flash"
}
```
**Why This Happened**:
1. In Gemini 3.x Flash models, internal reasoning tokens (`thoughtsTokenCount`) **eat directly into the `maxOutputTokens` budget**.
2. If `maxOutputTokens` is low (e.g., 1 or 20) and `thinkingBudget` is unconstrained, the model generates 22 thinking tokens, immediately exceeds the budget, and returns an **empty `content: {}`** with `finishReason: "MAX_TOKENS"`.
3. In legacy code, health pings sent `maxOutputTokens: 1` to probe model availability, causing continuous false-positive failures!

### 4.2 The Two-Pronged Solution
1. **For Health Pings & Utility Tasks**:
   Explicitly disable reasoning by passing `thinkingBudget: 0`:
   ```json
   "generationConfig": {
     "maxOutputTokens": 100,
     "thinkingConfig": {
       "thinkingBudget": 0
     }
   }
   ```
   This eliminates thinking overhead, yielding instantaneous responses with zero token waste.
2. **For High-Creativity Tasks (Translation & Screenplay)**:
   Allocate sufficient headroom and an explicit thinking budget:
   ```json
   "generationConfig": {
     "temperature": 0.85,
     "maxOutputTokens": 32768,
     "thinkingConfig": {
       "thinkingBudget": 1024
     }
   }
   ```
   If `finishReason: "MAX_TOKENS"` occurs, halve `thinkingBudget` to 512 and retry once. If it fails again, halt fail-closed.

---

## 5. Multi-User Shared-Workstation Lease Architecture

### 5.1 Architecture Overview
Multiple developers and processes operate on the same workstation:
$$\text{Identity} = \langle \text{workstation\_id}, \text{user\_id}, \text{process\_id}, \text{worker\_id}, \text{session\_id} \rangle$$

```text
User A (Terminal 1) ──┐
                      ├── SQLite WAL DB ──► [KeyLeaseManager] ──► Free Key Fleet
User B (Terminal 2) ──┘
```

### 5.2 SQLite Schema (`audiobooks/key_pool_state.db`)

```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;

-- Master Key Inventory
CREATE TABLE IF NOT EXISTS key_inventory (
    key_hash TEXT PRIMARY KEY,
    key_alias TEXT NOT NULL UNIQUE,          -- Safe public alias: 'key_a8f2'
    encrypted_key TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'gemini',
    tier TEXT NOT NULL DEFAULT 'free',
    allowed_services TEXT NOT NULL,          -- JSON: ["text", "tts"]
    status TEXT NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE, EXHAUSTED_TODAY, TEMP_BACKOFF, INVALID
    exhausted_date TEXT,                     -- YYYY-MM-DD (Pacific Date)
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
    lease_id TEXT PRIMARY KEY,
    key_hash TEXT NOT NULL,
    provider TEXT NOT NULL,
    workstation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    process_id INTEGER NOT NULL,
    worker_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    workload_type TEXT NOT NULL,             -- 'text' or 'tts'
    leased_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,           -- leased_at + 60s
    heartbeat_at TIMESTAMP NOT NULL,
    status TEXT NOT NULL,                    -- 'ACTIVE', 'RELEASED', 'EXPIRED', 'REVOKED'
    FOREIGN KEY(key_hash) REFERENCES key_inventory(key_hash)
);

CREATE INDEX IF NOT EXISTS idx_leases_active 
ON key_leases(key_hash, status, expires_at);

CREATE INDEX IF NOT EXISTS idx_leases_user 
ON key_leases(user_id, workload_type, status);

-- Audit Ledger (Zero Secrets)
CREATE TABLE IF NOT EXISTS key_audit_log (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    lease_id TEXT NOT NULL,
    key_alias TEXT NOT NULL,
    user_id TEXT NOT NULL,
    process_id INTEGER NOT NULL,
    model_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    duration_ms INTEGER,
    status_code INTEGER,
    error_summary TEXT
);
```

### 5.3 Atomic Lease Acquisition Query
```sql
BEGIN IMMEDIATE;

-- 1. Auto-expire leases past their TTL
UPDATE key_leases
SET status = 'EXPIRED'
WHERE status = 'ACTIVE' AND expires_at < CURRENT_TIMESTAMP;

-- 2. Find and lease the least-used available key in one atomic step
INSERT INTO key_leases (
    lease_id, key_hash, provider, workstation_id, user_id,
    process_id, worker_id, session_id, workload_type,
    leased_at, expires_at, heartbeat_at, status
)
SELECT 
    :lease_id, k.key_hash, k.provider, :workstation_id, :user_id,
    :process_id, :worker_id, :session_id, :workload_type,
    CURRENT_TIMESTAMP, datetime('now', '+60 seconds'), CURRENT_TIMESTAMP, 'ACTIVE'
FROM key_inventory k
WHERE k.provider = :provider
  AND k.status = 'ACTIVE'
  AND (k.backoff_until IS NULL OR k.backoff_until <= CURRENT_TIMESTAMP)
  AND NOT EXISTS (
      SELECT 1 FROM key_leases l
      WHERE l.key_hash = k.key_hash 
        AND l.status = 'ACTIVE'
        AND l.expires_at > CURRENT_TIMESTAMP
  )
ORDER BY k.last_used ASC NULLS FIRST, k.total_calls_today ASC
LIMIT 1;

COMMIT;
```

### 5.4 Crash Recovery: Dual Liveness Probe
If a process crashes via `SIGKILL` or power loss:
1. When any caller requests a lease, the manager inspects active leases.
2. For each lease, it checks local OS process tables: `os.kill(process_id, 0)` (POSIX) or `OpenProcess` (Windows).
3. If the process is dead, the lease is instantly marked `EXPIRED`, and the key is freed immediately without waiting for the 60s TTL.

---

## 6. Core Module Specifications & Code Contracts

The new unified architecture resides in `audiobook_factory/core/models/`:

```text
audiobook_factory/
└── core/
    └── models/
        ├── __init__.py           # Unified exports
        ├── gateway.py            # ModelGateway: High-level entry point for all rooms
        ├── registry.py           # ModelRegistry: Immutable capabilities & quality tiers
        ├── lease_manager.py      # KeyLeaseManager: ACID SQLite lease engine
        ├── anti_ban_guard.py     # AntiBanGuard: Cadence shaper, anti-correlation, tripwire
        ├── policy_engine.py      # PolicyEngine: Error classifier, circuit breaker, rate limiter
        ├── router.py             # RequestRouter: Task requirements -> Execution plan
        └── adapters/
            ├── base.py           # BaseProviderAdapter interface
            ├── gemini.py         # GeminiProviderAdapter (REST, headers, thinking, audio)
            ├── openai_compat.py  # Cerebras, Groq, OpenAI, OpenRouter adapter
            └── local_gpu.py      # Local CUDA VRAM guard & MMS aligner adapter
```

### 6.1 `ModelGateway` Unified Interface
Every consumer subsystem uses this clean interface:

```python
class ModelGateway:
    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        task: TaskType = TaskType.UTILITY,
        response_schema: Optional[Dict[str, Any]] = None,
        thinking_budget: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Any:
        """Executes text generation adhering to task quality floor and anti-ban guards."""
        ...

    def synthesize_speech(
        self,
        text: str,
        voice: str,
        output_path: Path,
        emotion: str = "neutral",
        acting_directive: Optional[Any] = None,
    ) -> Path:
        """Synthesizes speech adhering to 10 RPD ceiling, SNR verification, and cadence."""
        ...

    @contextlib.contextmanager
    def lease_session(self, task: TaskType, workload: str = "text") -> Generator[ModelSession, None, None]:
        """Context-managed multi-turn session holding single-key affinity for an entire scene."""
        ...
```

---

## 7. Step-by-Step Implementation Checklist & Bug Prevention Playbook

### Phase P0: Foundational Safety & Key Leasing (Immediate)
- [ ] **Step 1: Database Initialization**
  - Create `key_inventory`, `key_leases`, and `key_audit_log` tables in `audiobooks/key_pool_state.db`.
  - Enable `PRAGMA journal_mode = WAL;` and `PRAGMA busy_timeout = 5000;`.
- [ ] **Step 2: KeyLeaseManager Implementation**
  - Implement atomic `acquire_lease()` with SQLite `IMMEDIATE` transaction.
  - Implement `renew_lease()` heartbeat (every 15s) and `release_lease()`.
  - Implement PID liveness probe (`os.kill(pid, 0)`) for instant crash recovery.
  - Enforce "One User = One Active Key per Workload".
- [ ] **Step 3: AntiBanGuard Implementation**
  - Implement `calculate_human_delay(text, prev_dur)` with Log-Normal jitter.
  - Implement `wait_for_key_switch()` enforcing 18–32s anti-correlation delay.
  - Implement 5-failure emergency pool tripwire (45s quarantine).
  - Enforce 11 RPM conservative rate limit.
- [ ] **Step 4: Zero-Secret Hardening**
  - Replace all log occurrences of `key[:6]...key[-4:]` with cryptographic alias `key_xxxx`.
  - Ensure `.env` is created with permissions `chmod 600`.

### Phase P1: Model Registry & Polymorphic Adapters
- [ ] **Step 5: ModelRegistry Implementation**
  - Register canonical specs for all 50 discovered Gemini models.
  - Map quality tiers (`TIER_1_FLAGSHIP`, `TIER_2_BALANCED`, `TIER_3_UTILITY`).
  - Configure `thinkingConfig: {"thinkingBudget": 0}` default for ping/utility tasks.
- [ ] **Step 6: GeminiProviderAdapter Implementation**
  - Inject authentic `google-genai-sdk-python/0.8.3` headers.
  - Support `BLOCK_NONE` safety framing on dramatic fiction tasks.
  - Support inline base64 WAV audio decoding for `gemini-3.8-flash-tts`.

### Phase P2: Gateway Facade & Backward Compatibility
- [ ] **Step 7: Facade Wiring**
  - Wrap `ModelGateway` around existing legacy functions `call_gemini`, `call_model`, `get_persistent_key_pool()`, and `get_model_manager()`.
  - Run regression test suite:
    ```bash
    python3 -m unittest tests/test_universal_key_pool_and_guard_shield.py
    python3 -m unittest tests/test_model_manager_and_strict_halt.py
    ```
- [ ] **Step 8: Multi-Process Concurrency Verification**
  - Create `tests/test_multi_user_lease_concurrency.py` simulating 10 parallel processes across 2 user IDs, verifying 0% double-leases.

---
*End of Engineering Guide. Authorized by Antigravity Studio Architecture Board.*
