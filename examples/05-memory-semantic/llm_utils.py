"""
Reusable LLM utilities for event selection and reasoning.

These utilities are used by agents to:
1. Discover available events from the Registry
2. Format event metadata for LLM consumption
3. Use LLM to select the appropriate event
4. Validate and publish the selected event

Note: In future SDK versions, these will be built-in methods.
"""

import json
import os
from litellm import completion
from soorma.ai.event_toolkit import EventToolkit
from soorma.context import PlatformContext


async def discover_events(context: PlatformContext, topic: str) -> list[dict]:
    """
    Discover available events from Registry for a specific topic.
    
    Args:
        context: PlatformContext with Registry client
        topic: Event topic to filter by (e.g., "action-requests")
    
    Returns:
        List of event definitions with name, description, schema
    """
    async with EventToolkit(context.registry.base_url) as toolkit:
        events = await toolkit.discover_actionable_events(topic=topic)
        return events


def format_events_for_llm(events: list[dict]) -> str:
    """
    Format event metadata into a readable string for LLM prompts.
    
    Args:
        events: List of event definitions from discover_events()
    
    Returns:
        Formatted string with event names and descriptions
    """
    formatted = []
    for event in events:
        formatted.append(
            f"**{event['name']}**\n"
            f"   Description: {event['description']}\n"
        )
    return "\n".join(formatted)


async def select_event_with_llm(
    prompt_template: str,
    context_data: dict,
    events: list[dict],
    model: str = None
) -> dict:
    """
    Use LLM to select the most appropriate event based on context.
    
    Args:
        prompt_template: Domain-specific prompt with {context_data} and {events} placeholders
        context_data: Data to pass to the LLM for decision making
        events: Available events from discover_events()
        model: LLM model name (defaults to LLM_MODEL env var or gpt-4o-mini)
    
    Returns:
        Dict with:
        - event_name: Selected event name
        - reasoning: Why this event was selected
        - data: Payload data for the event
    """
    # Format events for the prompt
    event_options = format_events_for_llm(events)
    
    # Build the full prompt
    prompt = prompt_template.format(
        context_data=json.dumps(context_data, indent=2),
        events=event_options
    )
    
    # Call LLM
    response = completion(
        model=model or os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    # Parse response
    decision = json.loads(response.choices[0].message.content)
    return decision


async def validate_and_publish(
    decision: dict,
    events: list[dict],
    topic: str,
    context: PlatformContext,
    correlation_id: str = None
) -> bool:
    """
    Validate LLM's event selection and publish the event.
    
    This prevents LLM hallucinations by ensuring the selected event exists.
    
    Args:
        decision: LLM's decision with event_name and data
        events: Available events (for validation)
        topic: Topic to publish to
        context: PlatformContext with EventBus client
        correlation_id: Optional correlation ID for request/response pattern
    
    Returns:
        True if event was published successfully, False otherwise
    """
    event_names = [e["name"] for e in events]
    
    # Validate event exists (prevent hallucinations)
    if decision["event_name"] not in event_names:
        print(f"❌ ERROR: LLM selected invalid event: {decision['event_name']}")
        print(f"   Valid options were: {', '.join(event_names)}")
        return False
    
    # Publish the validated event
    await context.bus.publish(
        event_type=decision["event_name"],
        topic=topic,
        data=decision["data"],
        correlation_id=correlation_id,
    )
    
    return True
