"""Pytest configuration and fixtures for soorma-nats tests."""

import os
import pytest


@pytest.fixture
def nats_url() -> str:
    """Return the NATS URL for integration tests.

    Override with NATS_URL environment variable when running against a live server.
    """
    return os.environ.get("NATS_URL", "nats://localhost:4222")
