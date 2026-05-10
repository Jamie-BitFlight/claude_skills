# Utilization Proposals: GitHub CLI (gh) Skill

**Research entry**: ./research/developer-tools/gh-skill.md
**Generated**: 2026-05-10
**Integration surfaces found**: 3 (CLI | SDK | Shell subprocess)
**Proposals written**: 3
**Skipped**: 2

---

## Utilization 1: create-milestone → GitHub CLI (gh)

**Research entry**: ./research/developer-tools/gh-skill.md
**Caller**: ./.claude/skills/create-milestone/SKILL.md
**Integration mechanism**: CLI subprocess via `gh api` REST endpoint
**Replaces or adds**: Replaces intermediate Python script `github_project_setup.py milestone create` with direct `gh api` call to GitHub REST API
**Setup cost**: Low (existing auth via `GITHUB_TOKEN`)
**Integration surface**: `gh api --method POST repos/{owner}/{repo}/milestones --input -` (REST API endpoint documented at research entry lines 174-179)

### Why this caller

The `create-milestone` skill currently delegates milestone creation to the `github_project_setup.py` script at line 87, invoking a custom Python wrapper around GitHub's REST API. Reading the research entry (lines 174–179, "No native milestone subcommand"), the skill has no dedicated `gh milestone` subcommand, so it uses `gh api` for direct REST calls. The skill documents this as the intended pattern (lines 245–256 of research entry show GraphQL and REST API output formatting).

Replacing the Python script invocation with a direct `gh api` call would:
- Remove the dependency on a custom automation script, reducing initialization cost
- Use the documented `gh api` pattern directly, matching the research entry's architecture (line 224: "Direct GraphQL query" example)
- Simplify error handling — `gh` returns structured exit codes and JSON directly

### Integration sketch

**Current (via Python script):**
```bash
uv run .claude/skills/gh/scripts/github_project_setup.py milestone create \
  --title "{title}" \
  --description "{description}" \
  --due "{YYYY-MM-DD}"
```

**Proposed (direct `gh api`):**
```bash
gh api \
  --method POST \
  -H "Accept: application/vnd.github.v3+json" \
  repos/{owner}/{repo}/milestones \
  -f title="{title}" \
  -f description="{description}" \
  -f due_on="{YYYY-MM-DD}"
```

Capture milestone number from response: `jq -r '.number'` (documented at research entry lines 246–256 for JSON output parsing).

---

## Utilization 2: complete-milestone → GitHub CLI (gh)

**Research entry**: ./research/developer-tools/gh-skill.md
**Caller**: ./.claude/skills/complete-milestone/SKILL.md
**Integration mechanism**: CLI subprocess via `gh api` REST endpoint + label update via `gh label`
**Replaces or adds**: Replaces `github_project_setup.py milestone close` and `github_project_setup.py project update-status` with direct `gh api` calls; adds native label management via `gh label list | grep`
**Setup cost**: Low (existing auth via `GITHUB_TOKEN`)
**Integration surface**: `gh api --method PATCH repos/{owner}/{repo}/milestones/{number}` (documented at research entry lines 174–179); `gh label list -R {owner}/{repo}` (documented at research entry lines 121–127 for label taxonomy operations)

### Why this caller

The `complete-milestone` skill invokes `github_project_setup.py milestone close` (line 107) to close milestones and update issue status labels. The research entry documents (lines 121–127) a label taxonomy with lifecycle states (`status:done`, `status:backlog`, etc.), and lines 245–256 document the `gh api` pattern for structured output.

Currently, the skill depends on a Python script for:
1. Closing the milestone (PATCH REST call)
2. Transitioning issues to `status:done` label

These are both achievable with direct `gh api` calls:
- Line 174–179 of research entry: REST API for milestone operations
- Line 121–127: Label taxonomy and bulk operations — the skill could use `gh label list` to fetch available labels, then `gh api` to update issue labels

Replacing the Python script removes a dependency and makes the milestone closure process observable in the skill documentation itself.

### Integration sketch

**Current (via Python script):**
```bash
uv run .claude/skills/gh/scripts/github_project_setup.py milestone close --number {number}
uv run .claude/skills/gh/scripts/github_project_setup.py project update-status --issue {issue_number} --status Done
```

**Proposed (direct `gh api` + label operations):**
```bash
# Close the milestone
gh api \
  --method PATCH \
  repos/{owner}/{repo}/milestones/{number} \
  -f state=closed

# Add status:done label to issue (if not present)
gh api \
  --method POST \
  repos/{owner}/{repo}/issues/{issue_number}/labels \
  -f labels='["status:done"]'
```

For bulk operations on multiple issues, chain `gh api` calls within a loop or use `gh issue list --milestone {number}` to fetch all issues, then update each.

---

## Utilization 3: group-items-to-milestone → GitHub CLI (gh)

**Research entry**: ./research/developer-tools/gh-skill.md
**Caller**: ./.claude/skills/group-items-to-milestone/SKILL.md
**Integration mechanism**: CLI subprocess via `gh api` REST endpoint + direct `gh issue` commands
**Replaces or adds**: Replaces `github_project_setup.py issue create`, `issue set-milestone`, and `project update-status` with direct `gh api` and `gh issue` commands; adds native issue query via `gh issue list`
**Setup cost**: Low (existing auth via `GITHUB_TOKEN`)
**Integration surface**: `gh issue create -R {owner}/{repo}` (documented at research entry lines 118–121); `gh issue list -R {owner}/{repo}` (documented at research entry line 93); `gh api` for bulk label operations (documented at research entry lines 245–256)

### Why this caller

The `group-items-to-milestone` skill invokes `github_project_setup.py` three times:
- Line 69: `issue create` — create issues with labels
- Line 86: `issue set-milestone` — assign to milestone
- Line 96: `project update-status` — update Project V2 status

The research entry documents (lines 118–121) the native `gh issue create` command with label support, which is simpler than the Python script wrapper. Lines 93 and 227 document `gh pr list` and `--paginate` — similar patterns apply to `gh issue list`.

Replacing the Python script would:
- Use the documented `gh issue create` command directly, reducing boilerplate
- Enable the skill to query issues more dynamically (e.g., `gh issue list --milestone {number}`) without a separate script
- Simplify label management — research entry documents label taxonomy (lines 121–127); `gh api` can apply labels without custom Python logic

### Integration sketch

**Current (via Python script):**
```bash
uv run .claude/skills/gh/scripts/github_project_setup.py issue create \
  --title "{type}: {title}" \
  --body "{story body}" \
  --priority-label "priority:{p0|p1|p2}" \
  --type-label "type:{feature|bug|refactor|docs|chore}" \
  --milestone {number}

uv run .claude/skills/gh/scripts/github_project_setup.py issue set-milestone \
  --issue {issue_number} \
  --milestone {milestone_number}

uv run .claude/skills/gh/scripts/github_project_setup.py project update-status \
  --issue {issue_number} \
  --status Backlog
```

**Proposed (direct `gh` commands):**
```bash
# Create issue with labels in one command
gh issue create -R {owner}/{repo} \
  --title "{type}: {title}" \
  --body "{story body}" \
  --label "priority:{p0|p1|p2}" \
  --label "type:{feature|bug|refactor|docs|chore}" \
  --milestone {number}

# Set milestone on existing issue
gh issue edit {issue_number} -R {owner}/{repo} \
  --milestone {milestone_number}

# Add status label via API (Project V2 update)
gh api \
  --method POST \
  repos/{owner}/{repo}/issues/{issue_number}/labels \
  -f labels='["status:backlog"]'
```

Query all issues in milestone:
```bash
gh issue list -R {owner}/{repo} --milestone {number} --json number,title,state
```

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `./.claude/skills/backlog-tools-administrator/SKILL.md` | This skill explicitly prevents `gh` command usage (line 11: "instead of bypassing the backlog tools ... with direct file edits or `gh` commands"). Integration would contradict the skill's purpose. |
| `./.claude/skills/daily-releases/SKILL.md` | Read and assessed: does not directly invoke GitHub API or CLI for issue/milestone operations; focuses on release notes generation. No integration surface overlap with `gh` skill documented in research entry. |

---

## Summary

The GitHub CLI skill documents an **established integration surface** (CLI binary with REST/GraphQL API access, authenticated via `GITHUB_TOKEN`). Three milestone/issue management skills currently invoke the `github_project_setup.py` automation script as an intermediate layer. Direct `gh` CLI calls would:

1. **Reduce dependency on custom Python scripts** — the documented `gh` commands (issue create, issue edit, gh api) can replace them
2. **Simplify error handling** — `gh` returns structured exit codes and JSON directly
3. **Enable dynamic querying** — `gh issue list`, `gh label list` patterns would allow skills to adapt based on current repository state

**Integration cost**: Low — all three caller skills already set `GITHUB_TOKEN` in their environment and reference the `gh` skill as a dependency. Replacing Python script invocations with direct `gh` commands is a straightforward refactor.

---

## Notes

- The research entry is comprehensive and current (verified 2026-05-10 against GitHub CLI v2.87.2)
- All proposed integrations use the `-R {owner}/{repo}` flag pattern, which is mandatory in proxy remote environments (documented at research entry lines 73–79)
- The automation script `github_project_setup.py` appears in multiple skills — a single refactor would benefit all three callers
- The `/backlog-tools-administrator` skill is a blocker: it explicitly prevents `gh` command usage to maintain backlog tooling isolation. Any integration proposal should respect this boundary.
