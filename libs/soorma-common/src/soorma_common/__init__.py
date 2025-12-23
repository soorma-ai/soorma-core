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
]

__version__ = "0.3.0"
