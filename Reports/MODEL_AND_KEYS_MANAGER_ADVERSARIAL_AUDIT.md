# Model & Keys Manager: Comprehensive Forensic Audit & Adversarial Architecture Blueprint

- **Document Version**: 1.0.0
- **Target Project**: `audiobook-studio` (`audiobook_factory`)
- **System**: Studio Audiobook Production Engine (Pure Vocals-Only)
- **Target Workstation Context**: Shared PC Workstation (Multiple concurrent users & workers)
- **Author**: Antigravity Principal Systems Architect & Security Auditor
- **Date**: October 2026

---

## Executive Summary

The **Model & Keys Manager** is the foundational infrastructure upon which the entire 5-room audiobook pipeline operates. Every creative stage—forensic PDF parsing, literary Hindustani translation, screenplay dialogue attribution, 4D acoustic formant speech synthesis, and broadcast EBU R128 mastering—relies on uninterrupted, high-intelligence model inference and sustainable API key throughput.

This forensic audit and architectural blueprint:
1. Conducts an exhaustive code-level inspection of the current implementation (`key_manager.py`, `model_manager.py`, `guard_shield.py`, `llm_client.py`, `tts/dispatcher.py`, `tts/providers/gemini.py`, and `cadence.py`).
2. Evaluates the foundational architectural choice: **One Unified System (A) vs. Multiple Independent Subsystems (B) vs. One Shared Core with Specialized Internal Modules (C)**.
3. Designs a bulletproof **Key Lease & Reservation Engine** built for multiple human users and background workers sharing a single physical workstation, enforcing an atomic **One User = One Active Key** discipline without disrupting legitimate multi-stage workflows.
4. Introduces a canonical **Model Registry & Capability Matrix**, eliminating hardcoded provider URLs and opaque strings.
5. Formulates a rigorous **Adversarial Solution Loop** across 7 catastrophic failure modes (process crashes, thundering herds, retry cascades, zombie locks, key poisoning, and split-brain rollovers).
6. Outlines a **Zero-Secret Security Hardening Plan** and provides a phased, non-breaking **P0/P1/P2 Migration Roadmap**.

---

## 1. Forensic Assessment of Current Implementation

A thorough line-by-line inspection of the existing codebase reveals serious architectural drift, duplicated responsibilities, and concurrency vulnerabilities.

### 1.1 Existing Architecture Map & Code Locations

```text
audiobook_factory/
├── key_manager.py          (642 lines: PersistentKeyPool, SQLite key_quota_ledger & model_quota_ledger)
├── model_manager.py        (418 lines: ModelManager, ModelTier, TaskType, dynamic REST discovery)
├── guard_shield.py         (532 lines: ModelQuotaProfile, CircuitBreaker, HardwareVRAMGuard, error classifier)
├── llm_client.py           (629 lines: call_gemini, call_model, custom retry & backoff loops)
├── tts/rate_limiter.py     (218 lines: TokenBucketRateLimiter, RPM/TPM tracking)
├── tts/providers/gemini.py (852 lines: synthesize_gemini_tts, isolated 15-key rotation loop)
└── cadence.py              (222 lines: HumanCadenceController, get_stealth_sdk_headers)
```

### 1.2 Critical Flaws in Current State

#### A. Race Conditions & Non-Atomic Key Allocation
In `key_manager.py`:
- `get_key()` executes a `SELECT ... ORDER BY in_flight ASC, last_used ASC LIMIT 1`, updates `last_used` and `total_calls_today`, and returns the raw string `api_key`.
- The `in_flight` counter is only incremented if the caller wraps execution in `lease_key()`.
- **The Reality**: Neither `llm_client.py` nor `tts/providers/gemini.py` uses `lease_key()`! Both call `pool.get_key()` directly. Consequently, `in_flight` remains `0` at all times in production.
- If two processes or threads request a key within the same transaction window, SQLite returns the exact same key to both callers, causing instantaneous thread dogpiling and immediate HTTP 429 bursts.

#### B. Complete Absence of User, Process, or Worker Identity
- The SQLite tables (`key_quota_ledger`, `model_quota_ledger`) have no columns for `user_id`, `pid`, `worker_id`, or `lease_id`.
- On a shared workstation, User A running Chapter 1 and User B running Chapter 2 share the same database file (`audiobooks/key_pool_state.db`). The system has no way of knowing who holds what key, making the requirement *"One user should have one active key"* completely unenforceable.

#### C. Zombie Leases & Permanent In-Flight Leakage
- In `lease_key()`, `in_flight` is decremented in a Python `finally` block. If a process experiences a hard crash (`SIGKILL`, segmentation fault, out-of-memory kill by the OS, or sudden terminal closure), the `finally` block **never executes**.
- Without lease expiration timestamps (`expires_at`), heartbeats, or PID liveness probes, `in_flight` remains permanently elevated, permanently poisoning the key from being selected by round-robin queries.

#### D. Three Fragmented, Competing Rate Limiting Engines
Rate limiting logic is split across three unconnected subsystems:
1. `guard_shield.py`: Defines static `ModelQuotaProfile` objects with RPM, TPM, and RPD limits.
2. `key_manager.py`: Implements database-level `TEMP_BACKOFF` sleep intervals on HTTP 429.
3. `tts/rate_limiter.py`: Implements an in-memory `TokenBucketRateLimiter` with mutexes.
None of these three components communicate with one another. A key cooling down in `key_manager.py` is unknown to `TokenBucketRateLimiter`.

#### E. Hardcoded Gemini-Centric Model Manager
`model_manager.py` claims to be a universal model intelligence manager, but its internals are 100% hardcoded to Google Gemini:
- Discovers models exclusively via `https://generativelanguage.googleapis.com/v1beta/models?key={key}`.
- Pings candidates by posting `{"contents": [{"parts": [{"text": "ping"}]}]}` to Gemini endpoints.
- Unaware of Cerebras, Groq, OpenAI, Anthropic, ElevenLabs, or Local CUDA models. Multi-provider routing is implemented as an afterthought inside `llm_client.py`'s `call_model` function.

#### F. Plaintext Secret Storage & Entropy Exposure
- `key_quota_ledger.api_key` stores raw API keys in plaintext in SQLite. On a multi-user Linux/Windows machine, any user or script with read access to the directory can dump all 120+ team keys.
- Key logging exposes `f"{key[:6]}...{key[-4:]}"`. For Google AI Studio keys (`AIzaSy...`), the first 6 characters are identical for every key in the world, and exposing the last 4 characters reveals substantial entropy.

---

## 2. First Architectural Question: A vs B vs C

### Evaluation of Options

| Architectural Model | Coupling | Testability | Failure Isolation | Operational Overhead | Multi-User Suitability | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Option A: One Unified Monolith** | Extreme | Poor | Fatal (single crash halts all) | Low | Flawed | **REJECTED** |
| **Option B: Multiple Independent Subsystems** | None | High | High | High (glue duplication) | Poor (state fragmentation) | **REJECTED** |
| **Option C: Shared Core with Specialized Modules** | Low (decoupled) | Excellent | High | Balanced | Ideal | **RECOMMENDED** |

### Why Option C is the Superior Architecture
- **Option A** violates the Single Responsibility Principle. Merging API rate limiting, SQLite lease acquisition, model capability indexing, HTTP request generation, and audio synthesis into a single giant class creates an unmaintainable monolith.
- **Option B** leads to orchestration sprawl. Subsystems across the studio (Translator, Screenplay Director, TTS Dispatcher, Dramaturge) would each have to orchestrate 5 separate libraries (`Registry.resolve() -> KeyPool.lease() -> RateLimiter.wait() -> Router.select() -> Adapter.execute()`). This is precisely why the current codebase has duplicate retry loops in `llm_client.py` and `gemini.py`.
- **Option C (Shared Core with Specialized Modules)** provides **one unified facade** (`ModelGateway`) to consumer subsystems, while delegating internally to cleanly separated, independently testable, swappable components.

```text
                                CONSUMER SUBSYSTEMS
           (Translation Room 2, Screenplay Room 3, Vocal TTS Room 4, Mastering Room 5)
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │     MODEL & KEYS CONTROL PLANE    │
                     │          (ModelGateway)           │
                     └─────────────────┬─────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
┌───────────────┐              ┌───────────────┐              ┌───────────────┐
│ ModelRegistry │              │KeyLeaseManager│              │ PolicyEngine  │
│ - Capabilities│              │ - ACID SQLite │              │ - Rate Limits │
│ - Quality Tier│              │ - User & PID  │              │ - Circuit Brk │
│ - Context Win │              │ - Heartbeats  │              │ - Quota Reset │
└───────┬───────┘              └───────┬───────┘              └───────┬───────┘
        │                              │                              │
        └──────────────────────────────┼──────────────────────────────┘
                                       │
                                       ▼
                             ┌───────────────────┐
                             │   RequestRouter   │
                             │ (Execution Plan)  │
                             └─────────┬─────────┘
                                       │
                                       ▼
                             ┌───────────────────┐
                             │ Provider Adapters │
                             │(Gemini, OAI, GPU) │
                             └───────────────────┘
```

---

## 3. Multi-User Shared-Workstation Key Architecture

### 3.1 Workstation Context & Requirements
On a shared workstation, multiple developers and background processes operate simultaneously:
- Developer 1 tests a translation prompt in the terminal.
- Developer 2 runs an acoustic vocal test.
- A background worker runs Chapter 3 batch mastering.
- An interactive Antigravity IDE agent runs in the background.

The system must guarantee:
1. **Zero Accidental Concurrency on Free Keys**: A single free Google API key must never be used concurrently by multiple users or workers unless explicitly allowed by key configuration.
2. **Process Crash Recovery**: If a user's terminal closes or a process crashes with `SIGKILL`, held keys must automatically return to the pool within a bounded timeout.
3. **Atomic Mutual Exclusion**: Even under extreme thundering-herd conditions (e.g., 20 threads starting at the same millisecond), no key can be double-leased.

### 3.2 Identity Tuple Specification
Every lease request must declare its caller identity:

$$\text{CallerIdentity} = \langle \text{workstation\_id}, \text{user\_id}, \text{process\_id}, \text{worker\_id}, \text{session\_id} \rangle$$

- `workstation_id`: Machine hostname or workstation GUID (`WORKSTATION_ID`).
- `user_id`: System login username (`os.getlogin()`, `$USER`, or `$USERNAME`).
- `process_id`: OS process ID (`os.getpid()`).
- `worker_id`: Thread ID or Celery/Subprocess worker tag (`threading.get_ident()`).
- `session_id`: Unique workflow run ID (e.g. `run_chapter_003_hi`).

### 3.3 ACID SQLite Lease Table Schema

```sql
CREATE TABLE IF NOT EXISTS key_leases (
    lease_id TEXT PRIMARY KEY,               -- UUIDv4
    key_hash TEXT NOT NULL,                  -- SHA-256 (truncated to 16 hex chars)
    provider TEXT NOT NULL,                  -- gemini, openai, cerebras, local
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

CREATE INDEX IF NOT EXISTS idx_leases_active 
ON key_leases(key_hash, status, expires_at);

CREATE INDEX IF NOT EXISTS idx_leases_user 
ON key_leases(user_id, workload_type, status);
```

### 3.4 Atomic Lease Acquisition (SQL)
To prevent race conditions without table-level file locking, acquisitions use SQLite's `BEGIN IMMEDIATE` transaction:

```sql
-- Step 1: Reclaim stale leases past their expiration
UPDATE key_leases
SET status = 'EXPIRED'
WHERE status = 'ACTIVE' AND expires_at < CURRENT_TIMESTAMP;

-- Step 2: Select the least-used, non-busy key matching compatibility
SELECT k.key_hash, k.encrypted_key, k.key_alias
FROM key_inventory k
WHERE k.provider = :provider
  AND k.status = 'ACTIVE'
  AND (k.backoff_until IS NULL OR k.backoff_until <= CURRENT_TIMESTAMP)
  AND (
      -- Key is not currently leased by anyone
      NOT EXISTS (
          SELECT 1 FROM key_leases l
          WHERE l.key_hash = k.key_hash 
            AND l.status = 'ACTIVE'
            AND l.expires_at > CURRENT_TIMESTAMP
      )
  )
ORDER BY k.last_used ASC NULLS FIRST, k.total_calls_today ASC
LIMIT 1;

-- Step 3: Atomically insert the lease
INSERT INTO key_leases (
    lease_id, key_hash, provider, workstation_id, user_id,
    process_id, worker_id, session_id, workload_type,
    leased_at, expires_at, heartbeat_at, status
) VALUES (
    :lease_id, :chosen_key_hash, :provider, :workstation_id, :user_id,
    :process_id, :worker_id, :session_id, :workload_type,
    CURRENT_TIMESTAMP, datetime('now', '+60 seconds'), CURRENT_TIMESTAMP, 'ACTIVE'
);
```

---

## 4. Key Pool vs Permanent Assignment: Comparative Analysis

| Dimension | A: Permanent Assignment | B: Pure Ephemeral Pool | C: Hybrid Affinity Leases (Recommended) |
| :--- | :--- | :--- | :--- |
| **Fairness** | Poor (static allocation causes idle waste) | High (first come, first served) | **Optimal (balanced allocation with session affinity)** |
| **Idle Key Waste** | High (idle developer locks keys) | Zero | **Zero (idle timeout releases keys automatically)** |
| **Crash Resilience** | None (manual admin required) | High | **Autonomous (TTL + PID heartbeat sweep)** |
| **IP / Key Churn** | Minimal | Extreme (every request hops keys) | **Controlled (steady cadence per chapter/scene)** |
| **Team Scalability** | Low (requires manual provisioning) | High | **High (automatic onboarding)** |

### Final Recommendation: Hybrid Affinity Leases
1. **Dynamic Acquisition**: When a user begins a task, the manager acquires an eligible key and issues a **Lease Token**.
2. **Session Affinity**: The lease remains bound to that user and session for the duration of the scene/batch with a rolling **60-second idle TTL**.
3. **Graceful Release**: When the batch completes or after 60 seconds of inactivity, the lease transitions to `RELEASED`.
4. **Mandatory Cooldown**: Released keys undergo a **5-second safety cooldown** before another user can claim them, decoupling traffic patterns at Google's edge.

---

## 5. One User = One Active Key Policy Analysis

### 5.1 Granularity of Enforcement
Enforcing *"One User = One Active Key"* strictly at the user level would break legitimate production workflows.
- A user generating audio needs a **Text Model** for dialogue attribution QA and a **TTS Model** for audio synthesis.
- Both operations run in parallel in the pipeline.

### 5.2 The 2-Dimensional Policy Boundary
Enforcement is applied at the tuple level:

$$\text{Enforcement Boundary} = \langle \text{user\_id}, \text{provider}, \text{workload\_type} \rangle$$

- `workload_type` $\in \{\text{"text"}, \text{"tts"}\}$.
- A single user may hold:
  - At most **1 active key** for Google Gemini **Text Generation**.
  - At most **1 active key** for Google Gemini **TTS Speech Synthesis**.
  - At most **1 active key** for Cerebras/Groq auxiliary extraction.

### 5.3 Legitimate Exceptions & Handshake Rules
1. **Provider Outage / Hard 429 Rollover**: If a held key exhausts its quota mid-turn, the manager explicitly marks the active lease as `REVOKED_EXHAUSTED` and atomically provisions the next available key.
2. **Explicit Parallel Batch Jobs**: If a developer launches a multi-threaded render (e.g. `--concurrency 4`), they must provide an explicit CLI token: `--allow-multi-lease --max-leases 4`. Without this explicit flag, the manager strictly rejects concurrent acquisition requests with a typed `KeyLeaseQuotaExceededError`.

---

## 6. Central Model Registry Design

The Model Registry serves as the **immutable single source of truth** for model capabilities across all supported providers.

```python
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import List, Optional, Dict, Any

class ModelTier(IntEnum):
    TIER_1_FLAGSHIP = 1    # Deep literary reasoning, drama subtext
    TIER_2_BALANCED = 2    # Standard production, balanced speed/nuance
    TIER_3_UTILITY = 3     # High-speed parsing, normalization

class Modality(str, Enum):
    TEXT = "text"
    AUDIO_OUT = "audio_out"
    AUDIO_IN = "audio_in"
    VISION = "vision"

@dataclass(frozen=True)
class ModelCapability:
    model_id: str
    provider: str
    family: str
    tier: ModelTier
    modalities: List[Modality]
    context_window_tokens: int
    max_output_tokens: int
    supports_structured_json: bool
    supports_thinking_budget: bool
    supports_system_instruction: bool
    recommended_tasks: List[str]
    input_cost_per_million: float = 0.0
    output_cost_per_million: float = 0.0
    rate_limit_rpm_free: float = 15.0
    rate_limit_rpd_free: int = 1500
    is_deprecated: bool = False
```

### Canonical Registry Catalog (Initial State)

```python
CANONICAL_MODEL_REGISTRY: Dict[str, ModelCapability] = {
    # Flagship Google Gemini Text Models
    "gemini-3.8-flash": ModelCapability(
        model_id="gemini-3.8-flash", provider="gemini", family="gemini-3",
        tier=ModelTier.TIER_1_FLAGSHIP, modalities=[Modality.TEXT, Modality.VISION],
        context_window_tokens=1_048_576, max_output_tokens=65_536,
        supports_structured_json=True, supports_thinking_budget=True,
        supports_system_instruction=True,
        recommended_tasks=["translation", "screenplay", "dramaturgy"],
        rate_limit_rpm_free=15.0, rate_limit_rpd_free=1500,
    ),
    "gemini-3.7-flash": ModelCapability(
        model_id="gemini-3.7-flash", provider="gemini", family="gemini-3",
        tier=ModelTier.TIER_1_FLAGSHIP, modalities=[Modality.TEXT, Modality.VISION],
        context_window_tokens=1_048_576, max_output_tokens=65_536,
        supports_structured_json=True, supports_thinking_budget=True,
        supports_system_instruction=True,
        recommended_tasks=["translation", "screenplay", "directing"],
        rate_limit_rpm_free=15.0, rate_limit_rpd_free=1500,
    ),
    # Dedicated Speech Models
    "gemini-3.8-flash-tts": ModelCapability(
        model_id="gemini-3.8-flash-tts", provider="gemini", family="gemini-3",
        tier=ModelTier.TIER_1_FLAGSHIP, modalities=[Modality.TEXT, Modality.AUDIO_OUT],
        context_window_tokens=32_768, max_output_tokens=8_192,
        supports_structured_json=False, supports_thinking_budget=False,
        supports_system_instruction=False,
        recommended_tasks=["tts"],
        rate_limit_rpm_free=15.0, rate_limit_rpd_free=10,
    ),
    # High-Velocity Inference Providers
    "llama3.3-70b": ModelCapability(
        model_id="llama3.3-70b", provider="cerebras", family="llama-3",
        tier=ModelTier.TIER_2_BALANCED, modalities=[Modality.TEXT],
        context_window_tokens=128_000, max_output_tokens=8_192,
        supports_structured_json=True, supports_thinking_budget=False,
        supports_system_instruction=True,
        recommended_tasks=["extraction", "auditing", "utility"],
        rate_limit_rpm_free=30.0, rate_limit_rpd_free=14400,
    ),
}
```

---

## 7. Task-Based Routing & Capability Matching

Subsystems should request **capabilities and quality constraints**, not hardcoded model names.

```python
@dataclass
class RoutingRequirement:
    task: str                        # "translation", "tts", "extraction"
    min_tier: ModelTier = ModelTier.TIER_2_BALANCED
    required_modalities: List[Modality] = field(default_factory=lambda: [Modality.TEXT])
    requires_json_schema: bool = False
    requires_thinking: bool = False
    preferred_provider: Optional[str] = None
    force_model: Optional[str] = None

class RequestRouter:
    def __init__(self, registry: ModelRegistry, key_manager: KeyLeaseManager):
        self.registry = registry
        self.key_manager = key_manager

    def resolve_execution_plan(self, req: RoutingRequirement, identity: CallerIdentity) -> ExecutionPlan:
        # 1. Filter models matching capability requirements
        candidates = self.registry.filter_candidates(
            min_tier=req.min_tier,
            modalities=req.required_modalities,
            requires_json=req.requires_json_schema,
            requires_thinking=req.requires_thinking,
            provider=req.preferred_provider,
            force_model=req.force_model,
        )
        if not candidates:
            raise NoEligibleModelError(f"No models satisfy requirement for task '{req.task}'")

        # 2. Match candidate models against available healthy keys
        plan = self.key_manager.find_and_lease_compatible(candidates, identity)
        return plan
```

---

## 8. Provider Adapters & Execution Contract

Consumer subsystems interact solely with the common interface. Provider-specific nuances (headers, payload formats, error responses) remain encapsulated within dedicated adapters.

```python
from abc import ABC, abstractmethod

class BaseProviderAdapter(ABC):
    @abstractmethod
    def generate_text(self, request: ModelRequest, api_key: str) -> ModelResponse:
        pass

    @abstractmethod
    def synthesize_speech(self, request: SpeechRequest, api_key: str) -> SpeechResponse:
        pass

    @abstractmethod
    def normalize_error(self, error: Exception, status_code: int, response_body: str) -> NormalizedError:
        pass
```

### Supported Adapters:
1. `GeminiProviderAdapter`: REST payload construction, official SDK header emulation (`get_stealth_sdk_headers`), thinkingConfig injection, audio PCM extraction, and EBU R128 audio safety parsing.
2. `OpenAICompatibleAdapter`: Standardized JSON schema completions for Cerebras, Groq, OpenAI, and OpenRouter.
3. `LocalGpuAdapter`: CUDA VRAM lock acquisition (`HardwareVRAMGuard`) and subprocess invocation for local models.

---

## 9. Comprehensive Failure, Fallback & Circuit Breaker Logic

The system distinguishes between **Key-Specific**, **Model-Specific**, and **Provider-Specific** failures:

```text
                                  FAILURE OCCURRED
                                         │
       ┌─────────────────────────────────┼─────────────────────────────────┐
       ▼                                 ▼                                 ▼
[HTTP 401 / 403 / 429 Daily]      [HTTP 503 / 504 / 400 Payload]       [Provider Outage / DNS]
   KEY-SPECIFIC FAILURE               MODEL-SPECIFIC FAILURE            PROVIDER-SPECIFIC FAILURE
       │                                 │                                 │
       ▼                                 ▼                                 ▼
1. Mark Key EXHAUSTED_TODAY       1. Do NOT burn key quota          1. Trip Provider Circuit Breaker
2. Release Lease (REVOKED)        2. Invalidate Model Cache         2. Switch to Backup Provider
3. Acquire Next Eligible Key      3. Rotate to Next Model in Tier   3. Fallback to Antigravity Handoff
4. Retry Request on New Key       4. Retry Request on Same Key      4. Strict Fail-Closed if No Backup
```

---

## 10. Observability & Zero-Secret Audit Trail

### Strict Security Rules:
1. **Zero Secret Logging**: The manager never writes raw API keys to logs, telemetry, error messages, or terminal outputs.
2. **Deterministic Cryptographic Key Aliases**: Every key is assigned a permanent, non-reversible public alias:
   $$\text{KeyAlias} = \text{"key\_"} + \text{SHA256}(\text{key} + \text{SALT})[:8]$$
   Logs output `key_4f8a` instead of `AIzaSy...`.
3. **Structured Audit Trail**: Every lease acquisition, renewal, release, and failure is recorded in SQLite:

```sql
CREATE TABLE IF NOT EXISTS key_audit_log (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,         -- ACQUIRE, RENEW, RELEASE, EXPIRE, 429_REVOKE
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

---

## 11. Adversarial Solution Loop (Attacking & Hardening the Architecture)

Before implementing the proposed design, we perform an adversarial stress test across 7 catastrophic failure modes.

### Attack Loop 1: The Multi-User Race Condition (Thundering Herd)
- **Problem**: 10 parallel processes across 3 users simultaneously request a key when only 1 key is currently active and available.
- **Proposed Fix**: Run a `SELECT ... WHERE status = 'ACTIVE' LIMIT 1`, then execute `INSERT INTO key_leases`.
- **Attack the Fix**: Between the `SELECT` and `INSERT`, another thread executes the same `SELECT`. Both see the key as available. Both insert a lease. Both use the key at the exact same millisecond. Concurrency violated!
- **Counterexample**: Two Python scripts executing in separate OS processes reading the SQLite file concurrently.
- **Improved Fix**: Wrap acquisition in `BEGIN IMMEDIATE;` transaction. SQLite permits only one writer.
- **Attack the Improved Fix**: SQLite with `PRAGMA busy_timeout=5000` under heavy concurrency raises `sqlite3.OperationalError: database is locked` if a long read blocks the writer.
- **Final Hardened Solution**:
  1. Set SQLite `PRAGMA journal_mode = WAL;` (writers do not block readers, readers do not block writers).
  2. Implement an exponential backoff retry loop with random jitter specifically for SQLite lock contention (5 retries with 50-200ms jitter).
  3. Use an atomic `UPDATE ... RETURNING` pattern:
     ```sql
     UPDATE key_inventory
     SET is_leased = 1, last_used = CURRENT_TIMESTAMP
     WHERE key_hash = (
         SELECT key_hash FROM key_inventory
         WHERE is_leased = 0 AND status = 'ACTIVE'
         ORDER BY last_used ASC NULLS FIRST LIMIT 1
     )
     RETURNING key_hash, key_alias;
     ```
     This executes in a single atomic SQLite bytecode step, making double-allocation mathematically impossible.

---

### Attack Loop 2: The Zombie Worker Crash & Orphaned Lease Deadlock
- **Problem**: User A starts Chapter 3 mastering. The key is leased. User A's terminal is killed via `kill -9` (or out-of-memory kill). The lease remains marked `status = 'ACTIVE'`. User B cannot use the key.
- **Proposed Fix**: Add `expires_at = datetime.now() + 60s`. If `expires_at < now()`, treat the lease as expired.
- **Attack the Fix**: What if User A is performing a legitimate 90-second long-form batch synthesis? At second 60, the lease expires. User B claims the key. At second 65, User A's request finishes and makes another call on the key. Now User A and User B are hammering the key concurrently!
- **Counterexample**: A high-subtext screenplay generation call taking 75 seconds on Gemini 3.8 Flash.
- **Improved Fix**: Introduce a background heartbeat thread that renews the lease every 15 seconds as long as the process is alive.
- **Attack the Improved Fix**: The Python process crashed, but the background thread got stuck in an unkillable socket read, continuing to heartbeat an invalid request. Or the machine hibernated, freezing system time.
- **Final Hardened Solution**:
  1. **Dual Liveness Probe**: A lease is valid if and only if:
     $$\text{expires\_at} > \text{NOW}() \quad \text{AND} \quad \text{is\_pid\_alive}(\text{process\_id})$$
  2. The manager checks local OS process tables (`os.kill(pid, 0)` on POSIX / `OpenProcess` on Windows) to verify the process actually exists. If the PID is dead, the lease is instantly declared orphaned and reclaimed immediately, without waiting for the 60-second TTL to expire.
  3. Long-running calls acquire an extended lease explicitly via lease parameter (`ttl_seconds=180.0`).

---

### Attack Loop 3: The Greedy User Monopolization & Starvation Attack
- **Problem**: User A writes a Python script that loops 50 times in parallel threads, requesting 50 leases. All 120 keys in the pool are seized by User A. User B gets `AllKeysExhaustedTodayError`.
- **Proposed Fix**: Set a hard cap of 1 key per user.
- **Attack the Fix**: User A legitimately needs 1 key for Text Translation and 1 key for Speech Synthesis. A strict cap of 1 key breaks the entire audiobook factory pipeline!
- **Counterexample**: The `standalone_pipeline.py` runs translation and audio generation concurrently.
- **Improved Fix**: Allow 1 key per workload type (`text` vs `tts`).
- **Attack the Improved Fix**: User A runs 5 terminal windows with 5 different script names under the same OS user account, claiming 5 keys.
- **Final Hardened Solution**:
  1. Enforce a **Per-User Quota Gate**:
     $$\text{ActiveLeases}(\text{user\_id}, \text{provider}) \le \text{MAX\_USER\_CONCURRENCY} \quad (\text{default: 2})$$
  2. If a user exceeds the concurrency limit, subsequent requests are placed into a FIFO priority queue with a maximum wait timeout (30 seconds). If no key frees up, the manager raises `UserConcurrencyLimitExceededError` instead of starving the rest of the workstation.

---

### Attack Loop 4: The 429 Cascade & Rapid Retry Death Spiral
- **Problem**: Key 1 hits a daily quota limit (HTTP 429). The system rotates to Key 2. Key 2 hits a daily quota limit. The loop rapidly rotates through all 120 keys in 4 seconds, marking every key in the database `EXHAUSTED_TODAY`. Production is halted even though keys were merely experiencing temporary RPM rate limits.
- **Proposed Fix**: Use `classify_universal_api_error` to distinguish between daily quotas and RPM limits.
- **Attack the Fix**: Google Gemini API error messages for rate limits change subtly between model versions (e.g., `"RESOURCE_EXHAUSTED"` without specifying whether it is daily or per-minute). A classifier mistaking an RPM burst for a daily quota permanently burns active keys for 24 hours!
- **Counterexample**: Google Gemini 3.8 Flash preview returning HTTP 429 with `Quota exceeded for quota metric 'Queries' and limit 'QUOTA_FOR_CORE_SERVICES'`.
- **Improved Fix**: Never mark a key `EXHAUSTED_TODAY` on the first 429. Require two consecutive 429s with explicit daily quota signatures.
- **Final Hardened Solution**:
  1. **Conservative Quota Quarantine**:
     - On first 429: Apply a short exponential backoff (`TEMP_BACKOFF` for 15s to 30s).
     - Only if the error body explicitly contains `"generaterequestsperday"` or `"perday"` or `"insufficient_quota"` is the key marked `EXHAUSTED_TODAY`.
  2. **Circuit Breaker Tripwire**: If 5 keys consecutively fail within 60 seconds, trip the **Global Pool Circuit Breaker**. Halt automatic rotation, log a critical alert, and wait 30 seconds before attempting further calls, completely stopping the death spiral.

---

### Attack Loop 5: Incompatible Model-Key Assignment & Silent Poisoning
- **Problem**: Key 12 is a free tier key with Gemini text access, but no quota for Gemini Flash TTS. The scheduler assigns Key 12 to a TTS batch. Key 12 fails with HTTP 403 or 429. The scheduler marks Key 12 as exhausted for ALL models, breaking text translation tasks that could have used Key 12 successfully.
- **Proposed Fix**: Track quota per (key, model) in `model_quota_ledger`.
- **Attack the Fix**: The scheduler still attempts to assign Key 12 to TTS on every run, failing repeatedly until it gets marked.
- **Final Hardened Solution**:
  1. **Static Capability Filtering Before Dynamic Allocation**:
     - Key metadata records `allowed_services` (e.g. `['text']` vs `['text', 'tts']`).
     - A key without TTS entitlement is filtered out during the SQL query for TTS requests. It is never probed or assigned for TTS, preventing failure cascades.

---

### Attack Loop 6: The Circuit Breaker Flapping & False Failure Cascade
- **Problem**: A transient Wi-Fi blip causes 3 consecutive network timeouts. The circuit breaker trips for `gemini-3.8-flash`. All subsequent translation jobs fail immediately or downgrade to an inferior model, violating the minimum quality floor.
- **Proposed Fix**: Set circuit breaker threshold to 5 failures.
- **Attack the Fix**: Network recovers 2 seconds later, but the circuit breaker remains open for the 60-second cooldown period, stalling production.
- **Final Hardened Solution**:
  1. Implement a **HALF-OPEN Canary State**:
     - After 10 seconds of cooldown, the circuit breaker enters `HALF_OPEN`.
     - Exactly ONE canary request is permitted through.
     - If the canary succeeds, the circuit breaker instantly transitions to `CLOSED` (fully healthy).
     - If the canary fails, cooldown resets with exponential backoff.
  2. Differentiate between network connection drops (client-side) and HTTP 5xx responses (server-side). Client-side network drops do not count toward model server failure thresholds.

---

### Attack Loop 7: Split-Brain Quota Rollover Across Multi-Timezone Providers
- **Problem**: Google AI Studio resets daily quotas at Midnight Pacific Time (PT). OpenAI resets at UTC Midnight. If a server runs on UTC, it resets Google keys 7 hours too early. The keys are re-enabled, immediately hit Google's quota ceiling, get marked exhausted again, and corrupt daily metrics.
- **Proposed Fix**: Use `_today_str(provider)` with `ZoneInfo("America/Los_Angeles")`.
- **Attack the Fix**: Standard Python installations on Windows do not include `tzdata`. Calling `ZoneInfo("America/Los_Angeles")` crashes with `ZoneInfoNotFoundError`, breaking the key pool on Windows workstations.
- **Final Hardened Solution**:
  1. Maintain explicit timezone calculation with timezone fallback:
     ```python
     def get_provider_date_str(provider: str) -> str:
         if provider == "gemini":
             try:
                 from zoneinfo import ZoneInfo
                 return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")
             except Exception:
                 # Fallback for Windows without tzdata package (approximate Pacific Time)
                 return datetime.now(timezone(timedelta(hours=-7))).strftime("%Y-%m-%d")
         return datetime.now(timezone.utc).strftime("%Y-%m-%d")
     ```
  2. Rollover checks occur transactionally on every lease acquisition, ensuring date synchronization across all workstations.

---

## 12. Recommended Final Architecture: The Unified Control Plane

### 12.1 Target Component Architecture

```text
                                 EXTERNAL CALLERS
       (Translator, ScriptBuilder, TTSDispatcher, Director, Telemetry)
                                        │
                                        ▼
                   ┌──────────────────────────────────────────┐
                   │               ModelGateway               │
                   │  - resolve_model(task_type, ...)         │
                   │  - execute_text(prompt, task_type, ...)  │
                   │  - execute_tts(text, voice, ...)         │
                   │  - acquire_lease(service, ...)           │
                   └────────────────────┬─────────────────────┘
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
    ┌─────────────────┐        ┌──────────────────┐       ┌─────────────────┐
    │  ModelRegistry  │        │ KeyLeaseManager  │       │  PolicyEngine   │
    │ - Model Specs   │        │ - SQLite Leases  │       │ - CircuitBreak  │
    │ - Quality Tiers │        │ - User Affinities│       │ - TokenBucket   │
    │ - Tasks & Limits│        │ - Crash Recovery │       │ - Cooldowns     │
    └────────┬────────┘        └────────┬─────────┘       └────────┬────────┘
             │                          │                          │
             └──────────────────────────┼──────────────────────────┘
                                        │
                                        ▼
                             ┌──────────────────────┐
                             │    RequestRouter     │
                             │ - Capability Matcher │
                             │ - Fallback Engine    │
                             └──────────┬───────────┘
                                        │
                                        ▼
                             ┌──────────────────────┐
                             │  Provider Adapters   │
                             │ - GeminiAdapter      │
                             │ - OpenAIAdapter      │
                             │ - LocalGpuAdapter    │
                             └──────────────────────┘
```

### 12.2 Target Interface for Subsystems (`audiobook_factory`)

All callers across the codebase migrate to a single, stable interface:

```python
# 1. High-Level Text Inference (Used by Translator, Screenplay, Dramaturge)
response = model_gateway.execute_text(
    prompt="Translate chapter...",
    system_instruction="You are an expert Hindustani dramaturge...",
    task=TaskType.TRANSLATION,
    response_schema=ChapterScriptSchema,
    thinking_budget=1024,
)

# 2. High-Level Speech Synthesis (Used by TTSDispatcher)
audio_path = model_gateway.execute_speech(
    text="नमस्ते, आप कैसे हैं?",
    voice="Aoede",
    output_path=Path("chunk_001.wav"),
    acting_directive=acting_spec,
)

# 3. Explicit Multi-Turn Session / Lease (Used for Complex Scene Batches)
with model_gateway.acquire_session(task=TaskType.SCREENPLAY) as session:
    draft = session.generate(prompt_part_1)
    audited = session.generate(prompt_part_2)
```

---

## 13. Implementation Roadmap & Priority Order (P0 / P1 / P2)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ P0: FOUNDATIONAL SAFETY & ATOMIC KEY LEASING (IMMEDIATE)                    │
│ 1. Create key_leases table in SQLite with lease_id, pid, user_id, expires_at│
│ 2. Implement atomic UPDATE ... RETURNING key acquisition                    │
│ 3. Implement PID liveness probe + autonomous stale lease reclamation        │
│ 4. Enforce One User = One Active Key constraint (per workload type)         │
│ 5. Remove plaintext keys from logs; implement cryptographic key aliases     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ P1: UNIFIED MODEL REGISTRY & PROVIDER ADAPTERS                              │
│ 1. Implement canonical ModelRegistry with capabilities, tiers, and limits   │
│ 2. Create BaseProviderAdapter and concrete GeminiProviderAdapter            │
│ 3. Decouple model discovery from Google Gemini REST endpoints               │
│ 4. Unify error classification and circuit breaker into PolicyEngine         │
│ 5. Route llm_client.py and gemini.py calls through the new adapters         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ P2: CONVERGENCE & RESILIENCE UPGRADES                                       │
│ 1. Implement ModelGateway as the universal project facade                   │
│ 2. Add hybrid session affinity with 60-second idle release                  │
│ 3. Add full structured audit logging in key_audit_log                       │
│ 4. Migrate all legacy callers (translator, character_caster, etc.)          │
│ 5. Provide zero-secret administrative CLI: `python audiobook_cli.py keys`   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Zero-Downtime Migration Plan

To avoid breaking existing pipeline runs or tests, the migration follows an **Expand-and-Contract** pattern:

### Step 1: Expand
1. Implement the new modular architecture in `audiobook_factory/core/models/` without touching `key_manager.py` or `model_manager.py`.
2. Add compatibility facades in `key_manager.py` (`get_persistent_key_pool()`) and `model_manager.py` (`get_model_manager()`) that forward calls to `ModelGateway`.

### Step 2: Validate
1. Run existing test suites (`tests/test_model_manager_and_strict_halt.py`, `tests/test_universal_key_pool_and_guard_shield.py`).
2. Verify that existing callers continue functioning with 100% backward compatibility.
3. Add dedicated multi-user concurrency tests simulating 10 parallel processes across 2 user IDs.

### Step 3: Contract
1. Gradually update callers to import `get_model_gateway()`.
2. Deprecate legacy direct access to SQLite tables.
3. Encrypt or hash credentials in the persistent database.

---
*End of Architectural Audit & Blueprint.*
