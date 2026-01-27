"""
Tests for VirtualFilesystemBackend.

Tests cover:
- BackendProtocol implementation (ls_info, read, write, edit)
- Path normalization for virtual filesystem
- Grep and glob operations
- Binary file upload/download
"""

import pytest

from cowork_dash.virtual_fs import VirtualFilesystem
from cowork_dash.backends import VirtualFilesystemBackend


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def fs():
    """Create a VirtualFilesystem with /workspace root for testing."""
    filesystem = VirtualFilesystem(root="/workspace")
    return filesystem


@pytest.fixture
def backend(fs):
    """Create a VirtualFilesystemBackend for testing."""
    return VirtualFilesystemBackend(fs)


@pytest.fixture
def backend_with_files(backend, fs):
    """Create a backend with some pre-existing files."""
    fs.write_text("/workspace/file1.txt", "content of file 1")
    fs.write_text("/workspace/file2.py", "print('hello')")
    fs.mkdir("/workspace/subdir", parents=True)
    fs.write_text("/workspace/subdir/nested.txt", "nested content")
    return backend


# =============================================================================
# PATH NORMALIZATION TESTS
# =============================================================================


class TestPathNormalization:
    """Tests for _normalize_path method."""

    def test_empty_path_returns_root(self, backend, fs):
        """Test empty path returns filesystem root."""
        result = backend._normalize_path("")
        assert result == "/workspace"

    def test_relative_path_prefixed_with_root(self, backend):
        """Test relative path is prefixed with root."""
        result = backend._normalize_path("file.txt")
        assert result == "/workspace/file.txt"

    def test_absolute_path_outside_root_rewritten(self, backend):
        """Test absolute path outside root is rewritten to be inside root."""
        result = backend._normalize_path("/other/file.txt")
        assert result == "/workspace/other/file.txt"

    def test_absolute_path_inside_root_unchanged(self, backend):
        """Test absolute path inside root is unchanged."""
        result = backend._normalize_path("/workspace/file.txt")
        assert result == "/workspace/file.txt"

    def test_trailing_slash_removed(self, backend):
        """Test trailing slash is removed from non-root paths."""
        result = backend._normalize_path("/workspace/subdir/")
        assert result == "/workspace/subdir"

    def test_root_trailing_slash_preserved(self, backend):
        """Test root path with trailing slash is handled."""
        result = backend._normalize_path("/workspace")
        assert result == "/workspace"


# =============================================================================
# LS_INFO TESTS
# =============================================================================


class TestLsInfo:
    """Tests for ls_info method."""

    def test_ls_info_empty_dir(self, backend):
        """Test ls_info on empty directory."""
        result = backend.ls_info("/workspace")
        assert result == []

    def test_ls_info_with_files(self, backend_with_files):
        """Test ls_info returns files and directories."""
        result = backend_with_files.ls_info("/workspace")

        paths = [r["path"] for r in result]
        assert "/workspace/file1.txt" in paths
        assert "/workspace/file2.py" in paths
        assert "/workspace/subdir/" in paths

    def test_ls_info_includes_size(self, backend_with_files):
        """Test ls_info includes file sizes."""
        result = backend_with_files.ls_info("/workspace")

        file1 = next(r for r in result if "file1.txt" in r["path"])
        assert "size" in file1
        assert file1["size"] == len("content of file 1")

    def test_ls_info_marks_directories(self, backend_with_files):
        """Test ls_info correctly marks directories."""
        result = backend_with_files.ls_info("/workspace")

        subdir = next(r for r in result if "subdir" in r["path"])
        assert subdir["is_dir"] is True

        file1 = next(r for r in result if "file1.txt" in r["path"])
        assert file1["is_dir"] is False

    def test_ls_info_nonexistent_returns_empty(self, backend):
        """Test ls_info on nonexistent directory returns empty list."""
        result = backend.ls_info("/workspace/missing")
        assert result == []

    def test_ls_info_relative_path(self, backend_with_files):
        """Test ls_info works with relative paths."""
        result = backend_with_files.ls_info("subdir")
        paths = [r["path"] for r in result]
        assert "/workspace/subdir/nested.txt" in paths


# =============================================================================
# READ TESTS
# =============================================================================


class TestRead:
    """Tests for read method."""

    def test_read_file(self, backend_with_files):
        """Test reading a file returns content with line numbers."""
        result = backend_with_files.read("/workspace/file1.txt")
        assert "content of file 1" in result
        assert "1" in result  # Line number

    def test_read_nonexistent_file(self, backend):
        """Test reading nonexistent file returns error."""
        result = backend.read("/workspace/missing.txt")
        assert "Error" in result
        assert "not found" in result.lower()

    def test_read_directory_returns_error(self, backend_with_files):
        """Test reading a directory returns error."""
        result = backend_with_files.read("/workspace/subdir")
        assert "Error" in result
        assert "directory" in result.lower()

    def test_read_with_offset(self, backend, fs):
        """Test reading with offset skips initial lines."""
        fs.write_text("/workspace/multi.txt", "line1\nline2\nline3\nline4")
        result = backend.read("/workspace/multi.txt", offset=2)
        assert "line1" not in result
        assert "line2" not in result
        assert "line3" in result

    def test_read_with_limit(self, backend, fs):
        """Test reading with limit restricts number of lines."""
        fs.write_text("/workspace/multi.txt", "line1\nline2\nline3\nline4")
        result = backend.read("/workspace/multi.txt", limit=2)
        assert "line1" in result
        assert "line2" in result

    def test_read_relative_path(self, backend_with_files):
        """Test reading with relative path."""
        result = backend_with_files.read("file1.txt")
        assert "content of file 1" in result


# =============================================================================
# WRITE TESTS
# =============================================================================


class TestWrite:
    """Tests for write method."""

    def test_write_new_file(self, backend, fs):
        """Test writing a new file."""
        result = backend.write("/workspace/new.txt", "new content")

        assert result.path == "/workspace/new.txt"
        assert result.error is None
        assert fs.read_text("/workspace/new.txt") == "new content"

    def test_write_existing_file_fails(self, backend_with_files, fs):
        """Test writing to existing file returns error."""
        result = backend_with_files.write("/workspace/file1.txt", "overwrite")

        assert result.error is not None
        assert "already exists" in result.error.lower()

    def test_write_creates_parent_directories(self, backend, fs):
        """Test write creates parent directories as needed."""
        result = backend.write("/workspace/a/b/c/file.txt", "deep content")

        assert result.error is None
        assert fs.exists("/workspace/a/b/c/file.txt")

    def test_write_relative_path(self, backend, fs):
        """Test writing with relative path."""
        result = backend.write("relative.txt", "content")

        assert result.error is None
        assert fs.exists("/workspace/relative.txt")


# =============================================================================
# EDIT TESTS
# =============================================================================


class TestEdit:
    """Tests for edit method."""

    def test_edit_single_occurrence(self, backend_with_files, fs):
        """Test editing replaces single occurrence."""
        result = backend_with_files.edit(
            "/workspace/file1.txt",
            old_string="content",
            new_string="CONTENT"
        )

        assert result.error is None
        assert result.occurrences == 1
        assert fs.read_text("/workspace/file1.txt") == "CONTENT of file 1"

    def test_edit_replace_all(self, backend, fs):
        """Test edit with replace_all replaces all occurrences."""
        fs.write_text("/workspace/test.txt", "foo bar foo baz foo")

        result = backend.edit(
            "/workspace/test.txt",
            old_string="foo",
            new_string="FOO",
            replace_all=True
        )

        assert result.error is None
        assert result.occurrences == 3
        assert fs.read_text("/workspace/test.txt") == "FOO bar FOO baz FOO"

    def test_edit_nonexistent_file(self, backend):
        """Test editing nonexistent file returns error."""
        result = backend.edit(
            "/workspace/missing.txt",
            old_string="foo",
            new_string="bar"
        )

        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_edit_string_not_found(self, backend_with_files):
        """Test editing when old_string not found returns error."""
        result = backend_with_files.edit(
            "/workspace/file1.txt",
            old_string="NOTFOUND",
            new_string="replacement"
        )

        assert result.error is not None

    def test_edit_directory_returns_error(self, backend_with_files):
        """Test editing a directory returns error."""
        result = backend_with_files.edit(
            "/workspace/subdir",
            old_string="foo",
            new_string="bar"
        )

        assert result.error is not None
        assert "directory" in result.error.lower()


# =============================================================================
# GREP TESTS
# =============================================================================


class TestGrepRaw:
    """Tests for grep_raw method."""

    def test_grep_finds_matches(self, backend_with_files):
        """Test grep finds matching lines."""
        result = backend_with_files.grep_raw("content")

        assert isinstance(result, list)
        assert len(result) >= 1

        paths = [m["path"] for m in result]
        assert "/workspace/file1.txt" in paths

    def test_grep_returns_line_numbers(self, backend_with_files):
        """Test grep results include line numbers."""
        result = backend_with_files.grep_raw("content")

        match = result[0]
        assert "line" in match
        assert "text" in match

    def test_grep_with_glob_filter(self, backend_with_files):
        """Test grep with glob filter only searches matching files."""
        result = backend_with_files.grep_raw("content", glob="*.txt")

        paths = [m["path"] for m in result]
        # Should find in .txt files
        assert any(".txt" in p for p in paths)

    def test_grep_no_matches(self, backend_with_files):
        """Test grep with no matches returns empty list."""
        result = backend_with_files.grep_raw("DOESNOTEXIST12345")
        assert result == []

    def test_grep_in_subdirectory(self, backend_with_files):
        """Test grep searches subdirectories."""
        result = backend_with_files.grep_raw("nested")

        paths = [m["path"] for m in result]
        assert "/workspace/subdir/nested.txt" in paths


# =============================================================================
# GLOB TESTS
# =============================================================================


class TestGlobInfo:
    """Tests for glob_info method."""

    def test_glob_finds_files(self, backend_with_files):
        """Test glob finds matching files."""
        result = backend_with_files.glob_info("*.txt")

        paths = [r["path"] for r in result]
        assert "/workspace/file1.txt" in paths

    def test_glob_finds_directories(self, backend_with_files):
        """Test glob can match directories."""
        result = backend_with_files.glob_info("sub*")

        paths = [r["path"] for r in result]
        assert "/workspace/subdir/" in paths

    def test_glob_recursive(self, backend_with_files):
        """Test glob with ** pattern matches recursively."""
        result = backend_with_files.glob_info("**/*.txt")

        paths = [r["path"] for r in result]
        # The ** pattern matches files in subdirectories
        assert "/workspace/subdir/nested.txt" in paths


# =============================================================================
# UPLOAD/DOWNLOAD TESTS
# =============================================================================


class TestUploadDownload:
    """Tests for upload_files and download_files methods."""

    def test_upload_single_file(self, backend, fs):
        """Test uploading a single file."""
        files = [("/workspace/uploaded.bin", b"\x00\x01\x02")]
        result = backend.upload_files(files)

        assert len(result) == 1
        assert result[0].error is None
        assert fs.read_bytes("/workspace/uploaded.bin") == b"\x00\x01\x02"

    def test_upload_multiple_files(self, backend, fs):
        """Test uploading multiple files."""
        files = [
            ("/workspace/a.bin", b"aaa"),
            ("/workspace/b.bin", b"bbb"),
        ]
        result = backend.upload_files(files)

        assert len(result) == 2
        assert all(r.error is None for r in result)

    def test_upload_creates_parent_dirs(self, backend, fs):
        """Test upload creates parent directories."""
        files = [("/workspace/deep/nested/file.bin", b"content")]
        result = backend.upload_files(files)

        assert result[0].error is None
        assert fs.exists("/workspace/deep/nested/file.bin")

    def test_download_single_file(self, backend_with_files):
        """Test downloading a single file."""
        result = backend_with_files.download_files(["/workspace/file1.txt"])

        assert len(result) == 1
        assert result[0].error is None
        assert result[0].content == b"content of file 1"

    def test_download_nonexistent_file(self, backend):
        """Test downloading nonexistent file returns error."""
        result = backend.download_files(["/workspace/missing.bin"])

        assert len(result) == 1
        assert result[0].error == "file_not_found"
        assert result[0].content is None

    def test_download_directory_returns_error(self, backend_with_files):
        """Test downloading a directory returns error."""
        result = backend_with_files.download_files(["/workspace/subdir"])

        assert len(result) == 1
        assert result[0].error == "is_directory"

    def test_download_multiple_files(self, backend_with_files):
        """Test downloading multiple files."""
        result = backend_with_files.download_files([
            "/workspace/file1.txt",
            "/workspace/file2.py"
        ])

        assert len(result) == 2
        assert all(r.error is None for r in result)
