# Improvement Proposals: Worktrunk

**Research entry**: ./research/developer-tools/worktrunk.md
**Generated**: 2026-03-28
**Patterns assessed**: 6
**Backlog items created**: 0 (backlog MCP tools unavailable in this session)
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: CI status integration for agent-facing branch context

**Source pattern**: "CI/CD status in agent context -- The `wt list --full` command with CI status integration could inform agent decision-making (e.g., agents prioritizing branches with failing CI)" (Integration Opportunities section)
**Local system**: plugins/development-harness/skills/implementation-manager/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the `gh` CLI is available to agents and could be used ad-hoc via Bash calls; structured integration would require verifying that agents actually encounter scenarios where CI status changes their behavior. No evidence of agents being blocked by lack of CI status today.

### Current state

The implementation-manager SKILL.md exposes `sam_status`, `sam_ready`, and `sam_list` commands for task/plan status. None of these include CI status for the branch associated with a task or plan. The work-milestone SKILL.md creates worktrees and spawns sessions but does not query or pass CI status to spawned agents. A Grep for "CI status", "ci_status", "github.actions", "workflow.*status" across both skills returned zero matches.

### Target state

The `sam_status` output includes a `ci_status` field per plan (or per branch if multiple branches exist) showing the latest GitHub Actions workflow run status (success/failure/pending). The work-milestone wave dispatch loop queries CI status on the integration branch before spawning the next wave -- if CI is failing, the orchestrator investigates before spawning more work.

### Measurable signal

`sam_status(plan="P1")` output JSON includes a `ci_status` field with value from {success, failure, pending, unknown}. The work-milestone SKILL.md includes a gate between waves that checks integration branch CI status.

---

## Improvement 2: Configurable post-worktree-creation hooks

**Source pattern**: "Project hooks (post-start, post-merge) run commands automatically on create, merge, etc" and "Post-start commands -- Install dependencies, start dev servers, copy build caches between worktrees" (Key Features / Workflow Automation section)
**Local system**: plugins/development-harness/skills/work-milestone/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the kage-bunshin spawn script already handles `.venv`/`node_modules` symlinking (line 118 of SKILL.md). The gap is that these are hard-coded in the spawn script rather than user-configurable via a project config file. Would need to read the spawn script fully to confirm whether it already supports configuration.

### Current state

The kage-bunshin spawn script (`plugins/development-harness/skills/kage-bunshin/scripts/spawn.py`) handles worktree creation and `.venv`/`node_modules` symlinking as part of its internal logic. There is no project-level configuration file (analogous to Worktrunk's `wt.toml` `[hooks]` section) where users can define arbitrary post-start commands (e.g., `npm install`, `pip install -e .`, custom build cache copy operations). The setup steps are embedded in the spawn script code.

### Target state

A configuration file (e.g., `.dh/worktree-hooks.toml` or a section in an existing DH config) allows users to define `post-start` commands that run automatically after worktree creation. The spawn script reads this config and executes the listed commands in the new worktree before launching the agent session.

### Measurable signal

A config file exists with a `[hooks]` or `[worktree.hooks]` section containing `post-start` commands. Running the spawn script with `--worktree` creates the worktree and executes the configured commands before returning.

---

## Improvement 3: Template variable expansion for worktree paths

**Source pattern**: "Template-based configuration -- Worktrunk's template variable system (`hash_port`, `{branch}`, `{repo}` in paths and hooks) provides a clean pattern for enabling user customization without hard-coded behavior" (Patterns Worth Adopting section)
**Local system**: plugins/development-harness/skills/work-milestone/SKILL.md
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred -- confidence medium: the spawn script constructs worktree paths internally. A Grep for "template.*variable" in the development-harness plugin found only a test checking `{files}` template variable documentation -- suggesting template variables exist in dispatch prompts but not in worktree path construction. Would need full spawn.py read to confirm path construction logic.

### Current state

The work-milestone SKILL.md shows worktree paths constructed as `worktrees/{slug}` (line 44 of the Mermaid flowchart). A Grep for "template.*variable|template.*expansion|hash_port|configurable.*path" across the development-harness plugin found only one match: a test for `{files}` template variable in dispatch prompts. Worktree path patterns are not user-configurable.

### Target state

Worktree paths support template variables (e.g., `{repo}`, `{branch}`, `{issue}`) configurable via a DH config file. Users can customize where worktrees are created relative to the repository (e.g., `../{repo}.{branch}` to place worktrees as siblings, or `worktrees/{issue}-{slug}` for issue-prefixed naming).

### Measurable signal

The spawn script accepts a `--worktree-path-template` flag or reads a template pattern from DH config. Worktree paths in the filesystem match the configured template pattern with variables expanded.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| CI status integration for agent-facing branch context | medium | Need evidence that agents are blocked or make suboptimal decisions due to missing CI status. The `gh` CLI is already available as an ad-hoc workaround. |
| Configurable post-worktree-creation hooks | medium | The spawn script already handles key setup tasks (symlinks). Full spawn.py read needed to confirm whether it supports any configuration mechanism already. |
| Template variable expansion for worktree paths | medium | The current hard-coded path scheme works. Template variables add flexibility but no current failure mode is addressed. Full spawn.py read needed to confirm path construction. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Interactive picker with live preview | The local system is agent-facing, not human-facing. Agents do not use interactive pickers -- they receive structured data via MCP tools and CLI output. Pattern domain mismatch. |
| Claude Code native support (Worktrunk `-x` flag) | Already covered. The local system has `/work-milestone` which creates worktrees and spawns full orchestrator sessions (kage-bunshin) per work item. This is equivalent to or more capable than `wt switch -x claude`. |
| Shell execution abstraction (unified `Cmd` wrapper) | Architecture incompatibility. The local system delegates command execution to Claude Code's `Bash` tool, which already provides logging, timeout, and error capture. Wrapping Bash calls in an additional abstraction layer would add indirection without observable benefit in an AI-agent context (unlike a CLI binary where all commands go through the same process). |
