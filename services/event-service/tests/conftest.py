"""
Pytest configuration for Event Service tests.
"""
import pytest
import os

# Set test environment variables
os.environ["EVENT_ADAPTER"] = "memory"
os.environ["DEBUG"] = "true"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def tenancy_headers():
    """Default authenticated platform tenant header used for publish tests."""
    return {"X-Tenant-ID": "spt_test"}
