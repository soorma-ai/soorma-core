# Research Advisor: Autonomous Choreography with LLM Reasoning

This example demonstrates **Autonomous Choreography** using the Soorma Platform and DisCo (Distributed Cognition) protocol. It showcases how AI agents can coordinate complex workflows without hardcoded rules, using LLM reasoning over dynamically discovered event metadata.

## Key Concepts

### 🎭 Autonomous Choreography (vs. Orchestration)
Traditional orchestration hardcodes workflow logic: "after research, do draft, then validate." This is brittle and requires code changes when workflows evolve.

**Autonomous Choreography** takes a different approach:
- Agents register their capabilities as **events** with rich metadata (description, purpose, schema)
- A Planner agent **discovers** available events from the Registry at runtime
- An **LLM reasons** about event metadata to decide the next action
- The workflow emerges from LLM decisions, not hardcoded rules

### 🧠 LLM Reasoning Engine
The Planner doesn't contain workflow rules. Instead, it:
1. Receives a trigger (goal, result, validation)
2. Queries the Registry for available events
3. Presents event metadata to an LLM
4. Lets the LLM decide which event to publish based on:
   - Event descriptions and purposes
   - Current workflow state
   - Progress toward the user's goal

### 🔌 Circuit Breakers
Autonomous systems can run away (infinite loops, stuck states). This example includes:
- **Max Actions Limit**: Caps total actions per goal (default: 10)
- **Vague Result Detection**: Catches when LLM returns meta-descriptions instead of actual content

Future versions will add a **Tracker Service** for:
- Timeout detection
- Lost event recovery
- Human intervention points
- Workflow observability

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│   Planner    │────▶│  Registry   │
│  (Goals)    │     │ (LLM Brain)  │◀────│  (Events)   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │ discovers & publishes
                           ▼
┌──────────────────────────────────────────────────────┐
│                    Event Bus                         │
└──────────────────────────────────────────────────────┘
        │              │              │
        ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Researcher  │ │   Advisor   │ │  Validator  │
│  (Worker)   │ │  (Worker)   │ │  (Worker)   │
└─────────────┘ └─────────────┘ └─────────────┘
```

### Agents

| Agent | Role | Events |
|-------|------|--------|
| **Planner** | LLM-powered orchestrator. Discovers events, reasons about next steps | Consumes: goal, results. Produces: requests, fulfilled |
| **Researcher** | Web search using DuckDuckGo | `research.requested` → `research.completed` |
| **Advisor** | Drafts responses using LLM | `draft.requested` → `draft.completed` |
| **Validator** | Fact-checks drafts against research | `validation.requested` → `validation.completed` |

## Setup

1. **Start Soorma Platform** (Registry + Event Bus):
   ```bash
   soorma dev
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure LLM** (optional - uses mocks without keys):
   
   The example supports multiple LLM providers via LiteLLM. Set any one of these API keys:
   
   ```bash
   # OpenAI (default)
   export OPENAI_API_KEY=sk-...
   
   # Anthropic
   export ANTHROPIC_API_KEY=sk-ant-...
   
   # Google/Gemini
   export GOOGLE_API_KEY=...
   # or
   export GEMINI_API_KEY=...
   
   # Azure OpenAI
   export AZURE_API_KEY=...
   
   # Together AI
   export TOGETHER_API_KEY=...
   
   # Groq
   export GROQ_API_KEY=...
   ```
   
   The agents automatically detect which key is available and use the appropriate model. See `llm_utils.py` for model mappings.

## Running the Example

Start each agent in a separate terminal:

```bash
# Terminal 1: Researcher
python researcher.py

# Terminal 2: Advisor (Drafter)
python advisor.py

# Terminal 3: Validator
python validator.py

# Terminal 4: Planner (LLM Brain)
python planner.py

# Terminal 5: Client
python client.py
```

## Example Flow

```
User: "Compare NATS vs Google Pub/Sub for event-driven architecture"

📋 Planner receives GOAL
   🔍 Discovers 4 events from Registry
   🤖 LLM reasons: "Need information first. Research event gathers data."
   📤 Publishes: agent.research.requested

📋 Planner receives RESEARCH RESULT
   🤖 LLM reasons: "Have research. Draft event creates user response."
   📤 Publishes: agent.draft.requested

📋 Planner receives DRAFT RESULT  
   🤖 LLM reasons: "Have draft. Validation event checks accuracy."
   📤 Publishes: agent.validation.requested

📋 Planner receives VALIDATION RESULT (approved)
   🤖 LLM reasons: "Draft validated. Goal can be fulfilled."
   ✅ Completes with validated draft
```

## Known Limitations

- **No Tracker Service**: Lost events or timeouts are not detected
- **In-Memory State**: Workflow state is lost on restart  
- **Single Planner**: No high-availability or load balancing

A future example will introduce a **Tracker** agent for observability and reliability.

## Deep Dive

See [ARCHITECTURE.md](ARCHITECTURE.md) for:
- Why we avoid hardcoded workflow rules
- The DisCo protocol and dynamic discovery
- Prompt engineering for autonomous agents
- Circuit breaker implementations
- Planned Tracker service architecture
