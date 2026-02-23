# Autonomous Event Discovery Pattern

This example demonstrates **true autonomous choreography** where the planner discovers and orchestrates workers based on their **capabilities**, not hardcoded event names.

## How It Works

### 1. Workers Register Rich Capability Descriptions

Instead of minimal descriptions:
```python
# ❌ OLD: Minimal description
EventDefinition(
    event_name="data.fetch.requested",
    description="Request to fetch data"  # Not helpful for LLM reasoning
)
```

Workers now register capability-rich descriptions:
```python
# ✅ NEW: Capability-rich description
EventDefinition(
    event_name="data.fetch.requested",
    description="Retrieve customer feedback entries from datastore. Use when you need to load raw feedback data for a product. Returns a collection of feedback entries with ratings and comments."
)
```

### 2. Planner Describes Logical Flow (Not Specific Events)

Instead of hardcoding event names:
```python
# ❌ OLD: Hardcoded event orchestration
system_instructions=(
    "1) Publish data.fetch.requested\n"
    "2) Publish analysis.requested\n"
    "3) Publish report.requested\n"
)
```

Planner describes **WHAT** capabilities are needed:
```python
# ✅ NEW: Logical workflow description
system_instructions=(
    "LOGICAL WORKFLOW:\n"
    "1. DATA RETRIEVAL: First, you need raw feedback data from the datastore\n"
    "   - Look for events that retrieve/fetch/load customer feedback\n"
    "2. ANALYSIS: Once you have raw data, extract insights\n"
    "   - Look for events that analyze/process sentiment\n"
    "3. REPORTING: Finally, format the insights into a report\n"
    "   - Look for events that generate/format reports\n"
)
```

### 3. LLM Matches Capabilities to Available Events

The ChoreographyPlanner automatically:
1. Queries Registry for available events in `ACTION_REQUESTS` topic
2. Builds a prompt with event descriptions
3. LLM reasons: "I need to retrieve feedback data... which event does that?"
4. LLM matches: "DATA RETRIEVAL → 'Retrieve customer feedback entries' → data.fetch.requested"
5. LLM publishes the discovered event

### 4. True Autonomy: Add Workers Without Code Changes

**You can now add new workers with different event names and the planner will discover them!**

Example: Replace the fetcher with a new worker:

```python
# NEW WORKER: Uses completely different event name
NEW_EVENT = EventDefinition(
    event_name="feedback.load",  # Different name!
    topic=EventTopic.ACTION_REQUESTS,
    description="Retrieve customer feedback entries from datastore. Use when you need to load raw feedback data for a product. Returns a collection of feedback entries with ratings and comments.",
    # Same capability description!
)

@worker.on_task("feedback.load")  # Different event name!
async def handle_load(task, context):
    # Same implementation
    pass
```

**The planner will discover and use `feedback.load` automatically!** No code changes needed in planner.py.

## Why This Matters

### Before (Hardcoded Orchestration)
```python
# Planner knows exactly what to call
await bus.publish("data.fetch.requested", ...)
await bus.publish("analysis.requested", ...)
await bus.publish("report.requested", ...)
```
**Problem:** Adding a new worker or renaming events requires updating planner code.

### After (Autonomous Discovery)
```python
# Planner discovers what's available
events = await registry.discover_events(ACTION_REQUESTS)
llm_decision = await llm.reason(logical_flow, events)
await bus.publish(llm_decision.event_type, ...)  # Discovered dynamically!
```
**Benefit:** Add workers with any event names - planner discovers based on capabilities.

## Extension Examples

### Add a Premium Analyzer
```python
PREMIUM_ANALYSIS_EVENT = EventDefinition(
    event_name="sentiment.deep_analyze",  # Different name
    description="Analyze sentiment and patterns in customer feedback using advanced ML models. Use when you have raw feedback data and need to extract insights like positive/negative sentiment counts and summary. Returns analysis with sentiment breakdown and confidence scores."
)
```

The planner will discover this as an alternative to `analysis.requested` and might choose it based on context (e.g., "customer tier: premium" in custom_context).

### Add a Video Feedback Fetcher
```python
VIDEO_FETCH_EVENT = EventDefinition(
    event_name="media.video_feedback.retrieve",
    description="Retrieve customer video feedback from media storage. Use when you need to load video feedback content for analysis. Returns video URLs and metadata."
)
```

Future enhancement: The planner could discover this and use it when the goal mentions "video feedback" in the objective.

## Testing Autonomous Discovery

### Scenario: Rename All Events
1. Rename `data.fetch.requested` → `feedback.retrieve`
2. Update worker registration and handler: `@worker.on_task("feedback.retrieve")`
3. **Do NOT change planner.py at all**
4. Run the example
5. ✅ Planner discovers and uses `feedback.retrieve` based on description match

### Scenario: Multiple Workers for Same Capability
1. Register both `data.fetch.requested` and `feedback.load` with similar descriptions
2. LLM will choose one (might vary based on wording, context, or randomness)
3. Both work because they implement the same capability

## Architecture Benefits

1. **Extensibility**: Add new workers without touching planner code
2. **Maintainability**: Event names can change without breaking orchestration
3. **Flexibility**: LLM can choose between multiple workers offering similar capabilities
4. **Discoverability**: New developers see what capabilities exist by reading Registry
5. **Evolution**: Workers can be replaced/upgraded without orchestration changes

## Key Takeaway

**The planner orchestrates based on WHAT workers can do (capabilities), not WHO they are (event names).**

This is the essence of autonomous choreography powered by LLM reasoning.
