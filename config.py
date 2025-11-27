"""
Configuration file for FastDash Browser.

Users should modify this file to customize their setup:
- Set WORKSPACE_ROOT to their desired working directory
- Configure their agent implementation
- Adjust other settings as needed
"""

from pathlib import Path

# =============================================================================
# WORKSPACE CONFIGURATION
# =============================================================================

# Set your workspace root directory
# Default: current directory
# Examples:
#   WORKSPACE_ROOT = Path("/Users/yourname/projects")
#   WORKSPACE_ROOT = Path("~/Documents/workspace").expanduser()
#   WORKSPACE_ROOT = Path("./my_workspace")
WORKSPACE_ROOT = Path("./").resolve()

# Ensure workspace exists
WORKSPACE_ROOT.mkdir(exist_ok=True, parents=True)


# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

def get_agent():
    """
    Configure and return your agent instance.

    Users should modify this function to use their own agent implementation.

    Returns:
        agent: Your configured agent instance, or None if not available
        error: Error message if agent setup failed, or None if successful

    Example with DeepAgents:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend

        backend = FilesystemBackend(root_dir=str(WORKSPACE_ROOT), virtual_mode=True)
        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-20250514",
            system_prompt="Your system prompt here",
            backend=backend,
            tools=[your_custom_tools]
        )
        return agent, None

    Example with custom agent:
        from my_agent import MyAgent

        agent = MyAgent(workspace=WORKSPACE_ROOT)
        return agent, None

    Example when agent is not available:
        return None, "Agent not configured"
    """
    # Add your agent here
    from agent import agent
    return agent


# =============================================================================
# UI CONFIGURATION
# =============================================================================

# Application title
APP_TITLE = "DeepAgents Dash"

# Port to run the server on
PORT = 8050

# Host to bind to (use "0.0.0.0" to allow external connections)
HOST = "localhost"

# Debug mode (set to False in production)
DEBUG = False
