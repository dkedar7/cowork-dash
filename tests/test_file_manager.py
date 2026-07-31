"""Tests for FileManager."""

import pytest
from pathlib import Path
from langstage.workspace.file_manager import FileManager


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "hello.py").write_text("print('hello')")
    (tmp_path / "data.csv").write_text("a,b\n1,2\n")
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested content")
    return tmp_path


def test_get_tree(workspace):
    fm = FileManager(workspace)
    tree = fm.get_tree("/", depth=1)
    assert "entries" in tree
    names = [e["name"] for e in tree["entries"]]
    assert "hello.py" in names
    assert "subdir" in names


def test_get_tree_depth_2(workspace):
    fm = FileManager(workspace)
    tree = fm.get_tree("/", depth=2)
    subdir = next(e for e in tree["entries"] if e["name"] == "subdir")
    assert subdir["children"] is not None
    child_names = [c["name"] for c in subdir["children"]]
    assert "nested.txt" in child_names


def test_read_file(workspace):
    fm = FileManager(workspace)
    content = fm.read_file("/hello.py")
    assert content["content"] == "print('hello')"
    assert content["language"] == "python"


def test_read_file_not_found(workspace):
    fm = FileManager(workspace)
    with pytest.raises(FileNotFoundError):
        fm.read_file("/nonexistent.txt")


def test_directory_traversal_prevention(workspace):
    fm = FileManager(workspace)
    with pytest.raises(ValueError, match="escapes workspace"):
        fm.read_file("/../../../etc/passwd")


def test_csv_language(workspace):
    fm = FileManager(workspace)
    content = fm.read_file("/data.csv")
    assert content["language"] == "csv"


# ── preview agrees with the read path on what counts as text (gh #114) ────────
# The file browser renders via GET /api/files/preview, which classified plain-text
# .log/.ini/.cfg/.conf as "binary" (download-only) because preview's LANGUAGE_MAP
# and the read path's is_text_file / TEXT_EXTENSIONS disagreed. They now share
# TEXT_EXTENSIONS as one source of truth, so both detectors agree.


@pytest.mark.parametrize(
    "name,body",
    [
        ("server.log", "INFO server started\nWARN low disk\n"),
        ("settings.ini", "[server]\nhost = localhost\n"),
        ("app.cfg", "key = value\n"),
        ("nginx.conf", "server { listen 80; }\n"),
    ],
)
def test_plain_text_configs_and_logs_preview_as_text_not_binary(tmp_path, name, body):
    (tmp_path / name).write_text(body)
    preview = FileManager(tmp_path).preview_file(name)
    assert preview["preview_type"] == "text", preview
    assert preview["data"] == body  # content is inlined, not a download-only stub
    assert "download_url" not in preview


def test_preview_and_is_text_file_agree_for_the_regressed_extensions(tmp_path):
    # The core invariant of gh #114: is_text_file(f) True ⇒ preview shows text.
    from langstage.file_utils import is_text_file

    for name in ("a.log", "b.ini", "c.cfg", "d.conf"):
        (tmp_path / name).write_text("plain text\n")
        assert is_text_file(name) is True
        assert FileManager(tmp_path).preview_file(name)["preview_type"] == "text"


def test_genuinely_binary_file_still_previews_as_binary(tmp_path):
    # The text-detector union must not loosen the guard for real binaries.
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01\x02\xff\xfe")
    preview = FileManager(tmp_path).preview_file("blob.bin")
    assert preview["preview_type"] == "binary"
    assert "download_url" in preview


def test_sibling_prefix_dir_cannot_escape_workspace(tmp_path):
    """A sibling dir sharing the workspace's name prefix must NOT be reachable.

    The old guard used a plain str startswith() with no separator boundary, so
    `ws-secret` passed the check for workspace `ws` and a ../-relative path could
    read/write/delete outside the workspace. (gh #41 — path traversal)
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    sibling = tmp_path / "ws_secret"
    sibling.mkdir()
    (sibling / "passwd.txt").write_text("SECRET outside the workspace")
    (ws / "inside.txt").write_text("ok")

    fm = FileManager(ws)
    # Legitimate in-workspace access still works.
    assert fm._resolve_path("inside.txt").name == "inside.txt"
    assert fm._resolve_path("/").resolve() == ws.resolve()
    # Every traversal into the prefix-sharing sibling is rejected.
    for escape in ("../ws_secret/passwd.txt", "../ws_secret", "/../ws_secret/passwd.txt"):
        with pytest.raises(ValueError, match="escapes workspace"):
            fm._resolve_path(escape)
