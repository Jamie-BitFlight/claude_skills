# Backlog CLI → MCP Migration Map

Comprehensive inventory of every file referencing `backlog.py` CLI invocations, with the corresponding MCP tool that replaces each call.

Generated: 2026-03-01
**Migration completed: 2026-03-02 — Tiers 1-3 fully migrated (issue #329, 10 tasks)**

## MCP Server

- **Name**: `backlog`
- **Server file**: `.claude/skills/backlog/backlog_core/server.py`
- **Transport**: STDIO (`mcp.run()`)
- **Status**: Tests passing (382 tests), registered in `.mcp.json` (lines 25-28)

## CLI → MCP Tool Mapping

| CLI Subcommand | MCP Tool | operations.py Function | Notes |
|---|---|---|---|
| `backlog add` | `backlog_add` | `add_item()` | always creates a GitHub issue |
| `backlog list` | `backlog_list` | `list_items()` | `--format json` implicit (MCP returns dicts); status fields always included in every response |
| `backlog view` | `backlog_view` | `view_item()` | `--format json` implicit (MCP returns dicts) |
| `backlog sync` | `backlog_sync` | `sync_items()` | `--dry-run` → `dry_run: true` |
| `backlog close` | `backlog_close` | `close_item()` | `--plan`/`--checklist-pass` → `plan`/`checklist_pass`, `--cleanup` → `cleanup`. **Note**: CLI `close --reason` is semantically wrong — use `backlog_resolve` instead (ADR-8) |
| `backlog resolve` | `backlog_resolve` | `resolve_item()` | `--reason` → `reason`, `--cleanup` → `cleanup` |
| `backlog update` | `backlog_update` | `update_item()` | `--plan`/`--status`/`--create-issue`/`--section`/`--content` all map directly |
| `backlog groom` | `backlog_groom` | `groom_item()` | `--section`/`--content` or `--groomed-content` → `section`/`content`/`groomed_content` |
| `backlog normalize` | `backlog_normalize` | `normalize_items()` | `--dry-run` → `dry_run: true` |
| `backlog pull` | `backlog_pull` | `pull_items()` | `--dry-run` → `dry_run: true`, `--force` → `force: true` |

Universal CLI flag `-R {OWNER/REPO}` → MCP param `repo: "{OWNER/REPO}"` (defaults to `DEFAULT_REPO` constant, discovered dynamically from the git remote).

---

## Files Requiring Changes

### Tier 1 — Policy & Infrastructure (change first) — ✅ DONE

These files define the "single interface" rule and wire up the CLI. Updating them sets the migration direction.

#### 1. `.claude/CLAUDE.md` — Lines 214–220

**Current**: Backlog Operations section mandates `backlog.py` as single interface.

```bash
uv run .claude/skills/backlog/scripts/backlog.py add|list|sync|close|resolve|update ...
```

**Action**: Update policy to reference MCP server as primary interface, CLI as fallback for CI/GitHub Actions. Add `.mcp.json` registration instructions.

---

#### 2. `.github/workflows/backlog-sync.yml` — Line 36

**Current**:

```yaml
uv run .claude/skills/backlog/scripts/backlog.py sync -R {OWNER/REPO}
```

**Action**: Keep CLI here — GitHub Actions runs in a shell, not an MCP client. No change needed but document that CI remains CLI-based.

---

#### 3. `.claude/settings.json` — Lines 17–40

**Current**: SessionStart/Stop hooks reference `/work-backlog-item` and `/create-backlog-item` skills.

**Action**: No direct `backlog.py` invocations, but the hooks inject context that references CLI commands. Update `session-start-backlog.cjs` and `stop-backlog-reminder.cjs` to reference MCP tools instead.

---

#### 4. `.claude/hooks/session-start-backlog.cjs` — FILE DOES NOT EXIST

**Note**: This file does not exist in the repository. No action required.

---

#### 5. `.claude/hooks/stop-backlog-reminder.cjs`

**Current**: References `/work-backlog-item close`.

**Action**: Update to reference MCP tool names.

---

#### 6. `.cursor/rules/backlog-before-work.mdc` — Line 12

**Current**:

```text
backlog update "{title}" --plan "{path}"
```

**Action**: Update to MCP tool reference.

---

#### 7. `pyproject.toml` — Line 107

**Current**: Adds `.claude/skills/backlog` to `extra-paths` for type checking.

**Action**: Keep — still needed for `backlog_core` package resolution.

---

#### 8. `.pre-commit-config.yaml` — Line 99

**Current**: Excludes `.claude/backlog/` from markdownlint.

**Action**: Keep — auto-generated files still exist.

---

### Tier 2 — Skill Files (highest impact, most invocations) — ✅ DONE

These contain the actual `uv run backlog.py` commands that agents execute.

#### 9. `.claude/skills/backlog/SKILL.md` — Line 12

**Current**: Documents CLI invocation syntax and all subcommands.

**Invocations**: 1 (documentation example)

**Action**: Rewrite to document MCP tool interface as primary, CLI as fallback.

---

#### 10. `.claude/skills/work-backlog-item/SKILL.md` — 19 invocations

**Highest density of CLI calls in the repo.**

| Line | CLI Command | MCP Replacement |
|---|---|---|
| 97 | `backlog.py list --format json --with-status` | `backlog_list()` (status fields always included; no format param) |
| 155 | `backlog.py view "{$0}" --format json` | `backlog_view(selector="{$0}")` |
| 195 | `backlog.py close "{title}" --reason "..."` | `backlog_resolve(selector="{title}", reason="...")` (ADR-8: close+reason → resolve) |
| 233 | `backlog.py list --format json` | `backlog_list()` |
| 301 | `backlog.py close "{title}" --reason "..."` | `backlog_resolve(selector="{title}", reason="...")` (ADR-8: close+reason → resolve) |
| 419 | `backlog.py update "{title}" --plan "..."` | `backlog_update(selector="{title}", plan="...")` |
| 453 | `backlog.py view "{$1}" --format json` | `backlog_view(selector="{$1}")` |
| 473 | `backlog.py resolve "{title or #N}" --reason "..."` | `backlog_resolve(selector="...", reason="...")` |
| 566 | `backlog.py update "{title}" --status in-progress` | `backlog_update(selector="{title}", status="in-progress")` |
| 584 | `backlog.py close "{title}" --plan "..." --checklist-pass` | `backlog_close(selector="{title}", plan="...", checklist_pass=true)` |
| 590 | `backlog.py close "#{N}" --plan "..." --checklist-pass` | `backlog_close(selector="#{N}", plan="...", checklist_pass=true)` |
| 641 | `backlog.py view "#{issue_number}" --format json` | `backlog_view(selector="#{N}")` |
| 650 | `backlog.py update "{title}" --create-issue` | `backlog_update(selector="{title}")` (issue created automatically when missing) |
| 660 | `backlog.py update "{title}" --status in-progress` | `backlog_update(selector="{title}", status="in-progress")` |
| 685 | `backlog.py list` | `backlog_list()` |

**Action**: Replace all 19 `uv run` invocations with MCP tool calls.

---

#### 11. `.claude/skills/work-backlog-item/references/step-procedures.md` — Lines 12, 117

| Line | CLI Command | MCP Replacement |
|---|---|---|
| 12 | `backlog.py list --format json --with-status` | `backlog_list()` (status fields always included) |
| 117 | `backlog.py update "{title}" --plan "..."` | `backlog_update(selector="{title}", plan="...")` |

---

#### 12. `.claude/skills/work-backlog-item/references/github-integration.md` — Lines 36, 46, 61

| Line | CLI Command | MCP Replacement |
|---|---|---|
| 36 | `backlog.py update "{title}" --create-issue` | `backlog_update(selector="{title}")` (issue created automatically when missing) |
| 46 | `backlog.py update "{title}" --status in-progress` | `backlog_update(selector="{title}", status="in-progress")` |
| 61 | `backlog.py close "{title}" --plan "..." --checklist-pass` | `backlog_close(selector="{title}", plan="...", checklist_pass=true)` |

---

#### 13. `.claude/skills/work-backlog-item/references/close-resolve-procedure.md` — Lines 36, 129, 135

| Line | CLI Command | MCP Replacement |
|---|---|---|
| 36 | `backlog.py resolve "{title or #N}" --reason "..."` | `backlog_resolve(selector="...", reason="...")` |
| 129 | `backlog.py close "{title}" --plan "..." --checklist-pass` | `backlog_close(selector="{title}", plan="...", checklist_pass=true)` |
| 135 | `backlog.py close "#{N}" --plan "..." --checklist-pass` | `backlog_close(selector="#{N}", plan="...", checklist_pass=true)` |

---

#### 14. `.claude/skills/create-backlog-item/SKILL.md` — Line 163

**Current**:

```bash
uv run .claude/skills/backlog/scripts/backlog.py add \
  --title "{title}" --priority "{priority}" --description "{description}" \
  --source "{source}" --type "{type}" -R {OWNER/REPO}
```

**MCP**: `backlog_add(title="{title}", priority="{priority}", description="{description}", source="{source}", type="{type}")`

---

#### 15. `.claude/skills/groom-backlog-item/SKILL.md` — 6 invocations

| Line | CLI Command | MCP Replacement |
|---|---|---|
| 25 | `backlog.py list --format json` | `backlog_list()` |
| 65 | `backlog.py close "{title}" --reason "..."` | `backlog_resolve(selector="{title}", reason="...")` (ADR-8: close+reason → resolve) |
| 71 | `backlog.py view "#{N}" --format json` | `backlog_view(selector="#{N}")` |
| 94 | `backlog.py close "{title}" --reason "..."` | `backlog_resolve(selector="{title}", reason="...")` (ADR-8: close+reason → resolve) |
| 195 | `backlog.py <subcommand> --help` | N/A (discovery pattern — replace with tool list) |
| 198 | `backlog.py update "{title}" --section "..." --content "..."` | `backlog_update(selector="{title}", section="...", content="...")` |

---

#### 16. `.claude/skills/group-items-to-milestone/SKILL.md` — Line 37

**Current**:

```bash
uv run .claude/skills/backlog/scripts/backlog.py list --format json
```

**MCP**: `backlog_list()`

---

#### 17. `.claude/skills/backlog-tools-administrator/SKILL.md` — Lines 9, 17, 71, 78–79, 122

**Current**: Describes process for extending `backlog.py` when capabilities are missing.

**Action**: Update to describe extending both CLI and MCP server. Verification commands at lines 78–79 stay as CLI (linting/testing).

---

### Tier 3 — Agent Files — ✅ DONE

#### 18. `.claude/agents/backlog-item-groomer.md` — Line 79

**Current**:

```bash
uv run .claude/skills/backlog/scripts/backlog.py list --format json
```

**MCP**: `backlog_list()`

---

### Tier 4 — Documentation & Draft Files

These are informational — lower priority but should be updated for consistency.

#### 19. `.claude/docs/backlog-lifecycle.draft.md` — 14 invocations

Lines 55, 69, 107, 134, 138, 142, 150, 153, 202, 229, 264, 288.

**Action**: Update examples to show MCP tool syntax alongside or instead of CLI.

---

#### 20. `.claude/skills/backlog/backlog_core/ARCHITECTURE.md`

**Action**: Update to reflect completed extraction. Currently describes planned work that is now done.

---

### Tier 5 — Plan Files (historical, low priority)

These are completed or in-progress plans. Changes are optional — they serve as historical records.

| File | Line Count | Notes |
|---|---|---|
| `plan/architect-backlog-lifecycle-promotion.md` | 7 refs | Architecture spec with `--help` verification commands |
| `plan/tasks-11-backlog-lifecycle-promotion.md` | 15+ refs | Lifecycle promotion testing task file |
| `plan/tasks-7-backlog-gh-first-phase1.md` | 6 refs | GH-first phase 1 task file |
| `plan/feature-context-backlog-lifecycle-promotion.md` | 10+ refs | Feature context with VERIFY annotations |
| `plan/codebase/cross-references-backlog.md` | 1 ref | Cross-reference analysis |
| `plugins/agentskill-kaizen/docs/plans/2026-02-20-duckdb-lock-scope-flag.md` | 3 refs | DuckDB plan with backlog note |

**Action**: Leave as-is or add a note that CLI calls now have MCP equivalents.

---

### Tier 6 — Backlog Item Files (self-referential)

These are backlog items about `backlog.py` improvements. They reference the CLI as the subject of work.

| File | Topic |
|---|---|
| `p0-streamline-backlog-urlissue-number-handling-to-use-backlogpy.md` | URL/issue# handling |
| `p1-backlogpy-add-implement-fuzzy-duplicate-detection-before-cre.md` | Duplicate detection |
| `p1-backlogpy-closeresolve-should-check-for-open-prs-before-clos.md` | PR check before close |
| `p1-backlogpy-unify-issue-body-template-and-add-missing-structur.md` | Issue body template |
| `p1-backlogpy-update-needs-title-and-description-flags.md` | Missing update flags |
| `p2-backlogpy-plan-field-na-blocks-work-backlog-item-step-2.md` | Plan field N/A blocking |
| `p2-backlogpy-pull-should-accept-issue-selector-argument.md` | Pull selector argument |
| `p2-backlogpy-resolveclose-fails-on-github-only-issues-without-l.md` | GitHub-only issue handling |
| `idea-convert-backlogpy-into-an-mcp-server-using-fastmcp-skill.md` | MCP conversion idea (this work!) |

**Action**: Close `idea-convert-backlogpy-into-an-mcp-server-using-fastmcp-skill.md` when MCP server is registered. Other items apply to both CLI and MCP (operations layer).

---

### Tier 7 — Python Code (internal references)

These reference `backlog.py` within the package itself — not migration targets but noted for completeness.

| File | Type | Notes |
|---|---|---|
| `.claude/skills/backlog/scripts/backlog.py` | CLI script | **Keep** — thin wrapper calling operations |
| `.claude/skills/backlog/backlog_core/operations.py` | Operations | References CLI in user-facing messages (line 274) |
| `.claude/skills/backlog/backlog_core/parsing.py` | Parsing | Module docstring references extraction from `backlog.py` |
| `.claude/skills/backlog/tests/test_backlog_gh_first.py` | Tests | `importlib` import of `backlog.py` for CLI integration tests |
| `.claude/scripts/rebuild_issue_bodies.py` | Utility | Works with backlog items directly, no CLI invocation |

---

## Summary Statistics

| Category | Files | CLI Invocations | Priority |
|---|---|---|---|
| Policy & infrastructure | 8 | 2 direct + context refs | Tier 1 — change first |
| Skill files | 9 (5 skills + 4 references) | **31** | Tier 2 — highest impact |
| Agent files | 1 | 1 | Tier 3 — moderate |
| Documentation & drafts | 2 | ~15 | Tier 4 — lower priority |
| Plan files (historical) | 6 | ~40 | Tier 5 — optional |
| Backlog items | 9 | subject references | Tier 6 — close/update |
| Python code (internal) | 5 | internal refs | Tier 7 — keep |

**Total unique files**: ~40
**Total CLI invocations requiring MCP migration**: ~34 (Tiers 1–3)
**Total CLI references across all tiers**: ~90+

---

## Migration Prerequisites

Before updating any skill/agent files:

1. **Register MCP server in `.mcp.json`** — without this, no MCP tool calls work
2. **Verify server starts cleanly**: `uv run python -m backlog_core.server` or equivalent
3. **Decide on dual-mode or MCP-only** — skills could use MCP when available, CLI as fallback
4. **GitHub Actions stays CLI** — CI/CD has no MCP client, keep `backlog-sync.yml` as-is

## Migration Order

```text
1. Register backlog server in .mcp.json or agent frontmatter mcpServers
2. Update .claude/CLAUDE.md policy section
3. Update session hooks (session-start-backlog.cjs, stop-backlog-reminder.cjs)
4. Update skill files (work-backlog-item → create-backlog-item → groom-backlog-item → group-items-to-milestone)
5. Update skill reference files (step-procedures.md, github-integration.md, close-resolve-procedure.md)
6. Update agent files (backlog-item-groomer.md)
7. Update backlog/SKILL.md documentation
8. Update backlog-tools-administrator/SKILL.md
9. Update documentation drafts
10. Close the MCP conversion backlog item
```
