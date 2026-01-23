# Soorma Memory Service: Technical Design & Specification

## 1. Executive Summary

The Soorma Memory Service provides a unified, persistent memory layer for autonomous agents. It is designed to support "Cognitive Architectures for Language Agents" (CoALA) while enforcing strict enterprise multi-tenancy and user isolation. The service leverages PostgreSQL with pgvector to handle both relational state and semantic (vector) retrieval in a single infrastructure.

## 2. Conceptual Framework (CoALA)

The service implements the four primary memory types defined by the CoALA framework:

| Memory Type | Description | Soorma Implementation |
|------------|-------------|----------------------|
| Working Memory | Short-term "scratchpad" for current tasks, goals, and active reasoning. | Key-Value store scoped to specific Plans/Goals. |
| Episodic Memory | History of past experiences and interaction sequences. | Time-series interaction logs with vector embeddings for recall. |
| Semantic Memory | Factual knowledge and general world information. | Knowledge Base (RAG) with tenant-wide access. |
| Procedural Memory | "Know-how," rules, and decision-making logic. | Dynamic prompt injection (Few-Shot examples/System Instructions). |

## 3. Business & Security Requirements

### 3.1 Multi-Tenancy (Native)

**Requirement:** Agents must only access memories matching their specific Tenant ID.

**Implementation:** Enforced via PostgreSQL Row Level Security (RLS). Application-level bugs cannot leak data between tenants.

### 3.2 User-Level Personalization

**Requirement:** Specific memories must be private to the User/Agent pair.

**User Identity Clarification:**
The `user_id` parameter represents **either a human end user OR an autonomous agent identity**:
- **Human-driven systems**: `user_id` = authenticated end user (e.g., "alice", "bob")
- **Autonomous agent systems**: `user_id` = agent identity (e.g., "research-agent", "monitoring-bot")
- **Hybrid systems**: Mix of both (users interact with agents, agents work autonomously)

This design ensures:
- Access control works for both human users and autonomous agents
- Semantic memory can be scoped to specific agents when needed (e.g., agent-specific knowledge bases)
- Audit trails capture whether actions were user-initiated or agent-initiated

**Scope:**
- Episodic: Private to User/Agent pair (human user + agent, or agent + sub-agent).
- Procedural: Private to User/Agent pair (personalized skills for specific user or agent).
- Semantic: Shared across Tenant by default, but `user_id` enables optional access restrictions.

### 3.3 Goal/Plan Context

**Requirement:** Multiple agents working on a single goal need a shared state.

**Scope:** Working Memory is scoped to a plan_id, allowing collaborative access among authorized agents.

## 4. Database Schema Design

**Infrastructure:** PostgreSQL + pgvector extension.

**Note:** PostgreSQL with pgvector is mandatory (not optional like other services that support SQLite). This is because:
- Vector embeddings are the core value proposition of the memory service
- pgvector's HNSW indexes provide sub-millisecond semantic search at scale
- Row Level Security (RLS) enforces tenant isolation at the database level
- JSONB support for flexible metadata storage

### 4.1 Core Identity (Local Replicas)

**Crucial Note:** The tenants and users tables below are local replicas, not the authentication source of truth. They exist to:
- Enforce Foreign Key constraints (Data Integrity).
- Enable ON DELETE CASCADE (Instant cleanup of vectors when a tenant is deleted in the main Identity Service).

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

-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
```

### 4.2 Semantic Memory (Knowledge Base)

Stores facts shared across the tenant.

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
CREATE INDEX semantic_embedding_idx ON semantic_memory USING hnsw (embedding vector_cosine_ops);
ALTER TABLE semantic_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON semantic_memory
    USING (tenant_id = current_setting('app.current_tenant')::UUID);
```

### 4.3 Episodic Memory (Experience)

Stores interaction history specific to User + Agent.

```sql
CREATE TABLE episodic_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,         -- e.g., "researcher-1"
    
    role TEXT CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    embedding VECTOR(1536),         -- For "What did we discuss last week?"
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes & Security
CREATE INDEX episodic_embedding_idx ON episodic_memory USING hnsw (embedding vector_cosine_ops);
CREATE INDEX episodic_time_idx ON episodic_memory (user_id, agent_id, created_at DESC);
ALTER TABLE episodic_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_agent_isolation ON episodic_memory
    USING (
        tenant_id = current_setting('app.current_tenant')::UUID 
        AND user_id = current_setting('app.current_user')::UUID
    );
```

### 4.4 Procedural Memory (Skills)

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
    content TEXT NOT NULL,          -- e.g., "Always check Stripe status first."
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes & Security
CREATE INDEX procedural_embedding_idx ON procedural_memory USING hnsw (embedding vector_cosine_ops);
ALTER TABLE procedural_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY procedural_isolation ON procedural_memory
    USING (
        tenant_id = current_setting('app.current_tenant')::UUID 
        AND user_id = current_setting('app.current_user')::UUID
    );
```

### 4.5 Working Memory (Plan State)

Stores shared state for a specific Plan execution.

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

## 5. API Specification

### 5.1 Authentication & Tenancy Strategy

The service extracts Tenant and User IDs from the API Token and sets session variables.

#### A. Local Development Strategy (Single Tenant)

To allow local development without a running Identity Service:

**Migration:** Ensure a "Default Tenant" row exists.

```sql
INSERT INTO tenants (id, name) 
VALUES ('00000000-0000-0000-0000-000000000000', 'Default Tenant') 
ON CONFLICT DO NOTHING;
```

**Middleware:** If no Auth Token is present, default to this UUID.

#### B. Production Strategy (Multi-Tenant)

**Lazy Population (Forward Deployed Phase):** Middleware extracts tenant_id from token. If it doesn't exist in local tenants table, UPSERT it immediately.

**Event-Driven (Mature Phase):** Listen for identity.tenant.created events to populate the table.

#### C. Session Context Execution

```sql
SET app.current_tenant = '<extracted_or_default_uuid>';
SET app.current_user = '<extracted_or_default_uuid>';
```

### 5.2 Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /v1/memory/semantic | Ingest knowledge (text + metadata). Service handles embedding. |
| GET | /v1/memory/semantic/search?q=query | Semantic retrieval of facts. |
| POST | /v1/memory/episodic | Log a chat turn or tool output. |
| GET | /v1/memory/episodic/recent?limit=N | Fetch recent history (Context Window). |
| GET | /v1/memory/episodic/search?q=query | Long-term recall of past events. |
| GET | /v1/memory/procedural/context?q=query | Fetch relevant rules/prompts based on current task. |
| PUT | /v1/memory/working/{plan}/{key} | Set shared state variable. |
| GET | /v1/memory/working/{plan}/{key} | Get shared state variable. |

## 6. Operational Workflow (Example)

**Scenario:** User asks, "Why did my billing fail?"

1. **Recall Skills (Procedural):** Agent queries `/procedural/context`.
   - Result: "When discussing billing, check Stripe status first." (Added to System Prompt).

2. **Recall Facts (Semantic):** Agent queries `/semantic/search`.
   - Result: "Error 402 means insufficient funds."

3. **Check State (Working):** Agent queries `/working/{plan_id}/account_id`.
   - Result: "acc_123".

4. **Execute & Log (Episodic):** Agent replies and calls `POST /episodic`.

## 7. Implementation Notes

- **Embeddings:** The Memory Service manages embedding generation internally (e.g., via OpenAI text-embedding-3-small or local models) to ensure dimensional consistency across the database.
- **Performance:** HNSW indexes are used for Approximate Nearest Neighbor (ANN) search, offering sub-millisecond retrieval at scale.
- **Scalability:** RLS policies are optimized to use session variables, avoiding costly JOIN operations during permission checks.

## 8. Architectural Design Decisions

### 8.1 Replica Table Strategy

**Decision:** Maintain local replica tables for tenants and users within the Memory Service, even though Identity Service is the source of truth.

**Rationale:**
- **Data Integrity:** Enforces foreign key constraints locally, preventing "orphan" memory records linked to non-existent tenants.
- **Lifecycle Management:** Enables ON DELETE CASCADE behavior. When a tenant is deleted (and synchronized to this replica), the database engine automatically wipes all associated vector data in milliseconds, avoiding the need for complex, error-prone application-level cleanup jobs.

### 8.2 Relational Cascade Logic

**Decision:** ON DELETE CASCADE is defined on child tables (users, semantic_memory, etc.), not the root tenants table.

**Rationale:** In RDBMS design, the "deletion rule" belongs to the dependent (child) table. It states: "If my parent is deleted, I should delete myself."

- **Root:** The tenants table has no parent, so it needs no cascade rule.
- **Chain of Destruction:** Deleting a row in tenants triggers the cascade on users (child), which in turn triggers the cascade on episodic_memory (grandchild). This creates a reliable chain reaction for data cleanup.

### 8.3 UUID Primary Keys

**Decision:** Use UUID (specifically uuid_generate_v4()) for all Primary Keys instead of auto-incrementing integers.

**Rationale:**
- **Security (Anti-Enumeration):** Prevents attackers from guessing valid resource IDs (e.g., accessing tenant 101 after seeing tenant 100), adding a critical layer of defense-in-depth for multi-tenant isolation.
- **Distributed Generation:** Allows the application layer and SDKs to generate IDs before database insertion, enabling better request tracing and distributed ID management.
- **Write Distribution:** Random UUIDs distribute write operations evenly across the database index, preventing "hot spots" that occur with linearly incrementing keys in high-throughput systems.

### 8.4 PostgreSQL Session Variables for RLS

**Decision:** Use PostgreSQL custom configuration parameters (`app.current_tenant` and `app.current_user`) to pass security context into Row Level Security (RLS) policies.

**Implementation:**

Before each database query, the middleware executes:

```sql
SET app.current_tenant = '<tenant_uuid>';
SET app.current_user = '<user_uuid>';
```

RLS policies then reference these values using `current_setting()`:

```sql
CREATE POLICY tenant_isolation_policy ON semantic_memory
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY user_agent_isolation ON episodic_memory
    USING (
        tenant_id = current_setting('app.current_tenant')::UUID 
        AND user_id = current_setting('app.current_user')::UUID
    );
```

**Rationale:**

- **Database-Level Security:** RLS enforcement happens at the PostgreSQL engine level, not in application code. Even SQL injection attacks or application bugs cannot bypass tenant isolation—the database physically restricts row visibility based on the session variables.

- **Zero Application Overhead:** Once session variables are set, no additional logic is needed in queries. Developers can write simple `SELECT * FROM episodic_memory` and the database automatically filters results to only authorized rows.

- **Transparency:** Application code doesn't need to remember to add `WHERE tenant_id = ?` clauses to every query. The security layer is invisible to business logic, reducing cognitive load and preventing mistakes.

- **Performance:** Session variables avoid the need for JOIN operations in permission checks. The database can use these values directly in index scans, making RLS policies nearly as fast as queries without security constraints.

**Security Properties:**

1. **Defense in Depth:** Even if authentication middleware fails to set session variables correctly, the RLS policy will block access (queries will return zero rows or fail).

2. **Immutability Within Transaction:** Session variables persist for the duration of the database connection/transaction but reset automatically when the connection returns to the pool, preventing cross-request contamination.

3. **Audit Trail:** All queries execute within the context of specific tenant/user IDs, enabling database-level audit logging if needed.

**Code Reference:** See `services/memory/src/memory_service/core/database.py` (`set_session_context()`) and `services/memory/src/memory_service/core/middleware.py` for implementation details.
