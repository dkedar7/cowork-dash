"""
Example of using DeepAgent Dash Python API.

This demonstrates how to create an agent in Python and run the app
in the same script using the direct agent instance approach.
"""

import os
from pathlib import Path
from deepagent_dash import run_app


# Example 1: Simple usage with agent instance
def example_1_simple():
    """Simplest way to run the app with an agent."""
    try:
        from deepagents import create_deep_agent
        from deepagents.backends.filesystem import FileSystemBackend

        # Get workspace from environment or use default
        workspace = Path(os.getenv('DEEPAGENT_WORKSPACE_ROOT', './workspace'))
        workspace.mkdir(exist_ok=True, parents=True)

        # Create agent
        backend = FileSystemBackend(root=str(workspace))
        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-20250514",
            system_prompt="You are a helpful AI assistant.",
            backend=backend
        )

        # Run app with agent instance
        run_app(agent, workspace=str(workspace))

    except ImportError:
        print("deepagents not installed. Install with: pip install deepagents")
        print("Or reinstall deepagent-dash: pip install deepagent-dash")

# Example 2: Using agent spec (alternative approach)
def example_2_agent_spec():
    """Run app by specifying agent file and object."""
    run_app(
        agent_spec="example_agent.py:simple_agent",
        workspace="~/my-workspace",
        port=8080
    )


# Example 3: Manual mode (default agent)
def example_3_manual_mode():
    """Run app without an agent for manual file browsing."""
    run_app(
        workspace="~/my-workspace",
        port=8080,
        title="File Browser",
        subtitle="Manual Mode"
    )


if __name__ == "__main__":
    # Uncomment the example you want to run:

    example_1_simple()
    # example_2_agent_spec()
    # example_3_manual_mode()