import asyncio
import os
from soorma import Worker
from soorma.context import PlatformContext
from ddgs import DDGS
from litellm import completion
from events import (
    RESEARCH_REQUEST_EVENT, RESEARCH_RESULT_EVENT,
    ResearchRequestPayload, ResearchResultPayload
)
from capabilities import RESEARCH_CAPABILITY

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

@researcher.on_event(RESEARCH_REQUEST_EVENT.event_name)
async def handle_research_request(event: dict, context: PlatformContext):
    """
    Handles research requests.
    """
    print(f"\n📚 Researcher received event: {event.get('type')}")
    
    data = event.get("data", {})
    try:
        request = ResearchRequestPayload(**data)
    except Exception as e:
        print(f"   ❌ Invalid payload: {e}")
        return

    query_topic = request.query
    extra_context = request.context
    
    # Check if we should use real search
    use_real_search = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    
    if use_real_search:
        print(f"   🔎 Searching web for: {query_topic}...")
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
                model="gpt-4.1-nano",
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

    # Publish Result
    result_payload = {
        "summary": summary,
        "source_url": source_url,
        "original_request_id": event.get("id")
    }
    
    print(f"   📤 Publishing results for: {query_topic}")
    await context.bus.publish(
        event_type=RESEARCH_RESULT_EVENT.event_name,
        topic=RESEARCH_RESULT_EVENT.topic,
        data=result_payload
    )

if __name__ == "__main__":
    researcher.run()
