"""Pytest configuration and fixtures."""

import os
import pytest
from pathlib import Path


@pytest.fixture
def clean_env():
    """Clean environment variables before test."""
    original_env = os.environ.copy()
    # Remove DEEPAGENT_* vars
    for key in list(os.environ.keys()):
        if key.startswith('DEEPAGENT_'):
            del os.environ[key]

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def sample_agent():
    """Create a mock agent for testing."""
    class MockAgent:
        def __init__(self):
            self.workspace = None

        def stream(self, input_data, stream_mode="updates"):
            """Mock streaming method."""
            yield {"thinking": "Processing..."}
            yield {"response": "Mock response"}

    return MockAgent()
