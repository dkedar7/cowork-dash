"""
Tests for VirtualFilesystem and SessionManager.

Tests cover:
- VirtualFilesystem basic operations (mkdir, write, read, unlink, rmdir)
- VirtualPath interface compatibility
- SessionManager session lifecycle
- Session isolation between different sessions
- Thread safety
"""

import threading
import time

import pytest

from cowork_dash.virtual_fs import (
    VirtualFilesystem,
    VirtualPath,
    SessionManager,
    get_session_manager,
)


# =============================================================================
# VIRTUALFILESYSTEM TESTS
# =============================================================================


class TestVirtualFilesystem:
    """Tests for VirtualFilesystem class."""

    def test_create_filesystem_with_default_root(self):
        """Test creating a VirtualFilesystem with default root."""
        fs = VirtualFilesystem()
        assert fs._root == "/"
        assert fs.root.name == ""  # Root has empty name

    def test_create_filesystem_with_custom_root(self):
        """Test creating a VirtualFilesystem with custom root."""
        fs = VirtualFilesystem(root="/custom")
        assert fs._root == "/custom"
        assert fs.root.name == "custom"

    def test_mkdir_creates_directory(self):
        """Test mkdir creates a directory."""
        fs = VirtualFilesystem()
        fs.mkdir("/testdir")
        assert fs.is_dir("/testdir")

    def test_mkdir_with_parents(self):
        """Test mkdir with parents=True creates nested directories."""
        fs = VirtualFilesystem()
        fs.mkdir("/a/b/c", parents=True)
        assert fs.is_dir("/a")
        assert fs.is_dir("/a/b")
        assert fs.is_dir("/a/b/c")

    def test_mkdir_without_parents_fails(self):
        """Test mkdir without parents=True fails for nested paths."""
        fs = VirtualFilesystem()
        with pytest.raises(FileNotFoundError):
            fs.mkdir("/a/b/c", parents=False)

    def test_mkdir_exist_ok(self):
        """Test mkdir with exist_ok=True doesn't error on existing dir."""
        fs = VirtualFilesystem()
        fs.mkdir("/testdir")
        # Should not raise
        fs.mkdir("/testdir", exist_ok=True)

    def test_mkdir_exist_ok_false_raises(self):
        """Test mkdir with exist_ok=False raises on existing dir."""
        fs = VirtualFilesystem()
        fs.mkdir("/testdir")
        with pytest.raises(FileExistsError):
            fs.mkdir("/testdir", exist_ok=False)

    def test_write_text_creates_file(self):
        """Test write_text creates a file with content."""
        fs = VirtualFilesystem()
        fs.write_text("/test.txt", "hello world")
        assert fs.exists("/test.txt")
        assert fs.is_file("/test.txt")

    def test_read_text_returns_content(self):
        """Test read_text returns file content."""
        fs = VirtualFilesystem()
        fs.write_text("/test.txt", "hello world")
        content = fs.read_text("/test.txt")
        assert content == "hello world"

    def test_write_bytes_creates_file(self):
        """Test write_bytes creates a file with binary content."""
        fs = VirtualFilesystem()
        fs.write_bytes("/test.bin", b"\x00\x01\x02")
        assert fs.exists("/test.bin")

    def test_read_bytes_returns_content(self):
        """Test read_bytes returns binary file content."""
        fs = VirtualFilesystem()
        fs.write_bytes("/test.bin", b"\x00\x01\x02")
        content = fs.read_bytes("/test.bin")
        assert content == b"\x00\x01\x02"

    def test_read_nonexistent_file_raises(self):
        """Test reading nonexistent file raises FileNotFoundError."""
        fs = VirtualFilesystem()
        with pytest.raises(FileNotFoundError):
            fs.read_text("/missing.txt")

    def test_listdir_returns_entries(self):
        """Test listdir returns directory entries."""
        fs = VirtualFilesystem()
        fs.write_text("/a.txt", "a")
        fs.write_text("/b.txt", "b")
        fs.mkdir("/subdir")

        entries = fs.listdir("/")
        assert set(entries) == {"a.txt", "b.txt", "subdir"}

    def test_listdir_nonexistent_raises(self):
        """Test listdir on nonexistent directory raises."""
        fs = VirtualFilesystem()
        with pytest.raises(FileNotFoundError):
            fs.listdir("/missing")

    def test_unlink_file(self):
        """Test unlink removes a file."""
        fs = VirtualFilesystem()
        fs.write_text("/test.txt", "content")
        fs.unlink("/test.txt")
        assert not fs.exists("/test.txt")

    def test_rmdir_directory(self):
        """Test rmdir removes an empty directory."""
        fs = VirtualFilesystem()
        fs.mkdir("/emptydir")
        fs.rmdir("/emptydir")
        assert not fs.exists("/emptydir")

    def test_unlink_nonexistent_raises(self):
        """Test unlink on nonexistent path raises."""
        fs = VirtualFilesystem()
        with pytest.raises(FileNotFoundError):
            fs.unlink("/missing")

    def test_exists_returns_correct_values(self):
        """Test exists returns True for existing paths."""
        fs = VirtualFilesystem()
        fs.write_text("/test.txt", "content")
        fs.mkdir("/testdir")

        assert fs.exists("/test.txt")
        assert fs.exists("/testdir")
        assert not fs.exists("/missing")

    def test_is_file_returns_correct_values(self):
        """Test is_file distinguishes files from directories."""
        fs = VirtualFilesystem()
        fs.write_text("/test.txt", "content")
        fs.mkdir("/testdir")

        assert fs.is_file("/test.txt")
        assert not fs.is_file("/testdir")
        assert not fs.is_file("/missing")

    def test_is_dir_returns_correct_values(self):
        """Test is_dir distinguishes directories from files."""
        fs = VirtualFilesystem()
        fs.write_text("/test.txt", "content")
        fs.mkdir("/testdir")

        assert fs.is_dir("/testdir")
        assert not fs.is_dir("/test.txt")
        assert not fs.is_dir("/missing")

    def test_path_returns_virtualpath(self):
        """Test path() returns a VirtualPath instance."""
        fs = VirtualFilesystem()
        vp = fs.path("/subdir/file.txt")
        assert isinstance(vp, VirtualPath)
        assert str(vp) == "/subdir/file.txt"

    def test_glob_finds_matching_files(self):
        """Test glob finds files matching pattern."""
        fs = VirtualFilesystem()
        fs.write_text("/a.py", "")
        fs.write_text("/b.py", "")
        fs.write_text("/c.txt", "")

        matches = fs.glob("/", "*.py")
        assert "/a.py" in matches
        assert "/b.py" in matches
        assert "/c.txt" not in matches

    def test_glob_in_subdirectory(self):
        """Test glob works in subdirectory."""
        fs = VirtualFilesystem()
        fs.mkdir("/sub", parents=True)
        fs.write_text("/sub/a.py", "")
        fs.write_text("/sub/b.py", "")

        matches = fs.glob("/sub", "*.py")
        assert "/sub/a.py" in matches
        assert "/sub/b.py" in matches


# =============================================================================
# VIRTUALPATH TESTS
# =============================================================================


class TestVirtualPath:
    """Tests for VirtualPath class (pathlib.Path-like interface)."""

    def test_name_property(self):
        """Test name property returns filename."""
        fs = VirtualFilesystem()
        vp = fs.path("/subdir/file.txt")
        assert vp.name == "file.txt"

    def test_parent_property(self):
        """Test parent property returns parent path."""
        fs = VirtualFilesystem()
        vp = fs.path("/subdir/file.txt")
        parent = vp.parent
        assert str(parent) == "/subdir"

    def test_suffix_property(self):
        """Test suffix property returns file extension."""
        fs = VirtualFilesystem()
        vp = fs.path("/file.txt")
        assert vp.suffix == ".txt"

    def test_exists_method(self):
        """Test exists() method on VirtualPath."""
        fs = VirtualFilesystem()
        fs.write_text("/test.txt", "content")
        vp = fs.path("/test.txt")
        assert vp.exists()
        assert not fs.path("/missing.txt").exists()

    def test_is_dir_method(self):
        """Test is_dir() method on VirtualPath."""
        fs = VirtualFilesystem()
        fs.mkdir("/testdir")
        assert fs.path("/testdir").is_dir()
        fs.write_text("/test.txt", "")
        assert not fs.path("/test.txt").is_dir()

    def test_is_file_method(self):
        """Test is_file() method on VirtualPath."""
        fs = VirtualFilesystem()
        fs.write_text("/test.txt", "")
        assert fs.path("/test.txt").is_file()
        fs.mkdir("/testdir")
        assert not fs.path("/testdir").is_file()

    def test_mkdir_method(self):
        """Test mkdir() method on VirtualPath."""
        fs = VirtualFilesystem()
        vp = fs.path("/newdir")
        vp.mkdir()
        assert fs.is_dir("/newdir")

    def test_read_text_method(self):
        """Test read_text() method on VirtualPath."""
        fs = VirtualFilesystem()
        fs.write_text("/test.txt", "hello")
        vp = fs.path("/test.txt")
        assert vp.read_text() == "hello"

    def test_write_text_method(self):
        """Test write_text() method on VirtualPath."""
        fs = VirtualFilesystem()
        vp = fs.path("/test.txt")
        vp.write_text("hello")
        assert fs.read_text("/test.txt") == "hello"

    def test_read_bytes_method(self):
        """Test read_bytes() method on VirtualPath."""
        fs = VirtualFilesystem()
        fs.write_bytes("/test.bin", b"\x00\x01")
        vp = fs.path("/test.bin")
        assert vp.read_bytes() == b"\x00\x01"

    def test_write_bytes_method(self):
        """Test write_bytes() method on VirtualPath."""
        fs = VirtualFilesystem()
        vp = fs.path("/test.bin")
        vp.write_bytes(b"\x00\x01")
        assert fs.read_bytes("/test.bin") == b"\x00\x01"

    def test_iterdir_method(self):
        """Test iterdir() method on VirtualPath."""
        fs = VirtualFilesystem()
        fs.write_text("/a.txt", "")
        fs.write_text("/b.txt", "")

        entries = list(fs.root.iterdir())
        names = [e.name for e in entries]
        assert "a.txt" in names
        assert "b.txt" in names

    def test_truediv_operator(self):
        """Test / operator for path joining."""
        fs = VirtualFilesystem()
        vp = fs.root / "subdir" / "file.txt"
        assert str(vp) == "/subdir/file.txt"


# =============================================================================
# SESSIONMANAGER TESTS
# =============================================================================


class TestSessionManager:
    """Tests for SessionManager class."""

    def test_create_session(self):
        """Test creating a new session."""
        sm = SessionManager()
        session_id = sm.create_session()

        assert session_id is not None
        assert sm.get_filesystem(session_id) is not None

    def test_create_session_with_custom_id(self):
        """Test creating a session with custom ID."""
        sm = SessionManager()
        sm.create_session("my-session")

        fs = sm.get_filesystem("my-session")
        assert fs is not None

    def test_get_filesystem_returns_none_for_missing(self):
        """Test get_filesystem returns None for nonexistent session."""
        sm = SessionManager()
        assert sm.get_filesystem("nonexistent") is None

    def test_sessions_are_isolated(self):
        """Test that different sessions have isolated filesystems."""
        sm = SessionManager()
        sm.create_session("session1")
        sm.create_session("session2")

        fs1 = sm.get_filesystem("session1")
        fs2 = sm.get_filesystem("session2")

        # Write to session1
        fs1.write_text("/workspace/test.txt", "session1 content")

        # Session2 should not see the file
        assert not fs2.exists("/workspace/test.txt")

        # Session1 should see it
        assert fs1.exists("/workspace/test.txt")
        assert fs1.read_text("/workspace/test.txt") == "session1 content"

    def test_delete_session(self):
        """Test deleting a session."""
        sm = SessionManager()
        sm.create_session("test-session")

        assert sm.get_filesystem("test-session") is not None
        sm.delete_session("test-session")
        assert sm.get_filesystem("test-session") is None

    def test_touch_session_updates_access_time(self):
        """Test accessing a session updates last access time."""
        sm = SessionManager()
        sm.create_session("test-session")

        initial_time = sm._sessions["test-session"]["last_accessed"]
        time.sleep(0.01)  # Small delay
        sm.get_session("test-session")  # This touches the session
        updated_time = sm._sessions["test-session"]["last_accessed"]

        assert updated_time > initial_time

    def test_get_or_create_session(self):
        """Test get_or_create_session creates if needed."""
        sm = SessionManager()

        # First call creates
        session_id = sm.get_or_create_session("new-session")
        assert session_id == "new-session"
        assert sm.get_filesystem("new-session") is not None

        # Second call returns existing
        session_id2 = sm.get_or_create_session("new-session")
        assert session_id2 == "new-session"

    def test_get_thread_id(self):
        """Test get_thread_id returns thread ID for session."""
        sm = SessionManager()
        sm.create_session("test-session")

        thread_id = sm.get_thread_id("test-session")
        assert thread_id is not None
        assert isinstance(thread_id, str)


# =============================================================================
# THREAD SAFETY TESTS
# =============================================================================


class TestThreadSafety:
    """Tests for thread safety of VirtualFilesystem and SessionManager."""

    def test_concurrent_file_writes(self):
        """Test concurrent writes to different files."""
        fs = VirtualFilesystem()
        errors = []

        def write_file(name):
            try:
                for i in range(10):
                    fs.write_text(f"/{name}_{i}.txt", f"content {i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=write_file, args=(f"thread{i}",))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        # Verify all files were created
        for i in range(5):
            for j in range(10):
                assert fs.exists(f"/thread{i}_{j}.txt")

    def test_concurrent_session_creation(self):
        """Test concurrent session creation."""
        sm = SessionManager()
        errors = []
        created_sessions = []

        def create_sessions(prefix):
            try:
                for i in range(10):
                    session_id = sm.create_session(f"{prefix}_{i}")
                    created_sessions.append(session_id)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=create_sessions, args=(f"batch{i}",))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(created_sessions) == 50

        # Verify all sessions exist
        for session_id in created_sessions:
            assert sm.get_filesystem(session_id) is not None


# =============================================================================
# GLOBAL SESSION MANAGER TESTS
# =============================================================================


class TestGlobalSessionManager:
    """Tests for the global session manager singleton."""

    def test_get_session_manager_returns_singleton(self):
        """Test get_session_manager returns the same instance."""
        sm1 = get_session_manager()
        sm2 = get_session_manager()
        assert sm1 is sm2
