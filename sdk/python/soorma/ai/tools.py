"""
OpenAI-compatible function tool definitions for AI agents.

These tool definitions allow AI agents (like GPT-4, Claude, etc.) to
interact with the event registry and generate events dynamically.

The tools follow the OpenAI function calling specification and can be
used with any LLM framework that supports function calling.
"""

import json
from typing import Any, Dict, List, Optional
from .event_toolkit import EventToolkit

# Function tools that can be provided to AI agents
AI_FUNCTION_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "discover_events",
            "description": (
                "Discover available events in the system. Use this to find out "
                "what events you can publish or subscribe to. Returns event names, "
                "descriptions, required fields, and example payloads. You can filter "
                "by topic (e.g., 'action-requests', 'business-facts') or search for "
                "specific event names."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": (
                            "Filter events by topic. Common topics include: "
                            "'action-requests' (events requesting actions), "
                            "'business-facts' (event responses with data), "
                            "'notifications' (notification events)."
                        ),
                    },
                    "event_name_pattern": {
                        "type": "string",
                        "description": (
                            "Search for events containing this pattern in their name. "
                            "For example, 'search' will find 'web.search.request', "
                            "'data.search.request', etc."
                        ),
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_event_schema",
            "description": (
                "Get detailed schema information for a specific event. "
                "Use this to understand what payload fields are required, "
                "their types, constraints, and what response to expect. "
                "Returns field descriptions, examples, and validation rules."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_name": {
                        "type": "string",
                        "description": (
                            "Full event name (e.g., 'web.search.request', 'order.created'). "
                            "Use discover_events first if you don't know the exact name."
                        ),
                    },
                },
                "required": ["event_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_event_payload",
            "description": (
                "Create and validate an event payload. Use this to generate "
                "a valid payload for publishing an event. The payload will be "
                "validated against the event's schema and returned in the correct "
                "format (with camelCase field names for JSON). If validation fails, "
                "you'll get detailed error messages explaining what's wrong."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_name": {
                        "type": "string",
                        "description": (
                            "Full event name (e.g., 'web.search.request'). "
                            "Use get_event_schema first to understand required fields."
                        ),
                    },
                    "payload_data": {
                        "type": "object",
                        "description": (
                            "Payload data as a JSON object with the event fields. "
                            "You can use snake_case keys (e.g., 'user_name') and "
                            "they will be automatically converted to camelCase "
                            "(e.g., 'userName')."
                        ),
                    },
                },
                "required": ["event_name", "payload_data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_event_response",
            "description": (
                "Validate an event response against its schema. Use this when "
                "you receive a response from an event (e.g., after publishing "
                "an action request) to ensure it matches the expected format."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_name": {
                        "type": "string",
                        "description": "Name of the event that produced this response.",
                    },
                    "response_data": {
                        "type": "object",
                        "description": "Response data to validate.",
                    },
                },
                "required": ["event_name", "response_data"],
            },
        },
    },
]


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Get the list of AI tool definitions."""
    return AI_FUNCTION_TOOLS


async def execute_ai_tool(
    tool_name: str,
    tool_args: Dict[str, Any],
    registry_url: str = "http://localhost:8000"
) -> Dict[str, Any]:
    """
    Execute an AI tool by name.
    
    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments for the tool
        registry_url: URL of the registry service
        
    Returns:
        Result of the tool execution
    """
    try:
        async with EventToolkit(registry_url) as toolkit:
            if tool_name == "discover_events":
                events = await toolkit.discover_events(
                    topic=tool_args.get("topic"),
                    event_name_pattern=tool_args.get("event_name_pattern")
                )
                return {
                    "success": True,
                    "events": events,
                    "count": len(events)
                }

            elif tool_name == "get_event_schema":
                event = await toolkit.get_event_info(tool_args["event_name"])
                if not event:
                    return {
                        "success": False,
                        "error": f"Event '{tool_args['event_name']}' not found",
                        "suggestion": "Use discover_events to find available events"
                    }
                return {
                    "success": True,
                    "event": event
                }

            elif tool_name == "create_event_payload":
                payload = await toolkit.create_payload(
                    tool_args["event_name"],
                    tool_args["payload_data"]
                )
                return {
                    "success": True,
                    "payload": payload
                }

            elif tool_name == "validate_event_response":
                response = await toolkit.validate_response(
                    tool_args["event_name"],
                    tool_args["response_data"]
                )
                return {
                    "success": True,
                    "validated_response": response
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}",
                    "available_tools": [t["function"]["name"] for t in AI_FUNCTION_TOOLS]
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "suggestion": "Check your input arguments and try again"
        }


def format_tool_result_for_llm(result: Dict[str, Any]) -> str:
    """
    Format tool execution result for LLM consumption.
    
    Args:
        result: Result dictionary from execute_ai_tool
        
    Returns:
        Formatted string representation
    """
    if not result.get("success", False):
        return json.dumps({
            "status": "error ❌",
            "message": result.get("error", "Unknown error"),
            "suggestion": result.get("suggestion", "")
        }, indent=2, ensure_ascii=False)
        
    # Format success results based on content
    if "events" in result:
        events = result["events"]
        if not events:
            return "No events found matching your criteria."
            
        summary = [f"Found {len(events)} event(s):"]
        for event in events:
            summary.append(f"- {event['name']} ({event.get('topic', 'no-topic')})")
            summary.append(f"  Description: {event.get('description', '')}")
            summary.append(f"  Required fields: {', '.join(event.get('required_fields', []))}")
            if event.get("has_response"):
                summary.append("  Has response: Yes")
            summary.append("")
        return "\n".join(summary)
        
    if "event" in result:
        event = result["event"]
        return json.dumps({
            "name": event["name"],
            "description": event.get("description"),
            "topic": event.get("topic"),
            "Payload Fields:": event.get("payload_fields"),
            "example_payload": event.get("example_payload"),
            "has_response": event.get("has_response")
        }, indent=2, ensure_ascii=False)
        
    if "payload" in result:
        return json.dumps({
            "status": "success ✅",
            "message": "Payload validated successfully",
            "payload": result["payload"]
        }, indent=2, ensure_ascii=False)
        
    if "validated_response" in result:
        return json.dumps({
            "status": "success ✅",
            "message": "Response validated successfully",
            "validated_response": result["validated_response"]
        }, indent=2, ensure_ascii=False)
        
    return json.dumps(result, indent=2, ensure_ascii=False)
