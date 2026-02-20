"""
Soorma Common - Common models and DTOs for Soorma platform services.
"""
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
    # Event Registry
    EventDefinition,
    EventRegistrationRequest,
    EventRegistrationResponse,
    EventQueryRequest,
    EventQueryResponse,
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
    # Event Registry
    "EventDefinition",
    "EventRegistrationRequest",
    "EventRegistrationResponse",
    "EventQueryRequest",
    "EventQueryResponse",
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
]

__version__ = "0.7.7"
