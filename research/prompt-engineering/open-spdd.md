# OpenSPDD

## Identity

**Name**: OpenSPDD (Structured Prompt-Driven Development)
**Repository**: <https://github.com/gszhangwei/open-spdd>
**Source URL**: <https://github.com/gszhangwei/open-spdd>
**Research Date**: 2026-09-11
**Version at Research**: unversioned (no tags; development in progress)
**License**: MIT
**Author**: gszhangwei
**Primary Language**: Go 1.23
**Latest Commit**: As of shallow clone: Merge pull request #19 (star-history-chart fix)
**Release Versions**: Not yet versioned with tags (development in progress)

## Overview

"OpenSPDD is a methodology and cross-platform CLI tool for the AI coding era. It upgrades AI coding prompts from 'disposable inputs' to 'executable design contracts' with bidirectional synchronization between design and implementation" (README.md, line 17). The tool provides a structured framework for expressing design intent, architectural decisions, and execution constraints in a format that AI coding agents can reliably consume and maintain over time.

## Problem Addressed

Typical AI coding workflows generate plan documents with fundamental limitations:

| Problem | OpenSPDD's Approach |
|---------|-------------------|
| Plans are task lists with no binding constraints | REASONS Canvas is a design contract with explicit norms and safeguards |
| No constraints on AI — AI improvises freely | Explicit constraints define "how" (Norms) and "what not to do" (Safeguards) |
| High-level detail ("Create BillingService") | Precise details — method signatures, parameters, error handling, dependency injection patterns |
| No traceability; docs don't sync with code | Bidirectional sync via `/spdd-sync` command keeps design and implementation aligned |
| Vague validation ("done when complete") | Explicit validation — exact error messages, HTTP status codes in Safeguards |
| Implicit dependencies — AI infers them | Explicit execution order defined in Operations |

## Key Features

### The REASONS Canvas Framework

OpenSPDD's core is a 7-dimensional structured design framework spanning three layers:

**Strategic Layer (Why/What)**:
- **Requirements (R)**: Business goals and scope
- **Entities (E)**: Domain model expressed as Mermaid class diagrams
- **Approach (A)**: Solution strategy and trade-offs

**Implementation Layer (How)**:
- **Structure (S)**: Architecture, inheritance, dependencies
- **Operations (O)**: Precise implementation tasks in order, including method signatures and error handling

**Constraint Layer (Boundary)**:
- **Norms (N)**: Coding standards and patterns to follow
- **Safeguards (S)**: Constraints and guardrails defining what must not be done

This framework acts as both a checklist (reminding developers to consider all dimensions) and a consumable artifact (executable by AI agents).

### Core Commands

"Five core commands comprise the SPDD workflow" (README.md, lines 293–300):

1. **`/spdd-analysis`**: Strategic analysis of requirements — decomposes business requirements into concepts, risks, and design considerations
2. **`/spdd-reasons-canvas`**: Generates structured REASONS Canvas design documents from analysis
3. **`/spdd-generate`**: Generates code from structured SPDD prompt files, following the contract defined in REASONS Canvas
4. **`/spdd-prompt-update`**: Updates existing SPDD prompt with new requirements
5. **`/spdd-sync`**: Reverse-synchronizes code changes back to SPDD prompt files, keeping design documents current

### Optional Commands (Beta)

Available via `openspdd generate <command>`:

- **`spdd-story`**: Decomposes feature requirements into INVEST-compliant stories with acceptance criteria
- **`spdd-code-review`**: Reviews code against REASONS Canvas, detecting intent drift and violations
- **`spdd-api-test`**: Generates self-contained shell scripts with cURL commands for API testing
- **`spdd-reverse`**: Reverse-engineers existing code into a REASONS Canvas prompt for legacy onboarding

### Cross-Platform Toolchain Integration

"Supports Cursor, Claude Code, GitHub Copilot, Antigravity, OpenCode, and Codex" (README.md, line 96). Each tool receives auto-generated commands in its native format:

- **Cursor**: `.cursor/commands/spdd-*.md`
- **Claude Code**: `.claude/commands/spdd-*.md`
- **GitHub Copilot**: `.github/copilot-prompts/spdd-*.md`
- **Antigravity**: `.antigravity/commands/spdd-*.md`
- **OpenCode**: `.opencode/commands/spdd-*.md` (command naming follows markdown filename)
- **Codex**: `.agents/skills/<id>/SKILL.md` (project-scoped skill bundles per agentskills.io standard)

Auto-detection identifies the AI tool based on marker files (`.cursor/`, `.claude/`, `.github/copilot-instructions.md`, etc.) and generates appropriate templates.

## Technical Architecture

### Core Dependencies

- **charmbracelet/huh** (v0.6.0): Interactive form/menu UI for command selection
- **fatih/color** (v1.18.0): Terminal color output
- **spf13/cobra** (v1.8.1): CLI framework for command structure and flags

The full dependency tree includes charmbracelet's terminal UI ecosystem (bubbles, bubbletea, lipgloss) and related terminal/OS abstractions.

### CLI Command Structure

The tool follows a hierarchical command structure (inferred from cmd/ directory):

- **`init`**: Auto-detects AI tool and initializes the project with command templates
- **`generate`**: Generates SPDD command files (interactive or specified)
- **`list`**: Lists available commands with optional filtering by category
- **`version`**: Prints installed version
- **`uninstall`**: Safely removes the binary and first-run markers
- **`pathcheck`**: Verifies PATH configuration and provides shell-specific hints

### Single Binary Distribution

"All templates embedded via Go's embed directive" (README.md, line 98). This means SPDD templates for all supported tools are compiled into the binary, eliminating runtime file lookups and enabling single-file installation.

### Workflow Engine

The `/spdd-sync` command implements bidirectional synchronization: it parses generated code, detects deviations from the REASONS Canvas specification, and updates the Canvas to reflect the actual implementation. This prevents design documents from becoming stale.

## Installation & Usage

### Installation Methods

1. **Homebrew (macOS/Linux)**: `brew install gszhangwei/tools/openspdd` or `brew tap gszhangwei/tools && brew install openspdd`
2. **Go install**: `go install github.com/gszhangwei/open-spdd/cmd/openspdd@latest` (requires Go 1.23+; installs to `$(go env GOPATH)/bin/openspdd`)
3. **Installer script**: Clone repo and run `./scripts/install.sh [version-tag]`
4. **Manual download**: GitHub Releases page (binary archives for Linux, macOS, Windows)

The first run of `openspdd` auto-detects PATH and prints shell-specific setup commands for `.bashrc` / `.zshrc`.

### Uninstall

`openspdd uninstall` detects installation method (Homebrew or go install) and removes the binary. Supports `--dry-run` (preview), interactive confirmation (default), and `--yes` (non-interactive).

### Quick Start Workflow

```bash
# Initialize project (auto-detects AI tool)
openspdd init

# Generate all default SPDD commands
openspdd generate --all

# In AI coding tool, follow the workflow:
/spdd-analysis @requirements/feature.md          # Strategic analysis
/spdd-reasons-canvas @spdd/analysis/xxx.md       # Generate REASONS Canvas
/spdd-generate @spdd/prompt/xxx.md               # Generate code from Canvas
/spdd-sync @spdd/prompt/xxx.md                   # Sync code changes back
```

For simpler features, skip Step 1 and provide requirements directly to `/spdd-reasons-canvas`.

### Available Commands Listing

```bash
openspdd list              # List default commands
openspdd list --optional   # List beta/optional commands
openspdd list --all        # List all commands
openspdd list -c Development  # Filter by category
```

## Key Design Insights

### Capability vs. Control

"There is a class of control needs that capability improvements alone cannot eliminate: when multiple 'correct' solutions exist, choosing which one is a human trade-off decision, not an AI logical inference" (design-philosophy.md, lines 31–33).

OpenSPDD addresses the control dimension — how to ensure AI's understanding aligns with design intent, how to pick the one solution the project actually needs among multiple technically correct options, and how to define what must not be done. This is distinct from capability improvements (larger context windows, better inference), which address understanding but not decision-making.

### Structured Prompts vs. Codebase Scanning

Code records "what is," not "what should be" and lacks "why." Codebase scanning cannot recover lost design intent or distinguish deliberate architectural choices from historical compromises. "Codebase scanning is one of the most important capabilities of current AI coding tools. Understanding its boundaries helps us work with it more effectively" (design-philosophy.md, lines 136–197). REASONS Canvas complements scanning by externalizing intent in a structured, versionable artifact.

### Bidirectional Synchronization Challenge

"Do structured prompts themselves also become outdated?" (design-philosophy.md, line 380). The design philosophy acknowledges that specs become stale when code changes. Current mitigation: manually run `/spdd-sync` after code review to detect and update spec changes. Future direction: automated sync detection after each code update.

## Limitations and Caveats

### Not Suitable For

- **Rapid prototyping**: Overhead too high for exploratory, disposable code
- **One-off scripts**: ROI too low for use-and-discard functionality
- **Simple tasks**: Fixing typos, adding logs, simple changes don't justify structured overhead

Structured prompts are for "core business logic, systems requiring long-term maintenance and multi-person collaboration" (design-philosophy.md, lines 365–378).

### Spec Drift Risk

Bidirectional sync is manual and convention-based, not enforced. If code changes are made without running `/spdd-sync`, the REASONS Canvas diverges from implementation. This is mitigated through team discipline, not guaranteed by the tool.

### Maturity and Versioning

The repository has no release tags or version numbers (as of shallow clone). Commands marked "Optional (Beta)" — `spdd-story`, `spdd-code-review`, `spdd-api-test`, `spdd-reverse` — are not installed by default and may change. The tool is "still under continuous iteration" (design-philosophy.md, line 451).

## Relevance to Claude Code Development

OpenSPDD is highly relevant to Claude Code as a framework for:

1. **Structured prompt design**: Provides a reusable template system for expressing design intent in a machine-parseable format
2. **Cross-tool compatibility**: Demonstrates how a single design methodology can be compiled into tool-specific command formats (CLAUDE.md, .claude/commands/, etc.)
3. **Bidirectional synchronization patterns**: The `/spdd-sync` workflow offers a reference implementation for keeping design documents and code aligned — a known challenge in agent-driven development
4. **Control-layer design**: Separates capability improvements from control problems, directly applicable to Claude Code's evolving agent coordination needs

For Claude Code specifically, REASONS Canvas is complementary to CLAUDE.md (repo-level conventions) — Canvas works at feature-level granularity while CLAUDE.md covers project-level patterns.

## References

- **GitHub Repository**: <https://github.com/gszhangwei/open-spdd> (accessed 2026-09-11) (primary source for README, LICENSE, design-philosophy.md, go.mod)
- **README.md**: <https://github.com/gszhangwei/open-spdd/blob/main/README.md> (accessed 2026-09-11) — line references throughout (features, installation, usage, supported environments)
- **docs/design-philosophy.md**: <https://github.com/gszhangwei/open-spdd/blob/main/docs/design-philosophy.md> (accessed 2026-09-11) — comprehensive exploration of capability vs. control, codebase scanning limitations, and structured prompt philosophy
- **Installation**: Homebrew tap: <https://github.com/gszhangwei/tools> (accessed 2026-09-11) (formula provides installation)
- **Build Requirements**: Go 1.23+ (from go.mod, accessed 2026-09-11)

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|-----------|---|---|
| Identity/Metadata | high | 2026-09-11 | MIT license, Go 1.23 from go.mod; no versioned releases yet |
| Overview/Problem Addressed | high | 2026-09-11 | Direct quotes from README.md and design-philosophy.md |
| Key Features | high | 2026-09-11 | REASONS Canvas, core commands, optional commands extracted from README |
| Technical Architecture | high | 2026-09-11 | Dependency analysis from go.mod; CLI structure from cmd/ directory inspection |
| Installation & Usage | high | 2026-09-11 | Installation methods and quick start from README.md |
| Design Insights | high | 2026-09-11 | Philosophical foundations from design-philosophy.md |
| Limitations | medium | 2026-09-11 | Maturity and spec-drift challenges inferred from source; not explicitly documented as limitations |
| Relevance | medium | 2026-09-11 | Relevance to Claude Code assessed from framework design; specific Claude Code integration not yet demonstrated in repository |

**Version at Verification**: unversioned (no tags at time of research)

**Next Review**: 2026-12-11 (3 months)

**Review Trigger**: Major version release, significant API changes to command structure, or new integration with Claude Code toolchain.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Spec Workflow MCP](../mcp-ecosystem/spec-workflow-mcp.md) | mcp-ecosystem | spec-driven development workflow with Requirements→Design→Tasks approval gates and real-time dashboard |
| [System Prompts for AI Tools](./system-prompts-ai-tools.md) | prompt-engineering | explores system prompt design patterns for AI coding tools and agents |
| [Prompt Engine](./prompt-engine.md) | prompt-engineering | automated prompt generation tool complementing structured prompt design methodology |
| [Google AI Studio](./google-ai-studio.md) | prompt-engineering | interactive playground for designing and testing prompts for AI agents with 20+ models |
| [OpenSpec MCP](../mcp-ecosystem/openspec-mcp.md) | mcp-ecosystem | MCP implementation of spec-driven development with 50+ tools and approval state machine |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | comprehensive Claude Code agent harness with 65+ skills for structured orchestration workflows |
| [Claude Code Harness](../agent-frameworks/claude-code-harness.md) | agent-frameworks | foundational Claude Code control framework providing 5-verb design methodology and guardrails |
| [Claude Pilot](../developer-tools/claude-pilot.md) | developer-tools | spec-driven enforcement layer for Claude Code with design specification support and /spec workflow |
