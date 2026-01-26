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
from soorma_common.events import EventEnvelope, EventTopic
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


@router.on_event("chat.message", topic=EventTopic.ACTION_REQUESTS)
async def route_message(event: EventEnvelope, context: PlatformContext):
    """Route incoming chat message based on classified intent."""
    data = event.data or {}
    message = data.get("message", "")
    session_id = data.get("session_id")
    
    tenant_id = event.tenant_id or "00000000-0000-0000-0000-000000000000"
    user_id = event.user_id or "00000000-0000-0000-0000-000000000001"
    
    print(f"\n📨 Incoming Message (session: {session_id})")
    print(f"   User: {message[:80]}...")
    
    # Get session state from working memory
    state = WorkflowState(
        context.memory,
        session_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    # Store CLIENT request info for later response (CRITICAL: router is orchestrator!)
    # This tells workers' handlers how to respond back to the CLIENT
    await state.set("client_correlation_id", event.correlation_id)
    await state.set("client_response_event", event.response_event or "chat.response")
    
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
        await context.bus.request(
            event_type="knowledge.store",
            response_event="knowledge.stored",
            data={
                "session_id": session_id,
                "message": message,
            },
            correlation_id=session_id,  # Use session_id so router handlers can retrieve client info
            tenant_id=tenant_id,
            user_id=user_id,
        )
    
    elif intent == "answer_question":
        print("   → Routing to RAG agent")
        await context.bus.request(
            event_type="question.answer",
            response_event="question.answered",
            data={
                "session_id": session_id,
                "question": message,
            },
            correlation_id=session_id,  # Use session_id so router handlers can retrieve client info
            tenant_id=tenant_id,
            user_id=user_id,
        )
    
    elif intent == "concierge":
        print("   → Routing to concierge")
        await context.bus.request(
            event_type="concierge.query",
            response_event="concierge.response",
            data={
                "session_id": session_id,
                "query": message,
            },
            correlation_id=session_id,  # Use session_id so router handlers can retrieve client info
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
        
        # Extract response event from request (caller specifies expected response)
        response_event_type = event.response_event or "chat.response"
        
        await context.bus.respond(
            event_type=response_event_type,
            data={
                "session_id": session_id,
                "response": response,
                "intent": intent
            },
            tenant_id=tenant_id,
            user_id=user_id,
            correlation_id=event.correlation_id,
        )


@router.on_event("knowledge.stored", topic=EventTopic.ACTION_RESULTS)
async def handle_knowledge_stored(event: EventEnvelope, context: PlatformContext):
    """Handle response from knowledge store worker - respond back to original client."""
    session_id = event.correlation_id  # This is the session_id we sent
    data = event.data or {}
    
    tenant_id = event.tenant_id or "00000000-0000-0000-0000-000000000000"
    user_id = event.user_id or "00000000-0000-0000-0000-000000000001"
    
    print(f"\n✓ Knowledge stored (session: {session_id})")
    
    # Retrieve client's response event from working memory
    state = WorkflowState(
        context.memory,
        session_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    client_correlation_id = await state.get("client_correlation_id")
    client_response_event = await state.get("client_response_event")
    
    # Log interaction
    message = data.get("message", "")
    await context.memory.log_interaction(
        agent_id="chatbot-router",
        role="assistant",
        content=f"Stored: {message}",
        user_id=user_id,
        metadata={"session_id": session_id}
    )
    
    # Respond to CLIENT using client's response event
    response = f"I've saved that information. I'll use it to help answer future questions."
    
    await context.bus.respond(
        event_type=client_response_event,
        data={
            "session_id": session_id,
            "response": response,
            "intent": "store_knowledge",
            "sources": {
                "knowledge_stored": True
            }
        },
        correlation_id=client_correlation_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )


@router.on_event("question.answered", topic=EventTopic.ACTION_RESULTS)
async def handle_question_answered(event: EventEnvelope, context: PlatformContext):
    """Handle response from RAG agent - respond back to original client."""
    session_id = event.correlation_id  # This is the session_id we sent
    data = event.data or {}
    
    tenant_id = event.tenant_id or "00000000-0000-0000-0000-000000000000"
    user_id = event.user_id or "00000000-0000-0000-0000-000000000001"
    
    print(f"\n✓ Question answered (session: {session_id})")
    
    # Retrieve client's response event from working memory
    state = WorkflowState(
        context.memory,
        session_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    client_correlation_id = await state.get("client_correlation_id")
    client_response_event = await state.get("client_response_event")
    
    # Log interaction
    answer = data.get("answer", "")
    await context.memory.log_interaction(
        agent_id="chatbot-router",
        role="assistant",
        content=answer,
        user_id=user_id,
        metadata={"session_id": session_id}
    )
    
    # Respond to CLIENT using client's response event
    await context.bus.respond(
        event_type=client_response_event,
        data={
            "session_id": session_id,
            "response": answer,
            "intent": "answer_question",
            "sources": {
                "history_matches": data.get("history_matches_count", 0),
                "knowledge_matches": data.get("knowledge_matches_count", 0)
            }
        },
        correlation_id=client_correlation_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )


@router.on_event("concierge.response", topic=EventTopic.ACTION_RESULTS)
async def handle_concierge_response(event: EventEnvelope, context: PlatformContext):
    """Handle response from concierge worker - respond back to original client."""
    session_id = event.correlation_id  # This is the session_id we sent
    data = event.data or {}
    
    tenant_id = event.tenant_id or "00000000-0000-0000-0000-000000000000"
    user_id = event.user_id or "00000000-0000-0000-0000-000000000001"
    
    print(f"\n✓ Concierge response (session: {session_id})")
    
    # Retrieve client's response event from working memory
    state = WorkflowState(
        context.memory,
        session_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    client_correlation_id = await state.get("client_correlation_id")
    client_response_event = await state.get("client_response_event")
    
    # Log interaction
    response_text = data.get("response", "")
    await context.memory.log_interaction(
        agent_id="chatbot-router",
        role="assistant",
        content=response_text,
        user_id=user_id,
        metadata={"session_id": session_id}
    )
    
    # Respond to CLIENT using client's response event
    await context.bus.respond(
        event_type=client_response_event,
        data={
            "session_id": session_id,
            "response": response_text,
            "intent": "concierge"
        },
        correlation_id=client_correlation_id,
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
