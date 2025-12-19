"""
soorma init - Scaffold a new agent project.
"""

import typer
from pathlib import Path
from typing import Optional

# Project templates
AGENT_PY_TEMPLATE = '''"""
{name} - A Soorma AI Agent.

This is your agent's main entry point. The agent will:
1. Register with the Soorma Registry on startup
2. Listen for events it's subscribed to
3. Process events and emit new ones
"""

from soorma import Agent, event_handler


agent = Agent(
    name="{name}",
    description="{description}",
    version="0.1.0",
)


@agent.on_startup
async def startup():
    """Called when the agent starts."""
    print(f"🚀 {{agent.name}} is starting up...")


@agent.on_shutdown
async def shutdown():
    """Called when the agent shuts down."""
    print(f"👋 {{agent.name}} is shutting down...")


@event_handler("example.request")
async def handle_example(event):
    """
    Handle incoming example.request events.
    
    Replace this with your own event handlers.
    """
    print(f"Received event: {{event}}")
    
    # Emit a response event
    await agent.emit("example.response", {{
        "message": "Hello from {name}!",
        "request_id": event.get("request_id"),
    }})


if __name__ == "__main__":
    agent.run()
'''

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

TEST_TEMPLATE = '''"""
Tests for {name} agent.
"""

import pytest


def test_agent_exists():
    """Basic test to verify agent module loads."""
    from {package_name} import agent
    assert agent.agent.name == "{name}"


@pytest.mark.asyncio
async def test_startup():
    """Test agent startup handler."""
    from {package_name}.agent import startup
    # startup() should not raise
    await startup()
'''

INIT_TEMPLATE = '''"""
{name} - A Soorma AI Agent.
"""

__version__ = "0.1.0"
'''


def init_project(
    name: str = typer.Argument(
        ...,
        help="Name of the agent project to create.",
    ),
    description: str = typer.Option(
        "A Soorma AI Agent",
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
    """
    # Determine output path
    base_dir = output_dir or Path.cwd()
    project_dir = base_dir / name
    
    # Convert name to valid Python package name
    package_name = name.lower().replace("-", "_").replace(" ", "_")
    
    # Check if directory already exists
    if project_dir.exists():
        typer.echo(f"❌ Error: Directory '{name}' already exists.", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"🔧 Creating new Soorma agent project: {name}")
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
    
    # agent.py
    (project_dir / package_name / "agent.py").write_text(
        AGENT_PY_TEMPLATE.format(
            name=name,
            description=description,
        )
    )
    files_created.append(f"{package_name}/agent.py")
    
    # tests/__init__.py
    (project_dir / "tests" / "__init__.py").write_text("")
    
    # tests/test_agent.py
    (project_dir / "tests" / "test_agent.py").write_text(
        TEST_TEMPLATE.format(
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
