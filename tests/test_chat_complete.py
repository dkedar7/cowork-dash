"""Headless one-turn chat: `POST /api/chat/complete` + the shared helper (gh #101).

The buffered endpoint is the synchronous, non-SSE sibling of the streaming chat
pair: one HTTP call, prompt in -> full reply out, with none of the SSE ceremony
(no persistent ``GET /api/stream`` to open first, no event parsing, no task row).
It drives the same ``SessionAdapter`` the streaming routes drive, so the reply is
identical — just buffered. These tests also pin that the streaming path is not
regressed.
"""
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langgraph.graph import END, START, MessagesState, StateGraph

from langstage_core import load_agent_spec
from langstage_core.adapters import SessionAdapter

from langstage.oneturn import OneTurnResult, complete_turn, run_turn_sync
from langstage.server.routes_chat import create_chat_router


def _stub():
    return load_agent_spec("langstage_core.demo.stub:graph")


def _boom_graph():
    def boom(state):
        raise RuntimeError("synthetic model failure")

    b = StateGraph(MessagesState)
    b.add_node("boom", boom)
    b.add_edge(START, "boom")
    b.add_edge("boom", END)
    return b.compile()


def _client(graph):
    app = FastAPI()
    app.include_router(create_chat_router(SessionAdapter(graph=graph)))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


# ── the endpoint ─────────────────────────────────────────────────────────────


async def test_complete_returns_reply_with_no_pre_opened_stream():
    """The whole point: a single POST returns the full reply, cold — no persistent
    GET /api/stream to create the session first (the SSE path's hidden ordering)."""
    async with _client(_stub()) as c:
        r = await c.post("/api/chat/complete", json={"content": "hello buffered"})
    assert r.status_code == 200
    body = r.json()
    assert "hello buffered" in body["content"]  # the demo echoes the user message
    assert body["session_id"]  # a session was created and returned
    assert body["tool_calls"] == []  # shape present (demo has no tools)


async def test_complete_reuses_a_provided_session_id():
    async with _client(_stub()) as c:
        r = await c.post(
            "/api/chat/complete", json={"content": "hi", "session_id": "sess-xyz"}
        )
    assert r.status_code == 200
    assert r.json()["session_id"] == "sess-xyz"


async def test_complete_surfaces_agent_error_as_500():
    async with _client(_boom_graph()) as c:
        r = await c.post("/api/chat/complete", json={"content": "hi"})
    assert r.status_code == 500
    assert "synthetic model failure" in r.json()["detail"]


async def test_streaming_chat_path_is_unchanged():
    """The SSE contract must not regress: a bare POST /api/chat still 404s without a
    session (which only the persistent stream creates) — the buffered path is
    additive, it doesn't loosen the streaming ordering."""
    async with _client(_stub()) as c:
        r = await c.post("/api/chat", json={"session_id": "never-opened", "content": "x"})
    assert r.status_code == 404


# ── the shared helper (one implementation behind CLI + endpoint) ─────────────


async def test_complete_turn_assembles_content_and_outcome():
    adapter = SessionAdapter(graph=_stub())
    result = await complete_turn(adapter, "ping the agent")
    assert isinstance(result, OneTurnResult)
    assert result.ok and result.outcome == "complete"
    assert "ping the agent" in result.content


async def test_complete_turn_reports_agent_error_without_raising():
    adapter = SessionAdapter(graph=_boom_graph())
    result = await complete_turn(adapter, "hi")
    assert not result.ok
    assert result.outcome == "error"
    assert "synthetic model failure" in (result.error or "")


def test_run_turn_sync_drives_one_turn_end_to_end():
    """The blocking entry point the CLI uses: wrap a graph, run one turn, return."""
    result = run_turn_sync(_stub(), "sync smoke")
    assert result.ok
    assert "sync smoke" in result.content


# ── the two siblings feed the agent the SAME input (gh #106) ─────────────────


def test_cli_and_endpoint_feed_the_agent_the_same_input(monkeypatch):
    """gh #106: `langstage chat` and `POST /api/chat/complete` share `complete_turn`
    and are documented as producing an identical, browser-faithful reply — so they must
    feed the agent the *same input* for the same prompt. Previously the CLI withheld the
    per-message `[Current time]` / `[Working directory]` context the web paths inject, so
    the demo echo agent (which reflects its input) returned different replies.

    Drive the endpoint via `httpx.ASGITransport` and the CLI via `CliRunner`, both keyless
    with `--demo` and the same prompt, and assert the replies match. `context_parts` is
    pinned to a fixed value so the assertion is deterministic (no per-second timestamp /
    workspace drift) and targets the real invariant: the CLI now injects the SAME context
    the endpoint does. Fails before the fix (CLI fed no context), passes after.

    This test is synchronous (not the module's default async): the CLI's `run_turn_sync`
    calls `asyncio.run`, which can't be nested inside a running loop, so the endpoint leg
    runs in its own `asyncio.run` and the CLI leg runs after it.
    """
    import asyncio
    import json

    from click.testing import CliRunner

    from langstage import cli as cli_mod
    from langstage.server import routes_chat

    fixed = ["[Current time: 2026-07-25 00:00:00 UTC]", "[Working directory: /ws]"]
    # Both siblings resolve `context_parts` from routes_chat at call time (the endpoint
    # via its module global, the CLI via `routes_chat.context_parts()`), so one patch
    # covers both. The demo echoes its full input, exposing any divergence.
    monkeypatch.setattr(routes_chat, "context_parts", lambda cwd=None: list(fixed))

    async def _endpoint_reply() -> str:
        async with _client(_stub()) as c:
            r = await c.post("/api/chat/complete", json={"content": "ping"})
        assert r.status_code == 200
        return r.json()["content"]

    endpoint_content = asyncio.run(_endpoint_reply())

    cli_result = CliRunner().invoke(cli_mod.main, ["chat", "--demo", "--json", "ping"])
    assert cli_result.exit_code == 0, cli_result.output
    cli_content = json.loads(cli_result.output)["content"]

    # Same shared complete_turn + same demo agent + same injected context => same reply.
    assert cli_content == endpoint_content
    # And the context really is injected (guards against a both-empty false pass).
    assert "[Working directory: /ws]" in cli_content
    assert "ping" in cli_content


def test_cli_no_context_flag_restores_the_terse_echo():
    """gh #106: `--no-context` opts back out of the browser-identical context injection
    for a clean scriptable echo — so the CLI's default (context injected) and its escape
    hatch (context withheld) are demonstrably different, and the flag exists at all
    (before the fix it did not, and the default omitted the context)."""
    import json

    from click.testing import CliRunner

    from langstage import cli as cli_mod

    default = CliRunner().invoke(cli_mod.main, ["chat", "--demo", "--json", "ping"])
    raw = CliRunner().invoke(
        cli_mod.main, ["chat", "--demo", "--no-context", "--json", "ping"]
    )
    assert default.exit_code == 0, default.output
    assert raw.exit_code == 0, raw.output

    default_content = json.loads(default.output)["content"]
    raw_content = json.loads(raw.output)["content"]

    # Default injects the real per-message context; --no-context strips it.
    assert "[Working directory:" in default_content
    assert "[Current time:" in default_content
    assert "[Working directory:" not in raw_content
    assert "[Current time:" not in raw_content
    assert default_content != raw_content
