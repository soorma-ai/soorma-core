# Soorma Common

Common models and DTOs shared across Soorma platform services.

## Installation

```bash
pip install -e .
```

## Usage

```python
from soorma_common.models import (
    AgentDefinition,
    AgentCapability,
    EventDefinition,
    SemanticMemoryCreate,
    EpisodicMemoryCreate,
    WorkingMemorySet,
)

# Create an agent definition
agent = AgentDefinition(
    agent_id="my-agent",
    name="My Agent",
    description="A sample agent",
    capabilities=[
        AgentCapability(
            task_name="process_data",
            description="Process incoming data",
            consumed_event="data.received",
            produced_events=["data.processed", "data.error"]
        )
    ]
)

# Create semantic memory (knowledge storage)
semantic = SemanticMemoryCreate(
    agent_id="researcher",
    content="Python is a high-level programming language",
    metadata={"category": "programming", "source": "textbook"}
)

# Create episodic memory (interaction history)
episodic = EpisodicMemoryCreate(
    agent_id="assistant",
    role="user",
    content="What is the weather like today?",
    metadata={"session_id": "abc-123"}
)

# Create working memory (plan state)
working = WorkingMemorySet(
    value={"current_step": 2, "total_steps": 5, "status": "in_progress"}
)
```

## Models

### Agent Registry

- `AgentCapability` - Describes a single capability or task an agent can perform
- `AgentDefinition` - Defines a single agent in the system
- `AgentRegistrationRequest` - Request to register a new agent
- `AgentRegistrationResponse` - Response after registering an agent
- `AgentQueryRequest` - Request to query agents
- `AgentQueryResponse` - Response containing agent definitions

### Event Registry

- `EventDefinition` - Defines a single event in the system
- `EventRegistrationRequest` - Request to register a new event
- `EventRegistrationResponse` - Response after registering an event
- `EventQueryRequest` - Request to query events
- `EventQueryResponse` - Response containing event definitions

### Memory Service (CoALA Framework)

The Memory Service implements the CoALA (Cognitive Architectures for Language Agents) framework with four memory types:

> **Authentication Note**: Memory Service supports dual authentication:
> - **JWT Token** (User sessions): Provides `tenant_id` + `user_id` from token
> - **API Key** (Agent operations): Provides `tenant_id` + `agent_id`, requires explicit `user_id` in request parameters
>
> See [Memory Service SDK documentation](../../sdk/python/docs/MEMORY_SERVICE.md) for details.

#### Semantic Memory (Knowledge Base)
- `SemanticMemoryCreate` - Add knowledge to semantic memory
- `SemanticMemoryResponse` - Semantic memory entry with similarity score
- **Use cases**: Store facts, documentation, learned information
- **Features**: Vector search, RAG (Retrieval-Augmented Generation)
- **Scoping**: Tenant-level (shared across users in tenant)

#### Episodic Memory (Interaction History)
- `EpisodicMemoryCreate` - Log an interaction or event
- `EpisodicMemoryResponse` - Episodic memory entry with timestamp
- **Use cases**: Conversation history, user interactions, audit logs
- **Features**: Temporal recall, role-based filtering (user/assistant/system/tool)
- **Scoping**: Tenant + User + Agent (user-specific conversation history)

#### Procedural Memory (Skills & Procedures)
- `ProceduralMemoryResponse` - Skill or procedure with trigger conditions
- **Use cases**: Dynamic prompts, few-shot examples, user-specific agent customization
- **Features**: Context-aware retrieval, trigger-based activation, personalization
- **Scoping**: Tenant + User + Agent (enables per-user agent customization)

#### Working Memory (Plan State)
- `WorkingMemorySet` - Store plan-scoped state
- `WorkingMemoryResponse` - Working memory entry
- **Use cases**: Multi-agent collaboration, plan execution state, shared variables
- **Features**: Plan-scoped isolation, key-value storage
- **Scoping**: Tenant + Plan (shared state within plan execution)

## Memory Service Examples

### Semantic Memory (Knowledge Storage)
```python
from soorma_common.models import SemanticMemoryCreate

# Store knowledge
memory = SemanticMemoryCreate(
    agent_id="researcher",
    content="FastAPI is a modern web framework for Python",
    metadata={"category": "web-dev", "language": "python"}
)
```

### Episodic Memory (Interaction History)
```python
from soorma_common.models import EpisodicMemoryCreate

# Log user interaction
memory = EpisodicMemoryCreate(
    agent_id="chatbot",
    role="user",  # user, assistant, system, tool
    content="How do I deploy to production?",
    metadata={"session_id": "session-123", "timestamp": "2025-12-23T10:00:00Z"}
)
```

### Working Memory (Plan State)
```python
from soorma_common.models import WorkingMemorySet

# Store plan execution state
state = WorkingMemorySet(
    value={
        "plan_id": "research-plan-1",
        "current_phase": "data_collection",
        "completed_tasks": ["search", "filter"],
        "pending_tasks": ["analyze", "report"],
        "research_summary": "Found 50 relevant papers..."
    }
)
```

## Development

```bash
# Install in editable mode
pip install -e .

# Run tests
pytest

# Build package
python -m build
```

## Version History

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.
