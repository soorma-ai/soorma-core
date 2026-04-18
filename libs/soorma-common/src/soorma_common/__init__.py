"""
Soorma Common - Common models and DTOs for Soorma platform services.
"""

__version__ = "0.9.0"

from .models import (
    BaseDTO,
    # Agent Registry
    AgentCapability,
    AgentDefinition,
    AgentRegistrationRequest,
    AgentRegistrationRequestFlat,
    AgentRegistrationResponse,
    AgentQueryRequest,
    AgentQueryResponse,
    # Schema Registry (v0.8.1+)
    PayloadSchema,
    PayloadSchemaRegistration,
    PayloadSchemaRegistrationRequest,
    PayloadSchemaResponse,
    PayloadSchemaListResponse,
    DiscoveredAgent,
    # Event Registry
    EventDefinition,
    EventRegistrationRequest,
    EventRegistrationResponse,
    EventQueryRequest,
    EventQueryResponse,
    # Identity Service
    OnboardingRequest,
    OnboardingResponse,
    PrincipalRequest,
    PrincipalResponse,
    TokenIssueRequest,
    TokenIssueResponse,
    TokenIssuanceType,
    DelegatedIssuerRequest,
    DelegatedIssuerResponse,
    TenantAdminCredentialRotateResponse,
    MappingEvaluationRequest,
    MappingEvaluationResponse,
    # Memory Service
    SemanticMemoryCreate,
    SemanticMemoryResponse,
    EpisodicMemoryCreate,
    EpisodicMemoryResponse,
    ProceduralMemoryResponse,
    WorkingMemorySet,
    WorkingMemoryResponse,
    # Task Context
    TaskContextCreate,
    TaskContextUpdate,
    TaskContextResponse,
    # Plan Context
    PlanContextCreate,
    PlanContextUpdate,
    PlanContextResponse,
    # Plans & Sessions
    PlanCreate,
    PlanUpdate,
    PlanSummary,
    SessionCreate,
    SessionSummary,
)

from .events import (
    # Event Topics
    EventTopic,
    # Event Envelopes
    EventEnvelope,
    ActionRequestEvent,
    ActionResultEvent,
    BusinessFactEvent,
    BillingEvent,
    NotificationEvent,
    # Event Service DTOs
    PublishRequest,
    PublishResponse,
    SubscribeRequest,
    StreamConnectionInfo,
)

from .state import (
    # State Machine
    StateAction,
    StateTransition,
    StateConfig,
    PlanDefinition,
    PlanRegistrationRequest,
    PlanInstanceRequest,
)

from .a2a import (
    # A2A Protocol
    A2AAuthType,
    A2AAuthentication,
    A2ASkill,
    A2AAgentCard,
    A2APart,
    A2AMessage,
    A2ATask,
    A2ATaskStatus,
    A2ATaskResponse,
)

from .tracking import (
    # Progress Tracking
    TaskState,
    TaskProgressEvent,
    TaskStateChanged,
)

from .tenancy import DEFAULT_PLATFORM_TENANT_ID

from .tracker import (
    # Tracker Service Response DTOs
    PlanProgress,
    TaskExecution,
    EventTimelineEntry,
    EventTimeline,
    AgentMetrics,
    PlanExecution,
    DelegationGroup,
)

from .decisions import (
    # Decision Types
    PlanAction,
    PublishAction,
    CompleteAction,
    WaitAction,
    DelegateAction,
    PlannerAction,
    PlannerDecision,
    EventDecision,
)

__all__ = [
    "BaseDTO",
    # Agent Registry
    "AgentCapability",
    "AgentDefinition",
    "AgentRegistrationRequest",
    "AgentRegistrationRequestFlat",
    "AgentRegistrationResponse",
    "AgentQueryRequest",
    "AgentQueryResponse",
    # Schema Registry (v0.8.1+)
    "PayloadSchema",
    "PayloadSchemaRegistration",
    "PayloadSchemaRegistrationRequest",
    "PayloadSchemaResponse",
    "PayloadSchemaListResponse",
    "DiscoveredAgent",
    # Event Registry
    "EventDefinition",
    "EventRegistrationRequest",
    "EventRegistrationResponse",
    "EventQueryRequest",
    "EventQueryResponse",
    # Identity Service
    "OnboardingRequest",
    "OnboardingResponse",
    "PrincipalRequest",
    "PrincipalResponse",
    "TokenIssueRequest",
    "TokenIssueResponse",
    "TokenIssuanceType",
    "DelegatedIssuerRequest",
    "DelegatedIssuerResponse",
    "TenantAdminCredentialRotateResponse",
    "MappingEvaluationRequest",
    "MappingEvaluationResponse",
    # Memory Service
    "SemanticMemoryCreate",
    "SemanticMemoryResponse",
    "EpisodicMemoryCreate",
    "EpisodicMemoryResponse",
    "ProceduralMemoryResponse",
    "WorkingMemorySet",
    "WorkingMemoryResponse",
    # Task Context
    "TaskContextCreate",
    "TaskContextUpdate",
    "TaskContextResponse",
    # Plan Context
    "PlanContextCreate",
    "PlanContextUpdate",
    "PlanContextResponse",
    # Plans & Sessions
    "PlanCreate",
    "PlanUpdate",
    "PlanSummary",
    "SessionCreate",
    "SessionSummary",
    # Event Topics
    "EventTopic",
    # Event Envelopes
    "EventEnvelope",
    "ActionRequestEvent",
    "ActionResultEvent",
    "BusinessFactEvent",
    "BillingEvent",
    "NotificationEvent",
    # Event Service DTOs
    "PublishRequest",
    "PublishResponse",
    "SubscribeRequest",
    "StreamConnectionInfo",
    # State Machine
    "StateAction",
    "StateTransition",
    "StateConfig",
    "PlanDefinition",
    "PlanRegistrationRequest",
    "PlanInstanceRequest",
    # A2A Protocol
    "A2AAuthType",
    "A2AAuthentication",
    "A2ASkill",
    "A2AAgentCard",
    "A2APart",
    "A2AMessage",
    "A2ATask",
    "A2ATaskStatus",
    "A2ATaskResponse",
    # Progress Tracking
    "TaskState",
    "TaskProgressEvent",
    "TaskStateChanged",
    # Tracker Service Response DTOs
    "PlanProgress",
    "TaskExecution",
    "EventTimelineEntry",
    "EventTimeline",
    "AgentMetrics",
    "PlanExecution",
    "DelegationGroup",
    # Decision Types
    "PlanAction",
    "PublishAction",
    "CompleteAction",
    "WaitAction",
    "DelegateAction",
    "PlannerAction",
    "PlannerDecision",
    "EventDecision",
]
