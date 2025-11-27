"""
Configuration file for DeepAgent Dash.

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
WORKSPACE_ROOT = Path("./workspace").resolve()

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
    import os
    from dotenv import load_dotenv
    load_dotenv()

    SYSTEM_PROMPT = """You are a helpful AI assistant with access to a filesystem workspace.
You can browse, read, create, and modify files to help users with their tasks.

When working on tasks:
1. Use write_todos to track your progress and next steps
2. Use think_tool to reason through complex problems
3. Be proactive in exploring the filesystem when relevant
4. Provide clear, helpful responses

The workspace is your sandbox - feel free to create files, organize content, and help users manage their projects."""

    try:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend

        if not os.environ.get("ANTHROPIC_API_KEY"):
            return None, "ANTHROPIC_API_KEY not set in environment"

        backend = FilesystemBackend(root_dir=str(WORKSPACE_ROOT), virtual_mode=True)

        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-20250514",
            system_prompt=SYSTEM_PROMPT,
            backend=backend,
        )

        print("✓ DeepAgents loaded successfully")
        return agent, None

    except ImportError as e:
        return None, f"DeepAgents not installed: {e}\n\nInstall with: pip install deepagents"
    except Exception as e:
        return None, f"Agent creation failed: {e}"


# =============================================================================
# UI CONFIGURATION
# =============================================================================

# Application title
APP_TITLE = "DeepAgent Dash"

# Port to run the server on
PORT = 8050

# Host to bind to (use "0.0.0.0" to allow external connections)
HOST = "127.0.0.1"

# Debug mode (set to False in production)
DEBUG = False
