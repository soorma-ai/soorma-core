# Memory Service SDK

The Memory Service SDK provides a complete implementation of the CoALA (Cognitive Architectures for Language Agents) framework, enabling autonomous agents to store and retrieve memories across four distinct memory types.

> **⚠️ Authentication Model Update (v0.6.0)**  
> **Current (v0.5.0)**: Only JWT authentication supported. All operations require `tenant_id` + `user_id` from JWT token.  
> **Future (v0.6.0)**: Dual authentication model:
> - **JWT Token** (User sessions): Provides `tenant_id` + `user_id` automatically
> - **API Key** (Agent operations): Provides `tenant_id` + `agent_id`, requires explicit `user_id` parameter
>
> This documentation describes the intended v0.6.0 design. Current implementation only supports JWT mode.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Memory Types](#memory-types)
  - [Semantic Memory](#semantic-memory)
  - [Episodic Memory](#episodic-memory)
  - [Procedural Memory](#procedural-memory)
  - [Working Memory](#working-memory)
- [API Reference](#api-reference)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)
- [Testing](#testing)

## Overview

The Memory Service implements persistent memory for autonomous agents following the CoALA framework:

```
┌────────────────────────────────────────────────────────────┐
│                    Memory Service (CoALA)                  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Semantic   │  │   Episodic   │  │  Procedural  │      │
│  │   (Facts)    │  │  (History)   │  │   (Skills)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↓                 ↓                  ↓             │
│  ┌────────────────────────────────────────────────────┐    │
│  │        PostgreSQL + pgvector (HNSW indexes)        │    │
│  └────────────────────────────────────────────────────┘    │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │     Working Memory (Plan-scoped shared state)       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Architecture

### Client Architecture

The SDK provides two layers of interaction:

1. **Direct Client** (`soorma.memory.client.MemoryClient`): Low-level HTTP client for Memory Service
2. **Context Wrapper** (`soorma.context.MemoryClient`): High-level wrapper with automatic fallback to local storage

```python
# Low-level direct client
from soorma.memory.client import MemoryClient as MemoryServiceClient
client = MemoryServiceClient(base_url="http://localhost:8083")

# High-level context wrapper (recommended for agents)
from soorma import PlatformContext
context = PlatformContext()
await context.memory.store("key", value)  # Auto-fallback to local storage
```

### Fallback Behavior

The context wrapper automatically falls back to local in-memory storage when the Memory Service is unavailable:

- **Development**: Use local storage without running Memory Service
- **Production**: Connect to Memory Service for persistence and vector search
- **Seamless transition**: Same API works in both modes

## Installation

```bash
pip install soorma-core
```

For development with Memory Service:

```bash
# Start infrastructure (includes PostgreSQL + Memory Service)
soorma dev --start

# Stop infrastructure
soorma dev --stop
```

## Quick Start

### Using Context Wrapper (Recommended)

```python
from soorma import PlatformContext

# Initialize context
context = PlatformContext()

# Store working memory
await context.memory.store("vehicle_id", "VIN-12345")

# Retrieve working memory
vehicle_id = await context.memory.retrieve("vehicle_id")

# Search semantic memory
results = await context.memory.search("How to replace brake pads?", limit=5)

# Log interaction
await context.memory.log_interaction(
    agent_id="assistant",
    role="user",
    content="What's the weather?",
    metadata={"session_id": "abc-123"}
)

# Get recent history
history = await context.memory.get_recent_history("assistant", limit=10)

# Get relevant skills
skills = await context.memory.get_relevant_skills(
    agent_id="researcher",
    context="need to analyze scientific papers",
    limit=3
)

# Clean up
await context.memory.close()
```

### Using Direct Client

```python
from soorma.memory.client import MemoryClient

# Initialize client
client = MemoryClient(base_url="http://localhost:8083")

# Store knowledge
memory_id = await client.store_knowledge(
    content="Python is a programming language",
    metadata={"category": "programming"}
)

# Search knowledge
results = await client.search_knowledge("programming languages", limit=5)

# Clean up
await client.close()
```

## Memory Types

### Semantic Memory

**Purpose**: Store facts, knowledge, and learned information with vector search capabilities.

**Use Cases**:
- RAG (Retrieval-Augmented Generation)
- Knowledge bases
- Documentation search
- FAQ systems

**Example**:

```python
from soorma.memory.client import MemoryClient

client = MemoryClient(base_url="http://localhost:8083")

# Store knowledge
memory_id = await client.store_knowledge(
    content="FastAPI is a modern, fast web framework for Python",
    metadata={
        "category": "web-development",
        "language": "python",
        "source": "documentation",
        "url": "https://fastapi.tiangolo.com"
    }
)

# Search with semantic similarity
results = await client.search_knowledge(
    query="What is the best Python web framework?",
    limit=5
)

for result in results:
    print(f"Score: {result.score:.3f}")
    print(f"Content: {result.content}")
    print(f"Metadata: {result.metadata}")
    print("---")
```

### Episodic Memory

**Purpose**: Store interaction history and events with temporal context.

**Use Cases**:
- Conversation history
- User interactions
- Audit logs
- Event timelines

**Roles**: `user`, `assistant`, `system`, `tool`

**Example**:

```python
from soorma.memory.client import MemoryClient

client = MemoryClient(base_url="http://localhost:8083")

# Log user message
await client.log_interaction(
    agent_id="chatbot-1",
    role="user",
    content="How do I reset my password?",
    metadata={"session_id": "session-123"}
)

# Log assistant response
await client.log_interaction(
    agent_id="chatbot-1",
    role="assistant",
    content="To reset your password, click on 'Forgot Password' on the login page.",
    metadata={"session_id": "session-123"}
)

# Get recent conversation history
history = await client.get_recent_history("chatbot-1", limit=10)

for entry in history:
    print(f"[{entry.role}] {entry.content}")
    print(f"Timestamp: {entry.created_at}")
    print("---")

# Search interactions by content
results = await client.search_interactions(
    agent_id="chatbot-1",
    query="password reset",
    limit=5
)
```

### Procedural Memory

**Purpose**: Store skills, procedures, and dynamic prompts with context-aware retrieval. Enables **personalized agent behavior** and **user-specific customization**.

**Use Cases**:
- **Dynamic system prompts**: Adapt agent instructions per user/tenant
- **Few-shot examples**: Provide context-specific examples
- **Agent skills**: Store callable procedures and tool usage patterns
- **Conditional behaviors**: Trigger-based behavior modifications
- **User preferences**: Customize agent responses based on learned patterns

**Scope**: `tenant_id` + `user_id` + `agent_id` (triple-scoped for maximum personalization)

**Procedure Types**:
- `system_prompt`: Dynamic agent instructions (overrides or extends default baseline)
- `few_shot_example`: Task-specific examples for in-context learning

**Personalization Model**:
```
┌─────────────────────────────────────────────────────────────┐
│                  Baseline Agent (Default)                    │
│          "You are a helpful research assistant"              │
└─────────────────────────────────────────────────────────────┘
                            ↓
            ┌───────────────────────────────┐
            │  User A's Customization       │
            │  (Procedural Memory)          │
            ├───────────────────────────────┤
            │  Type: system_prompt          │
            │  Content: "Always cite        │
            │  sources in APA format"       │
            │  Trigger: "research tasks"    │
            └───────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           Personalized Agent for User A                      │
│  "You are a helpful research assistant. Always cite          │
│   sources in APA format when conducting research"            │
└─────────────────────────────────────────────────────────────┘
```

**Current SDK Status**: 
- ✅ **Read operations** available via SDK (`get_relevant_skills()`)
- 🚧 **Write operations** coming soon (currently managed via direct database access)
- 📌 **Roadmap**: Admin APIs for managing procedural memory will be added in v0.6.0

**Example**:

```python
from soorma.memory.client import MemoryClient

client = MemoryClient(base_url="http://localhost:8083")

# Get relevant skills/prompts for a context
# This retrieves procedural memories specific to this tenant + user + agent
skills = await client.get_relevant_skills(
    agent_id="researcher",
    context="need to analyze scientific papers about climate change",
    limit=3
)

for skill in skills:
    print(f"Type: {skill.procedure_type}")  # system_prompt or few_shot_example
    print(f"Content: {skill.content}")
    print(f"Trigger: {skill.trigger_condition}")
    print(f"Relevance Score: {skill.score:.3f}")
    print("---")

# Example output:
# Type: system_prompt
# Content: Always cite sources in APA format and verify publication dates
# Trigger: research and citation tasks
# Relevance Score: 0.892
```

**How Agents Use Procedural Memory**:

```python
from soorma import PlatformContext

async def research_task(task, context: PlatformContext):
    # 1. Get user-specific customizations
    # Note: tenant_id and user_id are NOT passed as arguments
    # They are automatically extracted from the JWT token by the Memory Service
    skills = await context.memory.get_relevant_skills(
        agent_id="researcher",
        context=task.description,
        limit=3
    )
    
    # 2. Build personalized system prompt
    base_prompt = "You are a helpful research assistant."
    
    # Add user-specific behaviors from procedural memory
    customizations = []
    for skill in skills:
        if skill.procedure_type == "system_prompt":
            customizations.append(skill.content)
    
    if customizations:
        personalized_prompt = base_prompt + "\n\nUser preferences:\n" + "\n".join(customizations)
    else:
        personalized_prompt = base_prompt
    
    # 3. Use personalized prompt with LLM
    response = await llm.generate(
        prompt=personalized_prompt,
        user_input=task.data["query"]
    )
    
    return response
```

**How Tenant + User Scoping Works**:

The Memory Service supports **dual authentication** with different scoping rules:

**Mode 1: JWT Authentication (User Context)**

User-facing applications use JWT tokens that provide `tenant_id` + `user_id`:

```
┌─────────────────────────────────────────────────────────────┐
│                    User / Web App                           │
│                                                             │
│  context = PlatformContext(auth_token="jwt-token")          │
│  await context.memory.get_recent_history(agent_id="...")    │
│                                                             │
│  ↓ HTTP Request with Authorization: Bearer <jwt-token>      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Memory Service (Middleware)                    │
│                                                             │
│  1. Extract JWT from Authorization header                   │
│  2. Decode JWT to get:                                      │
│     - tenant_id: "acme-corp"  ← FROM JWT                    │
│     - user_id: "alice"        ← FROM JWT                    │
│  3. Store in request.state                                  │
│  4. Use in database queries (via RLS)                       │
│                                                             │
│  SQL Query:                                                 │
│  SELECT * FROM episodic_memory                              │
│  WHERE tenant_id = 'acme-corp'  ← From JWT (guaranteed)     │
│    AND user_id = 'alice'        ← From JWT (guaranteed)     │
│    AND agent_id = 'chatbot'     ← From API parameter        │
└─────────────────────────────────────────────────────────────┘
```

**Mode 2: API Key Authentication (Agent Context)**

Autonomous agents use API keys that provide `tenant_id` + `agent_id`:

```
┌─────────────────────────────────────────────────────────────┐
│                    Background Agent                         │
│                                                             │
│  context = PlatformContext(api_key="sk_test_...")           │
│  await context.memory.log_interaction(                      │
│      agent_id="processor",                                  │
│      user_id="alice",  ← MUST BE EXPLICIT                   │
│      role="system",                                         │
│      content="Task done"                                    │
│  )                                                          │
│                                                             │
│  ↓ HTTP Request with X-API-Key: sk_test_...                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Memory Service (Middleware)                    │
│                                                             │
│  1. Extract API Key from X-API-Key header                   │
│  2. Decode API Key to get:                                  │
│     - tenant_id: "acme-corp"    ← FROM API KEY              │
│     - agent_id: "processor"     ← FROM API KEY              │
│  3. user_id: Extract from request parameters (NOT in auth)  │
│  4. Use in database queries (via RLS)                       │
│                                                             │
│  SQL Query:                                                 │
│  INSERT INTO episodic_memory                                │
│  VALUES (                                                   │
│    tenant_id = 'acme-corp',  ← From API Key (guaranteed)    │
│    user_id = 'alice',        ← From API parameter (explicit)│
│    agent_id = 'processor',   ← From API parameter           │
│    ...                                                      │
│  )                                                          │
└─────────────────────────────────────────────────────────────┘
```

**Scoping Summary**:

| Auth Type | Tenant ID | User ID | Agent ID | Notes |
|-----------|-----------|---------|----------|-------|
| JWT Token | From JWT ✓ | From JWT ✓ | Parameter (explicit) | User-facing apps |
| API Key | From API Key ✓ | Parameter (explicit) | Parameter (explicit) | Background agents |

**Why This Design?**

- **Tenant ID**: Always from authentication (guaranteed isolation)
- **User ID**: From JWT for user sessions, explicit parameter for agent operations
- **Agent ID**: Always explicit (multiple agents can serve same user/tenant)

**Development Mode** (Local Testing):

In local development without authentication, the Memory Service uses default values:

```python
# services/memory/src/memory_service/core/config.py
IS_LOCAL_TESTING = True  # Set via environment variable
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000000"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000000"
```

```python
# Local development - no auth required
from soorma import PlatformContext

context = PlatformContext()  # No auth_token or api_key needed

# Works in dev mode - uses default tenant/user
skills = await context.memory.get_relevant_skills(
    agent_id="researcher",
    context="task description"
)
```

**Production Mode - JWT (User Sessions)**:

```python
from soorma import PlatformContext
from soorma.memory.client import MemoryClient

# JWT token contains: {"tenant_id": "acme-corp", "user_id": "alice", ...}
client = MemoryClient(
    base_url="https://memory.soorma.ai",
    auth_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
)

# user_id is automatic from JWT
history = await client.get_recent_history(
    agent_id="chatbot",  # Which agent handled this conversation?
    limit=10
)
# Returns memories for: tenant="acme-corp" (JWT) + user="alice" (JWT) + agent="chatbot" (param)
```

**Production Mode - API Key (Agent Operations)**:

```python
from soorma.memory.client import MemoryClient

# API Key contains: {"tenant_id": "acme-corp", "agent_id": "processor", ...}
client = MemoryClient(
    base_url="https://memory.soorma.ai",
    api_key="sk_test_abc123..."
)

# user_id MUST be explicit
await client.log_interaction(
    agent_id="processor",
    user_id="alice",  # ← REQUIRED: which user does this belong to?
    role="system",
    content="Scheduled task completed"
)
# Stored with: tenant="acme-corp" (API Key) + user="alice" (param) + agent="processor" (param)
```

**Authentication Token Structures**:

```json
// JWT Token (User Authentication)
{
  "tenant_id": "acme-corp-uuid",
  "user_id": "alice-uuid",
  "sub": "alice@acme.com",
  "iat": 1703347200,
  "exp": 1703433600
}
```

**Key Points**:
- ✅ **No explicit tenant/user parameters** in SDK method calls
- ✅ **Automatic extraction** from JWT token on server side
- ✅ **Row Level Security (RLS)** enforces tenant isolation in PostgreSQL
- ✅ **Seamless development** with default values in local mode
- ✅ **Production-ready** with JWT-based multi-tenancy

**Managing Procedural Memory (Current Workaround)**:

Until write APIs are available, procedural memories can be added directly to the database:

```sql
-- Add a system prompt customization for User A
INSERT INTO procedural_memory (
    tenant_id, user_id, agent_id,
    procedure_type, trigger_condition, content, embedding
) VALUES (
    'tenant-uuid',
    'user-a-uuid',
    'researcher',
    'system_prompt',
    'research tasks requiring citations',
    'Always cite sources in APA format. Verify publication dates are within the last 5 years unless specifically requested otherwise.',
    (SELECT embedding FROM generate_embedding('research citation formatting'))
);

-- Add a few-shot example
INSERT INTO procedural_memory (
    tenant_id, user_id, agent_id,
    procedure_type, trigger_condition, content, embedding
) VALUES (
    'tenant-uuid',
    'user-a-uuid',
    'researcher',
    'few_shot_example',
    'summarizing scientific papers',
    'Example: "Paper: Climate Change Effects\nSummary: This study (Smith et al., 2023) demonstrates that..."',
    (SELECT embedding FROM generate_embedding('paper summarization example'))
);
```

**Upcoming Write API (v0.6.0)**:

```python
# Future SDK API (planned)
from soorma.memory.client import MemoryClient

client = MemoryClient(base_url="http://localhost:8083")

# Add a system prompt customization
await client.add_procedural_memory(
    agent_id="researcher",
    procedure_type="system_prompt",
    trigger_condition="research tasks requiring citations",
    content="Always cite sources in APA format",
)

# Add a few-shot example
await client.add_procedural_memory(
    agent_id="researcher", 
    procedure_type="few_shot_example",
    trigger_condition="summarizing scientific papers",
    content="Example: Paper: Climate Change Effects\nSummary: This study (Smith et al., 2023)...",
)
```

### Working Memory

**Purpose**: Store plan-scoped shared state for multi-agent collaboration.

**Use Cases**:
- Plan execution state
- Multi-agent coordination
- Shared variables
- Task context

**Plan Isolation**: Each plan has its own isolated key-value namespace.

**Example**:

```python
from soorma.memory.client import MemoryClient

client = MemoryClient(base_url="http://localhost:8083")

# Store plan state
await client.set_plan_state(
    plan_id="research-plan-1",
    key="research_summary",
    value={
        "topic": "AI Safety",
        "papers_found": 50,
        "papers_analyzed": 10,
        "current_phase": "analysis",
        "findings": [
            "Alignment problem is critical",
            "Need better interpretability"
        ]
    }
)

# Retrieve plan state
state = await client.get_plan_state(
    plan_id="research-plan-1",
    key="research_summary"
)

print(f"Current phase: {state.value['current_phase']}")
print(f"Progress: {state.value['papers_analyzed']}/{state.value['papers_found']}")

# Another agent can access the same state
state = await client.get_plan_state(
    plan_id="research-plan-1",
    key="research_summary"
)
# Both agents see the same data
```

## API Reference

> **Note**: The current implementation (v0.5.0) only supports JWT authentication. API Key authentication with explicit `user_id` parameters is planned for v0.6.0.

### Context Wrapper API (`soorma.context.MemoryClient`)

#### Working Memory

```python
async def store(
    key: str,
    value: Any,
    plan_id: Optional[str] = None,
    memory_type: str = "working"
) -> bool
```

```python
async def retrieve(
    key: str,
    plan_id: Optional[str] = None
) -> Optional[Any]
```

```python
async def delete(
    key: str,
    plan_id: Optional[str] = None
) -> bool
```

#### Semantic Memory

```python
async def search(
    query: str,
    memory_type: str = "semantic",
    limit: int = 5
) -> List[Dict[str, Any]]
```

#### Episodic Memory

```python
async def log_interaction(
    agent_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool
```

```python
async def get_recent_history(
    agent_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]
```

#### Procedural Memory

```python
async def get_relevant_skills(
    agent_id: str,
    context: str,
    limit: int = 3
) -> List[Dict[str, Any]]
```

#### Lifecycle

```python
async def close() -> None
```

### Direct Client API (`soorma.memory.client.MemoryClient`)

#### Semantic Memory

```python
async def store_knowledge(
    content: str,
    metadata: Dict[str, Any] = None
) -> str
```

```python
async def search_knowledge(
    query: str,
    limit: int = 5
) -> List[SemanticMemoryResponse]
```

#### Episodic Memory

```python
async def log_interaction(
    agent_id: str,
    role: str,
    content: str,
    metadata: Dict[str, Any] = None
) -> str
```

```python
async def get_recent_history(
    agent_id: str,
    limit: int = 10
) -> List[EpisodicMemoryResponse]
```

```python
async def search_interactions(
    agent_id: str,
    query: str,
    limit: int = 5
) -> List[EpisodicMemoryResponse]
```

#### Procedural Memory

```python
async def get_relevant_skills(
    agent_id: str,
    context: str,
    limit: int = 3
) -> List[ProceduralMemoryResponse]
```

#### Working Memory

```python
async def set_plan_state(
    plan_id: str,
    key: str,
    value: Dict[str, Any]
) -> str
```

```python
async def get_plan_state(
    plan_id: str,
    key: str
) -> WorkingMemoryResponse
```

#### Health & Lifecycle

```python
async def health() -> Dict[str, str]
```

```python
async def close() -> None
```

## Advanced Usage

### Agent Personalization with Procedural Memory

Procedural memory enables **user-specific agent customization** while maintaining a shared baseline. This allows different users to experience personalized agent behavior without modifying the core agent code.

**Architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Baseline Agent Code                       │
│  - Default instructions                                      │
│  - Standard capabilities                                     │
│  - Core behavior                                             │
└──────────────────────┬───────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │   Procedural Memory     │
          │   (Per User/Tenant)     │
          ├─────────────────────────┤
          │  User A: APA citations  │
          │  User B: Casual tone    │
          │  User C: Technical depth│
          └────────────┬────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
    ┌─────▼────┐  ┌─────▼─────┐  ┌─▼────────┐
    │ Agent    │  │  Agent    │  │  Agent   │
    │ for      │  │  for      │  │  for     │
    │ User A   │  │  User B   │  │  User C  │
    └──────────┘  └───────────┘  └──────────┘
```

**Scoping Model**:

```
Procedural Memory Scope = Tenant ID + User ID + Agent ID

Examples:
- Tenant "Acme Corp" + User "alice@acme.com" + Agent "researcher"
  → Alice's personal research assistant preferences
  
- Tenant "Acme Corp" + User "bob@acme.com" + Agent "researcher" 
  → Bob's personal research assistant preferences
  
- Same baseline "researcher" agent, different behaviors per user
```

**Implementation Pattern**:

```python
from soorma import PlatformContext
from typing import List, Dict, Any

class PersonalizedAgent:
    """Agent with user-specific behavior via procedural memory."""
    
    def __init__(self, agent_id: str, baseline_prompt: str):
        self.agent_id = agent_id
        self.baseline_prompt = baseline_prompt
    
    async def get_personalized_prompt(
        self, 
        context: PlatformContext,
        task_context: str
    ) -> str:
        """Build personalized prompt from baseline + user preferences."""
        
        # Retrieve user-specific customizations
        skills = await context.memory.get_relevant_skills(
            agent_id=self.agent_id,
            context=task_context,
            limit=5
        )
        
        # Start with baseline
        prompt_parts = [self.baseline_prompt]
        
        # Add system prompt customizations
        system_prompts = [
            s.content for s in skills 
            if s.procedure_type == "system_prompt"
        ]
        if system_prompts:
            prompt_parts.append("\n## User Preferences:")
            prompt_parts.extend(system_prompts)
        
        # Add few-shot examples
        examples = [
            s.content for s in skills
            if s.procedure_type == "few_shot_example"
        ]
        if examples:
            prompt_parts.append("\n## Examples:")
            prompt_parts.extend(examples)
        
        return "\n\n".join(prompt_parts)
    
    async def execute_task(
        self,
        task: Dict[str, Any],
        context: PlatformContext
    ) -> str:
        """Execute task with personalized behavior."""
        
        # Get personalized instructions
        personalized_prompt = await self.get_personalized_prompt(
            context,
            task_context=task.get("description", "")
        )
        
        # Use with LLM
        response = await llm_client.generate(
            system=personalized_prompt,
            user=task["query"]
        )
        
        return response

# Usage
agent = PersonalizedAgent(
    agent_id="research-assistant",
    baseline_prompt="You are a helpful research assistant."
)

# User A gets their personalized version
result_a = await agent.execute_task(task, context_user_a)

# User B gets their personalized version  
result_b = await agent.execute_task(task, context_user_b)
```

**Learning User Preferences**:

```python
async def learn_from_feedback(
    user_feedback: Dict[str, Any],
    context: PlatformContext
):
    """Learn user preferences from explicit feedback."""
    
    if user_feedback["type"] == "citation_format":
        # Add procedural memory for citation preferences
        # Note: Currently requires direct database access
        # Future: Will use client.add_procedural_memory()
        
        preference = f"Use {user_feedback['format']} citation style"
        
        # Store in procedural memory (conceptual - API coming in v0.6.0)
        await context.memory.add_procedural_memory(
            agent_id="researcher",
            procedure_type="system_prompt",
            trigger_condition="research and citation tasks",
            content=preference
        )
        
        print(f"Learned preference: {preference}")
```

**Multi-Tenant Isolation**:

Procedural memory is automatically isolated by tenant ID through Row Level Security (RLS):

```python
# Tenant A's agent
context_a = PlatformContext()  # auth_token contains tenant_id = "tenant-a"
skills_a = await context_a.memory.get_relevant_skills("researcher", "task")
# Only sees Tenant A's procedural memories

# Tenant B's agent
context_b = PlatformContext()  # auth_token contains tenant_id = "tenant-b"  
skills_b = await context_b.memory.get_relevant_skills("researcher", "task")
# Only sees Tenant B's procedural memories

# Complete isolation - no cross-tenant data leakage
```

### Multi-Tenant Usage

**Dual Authentication Model**:

The Memory Service supports **two authentication modes**:

1. **JWT Token** (User-to-Service): Contains `tenant_id` + `user_id`
2. **API Key** (Agent-to-Service): Contains `tenant_id` + `agent_id`

This dual model enables both **end-user interactions** and **autonomous agent operations** with proper tenant isolation.

**Why Two Modes?**

```
┌─────────────────────────────────────────────────────────────┐
│                    Authentication Scenarios                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Scenario 1: User interacts with application               │
│  ┌──────┐  JWT (tenant+user)  ┌──────────┐                 │
│  │ User ├──────────────────────► Service  │                 │
│  └──────┘                      └──────────┘                 │
│  - User authenticated via OAuth/login                       │
│  - tenant_id + user_id from JWT token                       │
│  - Memories scoped to specific user                         │
│                                                             │
│  Scenario 2: Agent performs autonomous task                │
│  ┌───────┐  API Key (tenant+agent)  ┌──────────┐           │
│  │ Agent ├───────────────────────────► Service  │           │
│  └───────┘                           └──────────┘           │
│  - Agent authenticated via API Key                          │
│  - tenant_id + agent_id from API Key                        │
│  - Must specify user_id explicitly in method params         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**JWT Authentication (User Context)**:

```python
from soorma.memory.client import MemoryClient

# JWT token provides tenant_id + user_id automatically
client = MemoryClient(
    base_url="https://memory.soorma.ai",
    auth_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJhY21lLWNvcnAiLCJ1c2VyX2lkIjoiYWxpY2UiLCAic3ViIjoiYWxpY2VAYWNtZS5jb20ifQ..."
)

# User context is automatic - no need to pass user_id
await client.log_interaction(
    agent_id="chatbot",
    role="user",
    content="What's the weather?",
)
# Stored with tenant_id + user_id from JWT

# Search is automatically scoped to this user's history
history = await client.get_recent_history("chatbot", limit=10)
# Only sees memories for user_id from JWT
```

**API Key Authentication (Agent Context)**:

```python
from soorma.memory.client import MemoryClient

# API Key provides tenant_id + agent_id automatically
client = MemoryClient(
    base_url="https://memory.soorma.ai",
    api_key="sk_test_abc123..."  # Contains tenant_id + agent_id
)

# Agent must specify user_id explicitly
await client.log_interaction(
    agent_id="background-processor",
    user_id="alice",  # ← EXPLICIT parameter (not from auth)
    role="system",
    content="Scheduled report generated",
)
# Stored with tenant_id from API Key, user_id from parameter

# Agent must pass user_id for user-specific queries
history = await client.get_recent_history(
    agent_id="background-processor",
    user_id="alice",  # ← EXPLICIT parameter
    limit=10
)
```

**Why Agent ID is Always Explicit**:

```python
# Both JWT and API Key scenarios require explicit agent_id parameter
# Reason: Multiple agents can serve the same user/tenant

# JWT Auth (user context)
await client.log_interaction(
    agent_id="chatbot",      # ← EXPLICIT: which agent handled this?
    role="user",
    content="Hello"
)

# API Key Auth (agent context)
await client.log_interaction(
    agent_id="background-processor",  # ← EXPLICIT: which agent is this?
    user_id="alice",                  # ← EXPLICIT: which user?
    role="system",
    content="Task complete"
)
```

**Token/Key Formats**:

```json
// JWT Token (User Auth)
{
  "tenant_id": "acme-corp-uuid",        // Required: Tenant identifier
  "user_id": "alice-uuid",              // Required: User identifier
  "sub": "alice@acme.com",              // Optional: Subject (email)
  "iat": 1703347200,                    // Issued at
  "exp": 1703433600                     // Expiration
}

// API Key (Agent Auth)
{
  "tenant_id": "acme-corp-uuid",        // Required: Tenant identifier
  "agent_id": "background-processor",   // Required: Agent identifier
  "permissions": ["memory:read", "memory:write"],
  "iat": 1703347200,
  "exp": 1735689600                     // Longer expiration for API keys
}
```

**Development vs Production**:

```python
# Development Mode (local testing)
client = MemoryClient(base_url="http://localhost:8083")
# No auth needed - uses default tenant/user/agent IDs

# Production Mode - JWT (User Context)
client = MemoryClient(
    base_url="https://memory.soorma.ai",
    auth_token="<jwt-token>"  # tenant_id + user_id
)

# Production Mode - API Key (Agent Context)
client = MemoryClient(
    base_url="https://memory.soorma.ai",
    api_key="sk_test_..."  # tenant_id + agent_id
)
```

**Server-Side Middleware**:

The Memory Service middleware handles both authentication modes:

```python
# Memory Service middleware (automatic)
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Try JWT first
    if "Authorization" in request.headers:
        token = request.headers["Authorization"].replace("Bearer ", "")
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        
        # JWT provides tenant_id + user_id
        tenant_id = payload["tenant_id"]
        user_id = payload.get("user_id")  # From JWT
        
    # Fallback to API Key
    elif "X-API-Key" in request.headers:
        api_key = request.headers["X-API-Key"]
        payload = verify_api_key(api_key)
        
        # API Key provides tenant_id + agent_id
        tenant_id = payload["tenant_id"]
        user_id = None  # Must come from request parameters
    
    # Set PostgreSQL session context for RLS
    await db.execute(f"SET app.tenant_id = '{tenant_id}'")
    if user_id:
        await db.execute(f"SET app.user_id = '{user_id}'")
    
    return await call_next(request)
```

**Row Level Security (RLS) Policies**:

PostgreSQL RLS ensures data isolation at the database level:

```sql
-- Semantic memory RLS policy
CREATE POLICY semantic_tenant_isolation ON semantic_memory
    USING (tenant_id::text = current_setting('app.tenant_id')
       AND user_id::text = current_setting('app.user_id'));

-- Users can only see their own memories
-- Even if SQL injection occurs, RLS prevents cross-tenant access
```

### Embedding Configuration

By default, Memory Service uses OpenAI's `text-embedding-3-small` model. Configure via environment variables:

```bash
# Memory Service configuration
export OPENAI_API_KEY="your-api-key"
export EMBEDDING_MODEL="text-embedding-3-small"  # or text-embedding-3-large
export EMBEDDING_DIMENSIONS=1536
```

### Error Handling

```python
from soorma.memory.client import MemoryClient
from httpx import HTTPStatusError

client = MemoryClient(base_url="http://localhost:8083")

try:
    # Store knowledge
    memory_id = await client.store_knowledge(
        content="Important information",
        metadata={"priority": "high"}
    )
except HTTPStatusError as e:
    if e.response.status_code == 404:
        print("Memory not found")
    elif e.response.status_code == 401:
        print("Authentication failed")
    elif e.response.status_code == 500:
        print("Server error")
    else:
        print(f"HTTP error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    await client.close()
```

### Context Manager Pattern

```python
from soorma.memory.client import MemoryClient

async with MemoryClient(base_url="http://localhost:8083") as client:
    # Store knowledge
    await client.store_knowledge("Python is awesome")
    
    # Search
    results = await client.search_knowledge("programming", limit=5)
    
    # Automatic cleanup on exit
```

### Batch Operations

```python
from soorma.memory.client import MemoryClient

client = MemoryClient(base_url="http://localhost:8083")

# Store multiple knowledge entries
knowledge_base = [
    "Python is a programming language",
    "JavaScript is used for web development",
    "Rust is a systems programming language",
    "Go is designed for concurrency"
]

memory_ids = []
for content in knowledge_base:
    memory_id = await client.store_knowledge(
        content=content,
        metadata={"category": "programming"}
    )
    memory_ids.append(memory_id)

print(f"Stored {len(memory_ids)} knowledge entries")

await client.close()
```

## Best Practices

### 1. Use Context Wrapper for Agents

```python
# ✅ Good - automatic fallback, simpler API
from soorma import PlatformContext

async def my_agent_task(task, context: PlatformContext):
    # Works in dev (local) and prod (service)
    state = await context.memory.retrieve("task_state")
    
# ❌ Avoid - requires manual fallback handling
from soorma.memory.client import MemoryClient
client = MemoryClient()
# No automatic fallback
```

### 2. Always Close Connections

```python
# ✅ Good - explicit cleanup
context = PlatformContext()
try:
    await context.memory.store("key", "value")
finally:
    await context.memory.close()

# ✅ Better - context manager
async with MemoryClient() as client:
    await client.store_knowledge("content")
```

### 3. Use Meaningful Metadata

```python
# ✅ Good - rich metadata for filtering
await client.store_knowledge(
    content="Deploy with Docker",
    metadata={
        "category": "devops",
        "topic": "deployment",
        "difficulty": "intermediate",
        "last_updated": "2025-12-23",
        "author": "team-platform"
    }
)

# ❌ Bad - no metadata
await client.store_knowledge("Deploy with Docker")
```

### 4. Scope Working Memory to Plans

```python
# ✅ Good - plan-isolated state
await context.memory.store(
    key="research_results",
    value=data,
    plan_id="research-plan-1"
)

# ✅ Good - different plan, different namespace
await context.memory.store(
    key="research_results",
    value=other_data,
    plan_id="research-plan-2"
)
```

### 5. Use Appropriate Memory Types

```python
# ✅ Semantic: Facts and knowledge
await client.store_knowledge("Python supports type hints since 3.5")

# ✅ Episodic: Interactions and history
await client.log_interaction(agent_id="bot", role="user", content="Hello")

# ✅ Working: Temporary task state
await context.memory.store("current_step", 3, plan_id="plan-1")

# ❌ Wrong: Using working memory for persistent knowledge
await context.memory.store("python_info", "Type hints since 3.5")
```

### 6. Limit Search Results

```python
# ✅ Good - reasonable limit
results = await client.search_knowledge("python", limit=5)

# ❌ Bad - too many results, slow performance
results = await client.search_knowledge("python", limit=1000)
```

### 7. Handle Fallback Mode

```python
# ✅ Good - check for features
context = PlatformContext()

# Semantic search requires Memory Service
results = await context.memory.search("query")
if not results:
    # Fallback to alternative logic
    print("Memory Service unavailable, using local mode")
```

## Testing

### Unit Tests with Mocks

```python
import pytest
from unittest.mock import AsyncMock
from soorma.memory.client import MemoryClient

@pytest.mark.asyncio
async def test_store_knowledge():
    # Mock the HTTP client
    client = MemoryClient(base_url="http://test")
    client._client = AsyncMock()
    
    # Mock response
    client._client.post.return_value.status_code = 201
    client._client.post.return_value.json.return_value = {"id": "mem-123"}
    
    # Test
    memory_id = await client.store_knowledge("test content")
    
    # Verify
    assert memory_id == "mem-123"
    client._client.post.assert_called_once()
```

### Integration Tests

```python
import pytest
from soorma.memory.client import MemoryClient

@pytest.mark.asyncio
@pytest.mark.integration
async def test_memory_lifecycle():
    """Requires running Memory Service"""
    client = MemoryClient(base_url="http://localhost:8083")
    
    try:
        # Store
        memory_id = await client.store_knowledge(
            content="Integration test content",
            metadata={"test": True}
        )
        assert memory_id
        
        # Search
        results = await client.search_knowledge("integration test", limit=1)
        assert len(results) > 0
        assert "integration test" in results[0].content.lower()
        
    finally:
        await client.close()
```

### Test Fixtures

```python
# tests/conftest.py
import pytest
from soorma.memory.client import MemoryClient

@pytest.fixture
async def memory_client():
    """Provide a memory client for tests"""
    client = MemoryClient(base_url="http://localhost:8083")
    yield client
    await client.close()

@pytest.fixture
def mock_memory_client():
    """Provide a mocked memory client"""
    return AsyncMock(spec=MemoryClient)
```

## Related Documentation

- [Memory Service Architecture](../../../services/memory/ARCHITECTURE.md) - Memory Service design and implementation
- [Memory Service API](../../../services/memory/README.md) - REST API endpoints and deployment guide
- [Event Architecture](EVENT_ARCHITECTURE.md) - Event-driven agent choreography patterns
- [SDK README](../README.md) - Python SDK overview and quick start
- [Main README](../../../README.md) - Soorma platform overview

## Troubleshooting

### Connection Errors

```python
# Problem: Cannot connect to Memory Service
# Solution: Check if service is running
soorma dev --start

# Or verify connection
curl http://localhost:8083/health
```

### Embedding Errors

```python
# Problem: "OpenAI API key not configured"
# Solution: Set environment variable
export OPENAI_API_KEY="your-api-key"

# Restart Memory Service
soorma dev --stop
soorma dev --start
```

### Search Returns No Results

```python
# Problem: Semantic search returns empty list
# Cause: No memories stored yet, or query too specific

# Solution: Store some memories first
await client.store_knowledge("Some content to search")

# Then search with broader query
results = await client.search_knowledge("content", limit=5)
```

### Plan State Not Found

```python
# Problem: get_plan_state returns 404
# Cause: Key doesn't exist in that plan

# Solution: Always set state before retrieving
await client.set_plan_state("plan-1", "key", {"value": 1})
state = await client.get_plan_state("plan-1", "key")
```

## Version History

See [CHANGELOG.md](../CHANGELOG.md) for SDK version history.
