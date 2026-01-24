"""
View conversation history from episodic memory.

Simple utility to view recent interactions for the hardcoded demo user.

Usage:
    python view_history.py [limit]
"""

import asyncio
import sys
from soorma import PlatformContext

# Hardcoded user ID (matches client.py)
USER_ID = "00000000-0000-0000-0000-000000000001"


async def view_history(user_id: str, limit: int = 20):
    """View recent conversation history for a user."""
    context = PlatformContext()
    print(f"📜 Conversation History for {user_id}\n")
    print("=" * 60)
    
    try:
        # Get recent history
        history = await context.memory.get_recent_history(
            agent_id="chat-agent",
            user_id=user_id,
            limit=limit
        )
        
        if not history:
            print(f"\nNo conversation history found for {user_id}")
            print("\nStart the chatbot to create conversation history:")
            print("  bash start.sh  # Terminal 1")
            print("  python client.py  # Terminal 2")
            return
        
        # Display history in chronological order
        print(f"Showing {len(history)} most recent interactions:\n")
        
        for i, interaction in enumerate(history, 1):
            # Format role for display
            role_emoji = {
                "user": "👤",
                "assistant": "🤖",
                "system": "⚙️",
                "tool": "🔧"
            }
            role = interaction["role"]
            emoji = role_emoji.get(role, "💬")
            
            print(f"{emoji} [{role.upper()}]")
            print(f"   {interaction['content']}")
            
            # Show metadata if available
            if interaction.get("metadata"):
                session_id = interaction["metadata"].get("session_id", "unknown")
                print(f"   Session: {session_id}")
            
            if i < len(history):
                print()  # Blank line between interactions
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Failed to retrieve history: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure Memory Service is running: soorma dev")
        print("2. Check service health: curl http://localhost:8083/health")
        print("3. Chat with the bot to create history: python client.py")


if __name__ == "__main__":
    # Optional: specify limit as argument
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    
    print(f"Viewing history for user: {USER_ID}\n")
    asyncio.run(view_history(USER_ID, limit))
