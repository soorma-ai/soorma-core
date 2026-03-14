"""
A2A Gateway Service — Example 13: A2A Gateway Interoperability.

Exposes two HTTP endpoints that implement the Google A2A (Agent-to-Agent)
protocol, bridging external HTTP clients into the Soorma internal event bus.

Endpoints:
  GET  /.well-known/agent.json  — Publish an A2A Agent Card describing the
                                   internal research agent's capabilities.
  POST /a2a/tasks/send          — Accept an A2A Task, route it as an internal
                                   Soorma event, and return the A2A response.

SDK patterns shown:
  - A2AGatewayHelper.agent_to_card()   — AgentDefinition → A2AAgentCard
  - A2AGatewayHelper.task_to_event()   — A2ATask         → EventEnvelope
  - A2AGatewayHelper.event_to_response() — EventEnvelope  → A2ATaskResponse
  - EventClient (lifespan)             — NATS pub/sub without requiring a Worker
  - pending_requests dict              — async Future-per-task response routing
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from soorma.events import EventClient
from soorma.gateway import A2AGatewayHelper
from soorma.registry.client import RegistryClient
from soorma_common.a2a import A2AAgentCard, A2ATask, A2ATaskResponse, A2ATaskStatus
from soorma_common.events import EventEnvelope, EventTopic

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GATEWAY_URL: str = os.environ.get("GATEWAY_URL", "http://localhost:9000")
GATEWAY_PORT: int = int(os.environ.get("GATEWAY_PORT", "9000"))
EVENT_SERVICE_URL: str = os.environ.get("SOORMA_EVENT_SERVICE_URL", "http://localhost:8082")
REGISTRY_URL: str = os.environ.get("SOORMA_REGISTRY_URL", "http://localhost:8081")
TENANT_ID: str = os.environ.get("SOORMA_DEVELOPER_TENANT_ID", "00000000-0000-0000-0000-000000000001")
USER_ID: str = os.environ.get("SOORMA_USER_ID", "00000000-0000-0000-0000-000000000002")

# The internal event type the research agent consumes
INTERNAL_EVENT_TYPE: str = "research.requested"

# Response timeout (seconds) — how long to wait for the internal agent to respond
RESPONSE_TIMEOUT: float = 30.0

# ---------------------------------------------------------------------------
# Shared gateway state (populated in lifespan)
# ---------------------------------------------------------------------------

# EventClient instance used by the gateway for all NATS I/O
_event_client: Optional[EventClient] = None

# Pending response futures keyed by correlation_id (= A2A task.id)
# Populated by send_task() and resolved by the catch-all event handler
_pending_requests: Dict[str, "asyncio.Future[EventEnvelope]"] = {}


# ---------------------------------------------------------------------------
# Lifespan: connect EventClient on startup, disconnect on shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Manage the EventClient lifecycle for the gateway process.

    Args:
        app: The FastAPI application instance (unused; required by FastAPI API).
    """
    global _event_client

    _event_client = EventClient(
        event_service_url=EVENT_SERVICE_URL,
        agent_id="a2a-gateway",
        source="a2a-gateway",
        tenant_id=TENANT_ID,
    )

    # Catch-all handler: resolve any pending Future whose correlation_id matches
    @_event_client.on_all_events
    async def route_response(event: EventEnvelope) -> None:
        """Route incoming action-results events to waiting send_task() callers.

        Args:
            event: Incoming event from the action-results topic.
        """
        correlation_id = event.correlation_id
        if correlation_id and correlation_id in _pending_requests:
            future = _pending_requests[correlation_id]
            if not future.done():
                logger.info(
                    "[gateway] Received response for task %s (event_type=%s)",
                    correlation_id,
                    event.type,
                )
                future.set_result(event)

    await _event_client.connect(topics=[EventTopic.ACTION_RESULTS])
    logger.info("[gateway] EventClient connected — subscribed to action-results")

    yield  # Application is running

    await _event_client.disconnect()
    logger.info("[gateway] EventClient disconnected")


app = FastAPI(
    title="Soorma A2A Gateway",
    description="A2A (Agent-to-Agent) gateway for Soorma internal agents",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/.well-known/agent.json", response_model=Dict[str, Any])
async def get_agent_card() -> Dict[str, Any]:
    """Return the A2A Agent Card for the internal research agent.

    Queries the Soorma Registry for the first agent named "research-agent",
    converts the AgentDefinition to an A2A Agent Card, and returns the JSON
    representation.  External A2A clients use this endpoint to learn what
    capabilities the gateway exposes.

    Returns:
        A2A Agent Card JSON as a plain dictionary.

    Raises:
        HTTPException: 404 if no internal agent is registered yet.
    """
    registry = RegistryClient(base_url=REGISTRY_URL)
    # Query by name — the internal agent registers as "research-agent"
    agents = await registry.query_agents(name="research-agent")
    if not agents:
        raise HTTPException(
            status_code=404,
            detail="Internal agent not registered yet — start internal_agent.py first",
        )
    agent_def = agents[0]
    card: A2AAgentCard = A2AGatewayHelper.agent_to_card(agent_def, gateway_url=GATEWAY_URL)
    logger.info("[gateway] Agent Card requested for %s", agent_def.name)
    return card.model_dump()


@app.post("/a2a/tasks/send", response_model=Dict[str, Any])
async def send_task(task: A2ATask) -> Dict[str, Any]:
    """Accept an A2A Task, route it to the internal agent, and return the response.

    The flow is:
      1. Convert the A2A Task to an EventEnvelope via A2AGatewayHelper.
      2. Register a Future keyed by task.id in _pending_requests.
      3. Publish the event to the action-requests topic (correlation_id = task.id,
         response_event = "a2a.response.<task.id>" so the internal agent knows
         where to publish its result).
      4. Await the Future with RESPONSE_TIMEOUT seconds.
      5. Convert the response EventEnvelope to an A2ATaskResponse and return.

    Args:
        task: Incoming A2A Task from the external client.

    Returns:
        A2A Task Response JSON as a plain dictionary.

    Raises:
        HTTPException: 503 if the gateway is not ready (EventClient not connected).
        HTTPException: 504 if the internal agent does not respond within the timeout.
    """
    if _event_client is None:
        raise HTTPException(status_code=503, detail="Gateway is not ready")

    logger.info("[gateway] Received A2A task id=%s", task.id)

    # Convert A2A Task → Soorma EventEnvelope (data extraction + correlation mapping)
    envelope: EventEnvelope = A2AGatewayHelper.task_to_event(
        task=task,
        event_type=INTERNAL_EVENT_TYPE,
        topic="action-requests",
        tenant_id=TENANT_ID,
        user_id=USER_ID,
    )

    # The internal agent publishes its response to this event type on action-results.
    # We embed the task.id in the event type so it is unique per request.
    response_event_name: str = f"a2a.response.{task.id}"

    # Register a Future before publishing to avoid a race window
    future: asyncio.Future[EventEnvelope] = asyncio.get_running_loop().create_future()
    _pending_requests[task.id] = future

    try:
        await _event_client.publish(
            event_type=INTERNAL_EVENT_TYPE,
            topic=EventTopic.ACTION_REQUESTS,
            data=envelope.data,
            correlation_id=task.id,
            response_event=response_event_name,
            response_topic=EventTopic.ACTION_RESULTS,
            tenant_id=TENANT_ID,
            user_id=USER_ID,
        )
        logger.info(
            "[gateway] Published %s (correlation=%s, response_event=%s)",
            INTERNAL_EVENT_TYPE,
            task.id,
            response_event_name,
        )

        # Wait for the internal agent to publish its result
        response_envelope: EventEnvelope = await asyncio.wait_for(
            future, timeout=RESPONSE_TIMEOUT
        )

        a2a_response: A2ATaskResponse = A2AGatewayHelper.event_to_response(
            event=response_envelope, task_id=task.id
        )
        logger.info(
            "[gateway] ✓ Returning A2A response for task %s (status=%s)",
            task.id,
            a2a_response.status,
        )
        return a2a_response.model_dump()

    except asyncio.TimeoutError:
        logger.error("[gateway] Timeout waiting for response to task %s", task.id)
        raise HTTPException(
            status_code=504,
            detail=f"Internal agent did not respond within {RESPONSE_TIMEOUT}s",
        )
    finally:
        # Always clean up the pending future, whether it resolved or timed out
        _pending_requests.pop(task.id, None)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "gateway_service:app",
        host="0.0.0.0",
        port=GATEWAY_PORT,
        log_level="info",
    )
