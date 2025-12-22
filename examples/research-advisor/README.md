# Generic Research & Advice Agent System

This example demonstrates an advanced "Choreography" pattern using the Soorma SDK.
It showcases:
1. **Dynamic Discovery**: The Planner finds workers via the Registry.
2. **Verification Loop**: A "Fact Checker" agent critiques the "Drafter" agent's output.
3. **Event Choreography**: All communication happens via the Event Bus.
4. **LLM Orchestration**: The Planner uses an LLM to decide the next step based on available events.

For a deep dive into the design, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Architecture

- **AgentOrchestrator (Planner)**: Receives user goals and orchestrates the workflow.
- **WebResearcher (Worker)**: Performs web research using DuckDuckGo and summarizes findings.
- **ContentDrafter (Worker)**: Drafts responses based on research using LLM.
- **FactChecker (Worker)**: Validates content against source material.

### Event-Driven Architecture

The workflow is no longer a single procedural script. It is a choreography of discrete events.
- **Planner**: Listens for `GOAL`, `RESEARCH_RESULT`, `ADVICE_RESULT`, `VALIDATION_RESULT`.
- **Researcher**: Listens for `RESEARCH_REQUEST` -> Emits `RESEARCH_RESULT`.
- **Drafter**: Listens for `DRAFT_REQUEST` -> Emits `DRAFT_RESULT`.
- **Validator**: Listens for `VALIDATION_REQUEST` -> Emits `VALIDATION_RESULT`.

## Setup

1. Ensure you have the Soorma Platform running (Registry, Redis, etc.).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   (Note: `soorma-common` and `soorma-sdk` are assumed to be installed in your environment)

## LLM Configuration

By default, the agents run in **Mock Mode** using simulated responses. To enable real LLM capabilities (using OpenAI or Anthropic), set the corresponding environment variables before running the agents.

- **OpenAI**: `export OPENAI_API_KEY=sk-...`
- **Anthropic**: `export ANTHROPIC_API_KEY=sk-ant-...`

If these keys are present, the `Planner`, `Drafter`, and `Validator` agents will use `litellm` to generate real responses. The `Researcher` uses `ddgs` for real web search if keys are present.

## Usage

This example uses standalone agents. You need to run each agent in a separate terminal window.

**Terminal 1: Researcher**
```bash
python3 researcher.py
```

**Terminal 2: Drafter**
```bash
# Optional: export OPENAI_API_KEY=...
python3 advisor.py
```

**Terminal 3: Validator**
```bash
# Optional: export OPENAI_API_KEY=...
python3 validator.py
```

**Terminal 4: Planner**
```bash
# Optional: export OPENAI_API_KEY=...
python3 planner.py
```

**Terminal 5: Client (User)**
```bash
python3 client.py
```

## Workflow

1. **Client** publishes `agent.goal.submitted`.
2. **Planner** receives goal, asks LLM, decides to request research.
3. **Planner** publishes `agent.research.requested`.
4. **Researcher** receives request, searches web, publishes `agent.research.completed`.
5. **Planner** receives research, asks LLM, decides to request draft.
6. **Planner** publishes `agent.draft.requested`.
7. **Drafter** receives request, drafts response, publishes `agent.draft.completed`.
8. **Planner** receives draft, asks LLM, decides to request validation.
9. **Planner** publishes `agent.validation.requested`.
10. **Validator** receives request, validates, publishes `agent.validation.completed`.
11. **Planner** receives validation result.
    - If APPROVED: Publishes `agent.goal.fulfilled`.
    - If REJECTED: Publishes `agent.draft.requested` (loop back).
12. **Client** receives `agent.goal.fulfilled` and prints the result.
