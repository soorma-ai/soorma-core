# Example 10: Choreography Planner - Feedback Analysis

**Demonstrates:** Stage 4 Phase 2 ChoreographyPlanner pattern

## What This Shows

- **Autonomous orchestration driven by LLM reasoning** - No hardcoded event sequences
- **Capability-based event discovery** - LLM chooses events based on descriptions, not names
- Explicit action request and response events for choreography
- Planner + three Workers in a simple pipeline
- Tracker Service queries for plan progress

**🔍 See [AUTONOMOUS_DISCOVERY.md](AUTONOMOUS_DISCOVERY.md) for the discovery pattern deep-dive**

## Architecture

```
Client -> Planner -> Fetcher -> Analyzer -> Reporter -> Planner -> Client
		  (LLM picks next event)                       (complete)
```

## Event Flow

1. **Client** publishes `analyze.feedback` with `response_event: feedback.report.ready` and correlation_id
2. **Planner** (`on_goal`) creates plan → **LLM decides** → PUBLISH `data.fetch.requested`
3. **Fetcher** processes → responds with `data.fetched`
4. **Planner** (`on_transition`) receives response → **LLM decides** → PUBLISH `analysis.requested`
5. **Analyzer** processes → responds with `analysis.completed`
6. **Planner** (`on_transition`) receives response → **LLM decides** → PUBLISH `report.requested`
7. **Reporter** processes → responds with `report.ready`
8. **Planner** (`on_transition`) receives response → **LLM decides** → COMPLETE with `feedback.report.ready`
9. **Client** receives final report via correlation_id routing

## How It Works

### ChoreographyPlanner Decision Cycle

The planner uses GPT-4o to autonomously discover and orchestrate workers:

- **on_goal**: Receives initial client goal → Creates plan in Memory → Queries Registry for available events → LLM chooses first action based on capability match
- **on_transition**: Receives worker responses → Restores plan → Queries Registry → LLM decides next action

**LLM Actions:**
- `PUBLISH` - Orchestrate a worker by publishing a discovered event
- `COMPLETE` - Send final result back to client
- `WAIT` - Wait for more events
- `DELEGATE` - Hand off to another planner

### Autonomous Event Discovery

**Key Innovation:** The planner doesn't know event names in advance!

1. **Workers Register Capabilities**: Events have rich descriptions like "Retrieve customer feedback entries from datastore. Use when you need to load raw feedback data..."
2. **Planner Describes Logical Flow**: System instructions say "You need DATA RETRIEVAL capability" (not "call data.fetch.requested")
3. **LLM Matches Capabilities**: Queries Registry, reads descriptions, chooses events that match needed capabilities
4. **True Autonomy**: You can add new workers with different event names - planner discovers them automatically

**Example:** If you create a new worker with event `feedback.load` (instead of `data.fetch.requested`) with the same capability description, the planner will discover and use it. No code changes needed!

See [AUTONOMOUS_DISCOVERY.md](AUTONOMOUS_DISCOVERY.md) for detailed explanation and examples.

### Key Patterns

- **Correlation ID Tracking**: Client's correlation_id flows through all events for response routing
- **Plan Persistence**: Plan state saved to Memory Service after each decision
- **Loop Prevention**: Completed plans skip processing in `on_transition` handler
- **Explicit Response Events**: Workers declare `response_event` in their requests

## Files

- client.py - EventClient that sends feedback analysis goal
- planner.py - ChoreographyPlanner goal/transition handlers
- fetcher.py - Fetches feedback entries
- analyzer.py - Runs sentiment analysis
- reporter.py - Builds report output
- start.sh - Starts all agents

## Prerequisites

- `soorma dev --build` running (Event, Memory, Registry, Tracker services)
- LLM credentials for `ChoreographyPlanner` (for example, `OPENAI_API_KEY`)
- Optional: `pip install "soorma-core[ai]"` or `pip install litellm`

## Running

### Terminal 1: Start Platform Services

```bash
soorma dev --build
```

### Terminal 2: Start Planner + Workers

```bash
cd examples/10-choreography-basic
./start.sh
```

**Important**: Workers start first to register their events in the Registry,
then the planner starts. Wait for all agents to show "started" before sending goals.

### Terminal 3: Send a Goal

```bash
cd examples/10-choreography-basic
python client.py
```

## Expected Output

You should see the planner publish tasks in sequence and the final report
returned to the client as `feedback.report.ready`.

### Example Success Logs

**Planner Terminal:**
```
[ChoreographyPlanner] ✓ Published data.fetch.requested
[ChoreographyPlanner] ✓ Published analysis.requested
[ChoreographyPlanner] ✓ Published report.requested
[ChoreographyPlanner] ✓ Plan feedback-analysis-pipeline-001 completed
[Planner.on_transition] Plan already completed, skipping event processing
```

**Client Terminal:**
```
[client] Sending feedback analysis goal...
[client] Correlation ID: 3da318e8-3bc7-4679-a48d-67a19c505591
[client] Waiting for response (timeout: 30s)...
[client] Received report:
{'task_id': '...', 'status': 'completed', 'report': 'Feedback Report...'}
```

## Troubleshooting

**Client timeout waiting for response:**
- Ensure all services are running: `soorma dev --build`
- Verify all agents started successfully (Planner + 3 Workers)
- Check LLM credentials are configured (`OPENAI_API_KEY`)

**Planner stuck in loop:**
- This should be fixed in v0.7.x+ (plan status persistence)
- Check logs for "Plan already completed, skipping event processing"

**Workers not responding:**
- Ensure workers started BEFORE planner (start.sh does this)
- Check Registry has worker events registered
- Verify worker event names match planner's PUBLISH decisions
