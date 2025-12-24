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

# Constants
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000000"  # Hard-coded user ID for single-tenant mode

"""
Memory Usage Pattern in Planner:

1. SEMANTIC MEMORY (store_knowledge):
   - Stores facts/findings from worker results for future reuse
   - Enables cross-plan knowledge retrieval
   - Example: Store research summaries so future plans can find them

2. WORKING MEMORY (store/retrieve with plan_id):
   - Stores workflow_state scoped to current plan_id
   - Contains: action_history, research data, draft data, validation results
   - Only accessible by this plan - deleted after completion
   - Critical for maintaining plan execution state

3. EPISODIC MEMORY (log_interaction):
   - Logs planner decisions and reasoning for audit trail
   - Shows "what decisions did the planner make"
   - Scoped to user_id + agent_id for conversation history
"""

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


async def get_next_action(trigger_context: str, workflow_data: dict, available_events: list, context: PlatformContext) -> Dict[str, Any]:
    """
    Asks LLM to decide the next action based on:
    - The trigger context (what just happened)
    - Current workflow state (accumulated data from memory)
    - Available events discovered from registry (with their metadata)
    
    The LLM reasons autonomously based on event descriptions and schemas.
    """
    current_state = workflow_data
    action_history = current_state.get("action_history", [])
    
    # Circuit Breaker - prevent infinite loops per goal
    # Use current_goal_actions for multi-turn support (resets per new goal)
    current_goal_actions = current_state.get("current_goal_actions", 0)
    if current_goal_actions >= MAX_TOTAL_ACTIONS:
        print(f"   🔌 Circuit Breaker: Max actions ({MAX_TOTAL_ACTIONS}) reached for current goal. Forcing completion.")
        # Try to return best available result
        draft_text = current_state.get("draft", {}).get("draft_text")
        research_summary = current_state.get("research", {}).get("summary")
        previous_draft = current_state.get("previous_draft", {}).get("draft_text")
        result = draft_text or research_summary or previous_draft or "Process completed (max actions reached)."
        return {
            "action": "complete",
            "result": result,
            "reasoning": "Circuit breaker: maximum actions reached for current goal."
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
- Progress logically: gather information → process/draft it → validate/fact-check → deliver results
- IMPORTANT: If there is a validation/fact-checking event available, use it BEFORE completing - accuracy matters!
- Only mark as "complete" AFTER validation has passed, or if no validation event is available
- Do NOT repeat the same action if it won't provide new information

## PAYLOAD CONSTRUCTION
When constructing payloads, carefully examine each event's payload_schema:
- The "required" array lists which fields are mandatory
- The "properties" object describes each field and its purpose
- Extract values from the workflow_state to populate the payload
- Ensure ALL required fields are included in your payload
- For optional fields, read their descriptions carefully - they often explain when to include them

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


async def execute_decision(decision: dict, available_events: list, context: PlatformContext, plan_id: str):
    """Execute the LLM's decision - either publish an event or complete the workflow."""
    action = decision.get("action")
    reasoning = decision.get("reasoning", "No reasoning provided")
    
    print(f"   🤖 LLM Decision: {action}")
    print(f"   🤖 Reasoning: {reasoning}")
    
    # Log decision to episodic memory
    await context.memory.log_interaction(
        agent_id="agent-orchestrator",
        user_id=DEFAULT_USER_ID,
        role="assistant",
        content=f"Decision: {action}. Reasoning: {reasoning}",
        metadata={"plan_id": plan_id, "action": action}
    )
    
    if action == "publish":
        event_name = decision.get("event")
        payload = decision.get("payload", {})
        
        # Inject plan_id into payload for correlation tracking
        # This allows result handlers to correlate responses back to the original workflow
        payload['plan_id'] = plan_id
        
        # Track action in working memory
        workflow_state = await context.memory.retrieve("workflow_state", plan_id=plan_id) or {}
        action_history = workflow_state.get('action_history', [])
        action_history.append(event_name)
        workflow_state['action_history'] = action_history
        
        # Increment current goal action counter for circuit breaker
        workflow_state['current_goal_actions'] = workflow_state.get('current_goal_actions', 0) + 1
        
        await context.memory.store("workflow_state", workflow_state, plan_id=plan_id)
        
        # Find the event definition to get the topic
        target_event = next((e for e in available_events if e["name"] == event_name), None)
        
        if target_event:
            print(f"   📤 Publishing: {event_name} (plan_id: {plan_id})")
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
        
        # Always prefer actual content from working memory over LLM's result field
        # The LLM's "result" might be reasoning/explanation, not the actual content
        workflow_state = await context.memory.retrieve("workflow_state", plan_id=plan_id) or {}
        draft_text = workflow_state.get("draft", {}).get("draft_text", "")
        research_summary = workflow_state.get("research", {}).get("summary", "")
        
        # Use actual content if available
        if draft_text:
            print(f"   📄 Using draft_text from workflow state")
            result = draft_text
        elif research_summary:
            print(f"   📄 Using research summary from workflow state")
            result = research_summary
        # Otherwise fall back to LLM's result field (empty state)
        
        print(f"   ✅ Workflow COMPLETE")
        print(f"   📝 Result: {result[:200]}...")  # Truncate for display
        
        # Log completion to episodic memory
        await context.memory.log_interaction(
            agent_id="agent-orchestrator",
            user_id=DEFAULT_USER_ID,
            role="assistant",
            content=f"Workflow completed. Result: {result[:200]}...",
            metadata={"plan_id": plan_id, "status": "completed"}
        )
        
        # Publish the fulfillment event
        await context.bus.publish(
            event_type=FULFILLED_EVENT.event_name,
            topic=FULFILLED_EVENT.topic,
            data={"result": result, "source": "Autonomous Orchestrator", "plan_id": plan_id}
        )
        
        # Archive completed workflow in working memory
        workflow_state["final_result"] = result
        workflow_state["status"] = "completed"
        await context.memory.store("workflow_state", workflow_state, plan_id=plan_id)
            
    elif action == "wait":
        print(f"   ⏳ Waiting... ({reasoning})")
    else:
        print(f"   ⚠️  Unknown action: {action}")


async def discover_and_decide(trigger_context: str, context: PlatformContext, plan_id: str):
    """Discover available events and let LLM decide next action."""
    # Retrieve workflow state from working memory
    workflow_state = await context.memory.retrieve("workflow_state", plan_id=plan_id) or {"action_history": []}
    
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
        
        decision = await get_next_action(trigger_context, workflow_state, events, context)
        await execute_decision(decision, events, context, plan_id)


@planner.on_event(GOAL_EVENT.event_name)
async def handle_goal(event: dict, context: PlatformContext):
    """Handle new goal - can be part of multi-turn conversation."""
    print(f"\n📋 Planner received GOAL: {event.get('id')}")
    data = event.get("data", {})
    
    # Extract plan_id from goal payload (client provides for multi-turn conversations)
    # Fallback to event ID for backward compatibility
    plan_id = data.get('plan_id', event.get('id'))
    print(f"   Using plan_id: {plan_id}")
    
    # Log goal to episodic memory
    await context.memory.log_interaction(
        agent_id="agent-orchestrator",
        user_id=DEFAULT_USER_ID,
        role="user",
        content=data.get('goal', 'Unknown goal'),
        metadata={"plan_id": plan_id, "event_type": "goal"}
    )
    
    # Retrieve existing workflow state (for multi-turn) or initialize new one
    workflow_state = await context.memory.retrieve("workflow_state", plan_id=plan_id)
    
    if workflow_state:
        print(f"   📚 Continuing existing plan with {len(workflow_state.get('action_history', []))} previous actions")
        # Add new goal to history
        workflow_state.setdefault('goals', []).append(data.get('goal'))
        
        # Reset action counter for new goal (circuit breaker)
        workflow_state['current_goal_actions'] = 0
        
        # Clear draft and validation state for the new goal
        # Keep research in context (may be relevant) but mark it as from previous goal
        if 'draft' in workflow_state:
            workflow_state['previous_draft'] = workflow_state.pop('draft')
        if 'validation' in workflow_state:
            del workflow_state['validation']
        if 'research' in workflow_state:
            workflow_state['previous_research'] = workflow_state.pop('research')
    else:
        print(f"   🆕 Starting new plan")
        # Initialize fresh workflow state
        workflow_state = {
            'goals': [data.get('goal')],
            'action_history': [],
            'current_goal_actions': 0,  # Circuit breaker per goal
            'status': 'in_progress'
        }
    
    # Store the current goal
    workflow_state['current_goal'] = data.get('goal')
    await context.memory.store("workflow_state", workflow_state, plan_id=plan_id)
    
    # Build trigger context based on whether this is a continuation
    is_continuation = len(workflow_state.get('goals', [])) > 1
    if is_continuation:
        trigger_context = f"""USER INPUT in multi-turn conversation: "{data.get('goal', 'Unknown goal')}"

Previous research/drafts are available in the workflow state as 'previous_research' and 'previous_draft'.

Analyze the user's input to determine if this is:
- NEW QUESTION: Requires new research or information
- FEEDBACK/CORRECTION: User is critiquing or correcting the previous response (treat as validation feedback and request revised draft with user's feedback as critique)
- FOLLOW-UP: Related to previous topic but needs additional context

Choose the appropriate action based on your analysis of the user's intent."""
    else:
        trigger_context = f"New goal received from user: '{data.get('goal', 'Unknown goal')}'. This is the starting point - analyze available events to determine how to fulfill this goal."
    
    await discover_and_decide(trigger_context, context, plan_id)


@planner.on_event(RESEARCH_RESULT_EVENT.event_name)
async def handle_research_result(event: dict, context: PlatformContext):
    """Handle research completion - store results and decide next step."""
    print(f"\n📋 Planner received RESEARCH RESULT: {event.get('id')}")
    data = event.get("data", {})
    
    # Extract plan_id - should be propagated from original request
    plan_id = data.get('plan_id', data.get('original_request_id', event.get('id')))
    
    # 1. SEMANTIC MEMORY: Store research summary for future cross-plan reuse
    #    Any future workflow can find this via semantic search
    research_summary = data.get('summary', '')
    if research_summary:
        await context.memory.store_knowledge(
            content=research_summary,
            metadata={"event_id": event.get('id'), "plan_id": plan_id, "source_url": data.get('source_url')}
        )
    
    # 2. WORKING MEMORY: Store full structured data in plan-scoped workflow state
    #    Only this plan's agents can access this - deleted after plan completes
    workflow_state = await context.memory.retrieve("workflow_state", plan_id=plan_id) or {"action_history": []}
    workflow_state['research'] = data  # Full research data with all fields
    await context.memory.store("workflow_state", workflow_state, plan_id=plan_id)
    
    summary_preview = data.get('summary', '')[:100]
    trigger_context = f"Research completed. Summary: '{summary_preview}...'. Now have research data available. Determine next step to progress toward the goal."
    await discover_and_decide(trigger_context, context, plan_id)


@planner.on_event(ADVICE_RESULT_EVENT.event_name)
async def handle_advice_result(event: dict, context: PlatformContext):
    """Handle draft completion - store draft and decide next step."""
    print(f"\n📋 Planner received DRAFT RESULT: {event.get('id')}")
    data = event.get("data", {})
    
    # Extract plan_id - should be propagated from original request
    plan_id = data.get('plan_id', data.get('original_request_id', event.get('id')))
    
    # Update workflow state in working memory
    workflow_state = await context.memory.retrieve("workflow_state", plan_id=plan_id) or {"action_history": []}
    workflow_state['draft'] = data
    
    # Clear any previous validation when new draft arrives
    if 'validation' in workflow_state:
        del workflow_state['validation']
    
    await context.memory.store("workflow_state", workflow_state, plan_id=plan_id)
    
    draft_preview = data.get('draft_text', '')[:100]
    trigger_context = f"""Draft completed. Preview: '{draft_preview}...'. 

A draft response is now available in the workflow state. 

IMPORTANT: Before delivering content to users, it should be validated/fact-checked against the source research to ensure accuracy. Look for a validation event in the discovered events that can verify the draft against the research data."""
    await discover_and_decide(trigger_context, context, plan_id)


@planner.on_event(VALIDATION_RESULT_EVENT.event_name)
async def handle_validation_result(event: dict, context: PlatformContext):
    """Handle validation result - decide whether to retry or complete."""
    print(f"\n📋 Planner received VALIDATION RESULT: {event.get('id')}")
    data = event.get("data", {})
    
    # Extract plan_id - should be propagated from original request
    plan_id = data.get('plan_id', data.get('original_request_id', event.get('id')))
    
    # Update workflow state in working memory
    workflow_state = await context.memory.retrieve("workflow_state", plan_id=plan_id) or {"action_history": []}
    workflow_state['validation'] = data
    await context.memory.store("workflow_state", workflow_state, plan_id=plan_id)
    
    is_valid = data.get("is_valid", False)
    critique = data.get("critique", "No critique provided")
    
    # Log validation result to episodic memory
    await context.memory.log_interaction(
        agent_id="agent-orchestrator",
        user_id=DEFAULT_USER_ID,
        role="system",
        content=f"Validation {'PASSED' if is_valid else 'FAILED'}. Critique: {critique}",
        metadata={"plan_id": plan_id, "is_valid": is_valid}
    )
    
    if is_valid:
        trigger_context = f"Validation PASSED. The draft has been approved. Critique: '{critique}'. The goal can now be fulfilled with the validated draft."
    else:
        trigger_context = f"""Validation FAILED. The draft must be revised.

CRITIQUE FROM VALIDATOR: {critique}

REQUIRED ACTION: Request a NEW draft by publishing 'agent.draft.requested' with the following payload:
- user_request: (from workflow state)
- research_context: (from workflow state)  
- critique: "{critique}" (MUST include this so drafter knows what to fix)

DO NOT re-validate the same draft. DO NOT request more research. The drafter needs the critique to fix the issues."""
    
    await discover_and_decide(trigger_context, context, plan_id)


if __name__ == "__main__":
    planner.run()
