# Integration Test Instructions

## Purpose
Validate interactions across unit boundaries for the multi-tenancy rollout.

## Integration Scenarios

### Scenario 1: Event Service trust boundary -> Tracker ingestion
- Description: ensure Event Service sanitizes/injects platform tenant identity and Tracker consumes authoritative fields.
- Setup:
  - Start event-service and tracker with shared NATS.
  - Ensure `SOORMA_PLATFORM_TENANT_ID` is set in publishers and service runtime.
- Execute:
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core/services/event-service
python -m pytest tests/test_publish_api.py tests/test_hello_world_flow.py --tb=short -q

cd /Users/amit/ws/github/soorma-ai/soorma-core/services/tracker
python -m pytest tests/test_nats_subscribers.py --tb=short -q
```
- Expected: event payloads remain service-tenant scoped while platform tenant is enforced by headers/middleware.

### Scenario 2: SDK wrapper defaults -> Memory/Tracker low-level clients
- Description: ensure `context.memory` and `context.tracker` default from bound event metadata and project three headers.
- Execute:
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core/sdk/python
python -m pytest \
  tests/test_context_wrappers.py \
  tests/test_context_tracker_wrapper.py \
  tests/test_context_memory_deletion.py \
  tests/test_workflow_integration.py --tb=short -q
```
- Expected: wrapper calls succeed without explicit per-call identity where event metadata is bound.

### Scenario 3: SDK direct clients with service identity args
- Description: ensure low-level clients reject old kwargs and accept service-scoped args.
- Execute:
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core/sdk/python
python -m pytest \
  tests/test_memory_client.py \
  tests/test_memory_client_deletion.py \
  tests/test_tracker_service_client.py \
  tests/test_sdk_semantic_upsert_privacy.py --tb=short -q
```
- Expected: all requests use `service_tenant_id` + `service_user_id` at low-level API.

## Environment Setup
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core
source .venv/bin/activate
```

## Cleanup
- Stop any locally started services (event-service, tracker, memory).
- Clear temp sqlite/nats test artifacts if generated.
