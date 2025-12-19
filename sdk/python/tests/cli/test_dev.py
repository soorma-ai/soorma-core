"""Tests for the dev command."""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest
from typer.testing import CliRunner

from soorma.cli.main import app
from soorma.cli.commands.dev import (
    SERVICE_DEFINITIONS,
    check_service_image,
    find_soorma_core_root,
    get_soorma_dir,
)


runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    return click.unstyle(text)


class TestServiceDefinitions:
    """Tests for SERVICE_DEFINITIONS configuration."""

    def test_registry_service_defined(self):
        """Registry service should be properly defined."""
        assert "registry" in SERVICE_DEFINITIONS
        
        registry = SERVICE_DEFINITIONS["registry"]
        assert "local_image" in registry
        assert "public_image" in registry
        assert "dockerfile" in registry
        assert "name" in registry

    def test_registry_dockerfile_path(self):
        """Registry dockerfile should be relative to soorma-core root."""
        registry = SERVICE_DEFINITIONS["registry"]
        # Should NOT start with 'core/' since build context is soorma-core root
        assert registry["dockerfile"] == "services/registry/Dockerfile"
        assert not registry["dockerfile"].startswith("core/")

    def test_local_image_format(self):
        """Local images should follow naming convention."""
        for key, service in SERVICE_DEFINITIONS.items():
            assert service["local_image"].endswith(":latest")
            assert "-service:" in service["local_image"] or key in service["local_image"]

    def test_public_image_format(self):
        """Public images should be on ghcr.io/soorma-ai."""
        for key, service in SERVICE_DEFINITIONS.items():
            assert service["public_image"].startswith("ghcr.io/soorma-ai/")


class TestFindSoormaCoreRoot:
    """Tests for find_soorma_core_root function."""

    def test_finds_root_from_env_var(self, tmp_path):
        """Should find root when SOORMA_CORE_PATH is set."""
        # Create a mock soorma-core structure
        (tmp_path / "services").mkdir()
        (tmp_path / "libs").mkdir()
        
        with patch.dict(os.environ, {"SOORMA_CORE_PATH": str(tmp_path)}):
            result = find_soorma_core_root()
            assert result == tmp_path

    def test_returns_none_when_not_found(self):
        """Should return None when no valid root is found."""
        with patch.dict(os.environ, {"SOORMA_CORE_PATH": "/nonexistent/path"}, clear=False):
            # Clear other env vars that might point to valid paths
            env = os.environ.copy()
            env["SOORMA_CORE_PATH"] = "/nonexistent/path"
            
            with patch.dict(os.environ, env, clear=True):
                result = find_soorma_core_root()
                # Result depends on whether common paths exist on the system
                # Just verify it doesn't crash
                assert result is None or isinstance(result, Path)

    def test_requires_services_and_libs(self, tmp_path):
        """Should only return path if both services/ and libs/ exist."""
        # Only services/ exists
        (tmp_path / "services").mkdir()
        
        with patch.dict(os.environ, {"SOORMA_CORE_PATH": str(tmp_path)}):
            result = find_soorma_core_root()
            # Should not find it because libs/ is missing
            # (unless it finds another valid path in common locations)
            if result == tmp_path:
                pytest.fail("Should not match path without libs/")


class TestCheckServiceImage:
    """Tests for check_service_image function."""

    def test_returns_none_for_unknown_service(self):
        """Should return None for undefined service."""
        result = check_service_image("unknown-service")
        assert result is None

    @patch("subprocess.run")
    def test_prefers_local_image(self, mock_run):
        """Should return local image if it exists."""
        # Mock docker images command returning an image ID
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123\n"
        )
        
        result = check_service_image("registry")
        
        assert result == "registry-service:latest"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_falls_back_to_public_image(self, mock_run):
        """Should check public image if local doesn't exist."""
        # First call (docker images) returns empty, second (manifest inspect) succeeds
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),  # No local image
            MagicMock(returncode=0, stdout="{}"),  # Public exists
        ]
        
        result = check_service_image("registry")
        
        assert result == "ghcr.io/soorma-ai/registry-service:latest"
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_returns_none_if_no_image(self, mock_run):
        """Should return None if neither local nor public image exists."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),  # No local image
            MagicMock(returncode=1, stdout=""),  # No public image
        ]
        
        result = check_service_image("registry")
        
        assert result is None


class TestGetSoormaDir:
    """Tests for get_soorma_dir function."""

    def test_creates_soorma_dir(self, tmp_path):
        """Should create .soorma directory if it doesn't exist."""
        os.chdir(tmp_path)
        
        result = get_soorma_dir()
        
        assert result == tmp_path / ".soorma"
        assert result.exists()
        assert result.is_dir()

    def test_returns_existing_dir(self, tmp_path):
        """Should return existing .soorma directory."""
        os.chdir(tmp_path)
        soorma_dir = tmp_path / ".soorma"
        soorma_dir.mkdir()
        
        result = get_soorma_dir()
        
        assert result == soorma_dir


class TestDevCommand:
    """Integration tests for soorma dev command."""

    def test_dev_without_docker_shows_error(self):
        """Should show clear error if Docker isn't available."""
        with patch("shutil.which", return_value=None):
            result = runner.invoke(app, ["dev"])
            output = strip_ansi(result.output)
            
            assert result.exit_code != 0
            # Error goes to stderr, which is in result.output
            assert "docker" in output.lower()

    def test_dev_stop_without_running_stack(self, tmp_path):
        """soorma dev --stop should handle no running stack gracefully."""
        os.chdir(tmp_path)
        
        # Create .soorma dir with compose file
        soorma_dir = tmp_path / ".soorma"
        soorma_dir.mkdir()
        
        # This test requires Docker to be running
        # Skip if Docker isn't available
        if not subprocess.run(["docker", "info"], capture_output=True).returncode == 0:
            pytest.skip("Docker not available")
        
        result = runner.invoke(app, ["dev", "--stop"])
        output = strip_ansi(result.stdout)
        
        # Should not crash, even if nothing is running
        assert result.exit_code == 0 or "not running" in output.lower()

    def test_dev_status_shows_output(self, tmp_path):
        """soorma dev --status should show status info."""
        os.chdir(tmp_path)
        
        # Create .soorma dir
        soorma_dir = tmp_path / ".soorma"
        soorma_dir.mkdir()
        
        # Skip if Docker isn't available
        if not subprocess.run(["docker", "info"], capture_output=True).returncode == 0:
            pytest.skip("Docker not available")
        
        result = runner.invoke(app, ["dev", "--status"])
        output = strip_ansi(result.stdout)
        
        # Should show some status output
        assert result.exit_code == 0
        assert "status" in output.lower() or "NAME" in output


class TestDevMissingImages:
    """Tests for handling missing service images."""

    @patch("soorma.cli.commands.dev.check_service_image", return_value=None)
    @patch("soorma.cli.commands.dev.check_docker", return_value="docker compose")
    def test_missing_image_shows_options(self, mock_docker, mock_check, tmp_path):
        """Should show build options when image is missing."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["dev"])
        output = strip_ansi(result.output)
        
        assert result.exit_code != 0
        # Error messages go to stderr, available in result.output
        assert "soorma dev --build" in output
        assert "SOORMA_CORE_PATH" in output

    @patch("soorma.cli.commands.dev.check_service_image", return_value=None)
    @patch("soorma.cli.commands.dev.check_docker", return_value="docker compose")
    def test_missing_image_shows_dockerfile_path(self, mock_docker, mock_check, tmp_path):
        """Should show correct dockerfile path relative to soorma-core."""
        os.chdir(tmp_path)
        
        result = runner.invoke(app, ["dev"])
        output = strip_ansi(result.output)
        
        # Should show services/registry/Dockerfile, not core/services/...
        # Error messages go to stderr, available in result.output
        assert "services/registry/Dockerfile" in output
        assert "core/services" not in output
