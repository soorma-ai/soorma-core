import asyncio
import os
from soorma import Worker
from soorma.context import PlatformContext
from litellm import completion
from events import (
    ADVICE_REQUEST_EVENT, ADVICE_RESULT_EVENT,
    DraftRequestPayload, DraftResultPayload
)
from capabilities import ADVICE_CAPABILITY

# Create the Advisor Worker
advisor = Worker(
    name="content-drafter",
    description="Drafts responses based on research",
    capabilities=[ADVICE_CAPABILITY],
    events_consumed=[ADVICE_REQUEST_EVENT],
    events_produced=[ADVICE_RESULT_EVENT]
)

@advisor.on_startup
async def startup():
    print(f"\n🚀 {advisor.name} started! Ready to draft.")

@advisor.on_shutdown
async def shutdown():
    print(f"\n🛑 {advisor.name} shutting down. Goodbye!")

@advisor.on_event(ADVICE_REQUEST_EVENT.event_name)
async def handle_advice_request(event: dict, context: PlatformContext):
    """
    Drafts response based on user request and research context.
    """
    print(f"\n✍️  Drafter received event: {event.get('type')}")
    
    data = event.get("data", {})
    try:
        request = DraftRequestPayload(**data)
    except Exception as e:
        print(f"   ❌ Invalid payload: {e}")
        return
    
    user_request = request.user_request
    research_context = request.research_context
    critique = request.critique
    
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
        if os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"):
            response = completion(
                model="gpt-4.1-nano",
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

    result = DraftResultPayload(
        draft_text=draft_text,
        original_request_id=event.get("id")
    )
    
    print(f"   📝 Drafted: {draft_text[:50]}...")
    
    await context.bus.publish(
        event_type=ADVICE_RESULT_EVENT.event_name,
        topic=ADVICE_RESULT_EVENT.topic,
        data=result.model_dump()
    )

if __name__ == "__main__":
    advisor.run()
