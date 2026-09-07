# Architecture

What this repository is, and how its parts fit together. This document states the current design.
It is not the intent — a `PURPOSE.md` states what a subsystem is for, and this says how that is
achieved. It is not a deliberation: why a design was chosen, and what was rejected, belongs in an
ADR, and nothing here links to one (see [rules/adr-lifecycle.md](./rules/adr-lifecycle.md)).

Working conventions — how to set up, lint, test, commit — are in [AGENTS.md](./AGENTS.md), not here.

## What this repository is

A Claude Code marketplace plugin collection. `.claude-plugin/marketplace.json` is the authoritative
roster; read it rather than any list restated elsewhere. Entries are local directories under
`plugins/`, plus external plugins pinned from other repositories.

A plugin composes from parts the harness loads independently:

| part | is | loaded by |
|---|---|---|
| skill | instructions a harness loads on demand, as `SKILL.md` with optional `references/` and `scripts/` | the harness's skill mechanism |
| agent | a subagent definition with its own tool surface and system prompt | the harness's subagent mechanism |
| command | a user-invocable entry point, usually delegating to a skill | the harness's slash-command mechanism |
| hook | code run at a lifecycle point, shipped by a plugin where the harness allows it | the harness's hook mechanism |
| MCP server | a tool surface exposed over the Model Context Protocol | the harness's MCP client |

[docs/terminology-glossary.md](./docs/terminology-glossary.md) defines these terms precisely.

## Cross-harness design

Plugin content targets several agent harnesses, not one. Claude Code, Codex, Hermes, OpenCode and
Cursor are first-class; pi, Kimi Code and Kilo Code are best-effort. They differ in what they can
express — whether a hook carries the shell command text, whether hooks fire inside a subagent,
whether a subagent gets a worktree, whether a plugin may ship a hook at all.

Those differences are measured, not assumed. The capability matrix and its per-harness measurement
files live in
[plugins/development-harness/CLAIMS-REGISTER.md](./plugins/development-harness/CLAIMS-REGISTER.md)
and `plugins/development-harness/docs/work-ledger/measurements/`, each entry carrying its source
and the date it was read. A design that depends on a capability must find it established there for
every harness it claims to support, and an unestablished capability is a different finding from a
measured-absent one.

The consequence for content: a skill handoff is written in prose that any harness can act on, and
harness-specific invocation syntax is avoided in plugin content.

## Language and runtime boundaries

Python is the implementation language for scripts and tools, chosen so behaviour is identical
across platforms — see [rules/language-conventions.md](./rules/language-conventions.md). Shell is
reserved for thin CI wrappers. JavaScript and TypeScript implement hooks and some MCP scripts.

Standalone scripts carry PEP 723 inline metadata and run under `uv run`, so a script declares its
own dependencies rather than relying on an ambient environment. A script may span several modules;
size, not file count, is the constraint.

## Subsystem architecture

Each subsystem states its own design. Step through them from here.

| subsystem | document | covers |
|---|---|---|
| Development harness (`dh`) | [plugins/development-harness/ARCHITECTURE.md](./plugins/development-harness/ARCHITECTURE.md) | the automation boundary, the logical work model, the frontend and backend contracts, and the current boundary between them |
| Backlog storage and providers | [plugins/development-harness/backlog_core/ARCHITECTURE.md](./plugins/development-harness/backlog_core/ARCHITECTURE.md) | per-collaborator responsibilities, GitHub writable records, offline and replay policy |
| Plugin authoring | [plugins/plugin-creator/references/ARCHITECTURE.md](./plugins/plugin-creator/references/ARCHITECTURE.md) | how plugins, skills and agents are structured and validated |

## Where state lives

This checkout's backlog backend is GitHub Issues, configured in `.dh/config.yaml`. Beads is a
supported backend family in the abstraction but is not used here, so `bd init` and `bd setup` are
never run at the repository root.

Storage beyond that is a subsystem concern: the harness addresses work logically and the configured
backend owns persistence, which the dh architecture document describes.

## How tests relate to this document

System and end-to-end tests are written against the architecture, not against the code. A test
written against the implementation ratifies whatever the implementation does and drifts with it; it
cannot report that the design was wrong, because it was written after the design was chosen. Where
an architectural rule can be stated as data, state it as data and let the test assert against that
— `plugins/development-harness/dh_core/ledger_spec.py` and its closure tests are the pattern.
