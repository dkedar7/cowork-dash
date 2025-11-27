"""
Configuration file for DeepAgent Dash.
"""

from pathlib import Path

# Set your workspace root directory
# Default: current directory
# Examples:
#   WORKSPACE_ROOT = Path("/Users/yourname/projects")
#   WORKSPACE_ROOT = Path("~/Documents/workspace").expanduser()
#   WORKSPACE_ROOT = Path("./my_workspace")
WORKSPACE_ROOT = Path("./").resolve()

# Ensure workspace exists
WORKSPACE_ROOT.mkdir(exist_ok=True, parents=True)

# Agent configuration
agent_path = Path(__file__).parent / "agent.py"
AGENT_SPEC = f"{agent_path}:agent"  # Format: "module_path:variable_name"

# Application title
APP_TITLE = "DeepAgent Dash"

# Port to run the server on
PORT = 8050

# Host to bind to (use "0.0.0.0" to allow external connections)
HOST = "localhost"

# Debug mode (set to False in production)
DEBUG = False
