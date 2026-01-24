"""
Knowledge Store Tool

A stateless tool that stores knowledge in semantic memory.
Uses event-driven choreography pattern.
"""

from typing import Any, Dict
from soorma import Tool
from soorma.context import PlatformContext
from events import (
    STORE_KNOWLEDGE_EVENT,
    KNOWLEDGE_STORED_EVENT,
    KnowledgeStoredPayload,
)


# Create a Tool for storing knowledge
tool = Tool(
    name="knowledge-store",
    description="Stores knowledge and facts in semantic memory",
    capabilities=["knowledge-storage"],
    events_consumed=[STORE_KNOWLEDGE_EVENT],
    events_produced=[KNOWLEDGE_STORED_EVENT],
)


@tool.on_event("knowledge.store", topic="action-requests")
async def store_knowledge(event: Dict[str, Any], context: PlatformContext):
    """
    Store knowledge in semantic memory.
    
    This is a deterministic operation - just store the content
    with its metadata in the memory service.
    """
    data = event.get("data", {})
    content = data.get("content", "")
    metadata = data.get("metadata", {})
    user_id = data.get("user_id", "00000000-0000-0000-0000-000000000001")
    
    print(f"\n📚 Storing knowledge:")
    print(f"   Content: {content[:100]}...")
    print(f"   Metadata: {metadata}")
    
    try:
        # Store in semantic memory
        await context.memory.store_knowledge(
            content=content,
            user_id=user_id,
            metadata=metadata
        )
        
        print("   ✓ Stored successfully\n")
        
        # Publish success event using structured payload
        payload = KnowledgeStoredPayload(
            content=content,
            success=True,
            message="Knowledge stored successfully"
        )
        
        await context.bus.respond(
            event_type=KNOWLEDGE_STORED_EVENT.event_name,
            data=payload.model_dump(),
            correlation_id=event.get("correlation_id"),
        )
        
    except Exception as e:
        print(f"   ❌ Error storing knowledge: {e}\n")
        
        # Publish failure event using structured payload
        payload = KnowledgeStoredPayload(
            content=content,
            success=False,
            message=f"Failed to store knowledge: {str(e)}"
        )
        
        await context.bus.respond(
            event_type=KNOWLEDGE_STORED_EVENT.event_name,
            data=payload.model_dump(),
            correlation_id=event.get("correlation_id"),
        )


if __name__ == "__main__":
    print("🔧 Knowledge Store Tool starting...")
    print("Listening for knowledge.store events on action-requests topic")
    print()
    
    tool.run()
