# DeepAgent Dash

A modular Dash application providing a web interface for AI agent interactions with filesystem workspace, canvas visualization, and real-time streaming.

## Features

- 🤖 **AI Agent Chat**: Real-time streaming chat interface with thinking and task progress
- 📁 **File Browser**: Interactive file tree with upload/download capabilities
- 🎨 **Canvas**: Visualize DataFrames, charts, images, and diagrams
- 🔄 **Real-time Updates**: Live agent thinking and task progress
- 📊 **Rich Visualizations**: Support for Matplotlib, Plotly, Mermaid diagrams
- 🎛️ **Resizable Panels**: Adjustable split view
- ⚙️ **Flexible Configuration**: config.py or command-line arguments
- 📦 **Easy Distribution**: pip-installable package

## Quick Start

### Installation

**Option 1: Install from PyPI** (recommended)
```bash
pip install deepagent-dash
```

**Option 2: Install from source**
```bash
git clone https://github.com/dkedar7/deepagent-dash.git
cd deepagent-dash
pip install -e .
```

### Initialize a Project

```bash
# Create a new project
deepagent-dash init my-agent-project

# Navigate to project
cd my-agent-project

# Set up environment (if using DeepAgents)
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Edit config.py to customize your agent

# Run the application
deepagent-dash run
```

Then open your browser to `http://127.0.0.1:8050`

### Quick Run (without project)

```bash
# Run with defaults
deepagent-dash run

# Run with custom settings
deepagent-dash run --workspace ~/my-workspace --port 8080

# Run with custom agent
deepagent-dash run --agent my_agent.py:agent --debug
```

## Usage

### Command-Line Interface

```bash
# Initialize new project
deepagent-dash init my-project

# Run application
deepagent-dash run [OPTIONS]

Options:
  --workspace PATH        Workspace directory path
  --agent PATH:OBJECT     Agent specification (e.g., "agent.py:agent")
  --port PORT            Port to run on (default: 8050)
  --host HOST            Host to bind to (default: 127.0.0.1)
  --debug                Enable debug mode
  --no-debug             Disable debug mode
  --title TITLE          Application title
  --config PATH          Config file path (default: ./config.py)
  --help                 Show help message

# Examples
deepagent-dash run --workspace ~/projects --port 8080 --debug
deepagent-dash run --agent custom_agent.py:my_agent
```

> 💡 See [docs/CLI_USAGE.md](docs/CLI_USAGE.md) for detailed command-line documentation

### Python API

```python
from deepagent_dash import run_app

# Run with defaults
run_app()

# Run with custom configuration
run_app(
    workspace="~/my-workspace",
    port=8080,
    debug=True
)

# Run with custom agent
run_app(
    agent_spec="my_agent.py:custom_agent",
    workspace="~/projects"
)
```

### Configuration File

When you run `deepagent-dash init`, a `config.py` file is created:

```python
from pathlib import Path

# Set your workspace directory
WORKSPACE_ROOT = Path("./workspace").resolve()

# Configure your agent
def get_agent():
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend

    backend = FilesystemBackend(root_dir=str(WORKSPACE_ROOT), virtual_mode=True)
    agent = create_deep_agent(
        model="anthropic:claude-sonnet-4-20250514",
        system_prompt="Your custom system prompt here",
        backend=backend
    )
    return agent, None

# UI Configuration
APP_TITLE = "DeepAgent Dash"
PORT = 8050
HOST = "127.0.0.1"
DEBUG = False
```

## Project Structure

### Installed Package

```
deepagent-dash/
├── pyproject.toml         # Package configuration
├── README.md              # This file
├── LICENSE                # MIT License
├── deepagent_dash/       # Main package
│   ├── __init__.py       # Package exports
│   ├── __main__.py       # python -m deepagent_dash
│   ├── cli.py            # Command-line interface
│   ├── app.py            # Main application
│   ├── canvas.py   # Canvas functionality
│   ├── file_utils.py     # File operations
│   ├── components.py     # UI components
│   ├── config.py # Template for init
│   ├── assets/           # CSS, JavaScript
│   └── templates/        # HTML templates
├── examples/             # Example agents
└── docs/                 # Documentation
```

### Created Project (after `deepagent-dash init`)

```
my-project/
├── config.py             # Your configuration (edit this)
├── workspace/            # Your agent's workspace
├── .env.example          # Environment variables template
├── .env                  # Your environment variables (create this)
├── .gitignore           # Git ignore patterns
└── README.md            # Project README
```

## Agent Integration

### Using DeepAgents

```python
# In your config.py
def get_agent():
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend

    backend = FilesystemBackend(root_dir=str(WORKSPACE_ROOT), virtual_mode=True)
    agent = create_deep_agent(
        model="anthropic:claude-sonnet-4-20250514",
        system_prompt="Your prompt here",
        backend=backend
    )
    return agent, None
```

### Custom Agent

```python
# In your config.py
def get_agent():
    from my_agent_library import MyAgent

    agent = MyAgent(workspace=str(WORKSPACE_ROOT))
    return agent, None
```

Your agent must support:
- Streaming: `agent.stream(input, stream_mode="updates")`
- Message format: `{"messages": [{"role": "user", "content": "..."}]}`

### Agent Specification Format

Load agents from any Python file using the `path:object` pattern:

```bash
# Load 'agent' from agent.py
deepagent-dash run --agent agent.py:agent

# Load 'custom_agent' from my_agents.py
deepagent-dash run --agent my_agents.py:custom_agent

# Absolute path
deepagent-dash run --agent /path/to/agents.py:prod_agent
```

See [examples/example_agent.py](examples/example_agent.py) for examples.

## Features

### Chat Interface

- Real-time streaming responses
- Thinking process display (expandable)
- Task progress tracking
- Message history

### File Browser

- Interactive file tree with collapsible folders
- File upload and download
- View text files in modal
- Download any file

### Canvas

The canvas displays visualizations created by the agent:

- **DataFrames**: Interactive HTML tables
- **Charts**: Matplotlib and Plotly visualizations
- **Images**: PNG, JPG, etc.
- **Diagrams**: Mermaid flowcharts, sequence diagrams, etc.
- **Markdown**: Formatted text and notes

Canvas content auto-saves to `canvas.md` and can be:
- Exported to markdown
- Downloaded as a file
- Cleared for a fresh start

## Development

### Install for Development

```bash
git clone https://github.com/dkedar7/deepagent-dash.git
cd deepagent-dash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Build Package

```bash
python -m build
```

### Publish to PyPI

```bash
twine upload dist/*
```

## Documentation

- [CLI Usage Guide](docs/CLI_USAGE.md) - Detailed command-line documentation
- [Architecture](docs/ARCHITECTURE.md) - Technical architecture details
- [Examples](examples/) - Example agent configurations

## Requirements

- Python 3.11+
- Dash 2.0+
- dash-mantine-components
- pandas
- plotly
- matplotlib
- Pillow

Optional:
- deepagents (for DeepAgents integration)
- python-dotenv (for environment variables)

## Troubleshooting

### Agent Not Working

Check your `config.py`:
- Is `ANTHROPIC_API_KEY` set in `.env` file?
- Is DeepAgents installed? (`pip install deepagents`)
- Does `get_agent()` return `(agent, error_message)` format?

### Canvas Not Updating

- Check browser console for errors
- Verify Mermaid.js CDN is accessible
- Check `.canvas/` folder permissions

### Import Errors

```bash
# Reinstall package
pip uninstall deepagent-dash
pip install deepagent-dash

# Or for development
pip install -e .
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details

## Acknowledgments

Built with:
- [Dash](https://dash.plotly.com/) - Web framework
- [Plotly](https://plotly.com/) - Interactive charts
- [Mermaid.js](https://mermaid.js.org/) - Diagrams
- [DeepAgents](https://github.com/langchain-ai/deepagents) - AI agent framework (optional)

## Links

- **Homepage**: https://github.com/dkedar7/deepagent-dash
- **Documentation**: https://github.com/dkedar7/deepagent-dash/blob/main/README.md
- **PyPI**: https://pypi.org/project/deepagent-dash/
- **Issues**: https://github.com/dkedar7/deepagent-dash/issues
