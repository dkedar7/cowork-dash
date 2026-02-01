"""
Core functionality tests for Cowork Dash.

Tests the main entry points:
- CLI argument parsing (7 tests)
- run_app() Python API (7 tests)
- Agent loading (3 tests)
- Config/platform behavior (4 tests)

Total: 21 tests
"""

import os
from unittest.mock import patch

from cowork_dash.app import run_app, load_agent_from_spec
from cowork_dash.cli import main


# =============================================================================
# CLI TESTS (5 tests)
# =============================================================================


def test_cli_workspace_argument(monkeypatch, tmp_path):
    """Test CLI --workspace argument is parsed correctly."""
    workspace = tmp_path / "test_ws"
    workspace.mkdir()

    test_args = ["cowork-dash", "run", "--workspace", str(workspace)]
    monkeypatch.setattr("sys.argv", test_args)

    with patch("cowork_dash.app.run_app") as mock_run:
        main()
        assert mock_run.call_args[1]["workspace"] == str(workspace)


def test_cli_port_argument(monkeypatch):
    """Test CLI --port argument is parsed as integer."""
    test_args = ["cowork-dash", "run", "--port", "9999"]
    monkeypatch.setattr("sys.argv", test_args)

    with patch("cowork_dash.app.run_app") as mock_run:
        main()
        assert mock_run.call_args[1]["port"] == 9999


def test_cli_agent_argument(monkeypatch):
    """Test CLI --agent argument is passed through."""
    test_args = ["cowork-dash", "run", "--agent", "my_agent.py:agent"]
    monkeypatch.setattr("sys.argv", test_args)

    with patch("cowork_dash.app.run_app") as mock_run:
        main()
        assert mock_run.call_args[1]["agent_spec"] == "my_agent.py:agent"


def test_cli_debug_flag(monkeypatch):
    """Test CLI --debug flag sets debug=True."""
    test_args = ["cowork-dash", "run", "--debug"]
    monkeypatch.setattr("sys.argv", test_args)

    with patch("cowork_dash.app.run_app") as mock_run:
        main()
        assert mock_run.call_args[1]["debug"] is True


def test_cli_title_subtitle(monkeypatch):
    """Test CLI --title and --subtitle arguments."""
    test_args = ["cowork-dash", "run", "--title", "My App"]
    monkeypatch.setattr("sys.argv", test_args)

    with patch("cowork_dash.app.run_app") as mock_run:
        main()
        assert mock_run.call_args[1]["title"] == "My App"


def test_cli_virtual_fs_flag(monkeypatch):
    """Test CLI --virtual-fs flag is passed through."""
    test_args = ["cowork-dash", "run", "--virtual-fs"]
    monkeypatch.setattr("sys.argv", test_args)

    with patch("cowork_dash.app.run_app") as mock_run:
        with patch("platform.system") as mock_platform:
            mock_platform.return_value = "Linux"
            main()
            # On Linux, virtual_fs=True should be passed
            assert mock_run.call_args[1]["virtual_fs"] is True


def test_cli_virtual_fs_warning_on_non_linux(monkeypatch, capsys):
    """Test CLI --virtual-fs shows warning on non-Linux systems."""
    test_args = ["cowork-dash", "run", "--virtual-fs"]
    monkeypatch.setattr("sys.argv", test_args)

    with patch("cowork_dash.app.run_app") as mock_run:
        with patch("platform.system") as mock_platform:
            mock_platform.return_value = "Darwin"  # macOS
            main()
            # Should set virtual_fs to None (fallback to config)
            assert mock_run.call_args[1]["virtual_fs"] is None
            # Should print warning
            captured = capsys.readouterr()
            assert "Warning" in captured.out or "warning" in captured.out.lower()


# =============================================================================
# RUN_APP API TESTS (7 tests)
# =============================================================================


def test_api_agent_instance(tmp_path, sample_agent):
    """Test run_app() accepts agent instance as first parameter."""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    with patch("cowork_dash.app.app.run"):
        run_app(sample_agent, workspace=str(workspace))

        from cowork_dash.app import agent
        assert agent is sample_agent


def test_api_agent_spec_priority(tmp_path, sample_agent):
    """Test agent_spec parameter overrides agent_instance."""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    # Create test agent file
    agent_file = tmp_path / "test_agent.py"
    agent_file.write_text("class Agent:\n    pass\nmy_agent = Agent()\n")

    with patch("cowork_dash.app.app.run"):
        run_app(
            sample_agent,  # Should be ignored
            workspace=str(workspace),
            agent_spec=f"{agent_file}:my_agent"
        )

        from cowork_dash.app import agent
        assert agent.__class__.__name__ == "Agent"


def test_api_workspace_env_var(tmp_path):
    """Test run_app() sets DEEPAGENT_WORKSPACE_ROOT environment variable."""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    with patch("cowork_dash.app.app.run"):
        # Explicitly use physical filesystem mode to ensure env var is set
        run_app(workspace=str(workspace), virtual_fs=False)

        assert os.environ["DEEPAGENT_WORKSPACE_ROOT"] == str(workspace.resolve())


def test_api_port_config(tmp_path):
    """Test run_app() port parameter."""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    with patch("cowork_dash.app.app.run"):
        run_app(workspace=str(workspace), port=9000)

        from cowork_dash.app import PORT
        assert PORT == 9000


def test_api_host_config(tmp_path):
    """Test run_app() host parameter."""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    with patch("cowork_dash.app.app.run"):
        run_app(workspace=str(workspace), host="0.0.0.0")

        from cowork_dash.app import HOST
        assert HOST == "0.0.0.0"


def test_api_debug_config(tmp_path):
    """Test run_app() debug parameter."""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    with patch("cowork_dash.app.app.run"):
        run_app(workspace=str(workspace), debug=True)

        from cowork_dash.app import DEBUG
        assert DEBUG is True


def test_api_title_subtitle_config(tmp_path):
    """Test run_app() title and subtitle parameters."""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    with patch("cowork_dash.app.app.run"):
        run_app(
            workspace=str(workspace),
            title="Custom",
            subtitle="Subtitle"
        )

        from cowork_dash.app import APP_TITLE, APP_SUBTITLE
        assert APP_TITLE == "Custom"
        assert APP_SUBTITLE == "Subtitle"


# =============================================================================
# AGENT LOADING TESTS (3 tests)
# =============================================================================


def test_load_agent_invalid_file():
    """Test loading agent from nonexistent file returns error."""
    agent, error = load_agent_from_spec("missing.py:agent")

    assert agent is None
    assert error is not None
    assert "not found" in error.lower()


def test_load_agent_missing_object(tmp_path):
    """Test loading nonexistent object from file returns error."""
    agent_file = tmp_path / "test.py"
    agent_file.write_text("x = 1\n")

    agent, error = load_agent_from_spec(f"{agent_file}:missing")

    assert agent is None
    assert "not found" in error.lower()


def test_load_agent_success(tmp_path):
    """Test successfully loading agent from spec."""
    agent_file = tmp_path / "agent.py"
    agent_file.write_text("""
class MyAgent:
    def stream(self, input, stream_mode="updates"):
        yield {"response": "test"}

agent = MyAgent()
""")

    loaded_agent, error = load_agent_from_spec(f"{agent_file}:agent")

    assert loaded_agent is not None
    assert error is None
    assert hasattr(loaded_agent, 'stream')


# =============================================================================
# CONFIG TESTS (4 tests)
# =============================================================================


def test_config_is_linux_function():
    """Test is_linux() function returns correct value."""
    from cowork_dash.config import is_linux
    import platform

    expected = platform.system() == "Linux"
    assert is_linux() == expected


def test_config_virtual_fs_disabled_on_non_linux():
    """Test VIRTUAL_FS is False on non-Linux even when requested."""
    import importlib
    from unittest.mock import patch

    # Mock platform.system to return macOS
    with patch("platform.system") as mock_platform:
        mock_platform.return_value = "Darwin"

        # Set env var to request virtual FS
        with patch.dict(os.environ, {"DEEPAGENT_VIRTUAL_FS": "true"}):
            # Reload config module to pick up new values
            import cowork_dash.config as config_module
            importlib.reload(config_module)

            # On non-Linux, VIRTUAL_FS should be False
            assert config_module.VIRTUAL_FS is False
            assert config_module.VIRTUAL_FS_UNAVAILABLE_REASON is not None
            assert "Linux" in config_module.VIRTUAL_FS_UNAVAILABLE_REASON


def test_config_virtual_fs_enabled_on_linux():
    """Test VIRTUAL_FS can be enabled on Linux."""
    import importlib
    from unittest.mock import patch

    # Mock platform.system to return Linux
    with patch("platform.system") as mock_platform:
        mock_platform.return_value = "Linux"

        # Set env var to request virtual FS
        with patch.dict(os.environ, {"DEEPAGENT_VIRTUAL_FS": "true"}):
            # Reload config module to pick up new values
            import cowork_dash.config as config_module
            importlib.reload(config_module)

            # On Linux with env var set, VIRTUAL_FS should be True
            assert config_module.VIRTUAL_FS is True
            assert config_module.VIRTUAL_FS_UNAVAILABLE_REASON is None


def test_config_virtual_fs_default_false():
    """Test VIRTUAL_FS defaults to False."""
    import importlib
    from unittest.mock import patch

    # Remove env var if set
    with patch.dict(os.environ, {}, clear=True):
        # Keep other essential env vars
        os.environ.pop("DEEPAGENT_VIRTUAL_FS", None)

        # Reload config module
        import cowork_dash.config as config_module
        importlib.reload(config_module)

        # Default should be False
        assert config_module.VIRTUAL_FS is False
