#!/usr/bin/env python3
"""
LLM Utilities for Event Selection

This file contains generic utilities that will be provided by the Soorma SDK.
These patterns are common across many agents (see research-advisor/planner.py).

This file exists to:
1. Clearly separate "what will be SDK" from "agent-specific logic"
2. Demonstrate the pattern for educational purposes
3. Serve as reference for SDK implementation

Future SDK API (not yet available):
  - context.discover_events(topic, filters) -> list[dict]
  - context.select_next_action(prompt_template, events, state) -> dict
  - context.execute_decision(decision) -> None
"""

import json
import os
from litellm import completion
from soorma.ai.event_toolkit import EventToolkit


async def discover_events(context, topic: str) -> list[dict]:
    """
    Discover available events from the Registry for a given topic.
    
    This is a generic utility that will become context.discover_events() in the SDK.
    
    Args:
        context: Platform context with registry access
        topic: Event topic to filter by (e.g., "action-requests")
        
    Returns:
        List of event dictionaries with name, description, metadata
    """
    async with EventToolkit(context.registry.base_url) as toolkit:
        events = await toolkit.discover_actionable_events(topic=topic)
        return events


def format_events_for_llm(events: list[dict]) -> str:
    """
    Format discovered events for LLM consumption.
    
    This is a generic formatter that will be part of the SDK.
    Agents can customize the format via prompt templates.
    
    Args:
        events: List of event dictionaries from Registry
        
    Returns:
        Formatted string suitable for LLM prompts
    """
    formatted = []
    for i, event in enumerate(events, 1):
        metadata = event.get("metadata", {})
        when_to_use = metadata.get("when_to_use", "No guidance provided")
        
        formatted.append(
            f"{i}. **{event['name']}**\n"
            f"   Description: {event['description']}\n"
            f"   When to use: {when_to_use}\n"
        )
    return "\n".join(formatted)


async def select_event_with_llm(
    prompt_template: str,
    context_data: dict,
    events: list[dict],
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
    # Format the available events
    event_options = format_events_for_llm(events)
    
    # Build the LLM prompt by substituting template variables
    prompt = prompt_template.format(
        context_data=json.dumps(context_data, indent=2),
        events=event_options
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
    events: list[dict],
    topic: str,
    context
) -> bool:
    """
    Validate the LLM's decision and publish the event.
    
    This will be part of context.execute_decision() in the SDK.
    Prevents LLMs from hallucinating non-existent events.
    
    Args:
        decision: LLM decision dict with event_name, reason, data
        events: Available events from Registry (for validation)
        topic: Topic to publish to
        context: Platform context with event bus access
        
    Returns:
        True if published successfully, False otherwise
    """
    event_names = [e["name"] for e in events]
    
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
