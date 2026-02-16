# 05 - Memory Semantic (RAG with LLM Routing)

**Concepts:** Semantic memory (RAG), LLM-based routing, Knowledge management, Grounded answers  
**Difficulty:** Intermediate  
**Prerequisites:** [03-events-structured](../03-events-structured/)  
**Recommended:** Complete [04-memory-working](../04-memory-working/) first (simpler memory concepts)

## What You'll Learn

- How to build a knowledge management system with semantic memory
- How to use LLM-based routing to detect user intent (store vs query)
- How to implement RAG (Retrieval-Augmented Generation) with grounded answers
- How to combine patterns from example 03 (structured events) with semantic memory
- When to use Tool vs Worker agents

## The Pattern

This example builds on example 03's LLM-based routing pattern and applies it to knowledge management:

```
User Request
     ↓
   Router (LLM detects intent)
     ↓
     ├── knowledge.store → Knowledge Store Tool → store in semantic memory
     │
     └── question.ask → Answer Agent (Worker) → RAG with LLM → grounded answer
```

**Key Insight:** The router uses the same event discovery and LLM selection pattern from example 03, but routes between knowledge storage and question answering.

## Architecture

### Three Agents

1. **Router** (Worker) - LLM-based intent detection
   - Listens for: `user.request`
   - Discovers available actions from Registry
   - Uses LLM to determine: store knowledge or ask question?
   - Publishes: `knowledge.store` or `question.ask`

2. **Knowledge Store** (Tool) - Deterministic storage
   - Listens for: `knowledge.store`
   - Stores content in semantic memory
   - Publishes: `knowledge.stored` (confirmation)

3. **Answer Agent** (Worker) - RAG-powered answering
   - Listens for: `question.ask`
   - Retrieves relevant knowledge (semantic search)
   - Uses LLM to generate grounded, factual answer
   - Publishes: `question.answered`

### Event Flow

```
User: "Python was created by Guido van Rossum"
  ↓
Router: (LLM detects intent = "store knowledge")
  ↓ knowledge.store
Knowledge Store: stores in semantic memory
  ↓ knowledge.stored
User: "✅ Knowledge stored successfully"

User: "Who created Python?"
  ↓
Router: (LLM detects intent = "ask question")
  ↓ question.ask
Answer Agent:
  1. Search semantic memory for relevant facts
  2. Use LLM to generate grounded answer
  ↓ question.answered
User: "Python was created by Guido van Rossum in 1991..."
```

## Use Case

An AI assistant that can:
1. **Learn** - Users can teach it facts: "Docker is a container platform"
2. **Answer** - Users can ask questions: "What is Docker?"
3. **Stay Grounded** - Answers are based on stored knowledge, not hallucinations

Perfect for:
- Personal knowledge bases
- Team documentation systems
- Customer support knowledge bases
- Any system that needs to learn and retrieve information

### User-Scoped Privacy

**Semantic memory is user-scoped** - each user has their own private knowledge base:
- Knowledge stored by User A is NOT visible to User B
- Each user can only query their own stored knowledge
- Privacy isolation is enforced at the database level (Row-Level Security)

This enables:
- Multi-user systems with isolated knowledge per user
- Personal assistants that maintain user-specific context
- Secure knowledge bases where users don't see each other's data

## Code Walkthrough

### Event Definitions ([events.py](events.py))

Defines the event API: user.request → router → knowledge.store or question.ask → response events.

See file for full EventDefinition and Pydantic payload models.

### LLM Utilities ([llm_utils.py](llm_utils.py))

Reusable functions (same pattern as example 03):
- `discover_actionable_events()` - Find available actions from Registry via context.toolkit
- `select_event_with_llm()` - Use LLM to choose best action
- `validate_and_publish()` - Validate decision and publish event

### Router ([router.py](router.py))

Uses LLM to detect intent and route requests (extends example 03 pattern):

```python
@worker.on_event("user.request", topic=EventTopic.ACTION_REQUESTS)
async def route_request(event: EventEnvelope, context: PlatformContext):
    request = event.data.get("request", "")
    
    # Step 1: Discover available actions
    events = await context.toolkit.discover_actionable_events(topic=EventTopic.ACTION_REQUESTS)
    action_events = [e for e in events if e.event_name in ["knowledge.store", "question.ask"]]
    
    # Step 2: LLM decides which action to take
    decision = await select_event_with_llm(
        prompt_template=ROUTING_PROMPT,
        context_data={"request": request},
        formatted_events=context.toolkit.format_as_prompt_text(...)
    )
    
    # Step 3: Publish the selected event
    await validate_and_publish(decision, action_events, EventTopic.ACTION_REQUESTS, context, event.correlation_id)
```

**How it applies the concepts:**
- Discovers available actions (knowledge.store, question.ask) from Registry
- Uses LLM with domain-specific prompt to detect intent
- Publishes only events that exist in Registry (prevents hallucinations)

### Knowledge Store ([knowledge_store.py](knowledge_store.py))

Deterministic Tool for storing knowledge:

```python
@tool.on_event("knowledge.store", topic=EventTopic.ACTION_REQUESTS)
async def store_knowledge(event: EventEnvelope, context: PlatformContext):
    content = event.data.get("content", "")
    metadata = event.data.get("metadata", {})
    user_id = event.user_id or "00000000-0000-0000-0000-000000000001"
    
    # Store in semantic memory
    await context.memory.store_knowledge(
        content=content,
        user_id=user_id,
        metadata=metadata
    )
    
    # Respond with structured payload
    payload = KnowledgeStoredPayload(success=True, content=content)
    await context.bus.respond(KNOWLEDGE_STORED_EVENT.event_name, payload.model_dump(), event.correlation_id)
```

**Why a Tool?** Stateless, deterministic storage operation - perfect for Tool pattern.

### Answer Agent ([answer_agent.py](answer_agent.py))

RAG (Retrieval-Augmented Generation) Worker:

```python
@worker.on_event("question.ask", topic=EventTopic.ACTION_REQUESTS)
async def answer_question(event: EventEnvelope, context: PlatformContext):
    question = event.data.get("question", "")
    user_id = event.data.get("user_id", "00000000-0000-0000-0000-000000000001")
    
    # Step 1: Search semantic memory for relevant knowledge
    knowledge_results = await context.memory.search_knowledge(
        query=question,
        user_id=user_id,
        limit=5
    )
    
    # Step 2: If no knowledge, admit uncertainty
    if not knowledge_results:
        payload = QuestionAnsweredPayload(
            question=question,
            answer="I don't have knowledge to answer that. Teach me first!",
            knowledge_used=[],
            has_knowledge=False
        )
        await context.bus.respond(...payload...event.correlation_id)
        return
    
    # Step 3: Generate grounded answer with LLM
    knowledge_context = "\n\n".join([k["content"] for k in knowledge_results])
    answer = await _generate_grounded_answer(question, knowledge_context)
    
    payload = QuestionAnsweredPayload(
        question=question,
        answer=answer,
        knowledge_used=[{"content": k["content"], "score": k.get("score", 0)} for k in knowledge_results],
        has_knowledge=True
    )
    await context.bus.respond(...payload...event.correlation_id)
```

**How it applies the concepts:**
- Retrieves knowledge via semantic search on user_id scope
- Uses LLM with grounding prompt (low temperature=0.3 for factuality)
- Responds only with answers grounded in stored knowledge (no hallucinations)
- Falls back gracefully when no knowledge exists

**Why a Worker?** Requires reasoning and LLM calls for answer generation.

### Client ([client.py](client.py))

Unified interface - send requests and get routed responses automatically:
```bash
# Interactive: "Python was created by Guido van Rossum" → routed to knowledge.store
# Interactive: "Who created Python?" → routed to question.ask  
python3 client.py

# Single request
python3 client.py "Python was created by Guido van Rossum"
```

Client doesn't know about routing - it sends user.request and the router handles intent detection.

## Running the Example

### Prerequisites

```bash
# Terminal 1: Start platform services
soorma dev --build

# Set OpenAI API key
export OPENAI_API_KEY='your-key-here'
```

Required for LLM operations in router and answer agent.

### Quick Start

**Terminal 2: Start agents**
```bash
cd examples/05-memory-semantic
./start.sh  # Starts router, knowledge-store, answer-agent
```

**Terminal 3: Interact**
```bash
# Interactive mode
python3 client.py
You: Python was created by Guido van Rossum
You: Who created Python?  # → RAG retrieves knowledge + LLM generates answer

# Single request
python3 client.py "Python was created by Guido van Rossum"
```

### Testing User Privacy Isolation

**Verify that knowledge is user-scoped:**

```bash
# User 1 stores knowledge (default: 00000000-0000-0000-0000-000000000001)
python3 client.py "my favorite color is blue"
# ✅ Knowledge stored successfully

# User 1 can retrieve their own knowledge
python3 client.py "what is my favorite color?"
# ✅ Your favorite color is blue.

# User 2 CANNOT see User 1's knowledge
USER_ID=00000000-0000-0000-0000-000000000002 python3 client.py "what is my favorite color?"
# ⚠️  I don't have enough knowledge to answer that question.

# User 2 can store their own knowledge
USER_ID=00000000-0000-0000-0000-000000000002 python3 client.py "my favorite color is red"
# ✅ Knowledge stored successfully

# User 2 can retrieve their own knowledge
USER_ID=00000000-0000-0000-0000-000000000002 python3 client.py "what is my favorite color?"
# ✅ Your favorite color is red.
```

**Key points:**
- Default user ID is `00000000-0000-0000-0000-000000000001`
- Set `USER_ID` environment variable to test with different users
- Each user has completely isolated knowledge storage
- User ID propagates through the entire event chain automatically

### Expected Output

Watches flow: user.request → router (LLM detects intent) → knowledge.store or question.ask → response events.

## Key Takeaways

**LLM-based routing with event discovery:**
- Router discovers available actions from Registry (knowledge.store, question.ask)
- Uses LLM with domain-specific prompt to detect user intent
- Prevents hallucinations by only publishing real events

**Semantic memory enables RAG (Retrieval-Augmented Generation):**
- Store knowledge in embeddings for semantic search
- Retrieve relevant context for each question
- Use LLM to synthesize grounded answers from stored knowledge
- **User-scoped privacy:** Each user's knowledge is isolated from others

**Tool vs Worker pattern:**
- Knowledge Store is a Tool (deterministic, stateless storage)
- Answer Agent is a Worker (reasoning, LLM-based generation)
- Router is a Worker (LLM-based decision making)

**Pattern reusability:**
- Event discovery + LLM selection from example 03 works here for knowledge domain
- Same pattern applies to ticket routing, task planning, etc.

## Pattern Comparison

### vs Example 03 (Structured Events)

| Aspect | Example 03 | Example 05 |
|--------|-----------|------------|
| Domain | Ticket routing | Knowledge management |
| Actions | Route to support tiers | Store knowledge or answer |
| LLM Use | Select routing target | Intent detection + answer generation |
| Memory | None | Semantic memory (RAG) |
| Pattern | Event discovery + routing | Event discovery + routing + RAG |

### vs Traditional Chatbot

| Traditional Chatbot | This Example |
|---------------------|--------------|
| Hardcoded intents | LLM-detected intents |
| Static knowledge base | Dynamic learning |
| Rule-based routing | Event-based choreography |
| Single monolith | Distributed agents |

## Best Practices

**Memory isolation by user_id:**
- All store_knowledge() and search_knowledge() calls scoped by user_id
- Prevents cross-user knowledge leaks
- Each user has private knowledge base

**Preventing hallucinations:**
- Router validates decisions against Registry (only real events)
- Answer agent admits uncertainty when no knowledge found
- Use low LLM temperature (0.3) for factual generation
- Provide explicit grounding prompt: "Answer ONLY using this knowledge"

**Rich metadata support:**
- Store source, category, confidence, timestamp with knowledge
- Use for filtering, quality control, audit trails

## Extending the Example

**Add more capabilities:** Register new events (knowledge.update, knowledge.delete) in events.py. Router will auto-discover them via context.toolkit.discover_actionable_events().

**Add authorization:** Check user permissions in each handler before proceeding.

**Add metadata filtering:** Use metadata in search_knowledge() to filter by source, category, timestamp, etc.

**Add multi-modal knowledge:** Store images/documents in metadata with embeddings for hybrid search.

## Next Steps

- **[06-memory-episodic](../06-memory-episodic/)** - Conversation history and audit trails (recommended next)
- **08-planner-worker-basic (coming soon)** - Goal decomposition with semantic memory
- **09-app-research-advisor (coming soon)** - Full autonomous system combining all patterns

---

**📖 Additional Resources:**
- [Memory System Documentation](../../docs/memory_system/README.md)
- [Event System Documentation](../../docs/event_system/README.md)
- [Agent Patterns - DisCo Trinity](../../docs/agent_patterns/README.md)
