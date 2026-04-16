"""
Client for Choreography Example - Sends feedback analysis goal.

Demonstrates sending a request with response_event and waiting for the
orchestrated response from the planner.

Also demonstrates Tracker Service observability:
- Shows task execution timeline
- Displays performance metrics
- Helps debug timeouts
"""

import asyncio
from uuid import uuid4
from typing import Optional
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soorma import EventClient
from soorma.tracker.client import TrackerServiceClient
from soorma_common.events import EventEnvelope, EventTopic

from examples.shared.auth import build_example_token_provider

EXAMPLE_NAME = "10-choreography-basic"


async def show_observability(plan_id: str, token_provider, tenant_id: str, user_id: str) -> None:
    """
    Query Tracker Service to show workflow observability.
    
    Demonstrates the value of Tracker Service for:
    - Debugging autonomous choreography
    - Understanding LLM orchestration decisions
    - Performance analysis
    
    Args:
        plan_id: Correlation ID (used as plan_id in choreography)
    """
    tracker = TrackerServiceClient(auth_token_provider=token_provider)
    
    print("\n" + "="*70)
    print("  📊 WORKFLOW OBSERVABILITY (Tracker Service)")
    print("="*70)
    
    try:
        # Get plan progress summary
        progress = await tracker.get_plan_progress(
            plan_id=plan_id,
            service_tenant_id=tenant_id,
            service_user_id=user_id,
        )
        
        if progress:
            print(f"\n📋 Plan Progress:")
            print(f"   Status: {progress.status}")
            print(f"   Tasks: {progress.completed_tasks}/{progress.task_count} completed")
            if progress.failed_tasks > 0:
                print(f"   Failed: {progress.failed_tasks}")
            print(f"   Started: {progress.started_at.strftime('%H:%M:%S')}")
            if progress.completed_at:
                duration = (progress.completed_at - progress.started_at).total_seconds()
                print(f"   Duration: {duration:.2f}s")
        
        # Get task execution history
        tasks = await tracker.get_plan_tasks(
            plan_id=plan_id,
            service_tenant_id=tenant_id,
            service_user_id=user_id,
        )
        
        if tasks:
            print(f"\n⚡ Task Execution Timeline:")
            for task in tasks:
                status_icon = "✓" if task.state == "completed" else "⏳" if task.state == "running" else "❌"
                duration_str = f"{task.duration_seconds:.2f}s" if task.duration_seconds else "running"
                print(f"   {status_icon} {task.event_type:<30} {duration_str:>8}")
        
        # Get event timeline
        timeline = await tracker.get_plan_timeline(
            plan_id=plan_id,
            service_tenant_id=tenant_id,
            service_user_id=user_id,
        )
        
        if timeline and timeline.events:
            print(f"\n🔄 Event Flow (trace_id: {timeline.trace_id[:12]}...):")
            for i, event in enumerate(timeline.events[:10], 1):  # Show first 10
                time_str = event.timestamp.strftime('%H:%M:%S.%f')[:-3]
                indent = "  " * (1 if event.parent_event_id else 0)
                print(f"   {i}. {time_str} {indent}{event.event_type}")
            
            if len(timeline.events) > 10:
                print(f"   ... and {len(timeline.events) - 10} more events")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n⚠️  Tracker Service unavailable: {e}")
        print("   (Tracker provides observability but is optional)")
        print("="*70)


async def main() -> None:
    """Send feedback analysis goal and wait for result."""
    token_provider = build_example_token_provider(EXAMPLE_NAME, __file__)
    await token_provider.get_token()
    tenant_id = await token_provider.get_platform_tenant_id()
    user_id = await token_provider.get_bootstrap_admin_principal_id()
    client = EventClient(
        agent_id="feedback-client",
        source="feedback-client",
        auth_token_provider=token_provider,
    )
    
    response_event = asyncio.Event()
    response_payload = {}
    correlation_id = str(uuid4())
    plan_id = correlation_id  # In choreography, correlation_id is used as plan_id

    @client.on_event("feedback.report.ready", topic=EventTopic.ACTION_RESULTS)
    async def handle_response(event: EventEnvelope) -> None:
        """Receive orchestrated report."""
        if event.correlation_id != correlation_id:
            return
        response_payload.update(event.data or {})
        response_event.set()

    await client.connect(topics=[EventTopic.ACTION_RESULTS])

    print("\n[client] Sending feedback analysis goal...")
    print(f"[client] Correlation ID: {correlation_id}")
    
    await client.publish(
        event_type="analyze.feedback",
        topic=EventTopic.ACTION_REQUESTS,
        response_event="feedback.report.ready",
        response_topic=EventTopic.ACTION_RESULTS,
        correlation_id=correlation_id,
        data={"product": "Soorma Hub", "sample_size": 3},
        tenant_id=tenant_id,
        user_id=user_id,
    )

    print("[client] Waiting for response (timeout: 30s)...")
    
    try:
        await asyncio.wait_for(response_event.wait(), timeout=30.0)
        
        print("\n[client] ✅ Received report:")
        print(response_payload.get("result", response_payload))
        
        # Show observability data on success
        await show_observability(plan_id, token_provider, tenant_id, user_id)
        
    except asyncio.TimeoutError:
        print("\n⚠️  Timeout waiting for response")
        print("   Make sure the Planner and Workers are running!")
        print("   Run: ./start.sh")
        
        # Show observability data on timeout (helps debug!)
        await show_observability(plan_id, token_provider, tenant_id, user_id)
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted\n")
