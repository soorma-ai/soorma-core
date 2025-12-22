import asyncio
import sys
from soorma import EventClient
from events import GOAL_EVENT, FULFILLED_EVENT

async def interactive_cli():
    """Run an interactive CLI for the Generic Agent System."""
    
    client = EventClient(agent_id="client", source="client")
    
    # Shared event to signal completion of a request
    request_completed = asyncio.Event()
    
    @client.on_event(FULFILLED_EVENT.event_name)
    async def on_fulfilled(event):
        data = event.get("data", {})
        print(f"\n🎉 CLIENT RECEIVED FINAL RESULT:")
        print(f"   Result: {data.get('result')}")
        print(f"   Source: {data.get('source')}")
        request_completed.set()

    print("\n" + "="*60)
    print("  Generic Research & Advice Agent - DisCo Example")
    print("="*60)
    
    # Connect once
    await client.connect(topics=[FULFILLED_EVENT.topic])
    
    try:
        while True:
            print("\n" + "-"*40)
            try:
                goal = input("Enter your goal or question (or 'exit' to quit): ").strip()
            except EOFError:
                break

            if goal.lower() in ('exit', 'quit'):
                break
            
            if not goal:
                continue
            
            query = {
                "goal": goal
            }
            
            print(f"\n👤 User Goal: {query['goal']}")
            
            # Reset event for this new request
            request_completed.clear()
            
            # Publish goal
            await client.publish(
                event_type=GOAL_EVENT.event_name,
                topic=GOAL_EVENT.topic,
                data=query
            )
            
            print("   Waiting for result...")
            
            # Wait for result
            try:
                await asyncio.wait_for(request_completed.wait(), timeout=60.0)
            except asyncio.TimeoutError:
                print("\n⚠️  Timeout waiting for result")
                
    finally:
        await client.disconnect()
        print("\nGoodbye!")

if __name__ == "__main__":
    try:
        asyncio.run(interactive_cli())
    except KeyboardInterrupt:
        pass
