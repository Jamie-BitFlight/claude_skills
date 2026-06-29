---
title: "Biome"
research_date: "2026-02-23"
source_url: "https://biomejs.dev"
github_url: "https://github.com/biomejs/biome"
version_at_research: "v2.4.3"
license: "MIT OR Apache 2.0"
last_verified: "2026-02-23"
version_at_verification: "v2.4.3"
next_review: "2026-05-23"
---

## Overview

Biome is a high-performance, all-in-one toolchain for web projects built in Rust that combines formatting (97% Prettier compatibility), linting (450+ rules from ESLint/typescript-eslint), and import organization into a single binary. It runs ~35× faster than Prettier, requires zero configuration to get started, provides first-class LSP support for editor integration, and in v2 introduced type-aware linting without requiring the TypeScript compiler — making it a drop-in replacement for the ESLint + Prettier toolchain.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Maintaining separate ESLint and Prettier configs with frequent version conflicts | Single `biome check` command runs formatting, linting, and import organization together with a unified `biome.json` config |
| Slow CI times from running ESLint and Prettier over large codebases | Rust-based parallel processing runs ~35× faster than Prettier and significantly faster than ESLint |
| Type-aware linting requires slow TypeScript compiler invocation | v2 type inference engine works independently of the TypeScript compiler, providing type-aware rules without `tsc` overhead |
| ESLint + Prettier produce obscure, hard-to-act-on errors | Biome outputs detailed, contextualized diagnostics with exact source locations and safe-fix suggestions |
| Different tooling for different JS/TS languages (JSX, TSX, CSS, GraphQL) | First-class support for JS, TS, JSX, TSX, JSON, HTML, CSS, GraphQL in a single tool |
| Configuring and maintaining lint rules across a monorepo | Nested `biome.json` configuration files are fully supported with per-package overrides in v2 |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | ~23.8K | 2026-02-23 |
| Contributors | 18 core + active community | 2026-02-23 |
| Latest Release | v2.4.3 | 2026-02-23 |
| Formatting Speed | ~35× faster than Prettier (171K LOC, 2104 files) | 2026-02-23 |
| Prettier Compatibility | 97% | 2026-02-23 |
| Lint Rules | 450+ (from ESLint, typescript-eslint, and others) | 2026-02-23 |
| Supported Languages | JS, TS, JSX, TSX, JSON, HTML, CSS, GraphQL | 2026-02-23 |

---

## Key Features

### Formatting

- 97% compatibility with Prettier for JS, TS, JSX, TSX, JSON, CSS, GraphQL, HTML
- Formats malformed code during editing via LSP
- ~35× faster than Prettier on large codebases
- Configurable indent style (space/tab), indent width, line width, quote style, trailing commas, semicolons

### Linting

- 450+ rules sourced from ESLint, typescript-eslint, and additional sources
- Rule categories: correctness, complexity, style, suspicious, performance, accessibility, security, nursery
- Safe and unsafe fix suggestions with one-command auto-apply
- Detailed diagnostic output showing exact problem location and remediation

### Type-Aware Linting (v2)

- New type inference engine independent of the TypeScript compiler
- Multi-file analysis: scans project and `node_modules` to build type graph
- ~75% detection coverage vs `typescript-eslint` for rules like `noFloatingPromises` with no `tsc` overhead
- Opt-in via `project` domain rules; does not affect performance for non-type-aware linting
- Full monorepo support: uses the correct `package.json` per package

### Import Organization

- Automatic import sorting and deduplication via `assist.actions.source.organizeImports`
- Controlled via `biome check --write` or as part of CI via `biome ci`

### Editor Integration

- First-party extensions for VS Code, IntelliJ, and Zed
- Community extensions for Vim, Neovim, Sublime Text
- LSP server with full error recovery and format-on-save support
- Formats and lints malformed code as you type

### Zero-Config & Standalone

- Works out of the box with `npx @biomejs/biome check --write ./src`
- Optional `biome.json` for project-level configuration (`npx @biomejs/biome init`)
- Standalone binary available without Node.js
- Git VCS integration: respects `.gitignore` patterns via `vcs.useIgnoreFile`

### CI Integration

- `biome ci` command enforces code quality in CI pipelines (equivalent to `biome check` without writes)
- GitHub Actions and GitLab CI recipes provided in official documentation
- Exits with non-zero status on any violation for gate enforcement

---

## Technical Architecture

### Core Design

Biome is built in Rust with an architecture inspired by `rust-analyzer`, providing:

- **Shared parser**: A single parser produces a full-fidelity syntax tree (including trivia like whitespace and comments) used by both the formatter and linter — no double-parsing overhead
- **Error recovery**: Parser continues after syntax errors, enabling formatting and linting of malformed code
- **Parallel execution**: Files are processed in parallel using Rayon-based work-stealing
- **Single binary**: All tools ship in one executable, eliminating version coordination between tools

### v2 File Scanner

<eg>
biome check --write ./src
    ↓
File Scanner (opt-in for project domain rules)
    ↓ discovers all .js/.ts/.jsx/.tsx files
Parallel parser farm (one thread per CPU core)
    ↓ produces full-fidelity CSTs
Formatter pass → emit formatted text
    ↓
Linter pass (per-file rules) → collect diagnostics
    ↓
Type Inference Engine (project domain rules only)
    ↓ queries multi-file type graph
Type-aware lint rules → additional diagnostics
    ↓
Write fixes + report summary
</eg>

### Configuration Hierarchy

<eg>
biome.json (project root)
    ↓ overridden by
packages/pkg-a/biome.json (nested config, v2+)
    ↓ overridden by
CLI flags
    ↓ overridden by
BIOME_* environment variables
</eg>

---

## Installation & Usage

### Installation

```bash
# As a dev dependency (recommended)
npm i -D -E @biomejs/biome

# pnpm
pnpm add -D -E @biomejs/biome

# Standalone binary (no Node.js required)
# See: https://biomejs.dev/guides/manual-installation/
```

### Quick Start

```bash
# Initialize biome.json
npx @biomejs/biome init

# Format all files
npx @biomejs/biome format --write ./src

# Lint with safe auto-fixes
npx @biomejs/biome lint --write ./src

# Format + lint + organize imports (recommended)
npx @biomejs/biome check --write ./src

# CI enforcement (no writes, exits non-zero on violations)
npx @biomejs/biome ci ./src
```

### Example biome.json

```json
{
  "$schema": "https://biomejs.dev/schemas/2.4.3/schema.json",
  "vcs": { "enabled": true, "clientKind": "git", "useIgnoreFile": true },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "linter": {
    "enabled": true,
    "rules": { "recommended": true }
  },
  "javascript": {
    "formatter": { "quoteStyle": "single", "semicolons": "always" }
  },
  "assist": {
    "enabled": true,
    "actions": { "source": { "organizeImports": "on" } }
  }
}
```

### Migrate from ESLint + Prettier

```bash
# Automated migration command
npx @biomejs/biome migrate eslint --write
npx @biomejs/biome migrate prettier --write
```

---

## Relevance to Claude Code Development

### Applications

**This repository already uses Biome** (`biome.json` at repo root) for JS/TS linting and formatting via CI (`.github/workflows/code-quality.yml`) and pre-commit hooks (`.pre-commit-config.yaml`). The current config uses v2.3.13 schema with recommended rules and single-quote JS formatting.

**Enforcing Code Quality in Hook Scripts**:
- Claude Code hooks (`.claude/hooks/*.cjs`, `plugins/*/hooks/*.cjs`) are CommonJS Node.js files that benefit from Biome's linting and formatting
- `biome check --write` can be added to the pre-commit hook pipeline for hook script quality

**CI Quality Gate Integration**:
- `npx @biomejs/biome ci` already runs in CI and can be extended with project-domain type-aware rules
- Exit-code-based gate pattern directly supports Claude Code's pre-push quality enforcement

### Patterns Worth Adopting

**Single-Tool Simplicity over Toolchain Composition**:
- Biome's single-binary approach (formatter + linter + import organizer) eliminates the "N tools, N config files, N version conflicts" problem
- Skills and plugins can document "use `biome check --write` for JS/TS" as the single authoritative command

**Zero-Config First, Config When Needed**:
- Biome works with zero configuration — a pattern worth applying to Claude Code plugin defaults
- Optional `biome.json` only when project-level overrides are necessary

**Opt-In Performance Cost**:
- v2 type inference is opt-in, not default — isolating expensive multi-file scans to rules that need them
- Pattern: define expensive analysis as opt-in with explicit user consent (analogous to `--all-files` vs targeted pre-commit runs)

**Unified CLI Verbs**:
- `format`, `lint`, `check` (all), `ci` (CI-only no-write) provide clear semantic separation
- Pattern for skill CLI design: discrete verbs for distinct phases of a workflow

### Integration Opportunities

**Upgrade biome.json to v2.4.3 Schema**:
- Current repo config references schema `2.3.13`; upgrading to `2.4.3` enables access to new v2 rules and HTML support
- Run `npx @biomejs/biome migrate --write` to auto-apply breaking config changes

**Enable Type-Aware Rules**:
- Add `project` domain rules to `biome.json` to detect floating promises, undefined type access, and other type errors in hook scripts
- Provides ESLint `@typescript-eslint/no-floating-promises` equivalent without TypeScript compiler dependency

**Claude Code Plugin for Biome Diagnostics**:
- A skill that runs `biome check --json ./src` and parses the structured JSON output to present lint findings in a structured agent-readable format
- Integration point: `plugins/holistic-linting/skills/biome-diagnostics/`

**Pre-commit Hook for Hook Scripts**:
- Add `npx @biomejs/biome check --write` as a pre-commit stage specifically for `.cjs` hook files
- Ensures all Claude Code hooks maintain consistent style without separate ESLint config

---

## References

- [Biome Official Website](https://biomejs.dev) (accessed 2026-02-23)
- [biomejs/biome GitHub Repository](https://github.com/biomejs/biome) (accessed 2026-02-23)
- [Biome Getting Started Guide](https://biomejs.dev/guides/getting-started/) (accessed 2026-02-23)
- [Biome v2 Release Announcement](https://biomejs.dev/blog/biome-v2/) (accessed 2026-02-23)
- [Biome v2.3 Release - Vue/Svelte/Astro Support](https://biomejs.dev/blog/biome-v2-3/) (accessed 2026-02-23)
- [Biome Roadmap 2025](https://biomejs.dev/blog/roadmap-2025/) (accessed 2026-02-23)
- [Biome Linter Rules Reference](https://biomejs.dev/linter/) (accessed 2026-02-23)
- [Biome Configuration Reference](https://biomejs.dev/reference/configuration) (accessed 2026-02-23)

---
