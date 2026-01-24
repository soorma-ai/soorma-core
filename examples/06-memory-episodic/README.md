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

## Overview

This example demonstrates a **production-grade chatbot architecture** with:

### **Three Memory Types**
1. **Episodic Memory** - All interaction history (conversation log)
2. **Semantic Memory** - Stored knowledge and facts (knowledge base)
3. **Working Memory** - Session state and context (active conversation)

### **Cognitive Architecture**

The chatbot uses 4 specialized agents:

1. **Router** ([router.py](router.py))
   - Classifies user intent using LLM with JSON mode
   - Routes to appropriate handler
   - Logs all interactions
   - Fallback to heuristics if LLM fails

2. **RAG Agent** ([rag_agent.py](rag_agent.py))
   - Answers questions using dual context:
     - Searches episodic memory (past answers)
     - Searches semantic memory (stored knowledge)
   - Uses LLM to synthesize natural answers from contexts
   - Handles cases where context is incomplete

3. **Concierge** ([concierge.py](concierge.py))
   - Helps users explore conversation history
   - Uses LLM to analyze and answer questions about sessions
   - Provides intelligent conversation insights
   - Summarizes topics and interaction patterns

4. **Knowledge Store** ([knowledge_store.py](knowledge_store.py))
   - Extracts and stores facts to semantic memory
   - Confirms storage to user
   - Tracks stored knowledge per session

## How It Works

### Message Flow

```
User → Client → Router → [RAG | Concierge | Knowledge Store] → Response
        (action-requests)                      (action-results)
                  ↓
           Episodic Memory (per-agent logs)
                  ↓
           Working Memory (session state)
```

**DisCo Topics:**
- `action-requests` - All incoming commands and routing decisions
- `action-results` - All responses back to client

### Intent Classification

The router uses LLM with JSON mode to classify messages into:
- **store_knowledge**: "Remember that Python was created by Guido"
- **answer_question**: "What is Python?"
- **concierge**: "What have we discussed?"
- **general**: Everything else

**Note:** Falls back to keyword heuristics if LLM call fails.

### Dual-Context RAG

When answering questions, the RAG agent:
1. Searches episodic memory for past answers
2. Searches semantic memory for stored knowledge
3. Uses LLM to synthesize natural answers from both contexts
4. Handles incomplete context gracefully
5. Logs the interaction for future reference

## Running the Example

### Prerequisites

**1. Set OpenAI API Key:**

```bash
export OPENAI_API_KEY='your-key-here'
```

This example uses LLM for:
- Intent classification (Router)
- Answer synthesis (RAG Agent)
- Conversation analysis (Concierge)

**2. Start platform services:**

```bash
# From soorma-core root directory
soorma dev --build
```

### Quick Start

```bash
cd examples/06-memory-episodic

# Terminal 1: Start all backend agents
bash start.sh

# Terminal 2: Run the interactive client
python client.py
```

### Try These Interactions

**Store Knowledge:**
```
You: Remember that Python was created by Guido van Rossum in 1991
🤖: ✓ I've stored that information...
```

**Ask Questions:**
```
You: What is Python?
🤖: Based on stored knowledge: Python was created by Guido van Rossum in 1991.
     (sources: 0 from history, 1 from knowledge)
```

**Explore History:**
```
You: What have we discussed so far?
🤖: Here's what we've discussed:
     • Remember that Python was created...
     • What is Python?
```

**Session Management:**
```
You: /new
✨ Started new session: session-abc123

You: /quit
👋 Goodbye!
```

## Low-Level Utilities

For debugging and inspection, use these standalone scripts:

### View Conversation History
```bash
python view_history.py
```
Shows all interactions for the demo user. Optionally specify limit:
```bash
python view_history.py 50  # Show last 50 interactions
```

### Search Interactions
```bash
python search_memory.py "Python"
```
Searches past interactions by semantic similarity:
```bash
python search_memory.py "Docker" 10  # Top 10 results
```

**Note:** These utilities use the same hardcoded user ID as the client, so you'll see interactions from your chatbot sessions.

## Key Takeaways

### LLM Integration

✅ **This example demonstrates:**
- LLM-based intent classification with JSON mode
- Context-aware answer generation from dual memory
- Intelligent conversation analysis
- Graceful fallbacks when LLM calls fail
- Production-ready error handling

### When to Use Episodic Memory

✅ **Use episodic memory for:**
- Multi-turn conversations
- User interaction logging
- Personalization based on history
- Audit trails
- Recall of specific past events

❌ **Don't use episodic memory for:**
- Temporary task state (use Working Memory)
- Knowledge/facts (use Semantic Memory)
- Dynamic prompts (use Procedural Memory)

## Architecture Deep Dive

### Agent Responsibilities

#### Router ([router.py](router.py))
```python
@router.on_event("chat.message", topic="action-requests")
async def route_message(event, context):
    # 1. Classify intent using LLM
    classification = await classify_intent(message, history)
    
    # 2. Log to episodic memory
    await context.memory.log_interaction(
        agent_id="chatbot-router",
        role="user",
        content=message,
        user_id=user_id,
        metadata={"intent": classification["intent"]}
    )
    
    # 3. Route to appropriate handler
    if intent == "store_knowledge":
        await context.bus.publish("knowledge.store", ...)
    elif intent == "answer_question":
        await context.bus.publish("question.answer", ...)
```

#### RAG Agent ([rag_agent.py](rag_agent.py))
```python
@rag_agent.on_event("question.answer", topic="action-requests")
async def answer_question(event, context):
    # 1. Search episodic memory (past answers)
    history_context = await context.memory.search_interactions(
        agent_id="chatbot-rag",
        query=question,
        user_id=user_id,
        limit=3
    )
    
    # 2. Search semantic memory (knowledge)
    knowledge_context = await context.memory.search_knowledge(
        query=question,
        user_id=user_id,
        limit=3
    )
    
    # 3. Synthesize answer from both contexts
    answer = await synthesize_answer(
        question, 
        history_context, 
        knowledge_context
    )
    
    # 4. Log interaction
    await context.memory.log_interaction(...)
```

#### Concierge ([concierge.py](concierge.py))
```python
@concierge.on_event("concierge.query", topic="action-requests")
async def handle_query(event, context):
    # 1. Get session state from working memory
    state = WorkflowState(context.memory, session_id, ...)
    history = await state.get("history") or []
    
    # 2. Get episodic memories for session
    session_interactions = await context.memory.get_recent_history(
        agent_id="chatbot-router",
        user_id=user_id,
        limit=50
    )
    
    # 3. Analyze and respond
    response = await analyze_session(query, history)
```

#### Knowledge Store ([knowledge_store.py](knowledge_store.py))
```python
@knowledge_store.on_event("knowledge.store", topic="action-requests")
async def store_knowledge(event, context):
    # 1. Extract fact from message
    fact = await extract_fact(message)
    
    # 2. Store to semantic memory
    await context.memory.store_knowledge(
        content=fact,
        user_id=user_id,
        metadata={"session_id": session_id}
    )
    
    # 3. Log confirmation
    await context.memory.log_interaction(...)
```

## Key Concepts

### Memory Type Selection

| Memory Type | Use Case | Access Pattern |
|-------------|----------|----------------|
| **Episodic** | All interactions (audit log) | Recent + Search |
| **Semantic** | Facts and knowledge | Vector search |
| **Working** | Session state | Key-value (plan-scoped) |

### Why Three Memory Types?

**Episodic Memory:**
- Records *what happened* (conversation log)
- Preserves context and continuity
- Supports audit and replay

**Semantic Memory:**
- Stores *what is known* (knowledge base)
- Enables knowledge retrieval
- Powers RAG systems

**Working Memory:**
- Tracks *current state* (active session)
- Fast key-value access
- Ephemeral, plan-scoped data

### Session Management

Sessions use **Working Memory** for state:
```python
state = WorkflowState(context.memory, session_id, ...)
await state.set("history", [...])
await state.set("knowledge_stored", 5)
```

Benefits:
- Fast access (no search needed)
- Scoped to session (automatic cleanup)
- Structured data (lists, dicts, etc.)

### Best Practices

1. **Separate concerns**: Each agent has one responsibility
2. **Avoid duplicate logging**: Only router logs user messages; responders log their own replies
3. **Use standard DisCo topics**: `action-requests` for commands, `action-results` for responses
4. **Use metadata**: Track intent, session, sources for better debugging
5. **Combine contexts**: RAG with both history and knowledge beats either alone
6. **Session state**: Use working memory for fast, structured session data
7. **Episodic memory is per-agent**: Filter by agent_id to see specific agent's logs

## Troubleshooting

**"No response from agents"**
- Check all agents are running with `bash start.sh`
- Verify Memory Service: `curl http://localhost:8083/health`
- Check logs in agent terminals

**"Search returns empty results"**
- Data may be lost if services were rebuilt
- Try storing new knowledge and asking questions again
- Verify user_id matches (must be UUID format)

**"Intent classification wrong"**
- Router uses LLM for accurate classification
- Ensure OPENAI_API_KEY is set correctly
- Check LLM_MODEL environment variable (defaults to gpt-4o-mini)
- Falls back to heuristics if LLM fails

**"Memory Service errors"**
- Ensure `soorma dev --build` completed successfully
- Check database is running: `docker ps | grep postgres`
- Review service logs: `docker logs soorma-memory`

## Next Steps

- **[07-tool-discovery](../07-tool-discovery/)** - Dynamic capability discovery and tool binding (coming soon)
- **[08-planner-worker-basic](../08-planner-worker-basic/)** - Trinity pattern with goal decomposition (coming soon)
- **[docs/MEMORY_PATTERNS.md](../../docs/MEMORY_PATTERNS.md)** - Comprehensive memory patterns guide
- **[docs/EVENT_PATTERNS.md](../../docs/EVENT_PATTERNS.md)** - DisCo event patterns and best practices

## Additional Resources

- [Memory Patterns Guide](../../docs/MEMORY_PATTERNS.md)
- [CoALA Framework](https://arxiv.org/abs/2309.02427) - Cognitive architecture for LLM agents
- [SDK Memory Client Documentation](../../sdk/python/README.md#memory-client)
- [Event Patterns Guide](../../docs/EVENT_PATTERNS.md) - Multi-agent event patterns

