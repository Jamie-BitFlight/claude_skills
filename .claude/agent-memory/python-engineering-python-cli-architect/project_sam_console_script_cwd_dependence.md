---
name: project-sam-console-script-cwd-dependence
description: uv run sam only resolves inside plugins/development-harness cwd; subprocess fallbacks in sam_schema must target cli.py by absolute path instead
metadata:
  type: project
---

`sam` is a `[project.scripts]` entry declared only in
`plugins/development-harness/pyproject.toml` — the repo root `pyproject.toml` has no such entry
and there is no uv workspace tying them together (see AGENTS.md "No uv workspace").

Consequence verified empirically (2026-08-06): `uv run sam --help` from the repo root fails with
`error: Failed to spawn: sam ... No such file or directory`. It only resolves when cwd is
`plugins/development-harness/` (that subproject's own venv/pyproject). Since `sam_schema/cli.py`
is documented and invoked elsewhere in the repo as `uv run
plugins/development-harness/sam_schema/cli.py ...` from the repo root (e.g.
`skills/implementation-manager/SKILL.md`), any code inside `sam_schema/` that shells out to "the
sam CLI" via `uv run sam ...` is cwd-fragile and will break for the common invocation pattern.

**Fix pattern**: build the subprocess command from `Path(__file__).resolve().parent / "cli.py"`
(an absolute path to the self-resolving PEP 723 script) instead of relying on the installed
console script name. Confirmed working via direct `uv run <abs-path>/cli.py ...` probes from both
the repo root and an unrelated cwd (`/tmp`).

Found while fixing `plugins/development-harness/sam_schema/backlog.py`'s `_sync_fallback` — a
Codex PR review comment's suggested fix (`uv run backlog sync` → `uv run sam backlog sync`)
correctly identified the missing `backlog` script but its own replacement was still cwd-dependent
and would have failed identically in the CLI's actual real-world invocation context. Always
falsification-test a review-suggested fix against the real invocation context before trusting it.

See also [[project_auto_sync_manifests]] for other PEP 723 self-resolving script gotchas in this
plugin.
