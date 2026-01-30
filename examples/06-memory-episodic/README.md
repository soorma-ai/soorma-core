# 06 - Episodic Memory (Multi-Agent Chatbot)

**Concepts:** Episodic memory, Semantic memory, Working memory, Multi-agent architecture, RAG, Intent routing  
**Difficulty:** Intermediate  
**Prerequisites:** [04-memory-working](../04-memory-working/), [05-memory-semantic](../05-memory-semantic/)

## What You'll Learn

- How to build a multi-agent chatbot with cognitive architecture
- How to combine three memory types (episodic, semantic, working)
- How to implement intent classification and routing
- How to build RAG (Retrieval Augmented Generation) with dual context
- How to manage conversation sessions with working memory
- How to track and manage plans for session visibility and cleanup

## The Pattern

This example demonstrates a **multi-agent chatbot with three memory types**:

### **Memory Architecture**
- **Episodic Memory** - All interaction history (conversation audit log)
- **Semantic Memory** - Stored knowledge and facts (knowledge base for RAG)
- **Working Memory** - Session state (active conversation context)

### **Four Specialized Agents**

1. **Router** - LLM-based intent classification → routes to appropriate handler
2. **RAG Agent** - Dual-context answers (episodic + semantic memory search)
3. **Concierge** - Conversation history analysis and insights
4. **Knowledge Store** - Extract facts → store in semantic memory

## How It Works

### Orchestration Pattern (Request/Response)

```
Client → chat.message (with correlation_id, response_event)
         ↓
Router → stores client info in working memory (session_id as key)
       → classifies intent (LLM with JSON mode)
       → routes to worker (session_id as correlation_id)
         ↓
Worker → processes request
       → responds with router's expected response_event
         ↓
Router → listens for worker response (matches session_id)
       → retrieves client info from working memory
       → responds to client (client's response_event + correlation_id)
```

**Key Pattern:** Router orchestrates - stores client context, routes with session correlation, listens for worker responses, routes back to client.

### Intent Classification

Router uses LLM (JSON mode) with conversation history context to classify:
- **store_knowledge**: "Remember that Python was created by Guido"
- **answer_question**: "What is Python?" or terse follow-ups like "again"
- **concierge**: "What have we discussed?"
- **general**: Greetings, acknowledgments

Falls back to keyword heuristics if LLM call fails.

### Dual-Context RAG

RAG agent retrieves from two memory sources:
1. **Episodic memory** - Past answers from conversation history
2. **Semantic memory** - Stored knowledge from knowledge base
3. **LLM synthesis** - Combines both contexts into natural answer

## Running the Example

### Prerequisites

```bash
# Set OpenAI API key
export OPENAI_API_KEY='your-key-here'

# Start platform services
soorma dev --build
```

LLM used for intent classification (router), answer synthesis (RAG), conversation analysis (concierge).

### Quick Start

```bash
cd examples/06-memory-episodic

# Terminal 1: Start agents
bash start.sh

# Terminal 2: Interactive client
python client.py
```

### Try These Interactions

```
You: Remember that Python was created by Guido van Rossum in 1991
🤖: ✓ Stored

You: What is Python?
🤖: Based on stored knowledge: Python was created by Guido van Rossum in 1991.
     (sources: 0 from history, 1 from knowledge)

You: What have we discussed?
🤖: We discussed: "Remember that Python..." and "What is Python?"

# Plan Management Commands
You: /sessions   # List existing plans, choose one or create new
You: /new        # Start new session (creates Plan record)
You: /delete     # Delete a plan and its working memory
You: /quit       # Exit
```

## Utility Scripts

For debugging and inspection:

```bash
# View conversation history
python view_history.py [limit]

# Search interactions by semantic similarity
python search_memory.py "query" [limit]
```

Uses same hardcoded user ID as client.

## Key Takeaways

**Three memory types serve different purposes:**
- **Episodic** - Audit log of all interactions (conversation history)
- **Semantic** - Knowledge base for RAG (facts and information)
- **Working** - Session state (fast key-value, plan-scoped)

**Orchestration with working memory:**
- Router stores client info in working memory (keyed by session_id)
- Router uses session_id as correlation_id when routing to workers
- Workers respond to router, router forwards to client with client's correlation info
- Pattern from Example 04, extended to multiple workers

**Dual-context RAG:**
- Search both episodic (past answers) and semantic (stored facts)
- LLM synthesizes natural answers from combined context
- Better than single-source RAG

**LLM integration best practices:**
- Use conversation history for better intent classification
- JSON mode for structured LLM outputs
- Fallback to heuristics when LLM fails
- Low temperature for factual answers

**Agent specialization:**
- Router: Orchestration + intent classification + logging
- RAG Agent: Dual-memory search + answer synthesis
- Concierge: History analysis
- Knowledge Store: Fact extraction + storage

## Code Walkthrough

### Router ([router.py](router.py))

Orchestrator that classifies intent and routes to workers:

```python
@router.on_event("chat.message", topic=EventTopic.ACTION_REQUESTS)
async def route_message(event: EventEnvelope, context: PlatformContext):
    message = event.data.get("message", "")
    session_id = event.data.get("session_id")
    user_id = event.user_id
    
    # Store client info in working memory
    state = WorkflowState(context.memory, session_id, tenant_id=event.tenant_id, user_id=user_id)
    await state.set("client_correlation_id", event.correlation_id)
    await state.set("client_response_event", event.response_event or "chat.response")
    
    # Classify intent with LLM (JSON mode)
    classification = await classify_intent(message, history)
    intent = classification["intent"]
    
    # Log to episodic memory
    await context.memory.log_interaction(
        agent_id="chatbot-router",
        role="user",
        content=message,
        user_id=user_id,
        metadata={"session_id": session_id, "intent": intent}
    )
    
    # Route to appropriate worker
    if intent == "answer_question":
        await context.bus.request(
            event_type="question.answer",
            response_event="question.answered",
            data={"session_id": session_id, "question": message},
            correlation_id=session_id,  # Use session_id for correlation
            tenant_id=event.tenant_id,
            user_id=user_id
        )
```

**How it applies the concepts:**
- Stores client correlation info in working memory (keyed by session_id)
- Uses LLM with conversation history for accurate intent classification
- Logs all interactions to episodic memory for audit trail
- Routes with session_id as correlation_id (not client's correlation)
- Workers respond to router, router responds to client

### Router Response Handlers

Router listens for worker responses and forwards to client:

```python
@router.on_event("question.answered", topic=EventTopic.ACTION_RESULTS)
async def handle_question_answered(event: EventEnvelope, context: PlatformContext):
    session_id = event.correlation_id  # Matches session_id we sent
    
    # Retrieve client info from working memory
    state = WorkflowState(context.memory, session_id, tenant_id=event.tenant_id, user_id=event.user_id)
    client_correlation_id = await state.get("client_correlation_id")
    client_response_event = await state.get("client_response_event")
    
    # Forward response to client
    await context.bus.respond(
        event_type=client_response_event,
        data=event.data,
        correlation_id=client_correlation_id,
        tenant_id=event.tenant_id,
        user_id=event.user_id
    )
```

**Pattern:** Router matches responses via session_id, retrieves client info, responds with client's expected event type.

### RAG Agent ([rag_agent.py](rag_agent.py))

Dual-context question answering with episodic + semantic memory:

```python
@rag_agent.on_event("question.answer", topic=EventTopic.ACTION_REQUESTS)
async def answer_question(event: EventEnvelope, context: PlatformContext):
    question = event.data.get("question", "")
    user_id = event.user_id
    
    # Search episodic memory for past answers
    history_results = await context.memory.search_interactions(
        agent_id="chatbot-rag",
        query=question,
        user_id=user_id,
        limit=3
    )
    
    # Search semantic memory for stored knowledge
    knowledge_results = await context.memory.search_knowledge(
        query=question,
        user_id=user_id,
        limit=3
    )
    
    # Synthesize answer from both contexts using LLM
    answer = await synthesize_answer(question, history_results, knowledge_results)
    
    # Log interaction
    await context.memory.log_interaction(
        agent_id="chatbot-rag",
        role="assistant",
        content=answer,
        user_id=user_id,
        metadata={"session_id": event.data.get("session_id")}
    )
    
    # Respond to router
    await context.bus.respond(
        event_type=event.response_event or "question.answered",
        data={"answer": answer, "sources": {...}},
        correlation_id=event.correlation_id
    )
```

**How it applies the concepts:**
- Searches both episodic (past conversations) and semantic (facts) memory
- Uses LLM to synthesize natural answers from combined context
- Logs own response to episodic memory (router logs user message)
- Responds to router, not directly to client

### Concierge ([concierge.py](concierge.py))

Conversation history analysis and insights:

```python
@concierge.on_event("concierge.query", topic=EventTopic.ACTION_REQUESTS)
async def handle_query(event: EventEnvelope, context: PlatformContext):
    query = event.data.get("query", "")
    session_id = event.correlation_id
    user_id = event.user_id
    
    # Get session history from episodic memory
    interactions = await context.memory.get_recent_history(
        agent_id="chatbot-router",
        user_id=user_id,
        limit=50
    )
    
    # Analyze with LLM
    response = await analyze_session(query, interactions)
    
    # Respond to router
    await context.bus.respond(
        event_type=event.response_event or "concierge.response",
        data={"response": response},
        correlation_id=event.correlation_id
    )
```

**How it applies the concepts:**
- Retrieves episodic memory filtered by agent_id (router logs all user messages)
- Uses LLM to analyze conversation patterns
- Provides insights on session history

### Knowledge Store ([knowledge_store.py](knowledge_store.py))

Extract facts and store in semantic memory:

```python
@knowledge_store.on_event("knowledge.store", topic=EventTopic.ACTION_REQUESTS)
async def store_knowledge(event: EventEnvelope, context: PlatformContext):
    message = event.data.get("message", "")
    user_id = event.user_id
    session_id = event.data.get("session_id")
    
    # Extract fact from message (could use LLM here)
    fact = message  # Or: await extract_fact_with_llm(message)
    
    # Store to semantic memory
    await context.memory.store_knowledge(
        content=fact,
        user_id=user_id,
        metadata={"session_id": session_id}
    )
    
    # Log confirmation
    await context.memory.log_interaction(
        agent_id="knowledge-store",
        role="assistant",
        content=f"✓ Stored: {fact[:100]}...",
        user_id=user_id,
        metadata={"session_id": session_id}
    )
    
    # Respond to router
    await context.bus.respond(
        event_type=event.response_event or "knowledge.stored",
        data={"fact": fact, "success": True},
        correlation_id=event.correlation_id
    )
```

**How it applies the concepts:**
- Stores extracted facts in semantic memory (knowledge base)
- Logs confirmation to episodic memory (audit trail)
- Tool-like behavior but implemented as Worker (could extract facts with LLM)

### Interactive Client ([client.py](client.py))

Multi-session client with plan management:

```python
async def start_new_session(self) -> str:
    """Start a new chat session."""
    session_id = str(uuid.uuid4())  # Full UUID for working memory
    await self.create_plan_record(session_id)
    return session_id

async def create_plan_record(self, plan_id: str) -> bool:
    """Create Plan record for tracking."""
    await self.memory_client.create_plan(
        plan_id=plan_id,
        goal_event="chat.conversation",
        goal_data={"type": "episodic_memory_demo"},
        tenant_id=TENANT_ID,
        user_id=USER_ID
    )

async def choose_session(self) -> str:
    """List plans and let user choose."""
    plans = await self.memory_client.list_plans(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        limit=20
    )
    # Display plans, let user choose or create new
    
async def delete_session(self) -> None:
    """Delete plan and working memory."""
    await self.memory_client.delete_plan(
        plan_id=plan_id,
        tenant_id=TENANT_ID,
        user_id=USER_ID
    )
```

**How it applies the concepts:**
- **Plan records** - Track conversation sessions for visibility
- **Working memory** - Uses `plan_id` (session UUID) as namespace for state
- **list_plans()** - Lets users resume previous conversations
- **delete_plan()** - Removes Plan record and cleans up working memory
- **Multi-session** - Users can switch between conversations (`/sessions` command)

**Commands:**
- `/new` - Create new session (creates Plan record)
- `/sessions` - List and choose existing plans
- `/delete` - Remove plan and associated state
- `/quit` - Exit client

**Pattern:** Plans are optional metadata for tracking. Working memory works with or without Plan records (uses `plan_id` as key either way).

## Best Practices

**Memory type selection:**
- Episodic: Log all interactions per agent (router logs user, workers log responses)
- Semantic: Store facts/knowledge for retrieval
- Working: Session state (correlation info, counters, flags)

**Avoid duplicate logging:**
- Router logs user messages only once
- Each worker logs its own responses
- Filter by agent_id to see specific agent's logs

**Orchestration patterns:**
- Store client info before routing to workers
- Use session_id as correlation for worker requests
- Listen for worker responses on ACTION_RESULTS topic
- Retrieve client info and forward response

**LLM best practices:**
- Provide conversation history for context-aware classification
- Use JSON mode for structured outputs
- Implement fallbacks for LLM failures
- Use low temperature for factual answers

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No response from agents" | Check `bash start.sh` ran successfully, verify Memory Service health |
| "Search returns empty" | Data lost on rebuild, store new knowledge and retry |
| "Intent classification wrong" | Verify OPENAI_API_KEY, check LLM_MODEL env var, router has heuristic fallback |
| "Memory Service errors" | Ensure `soorma dev --build` completed, check database with `docker ps` |

## Next Steps

- **[docs/MEMORY_PATTERNS.md](../../docs/MEMORY_PATTERNS.md)** - Comprehensive memory patterns guide
- **[docs/EVENT_PATTERNS.md](../../docs/EVENT_PATTERNS.md)** - DisCo event patterns and best practices
- **08-planner-worker-basic (coming soon)** - Trinity pattern with goal decomposition

