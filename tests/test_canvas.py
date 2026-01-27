"""
Tests for canvas parsing, export, and loading.

Tests cover:
- parse_canvas_object for different content types
- export_canvas_to_markdown
- load_canvas_from_markdown
- Round-trip (export then load) preservation
- Virtual filesystem support
"""

import json
from pathlib import Path

import pytest

from cowork_dash.canvas import (
    parse_canvas_object,
    export_canvas_to_markdown,
    load_canvas_from_markdown,
    generate_canvas_id,
)
from cowork_dash.virtual_fs import VirtualFilesystem


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def physical_workspace(tmp_path):
    """Create a temporary physical workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def virtual_workspace():
    """Create a virtual filesystem workspace."""
    fs = VirtualFilesystem(root="/workspace")
    return fs


# =============================================================================
# GENERATE_CANVAS_ID TESTS
# =============================================================================


class TestGenerateCanvasId:
    """Tests for generate_canvas_id function."""

    def test_generates_unique_ids(self):
        """Test that generated IDs are unique."""
        ids = [generate_canvas_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_id_format(self):
        """Test that IDs have expected format."""
        canvas_id = generate_canvas_id()
        assert canvas_id.startswith("canvas_")
        assert len(canvas_id) == len("canvas_") + 8  # 8 hex chars


# =============================================================================
# PARSE_CANVAS_OBJECT TESTS - MARKDOWN
# =============================================================================


class TestParseCanvasObjectMarkdown:
    """Tests for parsing markdown strings."""

    def test_parse_plain_markdown(self, physical_workspace):
        """Test parsing a plain markdown string."""
        result = parse_canvas_object("# Hello World", physical_workspace)

        assert result["type"] == "markdown"
        assert result["data"] == "# Hello World"
        assert "id" in result
        assert "created_at" in result

    def test_parse_markdown_with_title(self, physical_workspace):
        """Test parsing markdown with a title."""
        result = parse_canvas_object(
            "Some content",
            physical_workspace,
            title="My Title"
        )

        assert result["title"] == "My Title"

    def test_parse_markdown_with_custom_id(self, physical_workspace):
        """Test parsing markdown with custom ID."""
        result = parse_canvas_object(
            "Content",
            physical_workspace,
            item_id="custom_id"
        )

        assert result["id"] == "custom_id"


# =============================================================================
# PARSE_CANVAS_OBJECT TESTS - MERMAID
# =============================================================================


class TestParseCanvasObjectMermaid:
    """Tests for parsing mermaid diagrams."""

    def test_parse_mermaid_diagram(self, physical_workspace):
        """Test parsing a mermaid diagram."""
        mermaid_content = """```mermaid
graph TD
    A --> B
```"""
        result = parse_canvas_object(mermaid_content, physical_workspace)

        assert result["type"] == "mermaid"
        assert "graph TD" in result["data"]
        assert "A --> B" in result["data"]

    def test_parse_mermaid_preserves_diagram(self, physical_workspace):
        """Test that mermaid diagram content is preserved."""
        diagram = """flowchart LR
    Start --> Stop"""
        mermaid_content = f"```mermaid\n{diagram}\n```"

        result = parse_canvas_object(mermaid_content, physical_workspace)

        assert result["type"] == "mermaid"
        assert "flowchart LR" in result["data"]


# =============================================================================
# PARSE_CANVAS_OBJECT TESTS - DATAFRAME
# =============================================================================


class TestParseCanvasObjectDataFrame:
    """Tests for parsing pandas DataFrames."""

    def test_parse_dataframe(self, physical_workspace):
        """Test parsing a pandas DataFrame."""
        pytest.importorskip("pandas")
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = parse_canvas_object(df, physical_workspace)

        assert result["type"] == "dataframe"
        assert "data" in result
        assert "columns" in result
        assert "html" in result
        assert result["columns"] == ["a", "b"]

    def test_parse_dataframe_data_format(self, physical_workspace):
        """Test DataFrame data is in records format."""
        pytest.importorskip("pandas")
        import pandas as pd

        df = pd.DataFrame({"x": [1], "y": [2]})
        result = parse_canvas_object(df, physical_workspace)

        assert result["data"] == [{"x": 1, "y": 2}]


# =============================================================================
# PARSE_CANVAS_OBJECT TESTS - PLOTLY DICT
# =============================================================================


class TestParseCanvasObjectPlotlyDict:
    """Tests for parsing Plotly-style dict."""

    def test_parse_plotly_dict_with_data(self, physical_workspace):
        """Test parsing a dict with 'data' key (Plotly format)."""
        plotly_dict = {
            "data": [{"x": [1, 2], "y": [3, 4], "type": "scatter"}],
            "layout": {"title": "Test"}
        }

        result = parse_canvas_object(plotly_dict, physical_workspace)

        assert result["type"] == "plotly"
        assert "file" in result
        assert result["file"].endswith(".json")

        # Verify file was created
        canvas_dir = physical_workspace / ".canvas"
        assert canvas_dir.exists()

    def test_parse_plotly_dict_with_layout_only(self, physical_workspace):
        """Test parsing a dict with only 'layout' key."""
        plotly_dict = {"layout": {"title": "Test"}}

        result = parse_canvas_object(plotly_dict, physical_workspace)

        assert result["type"] == "plotly"


# =============================================================================
# PARSE_CANVAS_OBJECT TESTS - VIRTUAL FILESYSTEM
# =============================================================================


class TestParseCanvasObjectVirtualFS:
    """Tests for parsing with VirtualFilesystem."""

    def test_parse_markdown_virtual_fs(self, virtual_workspace):
        """Test parsing markdown with virtual filesystem."""
        result = parse_canvas_object("# Virtual Test", virtual_workspace)

        assert result["type"] == "markdown"
        assert result["data"] == "# Virtual Test"

    def test_parse_plotly_dict_virtual_fs(self, virtual_workspace):
        """Test parsing Plotly dict creates file in virtual filesystem."""
        plotly_dict = {"data": [], "layout": {}}

        result = parse_canvas_object(plotly_dict, virtual_workspace)

        assert result["type"] == "plotly"
        assert result["file"].endswith(".json")

        # Verify file exists in virtual filesystem
        assert virtual_workspace.exists(f"/workspace/.canvas/{result['file']}")


# =============================================================================
# EXPORT_CANVAS_TO_MARKDOWN TESTS
# =============================================================================


class TestExportCanvasToMarkdown:
    """Tests for export_canvas_to_markdown function."""

    def test_export_empty_canvas(self, physical_workspace):
        """Test exporting empty canvas."""
        result = export_canvas_to_markdown([], physical_workspace)

        assert result.endswith("canvas.md")
        assert (physical_workspace / ".canvas" / "canvas.md").exists()

    def test_export_markdown_item(self, physical_workspace):
        """Test exporting a markdown item."""
        items = [{
            "id": "test_id",
            "type": "markdown",
            "data": "# Test Content"
        }]

        export_canvas_to_markdown(items, physical_workspace)

        content = (physical_workspace / ".canvas" / "canvas.md").read_text()
        assert "# Test Content" in content
        assert "canvas-item:" in content

    def test_export_mermaid_item(self, physical_workspace):
        """Test exporting a mermaid item."""
        items = [{
            "id": "mermaid_id",
            "type": "mermaid",
            "data": "graph TD\n    A --> B"
        }]

        export_canvas_to_markdown(items, physical_workspace)

        content = (physical_workspace / ".canvas" / "canvas.md").read_text()
        assert "```mermaid" in content
        assert "graph TD" in content

    def test_export_with_title(self, physical_workspace):
        """Test exporting item with title."""
        items = [{
            "id": "titled_id",
            "type": "markdown",
            "data": "Content",
            "title": "My Title"
        }]

        export_canvas_to_markdown(items, physical_workspace)

        content = (physical_workspace / ".canvas" / "canvas.md").read_text()
        assert "## My Title" in content

    def test_export_multiple_items(self, physical_workspace):
        """Test exporting multiple items."""
        items = [
            {"id": "id1", "type": "markdown", "data": "First"},
            {"id": "id2", "type": "markdown", "data": "Second"},
        ]

        export_canvas_to_markdown(items, physical_workspace)

        content = (physical_workspace / ".canvas" / "canvas.md").read_text()
        assert "First" in content
        assert "Second" in content

    def test_export_virtual_fs(self, virtual_workspace):
        """Test exporting to virtual filesystem."""
        items = [{"id": "v_id", "type": "markdown", "data": "Virtual content"}]

        result = export_canvas_to_markdown(items, virtual_workspace)

        assert virtual_workspace.exists("/workspace/.canvas/canvas.md")
        content = virtual_workspace.read_text("/workspace/.canvas/canvas.md")
        assert "Virtual content" in content


# =============================================================================
# LOAD_CANVAS_FROM_MARKDOWN TESTS
# =============================================================================


class TestLoadCanvasFromMarkdown:
    """Tests for load_canvas_from_markdown function."""

    def test_load_nonexistent_returns_empty(self, physical_workspace):
        """Test loading from nonexistent file returns empty list."""
        result = load_canvas_from_markdown(physical_workspace)
        assert result == []

    def test_load_markdown_item(self, physical_workspace):
        """Test loading a markdown item."""
        # Create canvas file with metadata
        canvas_dir = physical_workspace / ".canvas"
        canvas_dir.mkdir()
        canvas_file = canvas_dir / "canvas.md"
        canvas_file.write_text("""# Canvas Export

<!-- canvas-item: {"id": "test_id", "type": "markdown"} -->

# Test Content
""")

        result = load_canvas_from_markdown(physical_workspace)

        assert len(result) == 1
        assert result[0]["id"] == "test_id"
        assert result[0]["type"] == "markdown"
        assert "Test Content" in result[0]["data"]

    def test_load_mermaid_item(self, physical_workspace):
        """Test loading a mermaid item."""
        canvas_dir = physical_workspace / ".canvas"
        canvas_dir.mkdir()
        canvas_file = canvas_dir / "canvas.md"
        canvas_file.write_text("""# Canvas Export

<!-- canvas-item: {"id": "mermaid_id", "type": "mermaid"} -->

```mermaid
graph TD
    A --> B
```
""")

        result = load_canvas_from_markdown(physical_workspace)

        assert len(result) == 1
        assert result[0]["type"] == "mermaid"
        assert "graph TD" in result[0]["data"]

    def test_load_preserves_title(self, physical_workspace):
        """Test loading preserves item title."""
        canvas_dir = physical_workspace / ".canvas"
        canvas_dir.mkdir()
        canvas_file = canvas_dir / "canvas.md"
        canvas_file.write_text("""# Canvas Export

<!-- canvas-item: {"id": "titled", "type": "markdown", "title": "My Title"} -->

## My Title

Content here
""")

        result = load_canvas_from_markdown(physical_workspace)

        assert result[0]["title"] == "My Title"

    def test_load_virtual_fs(self, virtual_workspace):
        """Test loading from virtual filesystem."""
        virtual_workspace.mkdir("/workspace/.canvas", parents=True)
        virtual_workspace.write_text("/workspace/.canvas/canvas.md", """# Canvas Export

<!-- canvas-item: {"id": "v_id", "type": "markdown"} -->

Virtual content
""")

        result = load_canvas_from_markdown(virtual_workspace)

        assert len(result) == 1
        assert result[0]["type"] == "markdown"


# =============================================================================
# ROUND-TRIP TESTS
# =============================================================================


class TestRoundTrip:
    """Tests for export then load round-trip."""

    def test_roundtrip_markdown(self, physical_workspace):
        """Test markdown survives round-trip."""
        original = [{
            "id": "rt_id",
            "type": "markdown",
            "data": "# Round Trip Test\n\nSome content here.",
            "title": "RT Title"
        }]

        export_canvas_to_markdown(original, physical_workspace)
        loaded = load_canvas_from_markdown(physical_workspace)

        assert len(loaded) == 1
        assert loaded[0]["id"] == "rt_id"
        assert loaded[0]["type"] == "markdown"
        assert loaded[0]["title"] == "RT Title"

    def test_roundtrip_mermaid(self, physical_workspace):
        """Test mermaid survives round-trip."""
        original = [{
            "id": "mermaid_rt",
            "type": "mermaid",
            "data": "flowchart LR\n    A --> B --> C"
        }]

        export_canvas_to_markdown(original, physical_workspace)
        loaded = load_canvas_from_markdown(physical_workspace)

        assert len(loaded) == 1
        assert loaded[0]["type"] == "mermaid"
        assert "flowchart LR" in loaded[0]["data"]

    def test_roundtrip_multiple_items(self, physical_workspace):
        """Test multiple items survive round-trip."""
        original = [
            {"id": "id1", "type": "markdown", "data": "First item"},
            {"id": "id2", "type": "mermaid", "data": "graph TD\n    X --> Y"},
            {"id": "id3", "type": "markdown", "data": "Third item", "title": "Third"},
        ]

        export_canvas_to_markdown(original, physical_workspace)
        loaded = load_canvas_from_markdown(physical_workspace)

        assert len(loaded) == 3
        ids = [item["id"] for item in loaded]
        assert "id1" in ids
        assert "id2" in ids
        assert "id3" in ids

    def test_roundtrip_virtual_fs(self, virtual_workspace):
        """Test round-trip with virtual filesystem."""
        original = [{
            "id": "vfs_rt",
            "type": "markdown",
            "data": "Virtual round trip"
        }]

        export_canvas_to_markdown(original, virtual_workspace)
        loaded = load_canvas_from_markdown(virtual_workspace)

        assert len(loaded) == 1
        assert loaded[0]["id"] == "vfs_rt"
        assert "Virtual round trip" in loaded[0]["data"]


# =============================================================================
# PLOTLY FILE REFERENCE TESTS
# =============================================================================


class TestPlotlyFileReferences:
    """Tests for Plotly file references in export/load."""

    def test_export_plotly_creates_json_file(self, physical_workspace):
        """Test exporting Plotly item creates JSON file."""
        items = [{
            "id": "plotly_id",
            "type": "plotly",
            "file": "plotly_test.json",
            "data": {"data": [], "layout": {"title": "Test"}}
        }]

        # First create the JSON file as parse_canvas_object would
        canvas_dir = physical_workspace / ".canvas"
        canvas_dir.mkdir(exist_ok=True)
        (canvas_dir / "plotly_test.json").write_text(
            json.dumps(items[0]["data"], indent=2)
        )

        export_canvas_to_markdown(items, physical_workspace)

        content = (canvas_dir / "canvas.md").read_text()
        assert "```plotly" in content
        assert "plotly_test.json" in content

    def test_load_plotly_reads_json_file(self, physical_workspace):
        """Test loading Plotly item reads JSON file."""
        canvas_dir = physical_workspace / ".canvas"
        canvas_dir.mkdir()

        # Create the JSON file
        plotly_data = {"data": [{"x": [1, 2], "y": [3, 4]}], "layout": {}}
        (canvas_dir / "plotly_data.json").write_text(json.dumps(plotly_data))

        # Create canvas.md referencing it
        (canvas_dir / "canvas.md").write_text("""# Canvas Export

<!-- canvas-item: {"id": "plotly_load", "type": "plotly"} -->

```plotly
plotly_data.json
```
""")

        result = load_canvas_from_markdown(physical_workspace)

        assert len(result) == 1
        assert result[0]["type"] == "plotly"
        assert result[0]["file"] == "plotly_data.json"
        assert result[0]["data"] == plotly_data
