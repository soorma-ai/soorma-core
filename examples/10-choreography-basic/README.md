# Example 10: Choreography Planner - Feedback Analysis

**Demonstrates:** Stage 4 Phase 2 ChoreographyPlanner pattern

## What This Shows

- Autonomous orchestration driven by LLM decisions
- Explicit action request and response events
- Planner + three Workers in a simple pipeline
- Tracker Service queries for plan progress

## Architecture

```
Client -> Planner -> Fetcher -> Analyzer -> Reporter -> Planner -> Client
		  (LLM picks next event)                       (complete)
```

## Event Flow

1. Client publishes `analyze.feedback` with response_event `feedback.report.ready`
2. Planner publishes `data.fetch.requested`
3. Fetcher responds `data.fetched`
4. Planner publishes `analysis.requested`
5. Analyzer responds `analysis.completed`
6. Planner publishes `report.requested`
7. Reporter responds `report.ready`
8. Planner completes with `feedback.report.ready`

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

### Terminal 3: Send a Goal

```bash
cd examples/10-choreography-basic
python client.py
```

## Expected Output

You should see the planner publish tasks in sequence and the final report
returned to the client as `feedback.report.ready`.
