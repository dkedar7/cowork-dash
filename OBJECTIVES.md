# Objectives & scope — langstage

*What this repo is for, who it serves, and what it deliberately is **not** — the yardstick
for deciding whether a proposed change or filed issue belongs here. When triaging an issue,
start here.*

## Objective

A local, single-workspace **web app** — "AI-power your workspace with deep agents." A FastAPI
backend + React SPA where an agent operates *on a workspace*: file browser, canvas, task
board, scheduler/cron, and chat, driven through langstage-core's `SessionAdapter`.

## Who it's for

A developer running an agent against their own working directory, on their own machine.

## In scope

- Workspace-aware behavior — the `_enter_workspace()` chdir contract, so a bring-your-own
  agent's relative file ops land in the workspace the UI shows.
- The SPA and `/api/*`; scheduling/cron; the file, canvas, and task-board surfaces.
- The entry points: `run` (server), `chat` (headless readiness gate), `check`, `init`.
- Honest readiness (a preflight that reflects what the running server will actually do).

## Out of scope (anti-scope)

- Multi-tenant / SaaS / hosted / cloud-deploy / external-auth features. This is a **local,
  single-user** tool — local by default (see the CORS posture: loopback-only unless explicitly
  opted in). Hosting/scaling asks → decline.
- Terminal-CLI-parity features — those belong in **langstage-cli**.
- A headless SDK use case — that belongs in **langstage-core**.
- Becoming a general-purpose IDE or code editor.

## How this fits the family

langstage is the **web surface** of the family. It is a thin consumer of langstage-core (the
wire, config, task engine) — logic it would share with another surface belongs in core, not
here. The terminal, JupyterLab, and VS Code surfaces are separate repos.

## Using this to triage

Before acting on an issue or PR: does it serve the objective above? Is it in scope or
anti-scope? Weigh its value — **security > correctness > advertised-≠-honored > DX/docs >
polish > net-new feature** — against the cost of a manual release. Then **fix, defer, or
decline with a reason.** Not every filed issue is worth acting on.
