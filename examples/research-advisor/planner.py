import asyncio
import json
import os
from typing import Dict, Any, List
from soorma import Planner
from soorma.context import PlatformContext
from soorma.ai.event_toolkit import EventToolkit
from litellm import completion
from llm_utils import get_llm_model

from events import (
    GOAL_EVENT, FULFILLED_EVENT,
    RESEARCH_REQUEST_EVENT, RESEARCH_RESULT_EVENT,
    ADVICE_REQUEST_EVENT, ADVICE_RESULT_EVENT,
    VALIDATION_REQUEST_EVENT, VALIDATION_RESULT_EVENT,
    GoalPayload, ResearchResultPayload,
    DraftResultPayload, ValidationResultPayload
)

# Create the Planner
planner = Planner(
    name="agent-orchestrator",
    description="Orchestrates workflows using autonomous LLM reasoning over discovered events",
    capabilities=["orchestration"],
    events_consumed=[GOAL_EVENT],
    events_produced=[FULFILLED_EVENT]
)

@planner.on_startup
async def startup():
    print(f"\n🚀 {planner.name} started! Ready to orchestrate with autonomous choreography.")

@planner.on_shutdown
async def shutdown():
    print(f"\n🛑 {planner.name} shutting down. Goodbye!")

# In-memory state for the demo (in production, use context.memory)
workflow_state = {
    "history": [],
    "current": {}
}

# Circuit breaker settings
MAX_TOTAL_ACTIONS = 10  # Maximum actions per goal to prevent infinite loops


def format_events_for_llm(events: List[dict]) -> str:
    """Format discovered events with their metadata for LLM reasoning."""
    formatted = []
    for e in events:
        event_info = {
            "event_name": e.get("name"),
            "description": e.get("description"),
            "purpose": e.get("purpose", "Not specified"),
            "payload_schema": e.get("payload_fields", e.get("payload_schema", {})),
        }
        formatted.append(event_info)
    return json.dumps(formatted, indent=2)


async def get_next_action(trigger_context: str, workflow_data: dict, available_events: list) -> Dict[str, Any]:
    """
    Asks LLM to decide the next action based on:
    - The trigger context (what just happened)
    - Current workflow state (accumulated data)
    - Available events discovered from registry (with their metadata)
    
    The LLM reasons autonomously based on event descriptions and schemas.
    """
    current_state = workflow_data.get("current", {})
    action_history = current_state.get("action_history", [])
    
    # Circuit Breaker - prevent infinite loops
    if len(action_history) >= MAX_TOTAL_ACTIONS:
        print(f"   🔌 Circuit Breaker: Max actions ({MAX_TOTAL_ACTIONS}) reached. Forcing completion.")
        # Try to return best available result
        draft_text = current_state.get("draft", {}).get("draft_text")
        research_summary = current_state.get("research", {}).get("summary")
        result = draft_text or research_summary or "Process completed (max actions reached)."
        return {
            "action": "complete",
            "result": result,
            "reasoning": "Circuit breaker: maximum actions reached."
        }

    if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")):
        print("   ⚠️  No API key found. Using mock response.")
        # Simple mock for demo without API keys
        return {"action": "wait", "reasoning": "No LLM API key configured."}

    # Format the prompt for autonomous reasoning
    prompt = f"""You are an autonomous orchestrator agent using the DisCo (Distributed Cognition) protocol.

Your task: Analyze the current state and select the BEST next action from the discovered events to progress toward fulfilling the user's goal.

## TRIGGER CONTEXT (What just happened)
{trigger_context}

## CURRENT WORKFLOW STATE
{json.dumps(current_state, indent=2)}

## PREVIOUS ACTIONS IN THIS WORKFLOW
{json.dumps(action_history, indent=2)}

## DISCOVERED AVAILABLE EVENTS
These events were dynamically discovered from the registry. Each has metadata describing its purpose and required payload:

{format_events_for_llm(available_events)}

## YOUR TASK
1. Analyze what data you have accumulated in the workflow state
2. Read the descriptions and payload schemas of available events
3. Determine which event would best progress toward the user's goal
4. Construct the appropriate payload using data from the workflow state

## DECISION GUIDELINES
- Choose events based on their DESCRIPTION and PURPOSE - they tell you what each event does
- Match payload fields using data available in the workflow state
- Progress logically: gather information → process/draft it → validate/fact-check → deliver results
- IMPORTANT: If there is a validation/fact-checking event available, use it BEFORE completing - accuracy matters!
- Only mark as "complete" AFTER validation has passed, or if no validation event is available
- Do NOT repeat the same action if it won't provide new information

## RESPONSE FORMAT
Return a JSON object with:
- "action": Either "publish" (to trigger an event) or "complete" (if goal is fulfilled)
- "event": The exact event_name to publish (only if action is "publish")
- "payload": The payload object matching the event's schema (only if action is "publish")
- "result": The final result text (only if action is "complete") - THIS MUST BE THE ACTUAL CONTENT (e.g., draft_text), NOT a summary or description
- "reasoning": Brief explanation of why you chose this action based on event descriptions

CRITICAL FOR COMPLETION:
When action is "complete", the "result" field MUST contain the ACTUAL CONTENT to deliver to the user.
- If there is a draft in the workflow state, use the draft_text value as the result
- If there is research but no draft, use the research summary as the result
- NEVER put a description like "The draft is ready" - put the ACTUAL draft content

Example for publish:
{{"action": "publish", "event": "some.event.name", "payload": {{"field": "value"}}, "reasoning": "..."}}

Example for complete (CORRECT - uses actual content):
{{"action": "complete", "result": "NATS is a lightweight messaging system that... [actual detailed content here]", "reasoning": "Draft is complete and validated, delivering to user."}}

Example for complete (WRONG - do not do this):
{{"action": "complete", "result": "The draft response is ready and prepared.", "reasoning": "..."}}
"""

    try:
        response = completion(
            model=get_llm_model(),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"   ❌ LLM Error: {e}")
        return {"action": "wait", "reasoning": f"LLM error: {e}"}


async def execute_decision(decision: dict, available_events: list, context: PlatformContext):
    """Execute the LLM's decision - either publish an event or complete the workflow."""
    action = decision.get("action")
    reasoning = decision.get("reasoning", "No reasoning provided")
    
    print(f"   🤖 LLM Decision: {action}")
    print(f"   🤖 Reasoning: {reasoning}")
    
    if action == "publish":
        event_name = decision.get("event")
        payload = decision.get("payload", {})
        
        # Track action in history
        if 'current' in workflow_state:
            if 'action_history' not in workflow_state['current']:
                workflow_state['current']['action_history'] = []
            workflow_state['current']['action_history'].append(event_name)
        
        # Find the event definition to get the topic
        target_event = next((e for e in available_events if e["name"] == event_name), None)
        
        if target_event:
            print(f"   📤 Publishing: {event_name}")
            print(f"   📦 Payload: {json.dumps(payload, indent=2)[:200]}...")  # Truncate for display
            await context.bus.publish(
                event_type=event_name,
                topic=target_event["topic"],
                data=payload
            )
        else:
            print(f"   ⚠️  Event '{event_name}' not found in discovered events.")
            print(f"   📋 Available: {[e['name'] for e in available_events]}")
            
    elif action == "complete":
        result = decision.get("result", "")
        
        # Safeguard: If LLM returned a vague result, use actual content from workflow state
        current_state = workflow_state.get("current", {})
        draft_text = current_state.get("draft", {}).get("draft_text", "")
        research_summary = current_state.get("research", {}).get("summary", "")
        
        # Check if result looks like a meta-description rather than actual content
        vague_indicators = [
            "draft is ready", "draft is prepared", "draft response is", 
            "already prepared", "has been generated", "is complete",
            "next step", "deliver this", "fulfill your"
        ]
        is_vague = any(indicator in result.lower() for indicator in vague_indicators)
        
        if is_vague or len(result) < 100:
            # Use actual content instead
            if draft_text:
                print(f"   🔄 Using actual draft_text instead of LLM summary")
                result = draft_text
            elif research_summary:
                print(f"   🔄 Using actual research summary instead of LLM summary")
                result = research_summary
        
        print(f"   ✅ Workflow COMPLETE")
        print(f"   📝 Result: {result[:200]}...")  # Truncate for display
        
        # Publish the fulfillment event
        await context.bus.publish(
            event_type=FULFILLED_EVENT.event_name,
            topic=FULFILLED_EVENT.topic,
            data={"result": result, "source": "Autonomous Orchestrator"}
        )
        
        # Archive completed workflow
        if workflow_state.get("current"):
            workflow_state["current"]["final_result"] = result
            workflow_state["history"].append(workflow_state["current"])
            workflow_state["current"] = {}
            
    elif action == "wait":
        print(f"   ⏳ Waiting... ({reasoning})")
    else:
        print(f"   ⚠️  Unknown action: {action}")


async def discover_and_decide(trigger_context: str, context: PlatformContext):
    """Discover available events and let LLM decide next action."""
    async with EventToolkit(context.registry.base_url) as toolkit:
        # Discover all actionable events from the registry
        events = await toolkit.discover_actionable_events(topic="action-requests")
        
        # Also include the fulfillment event as a possible action
        events.append({
            "name": FULFILLED_EVENT.event_name,
            "description": FULFILLED_EVENT.description,
            "purpose": "Deliver the final result to the user when the goal is fully addressed",
            "topic": FULFILLED_EVENT.topic,
            "payload_fields": {"result": {"type": "string", "description": "The final answer"}, 
                             "source": {"type": "string", "description": "Source attribution"}}
        })
        
        print(f"   🔍 Discovered {len(events)} events: {[e['name'] for e in events]}")
        
        decision = await get_next_action(trigger_context, workflow_state, events)
        await execute_decision(decision, events, context)


@planner.on_event(GOAL_EVENT.event_name)
async def handle_goal(event: dict, context: PlatformContext):
    """Handle new goal - start fresh workflow."""
    print(f"\n📋 Planner received GOAL: {event.get('id')}")
    data = event.get("data", {})
    
    # Archive previous workflow if any
    if workflow_state.get("current"):
        workflow_state["history"].append(workflow_state["current"])
    
    # Start new workflow
    workflow_state['current'] = {
        'goal': data,
        'action_history': []
    }
    
    trigger_context = f"New goal received from user: '{data.get('goal', 'Unknown goal')}'. This is the starting point - analyze available events to determine how to fulfill this goal."
    await discover_and_decide(trigger_context, context)


@planner.on_event(RESEARCH_RESULT_EVENT.event_name)
async def handle_research_result(event: dict, context: PlatformContext):
    """Handle research completion - store results and decide next step."""
    print(f"\n📋 Planner received RESEARCH RESULT: {event.get('id')}")
    data = event.get("data", {})
    
    if 'current' not in workflow_state:
        workflow_state['current'] = {'action_history': []}
    workflow_state['current']['research'] = data
    
    summary_preview = data.get('summary', '')[:100]
    trigger_context = f"Research completed. Summary: '{summary_preview}...'. Now have research data available. Determine next step to progress toward the goal."
    await discover_and_decide(trigger_context, context)


@planner.on_event(ADVICE_RESULT_EVENT.event_name)
async def handle_advice_result(event: dict, context: PlatformContext):
    """Handle draft completion - store draft and decide next step."""
    print(f"\n📋 Planner received DRAFT RESULT: {event.get('id')}")
    data = event.get("data", {})
    
    if 'current' not in workflow_state:
        workflow_state['current'] = {'action_history': []}
    workflow_state['current']['draft'] = data
    
    # Clear any previous validation when new draft arrives
    if 'validation' in workflow_state['current']:
        del workflow_state['current']['validation']
    
    draft_preview = data.get('draft_text', '')[:100]
    trigger_context = f"""Draft completed. Preview: '{draft_preview}...'. 

A draft response is now available in the workflow state. 

IMPORTANT: Before delivering content to users, it should be validated/fact-checked against the source research to ensure accuracy. Look for a validation event in the discovered events that can verify the draft against the research data."""
    await discover_and_decide(trigger_context, context)


@planner.on_event(VALIDATION_RESULT_EVENT.event_name)
async def handle_validation_result(event: dict, context: PlatformContext):
    """Handle validation result - decide whether to retry or complete."""
    print(f"\n📋 Planner received VALIDATION RESULT: {event.get('id')}")
    data = event.get("data", {})
    
    if 'current' not in workflow_state:
        workflow_state['current'] = {'action_history': []}
    workflow_state['current']['validation'] = data
    
    is_valid = data.get("is_valid", False)
    critique = data.get("critique", "No critique provided")
    
    if is_valid:
        trigger_context = f"Validation PASSED. The draft has been approved. Critique: '{critique}'. The goal can now be fulfilled with the validated draft."
    else:
        trigger_context = f"Validation FAILED. Critique: '{critique}'. The draft needs improvement based on this feedback. Determine how to address the issues."
    
    await discover_and_decide(trigger_context, context)


if __name__ == "__main__":
    planner.run()
