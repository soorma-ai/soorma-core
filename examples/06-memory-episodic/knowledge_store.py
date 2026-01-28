"""
Knowledge store agent that saves information to semantic memory.

This agent:
1. Receives facts/knowledge from users
2. Stores them in semantic memory for future retrieval
3. Confirms storage to user
"""

import asyncio
from typing import Any, Dict
from soorma import Worker
from soorma.context import PlatformContext
from soorma_common.events import EventEnvelope, EventTopic
from soorma.workflow import WorkflowState


knowledge_store = Worker(
    name="chatbot-knowledge",
    description="Stores facts and knowledge to semantic memory",
    capabilities=["knowledge-storage", "fact-extraction"],
    events_consumed=["knowledge.store"],
    events_produced=["chat.response"],
)


async def extract_fact(message: str) -> str:
    """
    Extract the core fact/knowledge from user message.
    
    In production, this would use an LLM to extract and reformat facts.
    For this demo, we do simple cleanup.
    """
    # Remove common prefixes
    prefixes = [
        "remember that", "keep in mind", "note that", "fyi",
        "for your information", "i want you to know", "please remember"
    ]
    
    fact = message.strip()
    for prefix in prefixes:
        if fact.lower().startswith(prefix):
            fact = fact[len(prefix):].strip()
            break
    
    # Ensure it starts with capital and ends with period
    if fact:
        fact = fact[0].upper() + fact[1:]
        if not fact.endswith("."):
            fact += "."
    
    return fact


@knowledge_store.on_event("knowledge.store", topic=EventTopic.ACTION_REQUESTS)
async def store_knowledge(event: EventEnvelope, context: PlatformContext):
    """Store knowledge to semantic memory."""
    data = event.data or {}
    message = data.get("message", "")
    session_id = data.get("session_id")
    
    tenant_id = event.tenant_id or "00000000-0000-0000-0000-000000000000"
    user_id = event.user_id  # User ID from event envelope
    
    print(f"\n📚 Knowledge Store Processing")
    print(f"   Session: {session_id}")
    print(f"   User: {user_id}")
    print(f"   Message: {message[:80]}...")
    
    # Extract fact
    print("   🔍 Extracting fact...")
    fact = await extract_fact(message)
    print(f"   Fact: {fact[:80]}...")
    
    # Store in semantic memory
    print("   💾 Storing to semantic memory...")
    await context.memory.store_knowledge(
        content=fact,
        user_id=user_id,
        metadata={
            "session_id": session_id,
            "original_message": message,
            "source": "user_input"
        }
    )
    
    # Log confirmation to episodic memory
    # Note: User message already logged by router
    response = f"✓ I've stored that information: \"{fact}\"\n\nI'll remember this for future questions."
    
    await context.memory.log_interaction(
        agent_id="chatbot-knowledge",
        role="assistant",
        content=response,
        user_id=user_id,
        metadata={"session_id": session_id, "type": "knowledge_confirmation"}
    )
    
    # Update session state
    state = WorkflowState(
        context.memory,
        session_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    history = await state.get("history") or []
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})
    await state.set("history", history)
    
    # Track stored knowledge count
    knowledge_count = await state.get("knowledge_stored") or 0
    await state.set("knowledge_stored", knowledge_count + 1)
    
    # Send response
    print(f"   ✓ Knowledge stored (total in session: {knowledge_count + 1})")
    
    # Extract response event from request (caller specifies expected response)
    response_event_type = event.response_event or "knowledge.stored"
    
    await context.bus.respond(
        event_type=response_event_type,
        data={
            "session_id": session_id,
            "message": message,
            "fact_stored": fact
        },
        correlation_id=event.correlation_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )


if __name__ == "__main__":
    print("📚 Knowledge Store Agent")
    print("=" * 50)
    print("Stores facts and knowledge to semantic memory:")
    print("  • Extracts core facts from user messages")
    print("  • Stores to semantic memory for future retrieval")
    print("  • Confirms storage to user")
    print("  • Tracks knowledge stored per session")
    print("\nThis demonstrates:")
    print("  • Semantic memory storage")
    print("  • Episodic memory logging")
    print("  • Working memory state tracking")
    print("\nListening for knowledge.store events...")
    print("=" * 50)
    
    knowledge_store.run()
