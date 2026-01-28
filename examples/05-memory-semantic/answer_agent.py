"""
Answer Agent - RAG-powered Question Answering

This agent uses the RAG (Retrieval-Augmented Generation) pattern:
1. Retrieve relevant knowledge from semantic memory
2. Use LLM to generate a grounded, factual answer
3. If no knowledge found, admit uncertainty

Uses event-driven choreography pattern.
"""

import os
from typing import Any, Dict
from litellm import completion
from soorma import Worker
from soorma.context import PlatformContext
from soorma_common.events import EventEnvelope, EventTopic
from events import (
    ANSWER_QUESTION_EVENT,
    QUESTION_ANSWERED_EVENT,
    QuestionAnsweredPayload,
)


def _build_knowledge_context(knowledge_results: list) -> tuple[list[dict], str]:
    """
    Build structured context from knowledge search results.
    
    Returns:
        Tuple of (knowledge_list, context_text) for LLM prompt
    """
    knowledge_list = [
        {
            "content": k["content"],
            "score": k.get("score", 0),
            "metadata": k.get("metadata", {})
        }
        for k in knowledge_results
    ]
    
    context_text = "\n\n".join([
        f"[Source {i+1}] {k['content']}"
        for i, k in enumerate(knowledge_results)
    ])
    
    return knowledge_list, context_text


async def _generate_grounded_answer(question: str, context_text: str) -> str:
    """
    Generate a grounded answer using LLM based on provided knowledge context.
    
    Args:
        question: The user's question
        context_text: Formatted knowledge context with sources
    
    Returns:
        Generated answer string
    
    Raises:
        Exception: If LLM call fails
    """
    prompt = f"""You are a helpful assistant that answers questions based ONLY on the provided knowledge.

KNOWLEDGE BASE:
{context_text}

QUESTION: {question}

INSTRUCTIONS:
1. Answer the question using ONLY the information from the knowledge base above
2. Provide a clear, natural, and complete answer (not just fragments)
3. If the knowledge base doesn't contain enough information to fully answer the question, say so
4. Be concise but informative
5. Do not make up or infer information beyond what's explicitly stated in the knowledge

Your answer:"""
    
    response = completion(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,  # Lower temperature for more factual answers
    )
    
    return response.choices[0].message.content


async def _send_response(event: EventEnvelope, context: PlatformContext, payload: QuestionAnsweredPayload):
    """Send response event with the answer payload."""
    await context.bus.respond(
        event_type=QUESTION_ANSWERED_EVENT.event_name,
        data=payload.model_dump(),
        correlation_id=event.correlation_id,
        user_id=event.user_id,  # Propagate user_id
    )


# Create a Worker for answering questions
worker = Worker(
    name="answer-agent",
    description="Answers questions using RAG with semantic memory",
    capabilities=["question-answering", "rag"],
    events_consumed=[ANSWER_QUESTION_EVENT],
    events_produced=[QUESTION_ANSWERED_EVENT],
)


@worker.on_event("question.ask", topic=EventTopic.ACTION_REQUESTS)
async def answer_question(event: EventEnvelope, context: PlatformContext):
    """
    Answer a question using RAG pattern with LLM.
    
    Steps:
    1. Retrieve relevant knowledge from semantic memory
    2. Use LLM to synthesize a grounded answer
    3. If no knowledge, admit we don't know
    """
    data = event.data or {}
    question = data.get("question", "")
    user_id = event.user_id  # User ID from event envelope
    
    print(f"\n❓ Question (user: {user_id}): {question}")
    
    # Step 1: Retrieve relevant knowledge from semantic memory
    print("🔍 Searching semantic memory...")
    knowledge_results = await context.memory.search_knowledge(
        query=question,
        user_id=user_id,
        limit=5
    )
    
    # No knowledge found - admit we don't know
    if not knowledge_results:
        print("   ⚠️  No relevant knowledge found\n")
        
        payload = QuestionAnsweredPayload(
            question=question,
            answer="I don't have enough knowledge to answer that question. You can teach me by providing relevant information first.",
            knowledge_used=[],
            has_knowledge=False
        )
        await _send_response(event, context, payload)
        return
    
    # Step 2: Build context from retrieved knowledge
    knowledge_list, context_text = _build_knowledge_context(knowledge_results)
    print(f"   ✓ Found {len(knowledge_results)} relevant knowledge fragments")
    print(f"   Top relevance score: {knowledge_results[0].get('score', 0):.3f}\n")
    
    # Step 3: Generate grounded answer with LLM
    print("🤖 Generating answer with LLM...")
    
    try:
        answer = await _generate_grounded_answer(question, context_text)
        print(f"   ✓ Answer generated\n")
        print(f"💡 Answer: {answer}\n")
        
        payload = QuestionAnsweredPayload(
            question=question,
            answer=answer,
            knowledge_used=knowledge_list,
            has_knowledge=True
        )
        
    except Exception as e:
        print(f"   ❌ Error generating answer: {e}\n")
        
        # Fallback to simple extraction if LLM fails
        payload = QuestionAnsweredPayload(
            question=question,
            answer=f"I found relevant information but encountered an error generating a complete answer. Here's what I know:\n\n{context_text}",
            knowledge_used=knowledge_list,
            has_knowledge=True
        )
    
    await _send_response(event, context, payload)


if __name__ == "__main__":
    print("🤖 Answer Agent starting...")
    print("Listening for question.ask events on action-requests topic")
    print("\nRequires:")
    print("  - OPENAI_API_KEY environment variable")
    print("  - Knowledge stored via knowledge.store events")
    print()
    
    worker.run()
