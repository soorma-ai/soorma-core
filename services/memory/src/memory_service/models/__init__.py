"""Initialize models package."""

from memory_service.models.memory import (
    Tenant,
    User,
    SemanticMemory,
    EpisodicMemory,
    ProceduralMemory,
    WorkingMemory,
)

# Import DTOs from soorma-common (not re-exported, just for IDE cross-referencing)
from soorma_common.models import (  # noqa: F401
    SemanticMemoryCreate,
    SemanticMemoryResponse,
    EpisodicMemoryCreate,
    EpisodicMemoryResponse,
    ProceduralMemoryResponse,
    WorkingMemorySet,
    WorkingMemoryResponse,
)

__all__ = [
    "Tenant",
    "User",
    "SemanticMemory",
    "EpisodicMemory",
    "ProceduralMemory",
    "WorkingMemory",
]
