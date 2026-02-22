# Tracker Service

**Version:** 0.7.7  
**Status:** 🚧 In Development (Phase 3)  
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

```sql
CREATE POLICY task_executions_user_isolation 
ON tracker.task_executions
USING (
    tenant_id = current_setting('app.tenant_id')::UUID
    AND user_id = current_setting('app.user_id')::UUID
);
```

API requests MUST include:
- `X-Tenant-ID` header
- `X-User-ID` header

## API Endpoints

### Query APIs (Read-Only)

- `GET /v1/tracker/plans/{plan_id}` - Plan progress summary
- `GET /v1/tracker/plans/{plan_id}/tasks` - Task execution history
- `GET /v1/tracker/plans/{plan_id}/timeline` - Event timeline
- `GET /v1/tracker/plans/{plan_id}/sub-plans` - Direct child plans
- `GET /v1/tracker/plans/{plan_id}/hierarchy` - Full plan tree
- `GET /v1/tracker/sessions/{session_id}/plans` - All plans in conversation
- `GET /v1/tracker/delegation-groups/{group_id}` - Parallel delegation status
- `GET /v1/tracker/metrics?agent_id={id}&period={period}` - Agent metrics

### Health Check

- `GET /health` - Service health status

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

Built as Docker container:

```bash
# Build from soorma-core root
docker build -f services/tracker/Dockerfile -t tracker-service:latest .

# Run
docker run -p 8084:8084 \
  -e DATABASE_URL=postgresql+asyncpg://... \
  -e EVENT_SERVICE_URL=http://event-service:8082 \
  tracker-service:latest
```

## Integration

### SDK Usage (Agent Code)

```python
from soorma import PlatformContext

context = PlatformContext()

# Query plan progress
progress = await context.tracker.get_plan_progress(plan_id="plan-123")
print(f"Completed: {progress.completed_tasks}/{progress.task_count}")

# Get task history
tasks = await context.tracker.get_plan_tasks(plan_id="plan-123")
for task in tasks:
    print(f"{task.event_type}: {task.state} ({task.duration_seconds}s)")

# Get plan hierarchy
hierarchy = await context.tracker.get_plan_hierarchy(plan_id="plan-123")
```

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
