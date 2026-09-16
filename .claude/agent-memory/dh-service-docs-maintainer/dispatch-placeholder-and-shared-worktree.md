# Dispatch-line placeholder convention and shared-worktree gotchas

## Attempt-number placeholder: use `{A}`

The dh dispatch-line contract (`P{N}/T{M}, attempt {A}`) is restated independently in at least
four places: `agents/task-worker.md`, `skills/implement-feature/SKILL.md`,
`skills/implementation-manager/SKILL.md`, `skills/complete-implementation/references/qg-dispatch-step.md`,
and `skills/subagent-contract` (not edited 2026-09, out of scope that pass). As of 2026-09 these
had drifted to four different spellings for the attempt number: `{A}`, `{attempt}`, `{n}`, bare
`N`. Canonical going forward: `{A}` for attempt, `{N}` for plan number, `{M}` for task number.
Files that use named variables instead (`implement-feature/SKILL.md`'s `{plan_ref}`/`{task_id}`)
keep those names — only the attempt token gets normalized to `{A}`, not the whole placeholder
style. No single file owns this contract as source of truth; a pass touching one occurrence should
grep the other three-plus sites for the same drift.

## `close/start.md` covers both `close` and `resolve` routes — pick the right one

`skills/work-backlog-item/references/workflows/close/start.md` is titled "Close / Resolve
Procedure (Phase 5)" and handles two distinct `<route/>` values under one file, despite living in
a directory named `close/`:

- `close` (Step 5.3): dismiss without completion — reason required, never calls `backlog_resolve`.
- `resolve` (Step 5.4-11): mark DONE with evidence — calls `backlog_resolve`, has the
  `Open-PR search failed` / `Open PRs reference issue` recovery branches with the
  `AskUserQuestion` + `force=True` retry pattern.

Do not write "`/dh:work-backlog-item close`" when the intended action is resolving/completing an
item — that invokes the dismissal route. Use "`/dh:work-backlog-item resolve {item_ref}`".

## Error-prefix contract for open-PR checks (`backlog_core/operations.py`)

`_search_open_prs` (line ~229) raises `BacklogError("Open-PR search failed for issue {ref}: {exc}.
Use force=True to skip the open-PR check.")` when the GitHub search itself fails (bad token, or a
proxy/firewall blocking the request) — distinct from `resolve_item`/`close_item` raising
`"Open PRs reference issue {ref}. Use force=True to..."` when the search succeeds and finds
matches. Never describe either as "offline" or "unreachable" per this repo's terminology rule —
name the cause (token rejected, or network path blocked).

## `agent-marketplace-versioner` prek hook can look like your own damage — check before reverting

This worktree is routinely shared with other concurrently-running agents (see task briefs that say
"Other agents are editing other files"). Running `uv run prek run --files <your files>` can report
`Synchronize staged agent marketplace versions ... Failed - files were modified by this hook`, and
`git status` right after can show unrelated files dirty that were clean at session start. Before
assuming prek did it (and reverting), diff those files: a real version-sync hook only touches
`version:`-type frontmatter fields. If the diff is substantive prose in files you never opened,
it's very likely a concurrent agent's edit landing mid-session, not a `prek` side effect — leave it
alone (reverting a peer agent's legitimate work is worse than a spurious hook failure), and confirm
your own target files are clean via `git status --short <your files>` before writing your report.
