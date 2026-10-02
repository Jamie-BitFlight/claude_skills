# Utilization Proposals: GitHub Agentic Workflows (gh-aw)

**Research entry**: ./research/developer-tools/gh-aw.md
**Generated**: 2026-10-02
**Integration surfaces found**: 3 (CLI extension | Markdown workflow definition | MCP server integration)
**Proposals written**: 2
**Skipped**: 2 — agent-orchestration plugin uses harness-agnostic patterns (not GitHub-specific); development harness agents require a new bridging skill to coordinate

---

## Utilization 1: .claude/skills/gh/ → gh-aw CLI extension

**Research entry**: ./research/developer-tools/gh-aw.md
**Caller**: /home/user/claude_skills/.claude/skills/gh/SKILL.md
**Integration mechanism**: CLI subprocess (gh aw extension discovery and invocation)
**Replaces or adds**: Adds capability to define and execute AI-powered GitHub workflows declaratively using Markdown
**Setup cost**: Low (gh-aw installs as GitHub CLI extension; no additional auth beyond existing GITHUB_TOKEN)
**Integration surface**: CLI extension `gh aw` with commands: `init`, `new`, `compile`, `run`, `logs`, `audit`, `doctor`, `add-wizard`, `status`, `fix`

### Why this caller

The `/gh` skill already provides GitHub CLI (`gh`) setup, authentication configuration, and repository detection patterns for AI agents. The skill's scope includes "Need authenticated GitHub operations with GITHUB_TOKEN" and "Managing GitHub Issues, Projects V2, Milestones, or Labels." gh-aw is a first-class `gh` extension that extends the CLI with AI-powered workflow capabilities. Adding gh-aw support to this skill enables agents to:
- Define repository automation tasks in plain Markdown instead of YAML
- Leverage AI reasoning for tasks requiring intelligent decisions (issue triage, PR review analysis, CI investigation)
- Execute these workflows through GitHub Actions with built-in safety constraints and MCP server integration

The skill currently documents how to use `gh` for simple API calls and project management; gh-aw would extend this to declarative workflow definition and orchestration.

### Integration sketch

```bash
# Extension setup (add to gh/SKILL.md or referenced script)
gh extension install github/gh-aw

# Workflow file structure (documented in gh skill references)
cat > .github/workflows/issue-triage.md << 'EOF'
---
name: Issue Triager
on: [issues]
engines: [claude]
permissions:
  issues: write
  pull-requests: read
mcp_servers:
  - github
---

# Markdown body: agent instructions
Analyze the newly opened issue and:
1. Classify it by type (bug, feature, documentation)
2. Add appropriate labels based on classification
3. Assign to relevant team if urgent
EOF

# Compilation (validates Markdown, generates .lock.yml)
gh aw compile

# Execution via GitHub Actions (automatic on trigger)
# Or manual execution for testing:
gh aw run issue-triage
```

---

## Utilization 2: .github/workflows/ (GitHub Actions) → gh-aw workflow format

**Research entry**: ./research/developer-tools/gh-aw.md
**Caller**: /home/user/claude_skills/.github/workflows/ (existing workflow files)
**Integration mechanism**: CLI subprocess (gh aw compile generates .lock.yml for Actions execution)
**Replaces or adds**: Replaces manual YAML workflow authoring with declarative Markdown for AI-driven tasks; preserves existing deterministic CI/CD workflows
**Setup cost**: Medium (requires initialization with `gh aw init`, workflow conversion, compiler validation; existing workflows remain unchanged)
**Integration surface**: Workflow file format (Markdown + YAML frontmatter), compiler (`gh aw compile`), execution (`gh aw run`), lock files (`.lock.yml`)

### Why this caller

The repository currently has 9 GitHub Actions workflows in `.github/workflows/` that handle CI/CD, code quality, Claude Code integration, and backlog synchronization. Several of these workflows involve intelligent decision-making that currently relies on:
- Hardcoded conditionals for when to trigger Claude Code (looking for `@claude` mentions)
- Sequential job execution with bash logic for state inspection
- Limited ability to reason about complex conditions (e.g., when to auto-rebase, how to triage failing tests)

gh-aw would replace manual YAML workflow authoring for tasks requiring AI reasoning with declarative Markdown that specifies the goal and constraints, leaving execution safety to gh-aw's built-in permission validation and sandboxing. Examples:
- **Issue triage** (`claude-code-review.yml`-adjacent): Use AI to classify issues, add labels, assign to teams
- **CI investigation** (`main-ci-health-check.yml`): Use AI to analyze CI failures and suggest remedies
- **Auto-rebase decisions** (`auto-rebase.yml`): Use AI to reason about when rebasing is safe
- **Code review orchestration**: Use AI to route reviews to appropriate specialists

The research entry notes that compiled workflows embed agent prompts, engine selection, MCP server configuration, and safe-outputs validation — exactly what this repository needs to coordinate complex repository automation without hardcoding conditional logic.

### Integration sketch

```markdown
# New file: .github/workflows/ci-investigation.md

---
name: CI Investigation Agent
on:
  workflow_run:
    workflows: [code-quality]
    types: [completed]
engines: [claude]
permissions:
  checks: read
  pull-requests: write
  contents: read
mcp_servers:
  - github  # Provides GitHub API access to read checks, artifacts
---

# Agent task description (in Markdown)

When the code quality workflow fails, analyze the failure:

1. Read the workflow run logs and artifact outputs
2. Identify the root cause (syntax error, test failure, type mismatch, etc.)
3. For each failure, suggest a specific fix with code if applicable
4. Comment on the PR with structured findings and next steps

Prioritize:
- Test failures first (usually actionable)
- Type check failures second
- Lint warnings last

Do NOT make fixes directly; only analyze and suggest.
```

After writing this workflow:

```bash
gh aw compile                              # Validates and generates .lock.yml
gh aw run ci-investigation --dry-run      # Test without executing
gh aw audit <run-id>                      # Review execution logs
```

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| plugins/agent-orchestration/ (delegate skill, parallel-work skill) | Orchestrates sub-agents within Claude ecosystem (Claude Code, Codex, etc.); uses harness-agnostic patterns. gh-aw is GitHub-specific and would inform orchestration concepts but does not directly replace or extend current agent dispatch mechanisms. |
| Development harness agents (research-curator, code-review, reviewers, etc.) | Currently triggered via backlog system and manual dispatch; no direct GitHub workflow integration. gh-aw could trigger these agents via GitHub Events, but would require creating a new bridging skill or agent to translate gh-aw workflows to harness dispatch calls. Deferred as a separate utilization opportunity. |

