"""
Client — Example 13: A2A Gateway Interoperability.

Demonstrates A2A client behaviour from an external caller's perspective:

  1. Discover what the gateway can do via the A2A Agent Card.
  2. Read the card's skills to understand accepted input.
  3. Send A2A tasks using the skills advertised on the card.

The client uses plain HTTP (httpx) — just like any external A2A client would.
It has no knowledge of Soorma internals, NATS, or the event bus.

Usage:
    # Show the agent card (gateway discovery)
    python client.py card

    # Send a task using a topic advertised on the card
    python client.py send "Research quantum computing"

    # Full demo: show card, then send three sample tasks
    python client.py demo

    # Default (runs demo)
    python client.py
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional
from uuid import uuid4

import httpx
from dotenv import load_dotenv
import os

load_dotenv()

GATEWAY_URL: str = os.environ.get("GATEWAY_URL", "http://localhost:9000").rstrip("/")
TIMEOUT: float = 35.0  # slightly above the gateway's 30 s internal timeout

# ---------------------------------------------------------------------------
# Sample tasks derived from the skills on the agent card
# ---------------------------------------------------------------------------

SAMPLE_QUERIES = [
    "Research quantum computing breakthroughs in 2025",
    "Explain machine learning model interpretability",
    "What are the security implications of blockchain in enterprise settings?",
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

async def fetch_agent_card(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Fetch the A2A Agent Card from the gateway's well-known endpoint.

    Args:
        client: Shared httpx.AsyncClient instance.

    Returns:
        Parsed Agent Card JSON as a dict.

    Raises:
        httpx.HTTPStatusError: If the gateway returns a non-2xx status.
    """
    response = await client.get(f"{GATEWAY_URL}/.well-known/agent.json")
    response.raise_for_status()
    return response.json()


async def send_a2a_task(
    client: httpx.AsyncClient,
    query: str,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Send an A2A task to the gateway.

    Constructs an A2A Task payload with a single text part and POSTs it
    to ``/a2a/tasks/send``.

    Args:
        client: Shared httpx.AsyncClient instance.
        query: Free-text research query to send as the task input.
        task_id: Optional task ID; auto-generated if not supplied.

    Returns:
        Parsed A2A Task Response JSON as a dict.

    Raises:
        httpx.HTTPStatusError: If the gateway returns a non-2xx status.
    """
    task_id = task_id or f"task-{uuid4().hex[:8]}"
    payload = {
        "id": task_id,
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": query}],
        },
    }
    response = await client.post(
        f"{GATEWAY_URL}/a2a/tasks/send",
        json=payload,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_agent_card(card: Dict[str, Any]) -> None:
    """Pretty-print an A2A Agent Card to stdout.

    Args:
        card: Parsed Agent Card dict.
    """
    print("=" * 60)
    print("  A2A Agent Card")
    print("=" * 60)
    print(f"  Name:        {card.get('name')}")
    print(f"  Description: {card.get('description')}")
    print(f"  URL:         {card.get('url')}")
    print(f"  Version:     {card.get('version')}")

    auth = card.get("authentication", {})
    schemes = auth.get("schemes", [])
    print(f"  Auth:        {', '.join(schemes) or 'none'}")

    skills = card.get("skills", [])
    if skills:
        print()
        print(f"  Skills ({len(skills)}):")
        for skill in skills:
            print(f"    • {skill['id']}")
            print(f"      {skill.get('description', '')}")
            input_schema = skill.get("inputSchema")
            if input_schema:
                # Show $ref name or inline schema compactly
                ref = input_schema.get("$ref")
                if ref:
                    print(f"      inputSchema: $ref → {ref}")
                else:
                    props = list(input_schema.get("properties", {}).keys())
                    print(f"      inputSchema: {{{', '.join(props)}}}")
    print()


def print_task_response(response: Dict[str, Any], query: str) -> None:
    """Pretty-print an A2A Task Response.

    Args:
        response: Parsed A2A Task Response dict.
        query: The original query (for context display).
    """
    status = response.get("status", "unknown")
    icon = "✅" if status == "completed" else "❌"
    print(f"  {icon} Task {response.get('id')}")
    print(f"     Query:   {query!r}")
    print(f"     Status:  {status}")
    if response.get("error"):
        print(f"     Error:   {response['error']}")
    print()


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

async def cmd_card() -> None:
    """Fetch and display the A2A Agent Card."""
    print()
    print(f"[client] Fetching Agent Card from {GATEWAY_URL}/.well-known/agent.json")
    print()
    async with httpx.AsyncClient() as client:
        card = await fetch_agent_card(client)
    print_agent_card(card)
    print("[client] ✓ Agent Card fetched successfully")
    print()
    print("Use the skills above to send tasks:")
    skills = card.get("skills", [])
    for skill in skills:
        input_schema = skill.get("inputSchema", {})
        ref = input_schema.get("$ref") if input_schema else None
        hint = f"(schema: {ref})" if ref else ""
        print(f"  python client.py send \"<query for '{skill['id']}' skill>\" {hint}")
    print()


async def cmd_send(query: str) -> None:
    """Send a single A2A task and show the response.

    First fetches the Agent Card to confirm the gateway is reachable and to
    display which skill will handle the request.

    Args:
        query: Research query to send.
    """
    print()
    print("=" * 60)
    print("  Example 13 — A2A Gateway Client")
    print("=" * 60)
    print()

    async with httpx.AsyncClient() as http:
        # Step 1 — discover what the agent can do
        print(f"[client] Fetching Agent Card from {GATEWAY_URL}...")
        card = await fetch_agent_card(http)
        print_agent_card(card)

        # Step 2 — confirm there is at least one skill to target
        skills = card.get("skills", [])
        if not skills:
            print("[client] ✗ No skills found on Agent Card — is the internal agent running?")
            sys.exit(1)

        # The card tells us this agent handles free-text research queries
        target_skill = skills[0]
        print(f"[client] Using skill: '{target_skill['id']}' — {target_skill.get('description', '')}")
        print()

        # Step 3 — send the task
        task_id = f"task-{uuid4().hex[:8]}"
        print(f"[client] Sending A2A task (id={task_id})...")
        print(f"         Query: {query!r}")
        print()

        response = await send_a2a_task(http, query=query, task_id=task_id)

        print_task_response(response, query)

        status = response.get("status")
        if status == "completed":
            print("[client] ✓ Round-trip complete: external HTTP → internal event bus → HTTP response")
        else:
            print(f"[client] ✗ Task ended with status: {status}")
            sys.exit(1)


async def cmd_demo() -> None:
    """Full demo: show Agent Card, then send multiple tasks using discovered skills.

    This is the recommended first-run command — it mirrors how a real A2A client
    would discover and use the gateway:
      1. Fetch the Agent Card to learn available skills.
      2. Send a task per skill using the input advertised on the card.
    """
    print()
    print("=" * 60)
    print("  Example 13 — A2A Gateway Demo")
    print("=" * 60)
    print()

    async with httpx.AsyncClient() as http:
        # -------------------------------------------------------------------
        # Phase 1: Discover
        # -------------------------------------------------------------------
        print("[client] Phase 1: Discover — fetch Agent Card")
        print()
        card = await fetch_agent_card(http)
        print_agent_card(card)

        skills = card.get("skills", [])
        if not skills:
            print("[client] ✗ No skills advertised — is the internal agent running?")
            sys.exit(1)

        print(f"[client] Found {len(skills)} skill(s):  {', '.join(s['id'] for s in skills)}")
        print()

        # -------------------------------------------------------------------
        # Phase 2: Use — send one task per sample query using the first skill
        # -------------------------------------------------------------------
        print("[client] Phase 2: Use — send tasks using the advertised skill")
        print()

        target_skill = skills[0]
        print(f"[client] Targeting skill: '{target_skill['id']}'")
        input_schema = target_skill.get("inputSchema", {})
        ref = input_schema.get("$ref") if input_schema else None
        if ref:
            print(f"[client] Input schema:     $ref → {ref}")
        print()

        results = []
        for i, query in enumerate(SAMPLE_QUERIES, start=1):
            task_id = f"demo-{i:03d}-{uuid4().hex[:6]}"
            print(f"[client] Task {i}/{len(SAMPLE_QUERIES)} — id={task_id}")
            print(f"         Query: {query!r}")
            response = await send_a2a_task(http, query=query, task_id=task_id)
            status = response.get("status", "unknown")
            icon = "✅" if status == "completed" else "❌"
            print(f"         {icon} Status: {status}")
            print()
            results.append(status)

        # -------------------------------------------------------------------
        # Summary
        # -------------------------------------------------------------------
        passed = sum(1 for s in results if s == "completed")
        print("=" * 60)
        print(f"  Demo complete: {passed}/{len(results)} tasks completed successfully")
        if passed == len(results):
            print("  ✓ A2A Gateway round-trip verified end-to-end")
        print("=" * 60)
        print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate command."""
    args = sys.argv[1:]

    try:
        if not args or args[0] == "demo":
            asyncio.run(cmd_demo())
        elif args[0] == "card":
            asyncio.run(cmd_card())
        elif args[0] == "send":
            query = " ".join(args[1:]) if len(args) > 1 else SAMPLE_QUERIES[0]
            asyncio.run(cmd_send(query))
        else:
            # Treat the whole argument list as a free-text query
            asyncio.run(cmd_send(" ".join(args)))
    except httpx.ConnectError:
        print()
        print(f"[client] ✗ Cannot connect to gateway at {GATEWAY_URL}")
        print("         Is ./start.sh running?  Is the gateway on the right port?")
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        print()
        print(f"[client] ✗ HTTP {exc.response.status_code}: {exc.response.text}")
        sys.exit(1)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
