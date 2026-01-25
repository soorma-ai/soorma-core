# Soorma Examples - Learning Path

This directory contains progressively more complex examples demonstrating Soorma's capabilities. Each example focuses on one core concept and builds on previous examples.

## 🎯 Quick Start

**New to Soorma?** Start with [01-hello-world](./01-hello-world/) and follow the sequence below.

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
<td><!--a href="./08-planner-worker-basic/"-->08-planner-worker-basic<!--/a--><br>(coming soon)</td>
<td>
• Trinity pattern (Planner-Worker-Tool)<br>
• Goal decomposition<br>
• Task execution
</td>
<td>20 min</td>
<td>01-hello-world</td>
</tr>

<tr>
<td><!--a href="./09-app-research-advisor/"-->09-app-research-advisor<!--/a--><br>(coming soon)</td>
<td>
• Autonomous Choreography pattern<br>
• ChoreographyPlanner SDK class<br>
• Multi-agent orchestration<br>
• Full application example
</td>
<td>30 min</td>
<td>03-events-structured<br>04-memory-working</td>
</tr>

<tr>
<td><!--a href="./10-multi-turn-conversation/"-->10-multi-turn-conversation<!--/a--><br>(coming soon)</td>
<td>
• Stateful conversations<br>
• Follow-up handling<br>
• Context preservation
</td>
<td>20 min</td>
<td>06-memory-episodic<br>08-planner-worker-basic</td>
</tr>
</table>

---

## Pattern Catalog

**"I want to..."** → Use this pattern → See this example

| Goal | Pattern | Example |
|------|---------|---------|
| Build a simple reactive agent | Event Subscriber | [02-events-simple](./02-events-simple/) |
| Let an LLM choose the next action | Structured Events + LLM | [03-events-structured](./03-events-structured/) |
| Share state across agents in a workflow | Working Memory | [04-memory-working](./04-memory-working/) |
| Store facts for RAG/knowledge retrieval | Semantic Memory | [05-memory-semantic](./05-memory-semantic/) |
| Build multi-agent chatbot with all memory types | Multi-Agent + All Memory Types | [06-memory-episodic](./06-memory-episodic/) |
| Discover and use tools at runtime | Tool Discovery | 07-tool-discovery (coming soon) |
| Break down goals into tasks | Planner-Worker Pattern | 08-planner-worker-basic (coming soon) |
| Build a fully autonomous multi-agent system | Autonomous Choreography | 09-app-research-advisor (coming soon) |
| Handle multi-turn conversations | Stateful Conversation | 10-multi-turn-conversation (coming soon) |

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
- **Design Patterns**: See [../docs/DESIGN_PATTERNS.md](../docs/DESIGN_PATTERNS.md) for agent patterns
- **Memory Patterns**: See [../docs/MEMORY_PATTERNS.md](../docs/MEMORY_PATTERNS.md) for memory usage guidance
- **Event Patterns**: See [../docs/EVENT_PATTERNS.md](../docs/EVENT_PATTERNS.md) for event-driven architecture
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
5. 09-app-research-advisor (coming soon) - Full autonomous system

### Path 3: Memory Deep Dive (90 minutes)
1. [01-hello-world](./01-hello-world/) - Basics
2. [02-events-simple](./02-events-simple/) - Event pub/sub
3. [04-memory-working](./04-memory-working/) - Workflow state (simpler, learn first)
4. [03-events-structured](./03-events-structured/) - LLM event selection
5. [05-memory-semantic](./05-memory-semantic/) - RAG/Knowledge (requires LLM routing)
6. [06-memory-episodic](./06-memory-episodic/) - Multi-agent chatbot combining all three memory types

### Path 4: Complete Journey (Coming Soon)
Once all examples are available, work through examples 01 → 10 in sequence for comprehensive understanding.

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
