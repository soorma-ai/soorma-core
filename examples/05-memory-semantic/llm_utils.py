"""
Reusable LLM utilities for event selection and reasoning.

These utilities are used by agents to:
1. Use LLM to select the appropriate event
2. Validate and publish the selected event

Note: Event discovery and formatting are done via context.toolkit methods:
  - context.toolkit.discover_actionable_events(topic)
  - context.toolkit.format_for_llm(events)
  - context.toolkit.format_as_prompt_text(event_dicts)
"""

import json
import os
from litellm import completion
from soorma.context import PlatformContext
from soorma_common.models import EventDefinition


async def select_event_with_llm(
    prompt_template: str,
    context_data: dict,
    formatted_events: str,
    model: str = None
) -> dict:
    """
    Use LLM to select the most appropriate event based on context.
    
    Args:
        prompt_template: Domain-specific prompt with {context_data} and {events} placeholders
        context_data: Data to pass to the LLM for decision making
        formatted_events: Formatted string of available events from context.toolkit.format_as_prompt_text()
        model: LLM model name (defaults to LLM_MODEL env var or gpt-4o-mini)
    
    Returns:
        Dict with:
        - event_name: Selected event name
        - reason: Why this event was selected
        - data: Payload data for the event
    """
    # Build the full prompt
    prompt = prompt_template.format(
        context_data=json.dumps(context_data, indent=2),
        events=formatted_events
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
    events: list[EventDefinition],
    topic: str,
    context: PlatformContext,
    correlation_id: str = None
) -> bool:
    """
    Validate LLM's event selection and publish the event.
    
    This prevents LLM hallucinations by ensuring the selected event exists.
    
    Args:
        decision: LLM's decision with event_name and data
        events: Available events (EventDefinition objects for validation)
        topic: Topic to publish to
        context: PlatformContext with EventBus client
        correlation_id: Optional correlation ID for request/response pattern
    
    Returns:
        True if event was published successfully, False otherwise
    """
    event_names = [e.event_name for e in events]
    
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
