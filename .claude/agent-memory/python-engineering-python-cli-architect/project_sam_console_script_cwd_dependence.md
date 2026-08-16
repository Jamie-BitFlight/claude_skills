---
name: project-sam-console-script-cwd-dependence
description: there is no "sam" binary/console-script anymore — it was deliberately removed (2026-08-06); the sam CLI is always invoked by absolute path to sam_schema/cli.py
metadata:
  type: project
---

`sam` was briefly a `[project.scripts]` entry declared only in
`plugins/development-harness/pyproject.toml` — the repo root `pyproject.toml` never had such an
entry and there is no uv workspace tying them together (see AGENTS.md "No uv workspace"). It no
longer exists in any form: commit `849bb495` ("chore(dh)!: remove unsanctioned per-plugin project
files", 2026-08-06) deleted `plugins/development-harness/pyproject.toml` outright, and the same-day
commit `79ce9ec3` ("test(dh): assert the CLI runs from a foreign CWD, drop console-script pin")
updated the test harness's own `run_cli()` helper from `["uv", "run", "sam", *args]` to
`["uv", "run", str(_CLI_PATH), *args]`. This was a deliberate removal — the `sam` name was
confusing agents into treating a plain PEP 723 script file as an installed binary entry point.

Do not write or say `uv run sam ...`, `sam plan list`, `sam backlog sync`, etc. as if `sam` is a
runnable command — it is not, in any cwd, on this or any later commit. The correct invocation is
always by absolute path to the self-resolving PEP 723 script: `uv run
plugins/development-harness/sam_schema/cli.py ...` (or the equivalent absolute path built from
`Path(__file__).resolve().parent / "cli.py"` inside `sam_schema/` itself), as documented and
invoked elsewhere in the repo (e.g. `skills/implementation-manager/SKILL.md`,
`skills/work-backlog-item/SKILL.md`'s `<sam_cli>` block). "sam plan list" as shorthand for "the
`plan list` subcommand of the sam CLI" is fine in prose describing behavior, but never as a literal
command example — always show the real invocation.

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
