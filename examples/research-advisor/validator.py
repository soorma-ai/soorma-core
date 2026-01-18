import asyncio
import os
import json
from soorma import Worker
from soorma.context import PlatformContext
from soorma.registry.client import RegistryClient
from litellm import completion
from events import (
    VALIDATION_REQUEST_EVENT, VALIDATION_RESULT_EVENT,
    ValidationRequestPayload, ValidationResultPayload
)
from capabilities import VALIDATION_CAPABILITY
from llm_utils import get_llm_model, has_any_llm_key

# Constants
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000000"  # Hard-coded user ID for single-tenant mode

# Create the Validator Worker
validator = Worker(
    name="fact-checker",
    description="Validates content against source material",
    capabilities=[VALIDATION_CAPABILITY],
    events_consumed=[VALIDATION_REQUEST_EVENT],
    events_produced=[VALIDATION_RESULT_EVENT]
)

@validator.on_startup
async def startup():
    print(f"\n🚀 {validator.name} started! Ready to validate.")

@validator.on_shutdown
async def shutdown():
    print(f"\n🛑 {validator.name} shutting down. Goodbye!")

@validator.on_event(VALIDATION_REQUEST_EVENT.event_name, topic="action-requests")
async def handle_validation_request(event: dict, context: PlatformContext):
    """
    Validates if the draft is accurate based on the source text.
    """
    print(f"\n🔍 Validator received event: {event.get('type')}")
    
    data = event.get("data", {})
    try:
        request = ValidationRequestPayload(**data)
    except Exception as e:
        print(f"   ❌ Invalid payload: {e}")
        return
    
    draft_text = request.draft_text
    source_text = request.source_text
    
    # Log validation request to episodic memory
    await context.memory.log_interaction(
        agent_id="fact-checker",
        user_id=DEFAULT_USER_ID,
        role="user",
        content=f"Validation request - Draft: {draft_text[:100]}... Source: {source_text[:100]}...",
        metadata={"event_id": event.get('id')}
    )
    
    prompt = f"""
    You are a fact checker.
    Source Material: {source_text}
    Draft Content: {draft_text}
    
    Does the draft accurately reflect the source material? 
    Return JSON with "is_valid" (boolean) and "critique" (string).
    """
    
    print("   🧐 Auditing...")
    
    try:
        if has_any_llm_key():
            response = completion(
                model=get_llm_model(),
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = json.loads(response.choices[0].message.content)
            is_valid = content.get("is_valid", False)
            critique = content.get("critique", "No critique provided.")
        else:
            # Fallback for demo
            await asyncio.sleep(1)
            # Simple heuristic for demo
            if len(draft_text) > 20:
                is_valid = True
                critique = "Content looks substantial enough."
            else:
                is_valid = False
                critique = "Content is too short."
            
    except Exception as e:
        print(f"   ❌ LLM Error: {e}")
        is_valid = False
        critique = f"Validation failed due to error: {e}"

    # Log validation result to episodic memory
    status = "APPROVED" if is_valid else "REJECTED"
    await context.memory.log_interaction(
        agent_id="fact-checker",
        user_id=DEFAULT_USER_ID,
        role="assistant",
        content=f"Validation {status}: {critique}",
        metadata={"event_id": event.get('id'), "is_valid": is_valid}
    )

    result_data = {
        "is_valid": is_valid,
        "critique": critique,
        "original_request_id": event.get("id"),
        "plan_id": data.get("plan_id", event.get("id"))  # Propagate plan_id for correlation
    }
    
    print(f"   {status}: {critique}")
    
    await context.bus.publish(
        event_type=VALIDATION_RESULT_EVENT.event_name,
        topic=VALIDATION_RESULT_EVENT.topic,
        data=result_data
    )

if __name__ == "__main__":
    validator.run()
