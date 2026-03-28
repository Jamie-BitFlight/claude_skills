# Worktrunk

**Research Date**: 2026-03-28
**Source URL**: <https://worktrunk.dev>
**GitHub Repository**: <https://github.com/max-sixty/worktrunk>
**Version at Research**: v0.33.0
**License**: MIT OR Apache-2.0

---

## Overview

Worktrunk is a command-line interface for git worktree management designed specifically to enable running AI agents in parallel. It simplifies the git worktree workflow by addressing branches by name rather than filesystem paths, making operations like creating, switching, and removing worktrees as straightforward as working with branches. The tool is particularly valuable in AI-driven development workflows where multiple agents need isolated working directories.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Git worktree UX is clunky — requires typing branch name multiple times | Worktrees addressed by branch name; paths computed from configurable templates |
| Difficult to coordinate parallel agent work without stepping on changes | Each agent gets isolated worktree; `wt list` shows status across all |
| Slow context switching between parallel worktrees | `wt switch` with optional command execution (`-x` flag) + interactive picker with live diff preview |
| Merge workflow requires multiple manual steps (squash, rebase, merge, cleanup) | `wt merge` performs one-shot: commit, merge, and cleanup in sequence |
| Post-worktree setup (install deps, build) requires manual per-branch configuration | Project hooks (post-start, post-merge) run commands automatically on create, merge, etc |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 14,823+ (as of Feb 2026) | 2026-03-28 |
| Latest Release | v0.33.0 | 2026-03-27 |
| Primary Language | Rust | 2026-03-28 |
| Minimum Rust Version (MSRV) | 1.89 | 2026-03-28 |
| Total Modules/Commands | 8+ core modules | 2026-03-28 |

---

## Key Features

### Core Worktree Commands

- **wt switch [branch]** — Create or switch to a worktree; with `-c` flag creates new branch and worktree; with `-x` flag executes a command (e.g., `wt switch -x claude -c feature-auth` launches Claude Code in the new worktree)
- **wt list** — Show all worktrees with status indicators (staged changes, commits ahead/behind, unpushed commits, current worktree marked with `@`); supports `--full` mode with CI status and AI-generated summaries
- **wt merge [target]** — Squash, rebase, fast-forward merge, and cleanup in one command; outputs commit statistics
- **wt remove** — Clean up worktree and branch; validates worktree state before removal

### Workflow Automation

- **Hooks** — Run commands on create, pre-merge, post-merge, and other lifecycle events; configured in `wt.toml` per project or user config
- **LLM commit messages** — Generate commit messages from diffs using configured LLM API
- **Post-start commands** — Install dependencies, start dev servers, copy build caches between worktrees
- **Interactive picker** — Browse worktrees with live diff and log previews; built with `skim` on Unix platforms

### Advanced Features

- **PR checkout** — `wt switch pr:123` jumps to a PR's branch (requires GitHub/GitLab setup)
- **CI status** — `wt list --full` shows CI status per branch (GitHub Actions, GitLab CI)
- **Hash-based port assignment** — `hash_port` template filter assigns unique dev server ports per worktree
- **Build cache sharing** — Skip cold starts by copying `target/`, `node_modules/`, etc between worktrees via post-start hooks
- **Template variable expansion** — Configure worktree paths with template filters for customization

### Shell Integration

- **Shell wrapper installation** — `wt config shell install` integrates into bash, zsh, fish, and other shells to enable directory changes after command execution
- **Syntax highlighting** — Optional tree-sitter-based syntax highlighting for bash commands in output (disabled by default for cross-platform compatibility)

---

## Technical Architecture

Worktrunk is a single-binary Rust CLI with modular internal structure:

**Core modules** (Source: src/lib.rs — public module declarations):

- **git** — Repository operations, worktree metadata, branch management, commit operations
- **config** — User config loading, project config parsing, hook configuration from `wt.toml`
- **commands** — Worktree operations (switch, merge, remove, list), command execution
- **shell_exec** — Consistent external command execution with logging and tracing; all git and external commands routed through `shell_exec::Cmd`
- **shell** — Shell wrapper installation, shell detection
- **sync** — Synchronization primitives for concurrent operations
- **trace** — Tracing and structured logging
- **styling** — ANSI color output, terminal formatting

**Command structure** (Source: src/main.rs, lines 22-29):

Modular CLI built with clap, dispatching to handler functions in `commands/` module. Each command (switch, list, merge, remove, step, config, hook, init) has dedicated handler function and supporting modules for complex operations.

**Key design patterns:**

- **Repository caching** — Read-only values (remote URLs, config, branch metadata) cached via `Arc<RepoCache>` to avoid repeated I/O
- **Shell execution abstraction** — All external commands (git, gh, glab) routed through `shell_exec::Cmd` for consistent logging, timing, and error handling
- **Hook system** — Extensible pre/post hooks (create, merge, remove, start) executed via shell command expansion and template variable substitution
- **Template expansion** — minijinja for worktree path templates, hook commands, and LLM commit prompts

**External dependencies** (Source: Cargo.toml, dependency list):

- clap 4.6 — command-line argument parsing with help text generation
- minijinja 2.18 — template expansion for worktree paths and hooks
- git2 (via gitoxide/gix integration) — git operations (implicitly used for Repository functions)
- tree-sitter 0.26 (optional, feature-gated) — syntax highlighting for bash commands
- config 0.15 — TOML configuration loading
- crossterm 0.29 — terminal manipulation (cursor, clearing, etc.)
- serde 1.0, serde_json 1.0 — JSON output for `wt list --format=json`

---

## Installation & Usage

### Installation

**Homebrew (macOS & Linux):**

```bash
brew install worktrunk && wt config shell install
```

**Cargo (Rust toolchain required):**

```bash
cargo install worktrunk && wt config shell install
```

**Arch Linux:**

```bash
paru worktrunk-bin && wt config shell install
```

**Windows (via Winget):**

```bash
winget install max-sixty.worktrunk
git-wt config shell install
```

Shell integration installation enables directory changes after commands complete.

### Quick Start

Create a new worktree for a feature:

```bash
wt switch --create feature-auth
```

This creates a new branch and worktree, then switches to it. List all worktrees:

```bash
wt list
```

Output example:

```text
  Branch        Status        HEAD±    main↕  Remote⇅  Commit    Age   Message
@ feature-auth  +   ↑      +27   -8   ↑1               4bc72dc9  2h    Add authentication module
^ main              ^⇡                         ⇡1      0e631add  1d    Initial commit
```

Launch Claude Code in a new worktree:

```bash
wt switch -x claude -c feature-a -- 'Add user authentication'
```

Merge worktree back to main and cleanup:

```bash
wt merge main
```

### Configuration

Project config at `wt.toml` in repository root:

```toml
[hooks]
post-start = ["npm install", "npm run dev"]

[config]
worktree-path = "../{repo}.{branch}"
```

User config at `~/.config/worktrunk/config.toml` (location varies by OS):

```toml
[llm]
api = "anthropic"
model = "claude-3-5-sonnet"
```

---

## Relevance to Claude Code Development

### Applications

- **Multi-agent workflows** — Worktrunk's core design is built for parallel AI agents. Launching multiple agents with `wt switch -x claude -c feature-name` provides each agent an isolated working directory and automatic setup via hooks, directly supporting the multi-agent coding patterns that Claude Code enables
- **Branch-centric thinking** — Addresses worktrees by branch name, aligning with how AI agents naturally think about parallel work (by task/feature) rather than filesystem paths
- **Automation integration** — Hooks system enables automated dependency installation, dev server startup, and CI status checking — reducing agent context switching overhead

### Patterns Worth Adopting

- **Template-based configuration** — Worktrunk's template variable system (`hash_port`, `{branch}`, `{repo}` in paths and hooks) provides a clean pattern for enabling user customization without hard-coded behavior
- **Shell execution abstraction** — Routing all external commands through a consistent `Cmd` wrapper for logging, tracing, and error handling is a pattern that reduces debugging friction
- **Interactive picker with live preview** — The branch picker with live diff and log previews is a UX pattern worth considering for agent-facing selection interfaces

### Integration Opportunities

- **Claude Code native support** — Worktrunk's `-x` flag for command execution makes it natural to integrate directly with Claude Code. The project includes a dedicated `claude-code.md` documentation page suggesting integration patterns
- **CI/CD status in agent context** — The `wt list --full` command with CI status integration could inform agent decision-making (e.g., agents prioritizing branches with failing CI)
- **Post-merge hooks** — Automated documentation updates, dependency pruning, or cleanup tasks triggered by merge completion could be orchestrated via Worktrunk hooks

---

## References

- [Worktrunk Official Documentation](https://worktrunk.dev) (accessed 2026-03-28)
- [Worktrunk GitHub Repository](https://github.com/max-sixty/worktrunk) (accessed 2026-03-28)
- [Worktrunk README.md](https://github.com/max-sixty/worktrunk/blob/main/README.md) (accessed 2026-03-28)
- [Worktrunk Cargo.toml](https://github.com/max-sixty/worktrunk/blob/main/Cargo.toml) (accessed 2026-03-28)
- [Worktrunk CLAUDE.md Development Guidelines](https://github.com/max-sixty/worktrunk/blob/main/CLAUDE.md) (accessed 2026-03-28)
- [Claude Code Best Practices — Anthropic Official Guide](https://www.anthropic.com/engineering/claude-code-best-practices) (accessed 2026-03-28)
- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree) (accessed 2026-03-28)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Agent Deck](../agent-deck.md) | developer-tools | terminal session manager for AI agents with native git worktree isolation and unified TUI |
| [Superset](../superset-sh.md) | developer-tools | runs 10+ parallel AI agents via git worktrees on macOS with branch-isolated execution |
| [Sidecar](../sidecar.md) | developer-tools | terminal UI companion for AI agents with tmux workspace management and git status tracking |
| [tmuxp](../tmuxp.md) | developer-tools | Python tmux session manager with YAML workspace configs—complementary to worktree orchestration |
| [Byobu](../byobu.md) | developer-tools | enhanced terminal multiplexer for tmux/screen—shares session management abstraction layer |
| [Using tmux with Claude Code](../using-tmux-with-claude-code.md) | developer-tools | practical guide for multi-pane agent orchestration; overlaps with Worktrunk's multi-agent coordination use case |
| [Everything Claude Code](../everything-claude-code.md) | developer-tools | 13 agents and 48+ skills—complements Worktrunk's agent isolation and parallel execution patterns |
| [Claude Code CLI Power Patterns](../claude-code-cli-power-patterns.md) | developer-tools | includes parallel worktrees pattern as core Claude Code deployment technique |
| [1Code](../1code.md) | coding-agents | Electron app wrapping Claude Code CLI with git worktree isolation for conflict-free parallel work |
| [Gastown](../gastown.md) | research-agent-patterns | multi-agent workspace manager coordinating 20-50+ Claude Code sessions—addresses same parallelism problem |
| [Vibe Kanban](../vibe-kanban.md) | task-management | Kanban UI for parallel AI agent orchestration with git worktree isolation |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-28 |
| Version at Verification | v0.33.0 |
| Next Review Recommended | 2026-06-28 |
| Confidence Map | Overview: high (official docs), Key Features: high (README verified), Architecture: medium (code-read, partial source inspection), Usage: high (official installation docs), Relevance: medium (inferred from capabilities) |

