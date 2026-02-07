"""
Calculator Client - Send requests to the calculator tool

Usage:
    python client.py --operation add --a 10 --b 5
    python client.py --operation subtract --a 20 --b 8
    python client.py --operation multiply --a 7 --b 6
    python client.py --operation divide --a 100 --b 4
    python client.py --operation divide --a 100 --b 0  # Error case
"""

import asyncio
import argparse
from uuid import uuid4
from soorma import EventClient
from soorma_common.events import EventEnvelope, EventTopic


async def send_calculation_request(operation: str, a: float, b: float):
    """
    Send a calculation request to the calculator tool.
    
    Args:
        operation: One of 'add', 'subtract', 'multiply', 'divide'
        a: First operand
        b: Second operand
    """
    # Map operation to event type
    operation_events = {
        "add": "math.add.requested",
        "subtract": "math.subtract.requested",
        "multiply": "math.multiply.requested",
        "divide": "math.divide.requested",
    }
    
    if operation not in operation_events:
        print(f"❌ Invalid operation: {operation}. Must be one of {list(operation_events.keys())}")
        return
    
    event_type = operation_events[operation]
    response_event = "math.result"
    
    # Create EventClient
    client = EventClient(
        agent_id="calculator-client",
        source="calculator-client",
    )
    
    print("=" * 60)
    print(f"  Calculator Tool - {operation.upper()} Operation")
    print("=" * 60)
    print()
    
    # Track when we receive a response
    response_received = asyncio.Event()
    response_data = {}
    
    # Define response handler
    @client.on_event(response_event, topic=EventTopic.ACTION_RESULTS)
    async def on_response(event: EventEnvelope):
        """Handle the response from the calculator tool."""
        data = event.data or {}
        response_data.update(data)
        response_received.set()
    
    # Connect to the platform
    await client.connect(topics=[EventTopic.ACTION_RESULTS])
    
    print(f"🎯 Sending {operation} request: {a} {operation} {b}")
    print(f"   Event Type: {event_type}")
    print(f"   Response Event: {response_event}")
    
    # Publish the request event
    correlation_id = str(uuid4())
    
    await client.publish(
        event_type=event_type,
        topic=EventTopic.ACTION_REQUESTS,
        data={"a": a, "b": b},
        correlation_id=correlation_id,
        response_event=response_event,
        response_topic="action-results",
    )
    
    print("📤 Request sent!")
    print("📊 Waiting for response...")
    print("-" * 60)
    
    try:
        # Wait for the response (with timeout)
        await asyncio.wait_for(response_received.wait(), timeout=5.0)
        
        # Display the result
        if "error" in response_data:
            print(f"\n❌ Error: {response_data['error']}")
            print(f"   Inputs: {response_data.get('inputs')}\n")
        else:
            result = response_data.get("result")
            print(f"\n✅ Result: {result}")
            print(f"   Operation: {response_data.get('operation')}")
            print(f"   Inputs: {response_data.get('inputs')}\n")
        
    except asyncio.TimeoutError:
        print("\n⚠️  Timeout waiting for response (5 seconds)")
        print("   Make sure the calculator tool is running!")
        print("   Run: ./start.sh\n")
    finally:
        await client.disconnect()
    
    print("=" * 60)

def main():
    """Parse arguments and send calculation request."""
    parser = argparse.ArgumentParser(
        description="Send calculation requests to the calculator tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python client.py --operation add --a 10 --b 5
  python client.py --operation subtract --a 20 --b 8
  python client.py --operation multiply --a 7 --b 6
  python client.py --operation divide --a 100 --b 4
  python client.py --operation divide --a 100 --b 0  # Division by zero
        """
    )
    
    parser.add_argument(
        "--operation",
        type=str,
        required=True,
        choices=["add", "subtract", "multiply", "divide"],
        help="Arithmetic operation to perform"
    )
    parser.add_argument(
        "--a",
        type=float,
        required=True,
        help="First operand"
    )
    parser.add_argument(
        "--b",
        type=float,
        required=True,
        help="Second operand"
    )
    
    args = parser.parse_args()
    
    # Run the async request
    try:
        asyncio.run(send_calculation_request(args.operation, args.a, args.b))
    except KeyboardInterrupt:
        print("\n🛑 Interrupted\n")


if __name__ == "__main__":
    main()
