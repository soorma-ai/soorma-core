"""
Router agent that classifies user intent and routes to appropriate handler.

This agent analyzes incoming messages and determines:
- Is this a fact/knowledge to store?
- Is this a question that needs answering?
- Is this a repeat question (already answered in session)?
- Is this general conversation about session history?

Uses LLM for accurate intent classification.
"""

import asyncio
import os
from typing import Any, Dict
from litellm import completion
from soorma import Worker
from soorma.context import PlatformContext
from soorma.workflow import WorkflowState


router = Worker(
    name="chatbot-router",
    description="Classifies user intent and routes to appropriate handler",
    capabilities=["intent-classification", "routing"],
    events_consumed=["chat.message"],
    events_produced=["knowledge.store", "question.answer", "concierge.query", "chat.response"],
)


async def classify_intent(message: str, session_history: list) -> Dict[str, Any]:
    """
    Classify user intent using LLM with conversation history for context.
    
    Returns:
        dict with 'intent' (store_knowledge, answer_question, concierge, general)
        and 'confidence' score
    """
    # Format recent history for context (last 5 exchanges)
    history_text = ""
    if session_history:
        recent = session_history[-10:]  # Last 10 messages (5 exchanges)
        history_lines = []
        for h in recent:
            role = h.get("role", "unknown").upper()
            content = h.get("content", "")[:100]  # Truncate long messages
            history_lines.append(f"{role}: {content}")
        history_text = "\n\nRECENT CONVERSATION:\n" + "\n".join(history_lines)
    
    prompt = f"""You are an intent classifier for a chatbot with memory capabilities.
{history_text}

CURRENT USER MESSAGE:
"{message}"

CLASSIFY THE INTENT:

1. **store_knowledge** - User wants to teach/store information
   Examples: "Remember that...", "I want you to know...", "Keep in mind..."

2. **answer_question** - User asks a question (about any topic)
   Examples: "What is...?", "How does...?", "Tell me about..."
   Note: Terse messages like "again", "repeat", "more" in context of previous question = answer_question

3. **concierge** - User asks about conversation history or session
   Examples: "What have we discussed?", "How many messages?", "What did I ask earlier?"

4. **general** - Greetings, acknowledgments, or unclear intent
   Examples: "Hi", "Thanks", "Okay"

IMPORTANT: Use the conversation history to resolve ambiguous or terse messages.

Return ONLY a JSON object:
{{
    "intent": "store_knowledge" or "answer_question" or "concierge" or "general",
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation"
}}"""
    
    try:
        response = completion(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        return {
            "intent": result.get("intent", "general"),
            "confidence": result.get("confidence", 0.5),
            "reasoning": result.get("reasoning", "")
        }
    except Exception as e:
        print(f"     LLM classification failed: {e}, using fallback")
        # Fallback to simple heuristics
        message_lower = message.lower().strip()
        if "remember" in message_lower or "keep in mind" in message_lower:
            return {"intent": "store_knowledge", "confidence": 0.7, "reasoning": "fallback"}
        elif message.endswith("?") or any(message_lower.startswith(q) for q in ["what", "how", "why", "when", "where"]):
            if any(kw in message_lower for kw in ["discussed", "said", "conversation", "messages"]):
                return {"intent": "concierge", "confidence": 0.7, "reasoning": "fallback"}
            return {"intent": "answer_question", "confidence": 0.7, "reasoning": "fallback"}
        return {"intent": "general", "confidence": 0.5, "reasoning": "fallback"}


@router.on_event("chat.message", topic="action-requests")
async def route_message(event: Dict[str, Any], context: PlatformContext):
    """Route incoming chat message based on classified intent."""
    data = event.get("data", {})
    message = data.get("message", "")
    session_id = data.get("session_id")
    
    tenant_id = event.get("tenant_id", "00000000-0000-0000-0000-000000000000")
    user_id = event.get("user_id", "00000000-0000-0000-0000-000000000001")
    
    print(f"\n📨 Incoming Message (session: {session_id})")
    print(f"   User: {message[:80]}...")
    
    # Get session state from working memory
    state = WorkflowState(
        context.memory,
        session_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    # Retrieve session history for context
    history = await state.get("history") or []
    
    # If working memory is empty, try episodic memory (e.g., after restart)
    if not history:
        try:
            recent_interactions = await context.memory.get_recent_history(
                agent_id="chatbot-router",
                user_id=user_id,
                limit=10
            )
            # Filter by session if available in metadata
            session_interactions = [
                {"role": i.get("role"), "content": i.get("content")}
                for i in recent_interactions
                if i.get("metadata", {}).get("session_id") == session_id
            ]
            if session_interactions:
                history = session_interactions
        except Exception as e:
            print(f"   ⚠️  Could not fetch episodic history: {e}")
    
    # Classify intent with history context
    classification = await classify_intent(message, history)
    intent = classification["intent"]
    confidence = classification["confidence"]
    
    print(f"   Intent: {intent} (confidence: {confidence:.2f})")
    
    # Log interaction to episodic memory
    await context.memory.log_interaction(
        agent_id="chatbot-router",
        role="user",
        content=message,
        user_id=user_id,
        metadata={
            "session_id": session_id,
            "intent": intent,
            "confidence": confidence
        }
    )
    
    # Route based on intent
    if intent == "store_knowledge":
        print("   → Routing to knowledge storage")
        await context.bus.publish(
            event_type="knowledge.store",
            topic="action-requests",
            data={
                "session_id": session_id,
                "message": message,
                "original_event": event
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
    
    elif intent == "answer_question":
        print("   → Routing to RAG agent")
        await context.bus.publish(
            event_type="question.answer",
            topic="action-requests",
            data={
                "session_id": session_id,
                "question": message,
                "original_event": event
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
    
    elif intent == "concierge":
        print("   → Routing to concierge")
        await context.bus.publish(
            event_type="concierge.query",
            topic="action-requests",
            data={
                "session_id": session_id,
                "query": message,
                "original_event": event
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
    
    else:
        # General conversation - respond with acknowledgment
        response = "I understand. I'm here to help you with knowledge storage, answering questions, or reviewing our conversation history."
        
        await context.memory.log_interaction(
            agent_id="chatbot-router",
            role="assistant",
            content=response,
            user_id=user_id,
            metadata={"session_id": session_id}
        )
        
        await context.bus.publish(
            event_type="chat.response",
            topic="action-results",
            data={
                "session_id": session_id,
                "response": response,
                "intent": intent
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )


if __name__ == "__main__":
    print("🧭 Chatbot Router Agent")
    print("=" * 50)
    print("Classifies user intent and routes to appropriate handler:")
    print("  • store_knowledge → Knowledge storage")
    print("  • answer_question → RAG agent")
    print("  • concierge → Session history assistant")
    print("  • general → Simple acknowledgment")
    print("\nListening for chat.message events...")
    print("\nStart other agents:")
    print("  python rag_agent.py")
    print("  python concierge.py")
    print("  python knowledge_store.py")
    print("\nThen start the client:")
    print("  python client.py")
    print("=" * 50)
    
    router.run()
