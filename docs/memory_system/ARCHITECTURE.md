# Memory System: Technical Architecture

**Status:** ✅ Stage 2 Complete (January 30, 2026)  
**Last Updated:** February 15, 2026  
**Related Stages:** Stage 2 (RF-ARCH-008, RF-ARCH-009, RF-SDK-006, RF-SDK-007, RF-SDK-008), Stage 2.1 (RF-ARCH-012, RF-ARCH-013, RF-ARCH-014)

---

## Executive Summary

The Soorma Memory Service provides a unified, persistent memory layer for autonomous agents, implementing the **CoALA (Cognitive Architectures for Language Agents)** framework with enterprise-grade multi-tenancy. It leverages **PostgreSQL + pgvector** to handle both relational state and semantic (vector) retrieval in a single infrastructure.

**Key Design Principles:**
- **Four Memory Types:** Semantic, Episodic, Procedural, Working (per CoALA framework)
- **Database-Level Security:** Row Level Security (RLS) enforces tenant isolation
- **Vector Search:** pgvector with HNSW indexes for sub-millisecond semantic retrieval
- **Multi-Tenancy:** Native tenant/user isolation via RLS policies

---

## CoALA Framework

The service implements four memory types modeled after human cognition:

| Memory Type | Description | Soorma Implementation |
|------------|-------------|----------------------|
| **Working Memory** | Short-term scratchpad for active tasks | Key-Value store scoped to Plans |
| **Episodic Memory** | History of past experiences | Time-series interaction logs with embeddings |
| **Semantic Memory** | Factual knowledge | Knowledge Base (RAG) with tenant-wide access |
| **Procedural Memory** | Know-how, rules, decision logic | Dynamic prompt injection and few-shot examples |

---

## Security & Multi-Tenancy

### Multi-Tenancy (Native)

**Requirement:** Agents must only access memories matching their specific Tenant ID.

**Implementation:** Enforced via **PostgreSQL Row Level Security (RLS)**. Application-level bugs cannot leak data between tenants—the database physically restricts row visibility.

### User-Level Personalization

**User Identity Clarification:**

The `user_id` parameter represents **either a human end user OR an autonomous agent identity**:
- **Human-driven systems:** `user_id` = authenticated end user (e.g., "alice", "bob")
- **Autonomous agent systems:** `user_id` = agent identity (e.g., "research-agent", "monitoring-bot")
- **Hybrid systems:** Mix of both (users interact with agents, agents work autonomously)

**Scoping:**
- **Episodic:** Private to User/Agent pair
- **Procedural:** Private to User/Agent pair (personalized skills)
- **Semantic:** Shared across Tenant by default, `user_id` enables optional restrictions
- **Working:** Scoped to `plan_id` (collaborative access among authorized agents)

### Goal/Plan Context

**Requirement:** Multiple agents working on a single goal need shared state.

**Solution:** Working Memory is scoped to `plan_id`, allowing collaborative access.

---

## Database Schema Design

**Infrastructure:** PostgreSQL + pgvector extension (mandatory)

**Why PostgreSQL + pgvector:**
- Vector embeddings are core value proposition
- pgvector's HNSW indexes: sub-millisecond semantic search at scale
- Row Level Security (RLS): tenant isolation at database level
- JSONB support for flexible metadata storage

### Core Identity (Local Replicas)

**Note:** `tenants` and `users` tables are local replicas, not authentication source of truth. They exist for:
- **Data Integrity:** Foreign Key constraints
- **Lifecycle Management:** ON DELETE CASCADE (instant cleanup when tenant deleted)

```sql
-- Enable Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tenants & Users (Synced from Identity Service)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
```

### Semantic Memory (Knowledge Base)

Stores facts shared across the tenant (RAG use case).

```sql
CREATE TABLE semantic_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    
    content TEXT NOT NULL,          -- Knowledge chunk
    embedding VECTOR(1536),         -- Semantic search vector
    metadata JSONB DEFAULT '{}',    -- Source info (doc_id, page)
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes & Security
CREATE INDEX semantic_embedding_idx ON semantic_memory 
    USING hnsw (embedding vector_cosine_ops);
ALTER TABLE semantic_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON semantic_memory
    USING (tenant_id = current_setting('app.current_tenant')::UUID);
```

**Stage 2.1 Enhancements (RF-ARCH-012, RF-ARCH-014):**
- **Upsert:** Prevent duplicates via content-based deduplication
- **Privacy:** Optional `user_id` for agent-specific knowledge bases

### Episodic Memory (Experience)

Stores interaction history specific to User + Agent.

```sql
CREATE TABLE episodic_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,         -- e.g., "researcher-1"
    
    role TEXT CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    embedding VECTOR(1536),         -- For "What did we discuss?"
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes & Security
CREATE INDEX episodic_embedding_idx ON episodic_memory 
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX episodic_time_idx ON episodic_memory 
    (user_id, agent_id, created_at DESC);
ALTER TABLE episodic_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_agent_isolation ON episodic_memory
    USING (
        tenant_id = current_setting('app.current_tenant')::UUID 
        AND user_id = current_setting('app.current_user')::UUID
    );
```

### Procedural Memory (Skills)

Stores dynamic prompts and rules.

```sql
CREATE TABLE procedural_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    
    trigger_condition TEXT,         -- e.g., "User asks about billing"
    embedding VECTOR(1536),         -- Vector match on User Query
    
    procedure_type TEXT CHECK (procedure_type IN ('system_prompt', 'few_shot_example')),
    content TEXT NOT NULL,          -- e.g., "Always check Stripe first."
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes & Security
CREATE INDEX procedural_embedding_idx ON procedural_memory 
    USING hnsw (embedding vector_cosine_ops);
ALTER TABLE procedural_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY procedural_isolation ON procedural_memory
    USING (
        tenant_id = current_setting('app.current_tenant')::UUID 
        AND user_id = current_setting('app.current_user')::UUID
    );
```

### Working Memory (Plan State)

Stores shared state for specific Plan execution.

```sql
CREATE TABLE working_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL,          -- Shared context ID
    
    key TEXT NOT NULL,              -- e.g., "research_summary"
    value JSONB NOT NULL,           -- e.g., { "confidence": 0.9, "data": "..." }
    
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(plan_id, key)
);

-- Indexes & Security
ALTER TABLE working_memory ENABLE ROW LEVEL SECURITY;
CREATE POLICY plan_isolation ON working_memory
    USING (tenant_id = current_setting('app.current_tenant')::UUID);
```

**Stage 2.1 Enhancement (RF-ARCH-013):**
- **Deletion:** DELETE endpoints to remove sensitive data immediately

---

## Stage 2 Enhancements

### TaskContext Memory Type (RF-ARCH-008)

**Problem:** Workers need persistent state when delegating to sub-agents.

**Solution:** Dedicated task context storage with sub-task tracking.

```sql
CREATE TABLE task_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    task_id VARCHAR(100) NOT NULL,
    plan_id VARCHAR(100),
    event_type VARCHAR(255) NOT NULL,
    response_event VARCHAR(255),
    response_topic VARCHAR(100) DEFAULT 'action-results',
    data JSONB NOT NULL DEFAULT '{}',
    sub_tasks JSONB DEFAULT '[]',
    state JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, task_id)
);

CREATE INDEX task_context_plan_idx ON task_context (tenant_id, plan_id);
CREATE INDEX task_context_subtasks_idx ON task_context USING GIN (sub_tasks);
```

**Endpoints:**

```python
# Store task context
POST /v1/memory/task-context
{
    "task_id": "task-123",
    "plan_id": "plan-456",
    "event_type": "research.requested",
    "response_event": "research.completed",
    "data": {...},
    "sub_tasks": [],
    "state": {}
}

# Retrieve task context
GET /v1/memory/task-context/{task_id}

# Update task context
PUT /v1/memory/task-context/{task_id}
{
    "sub_tasks": ["subtask-1", "subtask-2"],
    "state": {"progress": 0.75}
}

# Find parent task by sub-task ID
GET /v1/memory/task-context/by-subtask/{subtask_id}

# Delete task context
DELETE /v1/memory/task-context/{task_id}
```

### Plan/Session Query APIs (RF-ARCH-009)

**Problem:** Users need to list active plans and conversation sessions.

**Solution:** Memory Service query endpoints.

```sql
-- Plans table
CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    plan_id VARCHAR(100) NOT NULL,
    goal_event VARCHAR(255) NOT NULL,
    goal_data JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'running',
    state JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, plan_id)
);

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    agent_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_interaction TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    UNIQUE(tenant_id, session_id)
);
```

**Endpoints:**

```python
# Plans
POST /v1/memory/plans
GET /v1/memory/plans?status=active&limit=10
GET /v1/memory/plans/{plan_id}
PUT /v1/memory/plans/{plan_id}
DELETE /v1/memory/plans/{plan_id}

# Sessions
POST /v1/memory/sessions
GET /v1/memory/sessions?limit=10
GET /v1/memory/sessions/{session_id}
PUT /v1/memory/sessions/{session_id}
DELETE /v1/memory/sessions/{session_id}
```

---

## API Specification

### Authentication & Tenancy Strategy

#### Local Development (Single Tenant)

Default to predefined Tenant UUID:

```sql
INSERT INTO tenants (id, name) 
VALUES ('00000000-0000-0000-0000-000000000000', 'Default Tenant') 
ON CONFLICT DO NOTHING;
```

#### Production (Multi-Tenant)

**Lazy Population:** Extract `tenant_id` from auth token, UPSERT if not exists.

**Session Context Execution:**

```sql
SET app.current_tenant = '<extracted_uuid>';
SET app.current_user = '<extracted_uuid>';
```

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /v1/memory/semantic | Ingest knowledge (text + metadata) |
| GET | /v1/memory/semantic/search?q=query | Semantic retrieval |
| POST | /v1/memory/episodic | Log interaction |
| GET | /v1/memory/episodic/recent?limit=N | Fetch recent history |
| GET | /v1/memory/episodic/search?q=query | Long-term recall |
| GET | /v1/memory/procedural/context?q=query | Fetch relevant rules/prompts |
| PUT | /v1/memory/working/{plan}/{key} | Set shared state |
| GET | /v1/memory/working/{plan}/{key} | Get shared state |

### Stage 2.1 Endpoints

**Semantic Memory Upsert (RF-ARCH-012):**

```python
POST /v1/memory/semantic/upsert
{
    "content": "Python was created by Guido van Rossum.",
    "metadata": {...},
    "dedupe_threshold": 0.95  # Similarity threshold
}

# Returns: {"status": "created"} or {"status": "updated", "id": "..."}
```

**Working Memory Deletion (RF-ARCH-013):**

```python
DELETE /v1/memory/working/{plan_id}/{key}  # Delete specific key
DELETE /v1/memory/working/{plan_id}        # Delete all plan state
```

**Semantic Memory Privacy (RF-ARCH-014):**

```python
POST /v1/memory/semantic
{
    "content": "Agent-specific knowledge",
    "user_id": "research-agent",  # Optional: agent-scoped
    "public": false               # Default: false (private to user_id)
}
```

---

## Architectural Design Decisions

### 1. Replica Table Strategy

**Decision:** Maintain local replica tables for `tenants` and `users`.

**Rationale:**
- **Data Integrity:** Enforces Foreign Key constraints locally
- **Lifecycle Management:** ON DELETE CASCADE automatically wipes vector data when tenant deleted

### 2. Relational Cascade Logic

**Decision:** ON DELETE CASCADE on child tables, not root `tenants` table.

**Rationale:** In RDBMS design, deletion rule belongs to dependent (child) table. Creates reliable chain reaction: `tenants` → `users` → `episodic_memory`.

### 3. UUID Primary Keys

**Decision:** Use UUID (uuid_generate_v4()) for all Primary Keys.

**Rationale:**
- **Security:** Prevents ID enumeration attacks
- **Distributed Generation:** Application/SDK can generate IDs before insertion
- **Write Distribution:** Random UUIDs prevent "hot spots" in high-throughput systems

### 4. PostgreSQL Session Variables for RLS

**Decision:** Use `app.current_tenant` and `app.current_user` session variables for RLS policies.

**Implementation:**

```sql
-- Middleware sets session variables
SET app.current_tenant = '<tenant_uuid>';
SET app.current_user = '<user_uuid>';

-- RLS policies reference these
CREATE POLICY tenant_isolation_policy ON semantic_memory
    USING (tenant_id = current_setting('app.current_tenant')::UUID);
```

**Rationale:**
- **Database-Level Security:** RLS enforcement at PostgreSQL engine level
- **Zero Overhead:** No need for `WHERE tenant_id = ?` in queries
- **Transparency:** Application code doesn't manage security clauses
- **Performance:** Session variables avoid JOIN operations

**Security Properties:**
1. **Defense in Depth:** Even if middleware fails, RLS blocks access
2. **Immutability:** Session variables reset when connection returns to pool
3. **Audit Trail:** All queries execute within specific tenant/user context

**Code Reference:** `services/memory/src/memory_service/core/database.py` (`set_session_context()`)

---

## WorkflowState Helper

**Purpose:** Reduce boilerplate for Working Memory operations (8x less code).

**SDK Implementation (RF-SDK-008):**

```python
from soorma.workflow import WorkflowState

# Initialize
state = WorkflowState(context.memory, plan_id)

# Store/retrieve
await state.set("research_data", {"findings": [...]})
data = await state.get("research_data")

# Track actions
await state.record_action("research.completed")
history = await state.get_action_history()

# Cleanup
deleted = await state.delete("api_key")
count = await state.cleanup()  # Delete all plan state
```

**vs. Manual API:**

```python
# Manual (verbose)
await context.memory.set_plan_state(
    plan_id="plan-123",
    key="research_data",
    value={"findings": [...]}
)

response = await context.memory.get_plan_state(
    plan_id="plan-123",
    key="research_data"
)
data = response.value
```

---

## Performance Characteristics

### Throughput

- **HNSW Indexes:** Sub-millisecond vector similarity search
- **RLS Policies:** Near-zero overhead (uses session variables)
- **Embeddings:** Generated asynchronously (OpenAI text-embedding-3-small or local models)

### Scalability

- **Horizontal:** Add read replicas for queries
- **Vertical:** PostgreSQL cluster with replication
- **Partitioning:** Future enhancement (partition by tenant_id)

### Reliability

- **ACID Guarantees:** PostgreSQL transactions
- **Cascade Deletion:** Automatic cleanup of orphaned records
- **Connection Pooling:** PgBouncer for high-concurrency workloads

---

## Operational Workflow Example

**Scenario:** User asks, "Why did my billing fail?"

1. **Recall Skills (Procedural):** Agent queries `/procedural/context`
   - Result: "When discussing billing, check Stripe status first." (Added to System Prompt)

2. **Recall Facts (Semantic):** Agent queries `/semantic/search`
   - Result: "Error 402 means insufficient funds."

3. **Check State (Working):** Agent queries `/working/{plan_id}/account_id`
   - Result: "acc_123"

4. **Execute & Log (Episodic):** Agent replies and calls `POST /episodic`

---

## Implementation Status

### Stage 2: Foundation (✅ January 21, 2026)

**Completed Tasks:**
- ✅ RF-ARCH-008: TaskContext memory type
- ✅ RF-ARCH-009: Plan/Session query APIs
- ✅ RF-SDK-006: MemoryClient methods
- ✅ RF-SDK-007: TaskContext SDK
- ✅ RF-SDK-008: WorkflowState helper
- ✅ Database schema and migrations
- ✅ Examples: 04-memory-semantic, 05-memory-working, 06-memory-episodic

### Stage 2.1: Enhancements (✅ January 30, 2026)

**Completed Tasks:**
- ✅ RF-ARCH-012: Semantic Memory Upsert with deduplication
- ✅ RF-ARCH-013: Working Memory Deletion endpoints
- ✅ RF-ARCH-014: Semantic Memory Privacy (user_id scoping, public flag)
- ✅ RF-SDK-019: MemoryClient upsert_knowledge()
- ✅ RF-SDK-020: MemoryClient delete_plan_state()
- ✅ RF-SDK-021: MemoryClient semantic memory privacy

**Test Coverage:**
- Memory Service: 87 tests passing
- SDK Memory Tests: 45 tests passing
- Integration Tests: 28 tests passing
- **Total:** 160/160 tests passing (100%)

**CHANGELOG:** Updated in Memory Service, SDK, and soorma-common

---

## Related Documentation

- [README.md](./README.md) - User guide and patterns
- [Memory Service](../../services/memory/README.md) - Service implementation
- [Refactoring Plan](../refactoring/arch/02-MEMORY-SERVICE.md) - Stage 2 design decisions
- [SDK Memory Client](../../sdk/python/README.md#memory-client) - API reference
- [CoALA Framework Paper](https://arxiv.org/abs/2309.02427) - Research foundation

---

## Related Documentation

- [README.md](./README.md) - User guide
- [Service Implementation](../../services/memory/ARCHITECTURE.md)
- [MEMORY_PATTERNS.md](../MEMORY_PATTERNS.md) - Detailed patterns guide
