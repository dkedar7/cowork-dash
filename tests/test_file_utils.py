"""
Tests for file utilities.

Tests cover:
- is_text_file detection
- build_file_tree with physical and virtual filesystems
- load_folder_contents for lazy loading
- read_file_content
- write_file
- create_directory
- Virtual filesystem compatibility
"""

from pathlib import Path

import pytest

from cowork_dash.file_utils import (
    is_text_file,
    build_file_tree,
    load_folder_contents,
    read_file_content,
    write_file,
    create_directory,
    get_file_download_data,
)
from cowork_dash.virtual_fs import VirtualFilesystem


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def physical_workspace(tmp_path):
    """Create a temporary physical workspace with files."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create some files
    (workspace / "readme.md").write_text("# Readme")
    (workspace / "script.py").write_text("print('hello')")
    (workspace / "data.csv").write_text("a,b\n1,2")
    (workspace / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    # Create subdirectory
    subdir = workspace / "src"
    subdir.mkdir()
    (subdir / "main.py").write_text("def main(): pass")

    return workspace


@pytest.fixture
def virtual_workspace():
    """Create a virtual filesystem with files."""
    fs = VirtualFilesystem(root="/workspace")

    fs.write_text("/workspace/readme.md", "# Readme")
    fs.write_text("/workspace/script.py", "print('hello')")
    fs.write_text("/workspace/data.csv", "a,b\n1,2")
    fs.write_bytes("/workspace/image.png", b"\x89PNG\r\n\x1a\n")

    fs.mkdir("/workspace/src", parents=True)
    fs.write_text("/workspace/src/main.py", "def main(): pass")

    return fs


# =============================================================================
# IS_TEXT_FILE TESTS
# =============================================================================


class TestIsTextFile:
    """Tests for is_text_file function."""

    def test_python_files_are_text(self):
        """Test .py files are recognized as text."""
        assert is_text_file("script.py") is True

    def test_markdown_files_are_text(self):
        """Test .md files are recognized as text."""
        assert is_text_file("readme.md") is True

    def test_json_files_are_text(self):
        """Test .json files are recognized as text."""
        assert is_text_file("config.json") is True

    def test_csv_files_are_text(self):
        """Test .csv files are recognized as text."""
        assert is_text_file("data.csv") is True

    def test_html_files_are_text(self):
        """Test .html files are recognized as text."""
        assert is_text_file("index.html") is True

    def test_css_files_are_text(self):
        """Test .css files are recognized as text."""
        assert is_text_file("styles.css") is True

    def test_js_files_are_text(self):
        """Test .js files are recognized as text."""
        assert is_text_file("app.js") is True

    def test_ts_files_are_text(self):
        """Test .ts files are recognized as text."""
        assert is_text_file("app.ts") is True

    def test_yaml_files_are_text(self):
        """Test .yaml and .yml files are recognized as text."""
        assert is_text_file("config.yaml") is True
        assert is_text_file("config.yml") is True

    def test_txt_files_are_text(self):
        """Test .txt files are recognized as text."""
        assert is_text_file("notes.txt") is True

    def test_no_extension_is_text(self):
        """Test files without extension are treated as text."""
        assert is_text_file("Makefile") is True
        assert is_text_file("Dockerfile") is True

    def test_png_files_are_not_text(self):
        """Test .png files are not recognized as text."""
        assert is_text_file("image.png") is False

    def test_jpg_files_are_not_text(self):
        """Test .jpg files are not recognized as text."""
        assert is_text_file("photo.jpg") is False

    def test_pdf_files_are_not_text(self):
        """Test .pdf files are not recognized as text."""
        assert is_text_file("document.pdf") is False

    def test_zip_files_are_not_text(self):
        """Test .zip files are not recognized as text."""
        assert is_text_file("archive.zip") is False

    def test_exe_files_are_not_text(self):
        """Test .exe files are not recognized as text."""
        assert is_text_file("program.exe") is False


# =============================================================================
# BUILD_FILE_TREE TESTS - PHYSICAL
# =============================================================================


class TestBuildFileTreePhysical:
    """Tests for build_file_tree with physical filesystem."""

    def test_returns_list(self, physical_workspace):
        """Test build_file_tree returns a list."""
        result = build_file_tree(physical_workspace, physical_workspace)
        assert isinstance(result, list)

    def test_includes_files(self, physical_workspace):
        """Test result includes files."""
        result = build_file_tree(physical_workspace, physical_workspace)
        names = [item["name"] for item in result]

        assert "readme.md" in names
        assert "script.py" in names

    def test_includes_directories(self, physical_workspace):
        """Test result includes directories."""
        result = build_file_tree(physical_workspace, physical_workspace)
        dirs = [item for item in result if item["type"] == "folder"]
        dir_names = [d["name"] for d in dirs]

        assert "src" in dir_names

    def test_file_items_have_viewable_flag(self, physical_workspace):
        """Test file items have viewable flag."""
        result = build_file_tree(physical_workspace, physical_workspace)
        files = [item for item in result if item["type"] == "file"]

        for f in files:
            assert "viewable" in f

    def test_text_files_are_viewable(self, physical_workspace):
        """Test text files are marked as viewable."""
        result = build_file_tree(physical_workspace, physical_workspace)
        readme = next(item for item in result if item["name"] == "readme.md")

        assert readme["viewable"] is True

    def test_binary_files_not_viewable(self, physical_workspace):
        """Test binary files are not marked as viewable."""
        result = build_file_tree(physical_workspace, physical_workspace)
        image = next(item for item in result if item["name"] == "image.png")

        assert image["viewable"] is False

    def test_folders_have_has_children(self, physical_workspace):
        """Test folders have has_children flag."""
        result = build_file_tree(physical_workspace, physical_workspace)
        src = next(item for item in result if item["name"] == "src")

        assert "has_children" in src
        assert src["has_children"] is True

    def test_hidden_files_excluded(self, physical_workspace):
        """Test hidden files (starting with .) are excluded."""
        (physical_workspace / ".hidden").write_text("secret")

        result = build_file_tree(physical_workspace, physical_workspace)
        names = [item["name"] for item in result]

        assert ".hidden" not in names

    def test_lazy_load_doesnt_recurse(self, physical_workspace):
        """Test lazy_load=True doesn't load children."""
        result = build_file_tree(physical_workspace, physical_workspace, lazy_load=True)
        src = next(item for item in result if item["name"] == "src")

        # Children should be empty list in lazy mode
        assert src["children"] == []

    def test_non_lazy_load_recurses(self, physical_workspace):
        """Test lazy_load=False loads children."""
        result = build_file_tree(physical_workspace, physical_workspace, lazy_load=False)
        src = next(item for item in result if item["name"] == "src")

        # Children should be populated
        assert len(src["children"]) > 0
        child_names = [c["name"] for c in src["children"]]
        assert "main.py" in child_names


# =============================================================================
# BUILD_FILE_TREE TESTS - VIRTUAL
# =============================================================================


class TestBuildFileTreeVirtual:
    """Tests for build_file_tree with virtual filesystem."""

    def test_works_with_virtual_fs(self, virtual_workspace):
        """Test build_file_tree works with VirtualFilesystem."""
        result = build_file_tree(virtual_workspace.root, virtual_workspace)
        assert isinstance(result, list)

    def test_includes_virtual_files(self, virtual_workspace):
        """Test result includes files from virtual filesystem."""
        result = build_file_tree(virtual_workspace.root, virtual_workspace)
        names = [item["name"] for item in result]

        assert "readme.md" in names
        assert "script.py" in names

    def test_includes_virtual_directories(self, virtual_workspace):
        """Test result includes directories from virtual filesystem."""
        result = build_file_tree(virtual_workspace.root, virtual_workspace)
        dirs = [item for item in result if item["type"] == "folder"]
        dir_names = [d["name"] for d in dirs]

        assert "src" in dir_names


# =============================================================================
# LOAD_FOLDER_CONTENTS TESTS
# =============================================================================


class TestLoadFolderContents:
    """Tests for load_folder_contents function."""

    def test_loads_subfolder_physical(self, physical_workspace):
        """Test loading subfolder contents with physical filesystem."""
        result = load_folder_contents("src", physical_workspace)

        names = [item["name"] for item in result]
        assert "main.py" in names

    def test_loads_subfolder_virtual(self, virtual_workspace):
        """Test loading subfolder contents with virtual filesystem."""
        result = load_folder_contents("src", virtual_workspace)

        names = [item["name"] for item in result]
        assert "main.py" in names


# =============================================================================
# READ_FILE_CONTENT TESTS
# =============================================================================


class TestReadFileContent:
    """Tests for read_file_content function."""

    def test_read_text_file_physical(self, physical_workspace):
        """Test reading text file from physical filesystem."""
        content, is_text, error = read_file_content(physical_workspace, "readme.md")

        assert content == "# Readme"
        assert is_text is True
        assert error is None

    def test_read_text_file_virtual(self, virtual_workspace):
        """Test reading text file from virtual filesystem."""
        content, is_text, error = read_file_content(virtual_workspace, "readme.md")

        assert content == "# Readme"
        assert is_text is True
        assert error is None

    def test_read_binary_file_returns_error(self, physical_workspace):
        """Test reading binary file returns appropriate error."""
        content, is_text, error = read_file_content(physical_workspace, "image.png")

        assert content is None
        assert is_text is False
        assert error is not None

    def test_read_nonexistent_file(self, physical_workspace):
        """Test reading nonexistent file returns error."""
        content, is_text, error = read_file_content(physical_workspace, "missing.txt")

        assert content is None
        assert is_text is False
        assert "not found" in error.lower()


# =============================================================================
# WRITE_FILE TESTS
# =============================================================================


class TestWriteFile:
    """Tests for write_file function."""

    def test_write_text_physical(self, physical_workspace):
        """Test writing text file to physical filesystem."""
        result = write_file(physical_workspace, "new.txt", "new content")

        assert result is True
        assert (physical_workspace / "new.txt").read_text() == "new content"

    def test_write_text_virtual(self, virtual_workspace):
        """Test writing text file to virtual filesystem."""
        result = write_file(virtual_workspace, "new.txt", "new content")

        assert result is True
        assert virtual_workspace.read_text("/workspace/new.txt") == "new content"

    def test_write_bytes_physical(self, physical_workspace):
        """Test writing binary file to physical filesystem."""
        result = write_file(physical_workspace, "new.bin", b"\x00\x01\x02")

        assert result is True
        assert (physical_workspace / "new.bin").read_bytes() == b"\x00\x01\x02"

    def test_write_bytes_virtual(self, virtual_workspace):
        """Test writing binary file to virtual filesystem."""
        result = write_file(virtual_workspace, "new.bin", b"\x00\x01\x02")

        assert result is True
        assert virtual_workspace.read_bytes("/workspace/new.bin") == b"\x00\x01\x02"


# =============================================================================
# CREATE_DIRECTORY TESTS
# =============================================================================


class TestCreateDirectory:
    """Tests for create_directory function."""

    def test_create_dir_physical(self, physical_workspace):
        """Test creating directory in physical filesystem."""
        result = create_directory(physical_workspace, "newdir")

        assert result is True
        assert (physical_workspace / "newdir").is_dir()

    def test_create_dir_virtual(self, virtual_workspace):
        """Test creating directory in virtual filesystem."""
        result = create_directory(virtual_workspace, "newdir")

        assert result is True
        assert virtual_workspace.is_dir("/workspace/newdir")

    def test_create_nested_dirs_physical(self, physical_workspace):
        """Test creating nested directories in physical filesystem."""
        result = create_directory(physical_workspace, "a/b/c", parents=True)

        assert result is True
        assert (physical_workspace / "a" / "b" / "c").is_dir()

    def test_create_nested_dirs_virtual(self, virtual_workspace):
        """Test creating nested directories in virtual filesystem."""
        result = create_directory(virtual_workspace, "a/b/c", parents=True)

        assert result is True
        assert virtual_workspace.is_dir("/workspace/a/b/c")

    def test_create_existing_with_exist_ok(self, physical_workspace):
        """Test creating existing directory with exist_ok=True."""
        (physical_workspace / "existing").mkdir()

        result = create_directory(physical_workspace, "existing", exist_ok=True)

        assert result is True


# =============================================================================
# GET_FILE_DOWNLOAD_DATA TESTS
# =============================================================================


class TestGetFileDownloadData:
    """Tests for get_file_download_data function."""

    def test_download_text_file_physical(self, physical_workspace):
        """Test getting download data for text file."""
        b64, filename, mime = get_file_download_data(physical_workspace, "readme.md")

        assert b64 is not None
        assert filename == "readme.md"
        assert mime == "text/markdown"

    def test_download_text_file_virtual(self, virtual_workspace):
        """Test getting download data for text file from virtual fs."""
        b64, filename, mime = get_file_download_data(virtual_workspace, "readme.md")

        assert b64 is not None
        assert filename == "readme.md"

    def test_download_binary_file(self, physical_workspace):
        """Test getting download data for binary file."""
        b64, filename, mime = get_file_download_data(physical_workspace, "image.png")

        assert b64 is not None
        assert filename == "image.png"
        assert mime == "image/png"

    def test_download_nonexistent_file(self, physical_workspace):
        """Test getting download data for nonexistent file."""
        b64, filename, mime = get_file_download_data(physical_workspace, "missing.txt")

        assert b64 is None
        assert filename is None
        assert mime is None

    def test_download_csv_mime_type(self, physical_workspace):
        """Test CSV file has correct MIME type."""
        b64, filename, mime = get_file_download_data(physical_workspace, "data.csv")

        assert mime == "text/csv"

    def test_download_python_mime_type(self, physical_workspace):
        """Test Python file has correct MIME type."""
        b64, filename, mime = get_file_download_data(physical_workspace, "script.py")

        assert mime == "text/x-python"
