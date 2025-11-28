"""File tree and file operations utilities."""

import base64
from pathlib import Path
from typing import List, Dict, Tuple
from dash import html


TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md", ".txt",
    ".yaml", ".yml", ".toml", ".xml", ".csv", ".sh", ".bash", ".sql", ".env",
    ".gitignore", ".dockerignore", ".cfg", ".ini", ".conf", ".log"
}


def is_text_file(filename: str) -> bool:
    """Check if a file can be viewed as text."""
    ext = Path(filename).suffix.lower()
    return ext in TEXT_EXTENSIONS or ext == ""


def build_file_tree(root: Path, workspace_root: Path) -> List[Dict]:
    """Build file tree structure."""
    items = []
    try:
        entries = sorted(root.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        for entry in entries:
            if entry.name.startswith('.'):
                continue
            rel_path = str(entry.relative_to(workspace_root))
            if entry.is_dir():
                items.append({
                    "type": "folder",
                    "name": entry.name,
                    "path": rel_path,
                    "children": build_file_tree(entry, workspace_root)
                })
            else:
                items.append({
                    "type": "file",
                    "name": entry.name,
                    "path": rel_path,
                    "viewable": is_text_file(entry.name)
                })
    except PermissionError:
        pass
    return items


def render_file_tree(items: List[Dict], colors: Dict, styles: Dict, level: int = 0, parent_path: str = "") -> List:
    """Render file tree with collapsible folders."""
    components = []
    indent = level * 20

    for item in items:
        if item["type"] == "folder":
            folder_id = item["path"].replace("/", "_").replace("\\", "_")
            children = item.get("children", [])

            # Folder header (clickable to expand/collapse)
            components.append(
                html.Div([
                    html.Span(
                        "▶",
                        id={"type": "folder-icon", "path": folder_id},
                        style={
                            "marginRight": "8px",
                            "fontSize": "10px",
                            "color": colors["text_muted"],
                            "transition": "transform 0.2s",
                            "display": "inline-block",
                        }
                    ),
                    html.Span(item["name"], style={
                        "fontWeight": "500",
                        "color": colors["text_primary"],
                        "fontSize": "13px",
                    })
                ],
                id={"type": "folder-header", "path": folder_id},
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "padding": "8px 12px",
                    "paddingLeft": f"{12 + indent}px",
                    "cursor": "pointer",
                    "borderBottom": f"1px solid {colors['border_light']}",
                    "userSelect": "none",
                },
                className="folder-header"
                )
            )

            # Folder children (hidden by default) - always create even if empty
            components.append(
                html.Div(
                    render_file_tree(children, colors, styles, level + 1, item["path"]) if children else [
                        html.Div("(empty)", style={
                            "padding": "8px 12px",
                            "paddingLeft": f"{32 + (level + 1) * 20}px",
                            "fontSize": "12px",
                            "color": colors["text_muted"],
                            "fontStyle": "italic",
                        })
                    ],
                    id={"type": "folder-children", "path": folder_id},
                    style={"display": "none"}  # Collapsed by default
                )
            )
        else:
            # File item
            components.append(
                html.Div([
                    html.Span(item["name"], style={
                        "color": colors["text_secondary"],
                        "fontSize": "13px",
                        "flex": "1",
                    }),
                    # Download button
                    html.Span(
                        "↓",
                        id={"type": "download-btn", "path": item["path"]},
                        title="Download",
                        style={
                            "color": colors["text_muted"],
                            "fontSize": "14px",
                            "padding": "0 4px",
                            "cursor": "pointer",
                            "opacity": "0",
                            "transition": "opacity 0.15s",
                        },
                        className="download-btn"
                    )
                ],
                id={"type": "file-item", "path": item["path"]},
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "padding": "8px 12px",
                    "paddingLeft": f"{32 + indent}px",
                    "cursor": "pointer",
                    "borderBottom": f"1px solid {colors['border_light']}",
                    "transition": styles["transition"],
                },
                className="file-item",
                **{"data-viewable": "true" if item["viewable"] else "false"}
                )
            )

    return components


def read_file_content(workspace_root: Path, path: str) -> Tuple[str, bool, str]:
    """Read file content. Returns (content, is_text, error)."""
    full_path = workspace_root / path
    if not full_path.exists() or not full_path.is_file():
        return None, False, "File not found"

    if is_text_file(path):
        try:
            content = full_path.read_text(encoding="utf-8")
            return content, True, None
        except UnicodeDecodeError:
            return None, False, "Binary file - cannot display"
        except Exception as e:
            return None, False, str(e)
    else:
        return None, False, "Binary file - download to view"


def get_file_download_data(workspace_root: Path, path: str) -> Tuple[str, str, str]:
    """Get file data for download. Returns (base64_content, filename, mime_type)."""
    full_path = workspace_root / path
    if not full_path.exists():
        return None, None, None

    try:
        content = full_path.read_bytes()
        b64 = base64.b64encode(content).decode('utf-8')

        # Determine MIME type
        ext = full_path.suffix.lower()
        mime_types = {
            ".txt": "text/plain", ".py": "text/x-python", ".js": "text/javascript",
            ".json": "application/json", ".html": "text/html", ".css": "text/css",
            ".md": "text/markdown", ".csv": "text/csv", ".xml": "text/xml",
            ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
            ".gif": "image/gif", ".zip": "application/zip",
        }
        mime = mime_types.get(ext, "application/octet-stream")

        return b64, full_path.name, mime
    except Exception:
        return None, None, None
