import asyncio
import os
from soorma import Worker
from soorma.context import PlatformContext
from soorma_common.events import EventEnvelope, EventTopic
from ddgs import DDGS
from litellm import completion
from events import (
    RESEARCH_REQUEST_EVENT, RESEARCH_RESULT_EVENT,
    ResearchRequestPayload, ResearchResultPayload
)
from capabilities import RESEARCH_CAPABILITY
from llm_utils import get_llm_model, has_any_llm_key

# Constants
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000000"  # Hard-coded user ID for single-tenant mode

"""
Memory Usage Pattern in Web Researcher:

1. SEMANTIC MEMORY (search_knowledge → store_knowledge):
   - FIRST: Search existing knowledge to avoid redundant web searches
   - THRESHOLD: Only reuse cached knowledge with similarity score >= 0.7
     * Cosine similarity ranges from 0 (unrelated) to 1 (identical)
     * 0.7+ indicates strong semantic match, safe to reuse
     * Below 0.7, perform new search to get accurate results
   - THEN: Store NEW findings for future cross-plan reuse
   - Any agent, any user, any workflow can find via semantic search
   - Persistent beyond current workflow
   - Use case: "What research do we have on AI trends?" → Vector search retrieves cached research
   - Benefit: Avoid duplicate web searches, faster responses, cost savings

2. WORKING MEMORY (store/retrieve):
   - Stores structured research data scoped to current plan_id
   - Only accessible by agents working on this specific plan
   - Temporary - deleted after plan completes
   - Use case: Current workflow needs quick access to full research data

3. EPISODIC MEMORY (log_interaction):
   - Stores interaction history for audit trail and conversation context
   - Scoped to user_id + agent_id
   - Use case: "What did the researcher do last week?"
"""

# Create the Researcher Worker
researcher = Worker(
    name="web-researcher",
    description="Performs web research on any topic",
    capabilities=[RESEARCH_CAPABILITY],
    events_consumed=[RESEARCH_REQUEST_EVENT],
    events_produced=[RESEARCH_RESULT_EVENT]
)

@researcher.on_startup
async def startup():
    print(f"\n🚀 {researcher.name} started! Ready to research.")

@researcher.on_shutdown
async def shutdown():
    print(f"\n🛑 {researcher.name} shutting down. Goodbye!")

@researcher.on_event(RESEARCH_REQUEST_EVENT.event_name, topic=EventTopic.ACTION_REQUESTS)
async def handle_research_request(event: EventEnvelope, context: PlatformContext):
    """
    Handles research requests.
    """
    print(f"\n📚 Researcher received event: {event.type}")
    
    data = event.data or {}
    try:
        request = ResearchRequestPayload(**data)
    except Exception as e:
        print(f"   ❌ Invalid payload: {e}")
        return

    query_topic = request.query
    extra_context = request.context
    
    # Log research request to episodic memory
    await context.memory.log_interaction(
        agent_id="web-researcher",
        user_id=DEFAULT_USER_ID,
        role="user",
        content=f"Research request: {query_topic} (context: {extra_context})",
        metadata={"event_id": event.id}
    )
    
    # Check Semantic Memory first - maybe we already researched this!
    print(f"   🔍 Checking if we already have research on '{query_topic}'...")
    existing_knowledge = await context.memory.search_knowledge(
        query=query_topic,
        limit=3
    )
    
    # Define relevance threshold - only reuse if similarity score is high enough
    RELEVANCE_THRESHOLD = 0.7  # Cosine similarity: 0.7+ indicates strong match
    
    if existing_knowledge and len(existing_knowledge) > 0:
        best_match = existing_knowledge[0]
        score = best_match['score']
        
        if score >= RELEVANCE_THRESHOLD:
            # Found relevant existing research - reuse it!
            print(f"   ✅ Found relevant research (score: {score:.2f} >= {RELEVANCE_THRESHOLD})")
            print(f"      Source: {best_match['metadata'].get('source_url', 'Unknown')}")
            
            summary = best_match['content']
            source_url = best_match['metadata'].get('source_url', 'Previously researched')
        else:
            # Score too low - treat as no match
            print(f"   ⚠️  Found research but relevance too low (score: {score:.2f} < {RELEVANCE_THRESHOLD})")
            print(f"   ❌ Performing new web search...")
            existing_knowledge = None  # Clear so we proceed to search
    
    # If no relevant cached knowledge found, perform new web search
    if not existing_knowledge:
        print(f"   🔎 No relevant cached knowledge. Performing new web search...")
        
        # Check if we should use real search
        use_real_search = has_any_llm_key()
        
        if use_real_search:
            print(f"   🌐 Searching web for: {query_topic}...")
            try:
                # 1. Perform Web Search
                search_query = f"{query_topic}"
                if extra_context:
                    search_query += f" {extra_context}"
                    
                results = DDGS().text(search_query, max_results=3)
                
                search_context = "\n".join([f"Source: {r['href']}\nContent: {r['body']}" for r in results])
                
                # 2. Summarize with LLM
                prompt = f"""
                You are a research assistant.
                Topic: {query_topic}
                Context: {extra_context}
                
                Search Results:
                {search_context}
                
                Summarize the key findings relevant to the topic.
                """
                
                # Summarize with LLM
                response = completion(
                    model=get_llm_model(),
                    messages=[{"role": "user", "content": prompt}]
                )
                summary = response.choices[0].message.content
                source_url = results[0]['href'] if results else "No results found"
                
            except Exception as e:
                print(f"   ⚠️ Search failed: {e}")
                summary = "Could not perform search. Please try again."
                source_url = "Error"
        else:
            # Mock response
            print("   ⚠️ No API keys found. Using mock response.")
            summary = f"Mock research findings for {query_topic}. This is a simulated response."
            source_url = "http://mock-source.com"

    # Extract plan_id for proper memory scoping
    plan_id = data.get("plan_id", event.id)

    # Only store in Semantic Memory if this is NEW research (not from cache)
    if not existing_knowledge:
        # 1. SEMANTIC MEMORY: Store NEW knowledge for future cross-plan reuse
        #    Any agent can find this via semantic search (e.g., "research on AI trends")
        print(f"   💾 Storing new research in Semantic Memory for future reuse...")
        await context.memory.store_knowledge(
            content=summary,
            metadata={"query_topic": query_topic, "source_url": source_url, "plan_id": plan_id}
        )
    else:
        print(f"   ♻️  Reusing existing research from Semantic Memory (no new storage)")
    
    # 2. WORKING MEMORY: Always store structured data for current plan
    #    Only accessible by agents working on this specific plan_id
    await context.memory.store(
        key=f"research_{query_topic}",
        value={
            "summary": summary,
            "source_url": source_url,
            "query_topic": query_topic,
        },
        plan_id=plan_id
    )
    
    # 3. EPISODIC MEMORY: Log interaction for audit trail
    #    Shows "what did the researcher do" in conversation history
    await context.memory.log_interaction(
        agent_id="web-researcher",
        user_id=DEFAULT_USER_ID,
        role="assistant",
        content=f"Research completed for '{query_topic}': {summary[:200]}...",
        metadata={"event_id": event.id, "source_url": source_url}
    )

    # Publish Result
    result_payload = {
        "summary": summary,
        "source_url": source_url,
        "original_request_id": event.id,
        "plan_id": data.get("plan_id", event.id)  # Propagate plan_id for correlation
    }
    
    print(f"   📤 Publishing results for: {query_topic}")
    await context.bus.respond(
        event_type=RESEARCH_RESULT_EVENT.event_name,
        data=result_payload,
        correlation_id=event.correlation_id or event.id,
    )

if __name__ == "__main__":
    researcher.run()
