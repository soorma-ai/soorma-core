# AI Assistant Guide

**How to Use Soorma Examples with GitHub Copilot & Cursor**

**Last Updated:** February 21, 2026

---

## 🚨 IMPORTANT: Start Every Implementation Session Correctly

**Before implementing any feature or Action Plan**, you MUST use the [Session Initialization Template](SESSION_INITIALIZATION.md).

**Why?** This enforces:
- ✅ TDD workflow (tests FIRST, implementation second)
- ✅ Constitutional compliance (AGENT.md requirements)
- ✅ Architecture validation (two-layer SDK pattern)
- ✅ No scope creep (sticks to Action Plan)

**Quick Link:** **[📋 SESSION_INITIALIZATION.md](SESSION_INITIALIZATION.md)** ← Copy/paste this at session start

**Failure to use this template will result in:**
- ❌ Implementation-first code (violates TDD)
- ❌ Missing tests or post-facto testing
- ❌ Architecture violations (service client leaks)
- ❌ Hours of refactoring later

**See:** [Session Initialization Guide](SESSION_INITIALIZATION.md) for the complete template and workflow.

---

## Overview

Soorma examples are specifically designed to serve as **context** for AI coding assistants. This guide shows you how to effectively use them with GitHub Copilot, Cursor, and similar tools to generate production-quality agents.

---

## Quick Start

### For Cursor Users

1. **Open the soorma-core workspace** in Cursor
2. **Reference examples in your prompts:**
   ```
   @examples/01-hello-world Create a worker agent that processes order.created events
   ```
3. **Cursor will use the example as context** to generate similar code

### For GitHub Copilot Users

1. **Open example files** you want to use as reference
2. **Keep them in tabs** while working
3. **Start typing** - Copilot will suggest code based on open files
4. **Use inline chat** with explicit references:
   ```
   #file:examples/01-hello-world/worker.py Create similar worker for orders
   ```

---

## Effective Prompting Patterns

### Pattern 1: Reference Specific Examples

**❌ Vague:**
```
Create a Soorma agent
```

**✅ Specific:**
```
Create a worker agent similar to examples/01-hello-world/worker.py that:
- Handles product.created events
- Validates product data
- Publishes product.validated events
```

### Pattern 2: Combine Multiple Examples

```
Create an agent that combines:
- Event handling from examples/01-hello-world
- Multiple event types from examples/02-events-simple
```

### Pattern 3: Specify Pattern by Name

```
Create a Worker Pattern agent (see examples/01-hello-world) that processes 
invoice events and stores them in semantic memory (see examples/04-memory-semantic)
```

### Pattern 4: Reference Pattern Catalog

```
I want to build a system that reacts to customer support tickets. 
Which example should I use? See examples/README.md pattern catalog.

[AI will recommend examples/02-events-simple or examples/03-events-structured]

Now create a support ticket handler based on that example.
```

---

## Example-Specific Prompts

### Using 01-hello-world (Basic Worker)

**Prompt Template:**
```
Using examples/01-hello-world/worker.py as a reference, create a worker agent that:

Agent Name: [your-agent-name]
Capabilities: [list capabilities]
Events Consumed:
  - [event.type]
Events Produced:
  - [event.type]
Events to Handle:
  - [event.type]: [what to do]
  - [event.type]: [what to do]
```

**Example Prompt:**
```
Using examples/01-hello-world/worker.py as a reference, create a worker agent that:

Agent Name: invoice-processor
Capabilities: [invoice-processing, validation]
Events Consumed:
  - invoice.received
  - invoice.validated
Events Produced:
  - invoice.valid
  - invoice.invalid
Events to Handle:
  - invoice.received: Validate invoice data, check required fields
  - invoice.validated: Store in database
```

### Using 02-events-simple (Event Chains)

**Prompt Template:**
```
Using examples/02-events-simple as a reference, create an event workflow for [domain]:

Workflow Steps:
1. [event.type] → [action] → publishes [next.event]
2. [next.event] → [action] → publishes [final.event]
...

Topics: [list topics to use]
```

**Example Prompt:**
```
Using examples/02-events-simple as a reference, create an event workflow for user onboarding:

Workflow Steps:
1. user.registered → Send welcome email → publishes user.welcomed
2. user.welcomed → Create user profile → publishes profile.created  
3. profile.created → Assign default preferences → publishes onboarding.completed

Topics: users, notifications, profiles
```

### Using 03-events-structured (LLM Selection with EventDefinition)

**Prompt Template:**
```
Using examples/03-events-structured as a reference, create an LLM-based event selector for [domain]:

Event Definitions (in events.py):
  - [event.name]: [when to use] - with Pydantic payload model
  - [event.name]: [when to use] - with Pydantic payload model

Agent (in [agent].py):
  - Import EventDefinition objects from events.py
  - Pass them to events_consumed/events_produced (SDK auto-registers)
  - Use LLM to select appropriate event based on input
  
Selection Criteria: [what the LLM should consider]
```

**Example Prompt:**
```
Using examples/03-events-structured as a reference, create an LLM-based event selector for customer inquiries:

Create events.py with EventDefinitions:
  - inquiry.route.sales: When customer is asking about pricing or purchasing
  - inquiry.route.support: When customer has a technical problem
  - inquiry.route.billing: When customer has payment or invoice questions

Each event should have:
  - Pydantic payload model with Field descriptions
  - EventDefinition with event_name, topic (from EventTopic enum), description, payload_schema

The agent will:
  - Import these EventDefinition objects
  - Pass them to Worker events_consumed/events_produced (auto-registration)
  - Use LLM to analyze inquiry text and select the appropriate routing event
```

---

## Best Practices

### ✅ Do This

1. **Be Specific About Examples**
   - Reference exact file paths
   - Mention specific patterns by name
   - Point to relevant sections

2. **Provide Context**
   - Explain your use case
   - Describe expected behavior
   - List inputs and outputs

3. **Iterate on Generated Code**
   - Start with basic structure from examples
   - Add domain-specific logic incrementally
   - Test frequently

4. **Keep Examples Open**
   - Have relevant examples in open tabs
   - Let Copilot/Cursor see them as context
   - Reference multiple examples for complex patterns

5. **Use Start Scripts**
   - Ask AI to generate start.sh following the pattern
   - Include platform startup checks
   - Make scripts executable

### ❌ Don't Do This

1. **Don't Be Vague**
   ```
   ❌ "Make me a Soorma thing"
   ✅ "Create a Worker agent using examples/01-hello-world pattern"
   ```

2. **Don't Ignore Prerequisites**
   ```
   ❌ "Create an autonomous choreography agent" (without understanding basics)
   ✅ Start with 01-hello-world, then progress to 03-events-structured
   ```

3. **Don't Mix Patterns Incorrectly**
   - Trinity and Worker patterns serve different purposes
   - Semantic vs Working memory have different use cases
   - Refer to docs/agent_patterns/README.md when unsure

4. **Don't Skip Testing**
   - Always run generated code
   - Use `soorma dev --build` for local testing
   - Verify events are published/received correctly

---

## Common Scenarios

### Scenario 1: Create a Simple Reactive Agent

**Prompt:**
```
Create a worker agent following examples/01-hello-world that:
- Listens for payment.received events
- Validates payment data (amount > 0, valid payment method)
- Publishes payment.valid or payment.invalid based on validation
```

**Expected Output:**
- `worker.py` with event handlers
- Clear event handling logic

---

### Scenario 2: Create an Event Workflow

**Prompt:**
```
Using examples/02-events-simple as a template, create a customer onboarding workflow:

Events:
- customer.registered → verify.email
- email.verified → create.profile  
- profile.created → assign.preferences
- preferences.assigned → onboarding.complete

Create both publisher.py and subscriber.py files.
```

**Expected Output:**
- Event chain with multiple handlers
- Publisher to trigger workflow
- Subscriber with sequential event handlers

---

### Scenario 3: Add LLM-Based Routing

**Prompt:**
```
Based on examples/03-events-structured, create an intelligent email router:

Create EventDefinitions:
- email.route.sales (for sales inquiries)
- email.route.support (for technical support)
- email.route.billing (for payment issues)
- email.route.general (for everything else)

Include:
- events.py with EventDefinition objects (Pydantic payloads + EventDefinition with topic/description)
- email_router.py that imports EventDefinitions and passes them to Worker (SDK auto-registers)
- llm_utils.py (or use LLM) to select the right routing event
- client.py to test with sample emails
```

**Expected Output:**
- EventDefinition objects with Pydantic payload models
- Worker agent with events_consumed/events_produced (auto-registration)
- LLM-based event selection

---

## Debugging AI-Generated Code

### Common Issues

**Issue 1: Wrong Event Names**
```python
# AI might generate:
@worker.on_event("orderCreated")  # Wrong format

# Should be:
@worker.on_event("order.created")  # Soorma naming convention
```

**Fix:** Reference examples/02-events-simple for event naming conventions

**Issue 2: Missing Context Parameter**
```python
# AI might generate:
@worker.on_event("order.placed")
async def handle(event):  # Missing context!

# Should be:
@worker.on_event("order.placed")
async def handle(event, context):  # Context is required
```

**Fix:** Point to examples/01-hello-world/worker.py

**Issue 3: Incorrect Bus Usage**
```python
# AI might generate:
context.bus.publish("order.placed", {...})  # Missing topic

# Should be:
context.bus.publish("order.placed", "business-facts", {...})
```

**Fix:** Show examples/02-events-simple/publisher.py

---

## Advanced: Custom .cursorrules

Create a `.cursorrules` file in your project root to guide AI assistants:

```markdown
# Soorma Agent Development Rules

When generating Soorma agent code:

## Worker Pattern
- Reference: examples/01-hello-world/worker.py
- Always specify events_consumed and events_produced lists
- Use @worker.on_event() decorators
- Always include (event, context) parameters
- Publish events with: await context.bus.publish(event_type, topic, data)

## Event Naming
- Format: domain.action (e.g., "order.placed", "payment.completed")
- See examples/02-events-simple for conventions

## Event Declarations
- events_consumed: List all event types this agent handles
- events_produced: List all event types this agent can publish
- Registry uses these to build event flow graphs

## Start Scripts
- Follow examples/01-hello-world/start.sh pattern
- Check for platform services before starting
- Include instructions for running client

## Memory Patterns
- Semantic (RAG): examples/04-memory-semantic
- Working (workflow state): examples/05-memory-working  
- Episodic (history): examples/06-memory-episodic

## Testing
- Use `soorma dev --build` for local testing
- Always create a client.py to test the agent
- Include expected output in README.md
```

---

## Workflow: From Idea to Agent

1. **Identify the Pattern**
   - Consult [examples/README.md](../examples/README.md) pattern catalog
   - Choose the example that matches your need

2. **Open Reference Examples**
   - Open 1-2 relevant examples in your editor
   - Keep them visible while generating code

3. **Prompt with Context**
   ```
   Using examples/[XX-example] as a reference, create an agent that [your requirements]
   ```

4. **Iterate on Output**
   - Review generated code
   - Compare with examples
   - Fix any deviations from patterns

5. **Test Locally**
   ```bash
   soorma dev --build
   ./start.sh
   python client.py
   ```

6. **Refine**
   - Add error handling
   - Improve logging
   - Add documentation

---

## Resources

- **Pattern Catalog**: [examples/README.md](../examples/README.md#pattern-catalog)
- **Agent Patterns**: [agent_patterns/README.md](./agent_patterns/README.md)
- **Event System**: [event_system/README.md](./event_system/README.md)
- **Memory System**: [memory_system/README.md](./memory_system/README.md)
- **Discovery**: [discovery/README.md](./discovery/README.md)

---

## Contributing

Found a great prompting pattern? Share it!

1. Test your pattern with multiple AI assistants
2. Document it in this guide
3. Submit a PR

---

**Pro Tip:** The more specific your prompt and the more examples you reference, the better the AI-generated code will be. Think of examples as your "training data" for the AI assistant.
