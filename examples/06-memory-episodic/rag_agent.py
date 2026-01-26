"""
RAG (Retrieval Augmented Generation) agent that answers questions using context.

This agent:
1. Searches episodic memory (interaction history) to check if question was answered before
2. Searches semantic memory (knowledge base) for relevant information
3. Uses LLM to synthesize comprehensive answer from contexts
4. Logs the interaction
"""

import asyncio
import os
from typing import Any, Dict, List
from litellm import completion
from soorma import Worker
from soorma.context import PlatformContext
from soorma_common.events import EventEnvelope, EventTopic
from soorma.workflow import WorkflowState


rag_agent = Worker(
    name="chatbot-rag",
    description="Answers questions using context from episodic and semantic memory",
    capabilities=["question-answering", "retrieval", "context-synthesis"],
    events_consumed=["question.answer"],
    events_produced=["chat.response"],
)


async def synthesize_answer(
    question: str,
    history_context: List[Dict],
    knowledge_context: List[Dict]
) -> str:
    """
    Synthesize answer from retrieved context using LLM.
    """
    
    # Build context sections
    history_text = ""
    if history_context:
        print(f"     Found {len(history_context)} relevant past interactions")
        history_text = "\n\nPAST CONVERSATION CONTEXT:\n" + "\n".join([
            f"- {h.get('content', '')}" for h in history_context[:3]
        ])
    
    knowledge_text = ""
    if knowledge_context:
        print(f"     Found {len(knowledge_context)} relevant knowledge items")
        knowledge_text = "\n\nSTORED KNOWLEDGE:\n" + "\n".join([
            f"- {k.get('content', '')}" for k in knowledge_context[:3]
        ])
    
    # If no context at all
    if not history_context and not knowledge_context:
        return (
            "I don't have enough information to answer that question. "
            "Could you provide more context, or would you like me to remember "
            "some information about this topic?"
        )
    
    # Generate answer with LLM
    prompt = f"""You are a helpful assistant answering questions based on available context.

QUESTION:
{question}
{history_text}{knowledge_text}

INSTRUCTIONS:
1. Answer the question using the provided context
2. If both past conversation and stored knowledge are available, synthesize them naturally
3. If the context doesn't fully answer the question, say so
4. Be conversational and helpful
5. Don't make up information beyond what's in the context

Your answer:"""
    
    try:
        response = completion(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"     LLM answer generation failed: {e}")
        # Fallback to simple context combination
        if history_context:
            return f"Based on our previous conversation:\n\n{history_context[0].get('content', '')}"
        elif knowledge_context:
            return f"Based on stored knowledge:\n\n{knowledge_context[0].get('content', '')}"
        return "I encountered an error generating the answer."


@rag_agent.on_event("question.answer", topic=EventTopic.ACTION_REQUESTS)
async def answer_question(event: EventEnvelope, context: PlatformContext):
    """Answer question using dual context retrieval."""
    data = event.data or {}
    question = data.get("question", "")
    session_id = data.get("session_id")
    
    tenant_id = event.tenant_id or "00000000-0000-0000-0000-000000000000"
    user_id = event.user_id or "00000000-0000-0000-0000-000000000001"
    
    print(f"\n🤖 RAG Agent Processing Question")
    print(f"   Session: {session_id}")
    print(f"   Question: {question[:80]}...")
    
    # 1. Search episodic memory for past interactions
    print("   🔍 Searching interaction history...")
    history_results = await context.memory.search_interactions(
        agent_id="chatbot-rag",  # Search for past RAG responses
        query=question,
        user_id=user_id,
        limit=3
    )
    
    # Filter for assistant responses (answers)
    history_context = [
        r for r in history_results
        if r.get("role") == "assistant"
    ]
    
    # 2. Search semantic memory for relevant knowledge
    print("   📚 Searching knowledge base...")
    knowledge_results = await context.memory.search_knowledge(
        query=question,
        user_id=user_id,
        limit=3
    )
    
    # 3. Synthesize answer from contexts
    print("   💡 Synthesizing answer...")
    answer = await synthesize_answer(question, history_context, knowledge_results)
    
    # 4. Log assistant response to episodic memory
    # Note: User message already logged by router
    await context.memory.log_interaction(
        agent_id="chatbot-rag",
        role="assistant",
        content=answer,
        user_id=user_id,
        metadata={
            "session_id": session_id,
            "type": "answer",
            "sources": {
                "history": len(history_context),
                "knowledge": len(knowledge_results)
            }
        }
    )
    
    # 5. Update session state
    state = WorkflowState(
        context.memory,
        session_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    history = await state.get("history") or []
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    await state.set("history", history)
    
    # 6. Send response
    print(f"   ✓ Answer ready (sources: {len(history_context)} history + {len(knowledge_results)} knowledge)")
    
    # Extract response event from request (caller specifies expected response)
    response_event_type = event.response_event or "question.answered"
    
    await context.bus.respond(
        event_type=response_event_type,
        data={
            "session_id": session_id,
            "answer": answer,
            "history_matches_count": len(history_context),
            "knowledge_matches_count": len(knowledge_results)
        },
        correlation_id=event.correlation_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )


if __name__ == "__main__":
    print("🤖 RAG Agent (Retrieval Augmented Generation)")
    print("=" * 50)
    print("Answers questions using dual context:")
    print("  1. Episodic memory (interaction history)")
    print("  2. Semantic memory (knowledge base)")
    print("\nThis demonstrates:")
    print("  • Checking if question was answered before")
    print("  • Retrieving relevant stored knowledge")
    print("  • Combining multiple context sources")
    print("  • Logging interactions for future reference")
    print("\nListening for question.answer events...")
    print("=" * 50)
    
    rag_agent.run()
