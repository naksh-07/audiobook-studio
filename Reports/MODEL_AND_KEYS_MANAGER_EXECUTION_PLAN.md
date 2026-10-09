# 🚀 Master Execution Plan: Model & Keys Manager Overhaul
## Phased Implementation Roadmap for High-Consequence 100+ Free Key Fleet & Universal Model Control Plane

- **Project**: `audiobook-studio` (`audiobook_factory`)
- **Version**: 1.0.0 (Execution Master Blueprint)
- **Target Architecture**: Option C (Unified Gateway Control Plane + Specialized Internal Modules)
- **Target Standard**: Zero Bans, Zero Race Conditions, Zero Plaintext Secrets, 100% Backward Compatibility
- **Date**: October 2026

---

## Executive Architecture Summary

This master plan details the exact sequence for executing the **Model & Keys Manager Overhaul** across **5 distinct, verifiable phases**. Every phase includes:
- Exact target files and directories.
- Core components and technical algorithms.
- Hard safety invariants and anti-ban safeguards.
- Specific unit tests and verification exit gates.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1 (P0): ACID SQLite Key Inventory & Lease Engine                      │
│ • DB schema (key_inventory, key_leases, key_audit_log) in WAL mode          │
│ • Atomic acquisition (UPDATE ... RETURNING), PID liveness probe, heartbeats │
│ • One User = One Active Key per workload enforcement                        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ [Exit Gate 1: 100% Pass Concurrency Tests]
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2 (P0): The 7 Iron Shields Anti-Ban Guard & Policy Engine             │
│ • Content-aware human cadence generator (reading + review + log-normal)     │
│ • Anti-correlation key-switch delay (18s-32s), 11 RPM conservative clamp     │
│ • Emergency global tripwire (5 consecutive failures -> 45s quarantine)      │
│ • Pacific Midnight DST-aware rollover calculator & circuit breaker          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ [Exit Gate 2: 100% Pass Anti-Ban Timing Tests]
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3 (P1): Canonical Model Registry & Polymorphic Provider Adapters      │
│ • Registry metadata for 50 live Gemini models + Cerebras + Groq + Local CUDA│
│ • Gemini 3.8 thinkingBudget rules (0 for pings, 1024 for creative)          │
│ • GeminiProviderAdapter with authentic google-genai-sdk-python headers      │
│ • OpenAICompatibleAdapter & LocalGpuAdapter (VRAM lock)                     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ [Exit Gate 3: 100% Pass Adapter & Payload Tests]
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4 (P1): Unified Request Router & Gateway Facade                       │
│ • RequestRouter: Requirement -> Eligible Models -> Compatible Key Leases    │
│ • ModelGateway: Central singleton for generate_content & synthesize_speech  │
│ • Context-managed multi-turn session with scene-level key affinity          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ [Exit Gate 4: 100% Pass Gateway Integration]
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5 (P2): Backward Compatibility, Subsystem Migration & Stress Tests    │
│ • Drop-in facades for call_gemini, call_model, PersistentKeyPool            │
│ • Subsystem migration (Translator, Director, TTSDispatcher)                 │
│ • Multi-process stress benchmark (10 parallel workers, 2 users, 0 collisions│
│ • Zero-secret admin CLI: python audiobook_cli.py keys status                │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │ [Exit Gate 5: 100% Full Regression Pass]
                                       ▼
                                PRODUCTION READY
```

---

## Detailed Phase Breakdown

### Phase 1 (P0): ACID SQLite Key Inventory & Lease Engine
**Goal**: Build the thread-safe, multi-process ACID reservation foundation in SQLite that eliminates race conditions and double-leases.

#### 1. Files Created / Modified
- `audiobook_factory/core/models/__init__.py`
- `audiobook_factory/core/models/db.py`: SQLite connection pool, WAL mode, busy timeout (`5000ms`), table creation and migration scripts.
- `audiobook_factory/core/models/lease_manager.py`: `KeyLeaseManager`, `CallerIdentity`, `KeyLease`, `KeyInventoryRecord`.
- `tests/test_key_lease_engine.py`: Unit test suite for atomic acquisition, PID death recovery, and user limits.

#### 2. Key Algorithms & Implementation Details
1. **Schema DDL**:
   - `key_inventory`: `key_hash` (PK), `key_alias` (e.g. `key_a8f2`), `encrypted_key`, `provider`, `allowed_services` (JSON), `status`, `backoff_until`, `last_used`.
   - `key_leases`: `lease_id` (UUIDv4), `key_hash`, `workstation_id`, `user_id`, `process_id`, `worker_id`, `workload_type`, `leased_at`, `expires_at`, `status`.
   - `key_audit_log`: Zero-secret event log (`ACQUIRE`, `RENEW`, `RELEASE`, `EXPIRE`, `REVOKE`).
2. **Atomic Allocation Algorithm**:
   - Wrap in `BEGIN IMMEDIATE;`.
   - Sweep expired leases (`expires_at < CURRENT_TIMESTAMP`).
   - Run atomic `UPDATE key_inventory SET is_leased = 1 ... RETURNING ...` or check availability via `NOT EXISTS (SELECT 1 FROM key_leases WHERE key_hash = k.key_hash AND status = 'ACTIVE' AND expires_at > CURRENT_TIMESTAMP)`.
   - Insert lease with rolling 60s expiration: `expires_at = datetime('now', '+60 seconds')`.
3. **Dual Liveness Crash Recovery**:
   - When inspecting active leases, verify caller PID:
     ```python
     def is_pid_alive(pid: int) -> bool:
         if pid <= 0: return False
         try:
             os.kill(pid, 0)
             return True
         except (OSError, ProcessLookupError):
             return False
     ```
   - If PID is dead, mark lease `EXPIRED` immediately without waiting for the 60s TTL.
4. **One User = One Key per Workload Enforcement**:
   - Before granting lease, check:
     $$\text{COUNT}(\text{leases where user\_id} = U \text{ and workload\_type} = W \text{ and status} = \text{'ACTIVE'}) = 0$$
   - If violated, raise `KeyLeaseQuotaExceededError`.
5. **Zero-Secret Public Aliases**:
   - Public alias generation:
     $$\text{alias} = \text{"key\_"} + \text{SHA256}(\text{key} + \text{SALT})[:8]$$
   - Plaintext keys never written to database logs or stdout.

#### 3. Exit Gate & Verification (Gate 1)
- [ ] Run `python3 -m unittest tests/test_key_lease_engine.py`.
- [ ] Verify 10 concurrent threads requesting a lease on 2 available keys yield exactly 2 active leases and 8 queued/rejected requests (0% double-leases).
- [ ] Verify killed process (`kill -9`) lease is reclaimed on next allocation within 50ms.

---

### Phase 2 (P0): The 7 Iron Shields Anti-Ban Guard & Policy Engine
**Goal**: Build the traffic-shaping, anti-correlation, rate-limiting, and error-quarantine core to protect 100+ free keys from edge bans.

#### 1. Files Created / Modified
- `audiobook_factory/core/models/anti_ban_guard.py`: `AntiBanGuard`, `HumanCadenceController`, `TokenBucketRateLimiter`.
- `audiobook_factory/core/models/policy_engine.py`: `PolicyEngine`, `CircuitBreaker`, `classify_universal_api_error`.
- `tests/test_anti_ban_guard_and_policy.py`: Unit test suite for cadence timing, anti-correlation pauses, and tripwires.

#### 2. Key Algorithms & Implementation Details
1. **Shield 2 (Session Affinity Leasing)**:
   - Worker holds lease for up to 15 sequential segments within a scene with a rolling 60-second idle renewal.
2. **Shield 3 (Key-Switch Anti-Correlation Cooldown)**:
   - When worker transitions from Key A to Key B:
     ```python
     def enforce_key_switch_cooldown(prev_key_alias: str, new_key_alias: str):
         if prev_key_alias and prev_key_alias != new_key_alias:
             cooldown_sec = random.uniform(18.0, 32.0)
             time.sleep(cooldown_sec)
     ```
3. **Shield 4 (Human Cadence Shaper)**:
   - Delay formula:
     $$T_{\text{wait}} = \min\left(12.0, \max\left(2.5, \frac{\text{words}}{4.0}\right)\right) + \min(15.0, \text{prev\_dur} \times \text{Uniform}(0.15, 0.35)) + \text{LogNormal}(1.2, 0.35)$$
   - Periodic scene review break: Every 14 segments, pause for 15.0s to 30.0s.
4. **Shield 5 (Conservative 75% Rate Limiting)**:
   - Token bucket clamped to **11.0 RPM** per key (3.5s minimum gap).
5. **Shield 6 (Stealth SDK Headers)**:
   - Inject `google-genai-sdk-python/0.8.3` headers on every Google request.
6. **Shield 7 (Emergency Global Tripwire)**:
   - If 5 consecutive keys encounter HTTP 429 or 503 within 60s, trip global circuit breaker for **45.0 seconds**.
7. **Timezone Rollover Engine**:
   - Pacific Midnight calculation with Windows timezone fallback (`timedelta(hours=-7)`).

#### 3. Exit Gate & Verification (Gate 2)
- [ ] Run `python3 -m unittest tests/test_anti_ban_guard_and_policy.py`.
- [ ] Assert inter-segment delay falls within $[3.5\text{s}, 15.0\text{s}]$.
- [ ] Assert key switch delay falls within $[18.0\text{s}, 32.0\text{s}]$.
- [ ] Assert 5 consecutive mock 429s halt the entire dispatch loop for 45s.

---

### Phase 3 (P1): Canonical Model Registry & Polymorphic Provider Adapters
**Goal**: Build the single source of truth for model capabilities and isolate provider API mechanics into clean adapters.

#### 1. Files Created / Modified
- `audiobook_factory/core/models/registry.py`: `ModelRegistry`, `ModelCapability`, `ModelTier`, `TaskType`, `Modality`.
- `audiobook_factory/core/models/adapters/base.py`: `BaseProviderAdapter` interface.
- `audiobook_factory/core/models/adapters/gemini.py`: `GeminiProviderAdapter`.
- `audiobook_factory/core/models/adapters/openai_compat.py`: `OpenAICompatibleAdapter` (Cerebras, Groq, OpenAI, OpenRouter).
- `audiobook_factory/core/models/adapters/local_gpu.py`: `LocalGpuAdapter` (CUDA lock & MMS aligner).
- `tests/test_model_registry_and_adapters.py`: Unit tests for capabilities, payload construction, and response parsing.

#### 2. Key Algorithms & Implementation Details
1. **Canonical Registry Specification**:
   - Register all 50 discovered Gemini models.
   - Primary mapping:
     - `gemini-3.8-flash`: Tier 1 Flagship, 1M input / 64k output.
     - `gemini-3.7-flash`: Tier 1 Flagship, 1M input / 64k output.
     - `gemini-3.6-flash`: Tier 2 Balanced, 1M input / 32k output.
     - `gemini-3.8-flash-tts`: Tier 1 Audio, 8k input / 16k output, 10 RPD hard ceiling.
     - `gemini-3.1-flash-lite`: Tier 3 Utility, 1M input / 8k output, 30 RPM.
2. **Gemini 3.8 Thinking Budget Strategy**:
   - In `GeminiProviderAdapter`:
     - If task is utility/ping: `thinkingBudget = 0` (eliminates thinking tokens, avoids empty `MAX_TOKENS` content).
     - If task is creative (Translation, Screenplay): `thinkingBudget = 1024` with 32k output headroom.
3. **Fiction Safety Framing**:
   - Auto-inject `BLOCK_NONE` thresholds and dramatic fiction context framing on all creative tasks.
4. **Speech Synthesis Extraction**:
   - Parse `audio/wav` inlineData base64 payload into raw 24kHz PCM WAV.

#### 3. Exit Gate & Verification (Gate 3)
- [ ] Run `python3 -m unittest tests/test_model_registry_and_adapters.py`.
- [ ] Verify `gemini-3.8-flash` payload includes `thinkingConfig: {"thinkingBudget": 0}` on utility tasks and `1024` on creative tasks.
- [ ] Verify audio payload decoding extracts valid WAV header and PCM samples.

---

### Phase 4 (P1): Unified Request Router & Gateway Facade
**Goal**: Assemble the control plane into a single, clean `ModelGateway` interface for all 5 production rooms.

#### 1. Files Created / Modified
- `audiobook_factory/core/models/router.py`: `RequestRouter`, `ExecutionPlan`.
- `audiobook_factory/core/models/gateway.py`: `ModelGateway`, `get_model_gateway()`.
- `tests/test_model_gateway_integration.py`: End-to-end integration tests.

#### 2. Key Algorithms & Implementation Details
1. **Capability-Based Routing**:
   - Caller asks for: `task=TaskType.TRANSLATION`, `min_tier=ModelTier.TIER_1_FLAGSHIP`.
   - Router evaluates: Registry candidates $\rightarrow$ Filter circuit breakers $\rightarrow$ Match eligible key inventory $\rightarrow$ Acquire lease from `KeyLeaseManager`.
2. **Gateway Execution Flow**:
   - `generate_content(...)`:
     1. Resolve execution plan via router.
     2. Wait for cadence pacing via `AntiBanGuard`.
     3. Dispatch request via chosen adapter.
     4. On success: Record tokens, update success metrics in SQLite, release lease.
     5. On failure: Classify error via `PolicyEngine`. If daily quota reached, mark key `EXHAUSTED_TODAY` and failover to next key adhering to 18-32s anti-correlation delay.
3. **Session-Level Leasing**:
   - Provide `with gateway.lease_session(task=TaskType.SCREENPLAY) as session:` for holding single-key affinity across entire multi-turn scenes.

#### 3. Exit Gate & Verification (Gate 4)
- [ ] Run `python3 -m unittest tests/test_model_gateway_integration.py`.
- [ ] Verify mock text generation routes through registry, leases key, passes anti-ban guard, and executes cleanly.

---

### Phase 5 (P2): Backward Compatibility, Subsystem Migration & Stress Tests
**Goal**: Wire existing callers to the new engine with 100% backward compatibility, verify zero regressions, and conduct a multi-process concurrency stress test.

#### 1. Files Created / Modified
- `audiobook_factory/key_manager.py`: Wrap legacy `PersistentKeyPool` around `KeyLeaseManager`.
- `audiobook_factory/model_manager.py`: Wrap legacy `ModelManager` around `ModelGateway`.
- `audiobook_factory/llm_client.py`: Delegate `call_gemini` and `call_model` to `ModelGateway`.
- `audiobook_factory/tts/providers/gemini.py`: Delegate synthesis to `ModelGateway.synthesize_speech`.
- `tests/test_multi_user_stress_concurrency.py`: Multi-process stress test (10 workers, 2 user IDs).
- `audiobook_cli.py`: Add `keys status`, `keys audit` CLI commands.

#### 2. Key Algorithms & Implementation Details
1. **Non-Breaking Facade Wrappers**:
   - Legacy functions (`get_persistent_key_pool()`, `get_model_manager()`) continue working seamlessly for any existing scripts.
2. **Multi-User Stress Benchmark**:
   - Spawn 10 concurrent processes under User A and User B.
   - Assert:
     - 0% race condition collisions.
     - 0% double-leased keys.
     - 0% rate limit cascades.
     - Perfect FIFO queueing for requests exceeding the 1-key-per-user limit.

#### 3. Exit Gate & Verification (Gate 5)
- [ ] Run full test suite:
  ```bash
  python3 -m unittest tests/test_universal_key_pool_and_guard_shield.py
  python3 -m unittest tests/test_model_manager_and_strict_halt.py
  python3 -m unittest tests/test_multi_user_stress_concurrency.py
  ```
- [ ] Assert **100% PASS** across all suites with 0 regressions.

---

## Risk Ledger & Mitigation Matrix

| Risk / Failure Mode | Likelihood | Impact | Built-in Mitigation Mechanism |
| :--- | :--- | :--- | :--- |
| **Worker SIGKILL Leaves Key Locked** | High | High | Dual Liveness Probe: `os.kill(pid, 0)` checks OS process table and auto-reclaims dead leases immediately. |
| **Google Changes Rate Limit Heuristics** | Medium | Severe | Conservative 75% rate limiting (11 RPM) + 18-32s anti-correlation key-switch delay prevents threshold triggers. |
| **Thinking Tokens Eat Output Budget** | High | High | `thinkingBudget: 0` explicitly set for ping/utility; 32k output headroom with dynamic halving for creative tasks. |
| **Speech Quota Depleted (10 RPD)** | High | Severe | Dedicated RPD ledger tracks daily count; gate halts audio calls before touching key if count reaches 10. |
| **Windows Timezone Crash** | Medium | Medium | DST-aware `ZoneInfo("America/Los_Angeles")` with automatic fallback to fixed `timedelta(hours=-7)`. |
| **SQLite Lock Contention Under Load** | Medium | Low | WAL mode (`PRAGMA journal_mode = WAL;`) + `PRAGMA busy_timeout = 5000;` + retry jitter loop. |

---
*Execution Plan Approved for Immediate Phased Implementation.*
