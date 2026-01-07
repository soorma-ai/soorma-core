# Memory Patterns

**Status:** 📝 Draft  
**Last Updated:** January 6, 2026

This document describes memory patterns in Soorma based on the CoALA framework.

---

## Overview

Soorma implements three types of memory from the CoALA (Cognitive Architectures for Language Agents) framework:

1. **Semantic Memory** - Long-term knowledge storage (RAG)
2. **Working Memory** - Plan-scoped shared state
3. **Episodic Memory** - Conversation history and audit trails

Each serves a different purpose and has different characteristics.

---

## 1. Semantic Memory (RAG)

### What It Is

Long-term storage of facts and knowledge with semantic search capabilities. Like a vector database or knowledge base.

### When to Use

- Store documentation for retrieval
- Build knowledge bases
- Implement RAG (Retrieval Augmented Generation)
- Answer questions from a corpus

### Example

See [04-memory-semantic](../examples/04-memory-semantic/) (coming in Phase 3)

```python
# Store knowledge with automatic embeddings
await context.memory.store_knowledge(
    content="To configure authentication, set the AUTH_PROVIDER environment variable to 'oauth2' for OAuth integration or 'saml' for SAML. Configure the provider-specific settings in the auth section of your config file.",
    metadata={
        "title": "Authentication Configuration",
        "category": "configuration",
        "source": "product_docs",
        "tags": ["auth", "sso", "configuration"]
    }
)

# Search by semantic similarity
results = await context.memory.search_knowledge(
    query="How do I set up single sign-on?",
    limit=5
)

for result in results:
    print(f"Score: {result['score']}")
    print(f"Content: {result['content']}")
    print(f"Metadata: {result['metadata']}")
```

### Characteristics

- **Persistent** - Survives agent restarts
- **Searchable** - Vector similarity search
- **Shared** - Accessible across all agents
- **Scoped** - Can filter by tags/categories

### Best Practices

✅ Use for:
- Product documentation
- FAQs and knowledge articles
- Historical patterns and insights
- Reference data

❌ Don't use for:
- Temporary workflow state
- Real-time coordination
- Transient data

---

## 2. Working Memory (Plan State)

### What It Is

Plan-scoped shared state for coordinating agents within a workflow. Like a shared scratchpad for a specific task.

### When to Use

- Share data between planner and workers
- Track workflow progress
- Store intermediate results
- Coordinate multi-agent tasks

### Example

See [05-memory-working](../examples/05-memory-working/) (coming in Phase 3)

```python
# Agent 1: Stores data in working memory
@agent1.on_event("data.request")
async def handle_request(event, context):
    request_id = event.data["request_id"]
    
    # Store initial state
    await context.memory.store(
        key="status",
        value="processing",
        plan_id=request_id
    )
    
    # Process and store result
    result = await process_data(event.data)
    await context.memory.store(
        key="result",
        value=result,
        plan_id=request_id
    )
    
    # Notify completion
    await context.bus.publish(
        event_type="data.processed",
        topic="action-results",
        data={"request_id": request_id}
    )

# Agent 2: Retrieves data from working memory
@agent2.on_event("data.processed")
async def handle_result(event, context):
    request_id = event.data["request_id"]
    
    # Retrieve stored data
    status = await context.memory.retrieve(
        key="status",
        plan_id=request_id
    )
    result = await context.memory.retrieve(
        key="result",
        plan_id=request_id
    )
    
    # Use the shared data
    await send_notification(result)
```

### Characteristics

- **Scoped** - Isolated by plan_id
- **Temporary** - Cleared after workflow completes
- **Fast** - PostgreSQL-backed (Redis planned)
- **Coordinating** - Shared between related agents

### API

```python
# Store a value (scoped by plan_id)
await context.memory.store(
    key="my_key",
    value={"some": "data"},
    plan_id="workflow-123"
)

# Retrieve a value
value = await context.memory.retrieve(
    key="my_key",
    plan_id="workflow-123"
)
```

The `plan_id` parameter scopes the data - different workflows can use the same key names without conflicts.

### Best Practices

✅ Use for:
- Workflow coordination
- Intermediate results
- Progress tracking
- Shared context in a plan

❌ Don't use for:
- Long-term storage
- Cross-plan data
- Knowledge bases

---

## 3. Episodic Memory (Conversation History)

### What It Is

Sequential record of events and interactions. Like a conversation log or audit trail.

### When to Use

- Store conversation history
- Track user interactions
- Audit trails
- Debugging and replay

### Example

See [06-memory-episodic](../examples/06-memory-episodic/) (coming in Phase 3)

```python
# Log conversation turn
await context.memory.log_interaction(
    agent_id="support-bot",
    role="user",
    content="How do I reset my password?",
    user_id=user_id,
    metadata={
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }
)

await context.memory.log_interaction(
    agent_id="support-bot",
    role="assistant",
    content="To reset your password, click the 'Forgot Password' link on the login page. You'll receive an email with reset instructions.",
    user_id=user_id,
    metadata={
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }
)

# Retrieve recent conversation history
history = await context.memory.get_recent_history(
    agent_id="support-bot",
    user_id=user_id,
    limit=10
)

# Build context for LLM
context_messages = []
for interaction in history:
    context_messages.append({
        "role": interaction["role"],
        "content": interaction["content"]
    })

# Search past interactions semantically
relevant = await context.memory.search_interactions(
    agent_id="support-bot",
    query="password reset issues",
    user_id=user_id,
    limit=5
)
```

### Characteristics

- **Sequential** - Ordered by time
- **Append-only** - Historical record
- **Persistent** - Long-term storage
- **Filterable** - By tags (session, user, etc.)

### Best Practices

✅ Use for:
- Multi-turn conversations
- Audit logs
- Debugging traces
- User interaction history

❌ Don't use for:
- Real-time coordination
- Frequently updated data
- Temporary state

---

## Comparison Table

| Feature | Semantic Memory | Working Memory | Episodic Memory |
|---------|----------------|----------------|-----------------|
| **Purpose** | Knowledge base | Workflow state | Interaction history |
| **Search** | Vector similarity | Key-value | Sequential/tags |
| **Scope** | Global | Plan-specific | Session/user-specific |
| **Lifetime** | Permanent | Workflow duration | Long-term |
| **Speed** | Slower (embeddings) | Fast (in-memory) | Medium (sequential) |
| **Use case** | RAG, docs | Coordination | Conversations |

---

## Decision Tree

```
Need to store data?
│
├─ Is it long-term knowledge? → Semantic Memory
│   Examples: docs, FAQs, insights
│
├─ Is it for workflow coordination? → Working Memory
│   Examples: intermediate results, plan state
│
└─ Is it interaction history? → Episodic Memory
    Examples: conversations, audit logs
```

---

## Anti-Patterns

### ❌ Using Semantic Memory for Workflow State

```python
# DON'T do this
await context.memory.store_knowledge(
    content="current_step: research",  # This is workflow state, not knowledge!
    metadata={"type": "state"}
)

# DO this instead
await context.memory.store(
    key="current_step",
    value="research",
    plan_id=plan_id
)
```

### ❌ Using Working Memory for Long-Term Data

```python
# DON'T do this
await context.memory.store(
    key=f"user_prefs_{user_id}",
    value={...},
    plan_id=plan_id  # Will be cleared when plan completes!
)

# DO this instead
await context.memory.store_knowledge(
    content=json.dumps(user_preferences),
    metadata={"user_id": user_id, "type": "preferences"}
)
```

### ❌ Using Episodic Memory for Real-Time Coordination

```python
# DON'T do this - too slow for real-time state sharing
await context.memory.log_interaction(
    agent_id="coordinator",
    role="system",
    content="latest_result",
    user_id="system"
)

# DO this instead - use working memory for shared state
await context.memory.store(
    key="latest_result",
    value={...},
    plan_id=plan_id
)

# OR use events to trigger/notify other agents
await context.bus.publish(
    event_type="result.ready",
    topic="action-results",
    data={...}
)
```

---

## Related Documentation

- [Design Patterns](./DESIGN_PATTERNS.md) - Agent orchestration patterns
- [Examples](../examples/) - Working implementations
- [CoALA Framework Paper](https://arxiv.org/abs/2309.02427) - Original memory taxonomy

---

**Coming Soon:**
- Examples 04, 05, 06 demonstrating each memory type
- Best practices for memory cleanup
- Performance optimization tips
