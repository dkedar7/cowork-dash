from typing import Any, Dict
from .config import WORKSPACE_ROOT
from .canvas import parse_canvas_object


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
        add_to_canvas(df, workspace_root)

        # Add a Matplotlib chart
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        add_to_canvas(fig, workspace_root)

        # Add Markdown text
        add_to_canvas("## Key Findings\\n- Point 1\\n- Point 2", workspace_root)
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
