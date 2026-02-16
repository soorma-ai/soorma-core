# Gateway: User Guide

**Status:** � DRAFT - Requires Design Review  
**Last Updated:** February 15, 2026  
**Related Stages:** Future enhancement (HTTP/REST API for external clients)

---

## ⚠️ IMPORTANT: Preliminary Documentation

**This documentation is a DRAFT proposal and has NOT been reviewed or approved.**

Before starting implementation:
1. **Conduct design discovery** - Research requirements, use cases, alternatives
2. **Create detailed design document** - Architecture decisions, trade-offs, security considerations
3. **Review with stakeholders** - Validate approach before coding
4. **DO NOT implement based on this draft alone** - It represents initial thinking, not final design

---

## Overview

The **Gateway Service** provides an HTTP/REST API for external clients (web applications, mobile apps, third-party integrations) to interact with Soorma agents. It acts as an entry point for clients that cannot directly participate in the event-driven architecture.

**Purpose:**
- **HTTP Bridge:** Translate HTTP requests to internal events
- **Synchronous Interface:** Provide request-response API for goal submission
- **Authentication:** Manage API keys and tenant context
- **Client SDKs:** Enable non-Python clients to use Soorma

**Current Status:** 🔄 Planned (placeholder service exists)

---

## Core Concepts

### HTTP/Event Bridge

**Problem:** External clients (web apps, mobile) use HTTP, but Soorma agents use events.

**Solution:** Gateway translates HTTP requests to events and waits for response events.

**Flow:**
```
Client (HTTP)
    ↓ POST /v1/goals
Gateway Service
    ↓ Publish goal event (action-requests topic)
Event Bus
    ↓ Subscribe to events
Planner Agent
    ↓ Process goal, delegate tasks
Worker Agents
    ↓ Complete tasks
Planner Agent
    ↓ Publish response event (action-results topic)
Gateway Service
    ↓ Wait for response (correlation_id match)
Client (HTTP)
    ↑ Return response
```

### Synchronous vs Asynchronous

**Synchronous (Default):**
- Client waits for result
- Gateway holds HTTP connection open
- Timeout after configured duration (e.g., 30 seconds)

**Asynchronous (Planned):**
- Client receives goal_id immediately
- Client polls `/v1/goals/{goal_id}` for status
- Webhook notification when complete

### Authentication & Multi-Tenancy

**API Keys:** Clients authenticate with API keys tied to tenant/user.

**Tenant Context:** Gateway extracts tenant_id from API key, sets context for all events.

**User Identity:** `user_id` represents client identity (human user or external system).

---

## Planned API Endpoints

### Goal Submission

```http
POST /v1/goals
Authorization: Bearer {api_key}
Content-Type: application/json

{
    "goal_type": "research.goal",
    "data": {
        "topic": "AI trends",
        "depth": "comprehensive"
    }
}

Response: 200 OK
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

**Timeout Response:**

```http
Response: 202 Accepted
{
    "goal_id": "goal-123",
    "status": "processing",
    "message": "Goal submitted, check status at /v1/goals/goal-123"
}
```

### Goal Status Query

```http
GET /v1/goals/{goal_id}
Authorization: Bearer {api_key}

Response: 200 OK
{
    "goal_id": "goal-123",
    "status": "processing",  // or "completed", "failed"
    "progress": {
        "current_stage": "research",
        "completed_tasks": 3,
        "total_tasks": 5
    }
}
```

### Agent Discovery

```http
GET /v1/agents
Authorization: Bearer {api_key}

Response: 200 OK
{
    "agents": [
        {
            "agent_id": "research-advisor",
            "name": "Research Advisor",
            "capabilities": ["research", "analysis"],
            "status": "active"
        }
    ]
}
```

### Direct Invocation

```http
POST /v1/invoke
Authorization: Bearer {api_key}
Content-Type: application/json

{
    "agent_id": "research-advisor",
    "action": "research",
    "params": {
        "topic": "AI trends"
    }
}

Response: 200 OK
{
    "result": {
        "findings": [...]
    }
}
```

---

## Authentication

### API Key Management

**Creation:** Admin creates API keys via CLI or Admin API.

```bash
soorma-admin create-api-key \\
    --tenant-id tenant-123 \\
    --user-id alice \\
    --name "Web App Key" \\
    --scopes read,write
```

**Usage:** Clients pass API key in `Authorization` header.

```http
Authorization: Bearer sk_live_...
```

**Validation:** Gateway validates key, extracts tenant/user context.

### Tenant Context

**Extraction:** API key contains tenant_id.

**Propagation:** Gateway sets `tenant_id` and `user_id` on all published events.

**Isolation:** Events are isolated to tenant (via Event Service RLS).

---

## Use Cases

### Web Applications

**Scenario:** React/Vue web app submits goals via HTTP.

**Example:**

```javascript
// Frontend code
async function submitResearchGoal(topic) {
    const response = await fetch('https://api.soorma.ai/v1/goals', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            goal_type: 'research.goal',
            data: { topic }
        })
    });
    
    return await response.json();
}
```

### Mobile Apps

**Scenario:** iOS/Android app invokes agents via REST API.

**Benefits:**
- No Python SDK required
- HTTP is universally supported
- Simplified authentication (API keys)

### External Integrations

**Scenario:** Third-party system (Slack bot, webhook receiver) triggers workflows.

**Example:** Slack command triggers research goal.

```python
# Slack bot handler
@slack.command("/research")
def research_command(topic: str):
    response = requests.post(
        "https://api.soorma.ai/v1/goals",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"goal_type": "research.goal", "data": {"topic": topic}}
    )
    return response.json()["result"]["summary"]
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

---

## Best Practices

### API Key Security

1. **Never commit keys:** Use environment variables
2. **Rotate regularly:** Change keys periodically
3. **Scope appropriately:** Limit permissions (read-only vs read-write)
4. **Monitor usage:** Track API calls per key

### Timeout Handling

1. **Set reasonable timeouts:** 30-60 seconds typical
2. **Fallback to async:** Return goal_id if timeout
3. **Retry logic:** Client should retry failed requests
4. **Idempotency:** Use correlation_id to prevent duplicate goals

### Error Handling

```javascript
// Client error handling
try {
    const result = await submitGoal(data);
    if (result.status === 'completed') {
        return result.result;
    } else {
        // Poll for completion
        return await pollGoalStatus(result.goal_id);
    }
} catch (error) {
    if (error.status === 401) {
        // Invalid API key
    } else if (error.status === 429) {
        // Rate limit exceeded
    } else if (error.status === 500) {
        // Server error, retry with backoff
    }
}
```

---

## Common Patterns

### Pattern: Polling for Completion

```javascript
async function submitGoalAndWait(data, maxWait = 60000) {
    // Submit goal
    const response = await fetch('/v1/goals', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${API_KEY}` },
        body: JSON.stringify(data)
    });
    
    const { goal_id } = await response.json();
    
    // Poll until complete or timeout
    const startTime = Date.now();
    while (Date.now() - startTime < maxWait) {
        const status = await fetch(`/v1/goals/${goal_id}`, {
            headers: { 'Authorization': `Bearer ${API_KEY}` }
        }).then(r => r.json());
        
        if (status.status === 'completed') {
            return status.result;
        } else if (status.status === 'failed') {
            throw new Error(status.error);
        }
        
        await sleep(1000);  // Poll every second
    }
    
    throw new Error('Goal execution timeout');
}
```

### Pattern: Webhook Notification (Planned)

```javascript
// Register webhook
await fetch('/v1/webhooks', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${API_KEY}` },
    body: JSON.stringify({
        url: 'https://myapp.com/webhook/goal-complete',
        events: ['goal.completed', 'goal.failed']
    })
});

// Webhook receiver
app.post('/webhook/goal-complete', (req, res) => {
    const { goal_id, status, result } = req.body;
    // Handle completion
});
```

---

## Implementation Status

### Current

- 🔄 Placeholder service (Dockerfile only)
- � **DRAFT documentation only - NO implementation started**
- ⚠️ **Requires formal design review before any coding**

### Planned (After Design Review)

- ⬜ Goal submission endpoint
- ⬜ Goal status query endpoint
- ⬜ Agent discovery endpoint
- ⬜ Direct invocation endpoint
- ⬜ API key authentication
- ⬜ Webhook notifications
- ⬜ Client SDKs (JavaScript, TypeScript)
- ⬜ OpenAPI specification
- ⬜ Rate limiting and quotas

---

## Client SDK Examples (Planned)

### JavaScript/TypeScript

```typescript
import { SoormaClient } from '@soorma/client';

const client = new SoormaClient({
    apiKey: process.env.SOORMA_API_KEY,
    baseUrl: 'https://api.soorma.ai'
});

// Submit goal
const result = await client.goals.submit({
    goalType: 'research.goal',
    data: { topic: 'AI trends' }
});

console.log(result.findings);
```

### cURL

```bash
curl -X POST https://api.soorma.ai/v1/goals \\
    -H "Authorization: Bearer sk_live_..." \\
    -H "Content-Type: application/json" \\
    -d '{
        "goal_type": "research.goal",
        "data": {"topic": "AI trends"}
    }'
```

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Technical design
- [Event System](../event_system/README.md) - Internal event-driven architecture
- [Discovery System](../discovery/README.md) - Agent discovery and registration
