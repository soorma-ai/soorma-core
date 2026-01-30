"""
Interactive chatbot client with multi-session support.

This client:
1. Connects to the chatbot backend
2. Allows users to start/resume chat sessions
3. Sends messages and displays responses
4. Manages session state
5. Tracks sessions locally
"""

import asyncio
import sys
import uuid
from datetime import datetime
from soorma import EventClient
from soorma.memory import MemoryClient
from soorma_common.events import EventEnvelope, EventTopic


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
        self.memory_client = MemoryClient()
        self.session_id = None
        self.waiting_for_response = False
        self.response_event = None
    
    async def connect(self):
        """Connect to the platform."""
        await self.client.connect(topics=[EventTopic.ACTION_RESULTS])
        
        # Register response handler
        @self.client.on_event("chat.response", topic=EventTopic.ACTION_RESULTS)
        async def on_response(event: EventEnvelope):
            data = event.data or {}
            
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
        print("  /sessions - List existing sessions")
        print("  /delete - Delete a session")
        print("  /quit - Exit")
        print("=" * 60)
    
    async def start_new_session(self) -> str:
        """Start a new chat session."""
        session_id = str(uuid.uuid4())  # Full UUID required for working memory
        print(f"\n✨ Started new session: {session_id}\n")
        # Create Plan record for this new session
        await self.create_plan_record(session_id)
        return session_id
    
    async def create_plan_record(self, plan_id: str) -> bool:
        """Create a Plan record in memory service for tracking."""
        try:
            await self.memory_client.create_plan(
                plan_id=plan_id,
                goal_event="chat.conversation",
                goal_data={"type": "episodic_memory_demo"},
                tenant_id=TENANT_ID,
                user_id=USER_ID
            )
            return True
        except Exception as e:
            print(f"   ⚠️  Could not create plan record: {e}")
            return False
    
    async def list_plans(self) -> list:
        """List all existing plans in working memory for this user."""
        try:
            print("\n📋 Fetching plans from working memory...")
            plans = await self.memory_client.list_plans(
                tenant_id=TENANT_ID,
                user_id=USER_ID,
                limit=20
            )
            return plans if plans else []
        except Exception as e:
            print(f"   ⚠️  Could not fetch plans: {e}")
            return []
    
    async def choose_session(self) -> str:
        """Display list of plans and let user choose one."""
        plans = await self.list_plans()

        if not plans:
            print("   No existing plans found.")
            print("   Starting a new session instead.\n")
            return await self.start_new_session()
        
        print(f"\n📋 Found {len(plans)} existing plan(s):\n")
        
        # Display plans with indices
        for i, plan in enumerate(plans, 1):
            plan_id = plan.plan_id if hasattr(plan, 'plan_id') else plan.get('planId', 'unknown')
            created = plan.created_at if hasattr(plan, 'created_at') else plan.get('createdAt', 'unknown')
            status = plan.status if hasattr(plan, 'status') else plan.get('status', 'unknown')
            print(f"   {i}. {plan_id}")
            print(f"      Created: {created}, Status: {status}")
        
        print(f"   {len(plans) + 1}. Start a new session")
        print()
        
        # Get user choice
        while True:
            try:
                choice = input("Choose a session (number): ").strip()
                choice_num = int(choice)
                
                if choice_num == len(plans) + 1:
                    return await self.start_new_session()
                
                if 1 <= choice_num <= len(plans):
                    selected = plans[choice_num - 1]
                    session_id = selected.plan_id if hasattr(selected, 'plan_id') else selected.get('planId')
                    print(f"\n✨ Resuming session: {session_id}\n")
                    return session_id
                
                print(f"   ❌ Invalid choice. Please enter 1-{len(plans) + 1}")
            except ValueError:
                print(f"   ❌ Please enter a valid number")
    
    async def delete_session(self) -> None:
        """Delete a plan from working memory."""
        plans = await self.list_plans()
        
        if not plans:
            print("   No plans to delete.")
            return
        
        print(f"\n🗑️  Delete Plan\n")
        print(f"📋 Found {len(plans)} plan(s):\n")
        
        # Display plans with indices
        for i, plan in enumerate(plans, 1):
            plan_id = plan.plan_id if hasattr(plan, 'plan_id') else plan.get('planId', 'unknown')
            created = plan.created_at if hasattr(plan, 'created_at') else plan.get('createdAt', 'unknown')
            print(f"   {i}. {plan_id}")
            print(f"      Created: {created}")
        
        print(f"   {len(plans) + 1}. Cancel")
        print()
        
        # Get user choice
        while True:
            try:
                choice = input("Choose a plan to delete (number): ").strip()
                choice_num = int(choice)
                
                if choice_num == len(plans) + 1:
                    print("   Cancelled.\n")
                    return
                
                if 1 <= choice_num <= len(plans):
                    to_delete = plans[choice_num - 1]
                    plan_id = to_delete.plan_id if hasattr(to_delete, 'plan_id') else to_delete.get('planId')
                    
                    # Confirm deletion
                    confirm = input(f"\n⚠️  Really delete plan {plan_id}? (yes/no): ").strip().lower()
                    if confirm == "yes":
                        try:
                            # Delete plan (includes working memory cleanup)
                            await self.memory_client.delete_plan(
                                plan_id=plan_id,
                                tenant_id=TENANT_ID,
                                user_id=USER_ID
                            )
                            print(f"✅ Plan deleted: {plan_id}\n")
                            # If we deleted the current session, need to switch
                            if plan_id == self.session_id:
                                print("   (Note: Your current session was deleted. Choose another.)\n")
                                self.session_id = await self.choose_session()
                            return
                        except Exception as e:
                            print(f"❌ Failed to delete plan: {e}\n")
                            return
                    else:
                        print("   Cancelled.\n")
                        return
                
                print(f"   ❌ Invalid choice. Please enter 1-{len(plans) + 1}")
            except ValueError:
                print(f"   ❌ Please enter a valid number")
    
    async def send_message(self, message: str):
        """Send a message and wait for response."""
        self.waiting_for_response = True
        self.response_event = asyncio.Event()
        
        await self.client.publish(
            event_type="chat.message",
            topic=EventTopic.ACTION_REQUESTS,
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
        
        # Start with option to choose or create session
        self.session_id = await self.choose_session()
        
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
                    self.session_id = await self.start_new_session()
                    continue
                
                elif user_input.lower() == "/sessions":
                    self.session_id = await self.choose_session()
                    continue
                
                elif user_input.lower() == "/delete":
                    await self.delete_session()
                    continue
                
                elif user_input.startswith("/"):
                    print(f"❌ Unknown command: {user_input}")
                    print("   Available: /new, /sessions, /delete, /quit")
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
