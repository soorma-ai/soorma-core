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
2. Decompose goals into actionable tasks
3. Assign tasks to Worker agents based on capabilities
4. Monitor plan execution progress

The PlatformContext provides access to:
- context.registry: Find available workers by capability
- context.memory: Store/retrieve planning context
- context.bus: Publish tasks as action-requests
- context.tracker: Monitor plan execution
"""

from soorma import Planner, PlatformContext
from soorma.agents.planner import Goal, Plan, Task


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
async def plan_example_goal(goal: Goal, context: PlatformContext) -> Plan:
    """
    Handle incoming example.goal requests.
    
    Replace this with your own goal handlers. Each goal handler:
    1. Receives a Goal with the high-level objective
    2. Has access to PlatformContext for service discovery
    3. Returns a Plan with ordered Tasks
    
    The platform automatically:
    - Tracks plan execution via Tracker service
    - Publishes tasks as action-requests
    - Monitors task completion and dependencies
    """
    print(f"Planning goal: {{goal.goal_type}} ({{goal.goal_id}})")
    
    # Discover available workers (example)
    # workers = await context.registry.find_all("data_processing")
    
    # Decompose goal into tasks
    # In real scenarios, you might use an LLM for intelligent decomposition
    tasks = [
        Task(
            name="step_1",
            assigned_to="example_task",  # Worker capability
            data={{"input": goal.data.get("input", "default")}},
        ),
        Task(
            name="step_2",
            assigned_to="example_task",
            data={{"previous_step": "step_1"}},
            depends_on=["step_1"],  # Wait for step_1 to complete
        ),
    ]
    
    return Plan(
        goal=goal,
        tasks=tasks,
        metadata={{"planned_by": "{name}"}},
    )


if __name__ == "__main__":
    planner.run()
'''

# =============================================================================
# WORKER TEMPLATE
# =============================================================================
WORKER_PY_TEMPLATE = '''"""
{name} - A Soorma Worker Agent.

Workers are the "hands" of the DisCo architecture. They:
1. Register capabilities with the Registry
2. Subscribe to action-requests matching their capabilities
3. Execute tasks with domain expertise (often using LLMs)
4. Report progress and results

The PlatformContext provides access to:
- context.registry: Service discovery & capabilities
- context.memory: Distributed state management
- context.bus: Event choreography (pub/sub)
- context.tracker: Observability & state machines
"""

from soorma import Worker, PlatformContext
from soorma.agents.worker import TaskContext


# Create a Worker agent
worker = Worker(
    name="{name}",
    description="{description}",
    version="0.1.0",
    capabilities=["example_task"],  # Add your capabilities here
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


@worker.on_task("example_task")
async def handle_example_task(task: TaskContext, context: PlatformContext):
    """
    Handle incoming example_task assignments.
    
    Replace this with your own task handlers. Each task handler:
    1. Receives a TaskContext with input data
    2. Has access to PlatformContext for platform services
    3. Returns a result dictionary
    
    The platform automatically:
    - Tracks task progress
    - Publishes action-results on completion
    - Handles errors and retries
    """
    print(f"Processing task: {{task.task_name}} ({{task.task_id}})")
    
    # Report progress (optional)
    await task.report_progress(0.5, "Processing...")
    
    # Access shared memory (example)
    # cached_data = await context.memory.retrieve(f"cache:{{task.data.get('key')}}")
    
    # Your task logic here
    result = {{
        "message": "Hello from {name}!",
        "processed": True,
    }}
    
    # Store results for other workers (optional)
    # await context.memory.store(f"result:{{task.task_id}}", result)
    
    return result


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
"""

from soorma import Tool, PlatformContext
from soorma.agents.tool import ToolRequest


# Create a Tool service
tool = Tool(
    name="{name}",
    description="{description}",
    version="0.1.0",
    capabilities=["example_operation"],  # Add your operations here
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


@tool.on_invoke("example_operation")
async def handle_example_operation(request: ToolRequest, context: PlatformContext):
    """
    Handle incoming example_operation requests.
    
    Replace this with your own operation handlers. Each handler:
    1. Receives a ToolRequest with input parameters
    2. Performs a stateless, deterministic operation
    3. Returns a result dictionary
    
    Tools are ideal for:
    - API integrations (weather, maps, search)
    - Calculations and conversions
    - Data transformations
    - File parsing
    """
    print(f"Executing operation: {{request.operation}} ({{request.request_id}})")
    
    # Your operation logic here
    input_value = request.data.get("input", "default")
    
    result = {{
        "output": f"Processed: {{input_value}}",
        "success": True,
    }}
    
    return result


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
    """Test the example_task handler."""
    from {package_name}.agent import handle_example_task
    from soorma.agents.worker import TaskContext
    
    # Create mock task context
    task = TaskContext(
        task_id="test-123",
        task_name="example_task",
        plan_id="plan-1",
        goal_id="goal-1",
        data={{"key": "value"}},
    )
    task.report_progress = AsyncMock()
    
    # Create mock platform context
    context = MagicMock()
    context.memory.retrieve = AsyncMock(return_value=None)
    context.memory.store = AsyncMock()
    
    # Execute handler
    result = await handle_example_task(task, context)
    
    # Verify result
    assert result["processed"] is True
    assert "message" in result
'''

TOOL_TEST_TEMPLATE = '''"""
Tests for {name} tool.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


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
    """Test the example_operation handler."""
    from {package_name}.agent import handle_example_operation
    from soorma.agents.tool import ToolRequest
    
    # Create mock request
    request = ToolRequest(
        operation="example_operation",
        data={{"input": "test_value"}},
    )
    
    # Create mock platform context
    context = MagicMock()
    
    # Execute handler
    result = await handle_example_operation(request, context)
    
    # Verify result
    assert result["success"] is True
    assert "output" in result
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
