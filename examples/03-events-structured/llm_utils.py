#!/usr/bin/env python3
"""
LLM Utilities for Event Selection

This file contains generic utilities that are used with the Soorma SDK.
These patterns are common across many agents.

This file demonstrates:
1. How to use SDK-provided event discovery and formatting
2. How to integrate LLM-based decision making
3. How to validate and publish events safely

Available SDK APIs:
  - context.toolkit.discover_actionable_events(topic) -> list[EventDefinition]
  - context.toolkit.format_for_llm(events) -> list[dict]
  - context.toolkit.format_as_prompt_text(event_dicts) -> str
  - context.bus.publish(event_type, topic, data, correlation_id)
"""

import json
import os
from litellm import completion
from soorma.ai.event_toolkit import EventToolkit
from soorma.context import PlatformContext
from soorma_common.models import EventDefinition

async def select_event_with_llm(
    prompt_template: str,
    context_data: dict,
    formatted_events: str,
    model: str = None
) -> dict:
    """
    Use an LLM to select the most appropriate event based on context.
    
    This is a generic selector that will become context.select_next_action() in the SDK.
    Agents provide their domain-specific prompt template.
    
    Args:
        prompt_template: Agent-specific prompt with placeholders {context_data}, {events}
        context_data: Current state/data to reason about
        events: Available events from Registry
        model: LLM model to use (defaults to LLM_MODEL env var or gpt-4o-mini)
        
    Returns:
        dict with keys: event_name, reason, data
    """
    # Build the LLM prompt by substituting template variables
    prompt = prompt_template.format(
        context_data=json.dumps(context_data, indent=2),
        events=formatted_events
    )
    
    # Get LLM model from parameter or environment
    model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    # Call LLM
    response = completion(
        model=model,
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
    context: PlatformContext
) -> bool:
    """
    Validate the LLM's decision and publish the event.
    
    This will be part of context.execute_decision() in the SDK.
    Prevents LLMs from hallucinating non-existent events.
    
    Args:
        decision: LLM decision dict with event_name, reason, data
        events: Available events from Registry (EventDefinition objects for validation)
        topic: Topic to publish to
        context: Platform context with event bus access
        
    Returns:
        True if published successfully, False otherwise
    """
    event_names = [e.event_name for e in events]
    
    # Validate event exists
    if decision["event_name"] not in event_names:
        print(f"   ✗ ERROR: LLM selected invalid event: {decision['event_name']}")
        print(f"   Available events: {event_names}")
        print("   This demonstrates why validation is important!")
        return False
    
    # Publish the event
    try:
        await context.bus.publish(
            event_type=decision["event_name"],
            topic=topic,
            data=decision["data"],
        )
        print("   ✓ Event published successfully")
        return True
        
    except Exception as e:
        print(f"   ✗ Failed to publish event: {e}")
        return False
