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
from soorma_common.events import EventEnvelope, EventTopic
from events import USER_REQUEST_EVENT, STORE_KNOWLEDGE_EVENT, ANSWER_QUESTION_EVENT
from llm_utils import select_event_with_llm, validate_and_publish


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
        "content": "..." (for knowledge.store) OR "question": "..." (for question.ask)
    }}
}}

Be precise in extracting the content/question - preserve the user's actual words."""


@worker.on_event("user.request", topic=EventTopic.ACTION_REQUESTS)
async def route_request(event: EventEnvelope, context: PlatformContext):
    """
    Route user requests using LLM-based event selection.
    
    This follows the exact pattern from example 03:
    1. Discover available events via context.toolkit
    2. Use LLM to select appropriate event
    3. Validate and publish the selected event
    """
    data = event.data or {}
    request = data.get("request", "")
    
    print(f"\n📨 User Request: {request}")
    
    # Step 1: Discover available routing options via context.toolkit
    print("🔍 Discovering available actions from Registry...")
    events = await context.toolkit.discover_actionable_events(topic=EventTopic.ACTION_REQUESTS)
    
    # Filter to only our action events (knowledge.store and question.ask)
    action_events = [e for e in events if e.event_name in ["knowledge.store", "question.ask"]]
    
    if not action_events:
        print("   ⚠️  No action events found in Registry")
        return
    
    print(f"   ✓ Found {len(action_events)} actions\n")
    
    # Step 2: Format events and let LLM select best action
    print("🤖 LLM analyzing request...")
    event_dicts = context.toolkit.format_for_llm(action_events)
    formatted_events = context.toolkit.format_as_prompt_text(event_dicts)
    
    decision = await select_event_with_llm(
        prompt_template=ROUTING_PROMPT,
        context_data={"request": request},
        formatted_events=formatted_events
    )
    
    print(f"   Selected: {decision['event_name']}")
    print(f"   Reasoning: {decision['reasoning']}\n")
    
    # Step 3: Validate and publish the decision
    success = await validate_and_publish(
        decision=decision,
        events=action_events,
        topic=EventTopic.ACTION_REQUESTS,
        context=context,
        correlation_id=event.correlation_id,
        user_id=event.user_id  # Propagate user_id from incoming event
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
