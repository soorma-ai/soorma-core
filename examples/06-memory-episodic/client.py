"""
Interactive chatbot client with multi-session support.

This client:
1. Connects to the chatbot backend
2. Allows users to start/resume chat sessions
3. Sends messages and displays responses
4. Manages session state
"""

import asyncio
import sys
import uuid
from datetime import datetime
from soorma import EventClient


# Hardcoded user ID (in production, this comes from authentication)
USER_ID = "00000000-0000-0000-0000-000000000001"
TENANT_ID = "00000000-0000-0000-0000-000000000000"


class ChatbotClient:
    """Interactive chatbot client."""
    
    def __init__(self):
        self.client = EventClient(
            agent_id="chatbot-client",
            source="chatbot-client"
        )
        self.session_id = None
        self.waiting_for_response = False
        self.response_event = None
    
    async def connect(self):
        """Connect to the platform."""
        await self.client.connect(topics=["action-results"])
        
        # Register response handler
        @self.client.on_event("chat.response", topic="action-results")
        async def on_response(event):
            data = event.get("data", {})
            
            # Check if response is for our session
            if data.get("session_id") != self.session_id:
                return
            
            response = data.get("response", "")
            sources = data.get("sources", {})
            
            print(f"\n🤖 Assistant: {response}")
            
            # Show source information if available
            if sources:
                history = sources.get("history_matches", 0)
                knowledge = sources.get("knowledge_matches", 0)
                if history or knowledge:
                    print(f"   (sources: {history} from history, {knowledge} from knowledge)")
            
            print()
            
            if self.waiting_for_response:
                self.waiting_for_response = False
                if self.response_event:
                    self.response_event.set()
    
    def print_welcome(self):
        """Print welcome message."""
        print("\n" + "=" * 60)
        print("🤖 Intelligent Chatbot with Multi-Memory Architecture")
        print("=" * 60)
        print(f"User ID: {USER_ID}")
        print("\nThis chatbot demonstrates:")
        print("  • Episodic Memory: Remembers all interactions")
        print("  • Semantic Memory: Stores and retrieves knowledge")
        print("  • Working Memory: Maintains session state")
        print("\nCognitive Architecture:")
        print("  • Router: Classifies your intent")
        print("  • RAG Agent: Answers using history + knowledge")
        print("  • Concierge: Helps explore conversation history")
        print("  • Knowledge Store: Saves facts you share")
        print("\nTry these patterns:")
        print("  \"Remember that Python was created by Guido van Rossum\"")
        print("  \"What is Python?\"")
        print("  \"What have we discussed so far?\"")
        print("  \"How many messages have I sent?\"")
        print("\nCommands:")
        print("  /new - Start a new session")
        print("  /sessions - List recent sessions")
        print("  /quit - Exit")
        print("=" * 60)
    
    def start_new_session(self) -> str:
        """Start a new chat session."""
        session_id = str(uuid.uuid4())  # Full UUID required for working memory
        print(f"\n✨ Started new session: {session_id}\n")
        return session_id
    
    async def send_message(self, message: str):
        """Send a message and wait for response."""
        self.waiting_for_response = True
        self.response_event = asyncio.Event()
        
        await self.client.publish(
            event_type="chat.message",
            topic="action-requests",
            data={
                "session_id": self.session_id,
                "message": message
            },
            tenant_id=TENANT_ID,
            user_id=USER_ID,
        )
        
        # Wait for response with timeout
        try:
            await asyncio.wait_for(self.response_event.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            print("\n⏱️  Response timeout. Is the backend running?")
            print("   Start backend agents with: bash start.sh")
            self.waiting_for_response = False
    
    async def run(self):
        """Run the interactive chat loop."""
        await self.connect()
        
        self.print_welcome()
        
        # Start first session
        self.session_id = self.start_new_session()
        
        try:
            while True:
                # Get user input
                try:
                    user_input = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() == "/quit":
                    print("👋 Goodbye!")
                    break
                
                elif user_input.lower() == "/new":
                    self.session_id = self.start_new_session()
                    continue
                
                elif user_input.lower() == "/sessions":
                    print(f"\n📋 Current session: {self.session_id}")
                    print("   (Session history not yet implemented)")
                    print()
                    continue
                
                elif user_input.startswith("/"):
                    print(f"❌ Unknown command: {user_input}")
                    print("   Available: /new, /sessions, /quit")
                    print()
                    continue
                
                # Send message
                await self.send_message(user_input)
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        finally:
            await self.client.disconnect()


async def main():
    """Main entry point."""
    client = ChatbotClient()
    await client.run()


if __name__ == "__main__":
    print("\n🚀 Starting chatbot client...")
    
    # Check if this is being run with arguments (old style)
    if len(sys.argv) > 1:
        print("\n⚠️  Note: This client is now interactive and doesn't take arguments.")
        print("   Just run: python client.py")
        print("   Then type your messages interactively.\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
