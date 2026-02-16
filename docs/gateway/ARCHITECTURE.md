# Gateway: Technical Architecture

**Status:** 📋 Stable  
**Last Updated:** February 15, 2026

---

## Design Principles

[HTTP bridge to event system, REST API design]

## Service Design

[FastAPI service, event bridge architecture]

## Request/Response Flow

```
HTTP Request → Gateway → Event Service → Agent → Event Service → Gateway → HTTP Response
```

## Authentication & Multi-tenancy

[API key validation, tenant context injection]

## Endpoints

### Goal Submission
- POST /v1/goals
- Request/response schemas

### Agent Discovery
- GET /v1/agents
- Filtering and pagination

### Direct Invocation
- POST /v1/invoke
- Synchronous vs asynchronous modes

---

## Implementation Status

- ✅ Core endpoints implemented
- ✅ API key authentication
- ✅ Event bridging

---

## Related Documentation

- [README.md](./README.md) - User guide
- [Gateway Service](../../services/gateway/README.md) - Service implementation
