#!/usr/bin/env python3
"""Command-line interface for DeepAgent Dash."""

import sys
import shutil
from pathlib import Path
import argparse


def init_project(name: str, template: str = "default"):
    """Initialize a new DeepAgent Dash project."""
    project_dir = Path(name).resolve()

    if project_dir.exists():
        print(f"❌ Error: Directory '{name}' already exists")
        return 1

    print(f"📦 Creating project: {project_dir}")

    # Create project structure
    project_dir.mkdir(parents=True)
    workspace_dir = project_dir / "workspace"
    workspace_dir.mkdir()

    # Copy config template
    import deepagent_dash
    package_dir = Path(deepagent_dash.__file__).parent
    template_file = package_dir / "config_template.py"

    if not template_file.exists():
        print(f"❌ Error: Template not found at {template_file}")
        return 1

    shutil.copy(template_file, project_dir / "config.py")

    # Create .env template
    env_template = """# DeepAgent Dash Environment Variables

# API Keys
ANTHROPIC_API_KEY=your_api_key_here

# Optional: Override config.py settings
# WORKSPACE_ROOT=./workspace
# PORT=8050
# HOST=127.0.0.1
# DEBUG=False
"""
    (project_dir / ".env.example").write_text(env_template)

    # Create .gitignore
    gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/

# DeepAgent Dash
.env
workspace/
canvas.md
.canvas/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo
"""
    (project_dir / ".gitignore").write_text(gitignore)

    # Create README
    readme = f"""# {name}

A DeepAgent Dash project.

## Setup

1. **Configure your API key** (if using DeepAgents):
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

2. **Edit config.py** to customize your agent and settings

3. **Run the application**:
   ```bash
   deepagent-dash run
   ```

## Usage

```bash
# Run with defaults from config.py
deepagent-dash run

# Override settings
deepagent-dash run --port 8080 --debug

# Use custom agent
deepagent-dash run --agent my_agent.py:agent

# See all options
deepagent-dash run --help
```

## Project Structure

```
{name}/
├── config.py          # Main configuration (edit this)
├── workspace/         # Your agent's workspace
├── .env.example       # Environment variables template
└── .gitignore         # Git ignore patterns
```

## Documentation

- [DeepAgent Dash Documentation](https://github.com/yourusername/deepagent-dash)
- [CLI Usage Guide](https://github.com/yourusername/deepagent-dash/blob/main/docs/CLI_USAGE.md)
"""
    (project_dir / "README.md").write_text(readme)

    print(f"✓ Created project structure")
    print(f"✓ Created config.py")
    print(f"✓ Created workspace/")
    print(f"✓ Created .env.example")
    print(f"✓ Created .gitignore")
    print(f"✓ Created README.md")
    print(f"\n{'='*50}")
    print(f"🎉 Project '{name}' created successfully!")
    print(f"{'='*50}\n")
    print(f"Next steps:")
    print(f"  1. cd {name}")
    print(f"  2. cp .env.example .env  # If using DeepAgents")
    print(f"  3. Edit .env and add your ANTHROPIC_API_KEY")
    print(f"  4. Edit config.py to customize your agent")
    print(f"  5. deepagent-dash run")
    print()

    return 0


def run_app_cli(args):
    """Run the application with CLI arguments."""
    # Import here to avoid loading Dash when just running init
    from .app import run_app

    return run_app(
        workspace=args.workspace,
        agent_spec=args.agent,
        port=args.port,
        host=args.host,
        debug=args.debug,
        title=args.title,
        config_file=args.config
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="deepagent-dash",
        description="DeepAgent Dash - AI Agent Web Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize a new project
  deepagent-dash init my-agent-project

  # Run with defaults from config.py
  deepagent-dash run

  # Run with custom settings
  deepagent-dash run --workspace ~/projects --port 8080

  # Run with custom agent
  deepagent-dash run --agent my_agent.py:agent

  # Debug mode
  deepagent-dash run --debug

For more help: https://github.com/yourusername/deepagent-dash
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # deepagent-dash init
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a new project",
        description="Create a new DeepAgent Dash project with config template"
    )
    init_parser.add_argument("name", help="Project name/directory")
    init_parser.add_argument(
        "--template",
        default="default",
        help="Template to use (default: default)"
    )

    # deepagent-dash run
    run_parser = subparsers.add_parser(
        "run",
        help="Run the application",
        description="Run DeepAgent Dash with optional configuration overrides"
    )
    run_parser.add_argument(
        "--workspace",
        type=str,
        help="Workspace directory path (overrides config.py)"
    )
    run_parser.add_argument(
        "--agent",
        type=str,
        metavar="PATH:OBJECT",
        help='Agent specification as "path/to/file.py:object_name"'
    )
    run_parser.add_argument(
        "--port",
        type=int,
        help="Port to run on (overrides config.py)"
    )
    run_parser.add_argument(
        "--host",
        type=str,
        help="Host to bind to (overrides config.py)"
    )
    run_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    run_parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Disable debug mode"
    )
    run_parser.add_argument(
        "--title",
        type=str,
        help="Application title (overrides config.py)"
    )
    run_parser.add_argument(
        "--config",
        type=str,
        default="./config.py",
        help="Config file path (default: ./config.py)"
    )

    # Parse arguments
    args = parser.parse_args()

    # Handle commands
    if args.command == "init":
        return init_project(args.name, args.template)

    elif args.command == "run":
        return run_app_cli(args)

    else:
        # No command provided - show help
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
