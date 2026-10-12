#!/usr/bin/env python3
"""
Audiobook Factory Core Models Package.
Provides centralized control plane for models, keys, leases, and anti-ban policies.
"""

from audiobook_factory.core.models.db import get_db_connection, init_db, DEFAULT_DB_PATH
from audiobook_factory.core.models.lease_manager import (
    KeyLeaseManager,
    KeyLease,
    CallerIdentity,
    KeyLeaseError,
    KeyLeaseQuotaExceededError,
    NoAvailableKeyError,
    AllKeysExhaustedTodayError,
    get_key_lease_manager,
    is_pid_alive,
)
from audiobook_factory.core.models.policy_engine import (
    get_provider_date_str,
    NormalizedApiError,
    parse_retry_after,
    classify_universal_api_error,
    CircuitBreaker,
    get_circuit_breaker,
)
from audiobook_factory.core.models.anti_ban_guard import (
    AntiBanGuard,
    get_anti_ban_guard,
    EmergencyTripwireActiveError,
    get_stealth_sdk_headers,
    HumanCadenceController,
    TokenBucketRateLimiter,
    EmergencyTripwire,
    SessionAffinityTracker,
)
from audiobook_factory.core.models.registry import (
    ModelTier,
    Modality,
    TaskCategory,
    ModelCapability,
    ModelRegistry,
    get_model_registry,
    CANONICAL_MODELS,
)
from audiobook_factory.core.models.adapters import (
    BaseProviderAdapter,
    GenerationResult,
    SpeechResult,
    GeminiProviderAdapter,
    ApiHttpError,
    OpenAICompatibleAdapter,
    LocalGpuAdapter,
    HardwareVRAMGuard,
)
from audiobook_factory.core.models.router import (
    RequestRouter,
    ExecutionPlan,
)
from audiobook_factory.core.models.gateway import (
    ModelGateway,
    get_model_gateway,
)
from audiobook_factory.core.models.quarantine import (
    KeyQuarantineManager,
    QuarantinedKeyRecord,
    get_key_quarantine_manager,
)

__all__ = [
    "get_db_connection",
    "init_db",
    "DEFAULT_DB_PATH",
    "KeyLeaseManager",
    "KeyLease",
    "CallerIdentity",
    "KeyLeaseError",
    "KeyLeaseQuotaExceededError",
    "NoAvailableKeyError",
    "AllKeysExhaustedTodayError",
    "get_key_lease_manager",
    "is_pid_alive",
    "get_provider_date_str",
    "NormalizedApiError",
    "parse_retry_after",
    "classify_universal_api_error",
    "CircuitBreaker",
    "get_circuit_breaker",
    "AntiBanGuard",
    "get_anti_ban_guard",
    "EmergencyTripwireActiveError",
    "get_stealth_sdk_headers",
    "HumanCadenceController",
    "TokenBucketRateLimiter",
    "EmergencyTripwire",
    "SessionAffinityTracker",
    "ModelTier",
    "Modality",
    "TaskCategory",
    "ModelCapability",
    "ModelRegistry",
    "get_model_registry",
    "CANONICAL_MODELS",
    "BaseProviderAdapter",
    "GenerationResult",
    "SpeechResult",
    "GeminiProviderAdapter",
    "ApiHttpError",
    "OpenAICompatibleAdapter",
    "LocalGpuAdapter",
    "HardwareVRAMGuard",
    "RequestRouter",
    "ExecutionPlan",
    "ModelGateway",
    "get_model_gateway",
    "KeyQuarantineManager",
    "QuarantinedKeyRecord",
    "get_key_quarantine_manager",
]



