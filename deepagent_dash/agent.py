import os
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from deepagent_dash.tools import add_to_canvas

SYSTEM_PROMPT = """You are a helpful AI assistant with access to a filesystem workspace.
You can browse, read, create, and modify files to help users with their tasks.

When working on tasks:
1. Use write_todos to track your progress and next steps
2. Use think_tool to reason through complex problems
3. Be proactive in exploring the filesystem when relevant
4. Provide clear, helpful responses

The workspace is your sandbox - feel free to create files, organize content, and help users manage their projects."""

backend = FilesystemBackend(root_dir=str("./"), virtual_mode=True)

agent = create_deep_agent(
    system_prompt=SYSTEM_PROMPT,
    backend=backend,
    tools=[add_to_canvas],
)