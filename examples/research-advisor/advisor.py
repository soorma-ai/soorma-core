import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soorma import Worker
from soorma.context import PlatformContext
from soorma_common.events import EventEnvelope, EventTopic
from litellm import completion
from events import (
    ADVICE_REQUEST_EVENT, ADVICE_RESULT_EVENT,
    DraftRequestPayload, DraftResultPayload
)
from capabilities import ADVICE_CAPABILITY
from llm_utils import get_llm_model, has_any_llm_key
from examples.shared.auth import build_example_token_provider

EXAMPLE_NAME = "research-advisor"
EXAMPLE_TOKEN_PROVIDER = build_example_token_provider(EXAMPLE_NAME, __file__)

# Create the Advisor Worker
advisor = Worker(
    name="content-drafter",
    description="Drafts responses based on research",
    capabilities=[ADVICE_CAPABILITY],
    events_consumed=[ADVICE_REQUEST_EVENT],
    events_produced=[ADVICE_RESULT_EVENT],
    auth_token_provider=EXAMPLE_TOKEN_PROVIDER,
)

@advisor.on_startup
async def startup():
    print(f"\n🚀 {advisor.name} started! Ready to draft.")

@advisor.on_shutdown
async def shutdown():
    print(f"\n🛑 {advisor.name} shutting down. Goodbye!")

@advisor.on_event(ADVICE_REQUEST_EVENT.event_name, topic=EventTopic.ACTION_REQUESTS)
async def handle_advice_request(event: EventEnvelope, context: PlatformContext):
    """
    Drafts response based on user request and research context.
    """
    print(f"\n✍️  Drafter received event: {event.type}")
    
    data = event.data or {}
    try:
        request = DraftRequestPayload(**data)
    except Exception as e:
        print(f"   ❌ Invalid payload: {e}")
        return
    
    user_request = request.user_request
    research_context = request.research_context
    critique = request.critique
    
    # Log drafting request to episodic memory
    await context.memory.log_interaction(
        agent_id="content-drafter",
        user_id=event.user_id,
        role="user",
        content=f"Draft request for: {user_request} (context: {research_context[:100]}...)",
        metadata={"event_id": event.id, "has_critique": bool(critique)}
    )
    
    prompt = f"""
    You are a helpful assistant.
    User Request: {user_request}
    Research Context: {research_context}
    """
    
    if critique:
        prompt += f"\n\nPrevious Draft Critique: {critique}\nPlease improve the draft based on this critique."
    
    prompt += "\nDraft a helpful, accurate response to the user based on the research."
    
    print("   🤔 Thinking...")
    
    try:
        if has_any_llm_key():
            response = completion(
                model=get_llm_model(),
                messages=[{"role": "user", "content": prompt}]
            )
            draft_text = response.choices[0].message.content
        else:
            # Fallback for demo without API keys
            await asyncio.sleep(1)
            draft_text = (
                f"Based on the research ({research_context[:30]}...), here is the answer. "
                f"Regarding '{user_request}', the findings suggest: {research_context}. "
            )
            if critique:
                draft_text += f" (Revised based on: {critique})"
            
    except Exception as e:
        print(f"   ❌ LLM Error: {e}")
        draft_text = "Error generating draft."

    # Log drafted content to episodic memory
    await context.memory.log_interaction(
        agent_id="content-drafter",
        user_id=event.user_id,
        role="assistant",
        content=f"Draft created: {draft_text[:200]}...",
        metadata={"event_id": event.id, "draft_length": len(draft_text)}
    )

    result_data = {
        "draft_text": draft_text,
        "original_request_id": event.id,
        "plan_id": data.get("plan_id", event.id)  # Propagate plan_id for correlation
    }
    
    print(f"   📝 Drafted: {draft_text[:50]}...")
    
    await context.bus.respond(
        event_type=ADVICE_RESULT_EVENT.event_name,
        data=result_data,
        correlation_id=event.correlation_id or event.id,
    )

if __name__ == "__main__":
    advisor.run()
