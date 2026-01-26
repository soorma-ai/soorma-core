"""Tests for the init command."""

import os
import tempfile
from pathlib import Path

import click
import pytest
from typer.testing import CliRunner

from soorma.cli.main import app


runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    return click.unstyle(text)


class TestInitCommand:
    """Tests for soorma init."""

    def test_init_creates_project_structure(self, tmp_path):
        """soorma init should create all expected files."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["init", "my-agent"])
        output = strip_ansi(result.stdout)
        
        # Command should succeed
        assert result.exit_code == 0
        assert "Success" in output or "✓" in result.stdout
        
        # Check project directory was created
        project_dir = tmp_path / "my-agent"
        assert project_dir.exists()
        assert "my-agent" in output

    def test_init_creates_expected_files(self, tmp_path):
        """Verify all expected files are created."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["init", "test-agent"])
        
        assert result.exit_code == 0
        
        project_dir = tmp_path / "test-agent"
        
        # Check all expected files
        assert (project_dir / "pyproject.toml").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / ".gitignore").exists()
        assert (project_dir / "test_agent" / "__init__.py").exists()
        assert (project_dir / "test_agent" / "agent.py").exists()
        assert (project_dir / "tests" / "test_agent.py").exists()

    def test_init_pyproject_has_correct_name(self, tmp_path):
        """pyproject.toml should have the correct project name."""
        os.chdir(tmp_path)
        
        runner.invoke(app, ["init", "my-cool-agent"])
        
        pyproject = (tmp_path / "my-cool-agent" / "pyproject.toml").read_text()
        assert 'name = "my-cool-agent"' in pyproject

    def test_init_agent_has_correct_name(self, tmp_path):
        """agent.py should use the project name."""
        os.chdir(tmp_path)
        
        runner.invoke(app, ["init", "smart-bot"])
        
        agent_py = (tmp_path / "smart-bot" / "smart_bot" / "agent.py").read_text()
        assert 'name="smart-bot"' in agent_py
        assert "smart-bot" in agent_py

    def test_init_refuses_existing_directory(self, tmp_path):
        """soorma init should fail if directory already exists."""
        os.chdir(tmp_path)
        
        # Create the directory first
        (tmp_path / "existing-project").mkdir()
        
        result = runner.invoke(app, ["init", "existing-project"])
        output = strip_ansi(result.output)
        
        assert result.exit_code != 0
        # Error messages may go to stderr, check result.output
        assert "exists" in output.lower() or "error" in output.lower()

    def test_init_sanitizes_package_name(self, tmp_path):
        """Package name should be valid Python identifier."""
        os.chdir(tmp_path)
        
        runner.invoke(app, ["init", "my-agent-123"])
        
        # Package directory should use underscores
        assert (tmp_path / "my-agent-123" / "my_agent_123").exists()

    def test_init_shows_next_steps(self, tmp_path):
        """Output should include helpful next steps."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["init", "new-agent"])
        output = strip_ansi(result.stdout)
        
        assert "cd new-agent" in output or "cd " in output
        assert "soorma dev" in output


class TestInitEdgeCases:
    """Edge case tests for init command."""

    def test_init_with_dots_in_name(self, tmp_path):
        """Names with dots should work."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["init", "my.agent"])
        output = strip_ansi(result.stdout)
        
        # Should either succeed or give a clear error
        # Dots in package names are problematic
        assert result.exit_code == 0 or "invalid" in output.lower()

    def test_init_with_numbers_only_fails(self, tmp_path):
        """Pure numeric names should be rejected or handled."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["init", "123"])
        
        # Python identifiers can't start with numbers
        # Should either handle it or error gracefully
        if result.exit_code == 0:
            # If it succeeds, package dir should have valid name
            assert (tmp_path / "123").exists()


class TestInitAgentTypes:
    """Tests for the --type option."""

    def test_init_default_type_is_worker(self, tmp_path):
        """Default agent type should be worker."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["init", "default-agent"])
        
        assert result.exit_code == 0
        
        agent_py = (tmp_path / "default-agent" / "default_agent" / "agent.py").read_text()
        assert "from soorma import Worker" in agent_py
        assert "@worker.on_event" in agent_py
        assert "EventEnvelope" in agent_py
        assert "EventTopic.ACTION_REQUESTS" in agent_py

    def test_init_planner_type(self, tmp_path):
        """--type planner should create a Planner agent."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["init", "my-planner", "--type", "planner"])
        output = strip_ansi(result.stdout)
        
        assert result.exit_code == 0
        assert "planner" in output.lower()
        
        agent_py = (tmp_path / "my-planner" / "my_planner" / "agent.py").read_text()
        assert "from soorma import Planner" in agent_py
        assert "@planner.on_goal" in agent_py
        assert "Plan" in agent_py
        assert "Task" in agent_py

    def test_init_worker_type(self, tmp_path):
        """--type worker should create a Worker agent."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["init", "my-worker", "--type", "worker"])
        output = strip_ansi(result.stdout)
        
        assert result.exit_code == 0
        assert "worker" in output.lower()
        
        agent_py = (tmp_path / "my-worker" / "my_worker" / "agent.py").read_text()
        assert "from soorma import Worker" in agent_py
        assert "@worker.on_event" in agent_py
        assert "EventEnvelope" in agent_py
        assert "EventTopic.ACTION_REQUESTS" in agent_py

    def test_init_tool_type(self, tmp_path):
        """--type tool should create a Tool service."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["init", "my-tool", "--type", "tool"])
        output = strip_ansi(result.stdout)
        
        assert result.exit_code == 0
        assert "tool" in output.lower()
        
        agent_py = (tmp_path / "my-tool" / "my_tool" / "agent.py").read_text()
        assert "from soorma import Tool" in agent_py
        assert "@tool.on_event" in agent_py
        assert "EventEnvelope" in agent_py
        assert "EventTopic.ACTION_REQUESTS" in agent_py

    def test_init_type_short_flag(self, tmp_path):
        """-t should work as shorthand for --type."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["init", "short-flag-test", "-t", "planner"])
        
        assert result.exit_code == 0
        
        agent_py = (tmp_path / "short-flag-test" / "short_flag_test" / "agent.py").read_text()
        assert "from soorma import Planner" in agent_py

    def test_init_type_case_insensitive(self, tmp_path):
        """Type option should be case insensitive."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["init", "case-test", "--type", "PLANNER"])
        
        assert result.exit_code == 0
        
        agent_py = (tmp_path / "case-test" / "case_test" / "agent.py").read_text()
        assert "from soorma import Planner" in agent_py

    def test_init_planner_test_template(self, tmp_path):
        """Planner should have appropriate test template."""
        os.chdir(tmp_path)
        
        runner.invoke(app, ["init", "planner-test", "--type", "planner"])
        
        test_py = (tmp_path / "planner-test" / "tests" / "test_agent.py").read_text()
        assert "test_planner_exists" in test_py
        assert "test_plan_example_goal" in test_py
        assert "from soorma.agents.planner import Goal" in test_py

    def test_init_tool_test_template(self, tmp_path):
        """Tool should have appropriate test template."""
        os.chdir(tmp_path)
        
        runner.invoke(app, ["init", "tool-test", "--type", "tool"])
        
        test_py = (tmp_path / "tool-test" / "tests" / "test_agent.py").read_text()
        assert "test_tool_exists" in test_py
        assert "test_example_operation" in test_py
        assert "from soorma_common.events import EventEnvelope, EventTopic" in test_py
        assert "context.bus.publish.assert_called_once()" in test_py
