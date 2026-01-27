"""Custom backend implementation wrapping VirtualFilesystem.

This module provides VirtualFilesystemBackend which implements DeepAgents'
BackendProtocol interface using the existing VirtualFilesystem for storage.
This enables unified file access between the agent and Dash UI in virtual FS mode.
"""

import fnmatch
import re

from deepagents.backends.protocol import (
    BackendProtocol,
    EditResult,
    FileDownloadResponse,
    FileInfo,
    FileUploadResponse,
    GrepMatch,
    WriteResult,
)
from deepagents.backends.utils import (
    check_empty_content,
    format_content_with_line_numbers,
    perform_string_replacement,
)

from .virtual_fs import VirtualFilesystem


class VirtualFilesystemBackend(BackendProtocol):
    """Backend that wraps VirtualFilesystem for session-isolated storage.

    Provides full BackendProtocol support including:
    - Directory operations (ls_info)
    - File read/write with text support
    - Binary file upload/download
    - Grep and glob search

    This backend stores files directly in the VirtualFilesystem instance,
    which is shared between the agent and Dash UI callbacks.

    Unlike StateBackend which stores data in LangGraph checkpoint state,
    this backend writes directly to the VirtualFilesystem. Therefore:
    - files_update is always None (no state updates needed)
    - Changes are immediately visible to other code using the same VirtualFilesystem
    """

    def __init__(self, fs: VirtualFilesystem):
        """Initialize the backend with a VirtualFilesystem instance.

        Args:
            fs: The VirtualFilesystem to use for storage. This instance
                should be shared with Dash callbacks for unified access.
        """
        self.fs = fs

    def _normalize_path(self, path: str) -> str:
        """Ensure path is absolute and within the VirtualFilesystem root."""
        if not path:
            return self.fs._root

        # If path doesn't start with /, treat it as relative to the FS root
        if not path.startswith("/"):
            path = f"{self.fs._root}/{path}"
        # If path starts with / but not with the FS root, prepend the root
        elif not path.startswith(self.fs._root):
            # Strip leading / and prepend root
            path = f"{self.fs._root}/{path.lstrip('/')}"

        # Remove trailing slash except for root
        if path != self.fs._root and path.endswith("/"):
            path = path.rstrip("/")

        return path

    def ls_info(self, path: str) -> list[FileInfo]:
        """List files and directories in path.

        Args:
            path: Absolute path to the directory to list.

        Returns:
            List of FileInfo dicts with path, is_dir, and size fields.
        """
        norm_path = self._normalize_path(path)

        if not self.fs.is_dir(norm_path):
            return []

        results: list[FileInfo] = []
        try:
            for name in self.fs.listdir(norm_path):
                if norm_path == "/":
                    full_path = f"/{name}"
                else:
                    full_path = f"{norm_path}/{name}"

                is_dir = self.fs.is_dir(full_path)

                info: FileInfo = {
                    "path": full_path + ("/" if is_dir else ""),
                    "is_dir": is_dir,
                }

                if not is_dir:
                    try:
                        content = self.fs.read_bytes(full_path)
                        info["size"] = len(content)
                    except Exception:
                        info["size"] = 0
                else:
                    info["size"] = 0

                results.append(info)
        except FileNotFoundError:
            pass

        results.sort(key=lambda x: x.get("path", ""))
        return results

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file with line numbers.

        Args:
            file_path: Absolute path to the file to read.
            offset: Line number to start reading from (0-indexed).
            limit: Maximum number of lines to read.

        Returns:
            Formatted content with line numbers, or error message.
        """
        norm_path = self._normalize_path(file_path)

        if not self.fs.exists(norm_path):
            return f"Error: File '{file_path}' not found"

        if not self.fs.is_file(norm_path):
            return f"Error: '{file_path}' is a directory, not a file"

        try:
            content = self.fs.read_text(norm_path)
        except UnicodeDecodeError:
            return f"Error: Binary file '{file_path}' cannot be read as text"
        except Exception as e:
            return f"Error reading file '{file_path}': {e}"

        empty_msg = check_empty_content(content)
        if empty_msg:
            return empty_msg

        lines = content.splitlines()
        start_idx = offset
        end_idx = min(start_idx + limit, len(lines))

        if start_idx >= len(lines):
            return f"Error: Line offset {offset} exceeds file length ({len(lines)} lines)"

        selected_lines = lines[start_idx:end_idx]
        return format_content_with_line_numbers(selected_lines, start_line=start_idx + 1)

    def write(self, file_path: str, content: str) -> WriteResult:
        """Create a new file (error if file exists).

        Args:
            file_path: Absolute path where the file should be created.
            content: String content to write to the file.

        Returns:
            WriteResult with path on success, or error message on failure.
            files_update is always None since we write directly to VirtualFilesystem.
        """
        norm_path = self._normalize_path(file_path)

        if self.fs.exists(norm_path):
            return WriteResult(
                error=f"Cannot write to {file_path} because it already exists. "
                "Use edit to modify existing files."
            )

        # Ensure parent directory exists
        parent = "/".join(norm_path.split("/")[:-1]) or "/"
        if parent != "/" and not self.fs.is_dir(parent):
            try:
                self.fs.mkdir(parent, parents=True, exist_ok=True)
            except Exception as e:
                return WriteResult(error=f"Cannot create parent directory: {e}")

        try:
            self.fs.write_text(norm_path, content)
            return WriteResult(path=norm_path, files_update=None)
        except Exception as e:
            return WriteResult(error=f"Error writing file: {e}")

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """Edit file by replacing strings.

        Args:
            file_path: Absolute path to the file to edit.
            old_string: Exact string to search for and replace.
            new_string: String to replace old_string with.
            replace_all: If True, replace all occurrences.

        Returns:
            EditResult with path and occurrences on success, or error message.
            files_update is always None since we write directly to VirtualFilesystem.
        """
        norm_path = self._normalize_path(file_path)

        if not self.fs.exists(norm_path):
            return EditResult(error=f"Error: File '{file_path}' not found")

        if not self.fs.is_file(norm_path):
            return EditResult(error=f"Error: '{file_path}' is a directory, not a file")

        try:
            content = self.fs.read_text(norm_path)
        except UnicodeDecodeError:
            return EditResult(error=f"Error: Binary file '{file_path}' cannot be edited as text")
        except Exception as e:
            return EditResult(error=f"Error reading file: {e}")

        result = perform_string_replacement(content, old_string, new_string, replace_all)

        if isinstance(result, str):
            # Error message returned
            return EditResult(error=result)

        new_content, occurrences = result

        try:
            self.fs.write_text(norm_path, new_content)
            return EditResult(path=norm_path, files_update=None, occurrences=occurrences)
        except Exception as e:
            return EditResult(error=f"Error writing file: {e}")

    def grep_raw(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> list[GrepMatch] | str:
        """Search file contents for pattern.

        Args:
            pattern: Literal string to search for (NOT regex per protocol,
                    but we use regex internally for flexibility).
            path: Optional directory path to search in.
            glob: Optional glob pattern to filter which files to search.

        Returns:
            List of GrepMatch dicts on success, or error string.
        """
        try:
            regex = re.compile(re.escape(pattern))  # Escape for literal matching
        except re.error as e:
            return f"Invalid pattern: {e}"

        norm_path = self._normalize_path(path or "/")
        matches: list[GrepMatch] = []

        def search_dir(dir_path: str) -> None:
            if not self.fs.is_dir(dir_path):
                return

            try:
                entries = self.fs.listdir(dir_path)
            except Exception:
                return

            for name in entries:
                if dir_path == "/":
                    full_path = f"/{name}"
                else:
                    full_path = f"{dir_path}/{name}"

                if self.fs.is_dir(full_path):
                    search_dir(full_path)
                elif self.fs.is_file(full_path):
                    # Apply glob filter if provided
                    if glob and not fnmatch.fnmatch(name, glob):
                        continue

                    try:
                        content = self.fs.read_text(full_path)
                        for line_num, line in enumerate(content.splitlines(), 1):
                            if regex.search(line):
                                matches.append({
                                    "path": full_path,
                                    "line": line_num,
                                    "text": line,
                                })
                    except Exception:
                        pass  # Skip binary or unreadable files

        search_dir(norm_path)
        return matches

    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        """Find files matching glob pattern.

        Args:
            pattern: Glob pattern with wildcards to match file paths.
            path: Base directory to search from.

        Returns:
            List of FileInfo dicts for matching files.
        """
        norm_path = self._normalize_path(path)

        if not self.fs.is_dir(norm_path):
            return []

        results: list[FileInfo] = []

        def search_dir(dir_path: str, relative_base: str) -> None:
            if not self.fs.is_dir(dir_path):
                return

            try:
                entries = self.fs.listdir(dir_path)
            except Exception:
                return

            for name in entries:
                if dir_path == "/":
                    full_path = f"/{name}"
                else:
                    full_path = f"{dir_path}/{name}"

                if relative_base:
                    relative_path = f"{relative_base}/{name}"
                else:
                    relative_path = name

                is_dir = self.fs.is_dir(full_path)

                # Check if this entry matches the pattern
                if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(name, pattern):
                    if is_dir:
                        results.append({
                            "path": full_path + "/",
                            "is_dir": True,
                            "size": 0,
                        })
                    else:
                        try:
                            size = len(self.fs.read_bytes(full_path))
                        except Exception:
                            size = 0
                        results.append({
                            "path": full_path,
                            "is_dir": False,
                            "size": size,
                        })

                # Recurse into directories for ** patterns
                if is_dir and ("**" in pattern or "*" in pattern):
                    search_dir(full_path, relative_path)

        search_dir(norm_path, "")
        return results

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        """Upload binary files.

        Args:
            files: List of (path, content) tuples to upload.

        Returns:
            List of FileUploadResponse objects, one per input file.
        """
        responses: list[FileUploadResponse] = []

        for path, content in files:
            norm_path = self._normalize_path(path)

            # Ensure parent directory exists
            parent = "/".join(norm_path.split("/")[:-1]) or "/"
            if parent != "/" and not self.fs.is_dir(parent):
                try:
                    self.fs.mkdir(parent, parents=True, exist_ok=True)
                except Exception:
                    responses.append(FileUploadResponse(path=path, error="invalid_path"))
                    continue

            try:
                self.fs.write_bytes(norm_path, content)
                responses.append(FileUploadResponse(path=path, error=None))
            except Exception:
                responses.append(FileUploadResponse(path=path, error="permission_denied"))

        return responses

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Download binary files.

        Args:
            paths: List of file paths to download.

        Returns:
            List of FileDownloadResponse objects, one per input path.
        """
        responses: list[FileDownloadResponse] = []

        for path in paths:
            norm_path = self._normalize_path(path)

            if not self.fs.exists(norm_path):
                responses.append(FileDownloadResponse(
                    path=path, content=None, error="file_not_found"
                ))
                continue

            if self.fs.is_dir(norm_path):
                responses.append(FileDownloadResponse(
                    path=path, content=None, error="is_directory"
                ))
                continue

            try:
                content = self.fs.read_bytes(norm_path)
                responses.append(FileDownloadResponse(
                    path=path, content=content, error=None
                ))
            except Exception:
                responses.append(FileDownloadResponse(
                    path=path, content=None, error="permission_denied"
                ))

        return responses
