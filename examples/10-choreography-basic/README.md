# Example 10: Autonomous Choreography - Feedback Analysis

**Demonstrates:** Stage 4 Phase 2 - Truly Autonomous LLM-Driven Orchestration

## What This Shows

This example demonstrates **zero-hardcoded choreography** where the planner discovers, orchestrates, and moves data through a multi-stage pipeline using only:
- **System prompt** describing business requirements (not event names!)
- **Registry Service** providing dynamic event discovery
- **LLM reasoning** for capability matching and data forwarding

**Key Innovation:** No hardcoded event chains, no workflow definitions, no manual data plumbing. Workers are hot-swappable.

### Breakthrough Features

✅ **No Hardcoded Event Names** - Planner never knows event names in advance  
✅ **Capability Matching** - LLM discovers events by reading descriptions from Registry  
✅ **Automatic Data Flow** - LLM extracts previous responses and forwards to next worker  
✅ **Hot-Swappable Workers** - Add/remove workers without touching planner code  
✅ **Same-Name Pattern** - Request/response use identical event names on different topics  
✅ **Simple Planner Code** - Just 2 handlers + system prompt (no workflow logic!)

**🔍 Deep Dive:** [AUTONOMOUS_DISCOVERY.md](AUTONOMOUS_DISCOVERY.md)

## Architecture

```
Client ──> Planner ──> Registry (event discovery)
            ↓ ↑              ↓
            LLM ←────────────┘ (capability descriptions)
            ↓
         [Dynamic Workflow]
            ↓
       data.fetch.requested → Fetcher → data.fetch.requested (response)
            ↓
       analysis.requested → Analyzer → analysis.requested (response)  
            ↓
       report.requested → Reporter → report.requested (response)
            ↓
         COMPLETE
            ↓
         Client
```

**Notice:** Same event names on different topics (ACTION_REQUESTS vs ACTION_RESULTS)

## Event Flow (Live Example)

This shows an actual execution trace with data flowing through the pipeline:

### Step 1: Client Initiates Goal
```
Client → analyze.feedback (correlation: abc-123)
         payload: {"objective": "feedback analysis", "product": "Soorma Hub"}
```

### Step 2: Planner Discovers & Publishes First Event
```
Planner queries Registry → Gets 3 events with descriptions
LLM reads descriptions → Matches "DATA RETRIEVAL" capability
LLM publishes: data.fetch.requested (topic: action-requests)
               payload: {"product": "Soorma Hub", "sample_size": 3}
               response_event: data.fetch.requested
```

### Step 3: Fetcher Processes & Responds
```
Fetcher consumes: data.fetch.requested (topic: action-requests)
Fetcher publishes: data.fetch.requested (topic: action-results) ← Same name!
                   payload: {"product": "Soorma Hub", 
                            "feedback": [{"rating": 5, ...}, {"rating": 3, ...}, ...]}
                   correlation_id: abc-123
```

### Step 4: Planner Receives Response, LLM Extracts Data
```
Planner on_transition receives: data.fetch.requested (topic: action-results)
LLM sees event_data: {"product": "Soorma Hub", "feedback": [...]}
LLM reads analysis.requested schema: needs "product" and "feedback" fields
LLM publishes: analysis.requested (topic: action-requests)
               payload: {"product": "Soorma Hub", "feedback": [...]}  ← Extracted!
               response_event: analysis.requested
```

### Step 5: Analyzer Processes & Responds
```
Analyzer consumes: analysis.requested (topic: action-requests)
Analyzer publishes: analysis.requested (topic: action-results) ← Same name!
                    payload: {"product": "Soorma Hub",
                             "summary": "Analyzed 3 entries: 2 positive, 1 negative...",
                             "positive_count": 2, "negative_count": 1}
                    correlation_id: abc-123
```

### Step 6: Planner Receives, LLM Extracts & Forwards
```
Planner on_transition receives: analysis.requested (topic: action-results)
LLM sees: {"product": "Soorma Hub", "summary": "...", "positive_count": 2, ...}
LLM reads report.requested schema: needs all these fields
LLM publishes: report.requested (topic: action-requests)
               payload: {"product": "Soorma Hub", "summary": "...", 
                        "positive_count": 2, "negative_count": 1}  ← All extracted!
```

### Step 7: Reporter Generates Final Report
```
Reporter consumes: report.requested (topic: action-requests)
Reporter publishes: report.requested (topic: action-results)
                    payload: {"product": "Soorma Hub",
                             "report": "Feedback Report for Soorma Hub...",
                             "timestamp": "2026-02-22T20:27:42"}
```

### Step 8: Planner Completes
```
Planner on_transition receives: report.requested (topic: action-results)
LLM decides: COMPLETE (all steps done)
Planner publishes: feedback.report.ready (topic: client-responses)
                   payload: {"status": "success", "product": "Soorma Hub",
                            "report": "...", "timestamp": "..."}
                   correlation_id: abc-123
```

### Step 9: Client Receives Final Result
```
Client receives: feedback.report.ready (correlation: abc-123)
Output: Full report with all data from pipeline
```

**Key Observation:** Data flows automatically through all 3 workers. Planner never hardcodes this!

## Why This Matters

### Traditional Orchestration (Hardcoded)
```python
# planner.py - TYPICAL approach (what we DON'T do)
async def handle_goal(goal):
    # Step 1: Hardcoded event name
    await bus.publish("data.fetch.requested", {"product": goal.data["product"]})
    
    # Wait for response... (how? manual correlation tracking)
    response = await wait_for("data.fetched")
    
    # Step 2: Manual data extraction
    feedback = response["feedback"]
    await bus.publish("analysis.requested", {"product": ..., "feedback": feedback})
    
    # Step 3: More manual extraction...
    # ... and so on
```

**Problems:**
- Event names hardcoded → Can't hot-swap workers
- Data extraction manual → Breaks when schemas change
- Workflow logic in planner → Coupled to pipeline structure
- Adding workers requires planner code changes

### Autonomous Choreography (This Example)
```python
# planner.py - AUTONOMOUS approach (what we DO)
async def handle_goal(goal, context):
    plan = await PlanContext.create_from_goal(goal, context, ...)
    
    # Single call - everything else is automatic!
    decision = await planner.reason_next_action(
        trigger=f"New goal: {goal.data.get('objective')}",
        context=context,
        plan_id=plan.plan_id,
    )
    
    await planner.execute_decision(decision, context, goal, plan)

async def handle_transition(event, context, plan, next_state):
    # LLM seen event data, decides next step, extracts payload
    decision = await planner.reason_next_action(
        trigger=f"Event: {event.type}",
        context=context,
        plan_id=plan.plan_id,
        custom_context={"event_data": event.data},  # ← LLM sees this
    )
    
    await planner.execute_decision(decision, context, event, plan)
```

**Benefits:**
- ✅ No event names in code → Workers hot-swappable
- ✅ LLM extracts data → Schema changes don't break planner
- ✅ No workflow logic → Just business requirements in system prompt
- ✅ Add/remove workers → Zero planner code changes

## How It Works

### The Autonomous Choreography Pattern

Unlike traditional orchestration where planners hardcode workflows, this pattern achieves **true autonomy**:

#### 1. Workers Register Capabilities (Not Workflows)

Workers define rich, capability-based event descriptions:

```python
# fetcher.py - Worker defines WHAT it does, not WHERE it fits in workflow
DATA_FETCH_REQUESTED_EVENT = EventDefinition(
    event_name="data.fetch.requested",
    topic=EventTopic.ACTION_REQUESTS,
    description="Retrieve customer feedback entries from datastore. "
                "Use when you need to load raw feedback data for a product. "
                "Returns a collection of feedback entries with ratings and comments.",
    payload_schema=DataFetchRequestPayload.model_json_schema(),
    response_schema=DataFetchedPayload.model_json_schema()
)

worker = Worker(
    name="feedback-fetcher",
    capabilities=["feedback_fetch"],
    events_consumed=[DATA_FETCH_REQUESTED_EVENT],
    events_produced=[DATA_FETCH_RESPONDED_EVENT],
)
```

Workers register with Registry Service on startup. **Planner never sees this code.**

#### 2. Planner Describes Business Logic (Not Technical Steps)

```python
# planner.py - System prompt describes WHAT to achieve, not HOW
planner = ChoreographyPlanner(
    system_instructions="""
    You orchestrate a feedback analysis workflow with these logical steps:
    1. DATA RETRIEVAL - Get raw feedback from datastore
    2. SENTIMENT ANALYSIS - Extract insights and sentiment breakdown  
    3. REPORT GENERATION - Create formatted report for presentation
    
    Choose events that match these capabilities based on their descriptions.
    """
)
```

**Notice:** No event names! Just business requirements.

#### 3. LLM Discovers and Orchestrates Dynamically

When a goal arrives, the `ChoreographyPlanner`:

1. **Queries Registry** for all events consumed by active workers
2. **Sends event descriptions to LLM** (GPT-4o)
3. **LLM matches capabilities** to business requirements
4. **LLM publishes events** with proper payloads extracted from context

```python
# This happens automatically inside ChoreographyPlanner.reason_next_action()
# Planner code just calls this method - no workflow logic!

@planner.on_goal("analyze.feedback")
async def handle_goal(goal: GoalContext, context: PlatformContext) -> None:
    plan = await PlanContext.create_from_goal(goal, context, ...)
    
    # Single call - LLM does everything!
    decision = await planner.reason_next_action(
        trigger=f"New goal: {goal.data.get('objective')}",
        context=context,
        plan_id=plan.plan_id,
    )
    
    await planner.execute_decision(decision, context, goal, plan)
```

#### 4. Automatic Data Flow Through Pipeline

**Critical:** LLM extracts data from previous responses and forwards to next worker.

```
Step 1: Planner → data.fetch.requested → Fetcher
        Response: {"product": "Widget", "feedback": [...]}

Step 2: LLM extracts {"product": "Widget", "feedback": [...]} from Step 1
        Planner → analysis.requested → Analyzer
        Payload: {"product": "Widget", "feedback": [...]}  ← Auto-populated!
        Response: {"product": "Widget", "summary": "...", "positive_count": 5, ...}

Step 3: LLM extracts from Step 2
        Planner → report.requested → Reporter  
        Payload: {"product": "Widget", "summary": "...", "positive_count": 5, ...}
```

**No manual data plumbing in planner code!** LLM reads schemas and forwards data.

#### 5. Hot-Swappable Workers

Want to replace the fetcher? Just create a new worker with better capability description:

```python
# NEW_fetcher.py - Different event name, same capability!
FEEDBACK_LOAD_EVENT = EventDefinition(
    event_name="feedback.load",  # ← Different name!
    topic=EventTopic.ACTION_REQUESTS,
    description="Retrieve customer feedback entries from datastore. "
                "Use when you need to load raw feedback data...",  # ← Same capability
)
```

**Start the new worker, stop the old one.** Planner discovers the new event automatically. **Zero code changes.**

### Same-Name Event Pattern

Requests and responses use **identical event names** on different topics:

| Event Name | Topic | Purpose |
|------------|-------|---------|
| `data.fetch.requested` | `action-requests` | Worker consumes this |
| `data.fetch.requested` | `action-results` | Worker publishes response here |

**Why?** Simplifies LLM prompt - just set `response_event = event_type`. Correlation ID ties them together.

**Enabled by:** Registry Service composite unique constraint `(event_name, topic)` allows same name on different topics.

### The Two-Method Planner

Entire planner logic is **just 2 handlers**:

```python
@planner.on_goal("analyze.feedback")  
async def handle_goal(goal, context):
    # Create plan → LLM decides → Execute
    
@planner.on_transition()
async def handle_transition(event, context, plan, next_state):
    # Restore plan → LLM decides → Execute
```

**That's it.** No workflow state machines, no hardcoded chains, no data mapping. LLM handles everything.

### Key Patterns

- **Correlation ID Tracking**: Single ID flows through all events for response routing
- **Plan Persistence**: Plan state saved to Memory Service after each decision  
- **Circuit Breaker**: Max actions limit prevents infinite loops
- **Schema-Driven**: LLM reads JSON schemas to know what data to forward
- **Capability Descriptions**: Rich text enables semantic matching vs keyword search

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

### Enabling Verbose Logging (For Troubleshooting)

**Current Default:**
- ✅ **Agent progress visible** (`print` statements): Task handling, worker logic, planner decisions
- ✅ **ChoreographyPlanner internals visible** (`logger.info`): Event discovery, LLM reasoning, decision execution
- ❌ **Infrastructure hidden** (`logger` at WARNING): HTTP requests, registrations, heartbeats, SSE connections

**To see ALL SDK infrastructure logs** (edit agent files):

```python
# Comment out these lines to see HTTP/infrastructure logs:
# logging.getLogger("httpx").setLevel(logging.WARNING)
# logging.getLogger("soorma.registry.client").setLevel(logging.WARNING)
# logging.getLogger("soorma.agents.base").setLevel(logging.WARNING)
# ...etc
```

This reveals:
- HTTP traffic: `POST http://localhost:8081/v1/events "HTTP/1.1 200 OK"`
- Registry operations: `Event report.requested registered successfully`
- Agent lifecycle: `✓ Registered feedback-reporter (feedback-reporter-33a99e9c)`
- Event streaming: `Connected to Event Service (connection_id: ...)`

**To disable ChoreographyPlanner internals** (just agent progress):
```python
# Add this after basicConfig:
logging.getLogger("soorma.ai.choreography").setLevel(logging.WARNING)
```

## Expected Output

By default, you'll see the **logical flow** of agent processing without low-level infrastructure noise.

### Client Terminal

```bash
[client] Sending feedback analysis goal...
[client] Correlation ID: abc-123-def-456
[client] ✓ Received report: {'product': 'Soorma Hub', 'summary': '...', 'report': '...'}
```

### Planner Terminal (Logical Flow Visible)

```
[planner] feedback-orchestrator started
[planner] Listening for analyze.feedback

[planner] Goal received: analyze.feedback
[planner] Correlation: abc-123-def-456
[planner] Creating plan context...
[planner] Plan created: plan-789
[planner] Calling ChoreographyPlanner.reason_next_action()...
INFO:soorma.ai.choreography:[ChoreographyPlanner] Starting reasoning for trigger: New goal: feedback analysis
INFO:soorma.ai.choreography:[ChoreographyPlanner] Discovering actionable events from Registry...
INFO:soorma.ai.choreography:[ChoreographyPlanner] Found 3 actionable events
INFO:soorma.ai.choreography:[ChoreographyPlanner] LLM response received (450 chars)
INFO:soorma.ai.choreography:[ChoreographyPlanner] Successfully parsed decision: action=publish
INFO:soorma.ai.choreography:[ChoreographyPlanner] Publishing event: data.fetch.requested
INFO:soorma.ai.choreography:[ChoreographyPlanner] Correlation ID: abc-123-def-456
INFO:soorma.ai.choreography:[ChoreographyPlanner] Response event: data.fetch.requested
[planner] Decision received: publish

[planner] ▶ Transition triggered by: data.fetch.requested
[planner] Calling reason_next_action for event: data.fetch.requested
INFO:soorma.ai.choreography:[ChoreographyPlanner] Publishing event: analysis.requested
...
```

**Notice:** Clean agent progress (`print`) + ChoreographyPlanner internals (`logger`) - NO HTTP noise!

### Worker Terminals (Logical Processing)

**Fetcher:**
```
[fetcher] feedback-fetcher started
[fetcher] Listening for: data.fetch.requested

[fetcher] ▶ Received: data.fetch.requested
[fetcher] Task ID: task-123
[fetcher] Correlation ID: abc-123-def-456
[fetcher] Response event: data.fetch.requested
[fetcher] Loading feedback for Soorma Hub (n=3)
[fetcher] Fetched 3 feedback entries
[fetcher] ✓ Completing with response_event=data.fetch.requested
```

**Analyzer:**
```
[analyzer] ▶ Received: analysis.requested
[analyzer] Task ID: task-456
[analyzer] Analyzing 3 entries for Soorma Hub  ← Data received!
[analyzer] Summary: 2 positive, 1 negative, avg=3.67
[analyzer] ✓ Completing with response_event=analysis.requested
```

**Reporter:**
```
[reporter] ▶ Received: report.requested
[reporter] Task ID: task-789
[reporter] Building report for Soorma Hub  ← Data received!
[reporter] Report generated (147 chars)
[reporter] ✓ Completing with response_event=report.requested
```

**Notice:** Clean, readable progress output - NO `INFO:__main__:` prefixes or HTTP requests!

### Client Terminal

```bash
python client.py

[client] Sending feedback analysis goal...
[client] Correlation ID: 4306472b-02d3-4f38-9b30-098d1ae46b37
[client] Waiting for response (timeout: 30s)...

[client] Received report:
{
  'status': 'success',
  'product': 'Soorma Hub',  ← Data from fetcher
  'report': 'Feedback Report for Soorma Hub\nSummary: Analyzed 3 feedback entries: 2 positive, 1 negative, 0 neutral (avg rating: 3.67)\nPositive: 2 | Negative: 1',  ← Data from all workers!
  'timestamp': '2026-02-22T20:27:42.501150'
}
```

**Success Indicator:** Report contains actual data (not "No summary available" or "Positive: 0").

### Experiment: Hot-Swap a Worker

**While system is running**, create a new fetcher with different event name:

```python
# new_fetcher.py
CUSTOM_FETCH_EVENT = EventDefinition(
    event_name="feedback.retrieve.v2",  # ← Different name!
    topic=EventTopic.ACTION_REQUESTS,
    description="Retrieve customer feedback entries from datastore...",  # ← Same capability
)
```

Start it, send another goal → **Planner discovers and uses the new event automatically!**

## Troubleshooting

### Logging Configuration

By default, you see **clean agent progress** (via `print`) and **ChoreographyPlanner internals** (via `logger.info`), with noisy SDK infrastructure suppressed.

**To see HTTP/infrastructure logs:**

Edit agent files (planner.py, fetcher.py, etc.) and comment out these lines:
```python
# Comment these out to see infrastructure logs:
# logging.getLogger("httpx").setLevel(logging.WARNING)
# logging.getLogger("soorma.registry.client").setLevel(logging.WARNING)
# logging.getLogger("soorma.agents.base").setLevel(logging.WARNING)
# ...etc
```

This shows:
- HTTP requests: `POST http://localhost:8081/v1/events "HTTP/1.1 200 OK"`
- Registry operations: `[RegistryClient] Event report.requested registered`
- Agent lifecycle: `✓ Registered feedback-reporter (feedback-reporter-33a99e9c)`
- Event streaming: `Connected to Event Service (connection_id: ...)`

**To silence ChoreographyPlanner internals** (just worker progress):
```python
# Add after basicConfig in any agent file:
logging.getLogger("soorma.ai.choreography").setLevel(logging.WARNING)
```

**To silence everything** (errors only):
```python
# Change this:
logging.basicConfig(level=logging.INFO, ...)

# To this:
logging.basicConfig(level=logging.ERROR, ...)
```

### Client Reports "No summary available" or "Positive: 0"

**Symptom:** Report is received but contains no actual data.

**Cause:** LLM not extracting data from previous responses.

**Solution:**
- Check planner logs for `[ChoreographyPlanner] Publishing event:` - does it show proper payload?
- Verify worker logs show data being received: `Analyzing 3 entries` (not `Analyzing 0 entries`)
- Ensure LLM prompt includes data extraction instructions (check `choreography.py`)

### "No actionable events found in Registry"

**Symptom:** Planner crashes immediately with RuntimeError.

**Cause:** Workers haven't registered events with Registry Service yet.

**Solution:**
- **Wait for workers to start first** - `start.sh` does this automatically
- Check Registry has events: `curl http://localhost:8081/v1/events | jq '.count'` (should be 6)
- Verify workers show `"Registered event: ..."` in logs

### Data Not Flowing Between Workers

**Symptom:** First worker succeeds but second worker gets empty data.

**Cause:** LLM not forwarding data, or field name mismatch.

**Solution:**
- Check event schemas align: fetcher outputs `feedback`, analyzer inputs `feedback` (same field name)
- Verify planner logs show payload in publish: `Publishing event: ... data: {"product": "...", "feedback": [...]}`
- LLM needs explicit prompt about data forwarding (see `choreography.py` prompt)

### Registry Service Returns Empty on Topic Filter

**Symptom:** `Querying events with topic=action-requests` returns `{"events":[],"count":0}`.

**Cause:** Old database schema (pre-v0.7.x) doesn't support same event name on different topics.

**Solution:**
- Delete old database: `rm services/registry/registry.db`
- Restart Registry Service (will create DB with composite unique constraint)
- Restart workers to re-register events

### Workers Receive Wrong Event Names

**Symptom:** Worker expects `data.fetch.requested` but planner publishes `data.fetched`.

**Cause:** LLM hallucinating event names or old documentation.

**Solution:**
- Check worker event definitions use consistent naming (request/response same name)
- Verify Registry has correct event names: `curl http://localhost:8081/v1/events | jq '.events[].eventName'`
- LLM should only use event names from Registry query (validation in `choreography.py`)

### Client Timeout

**Standard checks:**
- ✅ All services running: `soorma dev --build`
- ✅ All workers started and registered
- ✅ Planner started after workers
- ✅ LLM credentials configured (`OPENAI_API_KEY`)
- ✅ Check planner logs for LLM errors or validation failures

### LLM Returning Invalid JSON

**Symptom:** `ValidationError: 1 validation error for PlannerDecision`

**Cause:** LLM not following schema, missing required fields.

**Solution:**
- Check which field is missing in error message
- Verify prompt includes examples for that action type (PUBLISH, COMPLETE, etc.)
- Some models need explicit JSON schema in system message (already included)

## Technical Deep Dive

### What Makes This Possible?

**1. Registry Service with Composite Unique Constraint**

```sql
-- Allows same event name on different topics
CREATE UNIQUE INDEX uix_event_name_topic ON events (event_name, topic);
```

This enables the same-name pattern: `data.fetch.requested` on both `action-requests` and `action-results`.

**2. Dynamic Event Discovery**

```python
# Inside ChoreographyPlanner.reason_next_action()
events = await context.toolkit.discover_actionable_events(topic=EventTopic.ACTION_REQUESTS)
# Returns: [EventDefinition with schemas, descriptions, etc.]

# LLM receives rich descriptions
event_descriptions = "\n".join([
    f"- {e.event_name}: {e.description}" 
    for e in events
])
```

**3. Schema-Driven Data Extraction**

LLM prompt includes event schemas and explicit instructions:

```
CRITICAL RULES FOR PUBLISH ACTIONS:
1. Set response_event to the SAME event name as event_type
2. ALWAYS extract data from 'Additional Context' > 'event_data'
3. Look at the event schema's required fields and populate them from event_data
4. Copy forward all relevant fields from previous responses

Example: If event_data contains {"product": "XYZ", "feedback": [...]}
         and you're publishing analysis.requested which needs product and feedback,
         then data field MUST be: {"product": "XYZ", "feedback": [...]}
```

**4. Correlation ID Routing**

Single correlation_id flows through entire pipeline:
- Client sets it on initial goal
- Planner preserves it on all worker requests
- Event Bus routes responses back to planner using correlation_id
- Client receives final result matched by correlation_id

**5. Two-Layer SDK Architecture**

Planner uses high-level wrappers (never direct service clients):

```python
# ✅ CORRECT: Agent code uses wrappers
await context.toolkit.discover_actionable_events(...)
await context.bus.publish(event_type, data, ...)
await context.memory.store_plan_context(...)

# ❌ WRONG: Never import service clients in agent code
from soorma.registry.client import RegistryClient  # Forbidden!
```

This abstraction enables testing, caching, and future service replacements.

## Related Documentation

- **[AUTONOMOUS_DISCOVERY.md](AUTONOMOUS_DISCOVERY.md)** - Deep dive on capability matching
- **[../../docs/ARCHITECTURE_PATTERNS.md](../../docs/ARCHITECTURE_PATTERNS.md)** - Platform patterns (auth, events, multi-tenancy)
- **[../../docs/memory_system/](../../docs/memory_system/)** - Plan and task context storage
- **[../../docs/event_system/](../../docs/event_system/)** - Event choreography patterns

## Next Steps

1. **Experiment with hot-swapping** - Create a new worker with different event name but same capability
2. **Try different system prompts** - Change business logic without touching workflow code
3. **Add a new pipeline stage** - Insert a validation worker between analyzer and reporter (planner discovers it automatically)
4. **Test with different LLMs** - Try Claude, Gemini, or local models via litellm
5. **Build your own choreography** - Apply this pattern to your domain (order processing, content moderation, etc.)

---

**The autonomous choreography pattern represents a fundamental shift:** From hardcoded workflows to truly adaptive, LLM-driven orchestration where workers are hot-swappable plugins and the planner is just a thin reasoning layer.
