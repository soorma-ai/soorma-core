"""Tests for the main CLI entry point."""

import click
import pytest
from typer.testing import CliRunner

from soorma.cli.main import app


runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    return click.unstyle(text)


class TestVersion:
    """Tests for the version command."""

    def test_version_shows_version(self):
        """soorma version should display version info."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Soorma Core" in result.stdout
        assert "v" in result.stdout


class TestHelp:
    """Tests for help output."""

    def test_main_help(self):
        """soorma --help should show available commands."""
        result = runner.invoke(app, ["--help"])
        output = strip_ansi(result.stdout)
        assert result.exit_code == 0
        assert "init" in output
        assert "dev" in output
        assert "deploy" in output
        assert "version" in output

    def test_init_help(self):
        """soorma init --help should show init options."""
        result = runner.invoke(app, ["init", "--help"])
        output = strip_ansi(result.stdout)
        assert result.exit_code == 0
        assert "NAME" in output or "name" in output.lower()

    def test_dev_help(self):
        """soorma dev --help should show dev options."""
        result = runner.invoke(app, ["dev", "--help"])
        output = strip_ansi(result.stdout)
        assert result.exit_code == 0
        assert "--detach" in output
        assert "--stop" in output
        assert "--status" in output
        assert "--build" in output

    def test_deploy_help(self):
        """soorma deploy --help should show deploy info."""
        result = runner.invoke(app, ["deploy", "--help"])
        assert result.exit_code == 0
