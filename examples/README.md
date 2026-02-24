# Soorma Examples - Learning Path

This directory contains progressively more complex examples demonstrating Soorma's capabilities. Each example focuses on one core concept and builds on previous examples.

## 🎯 Quick Start

**New to Soorma?** Start with [01-hello-world](./01-hello-world/) or [01-hello-tool](./01-hello-tool/) and follow the sequence below.

**Looking for something specific?** See the [Pattern Catalog](#pattern-catalog) below.

## 📚 Learning Path

### Foundations

<table>
<tr>
<th>Example</th>
<th>Concepts</th>
<th>Time</th>
<th>Prerequisites</th>
</tr>

<tr>
<td><a href="./01-hello-world/">01-hello-world</a></td>
<td>
• Basic agent lifecycle<br>
• Worker registration<br>
• Event handling with decorators<br>
• action-requests / action-results topics
</td>
<td>10 min</td>
<td>None</td>
</tr>

<tr>
<td><a href="./01-hello-tool/">01-hello-tool</a></td>
<td>
• Tool pattern (stateless, synchronous)<br>
• Multiple @on_invoke() handlers<br>
• Caller-specified response_event<br>
• action-requests / action-results topics
</td>
<td>5 min</td>
<td>None</td>
</tr>

<tr>
<td><a href="./02-events-simple/">02-events-simple</a></td>
<td>
• Event publishing<br>
• Event subscription<br>
• Simple pub/sub pattern<br>
• business-facts topic for domain events
</td>
<td>10 min</td>
<td>01-hello-world</td>
</tr>

<tr>
<td><a href="./03-events-structured/">03-events-structured</a></td>
<td>
• Rich event metadata<br>
• LLM-based event selection<br>
• Structured events for reasoning<br>
• Dynamic event discovery<br>
<em>Requires: litellm, openai</em>
</td>
<td>15 min</td>
<td>02-events-simple</td>
</tr>
</table>

### Memory Systems

<table>
<tr>
<th>Example</th>
<th>Concepts</th>
<th>Time</th>
<th>Prerequisites</th>
</tr>

<tr>
<td><a href="./04-memory-working/">04-memory-working</a></td>
<td>
• Working memory<br>
• Plan-scoped shared state<br>
• WorkflowState helper
</td>
<td>15 min</td>
<td>01-hello-world</td>
</tr>

<tr>
<td><a href="./05-memory-semantic/">05-memory-semantic</a></td>
<td>
• Semantic memory (RAG)<br>
• LLM-based routing<br>
• Knowledge storage with embeddings<br>
• Grounded answer generation<br>
<em>Requires: litellm, openai</em>
</td>
<td>20 min</td>
<td>03-events-structured</td>
</tr>

<tr>
<td><a href="./06-memory-episodic/">06-memory-episodic</a></td>
<td>
• All three memory types combined<br>
• Multi-agent chatbot (Router, RAG, Concierge, Knowledge Store)<br>
• LLM-based intent classification<br>
• Dual-context RAG<br>
• Session management<br>
<em>Requires: litellm, openai</em>
</td>
<td>30 min</td>
<td>04-memory-working<br>05-memory-semantic</td>
</tr>
</table>

### Advanced Patterns

<table>
<tr>
<th>Example</th>
<th>Concepts</th>
<th>Time</th>
<th>Prerequisites</th>
</tr>

<tr>
<td><!--a href="./07-tool-discovery/"-->07-tool-discovery<!--/a--><br>(coming soon)</td>
<td>
• Dynamic capability discovery<br>
• Tool registration<br>
• Runtime tool binding
</td>
<td>20 min</td>
<td>01-hello-world</td>
</tr>

<tr>
<td><a href="./08-worker-basic/">08-worker-basic</a></td>
<td>
• Worker pattern (async, stateful)<br>
• TaskContext with persistence<br>
• Sequential and parallel delegation<br>
• Result aggregation (fan-out/fan-in)<br>
• action-requests / action-results topics
</td>
<td>15 min</td>
<td>01-hello-world<br>02-events-simple</td>
</tr>

<tr>
<td><a href="./09-planner-basic/">09-planner-basic</a></td>
<td>
• Planner pattern (Stage 4 Phase 1)<br>
• @on_goal() and @on_transition() decorators<br>
• PlanContext state machine orchestration<br>
• GoalContext wrapper<br>
• 3-state workflow with correlation routing
</td>
<td>15 min</td>
<td>01-hello-world<br>08-worker-basic</td>
</tr>

<tr>
<td><a href="./10-choreography-basic/">10-choreography-basic</a></td>
<td>
• ChoreographyPlanner pattern (Stage 4 Phase 2)<br>
• Autonomous LLM-based orchestration<br>
• Event discovery from Registry<br>
• Multi-agent choreography (Planner + 3 Workers)<br>
• Tracker Service integration for observability<br>
<em>Requires: litellm, openai</em>
</td>
<td>20 min</td>
<td>09-planner-basic<br>03-events-structured</td>
</tr>

<tr>
<td><!--a href="./11-app-research-advisor/"-->11-app-research-advisor<!--/a--><br>(coming soon)</td>
<td>
• Full autonomous research application<br>
• Web scraping with Playwright<br>
• Fact-checking pipeline<br>
• Citation management<br>
• Tracker Service integration<br>
<em>Requires: litellm, openai, playwright</em>
</td>
<td>45 min</td>
<td>10-choreography-basic<br>06-memory-episodic</td>
</tr>

<tr>
<td><!--a href="./10-planner-worker-tool/"-->DEPRECATED: 10-planner-worker-tool<!--/a--></td>
<td>
<em>Merged into 10-choreography-basic</em>
</td>
<td>-</td>
<td>-</td>
</tr>

<tr>
<td><!--a href="./12-multi-turn-conversation/"-->12-multi-turn-conversation<!--/a--><br>(coming soon)</td>
<td>
• Stateful conversations<br>
• Follow-up handling<br>
• Context preservation
</td>
<td>20 min</td>
<td>06-memory-episodic<br>10-choreography-basic</td>
</tr>
</table>

---

## Pattern Catalog

**"I want to..."** → Use this pattern → See this example

| Goal | Pattern | Example |
|------|---------|---------|
| Run a simple tool (stateless function) | Tool Pattern | [01-hello-tool](./01-hello-tool/) |
| Build a simple reactive agent | Event Subscriber | [02-events-simple](./02-events-simple/) |
| Let an LLM choose the next action | Structured Events + LLM | [03-events-structured](./03-events-structured/) |
| Share state across agents in a workflow | Working Memory | [04-memory-working](./04-memory-working/) |
| Store facts for RAG/knowledge retrieval | Semantic Memory | [05-memory-semantic](./05-memory-semantic/) |
| Build multi-agent chatbot with all memory types | Multi-Agent + All Memory Types | [06-memory-episodic](./06-memory-episodic/) |
| Discover and use tools at runtime | Tool Discovery | 07-tool-discovery (coming soon) |
| Handle async tasks with delegation | Worker Pattern | [08-worker-basic](./08-worker-basic/) |
| Orchestrate tasks with state machines | Planner Pattern | [09-planner-basic](./09-planner-basic/) |
| Build autonomous multi-agent systems | Choreography Pattern | [10-choreography-basic](./10-choreography-basic/) |
| Build production applications | Full Applications | 11-app-research-advisor (coming soon) |
| Handle multi-turn conversations | Stateful Conversation | 12-multi-turn-conversation (coming soon) |

---

## Running Examples

### Prerequisites

Before running examples, complete the initial setup:

```bash
# Clone the repository (if not already done)
git clone https://github.com/soorma-ai/soorma-core.git
cd soorma-core

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the SDK from local source (recommended during pre-launch)
pip install -e sdk/python
```

**For examples using LLMs** (03, 05, 06, research-advisor), also install:

```bash
pip install litellm openai
```

> **Note:** Examples 01 and 02 work with just `soorma-core`. Examples 03+ require LLM libraries for reasoning capabilities.

### Step 1: Start Platform Services (One Time)

From the `soorma-core` root directory:

```bash
soorma dev --build
```

The `--build` flag builds services from your local code instead of pulling Docker images. **Leave this running** - you can use it for all examples.

### Step 2: Run an Example

Each example provides a `start.sh` script that manages its agents:

```bash
cd examples/01-hello-world
./start.sh
```

This will start the example's agent(s) and provide instructions for running the client.

**Manual Steps** (if you prefer):

```bash
# After starting platform services above...

# Terminal 2: Start the agent
cd examples/01-hello-world
python worker.py

# Terminal 3: Run the client
python client.py
```

---

## Additional Resources

- **Architecture**: See [../ARCHITECTURE.md](../ARCHITECTURE.md) for platform service details
- **Agent Patterns**: See [../docs/agent_patterns/README.md](../docs/agent_patterns/README.md) for Tool, Worker, Planner models
- **Event System**: See [../docs/event_system/README.md](../docs/event_system/README.md) for event-driven architecture
- **Memory System**: See [../docs/memory_system/README.md](../docs/memory_system/README.md) for CoALA framework and memory types
- **Discovery**: See [../docs/discovery/README.md](../docs/discovery/README.md) for Registry and capability discovery
- **AI Assistant Guide**: See [../docs/AI_ASSISTANT_GUIDE.md](../docs/AI_ASSISTANT_GUIDE.md) for using examples with Copilot/Cursor
- **Blog**: Visit our [blog](https://soorma.ai/blog) for deep dives and use cases

---

## 🎓 Recommended Learning Paths

### Path 1: Quick Start (30 minutes)
1. [01-hello-world](./01-hello-world/) - Get your first agent running
2. [02-events-simple](./02-events-simple/) - Learn event pub/sub
3. [03-events-structured](./03-events-structured/) - LLM event selection

### Path 2: LLM-Powered Agents (70 minutes)
1. [01-hello-world](./01-hello-world/) - Basics
2. [03-events-structured](./03-events-structured/) - LLM event selection
3. [04-memory-working](./04-memory-working/) - State management
4. [06-memory-episodic](./06-memory-episodic/) - Multi-agent LLM chatbot
5. [10-choreography-basic](./10-choreography-basic/) - Autonomous choreography with ChoreographyPlanner
6. 11-app-research-advisor (coming soon) - Full research application

### Path 3: Memory Deep Dive (90 minutes)
1. [01-hello-world](./01-hello-world/) - Basics
2. [02-events-simple](./02-events-simple/) - Event pub/sub
3. [04-memory-working](./04-memory-working/) - Workflow state (simpler, learn first)
4. [03-events-structured](./03-events-structured/) - LLM event selection
5. [05-memory-semantic](./05-memory-semantic/) - RAG/Knowledge (requires LLM routing)
6. [06-memory-episodic](./06-memory-episodic/) - Multi-agent chatbot combining all three memory types

### Path 4: Complete Journey (Coming Soon)
Once all examples are available, work through examples 01 → 11 in sequence for comprehensive understanding.

---

## Tips for Success

- **One concept at a time**: Each example focuses on a single capability
- **Run the code**: Examples are meant to be executed, not just read
- **Check prerequisites**: Some examples build on concepts from earlier ones
- **Read the READMEs**: Each example has detailed explanations and walkthroughs
- **Experiment**: Modify the examples to solidify your understanding

---

## Getting Help

- **Issues**: Found a bug or unclear documentation? [Open an issue](https://github.com/soorma-ai/soorma-core/issues)
- **Questions**: Join our [Discord community](https://discord.gg/soorma) or [Discussions](https://github.com/soorma-ai/soorma-core/discussions)
- **Contributing**: See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines

---

## Example Template

Each example follows this structure:

```
XX-example-name/
├── README.md              # Concept overview, walkthrough, instructions
├── main_script.py         # Primary demonstration code
├── additional_script.py   # Supporting code if needed
└── client.py             # Script to trigger the workflow (if applicable)
```

Every README includes:
- **Concepts**: What you'll learn
- **Difficulty**: Beginner | Intermediate | Advanced
- **Prerequisites**: Required prior examples
- **Code Walkthrough**: Step-by-step explanation
- **Running Instructions**: How to execute the example
- **Key Takeaways**: What to remember
- **Next Steps**: Where to go next in your learning journey

---

## Using Examples with AI Assistants

These examples are designed to serve as **context** for AI coding assistants like GitHub Copilot and Cursor. See [AI Assistant Guide](../docs/AI_ASSISTANT_GUIDE.md) for details on:

- How to reference examples when prompting Copilot/Cursor
- Patterns for generating new agents based on examples
- Best practices for AI-assisted agent development
- Example prompts that work well with these examples

**Quick Tip:** When asking Copilot/Cursor to create an agent, reference the specific example:
```
"Create a worker agent similar to examples/01-hello-world that handles order.created events"
```

---

---

**Happy Learning! 🚀**
