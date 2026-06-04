---
source_type: codebase-analysis
source_path: plugins/development-harness/skills/ and plugins/development-harness/hooks/
summarized_at: 2026-05-14
method: full-read
word_count_source: 43 skills × SKILL.md + 7 hook files + 1 hook Python script
word_count_summary: ~4200
confidence: high — all SKILL.md files read via targeted grep; all hook files read in full
---

# DH Plugin: Skills and Hooks Beads Integration Analysis

## Summary

Every DH skill that participates in the SAM planning/execution lifecycle references GitHub Issue numbers as the primary identifier key passed to `artifact_*`, `backlog_*`, `sam_*`, and `dispatch_*` MCP tools. The identifier (`issue_number`, `selector="#N"`) is an integer GitHub issue number in all cases — there is no abstraction layer between skills and the GitHub identity system.

Zero skills contain existing awareness of `BACKLOG_BACKEND`, `beads`, or the `bd` CLI. No skill conditionally routes based on backend type.

The task_status_hook.py PostToolUse/SubagentStop Python hook calls SAM MCP tools directly (via fastmcp CLI subprocess). It reads `parent_issue_number` from the active-task context file but does not pass it to the backlog server — that field is stored for potential future use. The hook is effectively backend-agnostic for task state writes; it has no GitHub-specific logic itself, though the data it reads (active-task JSON) may contain a GitHub issue number written by `/start-task`.

The five Node.js hooks (kage-bunshin lifecycle) have no backlog, SAM, artifact, or dispatch MCP calls — they manage tmux session state only and are fully backend-agnostic.

## What Was Found

### Skills with `backlog_*` references

| Skill | Lines | Tool calls found |
|---|---|---|
| add-new-feature | 34, 72, 99, 159, 323, 376, 437, 463 | `backlog_view`, `backlog_update`, `artifact_list`, `artifact_read`, `artifact_register` |
| backlog | entire file | All `backlog_*` tools (reference guide) |
| complete-implementation | 56, 87, 224, 351, 365, 372, 374, 668, 680, 691, 703, 710 | `backlog_view`, `backlog_update`, `backlog_groom`, `backlog_list`, `backlog_add`, `artifact_list`, `artifact_read` |
| context-integration | 76, 90, 95 | `artifact_register`, `artifact_read` |
| create-artifact | entire file | `artifact_register`, `artifact_read` |
| dispatch | 37, 95 | `backlog_view`, `artifact_register` |
| final-verification | 47, 84, 105, 106, 107 | `artifact_read`, `sam_task` |
| forensic-review | 51, 82, 99, 108, 111 | `sam_task`, `artifact_register`, `artifact_read` |
| gate-push | 34, 36 | `backlog_list` |
| groom-backlog-item | (implicit via backlog tool calls) | `backlog_groom`, `backlog_update` |
| groom-milestone | 36, 45, 86–99 | `backlog_list_issues`, `backlog_view`, `backlog_groom`, `backlog_update`, `dispatch_create_plan`, `dispatch_wave_start`, `dispatch_wave_status` |
| implement-feature | 54, 62, 65, 151, 164, 200, 238, 284, 288, 294, 301 | `backlog_get_ready_sam_tasks`, `sam_plan`, `sam_task`, `backlog_groom`, `artifact_read`, `artifact_register` |
| interop | 92, 136, 139 | `backlog_add`, `sam_plan` |
| planning | 82, 89 | `artifact_read`, `artifact_register` |
| rt-ica | 69, 78 | `backlog_view`, `backlog_groom` |
| start-task | 36, 46, 62, 65, 68, 69, 74, 90, 94, 112 | `sam_task`, `artifact_list`, `artifact_read`, `sam_active_task` |
| task-decomposition | 114, 126, 132, 148, 158, 164 | `artifact_read`, `sam_plan` |
| work-backlog-item | 45, 52, 97, 114, 128, 156 | `backlog_view`, `backlog_update`, `backlog_list` (via MCP tools generically) |
| work-milestone | 28, 37, 116, 118, 174–176, 202, 265–281 | `backlog_list_issues`, `backlog_view`, `artifact_list`, `artifact_read`, `sam_plan`, `dispatch_read`, `dispatch_wave_start`, `dispatch_spawn`, `dispatch_wave_status`, `dispatch_item_status` |
| code-review-architecture | 256, 459, 475, 485 | `artifact_register` (output registration only) |
| execution | 47, 103, 110 | `sam_task`, `sam_plan` |

### Skills referencing GitHub issue numbers as identifiers

All skills that call `artifact_*` or `backlog_*` tools use `issue_number` (integer) or `selector="#N"` as the primary key. These are GitHub issue numbers by definition. The following skills have embedded GitHub-specific logic in their workflows:

- **add-new-feature**: The entire phase structure branches on `"Contains 'GitHub Issue: #N'"` pattern. Artifact discovery, backlog_view, and backlog_update all key on the extracted GitHub issue integer. The `{issue}` variable throughout is explicitly a GitHub issue number.
- **complete-implementation**: Input resolution logic explicitly handles `#N`, bare integer, and GitHub URL formats. Calls `backlog_view(selector="#{issue_number}")` where the integer is a GitHub issue number. Calls `backlog_update(..., verified=True)` to write back to the GitHub issue.
- **work-backlog-item**: Frontmatter description says "GitHub Issue, Project, and Milestone tracking." Accepts `#N`, bare number, GitHub issue URL as input. Documents `setup-github` mode. States "Primary source of truth is GitHub Issues." This skill has the deepest GitHub entanglement.
- **groom-milestone**: Frontmatter says "Grooms a GitHub milestone." Step 1 calls `backlog_list_issues(milestone=N)` where N is a GitHub milestone number.
- **work-milestone**: Creates integration branch at `milestone/{N}-{slug}`. Calls `github_branches create/merge/delete`. References GitHub milestones as the organizing primitive.
- **gate-push**: Contains a shell script that parses `git remote get-url origin` to extract a GitHub repo slug from the GitHub URL format.
- **interop**: `backlog_add` is called when creating a new item. The returned item from beads would have a different ID format.

### Skills with `dispatch_*` references

- **groom-milestone**: `dispatch_create_plan`, `dispatch_wave_start`, `dispatch_wave_status`
- **work-milestone**: `dispatch_read`, `dispatch_wave_start`, `dispatch_spawn`, `dispatch_wave_status`, `dispatch_item_status`
- **dispatch**: References `dispatch_spawn` semantics (spawning workers)

### Existing `bd` CLI awareness

None found. Zero SKILL.md files reference `bd`, `beads`, or `BACKLOG_BACKEND`.

---

## Skill Integration Analysis

### add-new-feature

- **Classification**: `BEHAVIOUR_CHANGE`
- **MCP tools**: `artifact_list`, `artifact_read`, `artifact_register`, `backlog_view`, `backlog_update` — 5 tool families, ~15 call sites
- **GitHub-specific**: Yes — entire phase entry point branches on `"GitHub Issue: #N"` pattern detection. The `{issue}` variable is a GitHub issue integer passed to every MCP call throughout all 5 phases.
- **Required change**: The `issue_number` parameter passed to `artifact_*` tools must work with the beads item ID format. If beads uses non-integer IDs, the integer-only parameter signature of `artifact_register(issue_number=N)` breaks. The phase entry conditional (`"Contains 'GitHub Issue: #N'"`) must recognize beads item references. `backlog_view(selector="#{issue}")` must work with beads selectors.

### analyze-test-failures

- **Classification**: `NO_CHANGE`
- **MCP tools**: None
- **GitHub-specific**: No
- **Required change**: None

### backlog

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: All `backlog_*` tools — reference guide for operators (13 tool descriptions)
- **GitHub-specific**: Notes GitHub Issues as source of truth; CLI table lists GitHub-named operations
- **Required change**: When `BACKLOG_BACKEND=beads`, the "source of truth" statement no longer describes GitHub Issues. The tool reference section itself is backend-agnostic (tools are MCP abstractions). Add a note: "When `BACKLOG_BACKEND=beads`, the source of truth is the beads service. `backlog_list_issues(milestone=N)` maps to beads milestone queries. Item identifiers returned by `backlog_list` are beads item IDs, not GitHub issue numbers."

### clear-cove-task-design

- **Classification**: `NO_CHANGE`
- **MCP tools**: None
- **GitHub-specific**: No
- **Required change**: None

### code-review-architecture

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `artifact_register` — output registration only (3 call sites)
- **GitHub-specific**: No — `issue_number` is parameter but no GitHub URL logic
- **Required change**: Ensure `issue_number` parameter accepted for `artifact_register` is a beads item ID when beads backend is active. No workflow change needed; the registration calls are generic.

### code-review-claude-skills, code-review-cli, code-review-llm, code-review-nodejs, code-review-python, code-review-typescript, code-review-web

- **Classification**: `NO_CHANGE`
- **MCP tools**: None
- **GitHub-specific**: No
- **Required change**: None (7 skills)

### complete-implementation

- **Classification**: `BEHAVIOUR_CHANGE`
- **MCP tools**: `backlog_view`, `backlog_update`, `backlog_groom`, `backlog_list`, `backlog_add`, `artifact_list`, `artifact_read`, `sam_plan`, `sam_task`, `sam_create`, `sam_state` — 11 tool families, ~20 call sites
- **GitHub-specific**: Yes — input resolution explicitly handles `#N`, bare integer, GitHub URL. Error messages contain `#{issue_number}` formatted as GitHub-style hash references. `backlog_update(..., verified=True)` writes a GitHub-specific "verified" field. The "GitHub token, repo access" error message in the retry block is GitHub-specific.
- **Required change**: Input resolver must accept beads item IDs as well as GitHub-style `#N`. Error messages should not mention GitHub token when beads is the backend. The `verified=True` field semantics need beads equivalent. The backlog-item lookup section (Strategy 1: `backlog_list(title=...)`, Strategy 2: `backlog_list(topic=...)`) is tool-level and would work if the MCP tools are backend-agnostic.

### comprehensive-test-review

- **Classification**: `NO_CHANGE`
- **MCP tools**: None
- **GitHub-specific**: No
- **Required change**: None

### context-integration

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `artifact_register`, `artifact_read` — 2 call sites
- **GitHub-specific**: No — uses `{issue}` parameter but no GitHub URL logic
- **Required change**: Verify `issue_number` parameter works with beads item IDs. No workflow change.

### create-artifact

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `artifact_register`, `artifact_read` — entire skill describes these two tools
- **GitHub-specific**: No explicit GitHub logic. The parameter is `issue_number` (int) — if beads uses non-integer IDs the parameter type breaks.
- **Required change**: Document that when `BACKLOG_BACKEND=beads`, `issue_number` accepts the beads item ID. If beads IDs are non-integer, the skill's type annotation (`int`) must be updated to reflect the accepted type. The table of artifact types is backend-agnostic.

### create-backlog-item

- **Classification**: `NO_CHANGE` (skill body is thin — no direct MCP tool calls documented in SKILL.md beyond the triggering of `backlog_add` implicitly)
- **MCP tools**: Calls `backlog_add` (via the workflow it invokes)
- **GitHub-specific**: No inline GitHub logic in the skill file itself
- **Required change**: None at skill level; changes needed in the backlog MCP tool implementation

### development-harness

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: None called directly — routing/orientation skill
- **GitHub-specific**: No direct GitHub calls
- **Required change**: Add a note to the Backend Providers section: when `BACKLOG_BACKEND=beads`, item identifiers are beads IDs not GitHub issue numbers. Reference existing `backend-providers.md` which already has beads information.

### dh-meta-docs

- **Classification**: `NO_CHANGE`
- **MCP tools**: None
- **GitHub-specific**: No
- **Required change**: None

### discovery

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `backlog_view`, `artifact_register` — 2 call sites
- **GitHub-specific**: No explicit GitHub logic
- **Required change**: None at workflow level; ensure `issue_number` parameter works with beads IDs.

### dispatch

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `backlog_view`, `artifact_register`, `sam_task`, `sam_plan` — 4 tool families
- **GitHub-specific**: No explicit GitHub URL or issue-number-format logic. The `backlog_view` call uses an issue number that originates upstream.
- **Required change**: The "Fetch-once rule" for `backlog_view` is backend-agnostic. No structural change needed. Add note: when beads is backend, the issue key used in fetch-once is a beads item ID.

### execution

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `sam_task`, `sam_plan` — 2 call sites
- **GitHub-specific**: No
- **Required change**: None — SAM tools are already backend-agnostic in this skill's usage.

### final-verification

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `artifact_read`, `sam_task` — 3 call sites
- **GitHub-specific**: No explicit GitHub logic
- **Required change**: Verify `issue_number` parameter works with beads IDs passed by calling context.

### forensic-review

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `sam_task`, `artifact_register`, `artifact_read` — 3 call sites
- **GitHub-specific**: No
- **Required change**: The `issue_number` used for `artifact_register` must be supplied from the beads item ID when applicable.

### gate-push

- **Classification**: `BEHAVIOUR_CHANGE`
- **MCP tools**: `backlog_list` — 2 call sites
- **GitHub-specific**: Yes — contains a shell script that parses `git remote get-url origin` to extract a GitHub repo slug using a GitHub URL regex pattern (`github.com[:/]([^/]+/[^/.]+)`). This breaks when the remote is not GitHub.
- **Required change**: The GitHub-URL-to-repo-slug extraction must be replaced or conditioned on backend. With beads, the repo slug may not be derivable from the git remote URL. Either detect `BACKLOG_BACKEND=beads` and skip the GitHub URL parsing, or use a separate configuration source for the beads project identifier.

### generate-task

- **Classification**: `NO_CHANGE`
- **MCP tools**: None
- **GitHub-specific**: No
- **Required change**: None

### groom-backlog-item

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `backlog_groom`, `backlog_update` (implicit)
- **GitHub-specific**: Accepts `#N` as input argument (argument-hint). The `#N` pattern is GitHub issue notation.
- **Required change**: Accept beads item ID format as input in addition to GitHub `#N` syntax.

### groom-milestone

- **Classification**: `BEHAVIOUR_CHANGE`
- **MCP tools**: `backlog_list_issues`, `backlog_view`, `backlog_groom`, `backlog_update`, `dispatch_create_plan`, `dispatch_wave_start`, `dispatch_wave_status` — 7 tool families
- **GitHub-specific**: Yes — frontmatter explicitly says "Grooms a GitHub milestone." Step 1 uses `backlog_list_issues(milestone=N)` where N is a GitHub milestone number. The preconditions state "Milestone exists on GitHub with state=open." Milestone is a GitHub-specific organizing concept.
- **Required change**: When `BACKLOG_BACKEND=beads`, the concept of "milestone" maps to a beads grouping primitive (board, project, sprint — requires verification). The `backlog_list_issues(milestone=N)` call must map to the beads equivalent. Frontmatter description must be updated to remove the GitHub-specific language.

### implementation-manager

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `sam_plan`, `sam_task` — all SAM tools, 8 call sites
- **GitHub-specific**: No
- **Required change**: None — implementation-manager is SAM-only. SAM tools are backend-agnostic in this context.

### implement-feature

- **Classification**: `BEHAVIOUR_CHANGE`
- **MCP tools**: `backlog_get_ready_sam_tasks`, `sam_plan`, `sam_task`, `backlog_groom`, `artifact_read`, `artifact_register` — 6 tool families, ~15 call sites
- **GitHub-specific**: Yes — `backlog_groom` call appends concerns with `source as "Quality vigilance concern from #{issue}"`. The `artifact_register` call at bookend task setup passes `issue_number=N`. The parent story issue number is described as a GitHub issue number throughout.
- **Required change**: The `backlog_get_ready_sam_tasks(parent_issue_number=N)` call uses a GitHub issue integer as primary key. With beads, this must accept a beads item ID. Artifact registration at bookend tasks must use the beads item ID. The `from #{issue}` source attribution in groom calls is display text only — cosmetic update needed.

### interop

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `backlog_add`, `sam_plan` — 2 call sites
- **GitHub-specific**: No explicit GitHub URL logic at skill level, though `backlog_add` creates a GitHub issue by default
- **Required change**: `backlog_add` will route to beads when backend is configured. The returned item ID will be a beads ID, not a GitHub issue number. The SAM plan lookup after `backlog_add` must use the beads-returned ID.

### kage-bunshin

- **Classification**: `NO_CHANGE`
- **MCP tools**: None
- **GitHub-specific**: No
- **Required change**: None

### planner-rt-ica

- **Classification**: `NO_CHANGE`
- **MCP tools**: None
- **GitHub-specific**: No
- **Required change**: None

### planning

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `artifact_read`, `artifact_register` — 2 call sites
- **GitHub-specific**: No
- **Required change**: Verify `issue_number` works with beads IDs.

### rt-ica

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `backlog_view`, `backlog_groom` — 2 call sites with `selector="#N"`
- **GitHub-specific**: Yes — input format documented as `#N` (GitHub-style). The `selector="#N"` syntax in MCP calls uses GitHub issue number notation.
- **Required change**: When `BACKLOG_BACKEND=beads`, document that `#N` is interpreted as a beads item ID by the MCP layer. If the beads backend accepts `#N` selector format, no skill-level change is required. If not, update the input format documentation and example calls.

### setup-skill-discovery

- **Classification**: `NO_CHANGE`
- **MCP tools**: None
- **GitHub-specific**: No
- **Required change**: None

### start-task

- **Classification**: `BEHAVIOUR_CHANGE`
- **MCP tools**: `sam_task`, `artifact_list`, `artifact_read`, `sam_active_task` — 4 tool families, ~8 call sites
- **GitHub-specific**: Yes — source code comment in SKILL.md references `backlog_core.gh_client.update_task_status(repo, github_issue, "in-progress")` — a GitHub-specific internal API call that syncs task status to GitHub Issues. This is called by `start-task` to mark items in-progress on GitHub.
- **Required change**: The `backlog_core.gh_client.update_task_status()` call is GitHub-specific and will not function with beads. This must be routed through a backend-agnostic MCP tool (`backlog_update`) rather than the direct GitHub client. Additionally, `artifact_list` and `artifact_read` must accept beads item IDs.

### subagent-contract

- **Classification**: `NO_CHANGE`
- **MCP tools**: None
- **GitHub-specific**: No
- **Required change**: None

### task-decomposition

- **Classification**: `INSTRUCTION_UPDATE`
- **MCP tools**: `artifact_read`, `sam_plan` — 3 call sites
- **GitHub-specific**: No
- **Required change**: `sam_plan(action='create', issue={issue_number})` binds the SAM plan to an issue. With beads, this integer must be the beads item ID. If the SAM backend requires a GitHub issue integer, the SAM `github` backend must be used alongside the beads backlog backend — a mixed-backend scenario that may require SAM backend configuration changes.

### test-failure-mindset

- **Classification**: `NO_CHANGE`
- **MCP tools**: None
- **GitHub-specific**: No
- **Required change**: None

### validation-protocol

- **Classification**: `NO_CHANGE`
- **MCP tools**: None
- **GitHub-specific**: No
- **Required change**: None

### work-backlog-item

- **Classification**: `BEHAVIOUR_CHANGE`
- **MCP tools**: `backlog_view`, `backlog_update`, `backlog_list`, `backlog_close`, `backlog_resolve`, `backlog_groom` — 6 tool families
- **GitHub-specific**: Yes — deepest entanglement. Frontmatter description explicitly names GitHub Issue, Project, and Milestone tracking. Accepts `#N` GitHub issue numbers and GitHub issue URLs as input. States "Primary source of truth is GitHub Issues." Has `setup-github` mode to initialize GitHub labels, project, and milestone. The entire item lifecycle model (labels = status) is GitHub-specific.
- **Required change**: With beads, `#N` input resolves to a beads item ID. GitHub URLs are not valid beads item references. `setup-github` mode has no beads equivalent. The status model (GitHub labels) does not map to beads. This skill requires significant rework for beads: replace the `setup-github` path with a beads initialization path, update the source-of-truth statement, update the identifier format accepted as input.

### work-milestone

- **Classification**: `BEHAVIOUR_CHANGE`
- **MCP tools**: `backlog_list_issues`, `backlog_view`, `artifact_list`, `artifact_read`, `sam_plan`, `dispatch_read`, `dispatch_wave_start`, `dispatch_spawn`, `dispatch_wave_status`, `dispatch_item_status`, `github_branches` — 11 tool families
- **GitHub-specific**: Yes — uses `github_branches create/merge/delete` for branch management. Creates milestone branch at `milestone/{N}-{slug}`. References GitHub milestones as organizing primitive. Milestone number N is a GitHub milestone number.
- **Required change**: `github_branches create/merge/delete` calls must be replaced with standard git operations or a backend-agnostic branching tool. The milestone number N must map to a beads grouping ID. The integration branch naming convention uses `milestone/{N}` which embeds the GitHub milestone number.

---

## Hook Integration Analysis

### session-start-session-id.cjs

- **Trigger event**: SessionStart
- **Reads SAM context**: No
- **Calls MCP tools**: No — writes to `CLAUDE_ENV_FILE` and injects `additionalContext` into the conversation
- **GitHub-specific**: No
- **Required change**: None

### block-context-direct-writes.cjs

- **Trigger event**: PreToolUse (matcher: Bash)
- **Reads SAM context**: No — detects path patterns (`active-task-*.json`, `.claude/context/`, `.dh/projects/`) but does not read context file content
- **Calls MCP tools**: No
- **GitHub-specific**: No
- **Required change**: None — the path patterns it blocks (`active-task-*.json`) are SAM context files. These exist regardless of backlog backend. The block message references `sam_active_task MCP tool` which remains correct.

### task-completed-kage-bunshin-reminder.cjs

- **Trigger event**: TaskCompleted
- **Reads SAM context**: No — reads kage-bunshin registry at `~/.dh/projects/{slug}/kage-bunshin/registry-{session_id}.json`
- **Calls MCP tools**: No
- **GitHub-specific**: No
- **Required change**: None — reads only tmux session registry, not backlog or SAM data.

### stop-kage-bunshin-idle-check.cjs

- **Trigger event**: Stop
- **Reads SAM context**: No — reads kage-bunshin registry and notifications JSONL files under `~/.dh/projects/{slug}/kage-bunshin/`
- **Calls MCP tools**: No
- **GitHub-specific**: No
- **Required change**: None — manages tmux session state only.

### stop-kage-bunshin-child-notify.cjs

- **Trigger event**: Stop
- **Reads SAM context**: No — writes `stopped` event to notifications JSONL file
- **Calls MCP tools**: No
- **GitHub-specific**: No
- **Required change**: None — inter-session notification only.

### session-end-kage-bunshin-cleanup.cjs

- **Trigger event**: SessionEnd (matcher: logout|other|prompt_input_exit)
- **Reads SAM context**: No — reads registry to find tmux sessions to kill
- **Calls MCP tools**: No
- **GitHub-specific**: No
- **Required change**: None — kills orphaned tmux sessions only.

### session-end-kage-bunshin-child-notify.cjs

- **Trigger event**: SessionEnd (matcher: logout|other|prompt_input_exit)
- **Reads SAM context**: No — writes `session_end` event to notifications JSONL file
- **Calls MCP tools**: No
- **GitHub-specific**: No
- **Required change**: None — child session notification only.

### task_status_hook.py (PostToolUse + SubagentStop)

- **Trigger event**: PostToolUse (matcher: Write|Edit|Bash) and SubagentStop (matcher: ^task-worker$)
- **Reads SAM context**: Yes — reads `~/.dh/projects/{slug}/context/active-task-{session_id}.json` to discover which SAM task is active. Extracts `task_file_path`, `task_id`, and `parent_issue_number` from this file.
- **Calls MCP tools**: Yes — calls SAM MCP tools via fastmcp CLI subprocess:
  - `sam_active_task(action='get')` — retrieve active task context
  - `sam_active_task(action='clear')` — clear context after task completion
  - `sam_task(action='state', status='complete')` — mark task complete
  - `sam_task(action='update', set_fields={...})` — update task timestamps
- **GitHub-specific**: Partially — `parent_issue_number` is read from the active-task context file (an integer, implying a GitHub issue number). The field is extracted but the hook itself does not call any GitHub-specific API. The hook docstring says "All task state WRITES route through the SAM MCP server via fastmcp CLI subprocess, making the hook backend-agnostic (ADR-001)."
- **Required change**: The `parent_issue_number` field read from the active-task JSON was written by `/start-task` and carries a GitHub issue integer. If beads uses non-integer item IDs, the `int(data["parent_issue_number"])` cast at line 807 will fail. The field is not currently used to call any backlog MCP tool — it is stored but not forwarded — so the impact is limited to potential type error on parse. Defensive fix: widen the type to `str | int` and skip the cast.

---

## What Was NOT Found

- No skill contains `BACKLOG_BACKEND`, `beads`, or `bd` references — zero existing beads awareness across all 43 skills
- No skill has conditional routing that would naturally extend to a beads code path
- No skill documents a "backend-agnostic" variant of its MCP tool calls
- No existing migration guide or compatibility note for non-GitHub backends in any skill

## Uncertain

- Whether the `backlog_list_issues(milestone=N)` MCP tool exists in the beads backend and what identifier type `N` accepts — this determines whether `groom-milestone` and `work-milestone` require data model changes or only documentation updates
- Whether the beads backend exposes `dispatch_*` MCP tools — if not, the entire wave-based dispatch system (`groom-milestone`, `work-milestone`) requires a beads-specific dispatch implementation
- Whether `artifact_register(issue_number=N)` in the beads backend accepts a string beads item ID — this affects all artifact-producing skills
- Whether `selector="#N"` in `backlog_view`/`backlog_groom` calls is a convention that the beads backend MCP layer maps to beads item IDs, or whether a different selector format is required
- The `github_branches` MCP tool referenced in `work-milestone` — whether this is a GitHub-only tool or a generic git-branches tool that works with any remote

## Sources

- `/home/user/repos/claude_skills/plugins/development-harness/skills/` — all 43 SKILL.md files, read 2026-05-14
- `/home/user/repos/claude_skills/plugins/development-harness/hooks/hooks.json` — read 2026-05-14
- `/home/user/repos/claude_skills/plugins/development-harness/hooks/*.cjs` — all 6 Node.js hook files, read 2026-05-14
- `/home/user/repos/claude_skills/plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py` — lines 1–200 + grep scan, read 2026-05-14

---

## Summary Tables

### Skills Summary

| Skill | Classification | MCP Tools Count | GitHub-specific | Priority |
|---|---|---|---|---|
| add-new-feature | BEHAVIOUR_CHANGE | 5 families | Yes — branch on GitHub issue pattern | P1 |
| analyze-test-failures | NO_CHANGE | 0 | No | — |
| backlog | INSTRUCTION_UPDATE | 13 | Yes — source of truth statement | P2 |
| clear-cove-task-design | NO_CHANGE | 0 | No | — |
| code-review-architecture | INSTRUCTION_UPDATE | 1 | No | P3 |
| code-review-claude-skills | NO_CHANGE | 0 | No | — |
| code-review-cli | NO_CHANGE | 0 | No | — |
| code-review-llm | NO_CHANGE | 0 | No | — |
| code-review-nodejs | NO_CHANGE | 0 | No | — |
| code-review-python | NO_CHANGE | 0 | No | — |
| code-review-typescript | NO_CHANGE | 0 | No | — |
| code-review-web | NO_CHANGE | 0 | No | — |
| complete-implementation | BEHAVIOUR_CHANGE | 11 | Yes — input resolves GitHub URL/`#N`, error messages | P1 |
| comprehensive-test-review | NO_CHANGE | 0 | No | — |
| context-integration | INSTRUCTION_UPDATE | 2 | No | P3 |
| create-artifact | INSTRUCTION_UPDATE | 2 | No — but `issue_number` is int | P2 |
| create-backlog-item | NO_CHANGE | 0 | No | — |
| development-harness | INSTRUCTION_UPDATE | 0 | No | P3 |
| dh-meta-docs | NO_CHANGE | 0 | No | — |
| discovery | INSTRUCTION_UPDATE | 2 | No | P3 |
| dispatch | INSTRUCTION_UPDATE | 4 | No | P2 |
| execution | INSTRUCTION_UPDATE | 2 | No | P3 |
| final-verification | INSTRUCTION_UPDATE | 2 | No | P3 |
| forensic-review | INSTRUCTION_UPDATE | 3 | No | P3 |
| gate-push | BEHAVIOUR_CHANGE | 1 | Yes — GitHub URL parsing in shell script | P1 |
| generate-task | NO_CHANGE | 0 | No | — |
| groom-backlog-item | INSTRUCTION_UPDATE | 2 | Yes — `#N` input format | P2 |
| groom-milestone | BEHAVIOUR_CHANGE | 7 | Yes — GitHub milestone concept | P1 |
| implementation-manager | INSTRUCTION_UPDATE | 2 | No | P3 |
| implement-feature | BEHAVIOUR_CHANGE | 6 | Yes — `gh_client`, `#{issue}` source attribution | P1 |
| interop | INSTRUCTION_UPDATE | 2 | No | P2 |
| kage-bunshin | NO_CHANGE | 0 | No | — |
| planner-rt-ica | NO_CHANGE | 0 | No | — |
| planning | INSTRUCTION_UPDATE | 2 | No | P3 |
| rt-ica | INSTRUCTION_UPDATE | 2 | Yes — `#N` selector format | P2 |
| setup-skill-discovery | NO_CHANGE | 0 | No | — |
| start-task | BEHAVIOUR_CHANGE | 4 | Yes — `gh_client.update_task_status()` reference | P1 |
| subagent-contract | NO_CHANGE | 0 | No | — |
| task-decomposition | INSTRUCTION_UPDATE | 2 | No | P2 |
| test-failure-mindset | NO_CHANGE | 0 | No | — |
| validation-protocol | NO_CHANGE | 0 | No | — |
| work-backlog-item | BEHAVIOUR_CHANGE | 6 | Yes — deepest entanglement, `setup-github` mode | P1 |
| work-milestone | BEHAVIOUR_CHANGE | 11 | Yes — `github_branches`, milestone number | P1 |

### Hooks Summary

| Hook | Trigger | SAM Context | Change Needed |
|---|---|---|---|
| session-start-session-id.cjs | SessionStart | No | None |
| block-context-direct-writes.cjs | PreToolUse (Bash) | Detects path patterns only | None |
| task-completed-kage-bunshin-reminder.cjs | TaskCompleted | No | None |
| stop-kage-bunshin-idle-check.cjs | Stop | No | None |
| stop-kage-bunshin-child-notify.cjs | Stop | No | None |
| session-end-kage-bunshin-cleanup.cjs | SessionEnd | No | None |
| session-end-kage-bunshin-child-notify.cjs | SessionEnd | No | None |
| task_status_hook.py (PostToolUse) | PostToolUse (Write\|Edit\|Bash) | Yes — reads active-task JSON | Widen `parent_issue_number` type from `int` to `str \| int` |
| task_status_hook.py (SubagentStop) | SubagentStop (^task-worker$) | Yes — reads active-task JSON, calls SAM MCP | Widen `parent_issue_number` type from `int` to `str \| int` |
