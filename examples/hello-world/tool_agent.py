#!/usr/bin/env python3
"""
Hello World Tool Agent

Demonstrates the Tool pattern using the Soorma SDK.
The Tool exposes stateless operations that can be invoked by Workers.
"""

from datetime import datetime
from soorma import Tool
from soorma.agents.tool import ToolRequest


# Create a Tool instance using the SDK
tool = Tool(
    name="greeting-tool",
    description="Performs greeting operations",
    capabilities=["greet", "farewell"],
)


@tool.on_invoke("greet")
async def handle_greet(request: ToolRequest, context) -> dict:
    """
    Handle a greet operation.
    
    This is the SDK pattern: use @tool.on_invoke() decorator to register
    a handler for a specific operation.
    
    Args:
        request: ToolRequest with operation, data, request_id, etc.
        context: PlatformContext with registry, memory, bus, tracker clients
    
    Returns:
        Result dictionary
    """
    print(f"\n🔧 Tool invoked: greet")
    print(f"   Request ID: {request.request_id}")
    print(f"   Data: {request.data}")
    
    name = request.data.get("name", "World")
    greeting = f"Hello, {name}! 👋"
    
    print(f"\n   💬 {greeting}")
    
    return {
        "greeting": greeting,
        "name": name,
        "timestamp": datetime.now().isoformat(),
    }


@tool.on_invoke("farewell")
async def handle_farewell(request: ToolRequest, context) -> dict:
    """
    Handle a farewell operation.
    
    Args:
        request: ToolRequest with operation, data, request_id, etc.
        context: PlatformContext
    
    Returns:
        Result dictionary
    """
    print(f"\n🔧 Tool invoked: farewell")
    print(f"   Request ID: {request.request_id}")
    print(f"   Data: {request.data}")
    
    name = request.data.get("name", "World")
    farewell = f"Goodbye, {name}! 👋"
    
    print(f"\n   💬 {farewell}")
    
    return {
        "farewell": farewell,
        "name": name,
        "timestamp": datetime.now().isoformat(),
    }


@tool.on_startup
async def startup():
    """Called when the tool starts."""
    print("\n🚀 Greeting Tool started!")
    print(f"   Name: {tool.name}")
    print(f"   Operations: {tool.capabilities}")
    print("   Listening for tool requests...")
    print("   Press Ctrl+C to stop\n")


@tool.on_shutdown
async def shutdown():
    """Called when the tool stops."""
    print("\n👋 Greeting Tool shutting down")


if __name__ == "__main__":
    tool.run()
