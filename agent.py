import os
from pathlib import Path
from typing import Any, Dict
from canvas_utils import add_to_canvas

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend


WORKSPACE_ROOT = Path("./").resolve()
WORKSPACE_ROOT.mkdir(exist_ok=True)

# Wrapper that doesn't require workspace_root parameter for agent tool
def _add_to_canvas_tool(content: Any) -> Dict[str, Any]:
    """Wrapper for add_to_canvas that automatically passes WORKSPACE_ROOT."""
    return add_to_canvas(content, WORKSPACE_ROOT)


SYSTEM_PROMPT = """You are a helpful AI assistant with access to a filesystem workspace.
You can browse, read, create, and modify files to help users with their tasks.

When working on tasks:
1. Use write_todos to track your progress and next steps
2. Use think_tool to reason through complex problems
3. Use add_to_canvas to show visualizations, charts, tables, and images on the collaborative canvas
4. Be proactive in exploring the filesystem when relevant
5. Provide clear, helpful responses

The workspace is your sandbox - feel free to create files, organize content, and help users manage their projects.

Canvas Usage:
- Use add_to_canvas to display Python objects like pandas DataFrames, matplotlib figures, plotly charts, or PIL images
- You can also add markdown content to the canvas
- The canvas automatically exports to a markdown file for easy sharing
- Use the canvas to create a visual record of your work and insights"""


backend = FilesystemBackend(root_dir=str(WORKSPACE_ROOT), virtual_mode=True)

# Add custom tools
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-20250514",
    system_prompt=SYSTEM_PROMPT,
    backend=backend,
    tools=[_add_to_canvas_tool]  # Add canvas tool
)