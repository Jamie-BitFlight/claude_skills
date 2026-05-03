---
name: no-mistakes - Git Push Quality Gate for AI-Driven Development
description: no-mistakes is a local git proxy that validates AI-generated code before pushing upstream. It spins up a disposable worktree, runs a configurable AI-driven validation pipeline (rebase, review, tests, docs, lint), and opens clean PRs automatically only after all gates pass.
license: MIT
metadata:
  topic: git workflow automation
  category: developer-tools
  source_url: https://github.com/kunchenguid/no-mistakes
  github: kunchenguid/no-mistakes
  version: "1.11.0"
  verified: "2026-05-03"
  next_review: "2026-08-03"
  language: Go
---

## Overview

no-mistakes is a local git proxy that acts as a quality gate for branches before they reach the remote repository. Instead of pushing directly to origin, developers push to a local `no-mistakes` gate. The tool:

1. Creates an isolated worktree for validation
2. Runs a configurable AI-driven validation pipeline (rebase, linting, tests, review, documentation)
3. Executes auto-fixes where possible
4. Pushes to upstream and opens a PR only after all gates pass
5. Monitors CI and auto-fixes failures (optional)

The core philosophy: **Kill all the slop. Raise clean PR.** By moving quality validation into the inner loop (before pushing), developers get faster feedback, cleaner PRs, and fewer review churn cycles.

---

## Problem Addressed

| Problem | no-mistakes Solution |
|---------|-------------------|
| AI agents generate massive diffs with mixed quality (brilliant code + slop) | Spins up isolated validation pipeline; quality checks happen before remote push |
| Developers can't review 5,000-line diffs effectively | Configurable gates (rebase, lint, test, review, docs) catch issues early in local worktree |
| CI failures require repeated push-fix-push cycles | Optional auto-fix watcher monitors CI and applies fixes automatically before human review |
| PRs opened without documentation or formatting checks | Documentation, linting, and formatting run before PR opens; developer can review or auto-accept fixes |
| Branch history is messy when rebased; squashing requires manual steps | Rebase step in pipeline ensures clean history before push |
| No unified approach to what gates a PR must pass before merging | Customizable gate configuration per repository; flexible enough for different project needs |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 413 | 2026-05-03 |
| GitHub Forks | 18 | 2026-05-03 |
| Open Issues | 4 | 2026-05-03 |
| Repository Created | 2026-04-05 | - |
| Latest Release | v1.11.0 | 2026-05-02 |
| Language | Go | 2026-05-03 |
| License | MIT | 2026-05-03 |
| Repository Size | ~3.2 MB | 2026-05-03 |
| Last Pushed | 2026-05-02 20:47 UTC | - |
| Documentation Site | <https://kunchenguid.github.io/no-mistakes/> | Active |

---

## Key Features

### Non-Blocking Isolated Worktree

Push to `no-mistakes` starts validation in a temporary worktree without interrupting local development. Your working directory remains unchanged while the gate processes your code.

```bash
git push no-mistakes <branch>
# Pipeline starts in background; you can continue working
```

### Agent-Agnostic Validation Pipeline

Configurable to work with any AI coding assistant:
- Claude Code (primary)
- OpenAI Codex CLI (`codex`)
- Rovodev (`rovodev`)
- OpenCode (`opencode`)
- Pi (`pi`)

Each agent has a distinct wire format; the tool detects and adapts.

### Multi-Stage Validation Gates

| Gate | Purpose | Example |
|------|---------|---------|
| **Rebase** | Sync with upstream and detect conflicts | Rebase onto fresh `main` before any other checks |
| **Lint/Format** | Code style compliance | `ruff format`, `prettier`, `eslint` |
| **Test** | Regression + new test coverage | Run test suite; fail if tests don't pass |
| **Review** | AI-driven code review | Detect common patterns, security issues, architecture problems |
| **Documentation** | Keep docs in sync with code | Generate/update README, API docs, etc. |
| **Custom** | User-defined gates | Run any shell command as a gate |

All gates run in the isolated worktree. Gates can auto-fix issues or require human review.

### Auto-Fix Capability

Gates can automatically fix violations without human intervention:
- Linting and formatting auto-fix (`--fix` flags)
- Documentation regeneration
- Test creation (when AI review identifies missing tests)

Developer sees all auto-fixes before they're committed and can reject them.

### Human-in-the-Loop Review

The TUI (`no-mistakes` command with no args) shows:
- Gate execution status
- Findings per gate (issues, auto-fixes, suggestions)
- Diff preview before accepting
- Option to auto-accept all fixes or review each gate

```bash
$ no-mistakes
# Opens TUI showing active run, gate results, findings
```

### Automatic PR Opening and CI Watching

After all gates pass:
1. Branch is pushed to upstream
2. PR is opened automatically
3. (Optional) Tool watches CI and applies auto-fixes if tests fail

No manual `gh pr create` needed.

### Real-Time TUI Dashboard

```bash
$ no-mistakes
┌─ Pipeline Run ─────────────────┐
│ Status: Running                │
│                                │
│ ✓ Rebase (passed)             │
│ ✓ Format (auto-fixed 3)       │
│ ⟳ Lint (running)              │
│ ⊗ Test (pending)              │
│ ⊗ Review (pending)            │
│ ⊗ Docs (pending)              │
└────────────────────────────────┘
```

Displays real-time progress, findings, and allows drilling into each gate for details.

---

## Technical Architecture

### Package Structure

Written in Go v1.25.0. Key dependencies:

- **TUI**: charmbracelet/bubbles + bubbletea (terminal UI framework)
- **CLI**: spf13/cobra (command framework)
- **Git**: (native git CLI via subprocess)
- **Storage**: modernc.org/sqlite (local state management)
- **UUID**: oklog/ulid (distributed unique identifiers for runs)

Primary modules:
- `cmd/` - CLI entry points (init, push, status, etc.)
- `internal/gate/` - Gate execution engine
- `internal/store/` - SQLite-backed state persistence
- `internal/e2e/` - End-to-end test fixtures and harness

### Gate Model (Core Architecture)

Each push is a **Run**:

```
Push → Worktree Creation → Gate Execution → Decision → Push/PR/Cleanup
                                ↓
                    (Parallel/Sequential gates)
                           ↓
                    Collect findings
                           ↓
                    Human review in TUI
```

**Run Lifecycle**:
1. Create isolated worktree (copy of repo at branch)
2. Check out branch in worktree
3. Rebase onto fresh upstream
4. Execute gates in order (or parallel if configured)
5. Collect auto-fix suggestions and findings
6. Present via TUI for human decision
7. If approved: push to origin, open PR
8. If rejected: discard worktree, branch unchanged locally
9. Cleanup

**State Persistence**:
- SQLite database stores all runs
- Run ID (ULID) tracks each invocation
- Gate results, auto-fixes, and decisions stored atomically
- Allows session recovery (reattach to running gate, review past runs)

### Multi-Agent Wire Format Detection

The tool must understand agent wire formats to extract findings. Currently supports:

| Agent | Format |
|-------|--------|
| Claude Code | stdio JSON + Claude API response schema |
| Codex CLI | YAML frontmatter + stdout |
| OpenCode | TBD (PR under review) |
| Rovodev | TBD (planned) |
| Pi | TBD (planned) |

New agents can be added by implementing the wire format parser in `internal/agent/`.

---

## Installation and Usage

### Install

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/kunchenguid/no-mistakes/main/docs/install.sh | sh

# Windows / Go install / build from source
# See https://kunchenguid.github.io/no-mistakes/start-here/installation/
```

Requires: Git 2.10+, your AI coding assistant CLI (claude, codex, opencode, etc.), shell access.

### First-Time Setup

```bash
$ cd /path/to/repo
$ no-mistakes init
  ✓ Gate initialized

    repo  /Users/you/src/my-repo
    gate  no-mistakes → /Users/you/.no-mistakes/repos/abc123def456.git
  remote  git@github.com:you/my-repo.git

  Push through the gate with:
  git push no-mistakes <branch>
```

This creates:
- Local git proxy at `~/.no-mistakes/repos/{repo-id}.git`
- Adds `no-mistakes` remote to your local repo
- Initializes SQLite state database

### Typical Workflow

```bash
# Make changes on a branch
$ git checkout -b feature/foo
$ # ... edit files ...
$ git add -A
$ git commit -m "feat: add foo"

# Push through the gate instead of origin
$ git push no-mistakes feature/foo
  * Pipeline started

  Run no-mistakes to review.

# Open TUI to review findings
$ no-mistakes
# (TUI shows gate results, auto-fixes, findings)
# (User approves or rejects)

# If approved:
# - Branch pushed to origin
# - PR opened automatically
# - (Optional) Tool watches CI for failures
```

### Configuration

Configuration via `.no-mistakes/config.yaml` (in repo root or home):

```yaml
agent: claude                    # or codex, opencode, etc.
gates:
  - name: rebase
    enabled: true
  - name: lint
    enabled: true
    auto_fix: true
    linter: ruff                 # or eslint, prettier, etc.
  - name: test
    enabled: true
    command: "npm test"          # custom test command
  - name: review
    enabled: true
    fix_suggestions: true        # auto-apply AI suggestions
  - name: docs
    enabled: true
    auto_generate: true          # regenerate README, API docs, etc.
  - name: custom
    enabled: true
    command: "./scripts/validate.sh"

pr:
  auto_open: true
  auto_fix_ci: true              # watch CI and auto-fix failures
  labels:
    - "automated"
    - "review:pending"
```

### CLI Commands

| Command | Purpose |
|---------|---------|
| `no-mistakes init` | Initialize gate for current repo |
| `no-mistakes` | Open TUI for active run (or list past runs) |
| `no-mistakes status` | Show current pipeline status |
| `no-mistakes log <run-id>` | View detailed log for a run |
| `no-mistakes config` | Show current configuration |

### Development

```bash
make build               # Build bin/no-mistakes with version
make test               # Run tests (excludes e2e)
make e2e                # Run end-to-end test suite
make e2e-record         # Re-record e2e fixtures from real agents
make lint               # Run go vet
make fmt                # Run gofmt
make demo               # Regenerate demo.gif and demo.mp4
make docs               # Build Astro docs site
```

The e2e suite records real interactions with Claude Code, Codex, and OpenCode CLIs. Recorded fixtures are committed; re-recording uses real API quota and should be reviewed before committing.

---

## Integration Points and Ecosystem

### Git Integration

- Acts as a transparent git remote (`git push no-mistakes`)
- Reads/writes to `.git` in isolated worktree
- Handles merge conflicts during rebase
- Compatible with any git workflow (trunk-based, feature branches, monorepos)

### AI Agent Integration

Works with any AI coding assistant that:
1. Reads branch diff or accepts instructions
2. Generates code changes
3. Outputs findings/suggestions in a parseable format

Planned integrations:
- **Devin AI** - once wire format is published
- **GitHub Copilot CLI** (codegen mode)
- **Anthropic Claude** (direct API, no CLI required)

### Git Hosting Integration

- **GitHub** - auto-opens PRs via `gh` CLI
- **GitLab** (planned) - auto-opens merge requests
- **Gitea** (planned) - self-hosted support
- **Bitbucket** (planned)

Currently GitHub-only; others planned.

### CI/CD Integration

- Monitors CI status via GitHub Actions API
- Auto-fixes on test failures (optional)
- Integrates with standard CI platforms (GitHub Actions, GitLab CI, CircleCI)
- Respects branch protection rules (enforces required reviews)

### MCP/Tool Ecosystem

Not yet an MCP server, but architecture allows:
- Future MCP server mode for Claude Code plugin integration
- Webhook integration for CI systems
- REST API for custom tooling

---

## Relevance to Claude Code Development

### Use Cases

1. **AI-Assisted Codebases**: Developers using Claude Code to generate large diffs benefit from automated quality validation before PR opens, reducing review churn.

2. **Multi-Agent Workflows**: When orchestrating Claude Code, Codex, and other agents (e.g., via oh-my-claudecode, TAKT), no-mistakes provides a unified quality gate regardless of which agent generates the code.

3. **Skill/Plugin Development**: Developers of Claude Code plugins/skills can use no-mistakes to validate generated code for their plugin before release (linting, tests, docs).

4. **Continuous Integration Gate**: Teams can enforce PR quality standards before human review by configuring gates that match their CI pipeline (linters, test coverage, security scanning).

### Integration Patterns

1. **As a Pre-PR Gate**: All AI-generated code goes through no-mistakes before opening PR, ensuring baseline quality (no formatting churn, tests pass, docs are synced).

2. **With Claude Code Plugins**: A Claude Code plugin could trigger `no-mistakes` directly after generating code, skipping the manual `git push origin` step.

3. **With Multi-Agent Orchestrators**: Orchestrators (oh-my-claudecode, TAKT, etc.) can wrap `no-mistakes` to ensure all agent outputs meet project quality standards.

4. **In CI Pipelines**: Teams can configure GitHub Actions to run `no-mistakes` on incoming branches, using it as a quality layer before merge.

### Patterns Worth Adopting

1. **Isolated Validation Worktree**: Non-blocking validation that doesn't interrupt developer workflow.

2. **Multi-Stage Gates**: Composable quality checks (lint → test → review → docs) can be reordered or conditionally enabled per project.

3. **AI-Driven Review**: Leverage Claude Code's code understanding to catch issues before human review, reducing feedback cycles.

4. **Auto-Fix with Human Review**: Automatically fix format/lint issues but surface all changes to developer for approval before committing.

5. **Real-Time TUI Dashboard**: Terminal UI for reviewing pipeline results and findings beats email notifications or web dashboards for CLI-first workflows.

---

## References

1. **no-mistakes GitHub Repository** - <https://github.com/kunchenguid/no-mistakes> (accessed 2026-05-03)
2. **no-mistakes Documentation** - <https://kunchenguid.github.io/no-mistakes/> (accessed 2026-05-03)
3. **README.md** - <https://raw.githubusercontent.com/kunchenguid/no-mistakes/main/README.md> (accessed 2026-05-03)
4. **GitHub API Repository Metadata** - <https://api.github.com/repos/kunchenguid/no-mistakes> (accessed 2026-05-03): stars, forks, license, creation date, latest pushed timestamp
5. **GitHub API Tags** - <https://api.github.com/repos/kunchenguid/no-mistakes/tags> (accessed 2026-05-03): latest release v1.11.0
6. **go.mod** - <https://raw.githubusercontent.com/kunchenguid/no-mistakes/main/go.mod> (accessed 2026-05-03): Go version 1.25.0, dependency list
7. **Installation Guide** - <https://kunchenguid.github.io/no-mistakes/start-here/installation/> (referenced, contains platform-specific install instructions)
8. **Quick Start Guide** - <https://kunchenguid.github.io/no-mistakes/start-here/quick-start/> (referenced, full first-run walkthrough)
9. **Gate Model Architecture** - <https://kunchenguid.github.io/no-mistakes/concepts/gate-model/> (referenced, core architectural documentation)
10. **Makefile** - <https://raw.githubusercontent.com/kunchenguid/no-mistakes/main/Makefile> (inferred from README development section)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Worktrunk](./worktrunk.md) | developer-tools | shares isolated git worktree pattern for non-blocking parallel agent validation |
| [Claude Pilot](./claude-pilot.md) | developer-tools | complementary quality-enforcement layer with lifecycle hooks and `/spec` workflow; both use worktrees for isolated validation |
| [wrkflw](./wrkflw.md) | developer-tools | workflow validation before merge; no-mistakes gates code quality, wrkflw gates CI/CD configuration |
| [The Claw Loop](../research-agent-patterns/claw-loop.md) | research-agent-patterns | multi-agent orchestration pattern where no-mistakes provides the quality gate ensuring orchestrated agents' output passes before merge |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | comprehensive quality system for Claude Code; no-mistakes integrates as a complementary pre-PR validation layer |
| [TAKT](../research-agent-patterns/takt.md) | research-agent-patterns | multi-agent workflow orchestrator with state machine routing; no-mistakes can gate agent outputs in TAKT pipelines |
| [Gastown](../research-agent-patterns/gastown.md) | research-agent-patterns | multi-agent workspace manager with persistent state; no-mistakes provides deterministic quality validation for work before Gastown merges to main |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-05-03 |
| Version at Verification | v1.11.0 |
| Next Review Recommended | 2026-08-03 |
| Confidence Map | Overview: high (official docs), Key Features: high (README verified), Architecture: medium (code-read, partial source inspection), Usage: high (official installation docs), Relevance: medium (inferred from capabilities) |

---

## Integration Opportunities

> Auto-generated by research-context-agent. Review before acting.

### Enhances Existing

| Target | Type | How |
|--------|------|-----|
| `/everything-claude-code` skill | skill | Include no-mistakes as a post-generation workflow automation option for Claude Code agents; document how to configure gates matching the plugin's quality standards. |
| `/claude-pilot` skill | skill | Reference no-mistakes as a complementary tool for pre-PR quality validation; document how TDD enforcement and hook automation can delegate to no-mistakes gates. |
| `/worktrunk` skill | skill | Cross-reference no-mistakes for worktree-based validation; show how git worktree isolation patterns align with no-mistakes architecture. |
| `plugins/development-harness/skills/git-workflow/` | skill | Add no-mistakes as a recommended git push alternative for AI-assisted development; document the gate model and agent-agnostic validation approach. |

### Cross-References

- Related research: `research/developer-tools/worktrunk.md` — Worktrunk manages git worktrees for parallel AI agent workflows; no-mistakes uses isolated worktrees for validation, sharing the non-blocking isolation pattern.
- Related research: `research/research-agent-patterns/claw-loop.md` — Claw Loop orchestrates multi-agent development via tmux; no-mistakes provides the quality gate ensuring orchestrated agents' output passes before merge.
- Related research: `research/agent-frameworks/everything-claude-code.md` — Everything Claude Code includes hook-based automation and 65+ skills; no-mistakes integrates as a post-generation hook to enforce quality gates automatically.
- Related research: `research/developer-tools/claude-pilot.md` — Claude Pilot adds quality enforcement hooks to Claude Code; no-mistakes provides multi-stage validation gates that extend Pilot's TDD and review enforcement.
