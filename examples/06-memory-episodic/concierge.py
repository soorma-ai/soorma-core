"""
Concierge agent that helps users explore their conversation history.

This agent:
1. Retrieves session state from working memory
2. Cross-references with episodic memory
3. Uses LLM to provide intelligent summaries and insights
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from litellm import completion
from soorma import Worker
from soorma.context import PlatformContext
from soorma_common import EventDefinition
from soorma_common.events import EventEnvelope, EventTopic
from soorma.workflow import WorkflowState

from examples.shared.auth import build_example_token_provider


EXAMPLE_NAME = "06-memory-episodic"
EXAMPLE_TOKEN_PROVIDER = build_example_token_provider(EXAMPLE_NAME, __file__)


# Define event types
CONCIERGE_QUERY_EVENT = EventDefinition(
    event_name="concierge.query",
    topic=EventTopic.ACTION_REQUESTS,
    description="Query for concierge service"
)

CHAT_RESPONSE_EVENT = EventDefinition(
    event_name="chat.response",
    topic=EventTopic.ACTION_RESULTS,
    description="Chat response to user"
)


concierge = Worker(
    name="chatbot-concierge",
    description="Helps users explore and understand their conversation history",
    capabilities=["conversation-analysis", "history-retrieval"],
    events_consumed=[CONCIERGE_QUERY_EVENT],
    events_produced=[CHAT_RESPONSE_EVENT],
    auth_token_provider=EXAMPLE_TOKEN_PROVIDER,
)


async def analyze_session(session_id: str, query: str, history: List[Dict]) -> str:
    """
    Analyze session history and respond to user's query using LLM.
    """
    if not history:
        return "This is a new session. We haven't discussed anything yet."
    
    # Format history for LLM
    conversation = "\n".join([
        f"{h.get('role', 'unknown').upper()}: {h.get('content', '')}" 
        for h in history[-20:]  # Last 20 messages
    ])
    
    prompt = f"""You are a helpful assistant analyzing a conversation session.

CONVERSATION HISTORY:
{conversation}

USER QUERY:
"{query}"

INSTRUCTIONS:
Analyze the conversation and answer the user's query about it.
- If asked about what was discussed, provide a clear summary
- If asked for counts, provide accurate numbers
- If asked about specific topics, find and reference them
- Be concise but helpful
- Use natural language

Your response:"""
    
    try:
        response = completion(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"     LLM analysis failed: {e}, using fallback")
        # Fallback to simple summary
        user_messages = [h for h in history if h.get("role") == "user"]
        assistant_messages = [h for h in history if h.get("role") == "assistant"]
        return (
            f"In this session, we've exchanged {len(history)} messages. "
            f"You've sent {len(user_messages)} messages and "
            f"I've provided {len(assistant_messages)} responses."
        )


@concierge.on_event("concierge.query", topic=EventTopic.ACTION_REQUESTS)
async def handle_concierge_query(event: EventEnvelope, context: PlatformContext):
    """Handle queries about conversation history."""
    data = event.data or {}
    query = data.get("query", "")
    session_id = data.get("session_id")
    
    tenant_id = event.tenant_id or "00000000-0000-0000-0000-000000000000"
    user_id = event.user_id or "00000000-0000-0000-0000-000000000001"
    
    print(f"\n🏨 Concierge Processing Query")
    print(f"   Session: {session_id}")
    print(f"   Query: {query[:80]}...")
    
    # Get session state from working memory
    state = WorkflowState(
        context.memory,
        session_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    # Retrieve session history from working memory
    print("   📖 Retrieving session history from working memory...")
    history = await state.get("history") or []
    
    # Also get episodic memory for this session (backup/verification)
    # Note: Episodic memory is per-agent, so we search the router's logs
    print("   🔍 Checking episodic memory...")
    recent = await context.memory.get_recent_history(
        agent_id="chatbot-router",  # Router logs all user messages
        user_id=user_id,
        limit=50
    )
    
    # Filter by session
    session_interactions = [
        r for r in recent
        if r.get("metadata", {}).get("session_id") == session_id
    ]
    
    print(f"     Found {len(history)} items in working memory")
    print(f"     Found {len(session_interactions)} interactions in episodic memory")
    
    # Analyze and respond
    print("   💭 Analyzing conversation...")
    response = await analyze_session(session_id, query, history)
    
    # Log interaction
    await context.memory.log_interaction(
        agent_id="chatbot-concierge",
        role="user",
        content=query,
        user_id=user_id,
        metadata={"session_id": session_id, "type": "concierge_query"}
    )
    
    await context.memory.log_interaction(
        agent_id="chatbot-concierge",
        role="assistant",
        content=response,
        user_id=user_id,
        metadata={"session_id": session_id, "type": "concierge_response"}
    )
    
    # Update session history in working memory
    history.append({"role": "user", "content": query})
    history.append({"role": "assistant", "content": response})
    await state.set("history", history)
    
    # Send response
    print(f"   ✓ Response ready")
    
    # Extract response event from request (caller specifies expected response)
    response_event_type = event.response_event or "concierge.response"
    
    await context.bus.respond(
        event_type=response_event_type,
        data={
            "session_id": session_id,
            "response": response
        },
        correlation_id=event.correlation_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )


if __name__ == "__main__":
    print("🏨 Concierge Agent (Conversation History Assistant)")
    print("=" * 50)
    print("Helps users explore their conversation history:")
    print("  • Summarize what was discussed")
    print("  • Count messages and interactions")
    print("  • Recall specific parts of conversation")
    print("  • Provide conversation insights")
    print("\nUses:")
    print("  • Working memory (session state)")
    print("  • Episodic memory (interaction history)")
    print("\nListening for concierge.query events...")
    print("=" * 50)
    
    concierge.run()
