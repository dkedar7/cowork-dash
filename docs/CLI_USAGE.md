# Command-Line Interface Usage

FastDash Browser supports command-line arguments to override configuration without modifying `config.py`.

## Quick Reference

```bash
python app.py [OPTIONS]

Options:
  --workspace PATH        Workspace directory path
  --agent PATH:OBJECT     Agent specification (e.g., "agent.py:agent")
  --port PORT            Port to run on
  --host HOST            Host to bind to (e.g., "0.0.0.0")
  --debug                Enable debug mode
  --no-debug             Disable debug mode
  --title TITLE          Application title
  -h, --help             Show help message
```

## Configuration Priority

Settings are applied in this order (highest to lowest priority):
1. **Command-line arguments** (highest)
2. **config.py** (defaults)

## Basic Usage

### Use Default Configuration

```bash
python app.py
```

Uses all settings from `config.py`.

### Override Port

```bash
python app.py --port 8080
```

Runs on port 8080 instead of the port specified in `config.py`.

### Change Workspace

```bash
python app.py --workspace ~/my-projects
```

Uses `~/my-projects` as the workspace directory.

### Enable Debug Mode

```bash
python app.py --debug
```

Enables Dash debug mode (auto-reload, detailed errors).

## Agent Specification

### Format

```
--agent PATH:OBJECT
```

Where:
- `PATH` is the path to a Python file (relative or absolute)
- `OBJECT` is the name of the agent object/variable in that file

### Examples

#### Use Default Agent from config.py

```bash
python app.py
```

#### Use Agent from agent.py

```bash
python app.py --agent agent.py:agent
```

Loads the `agent` object from `agent.py` in the current directory.

#### Use Custom Agent File

```bash
python app.py --agent /path/to/my_agents.py:custom_agent
```

Loads `custom_agent` from `/path/to/my_agents.py`.

#### Relative Path

```bash
python app.py --agent ./agents/production_agent.py:prod_agent
```

Loads `prod_agent` from `./agents/production_agent.py`.

### Creating Custom Agent Files

Your agent file should export an agent object:

**Example: `my_agent.py`**
```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from pathlib import Path

# Create your agent
backend = FilesystemBackend(root_dir="./workspace", virtual_mode=True)
my_agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-20250514",
    system_prompt="Custom system prompt",
    backend=backend
)
```

**Run with:**
```bash
python app.py --agent my_agent.py:my_agent
```

## Common Scenarios

### Development

```bash
# Quick testing with custom workspace
python app.py --debug --workspace /tmp/test-workspace
```

### Production Deployment

```bash
# Bind to all interfaces, no debug
python app.py --host 0.0.0.0 --port 80 --no-debug
```

### Testing Different Agents

```bash
# Test with agent A
python app.py --agent agents/agent_a.py:agent

# Test with agent B
python app.py --agent agents/agent_b.py:agent
```

### Custom Everything

```bash
python app.py \
  --workspace ~/my-workspace \
  --agent custom_agent.py:agent \
  --port 8080 \
  --host 0.0.0.0 \
  --title "My Custom Agent" \
  --debug
```

## Environment Variables

You can also use environment variables (loaded from `.env` file):

```bash
# .env file
ANTHROPIC_API_KEY=your_key_here
```

## Docker Example

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

# Expose port
EXPOSE 8050

# Run with production settings
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "8050", "--no-debug"]
```

## Error Handling

### Agent Not Found

```bash
$ python app.py --agent nonexistent.py:agent
Agent file not found: /path/to/nonexistent.py
```

### Invalid Agent Spec

```bash
$ python app.py --agent agent.py
Invalid agent spec 'agent.py'. Expected format: 'path/to/file.py:object_name'
```

### Object Not Found

```bash
$ python app.py --agent agent.py:nonexistent
Object 'nonexistent' not found in /path/to/agent.py
```

## Startup Banner

When you run the app, you'll see which settings came from CLI:

```
==================================================
  DeepAgent Dash
==================================================
  Workspace: /Users/you/my-workspace
    (from CLI: --workspace ~/my-workspace)
  Agent: Ready
    (from CLI: --agent agent.py:agent)
  URL: http://127.0.0.1:8080
  Debug: True
==================================================
```

## Advanced: Shell Scripts

Create wrapper scripts for common configurations:

**`dev.sh`**
```bash
#!/bin/bash
python app.py \
  --workspace ./dev-workspace \
  --port 8050 \
  --debug
```

**`prod.sh`**
```bash
#!/bin/bash
python app.py \
  --workspace /var/app/workspace \
  --host 0.0.0.0 \
  --port 80 \
  --no-debug \
  --agent /etc/app/production_agent.py:agent
```

Make executable:
```bash
chmod +x dev.sh prod.sh
```

Run:
```bash
./dev.sh    # Development
./prod.sh   # Production
```

## Tips

1. **Keep config.py for defaults**: Set sensible defaults in `config.py`, override with CLI as needed
2. **Use --debug for development**: Auto-reload on code changes
3. **Use --no-debug for production**: Better performance, hide internal errors
4. **Agent files are isolated**: Each agent file can have its own dependencies and configuration
5. **Workspace paths are resolved**: Relative paths like `./workspace` or `~/projects` work correctly

## Troubleshooting

### Port Already in Use

```bash
# Try a different port
python app.py --port 8051
```

### Permission Denied (Port 80)

```bash
# Use sudo for privileged ports
sudo python app.py --port 80 --host 0.0.0.0

# Or use a higher port
python app.py --port 8080 --host 0.0.0.0
```

### Workspace Permission Issues

```bash
# Ensure workspace exists and is writable
mkdir -p ~/my-workspace
chmod 755 ~/my-workspace
python app.py --workspace ~/my-workspace
```
