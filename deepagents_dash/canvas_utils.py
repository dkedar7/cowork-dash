"""Canvas utilities for parsing, exporting, and loading canvas objects."""

import io
import json
import base64
import re
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime


def parse_canvas_object(obj: Any, workspace_root: Path) -> Dict[str, Any]:
    """Parse Python objects into canvas-renderable format.

    Supports:
    - pd.DataFrame (inline in markdown)
    - matplotlib.figure.Figure (saved to .canvas/ folder)
    - plotly.graph_objects.Figure (saved to .canvas/ folder)
    - PIL.Image (saved to .canvas/ folder)
    - dict (Plotly JSON - saved to .canvas/ folder)
    - str (Markdown with Mermaid support - inline)
    """
    obj_type = type(obj).__name__
    module = type(obj).__module__

    # Ensure .canvas directory exists
    canvas_dir = workspace_root / ".canvas"
    canvas_dir.mkdir(exist_ok=True)

    # Pandas DataFrame - keep inline
    if module.startswith('pandas') and obj_type == 'DataFrame':
        return {
            "type": "dataframe",
            "data": obj.to_dict('records'),
            "columns": list(obj.columns),
            "html": obj.to_html(index=False, classes="dataframe-table")
        }

    # Matplotlib Figure - save to file
    elif module.startswith('matplotlib') and 'Figure' in obj_type:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"matplotlib_{timestamp}.png"
        filepath = canvas_dir / filename

        obj.savefig(filepath, format='png', bbox_inches='tight', dpi=100)

        # Also store base64 for in-memory rendering
        buf = io.BytesIO()
        obj.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()

        return {
            "type": "matplotlib",
            "file": f".canvas/{filename}",
            "data": img_base64  # Keep for current session rendering
        }

    # Plotly Figure - save to file
    elif module.startswith('plotly') and 'Figure' in obj_type:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"plotly_{timestamp}.json"
        filepath = canvas_dir / filename

        plotly_data = json.loads(obj.to_json())
        filepath.write_text(json.dumps(plotly_data, indent=2))

        return {
            "type": "plotly",
            "file": f".canvas/{filename}",
            "data": plotly_data  # Keep for current session rendering
        }

    # PIL Image - save to file
    elif module.startswith('PIL') and 'Image' in obj_type:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"image_{timestamp}.png"
        filepath = canvas_dir / filename

        obj.save(filepath, format='PNG')

        # Also store base64 for in-memory rendering
        buf = io.BytesIO()
        obj.save(buf, format='PNG')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()

        return {
            "type": "image",
            "file": f".canvas/{filename}",
            "data": img_base64  # Keep for current session rendering
        }

    # Plotly dict format - save to file
    elif isinstance(obj, dict) and ('data' in obj or 'layout' in obj):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"plotly_{timestamp}.json"
        filepath = canvas_dir / filename

        filepath.write_text(json.dumps(obj, indent=2))

        return {
            "type": "plotly",
            "file": f".canvas/{filename}",
            "data": obj  # Keep for current session rendering
        }

    # Markdown string - check for Mermaid diagrams - keep inline
    elif isinstance(obj, str):
        # Check if it's a Mermaid diagram
        if re.search(r'```mermaid', obj, re.IGNORECASE):
            # Extract mermaid code - more flexible pattern
            match = re.search(r'```mermaid\s*\n?(.*?)```', obj, re.DOTALL | re.IGNORECASE)
            if match:
                mermaid_code = match.group(1).strip()
                # Ensure proper formatting - each arrow should be on its own line
                # Replace inline arrows with newlined versions
                mermaid_code = re.sub(r'\s+(-->)\s+', r'\n\1 ', mermaid_code)
                mermaid_code = re.sub(r'\s+(--\|[^|]+\|)\s+', r'\n\1 ', mermaid_code)
                return {
                    "type": "mermaid",
                    "data": mermaid_code
                }

        return {
            "type": "markdown",
            "data": obj
        }

    # Unknown type - convert to string - keep inline
    else:
        return {
            "type": "markdown",
            "data": f"```\n{str(obj)}\n```"
        }


def export_canvas_to_markdown(canvas_items: List[Dict], workspace_root: Path, output_path: str = None):
    """Export canvas to markdown file with file references."""
    if not output_path:
        output_path = workspace_root / "canvas.md"

    lines = [
        "# Canvas Export",
        f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n",
    ]

    for i, parsed in enumerate(canvas_items):
        item_type = parsed.get("type", "unknown")

        # Add title if present
        if "title" in parsed:
            lines.append(f"\n## {parsed['title']}\n")

        if item_type == "markdown":
            lines.append(f"\n{parsed.get('data', '')}\n")

        elif item_type == "mermaid":
            lines.append(f"\n```mermaid\n{parsed.get('data', '')}\n```\n")

        elif item_type == "dataframe":
            lines.append(f"\n{parsed.get('html', '')}\n")

        elif item_type == "matplotlib" or item_type == "image":
            # Reference the file instead of embedding base64
            file_ref = parsed.get("file", "")
            if file_ref:
                lines.append(f"\n![Image]({file_ref})\n")
            else:
                # Fallback to base64 if no file
                img_data = parsed.get("data", "")
                lines.append(f"\n![Chart {i+1}](data:image/png;base64,{img_data})\n")

        elif item_type == "plotly":
            # Reference the file
            file_ref = parsed.get("file", "")
            if file_ref:
                lines.append(f"\n```plotly\n{file_ref}\n```\n")
            else:
                # Fallback to inline
                lines.append(f"\n```json\n{json.dumps(parsed.get('data'), indent=2)}\n```\n")

    # Write to file
    output_file = Path(output_path)
    output_file.write_text("\n".join(lines))
    return str(output_file)


def load_canvas_from_markdown(workspace_root: Path, markdown_path: str = None) -> List[Dict]:
    """Load canvas from markdown file and referenced assets."""
    if not markdown_path:
        markdown_path = workspace_root / "canvas.md"
    else:
        markdown_path = Path(markdown_path)

    if not markdown_path.exists():
        return []

    content = markdown_path.read_text()
    canvas_items = []

    # Split by common patterns
    sections = re.split(r'\n(?=##\s|\!\[|\<table|\`\`\`)', content)

    for section in sections:
        section = section.strip()
        if not section or section.startswith('#'):
            continue

        # Image references
        img_match = re.match(r'!\[.*?\]\((.canvas/[^)]+)\)', section)
        if img_match:
            file_path = workspace_root / img_match.group(1)
            if file_path.exists():
                # Load image and convert to base64
                with open(file_path, 'rb') as f:
                    img_base64 = base64.b64encode(f.read()).decode('utf-8')
                canvas_items.append({
                    "type": "image",
                    "file": img_match.group(1),
                    "data": img_base64
                })
            continue

        # Plotly file references
        plotly_match = re.match(r'```plotly\n(.canvas/[^\n]+)\n```', section, re.DOTALL)
        if plotly_match:
            file_path = workspace_root / plotly_match.group(1)
            if file_path.exists():
                plotly_data = json.loads(file_path.read_text())
                canvas_items.append({
                    "type": "plotly",
                    "file": plotly_match.group(1),
                    "data": plotly_data
                })
            continue

        # Mermaid diagrams
        mermaid_match = re.match(r'```mermaid\n(.*?)\n```', section, re.DOTALL)
        if mermaid_match:
            canvas_items.append({
                "type": "mermaid",
                "data": mermaid_match.group(1).strip()
            })
            continue

        # DataFrames (HTML tables)
        if section.startswith('<table'):
            canvas_items.append({
                "type": "dataframe",
                "html": section
            })
            continue

        # Regular markdown
        if section:
            canvas_items.append({
                "type": "markdown",
                "data": section
            })

    return canvas_items


def add_to_canvas(content: Any, workspace_root: Path) -> Dict[str, Any]:
    """Add an item to the canvas for visualization.

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
        parsed = parse_canvas_object(content, workspace_root)
        # Return the parsed object (deepagents will handle the JSON serialization)
        return parsed
    except Exception as e:
        return {
            "type": "error",
            "data": f"Failed to add to canvas: {str(e)}",
            "error": str(e)
        }
