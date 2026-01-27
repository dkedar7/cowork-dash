"""Pytest configuration and fixtures."""

import os
import pytest


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


# =============================================================================
# CANVAS FIXTURES
# =============================================================================


@pytest.fixture
def sample_canvas_items():
    """Create sample canvas items for testing."""
    return [
        {
            "id": "canvas_markdown1",
            "type": "markdown",
            "data": "# Sample Heading\n\nSome content here.",
            "title": "Sample Markdown"
        },
        {
            "id": "canvas_mermaid1",
            "type": "mermaid",
            "data": "graph TD\n    A --> B\n    B --> C"
        },
        {
            "id": "canvas_markdown2",
            "type": "markdown",
            "data": "- Item 1\n- Item 2\n- Item 3"
        }
    ]


# =============================================================================
# CLEANUP FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def reset_global_session_manager():
    """Reset the global session manager between tests."""
    yield
    # Clear any sessions created during tests
    from cowork_dash.virtual_fs import get_session_manager
    sm = get_session_manager()
    for session_id in list(sm._sessions.keys()):
        sm.delete_session(session_id)
