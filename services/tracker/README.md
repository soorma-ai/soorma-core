# Tracker Service

**Status:** ✅ Complete (Stage 4 Phase 3)  
**Purpose:** Event-driven observability for autonomous agents (DisCo framework)

## Overview

The Tracker Service provides real-time workflow observability by subscribing to system events and tracking:
- Task execution progress (pending → running → completed/failed)
- Plan hierarchies (nested sub-plans)
- Delegation groups (parallel task fan-out/fan-in)
- Event timelines (distributed trace reconstruction)
- Agent performance metrics

## Architecture

### Responsibilities
1. **Event Subscription:** Subscribe to `system-events`, `action-requests`, `action-results` topics
2. **Progress Tracking:** Record task state transitions in PostgreSQL
3. **Plan Hierarchy:** Track parent-child plan relationships
4. **Query API:** Provide read-only endpoints for workflow observability

### Non-Responsibilities
- **Event Publishing:** Tracker is read-only (passive consumer)
- **Workflow Orchestration:** Handled by Planner agents
- **State Mutations:** Tracker observes, never modifies workflow state

## Multi-Tenancy

All data is isolated by tenant using PostgreSQL Row-Level Security (RLS):

### Required Headers

Every API request **MUST** include authentication headers:

- `X-Tenant-ID`: Tenant identifier (UUID format)
- `X-User-ID`: User identifier (UUID format)

**Example:**
```bash
curl -H "X-Tenant-ID: 550e8400-e29b-41d4-a716-446655440000" \
     -H "X-User-ID: 660e8400-e29b-41d4-a716-446655440001" \
     http://localhost:8084/v1/tracker/plans/plan-123
```

### RLS Policy Enforcement

The service uses PostgreSQL Row-Level Security to enforce tenant isolation:

```sql
CREATE POLICY task_executions_user_isolation 
ON tracker.task_executions
USING (
    tenant_id = current_setting('app.tenant_id')::UUID
    AND user_id = current_setting('app.user_id')::UUID
);
```

**How it works:**
1. Service extracts `X-Tenant-ID` and `X-User-ID` from request headers
2. Sets PostgreSQL session variables: `SET app.tenant_id = '...'`
3. All queries automatically filtered by RLS policies
4. Users can ONLY see their own data within their tenant

**Tenant Isolation Guarantees:**
- No cross-tenant data leakage (enforced at database level)
- No cross-user data visibility within same tenant
- Failed authentication → 403 Forbidden
- Missing headers → 403 Forbidden

API requests MUST include:
- `X-Tenant-ID` header
- `X-User-ID` header

## API Endpoints

### Query APIs (Read-Only)

All endpoints require `X-Tenant-ID` and `X-User-ID` headers.

#### Get Plan Progress

`GET /v1/tracker/plans/{plan_id}`

Returns plan execution summary with task completion counts.

**Example Request:**
```bash
curl -H "X-Tenant-ID: 550e8400-e29b-41d4-a716-446655440000" \
     -H "X-User-ID: 660e8400-e29b-41d4-a716-446655440001" \
     http://localhost:8084/v1/tracker/plans/plan-abc123
```

**Example Response (200 OK):**
```json
{
  "plan_id": "plan-abc123",
  "status": "running",
  "started_at": "2026-02-23T10:15:30Z",
  "completed_at": null,
  "task_count": 5,
  "completed_tasks": 3,
  "failed_tasks": 0,
  "current_state": "research"
}
```

**Error Responses:**
- `403 Forbidden` - Missing or invalid tenant/user headers
- `404 Not Found` - Plan does not exist or not accessible to this user
- `500 Internal Server Error` - Database or service error

#### Get Plan Tasks

`GET /v1/tracker/plans/{plan_id}/tasks`

Returns execution history for all tasks in the plan.

**Example Request:**
```bash
curl -H "X-Tenant-ID: 550e8400-e29b-41d4-a716-446655440000" \
     -H "X-User-ID: 660e8400-e29b-41d4-a716-446655440001" \
     http://localhost:8084/v1/tracker/plans/plan-abc123/tasks
```

**Example Response (200 OK):**
```json
{
  "tasks": [
    {
      "task_id": "task-001",
      "event_type": "feedback.fetch",
      "state": "completed",
      "started_at": "2026-02-23T10:15:35Z",
      "completed_at": "2026-02-23T10:15:37Z",
      "duration_seconds": 2.1,
      "agent_id": "fetcher-agent"
    },
    {
      "task_id": "task-002",
      "event_type": "sentiment.analyze",
      "state": "running",
      "started_at": "2026-02-23T10:15:38Z",
      "completed_at": null,
      "duration_seconds": null,
      "agent_id": "analyzer-agent"
    }
  ]
}
```

#### Get Plan Timeline

`GET /v1/tracker/plans/{plan_id}/timeline`

Returns chronological event timeline for distributed trace reconstruction.

**Example Request:**
```bash
curl -H "X-Tenant-ID: 550e8400-e29b-41d4-a716-446655440000" \
     -H "X-User-ID: 660e8400-e29b-41d4-a716-446655440001" \
     http://localhost:8084/v1/tracker/plans/plan-abc123/timeline
```

**Example Response (200 OK):**
```json
{
  "events": [
    {
      "timestamp": "2026-02-23T10:15:30Z",
      "event_type": "plan.started",
      "data": {"goal": "analyze.feedback"}
    },
    {
      "timestamp": "2026-02-23T10:15:35Z",
      "event_type": "feedback.fetch.requested",
      "data": {"source": "datastore"}
    },
    {
      "timestamp": "2026-02-23T10:15:37Z",
      "event_type": "feedback.fetched",
      "data": {"count": 42}
    }
  ]
}
```

**Additional Endpoints:**

- `GET /v1/tracker/plans/{plan_id}/sub-plans` - Direct child plans
- `GET /v1/tracker/plans/{plan_id}/hierarchy` - Full plan tree
- `GET /v1/tracker/sessions/{session_id}/plans` - All plans in conversation
- `GET /v1/tracker/delegation-groups/{group_id}` - Parallel delegation status
- `GET /v1/tracker/metrics?agent_id={id}&period={period}` - Agent metrics

### Health Check

`GET /health`

Returns service health status. Does NOT require authentication headers.

**Example Request:**
```bash
curl http://localhost:8084/health
```

**Example Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "0.8.0",
  "database": "connected",
  "event_service": "connected"
}
```

## Development

### Local Setup

```bash
cd services/tracker
poetry install
```

### Run Locally

```bash
# Start with soorma dev (includes PostgreSQL + Event Service)
cd /Users/amit/ws/github/soorma-ai/soorma-core
soorma dev --build

# Or run standalone (requires services running)
cd services/tracker
uvicorn tracker_service.main:app --reload --port 8084
```

### Testing

```bash
cd services/tracker
poetry run pytest tests/ -v --cov
```

## Database Schema

Tables:
- `tracker.task_executions` - Task execution records
- `tracker.state_transitions` - State change history
- `tracker.event_timeline` - Event occurrence records
- `tracker.plan_executions` - Plan hierarchy tracking
- `tracker.delegation_groups` - Parallel delegation groups

All tables use RLS policies for tenant isolation.

## Deployment

### Docker Deployment

The Tracker Service is deployed as a Docker container alongside other Soorma services.

#### Build Image

```bash
# From soorma-core root directory
docker build -f services/tracker/Dockerfile -t tracker-service:0.8.0 .
```

#### Run Container

```bash
docker run -d \
  --name tracker-service \
  -p 8084:8084 \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@postgres:5432/soorma" \
  -e NATS_URL="nats://nats:4222" \
  -e EVENT_SERVICE_URL="http://event-service:8082" \
  tracker-service:0.8.0
```

#### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|----------|
| `DATABASE_URL` | Yes | PostgreSQL connection URL (asyncpg driver) | `postgresql+asyncpg://user:pass@localhost:5432/soorma` |
| `NATS_URL` | Yes | NATS server URL for event subscriptions | `nats://localhost:4222` |
| `EVENT_SERVICE_URL` | Yes | Event Service HTTP endpoint | `http://localhost:8082` |
| `LOG_LEVEL` | No | Logging level (default: INFO) | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `PORT` | No | HTTP server port (default: 8084) | `8084` |

#### Database Migrations

Run Alembic migrations before starting the service:

```bash
# Inside the container or during deployment
cd /app
alembic upgrade head
```

**For development:**
```bash
cd services/tracker
poetry run alembic upgrade head
```

#### Health Check Endpoint

Configure your orchestrator (Kubernetes, Docker Compose) to use the health endpoint:

```yaml
# Docker Compose example
services:
  tracker:
    image: tracker-service:0.8.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8084/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

```yaml
# Kubernetes example
livenessProbe:
  httpGet:
    path: /health
    port: 8084
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /health
    port: 8084
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Production Considerations

- **Database Connection Pooling:** Configure SQLAlchemy pool size based on load
- **Event Subscription:** Service auto-reconnects to NATS on connection loss
- **Horizontal Scaling:** NOT recommended (event subscriptions are stateful)
- **Monitoring:** Expose Prometheus metrics on `/metrics` endpoint (future)
- **Logging:** JSON-structured logs to stdout for container log aggregation

## Integration

### Recommended: SDK Usage (Agent Code)

**Always use the TrackerClient wrapper from PlatformContext**, not the direct API.

```python
from soorma import PlatformContext
from soorma.agents.planner import GoalContext

@planner.on_transition()
async def handle_transition(
    event: EventEnvelope,
    context: PlatformContext,
    plan: PlanContext,
    next_state: str,
) -> None:
    """SDK auto-provides tenant/user context from event."""
    
    # Query plan progress (wrapper extracts auth from event)
    progress = await context.tracker.get_plan_progress(
        plan.plan_id,
        tenant_id=event.tenant_id,  # From event envelope
        user_id=event.user_id,      # From event envelope
    )
    
    if progress:
        print(f"Progress: {progress.completed_tasks}/{progress.task_count}")
        print(f"Status: {progress.status}")
    
    # Get task execution history
    tasks = await context.tracker.get_plan_tasks(
        plan.plan_id,
        tenant_id=event.tenant_id,
        user_id=event.user_id,
    )
    
    for task in tasks:
        print(f"{task.event_type}: {task.state} ({task.duration_seconds}s)")
    
    # Get full plan hierarchy (nested sub-plans)
    hierarchy = await context.tracker.get_plan_hierarchy(
        plan.plan_id,
        tenant_id=event.tenant_id,
        user_id=event.user_id,
    )
```

**Why use the wrapper?**
- ✅ Auth context handling (tenant_id/user_id from events)
- ✅ Consistent error handling across SDK
- ✅ Type-safe response models (Pydantic validation)
- ✅ Retry logic and connection pooling
- ❌ Direct API calls bypass SDK safeguards

### SDK Documentation

For complete SDK reference:
- **TrackerClient API:** See [sdk/python/soorma/tracker_client.py](../../sdk/python/soorma/tracker_client.py)
- **Architecture Patterns:** See [docs/ARCHITECTURE_PATTERNS.md Section 2](../../docs/ARCHITECTURE_PATTERNS.md#2-sdk-two-layer-architecture)
- **Example Integration:** See [examples/10-choreography-basic/planner.py](../../examples/10-choreography-basic/planner.py)

### Direct API Usage (NOT Recommended)

If you must call the API directly (e.g., from non-Python clients):

```bash
# Get plan progress
curl -H "X-Tenant-ID: 550e8400-e29b-41d4-a716-446655440000" \
     -H "X-User-ID: 660e8400-e29b-41d4-a716-446655440001" \
     http://localhost:8084/v1/tracker/plans/plan-abc123
```

**Important:** You MUST manually manage:
- Authentication headers on every request
- Error handling (403, 404, 500)
- Response parsing and validation
- Retry logic for transient failures

## Event Subscriptions

The service subscribes to:

1. **system-events** topic:
   - `task.progress` → Update task execution progress
   - `task.state_changed` → Record state transition
   - `plan.started` → Create plan execution record
   - `plan.state_changed` → Update plan state
   - `plan.completed` → Mark plan complete
   - `delegation.started` → Create delegation group

2. **action-requests** topic:
   - `*` (all events) → Record task start

3. **action-results** topic:
   - `*` (all events) → Record task completion, update delegation groups

## License

MIT License - See [LICENSE](../../LICENSE)
