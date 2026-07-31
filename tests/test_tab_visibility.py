"""Tests for tab visibility: show_canvas / show_files config + auto-detection."""

import os

import pytest

from langstage.config import AppConfig, _parse_bool_strict, _parse_optional_bool
from langstage.middleware import CanvasMiddleware, agent_uses_canvas_middleware


# --- _parse_optional_bool -----------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("", None),
        ("1", True),
        ("true", True),
        ("yes", True),
        ("TRUE", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("NO", False),
        ("garbage", None),
    ],
)
def test_parse_optional_bool(value, expected):
    assert _parse_optional_bool(value) is expected


# --- _parse_bool_strict: the resolver caster that closes gh #112 --------------
# The two boolean UI fields go through this strict caster in the _ENV map: a
# recognized token resolves; a NON-EMPTY unrecognized value RAISES so the shared
# resolver's malformed-value guard degrades it to the default (None) with a note and
# does NOT credit the env var -- matching the theme/#104 treatment.


@pytest.mark.parametrize(
    "value,expected",
    [(None, None), ("", None), ("on", True), ("OFF", False), ("1", True), ("0", False)],
)
def test_parse_bool_strict_recognized_values(value, expected):
    assert _parse_bool_strict(value) is expected


@pytest.mark.parametrize("value", ["flase", "yep", "garbage", "2", "tru"])
def test_parse_bool_strict_raises_on_unrecognized_nonempty(value):
    with pytest.raises(ValueError):
        _parse_bool_strict(value)


def _clear_malformed_env_dedupe():
    # The shared resolver dedupes its malformed-env note per (var, value) across a
    # process; clear it so each test can observe its own note regardless of order.
    from langstage_core.host import config as core_config

    core_config._warned_malformed_env_value.clear()


@pytest.mark.parametrize("field", ["SHOW_FILES", "SHOW_CANVAS"])
def test_invalid_show_flag_degrades_to_none_with_note_not_credited(
    field, monkeypatch, capsys
):
    # gh #112: a typo (LANGSTAGE_SHOW_FILES=flase, meant to HIDE the tab) must NOT be
    # silently swallowed to auto and credited to the env var in --show-config. It now
    # degrades to the default (None) with a one-line stderr note, source repointed to
    # "default" -- exactly the #104 / theme behavior, for these two bool fields.
    _clear_malformed_env_dedupe()
    monkeypatch.setenv(f"LANGSTAGE_{field}", "flase")
    cfg = AppConfig.from_env()  # must NOT raise

    attr = field.lower()
    assert getattr(cfg, attr) is None  # degraded to auto, not silently mis-set
    assert cfg.sources[attr] == "default"  # not credited to the rejected env var
    err = capsys.readouterr().err
    assert f"LANGSTAGE_{field}='flase'" in err  # names the ignored var + value
    assert "using default" in err


@pytest.mark.parametrize(
    "raw,expected", [("off", False), ("false", False), ("on", True), ("1", True)]
)
def test_valid_show_flag_still_resolves_with_env_source(raw, expected, monkeypatch):
    # A VALID value must resolve normally with correct source attribution (only the
    # invalid path degrades).
    monkeypatch.setenv("LANGSTAGE_SHOW_FILES", raw)
    cfg = AppConfig.from_env()
    assert cfg.show_files is expected
    assert cfg.sources["show_files"] == "env:LANGSTAGE_SHOW_FILES"


# --- AppConfig: env + client_dict ---------------------------------------------


def test_appconfig_defaults_show_flags_are_none():
    cfg = AppConfig()
    assert cfg.show_canvas is None
    assert cfg.show_files is None


def test_appconfig_to_client_dict_converts_none_to_true():
    """Unresolved (None) flags should surface to the client as True."""
    cfg = AppConfig()
    d = cfg.to_client_dict()
    assert d["show_canvas"] is True
    assert d["show_files"] is True


def test_appconfig_to_client_dict_respects_explicit_values():
    cfg = AppConfig(show_canvas=False, show_files=False)
    d = cfg.to_client_dict()
    assert d["show_canvas"] is False
    assert d["show_files"] is False


def test_appconfig_from_env_reads_show_flags(monkeypatch):
    monkeypatch.setenv("DEEPAGENT_SHOW_CANVAS", "false")
    monkeypatch.setenv("DEEPAGENT_SHOW_FILES", "true")
    cfg = AppConfig.from_env()
    assert cfg.show_canvas is False
    assert cfg.show_files is True


def test_appconfig_from_env_missing_show_flags_are_none(monkeypatch):
    monkeypatch.delenv("DEEPAGENT_SHOW_CANVAS", raising=False)
    monkeypatch.delenv("DEEPAGENT_SHOW_FILES", raising=False)
    cfg = AppConfig.from_env()
    assert cfg.show_canvas is None
    assert cfg.show_files is None


def test_appconfig_merge_preserves_show_flags():
    base = AppConfig(show_canvas=True, show_files=False)
    merged = base.merge({"show_canvas": False})
    assert merged.show_canvas is False
    assert merged.show_files is False


def test_appconfig_merge_ignores_none_overrides():
    """None in the override dict should not clobber an explicit value."""
    base = AppConfig(show_canvas=True)
    merged = base.merge({"show_canvas": None})
    assert merged.show_canvas is True


# --- agent_uses_canvas_middleware ---------------------------------------------


class _FakeAgentWithCanvas:
    def __init__(self):
        self.middleware = [CanvasMiddleware()]


class _FakeAgentWithOtherMiddleware:
    def __init__(self):
        # Non-CanvasMiddleware objects should not trigger detection
        self.middleware = [object(), "not-middleware"]


class _FakeAgentNoMiddleware:
    pass


class _FakeAgentViaBuilder:
    class _Builder:
        def __init__(self):
            self.middleware = [CanvasMiddleware()]
    def __init__(self):
        self.builder = self._Builder()


def test_detect_canvas_middleware_direct_attribute():
    assert agent_uses_canvas_middleware(_FakeAgentWithCanvas()) is True


def test_detect_canvas_middleware_via_builder():
    assert agent_uses_canvas_middleware(_FakeAgentViaBuilder()) is True


def test_detect_no_canvas_middleware_when_absent():
    assert agent_uses_canvas_middleware(_FakeAgentNoMiddleware()) is False


def test_detect_no_canvas_middleware_when_other_middleware_present():
    assert agent_uses_canvas_middleware(_FakeAgentWithOtherMiddleware()) is False


class _FakeCompiledWithCanvasNode:
    # A BYO deep agent exposes no middleware list — langchain fuses the middleware —
    # but CanvasMiddleware's before_agent hook compiles to a named node. (gh #48)
    nodes = {"__start__": None, "model": None, "tools": None, "CanvasMiddleware.before_agent": None}


class _FakeCompiledWithoutCanvasNode:
    nodes = {"__start__": None, "model": None, "TodoListMiddleware.after_model": None}


def test_detect_canvas_middleware_via_node_name():
    # gh #48: detection must work for a BYO agent that only exposes graph nodes.
    assert agent_uses_canvas_middleware(_FakeCompiledWithCanvasNode()) is True


def test_no_false_positive_from_other_middleware_nodes():
    assert agent_uses_canvas_middleware(_FakeCompiledWithoutCanvasNode()) is False


def test_detect_handles_none_agent():
    # Should not crash on unexpected input
    assert agent_uses_canvas_middleware(None) is False
