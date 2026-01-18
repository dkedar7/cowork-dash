from typing import Any, Dict, List, Optional
import sys
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr

from .config import WORKSPACE_ROOT
from .canvas import parse_canvas_object


# =============================================================================
# JUPYTER-LIKE CODE EXECUTION TOOLS
# =============================================================================

class NotebookState:
    """
    Maintains persistent state for Jupyter-like code execution.

    This class manages:
    - An ordered list of code cells (the "script")
    - A persistent namespace for variable state across cells
    - Execution history and outputs
    - Canvas items generated during cell execution
    """

    def __init__(self):
        self._cells: List[Dict[str, Any]] = []
        self._namespace: Dict[str, Any] = {}
        self._execution_count: int = 0
        self._ipython_shell = None
        self._canvas_items: List[Dict[str, Any]] = []  # Collected canvas items
        self._initialize_namespace()

    def _initialize_namespace(self):
        """Initialize the namespace with common imports and utilities."""
        # Pre-populate with commonly used modules
        init_code = """
import sys
import os
import json
from pathlib import Path

# Data science essentials (imported if available)
try:
    import pandas as pd
except ImportError:
    pass

try:
    import numpy as np
except ImportError:
    pass

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
except ImportError:
    pass

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    pass
"""
        # Execute initialization silently
        try:
            exec(init_code, self._namespace)
        except Exception:
            pass  # Ignore import errors for optional packages

        # Inject add_to_canvas function that captures items
        def _add_to_canvas_wrapper(content: Any) -> Dict[str, Any]:
            """Add content to the canvas for visualization.

            Supports: DataFrames, matplotlib figures, plotly figures,
            PIL images, and markdown strings.
            """
            try:
                parsed = parse_canvas_object(content, workspace_root=WORKSPACE_ROOT)
                self._canvas_items.append(parsed)
                return parsed
            except Exception as e:
                error_result = {
                    "type": "error",
                    "data": f"Failed to add to canvas: {str(e)}",
                    "error": str(e)
                }
                self._canvas_items.append(error_result)
                return error_result

        self._namespace["add_to_canvas"] = _add_to_canvas_wrapper

    def _get_ipython(self):
        """Get or create an IPython InteractiveShell for enhanced execution."""
        if self._ipython_shell is None:
            try:
                from IPython.core.interactiveshell import InteractiveShell
                self._ipython_shell = InteractiveShell.instance()
                # Share the namespace
                self._ipython_shell.user_ns = self._namespace
            except ImportError:
                # IPython not available, will use exec() fallback
                pass
        return self._ipython_shell

    @property
    def cells(self) -> List[Dict[str, Any]]:
        """Return a copy of all cells."""
        return [cell.copy() for cell in self._cells]

    @property
    def namespace(self) -> Dict[str, Any]:
        """Return the current namespace (variable state)."""
        return self._namespace

    def get_cell(self, cell_index: int) -> Optional[Dict[str, Any]]:
        """Get a cell by index."""
        if 0 <= cell_index < len(self._cells):
            return self._cells[cell_index].copy()
        return None

    def add_cell(self, code: str, cell_type: str = "code") -> Dict[str, Any]:
        """Add a new cell to the end of the script."""
        cell = {
            "index": len(self._cells),
            "type": cell_type,
            "source": code,
            "execution_count": None,
            "outputs": [],
            "status": "pending"
        }
        self._cells.append(cell)
        return cell.copy()

    def insert_cell(self, index: int, code: str, cell_type: str = "code") -> Dict[str, Any]:
        """Insert a cell at a specific index."""
        if index < 0:
            index = 0
        if index > len(self._cells):
            index = len(self._cells)

        cell = {
            "index": index,
            "type": cell_type,
            "source": code,
            "execution_count": None,
            "outputs": [],
            "status": "pending"
        }
        self._cells.insert(index, cell)

        # Update indices for subsequent cells
        for i in range(index + 1, len(self._cells)):
            self._cells[i]["index"] = i

        return cell.copy()

    def modify_cell(self, cell_index: int, new_code: str) -> Dict[str, Any]:
        """Modify the code in an existing cell."""
        if not (0 <= cell_index < len(self._cells)):
            return {
                "error": f"Cell index {cell_index} out of range. Valid range: 0-{len(self._cells) - 1}"
            }

        self._cells[cell_index]["source"] = new_code
        self._cells[cell_index]["status"] = "modified"
        self._cells[cell_index]["outputs"] = []  # Clear previous outputs

        return self._cells[cell_index].copy()

    def delete_cell(self, cell_index: int) -> Dict[str, Any]:
        """Delete a cell by index."""
        if not (0 <= cell_index < len(self._cells)):
            return {
                "error": f"Cell index {cell_index} out of range. Valid range: 0-{len(self._cells) - 1}"
            }

        deleted_cell = self._cells.pop(cell_index)

        # Update indices for subsequent cells
        for i in range(cell_index, len(self._cells)):
            self._cells[i]["index"] = i

        return {"deleted": deleted_cell, "remaining_cells": len(self._cells)}

    def execute_cell(self, cell_index: int) -> Dict[str, Any]:
        """Execute a single cell and capture its output."""
        if not (0 <= cell_index < len(self._cells)):
            return {
                "error": f"Cell index {cell_index} out of range. Valid range: 0-{len(self._cells) - 1}"
            }

        cell = self._cells[cell_index]

        if cell["type"] != "code":
            return {
                "index": cell_index,
                "type": cell["type"],
                "source": cell["source"],
                "output": "(markdown cell - not executed)",
                "status": "skipped"
            }

        self._execution_count += 1
        cell["execution_count"] = self._execution_count

        # Track canvas items added during this cell's execution
        canvas_count_before = len(self._canvas_items)

        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        result = {
            "index": cell_index,
            "execution_count": self._execution_count,
            "source": cell["source"],
            "stdout": "",
            "stderr": "",
            "result": None,
            "error": None,
            "status": "success",
            "canvas_items": []  # Canvas items added during execution
        }

        try:
            # Try IPython first for better execution handling
            ipython = self._get_ipython()

            if ipython is not None:
                # Use IPython's run_cell for magic commands support
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    exec_result = ipython.run_cell(cell["source"], store_history=True)

                result["stdout"] = stdout_capture.getvalue()
                result["stderr"] = stderr_capture.getvalue()

                if exec_result.success:
                    if exec_result.result is not None:
                        result["result"] = repr(exec_result.result)
                else:
                    if exec_result.error_in_exec:
                        result["error"] = str(exec_result.error_in_exec)
                        result["status"] = "error"
                    elif exec_result.error_before_exec:
                        result["error"] = str(exec_result.error_before_exec)
                        result["status"] = "error"
            else:
                # Fallback to exec() if IPython is not available
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    # Compile to check for expression vs statement
                    code = cell["source"].strip()

                    # Try to evaluate as expression first (to get return value)
                    try:
                        # Check if it's a simple expression
                        compiled = compile(code, "<cell>", "eval")
                        exec_result = eval(compiled, self._namespace)
                        if exec_result is not None:
                            result["result"] = repr(exec_result)
                    except SyntaxError:
                        # It's a statement, execute it
                        exec(code, self._namespace)

                result["stdout"] = stdout_capture.getvalue()
                result["stderr"] = stderr_capture.getvalue()

        except Exception:
            result["error"] = traceback.format_exc()
            result["status"] = "error"
            result["stdout"] = stdout_capture.getvalue()
            result["stderr"] = stderr_capture.getvalue()

        # Capture any canvas items added during this cell's execution
        canvas_items_added = self._canvas_items[canvas_count_before:]
        result["canvas_items"] = canvas_items_added

        # Store outputs in cell
        cell["outputs"] = [result]
        cell["status"] = result["status"]

        return result

    def execute_all(self) -> List[Dict[str, Any]]:
        """Execute all cells in order."""
        results = []
        for i in range(len(self._cells)):
            results.append(self.execute_cell(i))
        return results

    def get_script(self) -> str:
        """Get all code cells concatenated as a single script."""
        code_cells = [cell["source"] for cell in self._cells if cell["type"] == "code"]
        return "\n\n".join(code_cells)

    def get_variables(self) -> Dict[str, str]:
        """Get a summary of user-defined variables in the namespace."""
        # Filter out modules, builtins, and private variables
        user_vars = {}
        for name, value in self._namespace.items():
            if name.startswith("_"):
                continue
            if isinstance(value, type(sys)):  # Skip modules
                continue
            if callable(value) and hasattr(value, "__module__"):
                # Skip imported functions
                if value.__module__ != "__main__" and value.__module__ not in [None, "builtins"]:
                    continue
            try:
                # Get a short repr
                value_repr = repr(value)
                if len(value_repr) > 100:
                    value_repr = value_repr[:97] + "..."
                user_vars[name] = f"{type(value).__name__}: {value_repr}"
            except Exception:
                user_vars[name] = f"{type(value).__name__}: <unable to repr>"
        return user_vars

    def get_canvas_items(self) -> List[Dict[str, Any]]:
        """Get all canvas items collected during execution."""
        return self._canvas_items.copy()

    def clear_canvas_items(self) -> Dict[str, Any]:
        """Clear collected canvas items."""
        count = len(self._canvas_items)
        self._canvas_items = []
        return {"cleared": count}

    def reset(self):
        """Reset the notebook state (clear all cells and namespace)."""
        self._cells = []
        self._namespace = {}
        self._execution_count = 0
        self._canvas_items = []
        self._initialize_namespace()
        return {"status": "reset", "message": "Notebook state cleared"}


# Global notebook state instance
_notebook_state = NotebookState()


def create_cell(code: str, cell_type: str = "code") -> Dict[str, Any]:
    """
    Create a new code or markdown cell and add it to the end of the script.

    This simulates creating a new cell in a Jupyter notebook. The cell is added
    but not executed - use execute_cell() to run it.

    Args:
        code: The Python code or markdown content for the cell
        cell_type: Either "code" or "markdown" (default: "code")

    Returns:
        Dictionary with cell information including:
        - index: The cell's position in the notebook
        - type: The cell type
        - source: The cell's code/content
        - status: "pending" (not yet executed)

    Examples:
        # Create a code cell
        create_cell("x = 42\\nprint(f'x = {x}')")

        # Create a markdown cell
        create_cell("## Analysis Results", cell_type="markdown")
    """
    return _notebook_state.add_cell(code, cell_type)


def insert_cell(index: int, code: str, cell_type: str = "code") -> Dict[str, Any]:
    """
    Insert a new cell at a specific position in the script.

    This is useful when you need to add code between existing cells,
    such as adding a missing import or intermediate calculation.

    Args:
        index: Position to insert the cell (0-based). Cells after this
               position will be shifted down.
        code: The Python code or markdown content
        cell_type: Either "code" or "markdown" (default: "code")

    Returns:
        Dictionary with cell information including index and status

    Examples:
        # Insert an import at the beginning
        insert_cell(0, "import pandas as pd")

        # Insert a cell between cells 2 and 3
        insert_cell(3, "intermediate_result = process(data)")
    """
    return _notebook_state.insert_cell(index, code, cell_type)


def modify_cell(cell_index: int, new_code: str) -> Dict[str, Any]:
    """
    Modify the code in an existing cell.

    Use this to fix errors, update logic, or refine code in a cell.
    The cell's outputs are cleared and status set to "modified".
    You'll need to re-execute the cell to see the new results.

    Args:
        cell_index: The index of the cell to modify (0-based)
        new_code: The new code to replace the existing code

    Returns:
        Dictionary with updated cell information, or error if index invalid

    Examples:
        # Fix a typo in cell 2
        modify_cell(2, "result = data.groupby('category').mean()")

        # Update a calculation
        modify_cell(0, "threshold = 0.95  # Updated from 0.9")
    """
    return _notebook_state.modify_cell(cell_index, new_code)


def delete_cell(cell_index: int) -> Dict[str, Any]:
    """
    Delete a cell from the script.

    Removes the cell at the specified index. Subsequent cells will have
    their indices updated. Note: This does NOT undo any side effects
    from executing the deleted cell (variables remain in namespace).

    Args:
        cell_index: The index of the cell to delete (0-based)

    Returns:
        Dictionary with deleted cell info and remaining cell count

    Examples:
        # Remove cell 3
        delete_cell(3)
    """
    return _notebook_state.delete_cell(cell_index)


def execute_cell(cell_index: int) -> Dict[str, Any]:
    """
    Execute a single cell and return its output.

    Runs the code in the specified cell within the persistent namespace.
    Variables created or modified will be available to subsequent cells.
    Captures stdout, stderr, and the cell's return value (if any).

    Args:
        cell_index: The index of the cell to execute (0-based)

    Returns:
        Dictionary containing:
        - index: Cell index
        - execution_count: Global execution counter
        - source: The executed code
        - stdout: Captured print() output
        - stderr: Captured error output
        - result: Return value of the last expression (if any)
        - error: Error traceback (if execution failed)
        - status: "success" or "error"

    Examples:
        # Execute the first cell
        execute_cell(0)

        # Execute and check for errors
        result = execute_cell(2)
        if result["status"] == "error":
            print(result["error"])
    """
    return _notebook_state.execute_cell(cell_index)


def execute_all_cells() -> List[Dict[str, Any]]:
    """
    Execute all cells in the script in order.

    Runs each cell sequentially from the beginning. Useful for
    re-running the entire notebook after modifications.

    Returns:
        List of execution results for each cell

    Examples:
        # Run entire notebook
        results = execute_all_cells()
        errors = [r for r in results if r.get("status") == "error"]
    """
    return _notebook_state.execute_all()


def get_script() -> Dict[str, Any]:
    """
    Get the complete script and current state.

    Returns all cells, the concatenated code, and current variable state.
    Useful for reviewing the notebook or exporting the code.

    Returns:
        Dictionary containing:
        - cells: List of all cells with their content and outputs
        - script: All code cells concatenated as a single script
        - variables: Summary of user-defined variables
        - cell_count: Total number of cells

    Examples:
        # Review current state
        state = get_script()
        print(f"Notebook has {state['cell_count']} cells")
        print(state['script'])
    """
    return {
        "cells": _notebook_state.cells,
        "script": _notebook_state.get_script(),
        "variables": _notebook_state.get_variables(),
        "cell_count": len(_notebook_state.cells)
    }


def get_variables() -> Dict[str, str]:
    """
    Get a summary of all user-defined variables in the namespace.

    Returns variable names with their types and values (truncated if long).
    Useful for understanding what data is available for use in new cells.

    Returns:
        Dictionary mapping variable names to "type: value" strings

    Examples:
        # Check available variables
        vars = get_variables()
        for name, info in vars.items():
            print(f"{name}: {info}")
    """
    return _notebook_state.get_variables()


def reset_notebook() -> Dict[str, Any]:
    """
    Reset the notebook state completely.

    Clears all cells and resets the namespace to its initial state.
    Use with caution - this cannot be undone.

    Returns:
        Dictionary confirming the reset

    Examples:
        # Start fresh
        reset_notebook()
    """
    return _notebook_state.reset()


def get_notebook_canvas_items() -> List[Dict[str, Any]]:
    """
    Get all canvas items generated during notebook cell execution.

    When code in cells calls add_to_canvas(), the items are collected here.
    Use this to retrieve visualizations generated by executed code.

    Returns:
        List of canvas item dictionaries with type and data

    Examples:
        # After executing cells that created charts
        items = get_notebook_canvas_items()
        for item in items:
            print(f"Type: {item['type']}")
    """
    return _notebook_state.get_canvas_items()


def clear_notebook_canvas_items() -> Dict[str, Any]:
    """
    Clear all canvas items collected from notebook execution.

    Returns:
        Dictionary with count of cleared items
    """
    return _notebook_state.clear_canvas_items()


# =============================================================================
# CANVAS TOOLS
# =============================================================================

def add_to_canvas(content: Any) -> Dict[str, Any]:
    """Add an item to the canvas for visualization. Canvas is like a note-taking tool where
    you can store charts, dataframes, images, and markdown text for the user to see.

    Args:
        content: Can be a pandas DataFrame, matplotlib Figure, plotly Figure,
                PIL Image, dictionary (for Plotly JSON), or string (for Markdown)
        workspace_root: Path to the workspace root directory

    Returns:
        Dictionary with the parsed canvas object

    Examples:
        # Add a DataFrame
        import pandas as pd
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        add_to_canvas(df)

        # Add a Matplotlib chart
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        add_to_canvas(fig)

        # Add Markdown text
        add_to_canvas("## Key Findings\\n- Point 1\\n- Point 2")
    """
    try:
        # Parse the content into canvas format
        parsed = parse_canvas_object(content, workspace_root=WORKSPACE_ROOT)
        # Return the parsed object (deepagents will handle the JSON serialization)
        return parsed
    except Exception as e:
        return {
            "type": "error",
            "data": f"Failed to add to canvas: {str(e)}",
            "error": str(e)
        }
