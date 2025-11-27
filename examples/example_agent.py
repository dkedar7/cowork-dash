"""
Example agent configuration file.

This demonstrates how to create a custom agent file that can be loaded with:
    python app.py --agent example_agent.py:my_custom_agent

You can create multiple agent configurations and switch between them easily.
"""

from pathlib import Path
import os

# Example 1: Simple agent with DeepAgents
def create_simple_agent():
    """Create a basic DeepAgents agent."""
    try:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend

        workspace = Path("./example_workspace").resolve()
        workspace.mkdir(exist_ok=True, parents=True)

        backend = FilesystemBackend(root_dir=str(workspace), virtual_mode=True)

        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-20250514",
            system_prompt="""You are a helpful AI assistant with filesystem access.
            Be concise and helpful. Use the filesystem tools when appropriate.""",
            backend=backend
        )

        return agent
    except Exception as e:
        print(f"Failed to create simple agent: {e}")
        return None


# Example 2: Agent with custom tools
def create_agent_with_tools():
    """Create an agent with custom tools."""
    try:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
        from langchain_core.tools import tool

        @tool
        def get_weather(location: str) -> str:
            """Get weather for a location (mock example)."""
            return f"The weather in {location} is sunny and 72°F"

        workspace = Path("./example_workspace").resolve()
        workspace.mkdir(exist_ok=True, parents=True)

        backend = FilesystemBackend(root_dir=str(workspace), virtual_mode=True)

        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-20250514",
            system_prompt="""You are a helpful AI assistant with filesystem and weather tools.""",
            backend=backend,
            tools=[get_weather]
        )

        return agent
    except Exception as e:
        print(f"Failed to create agent with tools: {e}")
        return None


# Example 3: Agent with custom configuration
def create_research_agent():
    """Create an agent optimized for research tasks."""
    try:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend

        workspace = Path("./research_workspace").resolve()
        workspace.mkdir(exist_ok=True, parents=True)

        backend = FilesystemBackend(root_dir=str(workspace), virtual_mode=True)

        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-20250514",
            system_prompt="""You are a research assistant specializing in data analysis.

            When the user asks questions:
            1. Break down complex problems into steps
            2. Use filesystem tools to organize research
            3. Create summaries and documentation
            4. Visualize data when helpful

            Be thorough and systematic in your approach.""",
            backend=backend
        )

        return agent
    except Exception as e:
        print(f"Failed to create research agent: {e}")
        return None


# Export different agent variants
# You can switch between these by changing the object name in the CLI

# Default agent for this file
my_custom_agent = create_simple_agent()

# Alternative agents (commented out examples)
# my_custom_agent = create_agent_with_tools()
# my_custom_agent = create_research_agent()

# You can also export multiple agents and choose which one to use:
simple_agent = create_simple_agent()
tool_agent = create_agent_with_tools()
research_agent = create_research_agent()


# Usage examples:
# python app.py --agent example_agent.py:my_custom_agent
# python app.py --agent example_agent.py:simple_agent
# python app.py --agent example_agent.py:tool_agent
# python app.py --agent example_agent.py:research_agent
