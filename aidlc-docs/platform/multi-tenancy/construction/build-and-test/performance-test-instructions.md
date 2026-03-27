# Performance Test Instructions

## Purpose
Validate that multi-tenancy identity projection changes do not introduce regressions in latency or throughput.

## Scope
This initiative did not add new performance-critical algorithms; focus on regression checks around:
- Middleware/header extraction paths
- Event publish path in SDK EventClient
- Memory/Tracker client request overhead

## Test Targets
- P95 SDK client call latency for representative Memory/Tracker operations
- Event publish throughput under concurrent client load
- Error rate under sustained traffic

## Baseline Targets
- Response time: no more than 10% regression from pre-change baseline
- Error rate: < 1%
- Throughput: maintain baseline requests/sec within 10%

## Suggested Approach

### 1. Prepare environment
```bash
cd /Users/amit/ws/github/soorma-ai/soorma-core
source .venv/bin/activate
# start required services with local test configs
```

### 2. Run lightweight load generation (example template)
```bash
# Replace with your team-approved load tool/script
# Example placeholders:
# python scripts/perf/run_memory_tracker_load.py --duration 300 --concurrency 25
# python scripts/perf/run_event_publish_load.py --duration 300 --concurrency 50
```

### 3. Collect metrics
- Request latency percentiles (P50, P95, P99)
- Throughput (req/s)
- Error counts by endpoint
- CPU/memory usage of event-service, memory, and tracker

### 4. Analyze and compare
- Compare results against prior baseline runs for same environment shape.
- If regression >10% on P95 or throughput, open follow-up optimization task.

## Notes
- No dedicated performance harness was introduced in this unit set.
- Treat this file as the execution guide for the QA/performance runbook.
