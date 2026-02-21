"""
soorma init - Scaffold a new agent project.
"""

import typer
from pathlib import Path
from typing import Optional
from enum import Enum


class AgentType(str, Enum):
    """Type of agent to generate."""
    planner = "planner"
    worker = "worker"
    tool = "tool"


# =============================================================================
# PLANNER TEMPLATE
# =============================================================================
PLANNER_PY_TEMPLATE = '''"""
{name} - A Soorma Planner Agent.

Planners are the "brain" of the DisCo architecture. They:
1. Receive high-level goals from clients
2. Model workflows as state machines
3. Publish tasks to Worker agents
4. Monitor plan execution progress

The PlatformContext provides access to:
- context.registry: Find available workers by capability
- context.memory: Store/retrieve planning context
- context.bus: Publish tasks as action-requests
- context.tracker: Monitor plan execution
"""

from soorma import Planner, PlatformContext
from soorma.agents.planner import GoalContext
from soorma.plan_context import PlanContext
from soorma_common.state import StateConfig, StateAction, StateTransition


# Create a Planner agent
planner = Planner(
    name="{name}",
    description="{description}",
    version="0.1.0",
    capabilities=["example_planning"],  # Add your planning capabilities here
)


@planner.on_startup
async def startup():
    """Called when the planner connects to the platform."""
    print(f"🧠 {{planner.name}} is starting up...")
    print(f"   Ready to decompose goals into tasks")


@planner.on_shutdown
async def shutdown():
    """Called when the planner is shutting down."""
    print(f"👋 {{planner.name}} is shutting down...")


@planner.on_goal("example.goal")
async def plan_example_goal(goal: GoalContext, context: PlatformContext) -> None:
    """
    Handle incoming example.goal requests.
    
    Replace this with your own goal handlers. Each goal handler:
    1. Receives a Goal with the high-level objective
    2. Has access to PlatformContext for service discovery
    3. Creates and persists a PlanContext with a state machine
    
    The platform automatically:
    - Persists plan context to Memory Service
    - Publishes tasks as action-requests
    - Routes transitions based on action-results
    """
    print(f"Planning goal: {{goal.event_type}} ({{goal.correlation_id}})")
    
    # Discover available workers (example)
    # workers = await context.registry.query_agents(name="data_processing")
    
    # Define state machine
    states = {{
        "start": StateConfig(
            state_name="start",
            default_next="execute",
        ),
        "execute": StateConfig(
            state_name="execute",
            action=StateAction(
                event_type="example.task",
                response_event="example.completed",
                data={{"input": "{{goal_data.input}}"}},
            ),
            transitions=[
                StateTransition(on_event="example.completed", to_state="complete")
            ],
        ),
        "complete": StateConfig(
            state_name="complete",
            is_terminal=True,
        ),
    }}
    
    # Create and persist plan context
    plan = await PlanContext.create_from_goal(
        goal=goal,
        context=context,
        state_machine=states,
        current_state="start",
        status="pending",
    )
    
    # Execute initial state
    await plan.execute_next()


if __name__ == "__main__":
    planner.run()
'''

# =============================================================================
# WORKER TEMPLATE
# =============================================================================
WORKER_PY_TEMPLATE = '''"""
{name} - A Soorma Worker Agent.

Workers are the "hands" of the DisCo architecture. They:
1. Subscribe to action-requests and execute domain-specific tasks
2. Use EventEnvelope for strongly-typed event handling
3. Execute tasks with domain expertise (often using LLMs)
4. Publish results as action-results

The PlatformContext provides access to:
- context.registry: Service discovery & event types
- context.memory: Distributed state management
- context.bus: Event choreography (pub/sub)
- context.toolkit: Event discovery and formatting
"""

from soorma import Worker, PlatformContext
from soorma_common.events import EventEnvelope, EventTopic


# Create a Worker agent
worker = Worker(
    name="{name}",
    description="{description}",
    version="0.1.0",
    capabilities=["example_task"],
)


@worker.on_startup
async def startup():
    """Called when the worker connects to the platform."""
    print(f"🔧 {{worker.name}} is starting up...")
    print(f"   Registered capabilities: {{worker.capabilities}}")


@worker.on_shutdown
async def shutdown():
    """Called when the worker is shutting down."""
    print(f"👋 {{worker.name}} is shutting down...")


@worker.on_event("example.task", topic=EventTopic.ACTION_REQUESTS)
async def handle_example_task(event: EventEnvelope, context: PlatformContext):
    """
    Handle incoming example.task events.
    
    Replace this with your own event handlers. Each handler:
    1. Receives an EventEnvelope with strongly-typed data
    2. Has access to PlatformContext for platform services
    3. Publishes results as action-results events
    
    Key patterns:
    - Access event data: event.data or {{}}
    - Access tenant/user: event.tenant_id, event.user_id
    - Publish results: context.bus.publish(event_type=..., topic=EventTopic.ACTION_RESULTS, ...)
    """
    data = event.data or {{}}
    print(f"Processing: {{data}}")
    
    # Your task logic here
    result_data = {{
        "message": "Hello from {name}!",
        "processed": True,
    }}
    
    # Publish result
    await context.bus.publish(
        event_type="example.result",
        topic=EventTopic.ACTION_RESULTS,
        data=result_data,
        correlation_id=event.correlation_id,
        tenant_id=event.tenant_id,
        user_id=event.user_id,
    )


if __name__ == "__main__":
    worker.run()
'''

# =============================================================================
# TOOL TEMPLATE
# =============================================================================
TOOL_PY_TEMPLATE = '''"""
{name} - A Soorma Tool Service.

Tools are the "utilities" of the DisCo architecture. They:
1. Expose atomic, stateless operations
2. Handle deterministic computations or API calls
3. Are highly reusable across different workflows

Key differences from Workers:
- Tools are stateless (no memory between calls)
- Tools are deterministic (same input = same output)
- Tools are typically rules-based, not cognitive

The PlatformContext provides access to:
- context.registry: Service discovery
- context.bus: Event choreography
- context.toolkit: Event discovery and formatting
"""

from soorma import Tool, PlatformContext
from soorma_common.events import EventEnvelope, EventTopic


# Create a Tool service
tool = Tool(
    name="{name}",
    description="{description}",
    version="0.1.0",
    capabilities=["example_operation"],
)


@tool.on_startup
async def startup():
    """Called when the tool connects to the platform."""
    print(f"🔨 {{tool.name}} is starting up...")
    print(f"   Available operations: {{tool.capabilities}}")


@tool.on_shutdown
async def shutdown():
    """Called when the tool is shutting down."""
    print(f"👋 {{tool.name}} is shutting down...")


@tool.on_event("example.operation", topic=EventTopic.ACTION_REQUESTS)
async def handle_example_operation(event: EventEnvelope, context: PlatformContext):
    """
    Handle incoming example.operation events.
    
    Replace this with your own event handlers. Each handler:
    1. Receives an EventEnvelope with strongly-typed data
    2. Performs a stateless, deterministic operation
    3. Publishes result as action-results event
    
    Key patterns:
    - Access event data: event.data or {{}}
    - Access tenant/user: event.tenant_id, event.user_id
    - Publish results: context.bus.publish(event_type=..., topic=EventTopic.ACTION_RESULTS, ...)
    
    Tools are ideal for:
    - API integrations (weather, maps, search)
    - Calculations and conversions
    - Data transformations
    - File parsing
    """
    data = event.data or {{}}
    input_value = data.get("input", "default")
    print(f"Executing operation with input: {{input_value}}")
    
    # Your operation logic here
    result_data = {{
        "output": f"Processed: {{input_value}}",
        "success": True,
    }}
    
    # Publish result
    await context.bus.publish(
        event_type="example.result",
        topic=EventTopic.ACTION_RESULTS,
        data=result_data,
        correlation_id=event.correlation_id,
        tenant_id=event.tenant_id,
        user_id=event.user_id,
    )


if __name__ == "__main__":
    tool.run()
'''

# Keep AGENT_PY_TEMPLATE as alias for backward compatibility
AGENT_PY_TEMPLATE = WORKER_PY_TEMPLATE

PYPROJECT_TEMPLATE = '''[project]
name = "{name}"
version = "0.1.0"
description = "{description}"
requires-python = ">=3.9"
dependencies = [
    "soorma-core>=0.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["{package_name}"]
'''

README_TEMPLATE = '''# {name}

{description}

## Getting Started

### Prerequisites

- Python 3.9+
- Docker (for local development)

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

# Install dependencies
pip install -e ".[dev]"
```

### Local Development

Start the local Soorma stack (Registry + NATS):

```bash
soorma dev
```

In another terminal, run your agent:

```bash
python -m {package_name}.agent
```

### Deploy to Soorma Cloud

```bash
soorma deploy
```

## Project Structure

```
{name}/
├── {package_name}/
│   ├── __init__.py
│   └── agent.py      # Your agent code
├── tests/
│   └── test_agent.py
├── pyproject.toml
└── README.md
```

## Learn More

- [Soorma Documentation](https://soorma.ai/docs)
- [DisCo Architecture](https://soorma.ai/docs/disco)
'''

GITIGNORE_TEMPLATE = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Soorma
.soorma/
'''

# =============================================================================
# TEST TEMPLATES
# =============================================================================
PLANNER_TEST_TEMPLATE = '''"""
Tests for {name} planner.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


def test_planner_exists():
    """Basic test to verify planner module loads."""
    from {package_name} import agent
    assert agent.planner.name == "{name}"
    assert agent.planner.config.agent_type == "planner"


@pytest.mark.asyncio
async def test_startup():
    """Test planner startup handler."""
    from {package_name}.agent import startup
    await startup()


@pytest.mark.asyncio
async def test_plan_example_goal():
    """Test the example goal handler."""
    from {package_name}.agent import plan_example_goal
    from soorma.agents.planner import Goal
    
    # Create mock goal
    goal = Goal(
        goal_type="example.goal",
        data={{"input": "test_value"}},
    )
    
    # Create mock platform context
    context = MagicMock()
    context.registry.find_all = AsyncMock(return_value=[])
    
    # Execute handler
    plan = await plan_example_goal(goal, context)
    
    # Verify plan
    assert plan.goal == goal
    assert len(plan.tasks) == 2
    assert plan.tasks[0].name == "step_1"
    assert plan.tasks[1].depends_on == ["step_1"]
'''

WORKER_TEST_TEMPLATE = '''"""
Tests for {name} worker.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from soorma_common.events import EventEnvelope, EventTopic


def test_worker_exists():
    """Basic test to verify worker module loads."""
    from {package_name} import agent
    assert agent.worker.name == "{name}"
    assert "example_task" in agent.worker.capabilities


@pytest.mark.asyncio
async def test_startup():
    """Test worker startup handler."""
    from {package_name}.agent import startup
    await startup()


@pytest.mark.asyncio
async def test_example_task():
    """Test the example_task event handler."""
    from {package_name}.agent import handle_example_task
    
    # Create event envelope
    event = EventEnvelope(
        event_name="example.task",
        topic=EventTopic.ACTION_REQUESTS,
        data={{"key": "value"}},
        tenant_id="test-tenant",
        user_id="test-user",
        correlation_id="corr-123",
    )
    
    # Create mock platform context
    context = MagicMock()
    context.bus.publish = AsyncMock()
    
    # Execute handler
    await handle_example_task(event, context)
    
    # Verify publish was called
    context.bus.publish.assert_called_once()
    call_kwargs = context.bus.publish.call_args[1]
    assert call_kwargs["event_type"] == "example.result"
    assert call_kwargs["topic"] == EventTopic.ACTION_RESULTS
    assert call_kwargs["data"]["processed"] is True
'''

TOOL_TEST_TEMPLATE = '''"""
Tests for {name} tool.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from soorma_common.events import EventEnvelope, EventTopic


def test_tool_exists():
    """Basic test to verify tool module loads."""
    from {package_name} import agent
    assert agent.tool.name == "{name}"
    assert "example_operation" in agent.tool.capabilities


@pytest.mark.asyncio
async def test_startup():
    """Test tool startup handler."""
    from {package_name}.agent import startup
    await startup()


@pytest.mark.asyncio
async def test_example_operation():
    """Test the example_operation event handler."""
    from {package_name}.agent import handle_example_operation
    
    # Create event envelope
    event = EventEnvelope(
        event_name="example.operation",
        topic=EventTopic.ACTION_REQUESTS,
        data={{"input": "test_value"}},
        tenant_id="test-tenant",
        user_id="test-user",
        correlation_id="corr-123",
    )
    
    # Create mock platform context
    context = MagicMock()
    context.bus.publish = AsyncMock()
    
    # Execute handler
    await handle_example_operation(event, context)
    
    # Verify publish was called
    context.bus.publish.assert_called_once()
    call_kwargs = context.bus.publish.call_args[1]
    assert call_kwargs["event_type"] == "example.result"
    assert call_kwargs["topic"] == EventTopic.ACTION_RESULTS
    assert call_kwargs["data"]["success"] is True
'''

# Keep TEST_TEMPLATE as alias for backward compatibility (worker)
TEST_TEMPLATE = WORKER_TEST_TEMPLATE

INIT_TEMPLATE = '''"""
{name} - A Soorma AI Agent.
"""

__version__ = "0.1.0"
'''


# Map agent types to their templates
AGENT_TEMPLATES = {
    AgentType.planner: PLANNER_PY_TEMPLATE,
    AgentType.worker: WORKER_PY_TEMPLATE,
    AgentType.tool: TOOL_PY_TEMPLATE,
}

TEST_TEMPLATES = {
    AgentType.planner: PLANNER_TEST_TEMPLATE,
    AgentType.worker: WORKER_TEST_TEMPLATE,
    AgentType.tool: TOOL_TEST_TEMPLATE,
}

AGENT_TYPE_DESCRIPTIONS = {
    AgentType.planner: "Planner (strategic reasoning, goal decomposition)",
    AgentType.worker: "Worker (domain-specific task execution)",
    AgentType.tool: "Tool (atomic, stateless operations)",
}

AGENT_TYPE_EMOJIS = {
    AgentType.planner: "🧠",
    AgentType.worker: "🔧",
    AgentType.tool: "🔨",
}


def init_project(
    name: str = typer.Argument(
        ...,
        help="Name of the agent project to create.",
    ),
    agent_type: AgentType = typer.Option(
        AgentType.worker,
        "--type", "-t",
        help="Type of agent to create: planner, worker, or tool.",
        case_sensitive=False,
    ),
    description: str = typer.Option(
        None,
        "--description", "-d",
        help="Short description of your agent.",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output directory. Defaults to current directory.",
    ),
):
    """
    Scaffold a new Soorma agent project.
    
    Creates a new directory with boilerplate code, configuration,
    and folder structure for a Soorma AI agent.
    
    Examples:
    
        soorma init my-worker                    # Default: Worker agent
        
        soorma init my-planner --type planner   # Planner agent
        
        soorma init my-tool --type tool         # Tool service
    """
    # Set default description based on type if not provided
    if description is None:
        description = f"A Soorma {agent_type.value.title()}"
    
    # Determine output path
    base_dir = output_dir or Path.cwd()
    project_dir = base_dir / name
    
    # Convert name to valid Python package name
    package_name = name.lower().replace("-", "_").replace(" ", "_")
    
    # Check if directory already exists
    if project_dir.exists():
        typer.echo(f"❌ Error: Directory '{name}' already exists.", err=True)
        raise typer.Exit(1)
    
    emoji = AGENT_TYPE_EMOJIS[agent_type]
    typer.echo(f"{emoji} Creating new Soorma {agent_type.value} project: {name}")
    typer.echo(f"   Type: {AGENT_TYPE_DESCRIPTIONS[agent_type]}")
    typer.echo("")
    
    # Create directory structure
    (project_dir / package_name).mkdir(parents=True)
    (project_dir / "tests").mkdir()
    
    # Create files
    files_created = []
    
    # pyproject.toml
    (project_dir / "pyproject.toml").write_text(
        PYPROJECT_TEMPLATE.format(
            name=name,
            description=description,
            package_name=package_name,
        )
    )
    files_created.append("pyproject.toml")
    
    # README.md
    (project_dir / "README.md").write_text(
        README_TEMPLATE.format(
            name=name,
            description=description,
            package_name=package_name,
        )
    )
    files_created.append("README.md")
    
    # .gitignore
    (project_dir / ".gitignore").write_text(GITIGNORE_TEMPLATE)
    files_created.append(".gitignore")
    
    # Package __init__.py
    (project_dir / package_name / "__init__.py").write_text(
        INIT_TEMPLATE.format(name=name)
    )
    files_created.append(f"{package_name}/__init__.py")
    
    # agent.py - use type-specific template
    agent_template = AGENT_TEMPLATES[agent_type]
    (project_dir / package_name / "agent.py").write_text(
        agent_template.format(
            name=name,
            description=description,
        )
    )
    files_created.append(f"{package_name}/agent.py")
    
    # tests/__init__.py
    (project_dir / "tests" / "__init__.py").write_text("")
    
    # tests/test_agent.py - use type-specific template
    test_template = TEST_TEMPLATES[agent_type]
    (project_dir / "tests" / "test_agent.py").write_text(
        test_template.format(
            name=name,
            package_name=package_name,
        )
    )
    files_created.append("tests/test_agent.py")
    
    # Success output
    typer.echo("📁 Created project structure:")
    for f in files_created:
        typer.echo(f"   ✓ {f}")
    typer.echo("")
    typer.echo("🎉 Success! Your agent project is ready.")
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo(f"  cd {name}")
    typer.echo("  python -m venv .venv")
    typer.echo("  source .venv/bin/activate")
    typer.echo("  pip install -e '.[dev]'")
    typer.echo("  soorma dev")
    typer.echo("")
