"""
Search episodic memory for past interactions.

Simple utility to search interactions for the hardcoded demo user.

Usage:
    python search_memory.py "Python"
    python search_memory.py "Docker containers" 10
"""

import asyncio
import sys
from soorma import PlatformContext

# Hardcoded user ID (matches client.py)
USER_ID = "00000000-0000-0000-0000-000000000001"


async def search_memory(query: str, user_id: str, limit: int = 5):
    """Search episodic memory for relevant past interactions."""
    context = PlatformContext()
    print(f"🔍 Searching memory for: '{query}' (user: {user_id})\n")
    
    try:
        # Search interactions
        results = await context.memory.search_interactions(
            agent_id="chat-agent",
            query=query,
            user_id=user_id,
            limit=limit
        )
        
        if not results:
            print(f"No matching interactions found.")
            print("\nTry:")
            print("  bash start.sh  # Start the chatbot")
            print("  python client.py  # Chat and create history")
            print("  python search_memory.py 'Python'  # Search again")
            return
        
        # Display results
        print(f"Found {len(results)} relevant interactions:\n")
        print("=" * 60)
        
        for i, interaction in enumerate(results, 1):
            role_emoji = {
                "user": "👤",
                "assistant": "🤖",
                "system": "⚙️",
                "tool": "🔧"
            }
            role = interaction["role"]
            emoji = role_emoji.get(role, "💬")
            
            print(f"\nResult {i}:")
            print(f"{emoji} [{role.upper()}]")
            print(f"   {interaction['content']}")
            
            if interaction.get("metadata"):
                session_id = interaction["metadata"].get("session_id", "unknown")
                print(f"   Session: {session_id}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure Memory Service is running: soorma dev")
        print("2. Check service health: curl http://localhost:8083/health")
        print("3. Chat with the bot to create history: python client.py")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search_memory.py \"<query>\" [limit]")
        print("\nExample:")
        print("  python search_memory.py 'Python'")
        print("  python search_memory.py 'Docker' 10")
        sys.exit(1)
    
    query = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    print(f"Searching for user: {USER_ID}\n")
    asyncio.run(search_memory(query, USER_ID, limit))
