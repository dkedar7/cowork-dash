"""
Configuration file for Cowork Dash.

This file is OPTIONAL and provides sensible defaults. You typically don't need to edit it.

Configuration Priority (highest to lowest):
1. CLI arguments (--workspace, --port, etc.)
2. Environment variables (DEEPAGENT_*)
3. This config file defaults

For most use cases, prefer environment variables or CLI arguments:

  # Using environment variables (recommended for deployment)
  export DEEPAGENT_WORKSPACE_ROOT=/my/project
  export DEEPAGENT_PORT=9000
  cowork-dash run

  # Using CLI arguments (recommended for development)
  cowork-dash run --workspace /my/project --port 9000

Only edit this file if you want to set project-specific defaults that apply
when no environment variables or CLI arguments are provided.
"""

import os
from pathlib import Path


def get_config(key: str, default=None, type_cast=None):
    """
    Get configuration value with priority:
    1. Environment variable DEEPAGENT_{KEY}
    2. Default value

    Args:
        key: Configuration key (will be uppercased for env var)
        default: Default value if env var not set
        type_cast: Optional function to cast env var value

    Returns:
        Configuration value
    """
    env_value = os.getenv(f"DEEPAGENT_{key.upper()}")
    if env_value is not None:
        return type_cast(env_value) if type_cast else env_value
    return default


# Workspace root directory
# Environment variable: DEEPAGENT_WORKSPACE_ROOT
# CLI argument: --workspace
# Default: current directory
_workspace_path = get_config("workspace_root", default="./")
WORKSPACE_ROOT = Path(_workspace_path).resolve() if _workspace_path else Path("./").resolve()

# Agent specification (format: "module_path:variable_name")
# Environment variable: DEEPAGENT_SPEC (or DEEPAGENT_AGENT_SPEC for backwards compatibility)
# CLI argument: --agent
# Default: None (manual mode, no agent)
# Example: "mymodule:agent" or "/path/to/agent.py:my_agent"
_default_agent = str(Path(__file__).parent / "agent.py") + ":agent"
AGENT_SPEC = get_config("spec", default=None) or get_config("agent_spec", default=None) or _default_agent

# Application title
# Environment variable: DEEPAGENT_APP_TITLE
# CLI argument: --title
APP_TITLE = get_config("app_title", default="Cowork Dash")

# Application subtitle
# Environment variable: DEEPAGENT_APP_SUBTITLE
# CLI argument: --subtitle
APP_SUBTITLE = get_config("app_subtitle", default="AI-Powered Workspace")

# Server port
# Environment variable: DEEPAGENT_PORT
# CLI argument: --port
PORT = get_config("port", default=8050, type_cast=int)

# Server host (use "0.0.0.0" to allow external connections)
# Environment variable: DEEPAGENT_HOST
# CLI argument: --host
HOST = get_config("host", default="localhost")

# Debug mode (set to True for development, False for production)
# Environment variable: DEEPAGENT_DEBUG (accepts: true/1/yes)
# CLI argument: --debug
DEBUG = get_config(
    "debug",
    default=False,
    type_cast=lambda x: str(x).lower() in ("true", "1", "yes")
)
