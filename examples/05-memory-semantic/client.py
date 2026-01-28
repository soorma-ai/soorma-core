"""
Client for Knowledge Management System

Unified client that can:
1. Store knowledge (teach the system)
2. Ask questions (query stored knowledge)

The router agent will automatically detect the intent and route accordingly.

Usage:
    # Interactive mode
    python client.py
    
    # Single request mode
    python client.py "Python was created by Guido van Rossum"
    python client.py "Who created Python?"
    
    # Specify user ID (default: 00000000-0000-0000-0000-000000000001)
    USER_ID=00000000-0000-0000-0000-000000000002 python client.py "Tell me about Python"
"""

import asyncio
import os
import sys
from uuid import uuid4
from soorma import EventClient
from soorma_common.events import EventEnvelope, EventTopic


# User ID can be set via environment variable (simulates authentication)
# Note: Memory service currently expects UUID format
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
USER_ID = os.getenv("USER_ID", DEFAULT_USER_ID)


async def send_request(request: str):
    """Send a user request to the knowledge management system."""
    
    # Create EventClient
    client = EventClient(
        agent_id="knowledge-client",
        source="knowledge-client",
    )
    
    print(f"\n📤 Sending request: {request}")
    print("─" * 60)
    
    # Track response
    response_received = asyncio.Event()
    response_data = {}
    
    # Define response handlers for both possible responses
    @client.on_event("knowledge.stored", topic=EventTopic.ACTION_RESULTS)
    async def on_knowledge_stored(event: EventEnvelope):
        """Handle knowledge stored confirmation."""
        response_data["type"] = "knowledge.stored"
        response_data["data"] = event.data or {}
        response_received.set()
    
    @client.on_event("question.answered", topic=EventTopic.ACTION_RESULTS)
    async def on_question_answered(event: EventEnvelope):
        """Handle question answer response."""
        response_data["type"] = "question.answered"
        response_data["data"] = event.data or {}
        response_received.set()
    
    # Connect to platform
    await client.connect(topics=[EventTopic.ACTION_RESULTS])
    
    # Generate correlation ID
    correlation_id = str(uuid4())
    
    print(f"   User: {USER_ID}")
    
    # Publish user request event with user_id in envelope
    await client.publish(
        event_type="user.request",
        topic=EventTopic.ACTION_REQUESTS,
        data={"request": request},
        correlation_id=correlation_id,
        user_id=USER_ID,  # User ID propagates through event chain
    )
    
    print(f"   Request sent (correlation_id: {correlation_id})")
    print("   Waiting for response...")
    print()
    
    try:
        # Wait for response (either knowledge.stored or question.answered)
        await asyncio.wait_for(response_received.wait(), timeout=15.0)
        
        event_type = response_data.get("type", "")
        data = response_data.get("data", {})
        
        print("─" * 60)
        print(f"📥 Response received ({event_type}):")
        print()
        
        if event_type == "knowledge.stored":
            # Response from knowledge store
            if data.get("success"):
                print(f"✅ {data.get('message')}")
            else:
                print(f"❌ {data.get('message')}")
                
        elif event_type == "question.answered":
            # Response from answer agent
            question = data.get("question", "")
            answer = data.get("answer", "")
            has_knowledge = data.get("has_knowledge", False)
            knowledge_used = data.get("knowledge_used", [])
            
            print(f"Q: {question}")
            print()
            print(f"A: {answer}")
            print()
            
            if has_knowledge and knowledge_used:
                print(f"📚 Used {len(knowledge_used)} knowledge sources")
                print(f"   Top relevance: {knowledge_used[0].get('score', 0):.3f}")
        
        print("─" * 60)
        print()
        
    except asyncio.TimeoutError:
        print("\n⏱️  Timeout waiting for response")
        print("   Make sure all agents are running: ./start.sh")
        print()
    finally:
        await client.disconnect()


async def interactive_mode():
    """Interactive mode for continuous conversation."""
    print("=" * 60)
    print("  Knowledge Management System - Interactive Mode")
    print("=" * 60)
    print()
    print("Examples:")
    print("  • Store: 'Python was created by Guido van Rossum in 1991'")
    print("  • Ask:   'Who created Python?'")
    print()
    print("Type 'exit' or 'quit' to stop")
    print("=" * 60)
    print()
    
    while True:
        try:
            request = input("You: ").strip()
            
            if not request:
                continue
            
            if request.lower() in ["exit", "quit", "q"]:
                print("\n👋 Goodbye!\n")
                break
            
            await send_request(request)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def main():
    """Main entry point."""
    
    if len(sys.argv) > 1:
        # Single request mode
        request = " ".join(sys.argv[1:])
        asyncio.run(send_request(request))
    else:
        # Interactive mode
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()
