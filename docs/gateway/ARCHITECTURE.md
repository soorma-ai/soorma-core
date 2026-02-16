# Gateway: Technical Architecture

**Status:** 📋 DRAFT PROPOSAL - NOT REVIEWED  
**Last Updated:** February 15, 2026  
**Related Stages:** Future enhancement (HTTP/REST API for external clients)

---

## ⚠️ CRITICAL: This is NOT Final Architecture

**DO NOT IMPLEMENT BASED ON THIS DOCUMENT WITHOUT FORMAL DESIGN REVIEW**

This document contains **preliminary thinking and draft proposals** for Gateway Service architecture. It has NOT undergone:
- Requirements analysis
- Design review
- Security assessment
- Performance validation
- Stakeholder approval

**Required Steps Before Implementation:**
1. **Discovery Phase:**
   - Analyze use cases and requirements
   - Research HTTP/Event bridging patterns
   - Evaluate authentication/authorization approaches
   - Consider rate limiting and scalability needs

2. **Design Phase:**
   - Create formal RFC/ADR (Architecture Decision Record)
   - Document trade-offs and alternatives considered
   - Security threat modeling
   - API design review (REST conventions, error handling)

3. **Review Phase:**
   - Technical review with team
   - Validate against AGENT.md constitution
   - Update this document with finalized design

**This draft serves as starting point for discussion, NOT implementation blueprint.**

---

## Executive Summary

The Gateway Service provides an **HTTP/REST API** for external clients to interact with Soorma agents. It acts as a bridge between synchronous HTTP requests and the asynchronous event-driven architecture.

**Key Responsibilities:**
- Translate HTTP requests to internal events
- Wait for event responses and return to client
- Authenticate API keys and inject tenant context
- Provide synchronous and asynchronous interfaces

**Current Status:** 🔄 Planned (design phase)

---

## Design Principles

### HTTP Bridge to Event System

**Problem:** External clients use HTTP (request-response), but Soorma uses events (pub-sub).

**Solution:** Gateway translates between protocols:

```
HTTP Request
    ↓
Gateway Service (FastAPI)
    ↓ publish event (correlation_id)
Event Service (NATS)
    ↓ subscribe to topic
Agent (Worker/Planner)
    ↓ process request
Agent
    ↓ publish response event
Event Service
    ↓ match correlation_id
Gateway Service
    ↓ return HTTP response
HTTP Response
```

### Synchronous vs Asynchronous

**Synchronous (Default):**
- Client waits for result
- Gateway holds HTTP connection open
- Timeout after 30 seconds (configurable)
- Best for: Real-time interactions (chat, web UI)

**Asynchronous (Optional):**
- Client receives goal_id immediately
- Client polls `/v1/goals/{goal_id}` for status
- Best for: Long-running workflows (research, analysis)

### REST API Design

**Principles:**
- RESTful resource design (`/v1/goals`, `/v1/agents`)
- JSON request/response bodies
- Standard HTTP status codes (200, 400, 401, 404, 429, 500)
- OpenAPI/Swagger documentation

---

## Service Architecture

### Tech Stack (Planned)

- **Framework:** FastAPI
- **Event Client:** SDK BusClient (HTTP → NATS)
- **Authentication:** JWT or API key validation
- **Async Runtime:** asyncio for event waiting
- **Database:** Redis (optional, for async goal tracking)

### Components

```
services/gateway/
├── src/gateway_service/
│   ├── api/v1/
│   │   ├── goals.py          # Goal submission, status
│   │   ├── agents.py         # Agent discovery
│   │   └── invoke.py         # Direct invocation
│   ├── core/
│   │   ├── auth.py           # API key validation
│   │   ├── event_bridge.py   # HTTP→Event translation
│   │   └── response_waiter.py # Event response waiting
│   ├── models/
│   │   ├── request.py        # HTTP request DTOs
│   │   └── response.py       # HTTP response DTOs
│   └── main.py               # FastAPI app
└── Dockerfile
```

---

## Request/Response Flow

### Synchronous Goal Submission

```python
# Client request
POST /v1/goals
{
    "goal_type": "research.goal",
    "data": {"topic": "AI trends"}
}

# Gateway implementation
@router.post("/v1/goals")
async def submit_goal(request: GoalRequest, auth: Auth = Depends(validate_api_key)):
    # 1. Generate correlation_id
    correlation_id = str(uuid4())
    
    # 2. Publish goal event
    await bus_client.request(
        topic=EventTopic.ACTION_REQUESTS,
        event_type=request.goal_type,
        data=request.data,
        correlation_id=correlation_id,
        response_event="goal.completed",
        response_topic="action-results",
        tenant_id=auth.tenant_id,
        user_id=auth.user_id
    )
    
    # 3. Wait for response (timeout 30s)
    try:
        response_event = await response_waiter.wait_for_response(
            correlation_id=correlation_id,
            timeout=30
        )
        
        # 4. Return result
        return {
            "goal_id": correlation_id,
            "status": "completed",
            "result": response_event.data
        }
    except TimeoutError:
        # 5. Fallback to async mode
        return {
            "goal_id": correlation_id,
            "status": "processing",
            "message": f"Check status at /v1/goals/{correlation_id}"
        }
```

### Asynchronous Goal Status Query

```python
GET /v1/goals/{goal_id}

# Gateway implementation
@router.get("/v1/goals/{goal_id}")
async def get_goal_status(goal_id: str, auth: Auth = Depends(validate_api_key)):
    # Query Memory Service for plan state
    plan = await memory_client.get_plan(plan_id=goal_id)
    
    if not plan:
        raise HTTPException(404, "Goal not found")
    
    return {
        "goal_id": goal_id,
        "status": plan.status,  # running, completed, failed
        "result": plan.state.get("result") if plan.status == "completed" else None,
        "error": plan.state.get("error") if plan.status == "failed" else None
    }
```

---

## Response Waiter Implementation

**Problem:** HTTP connection must wait for event response.

**Solution:** Subscribe to response topic, match correlation_id.

**Implementation:**

```python
class ResponseWaiter:
    def __init__(self, bus_client: BusClient):
        self.bus = bus_client
        self.pending_responses: Dict[str, asyncio.Future] = {}
    
    async def start(self):
        """Subscribe to action-results topic."""
        await self.bus.subscribe(
            topics=[EventTopic.ACTION_RESULTS],
            handler=self._handle_response
        )
    
    async def _handle_response(self, event: EventEnvelope):
        """Match event to pending request."""
        correlation_id = event.correlation_id
        if correlation_id in self.pending_responses:
            future = self.pending_responses.pop(correlation_id)
            future.set_result(event)
    
    async def wait_for_response(
        self,
        correlation_id: str,
        timeout: float = 30.0
    ) -> EventEnvelope:
        """Wait for response event with timeout."""
        future = asyncio.Future()
        self.pending_responses[correlation_id] = future
        
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self.pending_responses.pop(correlation_id, None)
            raise TimeoutError(f"No response after {timeout}s")
```

---

## Authentication & Multi-Tenancy

### API Key Validation

**Format:** `Bearer sk_live_{random_string}`

**Validation:**

```python
async def validate_api_key(authorization: str = Header(None)) -> Auth:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid API key")
    
    api_key = authorization.split(" ")[1]
    
    # Validate key (check database or JWT)
    key_data = await api_key_service.validate(api_key)
    if not key_data:
        raise HTTPException(401, "Invalid API key")
    
    return Auth(
        tenant_id=key_data["tenant_id"],
        user_id=key_data["user_id"],
        scopes=key_data["scopes"]
    )
```

### Tenant Context Injection

**Implementation:** Auth object provides tenant/user context.

**Event Propagation:**

```python
# All events published by Gateway include tenant/user from API key
await bus_client.publish(
    topic=EventTopic.ACTION_REQUESTS,
    event_type="goal.requested",
    data=data,
    tenant_id=auth.tenant_id,  # From API key
    user_id=auth.user_id        # From API key
)
```

**Isolation:** Event Service enforces tenant isolation via RLS.

---

## API Specification (Planned)

### POST /v1/goals - Submit Goal

**Request:**

```json
{
    "goal_type": "research.goal",
    "data": {
        "topic": "AI trends",
        "depth": "comprehensive"
    },
    "timeout": 30  // optional, seconds
}
```

**Response (Sync - Completed):**

```json
{
    "goal_id": "goal-123",
    "status": "completed",
    "result": {
        "findings": [...],
        "summary": "..."
    },
    "execution_time_ms": 5420
}
```

**Response (Async - Timeout):**

```json
{
    "goal_id": "goal-123",
    "status": "processing",
    "message": "Goal submitted, check status at /v1/goals/goal-123"
}
```

### GET /v1/goals/{goal_id} - Get Status

**Response:**

```json
{
    "goal_id": "goal-123",
    "status": "processing",  // or "completed", "failed"
    "progress": {
        "current_stage": "research",
        "completed_tasks": 3,
        "total_tasks": 5
    },
    "result": null  // or final result if completed
}
```

### GET /v1/agents - List Agents

**Response:**

```json
{
    "agents": [
        {
            "agent_id": "research-advisor",
            "name": "Research Advisor",
            "capabilities": ["research", "analysis"],
            "status": "active",
            "last_heartbeat": "2026-02-15T10:30:00Z"
        }
    ]
}
```

### POST /v1/invoke - Direct Invocation

**Request:**

```json
{
    "agent_id": "research-advisor",
    "action": "research",
    "params": {
        "topic": "AI trends"
    }
}
```

**Response:**

```json
{
    "result": {
        "findings": [...]
    }
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | Success | Goal completed successfully |
| 202 | Accepted | Goal submitted (async mode) |
| 400 | Bad Request | Invalid request format |
| 401 | Unauthorized | Invalid/missing API key |
| 404 | Not Found | Goal/agent not found |
| 429 | Rate Limit | Too many requests |
| 500 | Server Error | Internal error |
| 503 | Service Unavailable | Event Service down |
| 504 | Timeout | Goal execution timeout |

### Error Response Format

```json
{
    "error": {
        "code": "goal_timeout",
        "message": "Goal execution exceeded 30 second timeout",
        "details": {
            "goal_id": "goal-123",
            "elapsed_ms": 30042
        }
    }
}
```

---

## Configuration

### Environment Variables (Planned)

| Variable | Default | Description |
|----------|---------|-------------|
| `EVENT_SERVICE_URL` | `http://event-service:8000` | Event Service endpoint |
| `MEMORY_SERVICE_URL` | `http://memory-service:8001` | Memory Service endpoint |
| `REGISTRY_SERVICE_URL` | `http://registry-service:8002` | Registry Service endpoint |
| `API_KEY_SECRET` | (required) | Secret for API key encryption |
| `TIMEOUT_SECONDS` | `30` | Default goal execution timeout |
| `MAX_CONCURRENT_GOALS` | `100` | Concurrent goal limit per instance |
| `REDIS_URL` | (optional) | Redis for distributed ResponseWaiter |
| `RATE_LIMIT_PER_MINUTE` | `60` | Rate limit per API key |

---

## Performance Characteristics

### Throughput

- **Goal submission:** ~500 req/sec (limited by Event Service)
- **Status query:** ~2000 req/sec (Memory Service query)
- **Agent discovery:** ~1000 req/sec (Registry Service query)

### Latency

- **Synchronous goal:** Depends on agent execution (typically 1-10 seconds)
- **Asynchronous submit:** ~50ms (event publish only)
- **Status query:** ~20ms (database lookup)

### Scalability

- **Horizontal:** Add Gateway instances behind load balancer
- **Stateless:** ResponseWaiter uses Redis for distributed state
- **Connection pooling:** Reuse HTTP connections to Event Service

---

## Architectural Design Decisions

### 1. Correlation-Based Response Matching

**Decision:** Use correlation_id to match responses, not channels/queues.

**Rationale:**
- Simpler than per-request queues
- Works with NATS pub-sub model
- Scales to many concurrent requests

### 2. Timeout with Async Fallback

**Decision:** Return 202 Accepted if timeout, not 504 Gateway Timeout.

**Rationale:**
- Better client experience (get goal_id for polling)
- Avoids HTTP gateway timeout errors
- Allows long-running workflows

### 3. API Key (Not OAuth2)

**Decision:** Use API keys for authentication, not OAuth2.

**Rationale:**
- Simpler for machine-to-machine authentication
- No token refresh complexity
- Easier for curl/Postman testing
- OAuth2 can be added later for human users

### 4. FastAPI (Not Flask/Django)

**Decision:** Use FastAPI framework.

**Rationale:**
- Native async/await support
- Automatic OpenAPI documentation
- Type hints and validation (Pydantic)
- High performance

---

## Implementation Status

### Current

- � **DRAFT documentation phase - NOT approved for implementation**
- 🔄 Placeholder service (Dockerfile only)
- ⚠️ **Formal design review REQUIRED before proceeding**

### Planned (After Design Approval)

- ⬜ Goal submission endpoint
- ⬜ Goal status query endpoint
- ⬜ Agent discovery endpoint
- ⬜ Direct invocation endpoint
- ⬜ ResponseWaiter implementation
- ⬜ API key authentication
- ⬜ Rate limiting
- ⬜ OpenAPI specification
- ⬜ Client SDKs (JavaScript, TypeScript)
- ⬜ Webhook notifications
- ⬜ WebSocket support (real-time updates)

---

## Related Documentation

- [README.md](./README.md) - User guide and API examples
- [Event System](../event_system/ARCHITECTURE.md) - Internal event-driven architecture
- [Discovery System](../discovery/ARCHITECTURE.md) - Agent discovery and registration
- [Memory System](../memory_system/ARCHITECTURE.md) - Plan state management

- [README.md](./README.md) - User guide
- [Gateway Service](../../services/gateway/README.md) - Service implementation
