---
source_url: https://github.com/rtk-ai/rtk
research_date: 2026-09-12
version_at_research: 0.48.0
version_verified: 0.48.0
license: Apache-2.0
freshness_tracking:
  last_verified: 2026-09-12
  version_at_verification: 0.48.0
  next_review: 2026-12-12
  confidence:
    identity_metadata: high
    features: high
    technical_architecture: high
    installation_usage: high
    limitations: medium
    relevance_to_claude_code: high
---

# RTK (Rust Token Killer) — CLI Output Filtering for LLM Context

## Overview

**RTK** is a high-performance command-line proxy that minimizes LLM token consumption by filtering and compressing shell command output before it reaches agent contexts. Written in Rust as a single binary supporting 100+ commands, RTK intercepts Bash commands and applies intelligent filtering strategies to reduce output size by up to 90% without removing essential information.

**Core claim**: "RTK filters and compresses command outputs before they reach your LLM context. Single Rust binary, 100+ supported commands, <10ms overhead." (README.md line 37)

## Problem Addressed

LLM agents working with shell commands receive verbose, unstructured output that consumes tokens without adding proportional value. Commands like `git status`, `cargo test`, and `ls -la` produce boilerplate, progress bars, repetitive logging, and formatting that agents must parse but rarely need. This increases input token cost and context overhead.

RTK addresses this by intercepting Bash commands at execution time and applying four filtering strategies: **smart filtering** (removes noise/comments/whitespace), **grouping** (aggregates similar items by directory or error type), **truncation** (keeps context while cutting redundancy), and **deduplication** (collapses repeated log lines with counts).

## Key Features

### Command Coverage

RTK provides specialized filters for 100+ commands across multiple domains:

- **Git operations** (status, log, diff, add, commit, push, pull)
- **File operations** (ls, tree, cat, read, grep, rg, find, diff)
- **Test runners** (pytest, cargo test, jest, vitest, playwright, go test, rspec, rake test, phpt)
- **Build & linting** (cargo build/clippy, ruff, tsc, next build, prettier, sqlfluff, golangci-lint, rubocop, eslint)
- **Package managers** (pnpm, pip, bundle, uv)
- **Runtimes** (bun, deno — added in v0.48.0)
- **AWS CLI, Docker, Kubernetes, OpenShift**
- **Infrastructure as Code** (pulumi)
- **GitHub CLI** (pr list, pr view, issue list, run list)

(README.md lines 170–301)

### Filtering Strategy

Four core mechanisms applied to each command type:

1. **Smart Filtering** — Removes noise (comments, whitespace, boilerplate)
2. **Grouping** — Aggregates similar items (files by directory, errors by type)
3. **Truncation** — Keeps relevant context, cuts redundancy
4. **Deduplication** — Collapses repeated log lines with counts

(README.md lines 159–162)

Examples from README:
- `ls -la (45 lines)` → `rtk ls (12 lines)` — tree format with file counts instead of one-line-per-entry
- `git push (15 lines)` → `rtk git push (1 line)` — confirmation line instead of full progress output
- `cargo test (200+ lines on failure)` → `rtk test cargo test (~20 lines)` — failures only, passing tests collapsed to a count

### Auto-Rewrite Hook

RTK integrates with 17 AI coding tools (Claude Code, GitHub Copilot, Cursor, Gemini CLI, Codex, Windsurf, Cline/Roo Code, OpenCode, Pi, Oh My Pi, Hermes, Mistral Vibe, Kilo Code, Google Antigravity, Kimi AI, Factory Droid, OpenClaw) via hook-based command interception. Running `rtk init -g` installs hooks that transparently rewrite commands before execution (e.g., `git status` → `rtk git status`).

(README.md lines 415–437)

Hook strategies:
- **Auto-Rewrite (default)**: Hook rewrites command before execution, 100% adoption, zero context overhead
- **Suggest (non-intrusive)**: Hook emits hint, agent decides autonomously, ~70–85% adoption

(ARCHITECTURE.md lines 45–52)

### Analytics & Discovery

RTK provides observability commands:
- `rtk gain` — Summary stats and token savings dashboard
- `rtk gain --graph` — ASCII graph of last 30 days
- `rtk discover` — Find missed savings opportunities
- `rtk session` — Show adoption across recent sessions

(README.md lines 304–315)

### Token Savings Measurement

RTK calculates token savings as `bytes / 4` (approximation, no tokenizer shipped). Percentages reported are reductions in bash output, not reductions in the final bill. "Bash output is **one contributor to input tokens**, alongside your prompt, the system prompt and conversation history."

(README.md lines 61–65)

## Technical Architecture

### System Overview

RTK is a six-phase execution pipeline:

**Phase 1: PARSE** — Clap CLI parser extracts command, args, and flags
**Phase 2: ROUTE** — Dispatcher matches command type and routes to handler
**Phase 3: EXECUTE** — Launch subprocess and capture stdout/stderr
**Phase 4: FILTER** — Apply command-specific filtering and compression rules
**Phase 5: COMPRESS** — Deduplicate log lines, group by category
**Phase 6: OUTPUT** — Return filtered result and exit code

(ARCHITECTURE.md lines 59–136)

### Design Principles

1. **Single Responsibility** — Each module handles one command type
2. **Minimal Overhead** — ~5–15ms proxy overhead per command
3. **Exit Code Preservation** — CI/CD reliability through proper exit code propagation
4. **Fail-Safe** — If filtering fails, fall back to original output
5. **Transparent** — Users can always see raw output with `-v` flags

(ARCHITECTURE.md lines 31–36)

### Implementation Details

**Language**: Rust (edition 2021, min version 1.91)
**Dependencies**: clap (CLI parsing), serde/serde_json (serialization), regex (pattern matching), rusqlite (token tracking database), toml/toml_edit (configuration), libc (Unix) / windows-sys (Windows) for platform-specific APIs, ignore/walkdir (directory traversal), colored (output formatting), chrono (timestamps), ureq (HTTP for self-updates), sha2 (SHA256 verification)

(Cargo.toml)

**Hooks**: Two interception strategies — PreToolUse hooks (Claude Code, VS Code, Factory Droid), BeforeTool hooks (Gemini), AGENTS.md/rules directives (Codex, Kimi, Windsurf, Cline), TypeScript extensions (Pi, OMP), Python plugin adapters (Hermes)

(README.md lines 418–436)

## Installation & Usage

### Installation Methods

**Homebrew (recommended)**:

```bash
brew install rtk
```

**Windows (winget)**:

```powershell
winget install rtk-ai.rtk
```

**Quick install (Linux/macOS)**:

```bash
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
```

**Cargo**:

```bash
cargo install --git https://github.com/rtk-ai/rtk
```

**Pre-built binaries** available for macOS (x86_64/aarch64), Linux (x86_64-musl/aarch64-gnu), Windows (x86_64-msvc)

(README.md lines 71–108)

### Setup for AI Tools

Hook installation varies by tool:

```bash
rtk init -g                         # Claude Code / Copilot (default)
rtk init -g --gemini                # Gemini CLI
rtk init -g --codex                 # Codex (OpenAI)
rtk init -g --agent cursor          # Cursor
rtk init --agent cline              # Cline / Roo Code
rtk init -g --agent hermes          # Hermes
```

After install, restart the AI tool. The hook transparently rewrites Bash commands.

(README.md lines 124–140)

### Configuration

Configuration file: `~/.config/rtk/config.toml` (macOS: `~/Library/Application Support/rtk/config.toml`)

```toml
[hooks]
exclude_commands = ["curl", "playwright"]  # skip rewrite for these

[retriever]
mode = "sqlite"         # sqlite (default) | tee (legacy) | disabled
```

When a command fails, RTK saves the unfiltered output for later recovery via `rtk recall {token-id}`.

(README.md lines 442–459)

### Command Examples

**Files**:

```bash
rtk ls .                    # Compact directory tree
rtk read file.rs            # Smart file reading
rtk grep "pattern" .        # Grouped search results
```

**Git**:

```bash
rtk git status              # Compact status
rtk git log -n 10           # One-line commits
rtk git diff                # Condensed diff
```

**Testing**:

```bash
rtk pytest                  # Python tests (-90%)
rtk cargo test              # Cargo tests (-90%)
rtk jest                    # Jest compact (failures only)
```

(README.md lines 170–213)

## Relevance to Claude Code Development

**Direct integration**: RTK provides a PreToolUse hook for Claude Code that transparently rewrites Bash commands. This is the default installation method (`rtk init -g`) and requires no per-command context overhead from the agent.

**Scope limitation**: The hook only applies to Bash tool calls. Claude Code built-in tools (Read, Grep, Glob) bypass the hook because they are not shell commands. To get RTK filtering for file operations, use shell commands (`cat`, `rg`/`grep`, `find`) or call `rtk read`, `rtk grep`, `rtk find` directly.

(README.md lines 142–144)

**Use case**: For agents running multi-step workflows with intensive Git, test, and build operations, RTK reduces input token cost by filtering verbose command output. The transparent hook mode (100% adoption without context overhead) makes this especially valuable for long-running agent sessions.

## Limitations and Caveats

### Output Reduction ≠ Bill Reduction

RTK's reported savings are **reductions in bash output**, not final bill reductions. Bash output is one of multiple input token contributors (alongside prompt, system prompt, conversation history). The savings dilute at each step, and input tokens themselves are only part of the total bill (output tokens are also counted). The percentage reduction is reliable, but absolute token numbers are approximate (calculated as `bytes / 4` without a real tokenizer).

(README.md lines 61–65)

### Prompt Cache Interaction

RTK does not break Claude's prompt cache. "RTK filters output once per command. The result is stored in history and cached normally on subsequent API calls, so the cache keeps working as expected. Smaller outputs also mean cheaper cache writes and reads."

(README.md line 164, accessed 2026-09-12)

### Built-in Tool Limitation

The auto-rewrite hook only applies to Bash tool calls. Claude Code built-in tools (Read, Grep, Glob) do not pass through the hook and are not auto-rewritten. To use RTK filtering for file operations, use shell commands or call `rtk` commands explicitly.

(README.md lines 142–144, accessed 2026-09-12)

### Telemetry

RTK collects optional anonymous usage metrics (disabled by default, requires explicit opt-in). Data includes: salted device hash, RTK version, OS, architecture, command counts, top 5 passthrough commands, days since first use, etc. **Not collected**: source code, file paths, command arguments, secrets, environment variables, or repository contents.

(README.md lines 480–500)

## References

- **GitHub Repository**: <https://github.com/rtk-ai/rtk> (accessed 2026-09-12)
- **Official Website**: <https://www.rtk-ai.app> (referenced in README, accessed 2026-09-12)
- **User Guide**: <https://www.rtk-ai.app/guide> (referenced in README line 473, accessed 2026-09-12)
- **Architecture Documentation**: <https://github.com/rtk-ai/rtk/blob/master/docs/contributing/ARCHITECTURE.md> (accessed 2026-09-12)
- **Installation Reference**: <https://github.com/rtk-ai/rtk/blob/master/INSTALL.md> (referenced in README line 474, accessed 2026-09-12)
- **Contributing Guide**: <https://github.com/rtk-ai/rtk/blob/master/CONTRIBUTING.md> (referenced in README line 476, accessed 2026-09-12)
- **Security Policy**: <https://github.com/rtk-ai/rtk/blob/master/SECURITY.md> (referenced in README line 477, accessed 2026-09-12)
- **Telemetry Documentation**: <https://github.com/rtk-ai/rtk/blob/master/docs/TELEMETRY.md> (referenced in README line 481, accessed 2026-09-12)
- **Latest Release**: v0.48.0 (2026-09-04) — added Bun and Deno runtime support (CHANGELOG.md line 8)

## Freshness Tracking

**Last verified**: 2026-09-12
**Current version**: 0.48.0 (released 2026-09-04)
**Next review recommended**: 2026-12-12 (3 months from verification date)

**Changes in v0.48.0** (most recent from CHANGELOG.md):
- Added Bun and Deno runtime support (filtering, test summaries)
- Bug fixes for find, diff, discover, runner, and bun/deno tool routing
- Telemetry improvements (consent state distinction, salt labeling)

**Confidence Assessment**:
- **Identity/Metadata**: high — version, license, and build info directly from Cargo.toml and CHANGELOG
- **Features**: high — comprehensive feature list extracted verbatim from README and verified against command taxonomy
- **Technical Architecture**: high — design principles, module organization, and hook strategy directly quoted from official ARCHITECTURE.md
- **Installation & Usage**: high — all installation methods and command examples directly from official README
- **Limitations**: medium — documented limitations found in README; however, no explicit list of known bugs or edge cases in reviewed sources
- **Relevance to Claude Code Development**: high — direct integration via PreToolUse hook documented in README and ARCHITECTURE.md

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [abtop](./abtop.md) | developer-tools | real-time token and context window consumption tracking for Claude Code sessions |
| [sigmap](./sigmap.md) | developer-tools | AI context engine achieving 40–98% token reduction via signature extraction (complementary compression strategy) |
| [grepai](./grepai.md) | developer-tools | semantic code search for AI agents that reduces context overhead RTK targets |
| [repomix](./repomix.md) | developer-tools | prepares codebases into AI-friendly formats (complements RTK's output compression) |
| [jina-reader](./jina-reader.md) | developer-tools | URL-to-Markdown API for ingesting web content into agent context (RTK filters the ingested data) |
| [claude-pilot](./claude-pilot.md) | developer-tools | quality enforcement layer for Claude Code using hook-based automation (shares PreToolUse hook infrastructure with RTK) |
| [biome](./biome.md) | developer-tools | Rust-based formatter and linter (shared technology; complementary developer-workflow tool) |
| [everything-claude-code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | comprehensive Claude Code agent harness with 65+ skills including RTK context compression integration |
