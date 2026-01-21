import os
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

from dash import Dash, html, Input, Output, State, callback_context, no_update, ALL, clientside_callback
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
from dash_iconify import DashIconify

# Import custom modules
from .canvas import parse_canvas_object, export_canvas_to_markdown, load_canvas_from_markdown
from .file_utils import build_file_tree, render_file_tree, read_file_content, get_file_download_data, load_folder_contents
from .components import (
    format_message, format_loading, format_thinking, format_todos,
    format_todos_inline, render_canvas_items, format_tool_calls_inline,
    format_interrupt
)
from .layout import create_layout as create_layout_component

# Import configuration defaults
from . import config

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
    Load agent from specification string.

    Supports two formats (both use colon separator):
    1. File path format: "path/to/file.py:object_name"
    2. Module format: "mypackage.module.submodule:object_name"

    Args:
        agent_spec: String like "agent.py:agent", "my_agents.py:custom_agent",
                   or "mypackage.agents:my_agent"

    Returns:
        tuple: (agent_object, error_message)
    """
    try:
        # Both formats use colon separator
        if ":" not in agent_spec:
            return None, f"Invalid agent spec '{agent_spec}'. Expected format: 'path/to/file.py:object' or 'module.path:object'"

        left_part, object_name = agent_spec.rsplit(":", 1)

        # Determine if it's a file path or module path
        # File paths end with .py or contain path separators
        if left_part.endswith(".py") or "/" in left_part or "\\" in left_part:
            return _load_agent_from_file(left_part, object_name)
        else:
            return _load_agent_from_module(left_part, object_name)

    except Exception as e:
        return None, f"Failed to load agent from {agent_spec}: {e}"


def _load_agent_from_file(file_path_str: str, object_name: str):
    """Load agent from file path format: 'path/to/file.py:object_name'"""
    file_path = Path(file_path_str).resolve()

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


def _load_agent_from_module(module_path: str, object_name: str):
    """Load agent from module format: 'mypackage.module:object_name'"""
    try:
        # Import the module
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        return None, f"Module '{module_path}' not found: {e}"
    except ImportError as e:
        return None, f"Failed to import module '{module_path}': {e}"

    # Get the object
    if not hasattr(module, object_name):
        return None, f"Object '{object_name}' not found in module '{module_path}'"

    agent = getattr(module, object_name)
    return agent, None

# Module-level configuration (uses config defaults)
WORKSPACE_ROOT = config.WORKSPACE_ROOT
APP_TITLE = config.APP_TITLE
APP_SUBTITLE = config.APP_SUBTITLE
PORT = config.PORT
HOST = config.HOST
DEBUG = config.DEBUG

# Ensure workspace exists
WORKSPACE_ROOT.mkdir(exist_ok=True, parents=True)

# Initialize agent from config
agent, AGENT_ERROR = load_agent_from_spec(config.AGENT_SPEC)


# =============================================================================
# STYLING
# =============================================================================

COLORS_LIGHT = {
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
    "canvas_bg": "#ffffff",
    "interrupt_bg": "#fffbeb",
}

COLORS_DARK = {
    "bg_primary": "#1e1e1e",
    "bg_secondary": "#252526",
    "bg_tertiary": "#2d2d2d",
    "bg_hover": "#3c3c3c",
    "accent": "#4fc3f7",
    "accent_light": "#1e3a5f",
    "accent_dark": "#81d4fa",
    "text_primary": "#e0e0e0",
    "text_secondary": "#b0b0b0",
    "text_muted": "#808080",
    "border": "#404040",
    "border_light": "#333333",
    "success": "#4caf50",
    "warning": "#ffb74d",
    "error": "#ef5350",
    "thinking": "#b388ff",
    "todo": "#26a69a",
    "canvas_bg": "#2d2d2d",
    "interrupt_bg": "#3d3520",
}

# Default to light theme
COLORS = COLORS_LIGHT.copy()

STYLES = {
    "shadow": "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08)",
    "transition": "all 0.15s ease",
}

def get_colors(theme: str = "light") -> dict:
    """Get color scheme based on theme."""
    return COLORS_DARK if theme == "dark" else COLORS_LIGHT

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
    "tool_calls": [],  # Current turn's tool calls (reset each turn)
    "canvas": load_canvas_from_markdown(WORKSPACE_ROOT),  # Load from canvas.md if exists
    "response": "",
    "error": None,
    "interrupt": None,  # Track interrupt requests for human-in-the-loop
    "last_update": time.time(),
    "start_time": None,  # Track when agent started for response time calculation
}
_agent_state_lock = threading.Lock()

def _run_agent_stream(message: str, resume_data: Dict = None):
    """Run agent in background thread and update global state in real-time.

    Args:
        message: User message to send to agent
        resume_data: Optional dict with 'decisions' to resume from interrupt
    """
    if not agent:
        with _agent_state_lock:
            _agent_state["response"] = f"⚠️ {_agent_state['error']}\n\nPlease check your setup and try again."
            _agent_state["running"] = False
        return

    # Track tool calls by their ID for updating status
    tool_call_map = {}

    def _serialize_tool_call(tc) -> Dict:
        """Serialize a tool call to a dictionary."""
        if isinstance(tc, dict):
            return {
                "id": tc.get("id"),
                "name": tc.get("name"),
                "args": tc.get("args", {}),
                "status": "running",
                "result": None
            }
        else:
            return {
                "id": getattr(tc, 'id', None),
                "name": getattr(tc, 'name', None),
                "args": getattr(tc, 'args', {}),
                "status": "running",
                "result": None
            }

    def _update_tool_call_result(tool_call_id: str, result: Any, status: str = "success"):
        """Update a tool call with its result."""
        with _agent_state_lock:
            for tc in _agent_state["tool_calls"]:
                if tc.get("id") == tool_call_id:
                    tc["result"] = result
                    tc["status"] = status
                    break
            _agent_state["last_update"] = time.time()

    try:
        # Prepare input based on whether we're resuming or starting fresh
        stream_config = dict(configurable=dict(thread_id=thread_id))

        if message == "__RESUME__":
            # Resume from interrupt
            from langgraph.types import Command
            agent_input = Command(resume=resume_data)
        else:
            agent_input = {"messages": [{"role": "user", "content": message}]}

        for update in agent.stream(agent_input, stream_mode="updates", config=stream_config):
            # Check for interrupt
            if isinstance(update, dict) and "__interrupt__" in update:
                interrupt_value = update["__interrupt__"]
                interrupt_data = _process_interrupt(interrupt_value)
                with _agent_state_lock:
                    _agent_state["interrupt"] = interrupt_data
                    _agent_state["running"] = False  # Pause until user responds
                    _agent_state["last_update"] = time.time()
                return  # Exit stream, wait for user to resume

            if isinstance(update, dict):
                for _, state_data in update.items():
                    if isinstance(state_data, dict) and "messages" in state_data:
                        msgs = state_data["messages"]
                        if msgs:
                            last_msg = msgs[-1] if isinstance(msgs, list) else msgs
                            msg_type = last_msg.__class__.__name__ if hasattr(last_msg, '__class__') else None

                            # Capture AIMessage tool_calls
                            if msg_type == 'AIMessage' and hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                                new_tool_calls = []
                                for tc in last_msg.tool_calls:
                                    serialized = _serialize_tool_call(tc)
                                    tool_call_map[serialized["id"]] = serialized
                                    new_tool_calls.append(serialized)

                                with _agent_state_lock:
                                    _agent_state["tool_calls"].extend(new_tool_calls)
                                    _agent_state["last_update"] = time.time()

                            elif msg_type == 'ToolMessage' and hasattr(last_msg, 'name'):
                                # Update tool call status when we get the result
                                tool_call_id = getattr(last_msg, 'tool_call_id', None)
                                if tool_call_id:
                                    # Determine status based on content
                                    content = last_msg.content
                                    status = "success"
                                    if isinstance(content, str) and ("error" in content.lower() or "Error:" in content):
                                        status = "error"
                                    elif isinstance(content, dict) and content.get("error"):
                                        status = "error"

                                    # Truncate result for display
                                    result_display = str(content)
                                    if len(result_display) > 1000:
                                        result_display = result_display[:1000] + "..."

                                    _update_tool_call_result(tool_call_id, result_display, status)

                                # Handle specific tool messages
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

                                elif last_msg.name in ('execute_cell', 'execute_all_cells'):
                                    # Extract canvas_items from cell execution results
                                    content = last_msg.content
                                    canvas_items_to_add = []

                                    if isinstance(content, str):
                                        try:
                                            parsed = json.loads(content)
                                            # execute_cell returns a dict, execute_all_cells returns a list
                                            if isinstance(parsed, dict):
                                                canvas_items_to_add = parsed.get('canvas_items', [])
                                            elif isinstance(parsed, list):
                                                # execute_all_cells returns list of results
                                                for result in parsed:
                                                    if isinstance(result, dict):
                                                        canvas_items_to_add.extend(result.get('canvas_items', []))
                                        except:
                                            pass
                                    elif isinstance(content, dict):
                                        canvas_items_to_add = content.get('canvas_items', [])
                                    elif isinstance(content, list):
                                        for result in content:
                                            if isinstance(result, dict):
                                                canvas_items_to_add.extend(result.get('canvas_items', []))

                                    # Add any canvas items found
                                    if canvas_items_to_add:
                                        with _agent_state_lock:
                                            for item in canvas_items_to_add:
                                                if isinstance(item, dict) and item.get('type'):
                                                    _agent_state["canvas"].append(item)
                                            _agent_state["last_update"] = time.time()

                                            # Export to markdown file
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


def _process_interrupt(interrupt_value: Any) -> Dict[str, Any]:
    """Process a LangGraph interrupt value and convert to serializable format.

    Args:
        interrupt_value: The interrupt value from LangGraph

    Returns:
        Dict with 'message' and 'action_requests' for UI display
    """
    interrupt_data = {
        "message": "The agent needs your input to continue.",
        "action_requests": [],
        "raw": None
    }

    # Handle different interrupt formats
    if isinstance(interrupt_value, (list, tuple)) and len(interrupt_value) > 0:
        first_item = interrupt_value[0]

        # Check if it's an Interrupt object (from deepagents interrupt_on)
        if hasattr(first_item, 'value'):
            # This is a LangGraph Interrupt object
            for item in interrupt_value:
                value = getattr(item, 'value', None)

                # deepagents interrupt_on stores tool call info in a specific format:
                # {'action_requests': [{'name': 'bash', 'args': {...}, 'description': '...'}], 'review_configs': [...]}
                if value is not None and isinstance(value, dict):
                    # Check for deepagents format with action_requests
                    action_requests = value.get('action_requests', [])
                    if action_requests:
                        for action_req in action_requests:
                            tool_name = action_req.get('name', 'unknown')
                            tool_args = action_req.get('args', {})
                            interrupt_data["action_requests"].append({
                                "type": "tool_call",
                                "tool": tool_name,
                                "args": tool_args,
                            })
                            interrupt_data["message"] = f"The agent wants to execute: {tool_name}"
                    else:
                        # Fallback: direct tool call format
                        tool_name = value.get('name', value.get('tool', 'unknown'))
                        tool_args = value.get('args', value.get('arguments', {}))
                        if tool_name != 'unknown':
                            interrupt_data["action_requests"].append({
                                "type": "tool_call",
                                "tool": tool_name,
                                "args": tool_args,
                            })
                            interrupt_data["message"] = f"The agent wants to execute: {tool_name}"
                        else:
                            interrupt_data["message"] = str(value)
                elif value is not None:
                    interrupt_data["message"] = str(value)

        # Check if it's an ActionRequest or similar
        elif hasattr(first_item, 'action'):
            for item in interrupt_value:
                action = getattr(item, 'action', None)
                if action:
                    interrupt_data["action_requests"].append({
                        "type": getattr(action, 'type', 'unknown'),
                        "tool": getattr(action, 'name', getattr(action, 'tool', '')),
                        "args": getattr(action, 'args', {}),
                    })
        elif isinstance(first_item, dict):
            # Check if it's a tool call dict
            if 'name' in first_item or 'tool' in first_item:
                for item in interrupt_value:
                    tool_name = item.get('name', item.get('tool', 'unknown'))
                    tool_args = item.get('args', item.get('arguments', {}))
                    interrupt_data["action_requests"].append({
                        "type": "tool_call",
                        "tool": tool_name,
                        "args": tool_args,
                    })
                    interrupt_data["message"] = f"The agent wants to execute: {tool_name}"
            else:
                interrupt_data["action_requests"] = list(interrupt_value)
        else:
            interrupt_data["message"] = str(first_item)
    elif isinstance(interrupt_value, str):
        interrupt_data["message"] = interrupt_value
    elif isinstance(interrupt_value, dict):
        interrupt_data["message"] = interrupt_value.get("message", str(interrupt_value))
        interrupt_data["action_requests"] = interrupt_value.get("action_requests", [])

    # Store raw value for resume
    try:
        interrupt_data["raw"] = interrupt_value
    except:
        pass

    return interrupt_data

def call_agent(message: str, resume_data: Dict = None):
    """Start agent execution in background thread.

    Args:
        message: User message to send to agent
        resume_data: Optional dict with decisions to resume from interrupt
    """
    # Reset state but preserve canvas - do it all atomically
    with _agent_state_lock:
        existing_canvas = _agent_state.get("canvas", []).copy()

        _agent_state.clear()
        _agent_state.update({
            "running": True,
            "thinking": "",
            "todos": [],
            "tool_calls": [],  # Reset tool calls for this turn
            "canvas": existing_canvas,  # Preserve existing canvas
            "response": "",
            "error": None,
            "interrupt": None,  # Clear any previous interrupt
            "last_update": time.time(),
            "start_time": time.time(),  # Track when agent started
        })

    # Start background thread
    thread = threading.Thread(target=_run_agent_stream, args=(message, resume_data))
    thread.daemon = True
    thread.start()


def resume_agent_from_interrupt(decision: str, action: str = "approve", action_requests: List[Dict] = None):
    """Resume agent from an interrupt with the user's decision.

    Args:
        decision: User's response/decision text
        action: One of 'approve', 'reject', 'edit'
        action_requests: List of action requests from the interrupt (for edit mode)
    """
    with _agent_state_lock:
        interrupt_data = _agent_state.get("interrupt")
        if not interrupt_data:
            return

        # Get action requests from interrupt data if not provided
        if action_requests is None:
            action_requests = interrupt_data.get("action_requests", [])

        # Clear interrupt and set running, but preserve tool_calls and canvas
        existing_tool_calls = _agent_state.get("tool_calls", []).copy()
        existing_canvas = _agent_state.get("canvas", []).copy()

        _agent_state["interrupt"] = None
        _agent_state["running"] = True
        _agent_state["response"] = ""  # Clear any previous response
        _agent_state["error"] = None  # Clear any previous error
        _agent_state["tool_calls"] = existing_tool_calls  # Keep existing tool calls
        _agent_state["canvas"] = existing_canvas  # Keep canvas
        _agent_state["last_update"] = time.time()

    # Build decisions list in the format expected by deepagents HITL middleware
    # Format: {"decisions": [{"type": "approve"}, {"type": "reject", "message": "..."}, ...]}
    decisions = []

    if action == "approve":
        # Approve all action requests
        for _ in action_requests:
            decisions.append({"type": "approve"})
        # If no action requests, still add one approve decision
        if not decisions:
            decisions.append({"type": "approve"})
    elif action == "reject":
        # When user rejects, stop the agent immediately instead of resuming
        # Set the response to indicate the action was rejected
        reject_message = decision or "User rejected the action"

        # Get tool info for the rejection message
        tool_info = ""
        if action_requests:
            tool_names = [ar.get("tool", "unknown") for ar in action_requests]
            tool_info = f" ({', '.join(tool_names)})"

        with _agent_state_lock:
            _agent_state["running"] = False
            _agent_state["response"] = f"Action rejected{tool_info}: {reject_message}"
            _agent_state["last_update"] = time.time()

        return  # Don't resume the agent
    else:  # edit - provide edited action
        # For edit, we need to provide the edited tool call
        # The decision text should contain the edited command/args
        for action_req in action_requests:
            tool_name = action_req.get("tool", "")

            # If this is a bash command and user provided new command text
            if tool_name == "bash" and decision:
                decisions.append({
                    "type": "edit",
                    "edited_action": {
                        "name": tool_name,
                        "args": {"command": decision}
                    }
                })
            else:
                # For other tools or no input, just approve
                decisions.append({"type": "approve"})

        if not decisions:
            decisions.append({"type": "approve"})

    # Resume value in deepagents format
    resume_value = {"decisions": decisions}

    # Start background thread with resume value
    # Pass a special marker to indicate this is a resume operation
    thread = threading.Thread(target=_run_agent_stream, args=("__RESUME__", resume_value))
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
    external_stylesheets=dmc.styles.ALL,
    external_scripts=[
        "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js",
    ],
    assets_folder=str(Path(__file__).parent / "assets"),
)

# Custom index string for SVG favicon support
app.index_string = '''<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>'''


# =============================================================================
# LAYOUT
# =============================================================================

def create_layout():
    """Create the app layout with current configuration."""
    return create_layout_component(
        workspace_root=WORKSPACE_ROOT,
        app_title=APP_TITLE,
        app_subtitle=APP_SUBTITLE,
        colors=COLORS,
        styles=STYLES,
        agent=agent
    )

# Set layout as a function so it uses current WORKSPACE_ROOT
app.layout = create_layout

# Note: Component rendering functions imported from components module
# These are used in callbacks below with COLORS and STYLES passed as parameters

# =============================================================================
# CALLBACKS
# =============================================================================

# Initial message display
@app.callback(
    Output("chat-messages", "children"),
    [Input("chat-history", "data")],
    [State("theme-store", "data")],
    prevent_initial_call=False
)
def display_initial_messages(history, theme):
    """Display initial welcome message or chat history."""
    if not history:
        return []

    colors = get_colors(theme or "light")
    messages = []
    for msg in history:
        msg_response_time = msg.get("response_time") if msg["role"] == "assistant" else None
        messages.append(format_message(msg["role"], msg["content"], colors, STYLES, is_new=False, response_time=msg_response_time))
        # Render tool calls stored with this message
        if msg.get("tool_calls"):
            tool_calls_block = format_tool_calls_inline(msg["tool_calls"], colors)
            if tool_calls_block:
                messages.append(tool_calls_block)
        # Render todos stored with this message
        if msg.get("todos"):
            todos_block = format_todos_inline(msg["todos"], colors)
            if todos_block:
                messages.append(todos_block)
    return messages

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
     State("chat-history", "data"),
     State("theme-store", "data")],
    prevent_initial_call=True
)
def handle_send_immediate(n_clicks, n_submit, message, history, theme):
    """Phase 1: Immediately show user message and start agent."""
    if not message or not message.strip():
        raise PreventUpdate

    colors = get_colors(theme or "light")
    message = message.strip()
    history = history or []
    history.append({"role": "user", "content": message})

    # Render all history messages including tool calls and todos
    messages = []
    for i, m in enumerate(history):
        is_new = (i == len(history) - 1)
        msg_response_time = m.get("response_time") if m["role"] == "assistant" else None
        messages.append(format_message(m["role"], m["content"], colors, STYLES, is_new=is_new, response_time=msg_response_time))
        # Render tool calls stored with this message
        if m.get("tool_calls"):
            tool_calls_block = format_tool_calls_inline(m["tool_calls"], colors)
            if tool_calls_block:
                messages.append(tool_calls_block)
        # Render todos stored with this message
        if m.get("todos"):
            todos_block = format_todos_inline(m["todos"], colors)
            if todos_block:
                messages.append(todos_block)

    messages.append(format_loading(colors))

    # Start agent in background
    call_agent(message)

    # Enable polling
    return messages, history, "", message, False


@app.callback(
    [Output("chat-messages", "children", allow_duplicate=True),
     Output("chat-history", "data", allow_duplicate=True),
     Output("poll-interval", "disabled", allow_duplicate=True)],
    Input("poll-interval", "n_intervals"),
    [State("chat-history", "data"),
     State("pending-message", "data"),
     State("theme-store", "data")],
    prevent_initial_call=True
)
def poll_agent_updates(n_intervals, history, pending_message, theme):
    """Poll for agent updates and display them in real-time.

    Tool calls are stored in history and persist across turns.
    History items can be:
    - {"role": "user", "content": "..."} - user message
    - {"role": "assistant", "content": "...", "tool_calls": [...]} - assistant message with tool calls
    """
    state = get_agent_state()
    history = history or []
    colors = get_colors(theme or "light")

    def render_history_messages(history_items):
        """Render all history items including tool calls and todos."""
        messages = []
        for msg in history_items:
            msg_response_time = msg.get("response_time") if msg["role"] == "assistant" else None
            messages.append(format_message(msg["role"], msg["content"], colors, STYLES, response_time=msg_response_time))
            # Render tool calls stored with this message
            if msg.get("tool_calls"):
                tool_calls_block = format_tool_calls_inline(msg["tool_calls"], colors)
                if tool_calls_block:
                    messages.append(tool_calls_block)
            # Render todos stored with this message
            if msg.get("todos"):
                todos_block = format_todos_inline(msg["todos"], colors)
                if todos_block:
                    messages.append(todos_block)
        return messages

    # Check for interrupt (human-in-the-loop)
    if state.get("interrupt"):
        # Agent is paused waiting for user input
        messages = render_history_messages(history)

        # Add current turn's thinking/tool_calls/todos before interrupt
        if state["thinking"]:
            thinking_block = format_thinking(state["thinking"], colors)
            if thinking_block:
                messages.append(thinking_block)

        if state.get("tool_calls"):
            tool_calls_block = format_tool_calls_inline(state["tool_calls"], colors)
            if tool_calls_block:
                messages.append(tool_calls_block)

        if state["todos"]:
            todos_block = format_todos_inline(state["todos"], colors)
            if todos_block:
                messages.append(todos_block)

        # Add interrupt UI
        interrupt_block = format_interrupt(state["interrupt"], colors)
        if interrupt_block:
            messages.append(interrupt_block)

        # Disable polling - wait for user to respond to interrupt
        return messages, no_update, True

    # Check if agent is done
    if not state["running"]:
        # Calculate response time
        response_time = None
        if state.get("start_time"):
            response_time = time.time() - state["start_time"]

        # Agent finished - store tool calls and todos with the USER message (they appear after user msg)
        if history:
            # Find the last user message and attach tool calls and todos to it
            for i in range(len(history) - 1, -1, -1):
                if history[i]["role"] == "user":
                    if state.get("tool_calls"):
                        history[i]["tool_calls"] = state["tool_calls"]
                    if state.get("todos"):
                        history[i]["todos"] = state["todos"]
                    break

        # Add assistant response to history (with response time)
        assistant_msg = {
            "role": "assistant",
            "content": state["response"] if state["response"] else f"Error: {state['error']}",
            "response_time": response_time,
        }

        history.append(assistant_msg)

        # Render all history (tool calls and todos are now part of history)
        final_messages = []
        for i, msg in enumerate(history):
            is_new = (i >= len(history) - 1)
            msg_response_time = msg.get("response_time") if msg["role"] == "assistant" else None
            final_messages.append(format_message(msg["role"], msg["content"], colors, STYLES, is_new=is_new, response_time=msg_response_time))
            # Render tool calls stored with this message
            if msg.get("tool_calls"):
                tool_calls_block = format_tool_calls_inline(msg["tool_calls"], colors)
                if tool_calls_block:
                    final_messages.append(tool_calls_block)
            # Render todos stored with this message
            if msg.get("todos"):
                todos_block = format_todos_inline(msg["todos"], colors)
                if todos_block:
                    final_messages.append(todos_block)

        # Disable polling
        return final_messages, history, True
    else:
        # Agent still running - show loading with current thinking/tool_calls/todos
        messages = render_history_messages(history)

        # Add current thinking if available
        if state["thinking"]:
            thinking_block = format_thinking(state["thinking"], colors)
            if thinking_block:
                messages.append(thinking_block)

        # Add current tool calls if available
        if state.get("tool_calls"):
            tool_calls_block = format_tool_calls_inline(state["tool_calls"], colors)
            if tool_calls_block:
                messages.append(tool_calls_block)

        # Add current todos if available
        if state["todos"]:
            todos_block = format_todos_inline(state["todos"], colors)
            if todos_block:
                messages.append(todos_block)

        # Add loading indicator
        messages.append(format_loading(colors))

        # Continue polling
        return messages, no_update, False


# Interrupt handling callbacks
@app.callback(
    [Output("chat-messages", "children", allow_duplicate=True),
     Output("poll-interval", "disabled", allow_duplicate=True)],
    [Input("interrupt-approve-btn", "n_clicks"),
     Input("interrupt-reject-btn", "n_clicks"),
     Input("interrupt-edit-btn", "n_clicks")],
    [State("interrupt-input", "value"),
     State("chat-history", "data"),
     State("theme-store", "data")],
    prevent_initial_call=True
)
def handle_interrupt_response(approve_clicks, reject_clicks, edit_clicks, input_value, history, theme):
    """Handle user response to an interrupt.

    Note: Click parameters are required for Dash callback inputs but we use
    ctx.triggered to determine which button was clicked.
    """
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    triggered_value = ctx.triggered[0].get("value")

    # Only proceed if there was an actual click (value > 0)
    if not triggered_value or triggered_value <= 0:
        raise PreventUpdate

    colors = get_colors(theme or "light")
    history = history or []

    # Determine action based on which button was clicked
    if triggered_id == "interrupt-approve-btn":
        if not approve_clicks or approve_clicks <= 0:
            raise PreventUpdate
        action = "approve"
        decision = input_value or "approved"
    elif triggered_id == "interrupt-reject-btn":
        if not reject_clicks or reject_clicks <= 0:
            raise PreventUpdate
        action = "reject"
        decision = input_value or "rejected"
    elif triggered_id == "interrupt-edit-btn":
        if not edit_clicks or edit_clicks <= 0:
            raise PreventUpdate
        action = "edit"
        decision = input_value or ""
        if not decision:
            raise PreventUpdate  # Need input for edit action
    else:
        raise PreventUpdate

    # Resume the agent with the user's decision
    resume_agent_from_interrupt(decision, action)

    # Show loading state while agent resumes
    messages = []
    for msg in history:
        msg_response_time = msg.get("response_time") if msg["role"] == "assistant" else None
        messages.append(format_message(msg["role"], msg["content"], colors, STYLES, response_time=msg_response_time))
        # Render tool calls stored with this message
        if msg.get("tool_calls"):
            tool_calls_block = format_tool_calls_inline(msg["tool_calls"], colors)
            if tool_calls_block:
                messages.append(tool_calls_block)
        # Render todos stored with this message
        if msg.get("todos"):
            todos_block = format_todos_inline(msg["todos"], colors)
            if todos_block:
                messages.append(todos_block)

    messages.append(format_loading(colors))

    # Re-enable polling
    return messages, False


# Folder toggle callback
@app.callback(
    [Output({"type": "folder-children", "path": ALL}, "style"),
     Output({"type": "folder-icon", "path": ALL}, "style"),
     Output({"type": "folder-children", "path": ALL}, "children")],
    Input({"type": "folder-header", "path": ALL}, "n_clicks"),
    [State({"type": "folder-header", "path": ALL}, "data-realpath"),
     State({"type": "folder-children", "path": ALL}, "id"),
     State({"type": "folder-icon", "path": ALL}, "id"),
     State({"type": "folder-children", "path": ALL}, "style"),
     State({"type": "folder-icon", "path": ALL}, "style"),
     State({"type": "folder-children", "path": ALL}, "children"),
     State("theme-store", "data")],
    prevent_initial_call=True
)
def toggle_folder(n_clicks, real_paths, children_ids, icon_ids, children_styles, icon_styles, children_content, theme):
    """Toggle folder expansion and lazy load contents if needed."""
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks):
        raise PreventUpdate

    colors = get_colors(theme or "light")
    triggered = ctx.triggered[0]["prop_id"]
    try:
        id_str = triggered.rsplit(".", 1)[0]
        id_dict = json.loads(id_str)
        clicked_path = id_dict.get("path")
    except:
        raise PreventUpdate

    # Find the index of the clicked folder to get its real path
    clicked_idx = None
    for i, icon_id in enumerate(icon_ids):
        if icon_id["path"] == clicked_path:
            clicked_idx = i
            break

    if clicked_idx is None:
        raise PreventUpdate

    folder_rel_path = real_paths[clicked_idx] if clicked_idx < len(real_paths) else None
    if not folder_rel_path:
        raise PreventUpdate

    new_children_styles = []
    new_icon_styles = []
    new_children_content = []

    # Process all folder-children elements
    for i, child_id in enumerate(children_ids):
        path = child_id["path"]
        current_style = children_styles[i] if i < len(children_styles) else {"display": "none"}
        current_content = children_content[i] if i < len(children_content) else []

        if path == clicked_path:
            # Toggle this folder
            is_expanded = current_style.get("display") != "none"
            new_children_styles.append({"display": "none" if is_expanded else "block"})

            # If expanding and content is just "Loading...", load the actual contents
            if not is_expanded and current_content:
                # Check if content is the loading placeholder
                if (isinstance(current_content, list) and len(current_content) == 1 and
                    isinstance(current_content[0], dict) and
                    current_content[0].get("props", {}).get("children") == "Loading..."):
                    # Load folder contents using real path
                    try:
                        folder_items = load_folder_contents(folder_rel_path, WORKSPACE_ROOT)
                        loaded_content = render_file_tree(folder_items, colors, STYLES,
                                                          level=folder_rel_path.count("/") + 1,
                                                          parent_path=folder_rel_path)
                        new_children_content.append(loaded_content if loaded_content else current_content)
                    except Exception as e:
                        print(f"Error loading folder {folder_rel_path}: {e}")
                        new_children_content.append(current_content)
                else:
                    new_children_content.append(current_content)
            else:
                new_children_content.append(current_content)
        else:
            new_children_styles.append(current_style)
            new_children_content.append(current_content)

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
                    "color": colors["text_muted"],
                    "transition": "transform 0.2s",
                    "display": "inline-block",
                    "transform": "rotate(0deg)" if is_expanded else "rotate(90deg)",
                })
            else:
                new_icon_styles.append(current_icon_style)
        else:
            new_icon_styles.append(current_icon_style)

    return new_children_styles, new_icon_styles, new_children_content


# File click - open modal
@app.callback(
    [Output("file-modal", "opened"),
     Output("file-modal", "title"),
     Output("modal-content", "children"),
     Output("file-to-view", "data"),
     Output("file-click-tracker", "data")],
    Input({"type": "file-item", "path": ALL}, "n_clicks"),
    [State({"type": "file-item", "path": ALL}, "id"),
     State("file-click-tracker", "data"),
     State("theme-store", "data")],
    prevent_initial_call=True
)
def open_file_modal(all_n_clicks, all_ids, click_tracker, theme):
    """Open file in modal - only on actual new clicks."""
    ctx = callback_context

    if not ctx.triggered_id:
        raise PreventUpdate

    # ctx.triggered_id is the dict {"type": "file-item", "path": "..."}
    if not isinstance(ctx.triggered_id, dict):
        raise PreventUpdate

    if ctx.triggered_id.get("type") != "file-item":
        raise PreventUpdate

    file_path = ctx.triggered_id.get("path")
    if not file_path:
        raise PreventUpdate

    # Find the index of the triggered item to get its click count
    clicked_idx = None
    for i, item_id in enumerate(all_ids):
        if item_id.get("path") == file_path:
            clicked_idx = i
            break

    if clicked_idx is None:
        raise PreventUpdate

    # Get current click count for this file
    current_clicks = all_n_clicks[clicked_idx] if clicked_idx < len(all_n_clicks) else None

    # Must be an actual click (not None, not 0)
    if not current_clicks:
        raise PreventUpdate

    # Check if this is a NEW click vs a re-render with existing clicks
    click_tracker = click_tracker or {}
    prev_clicks = click_tracker.get(file_path, 0)

    # Update tracker regardless of whether we open modal
    new_tracker = click_tracker.copy()
    new_tracker[file_path] = current_clicks

    if current_clicks <= prev_clicks:
        # Not a new click - component was re-rendered or this click was already processed
        # Still need to return updated tracker to avoid stale state
        raise PreventUpdate

    # Verify file exists and is a file
    full_path = WORKSPACE_ROOT / file_path
    if not full_path.exists() or not full_path.is_file():
        raise PreventUpdate

    colors = get_colors(theme or "light")
    content, is_text, error = read_file_content(WORKSPACE_ROOT, file_path)
    filename = Path(file_path).name

    if is_text and content:
        modal_content = html.Pre(
            content,
            style={
                "background": colors["bg_tertiary"],
                "padding": "16px",
                "fontSize": "12px",
                "fontFamily": "'IBM Plex Mono', monospace",
                "overflow": "auto",
                "maxHeight": "60vh",
                "whiteSpace": "pre-wrap",
                "wordBreak": "break-word",
                "margin": "0",
                "color": colors["text_primary"],
            }
        )
    else:
        modal_content = html.Div([
            html.P(error or "Cannot display file", style={
                "color": colors["text_muted"],
                "textAlign": "center",
                "padding": "40px",
            }),
            html.P("Click Download to save the file.", style={
                "color": colors["text_muted"],
                "textAlign": "center",
                "fontSize": "13px",
            })
        ])

    return True, filename, modal_content, file_path, new_tracker

# Modal download button
@app.callback(
    Output("file-download", "data", allow_duplicate=True),
    Input("modal-download-btn", "n_clicks"),
    State("file-to-view", "data"),
    prevent_initial_call=True
)
def download_from_modal(n_clicks, file_path):
    """Download file from modal."""
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    # Verify this callback was actually triggered by the download button
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if triggered_id != "modal-download-btn":
        raise PreventUpdate

    if not n_clicks or not file_path:
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


# Refresh both file tree and canvas content
@app.callback(
    [Output("file-tree", "children"),
     Output("canvas-content", "children", allow_duplicate=True)],
    Input("refresh-btn", "n_clicks"),
    [State("theme-store", "data")],
    prevent_initial_call=True
)
def refresh_sidebar(n_clicks, theme):
    """Refresh both file tree and canvas content."""
    global _agent_state
    colors = get_colors(theme or "light")

    # Refresh file tree
    file_tree = render_file_tree(build_file_tree(WORKSPACE_ROOT, WORKSPACE_ROOT), colors, STYLES)

    # Refresh canvas by reloading from .canvas/canvas.md file
    canvas_items = load_canvas_from_markdown(WORKSPACE_ROOT)

    # Update agent state with reloaded canvas
    with _agent_state_lock:
        _agent_state["canvas"] = canvas_items

    # Render the canvas items
    canvas_content = render_canvas_items(canvas_items, colors)

    return file_tree, canvas_content


# File upload
@app.callback(
    [Output("upload-status", "children"),
     Output("file-tree", "children", allow_duplicate=True)],
    Input("file-upload", "contents"),
    [State("file-upload", "filename"),
     State("theme-store", "data")],
    prevent_initial_call=True
)
def handle_upload(contents, filenames, theme):
    """Handle file uploads."""
    if not contents:
        raise PreventUpdate

    colors = get_colors(theme or "light")
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
        return f"Uploaded: {', '.join(uploaded)}", render_file_tree(build_file_tree(WORKSPACE_ROOT, WORKSPACE_ROOT), colors, STYLES)
    return "Upload failed", no_update


# View toggle callbacks - using SegmentedControl
@app.callback(
    [Output("files-view", "style"),
     Output("canvas-view", "style"),
     Output("open-terminal-btn", "style")],
    [Input("sidebar-view-toggle", "value")],
    prevent_initial_call=True
)
def toggle_view(view_value):
    """Toggle between files and canvas view using SegmentedControl."""
    if not view_value:
        raise PreventUpdate

    if view_value == "canvas":
        # Show canvas, hide files, hide terminal button (not relevant for canvas)
        return (
            {"flex": "1", "display": "none", "flexDirection": "column"},
            {
                "flex": "1",
                "minHeight": "0",
                "display": "flex",
                "flexDirection": "column",
                "overflow": "hidden"
            },
            {"display": "none"}  # Hide terminal button on canvas view
        )
    else:
        # Show files, hide canvas, show terminal button
        return (
            {
                "flex": "1",
                "minHeight": "0",
                "display": "flex",
                "flexDirection": "column",
                "paddingBottom": "5%"
            },
            {
                "flex": "1",
                "minHeight": "0",
                "display": "none",
                "flexDirection": "column",
                "overflow": "hidden"
            },
            {}  # Show terminal button (default styles)
        )


# Canvas content update
@app.callback(
    Output("canvas-content", "children"),
    [Input("poll-interval", "n_intervals"),
     Input("sidebar-view-toggle", "value")],
    [State("theme-store", "data")],
    prevent_initial_call=False
)
def update_canvas_content(n_intervals, view_value, theme):
    """Update canvas content from agent state."""
    state = get_agent_state()
    canvas_items = state.get("canvas", [])
    colors = get_colors(theme or "light")

    # Use imported rendering function
    return render_canvas_items(canvas_items, colors)



# Clear canvas callback
@app.callback(
    Output("canvas-content", "children", allow_duplicate=True),
    Input("clear-canvas-btn", "n_clicks"),
    [State("theme-store", "data")],
    prevent_initial_call=True
)
def clear_canvas(n_clicks, theme):
    """Clear the canvas and archive the .canvas folder with a timestamp."""
    if not n_clicks:
        raise PreventUpdate

    global _agent_state
    colors = get_colors(theme or "light")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Archive .canvas folder if it exists (contains canvas.md and all assets)
    canvas_dir = WORKSPACE_ROOT / ".canvas"
    if canvas_dir.exists() and canvas_dir.is_dir():
        try:
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
        html.Div("🗒", style={
            "fontSize": "48px",
            "textAlign": "center",
            "marginBottom": "16px",
            "opacity": "0.3"
        }),
        html.P("Canvas is empty", style={
            "textAlign": "center",
            "color": colors["text_muted"],
            "fontSize": "14px"
        }),
        html.P("The agent will add visualizations, charts, and notes here", style={
            "textAlign": "center",
            "color": colors["text_muted"],
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
# THEME TOGGLE CALLBACK - Using DMC 2.4 forceColorScheme
# =============================================================================

@app.callback(
    [Output("theme-store", "data"),
     Output("mantine-provider", "forceColorScheme"),
     Output("theme-toggle-btn", "children")],
    [Input("theme-toggle-btn", "n_clicks")],
    [State("theme-store", "data")],
    prevent_initial_call=True
)
def toggle_theme(n_clicks, current_theme):
    """Toggle between light and dark theme using DMC's forceColorScheme."""
    if not n_clicks:
        raise PreventUpdate

    # Toggle theme
    new_theme = "dark" if current_theme == "light" else "light"

    # Update the icon
    toggle_icon = DashIconify(
        icon="radix-icons:sun" if new_theme == "dark" else "radix-icons:moon",
        width=18
    )

    return new_theme, new_theme, toggle_icon


# Callback to initialize theme on page load
@app.callback(
    [Output("mantine-provider", "forceColorScheme", allow_duplicate=True),
     Output("theme-toggle-btn", "children", allow_duplicate=True)],
    [Input("theme-store", "data")],
    prevent_initial_call='initial_duplicate'
)
def initialize_theme(theme):
    """Initialize theme on page load from stored preference."""
    if not theme:
        theme = "light"

    toggle_icon = DashIconify(
        icon="radix-icons:sun" if theme == "dark" else "radix-icons:moon",
        width=18
    )

    return theme, toggle_icon


# =============================================================================
# PROGRAMMATIC API
# =============================================================================

def run_app(
    agent_instance=None,
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
        agent_instance (object, optional): Agent object instance (Python API only)
        workspace (str, optional): Workspace directory path
        agent_spec (str, optional): Agent specification (overrides agent_instance).
            Supports two formats (both use colon separator):
            - File path: "path/to/file.py:object_name"
            - Module path: "mypackage.module:object_name"
        port (int, optional): Port number
        host (str, optional): Host to bind to
        debug (bool, optional): Debug mode
        title (str, optional): Application title
        subtitle (str, optional): Application subtitle
        config_file (str, optional): Path to config file (default: ./config.py)

    Returns:
        int: Exit code (0 for success, non-zero for error)

    Examples:
        >>> # Using agent instance directly
        >>> from cowork_dash import run_app
        >>> my_agent = MyAgent()
        >>> run_app(my_agent, workspace="~/my-workspace")

        >>> # Using agent spec (file path format)
        >>> run_app(agent_spec="my_agent.py:agent", port=8080)

        >>> # Using agent spec (module format)
        >>> run_app(agent_spec="mypackage.agents:my_agent", port=8080)

        >>> # Without agent (manual mode)
        >>> run_app(workspace="~/my-workspace", debug=True)
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

        # Agent priority: agent_spec > agent_instance > config file
        if agent_spec:
            # Load agent from spec (highest priority)
            agent, AGENT_ERROR = load_agent_from_spec(agent_spec)
        elif agent_instance is not None:
            # Use provided agent instance
            agent = agent_instance
            AGENT_ERROR = None
        else:
            # Get agent from config file
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
        # No config file, use CLI args or defaults
        WORKSPACE_ROOT = Path(workspace).resolve() if workspace else config.WORKSPACE_ROOT
        APP_TITLE = title if title else config.APP_TITLE
        APP_SUBTITLE = subtitle if subtitle else config.APP_SUBTITLE
        PORT = port if port is not None else config.PORT
        HOST = host if host else config.HOST
        DEBUG = debug if debug is not None else config.DEBUG

        # Agent priority: agent_spec > agent_instance > config default
        if agent_spec:
            # Load agent from spec (highest priority)
            agent, AGENT_ERROR = load_agent_from_spec(agent_spec)
        elif agent_instance is not None:
            # Use provided agent instance
            agent = agent_instance
            AGENT_ERROR = None
        else:
            # Use default config agent
            agent, AGENT_ERROR = load_agent_from_spec(config.AGENT_SPEC)

    # Ensure workspace exists
    WORKSPACE_ROOT.mkdir(exist_ok=True, parents=True)

    # Set environment variable for agent to access workspace
    # This allows user agents to read DEEPAGENT_WORKSPACE_ROOT
    os.environ['DEEPAGENT_WORKSPACE_ROOT'] = str(WORKSPACE_ROOT)

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
    # Parse CLI arguments
    args = parse_args()

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