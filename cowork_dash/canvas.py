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
            "file": filename,  # Relative to .canvas/ directory where canvas.md lives
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
            "file": filename,  # Relative to .canvas/ directory where canvas.md lives
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
            "file": filename,  # Relative to .canvas/ directory where canvas.md lives
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
            "file": filename,  # Relative to .canvas/ directory where canvas.md lives
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
    # Ensure .canvas directory exists
    canvas_dir = workspace_root / ".canvas"
    canvas_dir.mkdir(exist_ok=True)

    if not output_path:
        output_path = canvas_dir / "canvas.md"

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
        markdown_path = workspace_root / ".canvas" / "canvas.md"
    else:
        markdown_path = Path(markdown_path)

    if not markdown_path.exists():
        return []

    content = markdown_path.read_text()
    canvas_items = []

    # First, extract all code blocks to process them separately
    code_blocks = []

    # Find all mermaid blocks
    for match in re.finditer(r'```mermaid\s*\n(.*?)```', content, re.DOTALL | re.IGNORECASE):
        start, end = match.span()
        code_blocks.append({
            'type': 'mermaid',
            'start': start,
            'end': end,
            'content': match.group(1).strip()
        })

    # Find all plotly blocks (supports both relative filenames and legacy .canvas/ paths)
    for match in re.finditer(r'```plotly\s*\n([^\n]+)\n```', content, re.DOTALL):
        start, end = match.span()
        code_blocks.append({
            'type': 'plotly_file',
            'start': start,
            'end': end,
            'content': match.group(1).strip()
        })

    # Find all image references (supports both relative filenames and legacy .canvas/ paths)
    for match in re.finditer(r'!\[.*?\]\(([^)]+)\)', content):
        start, end = match.span()
        file_ref = match.group(1)
        # Skip data: URLs (base64 embedded images)
        if not file_ref.startswith('data:'):
            code_blocks.append({
                'type': 'image_file',
                'start': start,
                'end': end,
                'content': file_ref
            })

    # Find all HTML tables
    for match in re.finditer(r'<table.*?</table>', content, re.DOTALL):
        start, end = match.span()
        code_blocks.append({
            'type': 'table',
            'start': start,
            'end': end,
            'content': match.group(0)
        })

    # Sort blocks by position
    code_blocks.sort(key=lambda x: x['start'])

    # Process content in order
    last_pos = 0
    for block in code_blocks:
        # Add any markdown content before this block
        if block['start'] > last_pos:
            markdown_text = content[last_pos:block['start']].strip()
            # Clean up metadata lines but keep actual content
            lines = markdown_text.split('\n')
            filtered_lines = []
            for line in lines:
                # Skip only the exact metadata lines
                if line.strip() in ['# Canvas Export', ''] or line.strip().startswith('*Generated:'):
                    continue
                filtered_lines.append(line)

            cleaned_text = '\n'.join(filtered_lines).strip()
            if cleaned_text:
                canvas_items.append({
                    "type": "markdown",
                    "data": cleaned_text
                })

        # Add the block itself
        if block['type'] == 'mermaid':
            canvas_items.append({
                "type": "mermaid",
                "data": block['content']
            })
        elif block['type'] == 'plotly_file':
            file_ref = block['content']
            file_path = markdown_path.parent / file_ref
            if file_path.exists():
                plotly_data = json.loads(file_path.read_text())
                canvas_items.append({
                    "type": "plotly",
                    "file": file_ref,
                    "data": plotly_data
                })
        elif block['type'] == 'image_file':
            file_ref = block['content']
            file_path = markdown_path.parent / file_ref
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    img_base64 = base64.b64encode(f.read()).decode('utf-8')
                canvas_items.append({
                    "type": "image",
                    "file": file_ref,
                    "data": img_base64
                })
        elif block['type'] == 'table':
            canvas_items.append({
                "type": "dataframe",
                "html": block['content']
            })

        last_pos = block['end']

    # Add any remaining markdown after the last block
    if last_pos < len(content):
        markdown_text = content[last_pos:].strip()
        if markdown_text:
            canvas_items.append({
                "type": "markdown",
                "data": markdown_text
            })

    return canvas_items