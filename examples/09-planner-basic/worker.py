"""
Mock Research Worker

Simple worker that responds to research tasks.
In a real system, this would call external APIs, databases, etc.
"""

import asyncio
from soorma import Worker
from soorma.context import PlatformContext
from soorma_common.events import EventEnvelope, EventTopic


# Create Worker agent
worker = Worker(
    name="research-worker",
    description="Performs research tasks",
    capabilities=["research"],
    events_consumed=["research.task"],
    events_produced=["research.complete"],
)


@worker.on_startup
async def startup():
    """Initialize worker on startup."""
    print("\n🔬 Research Worker Started")
    print("   Listening for: research.task\n")


@worker.on_shutdown
async def shutdown():
    """Cleanup on shutdown."""
    print("\n🛑 Research Worker Shutting Down")


@worker.on_event("research.task", topic=EventTopic.ACTION_REQUESTS)
async def handle_research_task(event: EventEnvelope, context: PlatformContext):
    """
    Handle research tasks.
    
    Receives:
    - query: Research topic
    - max_results: Maximum papers to find
    
    Returns:
    - summary: Brief summary
    - papers_found: Number of papers
    - papers: List of paper titles (mock data)
    """
    data = event.data or {}
    query = data.get("query", "unknown")
    max_results = data.get("max_results", 3)
    
    print(f"\n📥 Received: research.task")
    print(f"   Query: {query}")
    print(f"   Max results: {max_results}")
    print(f"   Correlation: {event.correlation_id}")
    
    # Simulate research work
    print(f"🔬 Researching: {query}")
    await asyncio.sleep(0.5)  # Simulate API call
    
    # Mock research results
    papers = [
        f"Paper 1: Introduction to {query}",
        f"Paper 2: Advanced {query} Techniques",
        f"Paper 3: {query} in Practice"
    ][:max_results]
    
    result_data = {
        "summary": f"Research complete: Found {len(papers)} papers on {query}",
        "papers_found": len(papers),
        "papers": papers,
        "query": query
    }
    
    print(f"✅ Complete: Found {len(papers)} papers on {query}")
    
    # Respond using the response_event from the request
    # This ensures the planner receives our result
    print(f"📤 Sending response...")
    print(f"   Event: {event.response_event}")
    print(f"   Correlation: {event.correlation_id}")
    print(f"   Topic: action-results")
    
    await context.bus.respond(
        event_type=event.response_event or "research.complete",
        data=result_data,
        correlation_id=event.correlation_id,
        tenant_id=event.tenant_id,
        user_id=event.user_id,
        session_id=event.session_id,
    )
    
    print(f"✅ Response published")


if __name__ == "__main__":
    # Run the worker
    worker.run()
