"""
DeepAgent Dash - AI Agent Web Interface

A modular Dash application providing a web interface for AI agent interactions
with filesystem workspace, canvas visualization, and real-time streaming.

Features:
- AI Agent Chat with real-time streaming
- File Browser with upload/download
- Canvas for visualizations (DataFrames, charts, diagrams)
- Real-time updates for thinking and task progress
- Support for Matplotlib, Plotly, Mermaid diagrams
- Resizable split-pane interface

Usage:
    # Command-line
    $ deepagent-dash init my-project
    $ cd my-project
    $ deepagent-dash run

    # Python API
    from deepagent_dash import run_app
    run_app(workspace="~/my-workspace", port=8080)
"""

__version__ = "0.1.0"
__author__ = "Kedar Dabhadkar"
__license__ = "MIT"

# Export main API
from .app import run_app

__all__ = ["run_app", "__version__"]
