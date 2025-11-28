import uuid
import sys
import json
import base64
import re
import shutil
import platform
import subprocess
import threading
import time
import argparse
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
load_dotenv()

from dash import Dash, html, dcc, Input, Output, State, callback_context, no_update, ALL
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc

# Import custom modules
from canvas import parse_canvas_object, export_canvas_to_markdown, load_canvas_from_markdown
from file_utils import build_file_tree, render_file_tree, read_file_content, get_file_download_data
from components import (
    format_message, format_loading, format_thinking, format_todos,
    format_todos_inline, render_canvas_items
)

# Import configuration defaults
import config

# Generate thread ID
thread_id = str(uuid.uuid4())

# Parse command-line arguments early
def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="FastDash Browser - AI Agent Web Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use defaults from config.py
  python app.py

  # Override workspace and port
  python app.py --workspace ~/my-workspace --port 8080

  # Use custom agent from file
  python app.py --agent my_agents.py:my_agent

  # Production mode
  python app.py --host 0.0.0.0 --port 80 --no-debug

  # Debug mode with custom workspace
  python app.py --debug --workspace /tmp/test-workspace
        """
    )

    parser.add_argument(
        "--workspace",
        type=str,
        help="Workspace directory path (default: from config.py)"
    )

    parser.add_argument(
        "--agent",
        type=str,
        metavar="PATH:OBJECT",
        help='Agent specification as "path/to/file.py:object_name" (e.g., "agent.py:agent" or "my_agents.py:custom_agent")'
    )

    parser.add_argument(
        "--port",
        type=int,
        help="Port to run on (default: from config.py)"
    )

    parser.add_argument(
        "--host",
        type=str,
        help="Host to bind to (default: from config.py)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Disable debug mode"
    )

    parser.add_argument(
        "--title",
        type=str,
        help="Application title (default: from config.py)"
    )

    parser.add_argument(
        "--subtitle",
        type=str,
        help="Application subtitle (default: from config.py)"
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (default: config.py)"
    )

    return parser.parse_args()

def load_agent_from_spec(agent_spec: str):
    """
    Load agent from specification string in format "path/to/file.py:object_name".

    Args:
        agent_spec: String like "agent.py:agent" or "my_agents.py:custom_agent"

    Returns:
        tuple: (agent_object, error_message)
    """
    try:
        # Parse the spec
        if ":" not in agent_spec:
            return None, f"Invalid agent spec '{agent_spec}'. Expected format: 'path/to/file.py:object_name'"

        file_path, object_name = agent_spec.rsplit(":", 1)
        file_path = Path(file_path).resolve()

        if not file_path.exists():
            return None, f"Agent file not found: {file_path}"

        # Load the module
        spec = importlib.util.spec_from_file_location("custom_agent_module", file_path)
        if spec is None or spec.loader is None:
            return None, f"Failed to load module from {file_path}"

        module = importlib.util.module_from_spec(spec)
        sys.modules["custom_agent_module"] = module
        spec.loader.exec_module(module)

        # Get the object
        if not hasattr(module, object_name):
            return None, f"Object '{object_name}' not found in {file_path}"

        agent = getattr(module, object_name)
        return agent, None

    except Exception as e:
        return None, f"Failed to load agent from {agent_spec}: {e}"

# Parse CLI arguments
args = parse_args()

# Apply configuration with CLI overrides
WORKSPACE_ROOT = Path(args.workspace).resolve() if args.workspace else config.WORKSPACE_ROOT
APP_TITLE = args.title if args.title else config.APP_TITLE
APP_SUBTITLE = args.subtitle if args.subtitle else config.APP_SUBTITLE
PORT = args.port if args.port else config.PORT
HOST = args.host if args.host else config.HOST

# Handle debug flag
if args.debug:
    DEBUG = True
elif args.no_debug:
    DEBUG = False
else:
    DEBUG = config.DEBUG

# Ensure workspace exists
WORKSPACE_ROOT.mkdir(exist_ok=True, parents=True)

# Initialize agent with override support
if args.agent:
    # Load agent from CLI specification
    agent, agent_error = load_agent_from_spec(args.agent)
    AGENT_ERROR = agent_error
else:
    # Use agent from config.py
    agent, AGENT_ERROR = load_agent_from_spec(config.AGENT_SPEC)


# =============================================================================
# STYLING
# =============================================================================

COLORS = {
    "bg_primary": "#ffffff",
    "bg_secondary": "#f8f9fa",
    "bg_tertiary": "#f1f3f4",
    "bg_hover": "#e8eaed",
    "accent": "#1a73e8",
    "accent_light": "#e8f0fe",
    "accent_dark": "#1557b0",
    "text_primary": "#202124",
    "text_secondary": "#5f6368",
    "text_muted": "#80868b",
    "border": "#dadce0",
    "border_light": "#e8eaed",
    "success": "#1e8e3e",
    "warning": "#f9ab00",
    "error": "#d93025",
    "thinking": "#7c4dff",
    "todo": "#00897b",
}

STYLES = {
    "shadow": "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08)",
    "transition": "all 0.15s ease",
}

# Note: File utilities imported from file_utils module
# No local wrappers needed - file_utils functions will be called with WORKSPACE_ROOT

# =============================================================================
# AGENT INTERACTION - WITH REAL-TIME STREAMING
# =============================================================================

# Global state for streaming updates
_agent_state = {
    "running": False,
    "thinking": "",
    "todos": [],
    "canvas": load_canvas_from_markdown(WORKSPACE_ROOT),  # Load from canvas.md if exists
    "response": "",
    "error": None,
    "last_update": time.time()
}
_agent_state_lock = threading.Lock()

def _run_agent_stream(message: str):
    """Run agent in background thread and update global state in real-time."""
    global _agent_state

    if not agent:
        with _agent_state_lock:
            _agent_state["response"] = f"⚠️ {_agent_state['error']}\n\nPlease check your setup and try again."
            _agent_state["running"] = False
        return

    try:
        agent_input = {"messages": [{"role": "user", "content": message}]}

        for update in agent.stream(agent_input, stream_mode="updates", config=dict(configurable=dict(thread_id=thread_id))):
            if isinstance(update, dict):
                for _, state_data in update.items():
                    if isinstance(state_data, dict) and "messages" in state_data:
                        msgs = state_data["messages"]
                        if msgs:
                            last_msg = msgs[-1] if isinstance(msgs, list) else msgs
                            msg_type = last_msg.__class__.__name__ if hasattr(last_msg, '__class__') else None

                            if msg_type == 'ToolMessage' and hasattr(last_msg, 'name'):
                                if last_msg.name == 'think_tool':
                                    content = last_msg.content
                                    thinking_text = ""
                                    if isinstance(content, str):
                                        try:
                                            parsed = json.loads(content)
                                            thinking_text = parsed.get('reflection', content)
                                        except:
                                            thinking_text = content
                                    elif isinstance(content, dict):
                                        thinking_text = content.get('reflection', str(content))

                                    # Update state immediately
                                    with _agent_state_lock:
                                        _agent_state["thinking"] = thinking_text
                                        _agent_state["last_update"] = time.time()

                                elif last_msg.name == 'write_todos':
                                    content = last_msg.content
                                    todos = []
                                    if isinstance(content, str):
                                        import ast
                                        match = re.search(r'\[.*\]', content, re.DOTALL)
                                        if match:
                                            try:
                                                todos = ast.literal_eval(match.group(0))
                                            except:
                                                try:
                                                    todos = json.loads(match.group(0))
                                                except:
                                                    pass
                                    elif isinstance(content, list):
                                        todos = content

                                    # Update state immediately
                                    with _agent_state_lock:
                                        _agent_state["todos"] = todos
                                        _agent_state["last_update"] = time.time()

                                elif last_msg.name == 'add_to_canvas':
                                    content = last_msg.content
                                    # Canvas tool returns the parsed canvas object
                                    if isinstance(content, str):
                                        try:
                                            parsed = json.loads(content)
                                            canvas_item = parsed
                                        except:
                                            # If not JSON, treat as markdown
                                            canvas_item = {"type": "markdown", "data": content}
                                    elif isinstance(content, dict):
                                        canvas_item = content
                                    else:
                                        canvas_item = {"type": "markdown", "data": str(content)}

                                    # Update state immediately - append to canvas
                                    with _agent_state_lock:
                                        _agent_state["canvas"].append(canvas_item)
                                        _agent_state["last_update"] = time.time()

                                        # Also export to markdown file
                                        try:
                                            export_canvas_to_markdown(_agent_state["canvas"], WORKSPACE_ROOT)
                                        except Exception as e:
                                            print(f"Failed to export canvas: {e}")

                            elif hasattr(last_msg, 'content'):
                                content = last_msg.content
                                response_text = ""
                                if isinstance(content, str):
                                    response_text = re.sub(
                                        r"\{'id':\s*'[^']+',\s*'input':\s*\{.*?\},\s*'name':\s*'[^']+',\s*'type':\s*'tool_use'\}",
                                        '', content, flags=re.DOTALL
                                    ).strip()
                                elif isinstance(content, list):
                                    text_parts = [
                                        block.get("text", "") if isinstance(block, dict) else str(block)
                                        for block in content
                                    ]
                                    response_text = " ".join(text_parts).strip()

                                if response_text:
                                    with _agent_state_lock:
                                        _agent_state["response"] = response_text
                                        _agent_state["last_update"] = time.time()

    except Exception as e:
        with _agent_state_lock:
            _agent_state["error"] = str(e)
            _agent_state["response"] = f"Error: {str(e)}"

    finally:
        with _agent_state_lock:
            _agent_state["running"] = False
            _agent_state["last_update"] = time.time()

def call_agent(message: str):
    """Start agent execution in background thread."""
    global _agent_state

    # Preserve existing canvas from current state
    with _agent_state_lock:
        existing_canvas = _agent_state.get("canvas", []).copy()

    # Reset state but preserve canvas
    with _agent_state_lock:
        _agent_state = {
            "running": True,
            "thinking": "",
            "todos": [],
            "canvas": existing_canvas,  # Preserve existing canvas
            "response": "",
            "error": None,
            "last_update": time.time()
        }

    # Start background thread
    thread = threading.Thread(target=_run_agent_stream, args=(message,))
    thread.daemon = True
    thread.start()

def get_agent_state() -> Dict[str, Any]:
    """Get current agent state (thread-safe)."""
    with _agent_state_lock:
        return _agent_state.copy()

# =============================================================================
# DASH APP
# =============================================================================

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    title=APP_TITLE,
)

# Load HTML template from file
with open(Path(__file__).parent / "templates" / "index.html", "r") as f:
    app.index_string = f.read()


# =============================================================================
# LAYOUT
# =============================================================================

app.layout = dmc.MantineProvider([
    # State stores
    dcc.Store(id="chat-history", data=[]),
    dcc.Store(id="pending-message", data=None),
    dcc.Store(id="expanded-folders", data=[]),
    dcc.Store(id="file-to-view", data=None),
    dcc.Download(id="file-download"),

    # Interval for polling agent updates (disabled by default)
    dcc.Interval(id="poll-interval", interval=250, disabled=True),
    
    # File viewer modal
    dmc.Modal(
        id="file-modal",
        title="",
        size="xl",
        children=[
            html.Div(id="modal-content"),
            html.Div([
                dmc.Button(
                    "Download",
                    id="modal-download-btn",
                    variant="outline",
                    color="blue",
                    style={"marginTop": "16px"}
                )
            ], style={"textAlign": "right"})
        ],
        opened=False,
    ),
    
    html.Div([
        # Header
        html.Header([
            html.Div([
                html.Div([
                    html.H1(APP_TITLE or "DeepAgent Dash", style={
                        "fontSize": "18px", "fontWeight": "600", "margin": "0",
                    }),
                    html.Span(APP_SUBTITLE or "AI-Powered Workspace", style={
                        "fontSize": "12px", "color": COLORS["text_muted"], "marginLeft": "12px",
                    })
                ], style={"display": "flex", "alignItems": "baseline"}),
                html.Div([
                    html.Div(style={
                        "width": "8px", "height": "8px",
                        "background": COLORS["success"] if agent else COLORS["error"],
                        "marginRight": "8px",
                    }),
                    html.Span("Ready" if agent else "No Agent", style={
                        "fontSize": "13px", "color": COLORS["text_secondary"],
                    })
                ], style={"display": "flex", "alignItems": "center"})
            ], style={
                "display": "flex", "justifyContent": "space-between",
                "alignItems": "center", "maxWidth": "1600px",
                "margin": "0 auto", "padding": "0 24px",
            })
        ], style={
            "background": COLORS["bg_primary"],
            "borderBottom": f"1px solid {COLORS['border']}",
            "padding": "16px 0",
        }),
        
        # Main content
        html.Main([
            # Chat panel
            html.Div([
                html.Div([
                    html.H2("Chat", style={"fontSize": "14px", "fontWeight": "600", "margin": "0"}),
                ], style={
                    "padding": "16px 20px",
                    "borderBottom": f"1px solid {COLORS['border']}",
                    "background": COLORS["bg_primary"],
                }),
                
                # Messages
                html.Div(id="chat-messages", style={
                    "flex": "1", "overflowY": "auto", "padding": "20px",
                    "display": "flex", "flexDirection": "column", "gap": "16px",
                }),
                
                # Input
                html.Div([
                    dcc.Upload(
                        id="file-upload",
                        children=html.Div("+", style={"fontSize": "20px", "color": COLORS["text_muted"]}),
                        style={
                            "width": "40px", "height": "40px",
                            "display": "flex", "alignItems": "center", "justifyContent": "center",
                            "cursor": "pointer", "border": f"1px solid {COLORS['border']}",
                            "background": COLORS["bg_primary"],
                        },
                        multiple=True
                    ),
                    dcc.Input(
                        id="chat-input",
                        type="text",
                        placeholder="Type a message...",
                        className="chat-input",
                        debounce=False,
                        style={
                            "flex": "1", "padding": "10px 16px", "height": "40px",
                            "border": f"1px solid {COLORS['border']}",
                            "background": COLORS["bg_primary"], "fontSize": "14px",
                        },
                    ),
                    html.Button("Send", id="send-btn", className="send-btn", style={
                        "padding": "0 24px", "height": "40px",
                        "background": COLORS["accent"], "color": "#ffffff",
                        "border": "none", "fontSize": "14px", "fontWeight": "500",
                        "cursor": "pointer",
                    }),
                ], style={
                    "display": "flex", "gap": "8px", "padding": "16px 20px",
                    "borderTop": f"1px solid {COLORS['border']}",
                    "background": COLORS["bg_primary"],
                }),
                html.Div(id="upload-status", style={
                    "padding": "0 20px 12px", "fontSize": "12px", "color": COLORS["text_muted"],
                }),
            ], id="chat-panel", style={
                "flex": "1", "display": "flex", "flexDirection": "column",
                "background": COLORS["bg_secondary"], "minWidth": "0",
            }),

            # Resize handle
            html.Div(id="resize-handle", className="resize-handle", style={
                "width": "4px",
                "cursor": "col-resize",
                "background": "transparent",
                "flexShrink": "0",
            }),

            # Sidebar (Files/Canvas toggle)
            html.Div([
                # Header with toggle
                html.Div([
                    html.Div([
                        html.Button("Files", id="view-files-btn", style={
                            "background": COLORS["accent"],
                            "color": "#ffffff",
                            "border": "none",
                            "fontSize": "13px",
                            "fontWeight": "500",
                            "cursor": "pointer",
                            "padding": "6px 12px",
                            "borderRadius": "4px 0 0 4px",
                        }),
                        html.Button("Canvas", id="view-canvas-btn", style={
                            "background": COLORS["bg_secondary"],
                            "color": COLORS["text_secondary"],
                            "border": "none",
                            "fontSize": "13px",
                            "fontWeight": "500",
                            "cursor": "pointer",
                            "padding": "6px 12px",
                            "borderRadius": "0 4px 4px 0",
                        }),
                    ], style={"display": "flex"}),
                    html.Div([
                        html.Button(">_", id="open-terminal-btn", title="Open in Terminal", style={
                            "background": "transparent", "border": "none",
                            "fontSize": "13px", "cursor": "pointer", "padding": "4px 8px",
                            "color": COLORS["text_secondary"], "fontFamily": "'IBM Plex Mono', monospace",
                            "fontWeight": "600",
                        }),
                        html.Button("↻", id="refresh-btn", title="Refresh", style={
                            "background": "transparent", "border": "none",
                            "fontSize": "16px", "cursor": "pointer", "padding": "4px 8px",
                        }),
                    ], id="files-actions", style={"display": "flex", "alignItems": "center"})
                ], style={
                    "display": "flex", "justifyContent": "space-between",
                    "alignItems": "center", "padding": "16px",
                    "borderBottom": f"1px solid {COLORS['border']}",
                }),

                # Files view
                html.Div([
                    html.Div(
                        id="file-tree",
                        children=render_file_tree(build_file_tree(WORKSPACE_ROOT, WORKSPACE_ROOT), COLORS, STYLES),
                        style={"flex": "1", "overflowY": "auto"}
                    ),
                ], id="files-view", style={"flex": "1", "display": "flex", "flexDirection": "column"}),

                # Canvas view (hidden by default)
                html.Div([
                    html.Div(id="canvas-content", style={
                        "flex": "1",
                        "minHeight": "0",  # Critical for flex overflow
                        "overflowY": "auto",
                        "padding": "20px",
                        "background": "#ffffff",  # White background like a note
                    }),
                    # Clear canvas button (floating at bottom)
                    html.Div([
                        html.Button("Clear Canvas", id="clear-canvas-btn", style={
                            "background": COLORS["error"],
                            "color": "#ffffff",
                            "border": "none",
                            "fontSize": "13px",
                            "fontWeight": "500",
                            "cursor": "pointer",
                            "padding": "8px 16px",
                            "borderRadius": "4px",
                        })
                    ], style={
                        "padding": "12px 20px",
                        "borderTop": f"1px solid {COLORS['border']}",
                        "background": COLORS["bg_primary"],
                        "display": "flex",
                        "justifyContent": "center"
                    })
                ], id="canvas-view", style={
                    "flex": "1",
                    "minHeight": "0",  # Critical for flex overflow
                    "display": "none",
                    "flexDirection": "column",
                    "overflow": "hidden"  # Prevent overflow from this container
                }),
            ], id="sidebar-panel", style={
                "flex": "1",
                "minWidth": "0",
                "minHeight": "0",  # Critical for flex overflow
                "display": "flex",
                "flexDirection": "column",
                "background": COLORS["bg_primary"],
                "borderLeft": f"1px solid {COLORS['border']}",
            }),
        ], id="main-container", style={"display": "flex", "flex": "1", "overflow": "hidden"}),
    ], style={"display": "flex", "flexDirection": "column", "height": "100vh"})
])

# Note: Component rendering functions imported from components module
# These are used in callbacks below with COLORS and STYLES passed as parameters

# =============================================================================
# CALLBACKS
# =============================================================================

# Chat callbacks
@app.callback(
    [Output("chat-messages", "children", allow_duplicate=True),
     Output("chat-history", "data", allow_duplicate=True),
     Output("chat-input", "value"),
     Output("pending-message", "data"),
     Output("poll-interval", "disabled")],
    [Input("send-btn", "n_clicks"),
     Input("chat-input", "n_submit")],
    [State("chat-input", "value"),
     State("chat-history", "data")],
    prevent_initial_call=True
)
def handle_send_immediate(n_clicks, n_submit, message, history):
    """Phase 1: Immediately show user message and start agent."""
    if not message or not message.strip():
        raise PreventUpdate

    message = message.strip()
    history = history or []
    history.append({"role": "user", "content": message})

    messages = [format_message(m["role"], m["content"], COLORS, STYLES, is_new=(i == len(history)-1)) for i, m in enumerate(history)]
    messages.append(format_loading(COLORS))

    # Start agent in background
    call_agent(message)

    # Enable polling
    return messages, history, "", message, False


@app.callback(
    [Output("chat-messages", "children"),
     Output("chat-history", "data", allow_duplicate=True),
     Output("poll-interval", "disabled", allow_duplicate=True)],
    Input("poll-interval", "n_intervals"),
    [State("chat-history", "data"),
     State("pending-message", "data")],
    prevent_initial_call=True
)
def poll_agent_updates(n_intervals, history, pending_message):
    """Poll for agent updates and display them in real-time."""
    state = get_agent_state()
    history = history or []

    # Check if agent is done
    if not state["running"]:
        # Agent finished - add response to history
        if state["response"]:
            history.append({"role": "assistant", "content": state["response"]})
        elif state["error"]:
            history.append({"role": "assistant", "content": f"Error: {state['error']}"})

        # Build final messages with inline thinking/todos between user and assistant
        final_messages = []
        for i, msg in enumerate(history):
            final_messages.append(format_message(msg["role"], msg["content"], COLORS, STYLES, is_new=(i >= len(history)-1)))

            # Add thinking/todos after user message, before assistant response
            if msg["role"] == "user" and i == len(history) - 2:  # Last user message
                # Add thinking block
                thinking_block = format_thinking(state["thinking"], COLORS)
                if thinking_block:
                    final_messages.append(thinking_block)

                # Add todos block
                todos_block = format_todos_inline(state["todos"], COLORS)
                if todos_block:
                    final_messages.append(todos_block)

        # Disable polling
        return final_messages, history, True
    else:
        # Agent still running - show loading with current thinking/todos
        messages = []
        for msg in history:
            messages.append(format_message(msg["role"], msg["content"], COLORS, STYLES))

        # Add current thinking/todos if available
        if state["thinking"]:
            thinking_block = format_thinking(state["thinking"], COLORS)
            if thinking_block:
                messages.append(thinking_block)

        if state["todos"]:
            todos_block = format_todos_inline(state["todos"], COLORS)
            if todos_block:
                messages.append(todos_block)

        # Add loading indicator
        messages.append(format_loading(COLORS))

        # Continue polling
        return messages, no_update, False


# Folder toggle callback
@app.callback(
    [Output({"type": "folder-children", "path": ALL}, "style"),
     Output({"type": "folder-icon", "path": ALL}, "style")],
    Input({"type": "folder-header", "path": ALL}, "n_clicks"),
    [State({"type": "folder-children", "path": ALL}, "id"),
     State({"type": "folder-icon", "path": ALL}, "id"),
     State({"type": "folder-children", "path": ALL}, "style"),
     State({"type": "folder-icon", "path": ALL}, "style")],
    prevent_initial_call=True
)
def toggle_folder(n_clicks, children_ids, icon_ids, children_styles, icon_styles):
    """Toggle folder expansion."""
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks):
        raise PreventUpdate

    triggered = ctx.triggered[0]["prop_id"]
    try:
        id_str = triggered.rsplit(".", 1)[0]
        id_dict = json.loads(id_str)
        clicked_path = id_dict.get("path")
    except:
        raise PreventUpdate

    new_children_styles = []
    new_icon_styles = []

    # Process all folder-children elements
    for i, child_id in enumerate(children_ids):
        path = child_id["path"]
        current_style = children_styles[i] if i < len(children_styles) else {"display": "none"}

        if path == clicked_path:
            # Toggle this folder
            is_expanded = current_style.get("display") != "none"
            new_children_styles.append({"display": "none" if is_expanded else "block"})
        else:
            new_children_styles.append(current_style)

    # Process all folder-icon elements
    for i, icon_id in enumerate(icon_ids):
        path = icon_id["path"]
        current_icon_style = icon_styles[i] if i < len(icon_styles) else {}

        if path == clicked_path:
            # Find corresponding children style to check if expanded
            children_idx = next((idx for idx, cid in enumerate(children_ids) if cid["path"] == path), None)
            if children_idx is not None:
                current_children_style = children_styles[children_idx] if children_idx < len(children_styles) else {"display": "none"}
                is_expanded = current_children_style.get("display") != "none"
                new_icon_styles.append({
                    "marginRight": "8px",
                    "fontSize": "10px",
                    "color": COLORS["text_muted"],
                    "transition": "transform 0.2s",
                    "display": "inline-block",
                    "transform": "rotate(0deg)" if is_expanded else "rotate(90deg)",
                })
            else:
                new_icon_styles.append(current_icon_style)
        else:
            new_icon_styles.append(current_icon_style)

    return new_children_styles, new_icon_styles


# File click - open modal
@app.callback(
    [Output("file-modal", "opened"),
     Output("file-modal", "title"),
     Output("modal-content", "children"),
     Output("file-to-view", "data")],
    Input({"type": "file-item", "path": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def open_file_modal(n_clicks):
    """Open file in modal."""
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks):
        raise PreventUpdate
    
    triggered = ctx.triggered[0]["prop_id"]
    try:
        id_str = triggered.rsplit(".", 1)[0]
        id_dict = json.loads(id_str)
        file_path = id_dict.get("path")
    except:
        raise PreventUpdate
    
    if not file_path:
        raise PreventUpdate
    
    content, is_text, error = read_file_content(WORKSPACE_ROOT, file_path)
    filename = Path(file_path).name
    
    if is_text and content:
        modal_content = html.Pre(
            content,
            style={
                "background": COLORS["bg_tertiary"],
                "padding": "16px",
                "fontSize": "12px",
                "fontFamily": "'IBM Plex Mono', monospace",
                "overflow": "auto",
                "maxHeight": "60vh",
                "whiteSpace": "pre-wrap",
                "wordBreak": "break-word",
                "margin": "0",
            }
        )
    else:
        modal_content = html.Div([
            html.P(error or "Cannot display file", style={
                "color": COLORS["text_muted"],
                "textAlign": "center",
                "padding": "40px",
            }),
            html.P("Click Download to save the file.", style={
                "color": COLORS["text_muted"],
                "textAlign": "center",
                "fontSize": "13px",
            })
        ])
    
    return True, filename, modal_content, file_path


# Modal download button
@app.callback(
    Output("file-download", "data", allow_duplicate=True),
    Input("modal-download-btn", "n_clicks"),
    State("file-to-view", "data"),
    prevent_initial_call=True
)
def download_from_modal(n_clicks, file_path):
    """Download file from modal."""
    if not n_clicks or not file_path:
        raise PreventUpdate
    
    b64, filename, mime = get_file_download_data(WORKSPACE_ROOT, file_path)
    if not b64:
        raise PreventUpdate
    
    return dict(content=b64, filename=filename, base64=True, type=mime)


# Direct download button in file tree
@app.callback(
    Output("file-download", "data"),
    Input({"type": "download-btn", "path": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def download_file(n_clicks):
    """Download file directly."""
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks):
        raise PreventUpdate
    
    triggered = ctx.triggered[0]["prop_id"]
    try:
        id_str = triggered.rsplit(".", 1)[0]
        id_dict = json.loads(id_str)
        file_path = id_dict.get("path")
    except:
        raise PreventUpdate
    
    if not file_path:
        raise PreventUpdate
    
    b64, filename, mime = get_file_download_data(WORKSPACE_ROOT, file_path)
    if not b64:
        raise PreventUpdate
    
    return dict(content=b64, filename=filename, base64=True, type=mime)


# Open terminal
@app.callback(
    Output("open-terminal-btn", "n_clicks"),
    Input("open-terminal-btn", "n_clicks"),
    prevent_initial_call=True
)
def open_terminal(n_clicks):
    """Open system terminal at workspace directory."""
    if not n_clicks:
        raise PreventUpdate
    
    workspace_path = str(WORKSPACE_ROOT)
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", "Terminal", workspace_path])
        elif system == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "cmd", "/K", f"cd /d {workspace_path}"], shell=True)
        else:  # Linux
            # Try common terminal emulators
            terminals = [
                ["gnome-terminal", f"--working-directory={workspace_path}"],
                ["konsole", f"--workdir={workspace_path}"],
                ["xfce4-terminal", f"--working-directory={workspace_path}"],
                ["xterm", "-e", f"cd {workspace_path} && $SHELL"],
            ]
            for term_cmd in terminals:
                try:
                    subprocess.Popen(term_cmd)
                    break
                except FileNotFoundError:
                    continue
    except Exception as e:
        print(f"Failed to open terminal: {e}")
    
    raise PreventUpdate


# Refresh file tree
@app.callback(
    Output("file-tree", "children"),
    Input("refresh-btn", "n_clicks"),
    prevent_initial_call=True
)
def refresh_tree(n_clicks):
    """Refresh file tree."""
    return render_file_tree(build_file_tree(WORKSPACE_ROOT, WORKSPACE_ROOT), COLORS, STYLES)


# File upload
@app.callback(
    [Output("upload-status", "children"),
     Output("file-tree", "children", allow_duplicate=True)],
    Input("file-upload", "contents"),
    State("file-upload", "filename"),
    prevent_initial_call=True
)
def handle_upload(contents, filenames):
    """Handle file uploads."""
    if not contents:
        raise PreventUpdate
    
    uploaded = []
    for content, filename in zip(contents, filenames):
        try:
            _, content_string = content.split(',')
            decoded = base64.b64decode(content_string)
            file_path = WORKSPACE_ROOT / filename
            try:
                file_path.write_text(decoded.decode('utf-8'))
            except UnicodeDecodeError:
                file_path.write_bytes(decoded)
            uploaded.append(filename)
        except Exception as e:
            print(f"Upload error: {e}")
    
    if uploaded:
        return f"Uploaded: {', '.join(uploaded)}", render_file_tree(build_file_tree(WORKSPACE_ROOT, WORKSPACE_ROOT), COLORS, STYLES)
    return "Upload failed", no_update


# View toggle callbacks
@app.callback(
    [Output("files-view", "style"),
     Output("canvas-view", "style"),
     Output("view-files-btn", "style"),
     Output("view-canvas-btn", "style"),
     Output("files-actions", "style")],
    [Input("view-files-btn", "n_clicks"),
     Input("view-canvas-btn", "n_clicks")],
    prevent_initial_call=True
)
def toggle_view(files_clicks, canvas_clicks):
    """Toggle between files and canvas view."""
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "view-canvas-btn":
        # Show canvas, hide files
        return (
            {"flex": "1", "display": "none", "flexDirection": "column"},
            {
                "flex": "1",
                "minHeight": "0",  # Critical for flex overflow
                "display": "flex",
                "flexDirection": "column",
                "overflow": "hidden"  # Prevent overflow from this container
            },
            {
                "background": COLORS["bg_secondary"],
                "color": COLORS["text_secondary"],
                "border": "none",
                "fontSize": "13px",
                "fontWeight": "500",
                "cursor": "pointer",
                "padding": "6px 12px",
                "borderRadius": "4px 0 0 4px",
            },
            {
                "background": COLORS["accent"],
                "color": "#ffffff",
                "border": "none",
                "fontSize": "13px",
                "fontWeight": "500",
                "cursor": "pointer",
                "padding": "6px 12px",
                "borderRadius": "0 4px 4px 0",
            },
            {"display": "none"}
        )
    else:
        # Show files, hide canvas
        return (
            {"flex": "1", "display": "flex", "flexDirection": "column"},
            {
                "flex": "1",
                "minHeight": "0",  # Critical for flex overflow
                "display": "none",
                "flexDirection": "column",
                "overflow": "hidden"  # Prevent overflow from this container
            },
            {
                "background": COLORS["accent"],
                "color": "#ffffff",
                "border": "none",
                "fontSize": "13px",
                "fontWeight": "500",
                "cursor": "pointer",
                "padding": "6px 12px",
                "borderRadius": "4px 0 0 4px",
            },
            {
                "background": COLORS["bg_secondary"],
                "color": COLORS["text_secondary"],
                "border": "none",
                "fontSize": "13px",
                "fontWeight": "500",
                "cursor": "pointer",
                "padding": "6px 12px",
                "borderRadius": "0 4px 4px 0",
            },
            {"display": "flex", "alignItems": "center"}
        )


# Canvas content update
@app.callback(
    Output("canvas-content", "children"),
    [Input("poll-interval", "n_intervals"),
     Input("view-canvas-btn", "n_clicks")],
    prevent_initial_call=False
)
def update_canvas_content(n_intervals, canvas_clicks):
    """Update canvas content from agent state."""
    state = get_agent_state()
    canvas_items = state.get("canvas", [])

    # Use imported rendering function
    return render_canvas_items(canvas_items, COLORS)



# Clear canvas callback
@app.callback(
    Output("canvas-content", "children", allow_duplicate=True),
    Input("clear-canvas-btn", "n_clicks"),
    prevent_initial_call=True
)
def clear_canvas(n_clicks):
    """Clear the canvas and archive the current canvas.md with a timestamp."""
    if not n_clicks:
        raise PreventUpdate

    global _agent_state

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Archive existing canvas.md file if it exists
    canvas_file = WORKSPACE_ROOT / "canvas.md"
    if canvas_file.exists():
        try:
            archive_path = WORKSPACE_ROOT / f"canvas_{timestamp}.md"
            canvas_file.rename(archive_path)
            print(f"Archived canvas to {archive_path}")
        except Exception as e:
            print(f"Failed to archive canvas.md: {e}")

    # Archive .canvas folder if it exists
    canvas_dir = WORKSPACE_ROOT / ".canvas"
    if canvas_dir.exists() and canvas_dir.is_dir():
        try:
            import shutil
            archive_dir = WORKSPACE_ROOT / f".canvas_{timestamp}"
            shutil.move(str(canvas_dir), str(archive_dir))
            print(f"Archived .canvas folder to {archive_dir}")
        except Exception as e:
            print(f"Failed to archive .canvas folder: {e}")

    # Clear canvas in state
    with _agent_state_lock:
        _agent_state["canvas"] = []

    # Return empty state
    return html.Div([
        html.Div("🎨", style={
            "fontSize": "48px",
            "textAlign": "center",
            "marginBottom": "16px",
            "opacity": "0.3"
        }),
        html.P("Canvas is empty", style={
            "textAlign": "center",
            "color": COLORS["text_muted"],
            "fontSize": "14px"
        }),
        html.P("The agent will add visualizations, charts, and notes here", style={
            "textAlign": "center",
            "color": COLORS["text_muted"],
            "fontSize": "12px",
            "marginTop": "8px"
        })
    ], style={
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "center",
        "height": "100%",
        "padding": "40px"
    })


# =============================================================================
# PROGRAMMATIC API
# =============================================================================

def run_app(
    workspace=None,
    agent_spec=None,
    port=None,
    host=None,
    debug=None,
    title=None,
    subtitle=None,
    config_file=None
):
    """
    Run DeepAgent Dash programmatically.

    This function can be called from Python code or used as the entry point
    for the CLI. It handles configuration loading and overrides.

    Args:
        workspace (str, optional): Workspace directory path
        agent_spec (str, optional): Agent specification as "path:object"
        port (int, optional): Port number
        host (str, optional): Host to bind to
        debug (bool, optional): Debug mode
        title (str, optional): Application title
        config_file (str, optional): Path to config file (default: ./config.py)

    Returns:
        int: Exit code (0 for success, non-zero for error)

    Example:
        >>> from deepagents_dash import run_app
        >>> run_app(workspace="~/my-workspace", port=8080, debug=True)
    """
    global WORKSPACE_ROOT, APP_TITLE, APP_SUBTITLE, PORT, HOST, DEBUG, agent, AGENT_ERROR, args

    # Load config file if specified and exists
    config_module = None
    if config_file:
        config_path = Path(config_file).resolve()
        if config_path.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("user_config", config_path)
            if spec and spec.loader:
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                print(f"✓ Loaded config from {config_path}")
        else:
            print(f"⚠️  Config file not found: {config_path}, using defaults")

    # Apply configuration with overrides
    if config_module:
        # Use config file values as base
        WORKSPACE_ROOT = Path(workspace).resolve() if workspace else getattr(config_module, "WORKSPACE_ROOT", config.WORKSPACE_ROOT)
        APP_TITLE = title if title else getattr(config_module, "APP_TITLE", config.APP_TITLE)
        APP_SUBTITLE = subtitle if subtitle else getattr(config_module, "APP_SUBTITLE", config.APP_SUBTITLE)
        PORT = port if port is not None else getattr(config_module, "PORT", config.PORT)
        HOST = host if host else getattr(config_module, "HOST", config.HOST)
        DEBUG = debug if debug is not None else getattr(config_module, "DEBUG", config.DEBUG)

        # Get agent from config file if not specified via CLI
        if not agent_spec:
            get_agent_func = getattr(config_module, "get_agent", None)
            if get_agent_func:
                result = get_agent_func()
                if isinstance(result, tuple):
                    agent, AGENT_ERROR = result
                else:
                    agent = result
                    AGENT_ERROR = None
            else:
                agent = None
                AGENT_ERROR = "No get_agent() function in config file"
        else:
            # Load agent from CLI spec
            agent, AGENT_ERROR = load_agent_from_spec(agent_spec)
    else:
        # No config file, use CLI args or defaults
        WORKSPACE_ROOT = Path(workspace).resolve() if workspace else config.WORKSPACE_ROOT
        APP_TITLE = title if title else config.APP_TITLE
        APP_SUBTITLE = subtitle if subtitle else config.APP_SUBTITLE
        PORT = port if port is not None else config.PORT
        HOST = host if host else config.HOST
        DEBUG = debug if debug is not None else config.DEBUG

        if agent_spec:
            agent, AGENT_ERROR = load_agent_from_spec(agent_spec)
        else:
            # Use default config agent
            agent, AGENT_ERROR = load_agent_from_spec(config.AGENT_SPEC)

    # Ensure workspace exists
    WORKSPACE_ROOT.mkdir(exist_ok=True, parents=True)

    # Update global state to use the configured workspace
    global _agent_state
    _agent_state["canvas"] = load_canvas_from_markdown(WORKSPACE_ROOT)

    # Create a mock args object for compatibility with existing code
    class Args:
        pass
    args = Args()
    args.workspace = workspace
    args.agent = agent_spec

    # Print startup banner
    print("\n" + "="*50)
    print(f"  {APP_TITLE}")
    print("="*50)
    print(f"  Workspace: {WORKSPACE_ROOT}")
    if workspace:
        print(f"    (from CLI: --workspace {workspace})")
    print(f"  Agent: {'Ready' if agent else 'Not available'}")
    if agent_spec:
        print(f"    (from CLI: --agent {agent_spec})")
    if AGENT_ERROR:
        print(f"    Error: {AGENT_ERROR}")
    print(f"  URL: http://{HOST}:{PORT}")
    print(f"  Debug: {DEBUG}")
    print("="*50 + "\n")

    # Run the app
    try:
        app.run(debug=DEBUG, host=HOST, port=PORT)
        return 0
    except Exception as e:
        print(f"\n❌ Error running app: {e}")
        return 1


# =============================================================================
# MAIN - BACKWARDS COMPATIBILITY
# =============================================================================

if __name__ == "__main__":
    # When run directly (not as package), use original CLI arg parsing
    sys.exit(run_app(
        workspace=args.workspace if args.workspace else None,
        agent_spec=args.agent if args.agent else None,
        port=args.port if args.port else None,
        host=args.host if args.host else None,
        debug=args.debug if args.debug else (not args.no_debug if args.no_debug else None),
        title=args.title if args.title else None,
        subtitle=args.subtitle if args.subtitle else None,
        config_file=args.config if args.config else None
    ))