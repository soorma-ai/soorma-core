import asyncio
import json
import os
from typing import Dict, Any
from soorma import Planner
from soorma.context import PlatformContext
from soorma.ai.event_toolkit import EventToolkit
from litellm import completion

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
    description="Orchestrates generic research and advice workflows",
    capabilities=["orchestration"],
    events_consumed=[GOAL_EVENT],
    events_produced=[FULFILLED_EVENT]
)

@planner.on_startup
async def startup():
    print(f"\n🚀 {planner.name} started! Ready to orchestrate.")

@planner.on_shutdown
async def shutdown():
    print(f"\n🛑 {planner.name} shutting down. Goodbye!")

# In-memory state for the demo (in production, use context.memory)
workflow_state = {
    "history": [],
    "current": {}
}

async def get_next_action(context_summary: str, workflow_data: dict, available_events: list) -> Dict[str, Any]:
    """
    Asks LLM to decide the next action based on context and available events.
    """
    current_state = workflow_data.get("current", {})

    # Circuit Breaker
    action_history = current_state.get("action_history", [])
    validation_count = action_history.count("agent.validation.requested")
    if validation_count >= 3:
        print(f"   🔌 Circuit Breaker: Validation limit ({validation_count}) reached. Forcing fulfillment.")
        draft_text = current_state.get("draft", {}).get("draft_text", "Process completed (max retries).")
        return {
            "action": "publish",
            "event": "agent.goal.fulfilled",
            "payload": {
                "result": draft_text,
                "source": "Circuit Breaker (Max Retries)"
            },
            "reasoning": "Circuit breaker triggered due to excessive validation loops."
        }

    if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")):
        # Mock logic for demo if no keys
        if "Goal received" in context_summary:
            return {
                "action": "publish", 
                "event": "agent.research.requested",
                "payload": {"query": current_state.get("goal", {}).get("goal"), "context": "General research"}
            }
        # ... (simplified mock logic for brevity)
        return {"action": "wait"}

    prompt = f"""
    You are an autonomous agent orchestrator.
    Your goal is to fulfill the user's request by driving the workflow to completion.
    
    Current Context Summary: {context_summary}
    
    Current Turn State (Active Goal):
    {json.dumps(current_state, indent=2)}
    
    History (Previous Turns):
    {json.dumps(workflow_data.get("history", []), indent=2)}
    
    Available Events to Publish:
    {json.dumps(available_events, indent=2)}
    
    Standard Workflow:
    1. Research: Find relevant information.
    2. Draft: Create a response based on research.
    3. Validate: Check if the response is accurate.
    4. Fulfill: If validation passes, return the drafted text as the final result.
    
    Instructions:
    - Analyze the Current Turn State to determine the next step.
    - Select the MOST APPROPRIATE event from the "Available Events" list.
    - Construct the 'payload' for the event using data from 'Current Turn State'.
      - Map fields intelligently (e.g., 'goal' -> 'query', 'summary' -> 'research_context').
    - If Validation failed (REJECTED), you should retry the Drafting step (pass the critique).
    - If Validation succeeded (APPROVED), you should trigger the Fulfillment event.
      - IMPORTANT: The 'result' field in the fulfillment payload MUST be the actual 'draft_text' from the draft step. Do not summarize it.
    
    Decide the next logical step. Return JSON with:
    - "action": "publish" (do not use "wait" unless absolutely necessary)
    - "event": The EXACT name of the event to publish.
    - "payload": The JSON payload for the event, matching its schema.
    - "reasoning": Why you chose this action.
    """
    
    try:
        response = completion(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"LLM Error: {e}")
        return {"action": "wait"}

async def execute_decision(decision: dict, available_events: list, context: PlatformContext):
    """Helper to execute the LLM's decision generically."""
    print(f"   🤖 LLM Suggested Action: {decision.get('action')} -> {decision.get('event')}")
    print(f"   🤖 Reasoning: {decision.get('reasoning')}")
    
    if decision.get("action") == "publish":
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
            await context.bus.publish(
                event_type=event_name,
                topic=target_event["topic"],
                data=payload
            )
        else:
            print(f"   ⚠️  Error: LLM selected unknown event '{event_name}'")

@planner.on_event(GOAL_EVENT.event_name)
async def handle_goal(event: dict, context: PlatformContext):
    print(f"\n📋 Planner received GOAL: {event.get('id')}")
    data = event.get("data", {})
    
    # Archive previous turn
    if workflow_state.get("current"):
        workflow_state["history"].append(workflow_state["current"])
    
    workflow_state['current'] = {'goal': data, 'action_history': []}
    
    # Dynamic Discovery
    async with EventToolkit(context.registry.base_url) as toolkit:
        events = await toolkit.discover_actionable_events(topic="action-requests")
        print(f"   🔍 Discovered {len(events)} actionable events: {[e['name'] for e in events]}")
        
        decision = await get_next_action("Goal received. Need to research.", workflow_state, events)
        await execute_decision(decision, events, context)

@planner.on_event(RESEARCH_RESULT_EVENT.event_name)
async def handle_research_result(event: dict, context: PlatformContext):
    print(f"\n📋 Planner received RESEARCH: {event.get('id')}")
    data = event.get("data", {})
    if 'current' not in workflow_state: workflow_state['current'] = {}
    workflow_state['current']['research'] = data
    
    async with EventToolkit(context.registry.base_url) as toolkit:
        events = await toolkit.discover_actionable_events(topic="action-requests")
        print(f"   🔍 Discovered {len(events)} actionable events: {[e['name'] for e in events]}")
        
        decision = await get_next_action("Research received. Need to draft response.", workflow_state, events)
        await execute_decision(decision, events, context)

@planner.on_event(ADVICE_RESULT_EVENT.event_name)
async def handle_advice_result(event: dict, context: PlatformContext):
    print(f"\n📋 Planner received DRAFT: {event.get('id')}")
    data = event.get("data", {})
    if 'current' not in workflow_state: workflow_state['current'] = {}
    workflow_state['current']['draft'] = data
    
    # Clear stale validation result to prevent loop
    if 'validation' in workflow_state['current']:
        del workflow_state['current']['validation']
    
    async with EventToolkit(context.registry.base_url) as toolkit:
        events = await toolkit.discover_actionable_events(topic="action-requests")
        print(f"   🔍 Discovered {len(events)} actionable events: {[e['name'] for e in events]}")
        
        decision = await get_next_action("Draft received. Need to validate it.", workflow_state, events)
        await execute_decision(decision, events, context)

@planner.on_event(VALIDATION_RESULT_EVENT.event_name)
async def handle_validation_result(event: dict, context: PlatformContext):
    print(f"\n📋 Planner received VALIDATION: {event.get('id')}")
    data = event.get("data", {})
    if 'current' not in workflow_state: workflow_state['current'] = {}
    workflow_state['current']['validation'] = data  # Store validation result
    is_valid = data.get("is_valid")
    critique = data.get("critique")
    
    async with EventToolkit(context.registry.base_url) as toolkit:
        events = await toolkit.discover_actionable_events()
        
        # Hack: Ensure FULFILLED_EVENT is available
        has_fulfilled = any(e['name'] == FULFILLED_EVENT.event_name for e in events)
        if not has_fulfilled:
             events.append({
                 "name": FULFILLED_EVENT.event_name,
                 "description": FULFILLED_EVENT.description,
                 "topic": FULFILLED_EVENT.topic,
                 "payload_fields": {"result": {"type": "string"}, "source": {"type": "string"}}
             })
        
        print(f"   🔍 Discovered {len(events)} actionable events: {[e['name'] for e in events]}")
        
        ctx_str = f"Validation received. Status: {'APPROVED' if is_valid else 'REJECTED'}. Critique: {critique}"
        decision = await get_next_action(ctx_str, workflow_state, events)
        await execute_decision(decision, events, context)
        
        # Handle manual fallback logic if LLM fails to construct payload or for specific overrides
        # Note: execute_decision handles the publishing if LLM returns a valid payload.
        # But here we have specific logic for FULFILLED and RETRY that might need manual intervention
        # if the LLM didn't construct the payload correctly or if we want to enforce it.
        # However, the new get_next_action prompt asks LLM to construct payload.
        # So we should trust execute_decision mostly.
        # BUT, the original code had a block here to manually publish if decision matched.
        # Let's keep it but update it to use new state structure, OR rely on LLM.
        # Given the prompt instructions, LLM *should* construct the payload.
        # But let's add a safety check: if LLM returned action='publish' but no payload, we might need to fill it.
        # For now, let's assume LLM does its job as per prompt.
        # Wait, the original code had:
        # if decision.get("event") == FULFILLED_EVENT.event_name: ... await context.bus.publish(...)
        # AND execute_decision ALSO publishes.
        # We should NOT double publish.
        # The previous code I wrote:
        # decision = await get_next_action(...)
        # await execute_decision(decision, events, context)
        #
        # So I should REMOVE the manual publishing block below execute_decision to avoid duplicates.
        # The LLM is now responsible for payload construction.



if __name__ == "__main__":
    planner.run()
