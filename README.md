# FastDash Browser

A modular Dash application providing a web interface for AI agent interactions with filesystem workspace, canvas visualization, and real-time streaming.

## Features

- 🤖 **AI Agent Chat**: Real-time streaming chat interface with thinking and task progress
- 📁 **File Browser**: Interactive file tree with upload/download capabilities
- 🎨 **Canvas**: Visualize DataFrames, charts, images, and diagrams
- 🔄 **Real-time Updates**: Live agent thinking and task progress
- 📊 **Rich Visualizations**: Support for Matplotlib, Plotly, Mermaid diagrams
- 🎛️ **Resizable Panels**: Adjustable split view

## Quick Start

### Installation

```bash
# Clone or download the repository
git clone <your-repo-url>
cd fastdash-browser

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Edit `config.py` to customize your setup:

```python
from pathlib import Path

# Set your workspace directory
WORKSPACE_ROOT = Path("~/my-workspace").expanduser()

# Configure your agent
def get_agent():
    from deepagents import create_deep_agent
    from canvas_utils import add_to_canvas

    # Wrapper to pass workspace_root automatically
    def _add_to_canvas_tool(content):
        return add_to_canvas(content, WORKSPACE_ROOT)

    agent = create_deep_agent(
        model="anthropic:claude-sonnet-4-20250514",
        system_prompt="Your custom system prompt here",
        tools=[_add_to_canvas_tool]
    )
    return agent, None

# UI Configuration
APP_TITLE = "My AI Assistant"
PORT = 8050
HOST = "127.0.0.1"
DEBUG = False
```

### Running

**Option 1: Use defaults from config.py**
```bash
python app.py
```

**Option 2: Override with command-line arguments**
```bash
# Use custom workspace and port
python app.py --workspace ~/my-workspace --port 8080

# Use different agent
python app.py --agent my_agent.py:agent

# Enable debug mode
python app.py --debug

# See all options
python app.py --help
```

Then open your browser to `http://127.0.0.1:8050` (or your specified port)

> 💡 See [CLI_USAGE.md](CLI_USAGE.md) for detailed command-line documentation

## Project Structure

```
fastdash-browser/
├── app.py                 # Main application (DO NOT MODIFY)
├── config.py             # User configuration (MODIFY THIS)
├── canvas_utils.py       # Canvas parsing and persistence
├── file_utils.py         # File tree and I/O operations
├── components.py         # UI component rendering
├── assets/
│   ├── app.js           # JavaScript (resize, Mermaid)
│   └── styles.css       # CSS styling
├── templates/
│   └── index.html       # HTML template
└── .canvas/             # Canvas assets (auto-generated)
```

## Usage

### Chat with Agent

Type your message in the chat input and press Enter or click Send. The agent will:
- Stream responses in real-time
- Show thinking process (expandable)
- Display task progress
- Update the canvas with visualizations

### File Browser

- **Browse**: Click folders to expand/collapse
- **View**: Click files to view content
- **Download**: Click download icon next to files
- **Upload**: Use the upload area to add files

### Canvas

The canvas displays visualizations created by the agent:
- **DataFrames**: Interactive tables
- **Charts**: Matplotlib and Plotly visualizations
- **Images**: PNG, JPG, etc.
- **Diagrams**: Mermaid flowcharts, sequence diagrams, etc.
- **Markdown**: Formatted text and notes

Canvas content is automatically saved to `canvas.md` and can be:
- Exported to markdown
- Downloaded as a file
- Cleared for a fresh start

### Keyboard Shortcuts

- `Enter`: Send message (in chat input)
- `Shift + Enter`: New line (in chat input)

## Customization

### Adding Custom Agent

Implement your agent in `config.py`:

```python
def get_agent():
    from my_agent_library import MyAgent

    agent = MyAgent(
        workspace=str(WORKSPACE_ROOT),
        # your configuration
    )
    return agent, None
```

Your agent must support:
- Streaming: `agent.stream(input, stream_mode="updates")`
- Message format: `{"messages": [{"role": "user", "content": "..."}]}`

### Canvas Integration

To enable canvas in your agent, provide the `add_to_canvas` tool:

```python
from canvas_utils import add_to_canvas

def get_agent():
    # Create wrapper that automatically passes WORKSPACE_ROOT
    def _add_to_canvas_tool(content):
        return add_to_canvas(content, WORKSPACE_ROOT)

    # Pass tool to your agent
    agent = create_agent(tools=[_add_to_canvas_tool])
    return agent, None
```

The tool supports:
- Pandas DataFrames
- Matplotlib figures
- Plotly charts
- PIL Images
- Markdown strings
- Mermaid diagram code

### Styling

Edit `assets/styles.css` to customize appearance:

```css
/* Change accent color */
:root {
    --accent: #1a73e8;  /* Change this */
}
```

### UI Layout

Modify the layout in `app.py` if you need structural changes (though try to keep core logic intact).

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation on:
- Module responsibilities
- Configuration workflow
- Agent integration
- Canvas persistence strategy
- Performance considerations
- Extension points

## Canvas Persistence

Canvas content is saved to `canvas.md` with a hybrid approach:

### Inline Content
Lightweight items stored directly in markdown:
- Markdown text
- DataFrames (as HTML)
- Mermaid diagrams

### External Assets
Heavy items saved to `.canvas/` folder:
- Matplotlib/PIL images → `.canvas/matplotlib_timestamp.png`
- Plotly charts → `.canvas/plotly_timestamp.json`

This keeps `canvas.md` readable while handling large visualizations efficiently.

## Troubleshooting

### Agent Not Working

Check `config.py`:
- Is `ANTHROPIC_API_KEY` set in environment or `.env` file?
- Is DeepAgents installed? (`pip install deepagents`)
- Does `get_agent()` return the correct format `(agent, error_message)`?

### Canvas Not Updating

- Check browser console for JavaScript errors
- Verify Mermaid.js CDN is accessible
- Check `.canvas/` folder permissions

### File Browser Issues

- Verify `WORKSPACE_ROOT` path exists
- Check file permissions
- Ensure workspace is not a symbolic link (or adjust code)

### Resize Not Working

- Check that `assets/app.js` is loaded (view source)
- Verify browser console for errors
- Try refreshing the page

## Requirements

- Python 3.8+
- Dash 2.0+
- dash-mantine-components
- pandas (for DataFrames)
- plotly (for charts)
- matplotlib (for plots)
- PIL/Pillow (for images)

Optional:
- deepagents (if using DeepAgents)
- python-dotenv (for environment variables)

## Development

### Running in Debug Mode

Set in `config.py`:
```python
DEBUG = True
```

This enables:
- Auto-reload on code changes
- Detailed error messages
- Dash debug menu

### Adding New Canvas Types

Edit `canvas_utils.py` → `parse_canvas_object()`:

```python
def parse_canvas_object(obj: Any, workspace_root: Path) -> Dict[str, Any]:
    # Add your type check
    if isinstance(obj, MyCustomType):
        return {
            "type": "my_custom_type",
            "data": obj.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    # ... existing code
```

Then add rendering in `components.py` → `render_canvas_items()`:

```python
elif item_type == "my_custom_type":
    # Your rendering code
    rendered_items.append(
        html.Div([...])
    )
```

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

## Support

For issues and questions:
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for detailed docs
- Review `config.py` examples
- Check browser console and terminal for errors

## Acknowledgments

Built with:
- [Dash](https://dash.plotly.com/) - Web framework
- [Plotly](https://plotly.com/) - Interactive charts
- [Mermaid.js](https://mermaid.js.org/) - Diagrams
- [DeepAgents](https://github.com/langchain-ai/deepagents) - AI agent framework (optional)
