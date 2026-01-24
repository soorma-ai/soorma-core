"""
Knowledge Router Agent

This agent uses LLM-based event selection (pattern from example 03) to route
user requests to either knowledge storage or question answering.

It demonstrates:
1. Event discovery from Registry (via llm_utils)
2. LLM-based decision making (via llm_utils)
3. Event-driven choreography (publish selected event)
"""

from typing import Any, Dict
from soorma import Worker
from soorma.context import PlatformContext
from events import USER_REQUEST_EVENT, STORE_KNOWLEDGE_EVENT, ANSWER_QUESTION_EVENT
from llm_utils import discover_events, select_event_with_llm, validate_and_publish


# Create a Worker for routing user requests
worker = Worker(
    name="knowledge-router",
    description="Routes user requests to knowledge storage or question answering",
    capabilities=["routing", "intent-detection"],
    events_consumed=[USER_REQUEST_EVENT],
    events_produced=[STORE_KNOWLEDGE_EVENT, ANSWER_QUESTION_EVENT],
)

# LLM prompt template for routing decisions
ROUTING_PROMPT = """You are a smart router for a knowledge management system.

USER REQUEST:
{context_data}

AVAILABLE ACTIONS:
{events}

INSTRUCTIONS:
1. Analyze the user's request to determine their intent
2. Choose the appropriate action:
   - Use "knowledge.store" if the user wants to:
     * Teach the system something
     * Store facts or information
     * Add knowledge to the system
     * Remember something for later
   
   - Use "question.ask" if the user wants to:
     * Get information or answers
     * Query stored knowledge
     * Learn about something
     * Retrieve facts

3. Extract the relevant data for the chosen action:
   - For knowledge.store: extract the content to store
   - For question.ask: extract the question

Return your decision in this JSON format:
{{
    "event_name": "knowledge.store" or "question.ask",
    "reasoning": "Brief explanation of why you chose this action",
    "data": {{
        "content": "..." (for knowledge.store) OR "question": "..." (for question.ask),
        "user_id": "00000000-0000-0000-0000-000000000001"
    }}
}}

Be precise in extracting the content/question - preserve the user's actual words."""


@worker.on_event("user.request", topic="action-requests")
async def route_request(event: Dict[str, Any], context: PlatformContext):
    """
    Route user requests using LLM-based event selection.
    
    This follows the exact pattern from example 03:
    1. Discover available events
    2. Use LLM to select appropriate event
    3. Validate and publish the selected event
    """
    data = event.get("data", {})
    request = data.get("request", "")
    
    print(f"\n📨 User Request: {request}")
    
    # Step 1: Discover available routing options
    print("🔍 Discovering available actions from Registry...")
    events = await discover_events(context, topic="action-requests")
    
    # Filter to only our action events (knowledge.store and question.ask)
    action_events = [e for e in events if e["name"] in ["knowledge.store", "question.ask"]]
    
    if not action_events:
        print("   ⚠️  No action events found in Registry")
        return
    
    print(f"   ✓ Found {len(action_events)} actions\n")
    
    # Step 2: Let LLM select best action
    print("🤖 LLM analyzing request...")
    decision = await select_event_with_llm(
        prompt_template=ROUTING_PROMPT,
        context_data={"request": request},
        events=action_events
    )
    
    print(f"   Selected: {decision['event_name']}")
    print(f"   Reasoning: {decision['reasoning']}\n")
    
    # Step 3: Validate and publish the decision
    success = await validate_and_publish(
        decision=decision,
        events=action_events,
        topic="action-requests",
        context=context,
        correlation_id=event.get("correlation_id")
    )
    
    if success:
        print(f"✅ Routed to {decision['event_name']}\n")
    else:
        print(f"❌ Failed to route request\n")


if __name__ == "__main__":
    print("🧭 Knowledge Router starting...")
    print("Listening for user.request events on action-requests topic")
    print("\nThis agent will:")
    print("  1. Discover available events from Registry")
    print("  2. Use LLM to determine user intent")
    print("  3. Publish knowledge.store or question.ask event")
    print("\nRequires:")
    print("  - OPENAI_API_KEY environment variable")
    print("  - knowledge-store and answer-agent running")
    print()
    
    worker.run()
