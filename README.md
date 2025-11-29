# DeepAgent Dash

A web interface for AI agent interactions with filesystem workspace, canvas visualization, and real-time streaming.

## Features

- 🤖 **AI Agent Chat**: Real-time streaming with thinking process and task progress
- 📁 **File Browser**: Interactive file tree with lazy loading
- 🎨 **Canvas**: Visualize DataFrames, Plotly/Matplotlib charts, Mermaid diagrams, images
- ⚙️ **Flexible Configuration**: Environment variables, CLI args, or config file

## Quick Start

### Installation

```bash
pip install deepagent-dash
```

### Run

```bash
# Run with defaults (current directory as workspace, no agent)
deepagent-dash run

# Run with workspace
deepagent-dash run --workspace ~/my-workspace

# Run with custom agent (optional)
deepagent-dash run --agent my_agent.py:agent
```

Open browser to `http://localhost:8050`

## Configuration

### Priority (highest to lowest)

1. **CLI Arguments** - `--workspace`, `--port`, etc.
2. **Environment Variables** - `DEEPAGENT_*`
3. **Config File** - `config.py` defaults

### Environment Variables (optional)

```bash
export DEEPAGENT_WORKSPACE_ROOT=/path/to/workspace
export DEEPAGENT_AGENT_SPEC=my_agent.py:agent  # optional
export DEEPAGENT_PORT=9000                      # optional (default: 8050)
export DEEPAGENT_HOST=0.0.0.0                   # optional (default: localhost)
export DEEPAGENT_DEBUG=true                     # optional (default: false)
export DEEPAGENT_APP_TITLE="My App"             # optional
export DEEPAGENT_APP_SUBTITLE="Subtitle"        # optional

deepagent-dash run
```

### CLI Options (all optional)

```bash
deepagent-dash run [OPTIONS]

  --workspace PATH        Workspace directory (default: current directory)
  --agent PATH:OBJECT     Agent spec (default: none, manual mode)
  --port PORT            Server port (default: 8050)
  --host HOST            Server host (default: localhost)
  --debug                Enable debug mode
  --title TITLE          App title (default: "DeepAgent Dash")
  --subtitle TEXT        App subtitle (default: "AI-Powered Workspace")
```

### Python API

```python
from deepagent_dash import run_app

# Run with defaults
run_app()

# Run with custom settings (all optional)
run_app(
    workspace="~/my-workspace",
    agent_spec="my_agent.py:agent",  # optional
    port=8080,                        # optional
    debug=True                        # optional
)
```

## Agent Integration

### Workspace Access

DeepAgent Dash sets `DEEPAGENT_WORKSPACE_ROOT` environment variable for your agent:

```python
import os
from pathlib import Path

# In your agent code
workspace = Path(os.getenv('DEEPAGENT_WORKSPACE_ROOT', './'))

# Read/write files in workspace
config_file = workspace / "config.json"
```

### Agent Specification

Load agents using `path:object` format:

```bash
# Load from Python file
deepagent-dash run --agent agent.py:my_agent

# Absolute path
deepagent-dash run --agent /path/to/agent.py:agent_instance
```

### Agent Requirements

Your agent must implement:
- **Streaming**: `agent.stream(input, stream_mode="updates")`
- **Message format**: `{"messages": [{"role": "user", "content": "..."}]}`
- **Workspace access** (optional): Read `DEEPAGENT_WORKSPACE_ROOT` env var

### Example Agent Setup

```python
# my_agent.py
import os
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FileSystemBackend

backend = FileSystemBackend(root=os.getenv('DEEPAGENT_WORKSPACE_ROOT', './'))
my_agent = create_deep_agent(..., backend=backend)
```

Then run: `deepagent-dash run --agent my_agent.py:my_agent`

## Canvas

The canvas displays agent-created visualizations:

- **DataFrames**: HTML tables
- **Charts**: Plotly, Matplotlib
- **Images**: PNG, JPG, etc.
- **Diagrams**: Mermaid (flowcharts, sequence diagrams)
- **Markdown**: Text and notes

Content auto-saves to `canvas.md` and can be exported or cleared.

## Development

```bash
# Install from source
git clone https://github.com/dkedar7/deepagent-dash.git
cd deepagent-dash
pip install -e ".[dev]"

# Run tests
pytest

# Build package
python -m build
```

## Requirements

- Python 3.11+
- Dash 2.0+
- dash-mantine-components
- pandas, plotly, matplotlib, Pillow
- python-dotenv
- deepagents (optional, for AI agents)

## Links

- **PyPI**: https://pypi.org/project/deepagent-dash/
- **GitHub**: https://github.com/dkedar7/deepagent-dash
- **Issues**: https://github.com/dkedar7/deepagent-dash/issues

## License

MIT License - see [LICENSE](LICENSE) for details
