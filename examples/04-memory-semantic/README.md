# 04 - Memory Semantic (RAG with LLM Routing)

**Concepts:** Semantic memory (RAG), LLM-based routing, Knowledge management, Grounded answers  
**Difficulty:** Intermediate  
**Prerequisites:** [03-events-structured](../03-events-structured/)

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

## Code Walkthrough

### Event Definitions ([events.py](events.py))

Defines the event API for the system:

```python
# User input
USER_REQUEST_EVENT = EventDefinition(
    event_name="user.request",
    topic=EventTopic.ACTION_REQUESTS,
    description="User request that needs to be routed...",
)

# Actions (what router can choose)
STORE_KNOWLEDGE_EVENT = EventDefinition(
    event_name="knowledge.store",
    description="Store factual knowledge in semantic memory...",
)

ANSWER_QUESTION_EVENT = EventDefinition(
    event_name="question.ask",
    description="Answer a question using stored knowledge...",
)

# Results
KNOWLEDGE_STORED_EVENT = EventDefinition(...)
QUESTION_ANSWERED_EVENT = EventDefinition(...)
```

### LLM Utilities ([llm_utils.py](llm_utils.py))

Reusable functions from example 03:

- `discover_events()` - Find available events from Registry
- `format_events_for_llm()` - Format for LLM consumption
- `select_event_with_llm()` - Use LLM to choose event
- `validate_and_publish()` - Prevent hallucinations, publish event

### Router ([router.py](router.py))

Uses LLM to detect intent and route requests:

```python
@worker.on_event("user.request", topic="action-requests")
async def route_request(event, context):
    data = event.get("data", {})
    request = data.get("request", "")
    
    # Step 1: Discover available actions from Registry
    events = await discover_events(context, topic="action-requests")
    
    # Filter to our action events (knowledge.store and question.ask)
    action_events = [e for e in events if e["name"] in ["knowledge.store", "question.ask"]]
    
    # Step 2: LLM selects appropriate action
    decision = await select_event_with_llm(
        prompt_template=ROUTING_PROMPT,  # Domain-specific instructions
        context_data={"request": request},
        events=action_events
    )
    
    # Step 3: Validate and publish
    await validate_and_publish(
        decision=decision,
        events=action_events,
        topic="action-requests",
        context=context,
        correlation_id=event.get("correlation_id")
    )
```

The prompt guides the LLM:
- "Use knowledge.store if user wants to teach/store/remember"
- "Use question.ask if user wants to get/query/learn"

### Knowledge Store ([knowledge_store.py](knowledge_store.py))

Simple, deterministic Tool:

```python
@tool.on_event("knowledge.store", topic="action-requests")
async def store_knowledge(event, context):
    data = event.get("data", {})
    content = data.get("content", "")
    metadata = data.get("metadata", {})
    user_id = data.get("user_id", "00000000-0000-0000-0000-000000000001")
    
    # Store in semantic memory
    await context.memory.store_knowledge(
        content=content,
        user_id=user_id,
        metadata=metadata
    )
    
    # Confirm success using structured payload
    payload = KnowledgeStoredPayload(
        content=content,
        success=True,
        message="Knowledge stored successfully"
    )
    
    await context.bus.respond(
        event_type=KNOWLEDGE_STORED_EVENT.event_name,
        data=payload.model_dump(),
        correlation_id=event.get("correlation_id")
    )
```

**Why a Tool?** Storage is stateless and deterministic - perfect for Tool pattern.

### Answer Agent ([answer_agent.py](answer_agent.py))

RAG-powered Worker with LLM:

```python
@worker.on_event("question.ask", topic="action-requests")
async def answer_question(event, context):
    data = event.get("data", {})
    question = data.get("question", "")
    user_id = data.get("user_id", "00000000-0000-0000-0000-000000000001")
    
    # Step 1: Retrieve relevant knowledge from semantic memory
    knowledge_results = await context.memory.search_knowledge(
        query=question,
        user_id=user_id,
        limit=5
    )
    
    # No knowledge found - admit we don't know
    if not knowledge_results:
        payload = QuestionAnsweredPayload(
            question=question,
            answer="I don't have enough knowledge to answer that question. You can teach me by providing relevant information first.",
            knowledge_used=[],
            has_knowledge=False
        )
        await _send_response(event, context, payload)
        return
    
    # Step 2: Build context from retrieved knowledge (helper function)
    knowledge_list, context_text = _build_knowledge_context(knowledge_results)
    
    # Step 3: Generate grounded answer with LLM (helper function)
    try:
        answer = await _generate_grounded_answer(question, context_text)
        
        payload = QuestionAnsweredPayload(
            question=question,
            answer=answer,
            knowledge_used=knowledge_list,
            has_knowledge=True
        )
    except Exception as e:
        # Fallback if LLM fails
        payload = QuestionAnsweredPayload(
            question=question,
            answer=f"I found relevant information but encountered an error...\n\n{context_text}",
            knowledge_used=knowledge_list,
            has_knowledge=True
        )
    
    await _send_response(event, context, payload)
```

**Code Organization:** The handler uses three helper functions:
- `_build_knowledge_context()` - Formats knowledge results for LLM
- `_generate_grounded_answer()` - LLM completion call with grounding prompt
- `_send_response()` - Publishes structured response event

**Why a Worker?** Answer generation requires reasoning and LLM calls - Worker pattern.

**Key Feature:** Answers are grounded in stored knowledge. No hallucinations.

### Client ([client.py](client.py))

Unified interface for both operations:

```python
# Interactive mode
python3 client.py

# Single request mode
python3 client.py "Python was created by Guido van Rossum"
python3 client.py "Who created Python?"
```

The client doesn't need to know about routing - it just sends requests and gets responses.

## Running the Example

### Prerequisites

**Terminal 1: Start Platform Services**

```bash
# From soorma-core root directory
soorma dev --build
```

**Set your OpenAI API key:**

```bash
export OPENAI_API_KEY='your-key-here'
```

This example requires OpenAI API access for:
- Router: Intent detection
- Answer Agent: Grounded answer generation

### Quick Start

**Terminal 2: Start all agents**

```bash
cd examples/04-memory-semantic
./start.sh
```

This will start all three agents (router, knowledge store, answer agent).

**Terminal 3: Use the system**

```bash
# Interactive mode (recommended)
python3 client.py

# Then try:
You: Python was created by Guido van Rossum in 1991
You: Docker is a containerization platform
You: Who created Python?
You: What is Docker?
```

**Or single requests:**

```bash
# Store knowledge
python3 client.py "Python was created by Guido van Rossum in 1991"

# Ask questions
python3 client.py "Who created Python?"
```

### Expected Output

**Storing Knowledge:**
```
📤 Sending request: Python was created by Guido van Rossum
────────────────────────────────────────────────────────────

🧭 Router: LLM analyzing request...
   Selected: knowledge.store
   Reasoning: User is teaching a fact

📚 Knowledge Store: Storing knowledge...
   ✓ Stored successfully

────────────────────────────────────────────────────────────
📥 Response received (knowledge.stored):

✅ Knowledge stored successfully
────────────────────────────────────────────────────────────
```

**Asking Questions:**
```
📤 Sending request: Who created Python?
────────────────────────────────────────────────────────────

🧭 Router: LLM analyzing request...
   Selected: question.ask
   Reasoning: User is asking a question

❓ Answer Agent: Question: Who created Python?
🔍 Searching semantic memory...
   ✓ Found 2 relevant knowledge fragments
🤖 Generating answer with LLM...
   ✓ Answer generated

────────────────────────────────────────────────────────────
📥 Response received (question.answered):

Q: Who created Python?

A: Python was created by Guido van Rossum in 1991.

📚 Used 2 knowledge sources
   Top relevance: 0.912
────────────────────────────────────────────────────────────
```

## Key Takeaways

✅ **LLM routing enables flexible UX** - Users don't need to specify "store" or "ask"  
✅ **Semantic memory powers RAG** - Knowledge is embedded and searchable  
✅ **Grounded answers prevent hallucinations** - LLM only uses stored facts  
✅ **Tool vs Worker distinction** - Use Tools for deterministic ops, Workers for reasoning  
✅ **Pattern reusability** - Event discovery + LLM selection works across domains  
✅ **Event-driven architecture** - Clean separation between router, storage, and answering

## Pattern Comparison

### vs Example 03 (Events Structured)

| Aspect | Example 03 | Example 04 |
|--------|-----------|-----------|
| Domain | Support ticket routing | Knowledge management |
| Actions | Route to support tiers | Store or answer |
| LLM Use | Select routing target | 1) Detect intent 2) Generate answers |
| Memory | None | Semantic memory (RAG) |
| Pattern | LLM-based routing only | LLM routing + RAG |

### vs Traditional Chatbot

| Traditional Chatbot | This Example |
|---------------------|--------------|
| Hardcoded intents | LLM-detected intents |
| Static knowledge base | Dynamic learning |
| Rule-based routing | Event-based choreography |
| Single monolith | Distributed agents |

## When to Use This Pattern

| Use This Pattern When... | Use Simple Events When... |
|-------------------------|--------------------------|
| Users need natural language interface | API/programmatic access is fine |
| System needs to learn from users | Knowledge is static |
| Multiple agents need coordination | Single agent is sufficient |
| Answers must be grounded in facts | General knowledge is acceptable |

## Advanced Topics

### Memory Isolation

Each user gets isolated memory:

```python
user_id = "user-123"  # From authentication

# Store knowledge for this user
await context.memory.store_knowledge(
    content=content,
    user_id=user_id
)

# Retrieve only this user's knowledge
knowledge = await context.memory.search_knowledge(
    query=question,
    user_id=user_id
)
```

### Metadata and Filtering

Store rich metadata:

```python
await context.memory.store_knowledge(
    content="Python was created by Guido van Rossum",
    metadata={
        "source": "Wikipedia",
        "category": "programming-languages",
        "confidence": 0.95,
        "timestamp": "2024-01-01"
    }
)
```

### Preventing Hallucinations

The answer agent uses several techniques:

1. **Explicit instructions** - "Answer ONLY using this knowledge"
2. **Low temperature** - `temperature=0.3` for factual answers
3. **Fallback message** - "I don't have enough knowledge..." when nothing found
4. **Source transparency** - Returns knowledge fragments used

## Extending the Example

### Add More Capabilities

```python
# Update definitions
UPDATE_KNOWLEDGE_EVENT = EventDefinition(
    event_name="knowledge.update",
    description="Update existing knowledge with corrections",
)

DELETE_KNOWLEDGE_EVENT = EventDefinition(
    event_name="knowledge.delete",
    description="Remove specific knowledge from memory",
)

# Router will automatically discover these new events
```

### Add Authorization

```python
@worker.on_event("knowledge.store", topic="action-requests")
async def store_knowledge(event, context):
    user_id = event.data.get("user_id")
    
    # Check permissions
    if not await can_store_knowledge(user_id):
        await context.bus.respond(
            event_type="knowledge.stored",
            data={"success": False, "message": "Unauthorized"}
        )
        return
    
    # Proceed with storage...
```

### Add Multi-Modal Knowledge

```python
await context.memory.store_knowledge(
    content="Chart showing Python's popularity over time",
    metadata={
        "type": "image",
        "image_url": "https://...",
        "alt_text": "Line chart..."
    }
)
```

## Next Steps

- **05-memory-working** - State sharing across agents in workflows
- **06-memory-episodic** - Conversation history and audit trails  
- **08-planner-worker-basic (coming soon)** - Goal decomposition with semantic memory
- **09-app-research-advisor (coming soon)** - Full autonomous system combining all patterns

---

**📖 Additional Resources:**
- [Memory Patterns Documentation](../../docs/MEMORY_PATTERNS.md)
- [Event Patterns Documentation](../../docs/EVENT_PATTERNS.md)
- [Design Patterns - DisCo Trinity](../../docs/DESIGN_PATTERNS.md)
