---
title: wrkflw — GitHub Actions Workflow Validator and Executor
resource-type: developer-tool
category: developer-tools
language: Rust
tags:
  - github-actions
  - workflow-validation
  - local-testing
  - ci-cd
  - command-line-tool
keywords:
  - workflow validation
  - local execution
  - docker integration
  - expression evaluation
  - matrix builds
  - reusable workflows
created-date: 2026-04-25
updated-date: 2026-04-25
research-version: 1.0
status: current
---

# wrkflw — GitHub Actions Workflow Validator and Executor

## Overview

wrkflw is a Rust command-line tool that enables developers to validate and execute GitHub Actions workflows locally before pushing to GitHub. It provides a complete local development environment for testing CI/CD pipelines with support for multiple execution runtimes (Docker, Podman, pure emulation, and sandboxed secure emulation) and includes a terminal UI for interactive workflow inspection and debugging.

**Primary use case**: Test GitHub Actions workflows on a developer's machine to catch errors early, reduce CI/CD iteration cycles, and debug workflow logic without requiring commits and GitHub Actions runs.

**Repository**: <https://github.com/bahdotsh/wrkflw>
**License**: MIT
**Language**: Rust
**Latest version**: 0.8.0 (released 2026-04-22)
**Installation**: `cargo install wrkflw` or `brew install wrkflw`

---

## Problem Addressed

GitHub Actions workflows can only be tested on GitHub through CI/CD runs. This creates a costly feedback loop: developers must commit changes, push to GitHub, and wait for Actions to run before discovering syntax errors, logic bugs, or action compatibility issues. wrkflw eliminates this cycle by executing workflows locally with complete fidelity to GitHub's runtime behavior.

**Specific problems solved**:

1. **Silent workflow failures**: Workflows with `paths:` filters would fail silently due to unspecified change sets. wrkflw's strict-filter mode (default in v0.8.0) now rejects ambiguous invocations with clear error messages.
2. **Expression evaluation errors**: Complex `${{ ... }}` expressions are now evaluated locally with support for `toJSON`, `fromJSON`, `contains`, `startsWith`, and context-aware variable substitution.
3. **Action compatibility**: Container actions, JavaScript actions, composite actions, and reusable workflows execute locally with output propagation, revealing integration issues before CI/CD runs.
4. **Matrix build complexity**: Full matrix expansion support (`include`, `exclude`, `fail-fast`) allows testing parametrized workflows locally.

---

## Key Statistics

| Metric | Value | Date |
|--------|-------|------|
| Latest version | 0.8.0 | 2026-04-22 |
| Repository commits (shallow) | 1 | 2026-04-25 |
| Codebase size | 44,819 lines of code | 2026-04-02 |
| Supported platforms | Linux, macOS, Windows (via Docker) | current |
| Installation methods | cargo, Homebrew, source build | current |

---

## Key Features

### 1. Workflow Validation

Syntax checking and structural validation with CI/CD-friendly exit codes:

- **JSON Schema validation**: Validates GitHub Actions workflow YAML against official JSON Schema
- **Composite action input cross-checking**: Ensures all required inputs to composite actions are provided and match declared types
- **Exit codes**: `0` = all valid, `1` = validation failures, `2` = usage error
- **Verbose output**: Optional detailed error reporting via `--verbose` flag

**Example**:
```bash
wrkflw validate .github/workflows/ci.yml
wrkflw validate path/to/workflows/ --verbose
```

### 2. Local Workflow Execution

Execute workflows with multiple runtime modes:

- **Docker** (default): Full container isolation, closest to GitHub runners
- **Podman**: Rootless containers, no daemon required, security-conscious environments
- **Emulation**: Direct host execution, no containers needed, fastest for quick testing
- **Secure Emulation**: Sandboxed host processes with filesystem/network restrictions for untrusted workflows

**Example**:
```bash
wrkflw run .github/workflows/ci.yml                  # Docker (default)
wrkflw run --runtime podman .github/workflows/ci.yml # Podman
wrkflw run --runtime emulation .github/workflows/ci.yml
```

### 3. Job and Step Execution Engine

- **Job dependency resolution**: Automatically orders jobs based on `needs` declarations with parallel execution of independent jobs
- **Individual job selection**: Run specific jobs via `--job <name>` or TUI selection
- **Job listing**: `wrkflw run --jobs` displays all jobs in a workflow without executing
- **Parallel execution**: Independent jobs run concurrently; dependent jobs wait for `needs` predecessors

### 4. Expression Evaluator

Evaluates GitHub Actions `${{ ... }}` expressions with comprehensive function support:

- **Functions**: `toJSON`, `fromJSON`, `contains`, `startsWith`, `success()`, `failure()`, `hashFiles()`, and more
- **Context variables**: `github`, `env`, `matrix`, `secrets`, `needs`, `steps` contexts
- **String interpolation**: Variable substitution across all workflow fields
- **Type coercion**: Automatic conversion for condition evaluation

### 5. Trigger-Aware Filtering

New in v0.8.0: Skip workflows that wouldn't trigger for a given event and change set.

- **Diff detection**: Auto-detect changed files from git (vs `origin/HEAD`, `main`, `master`, or `HEAD~1`)
- **Custom change sets**: Supply changed files explicitly via `--changed-files`
- **Event simulation**: Simulate `push`, `pull_request`, and other GitHub event types
- **Strict mode** (default): Requires explicit change set input to prevent silent failures
- **Base branch specification**: Required for `pull_request` events to evaluate `branches:` filters correctly

**Example**:
```bash
wrkflw run --diff --event push .github/workflows/ci.yml
wrkflw run --event pull_request --base-branch main --diff .github/workflows/ci.yml
wrkflw run --event push --changed-files src/main.rs,Cargo.toml .github/workflows/ci.yml
```

### 6. Watch Mode

Automatically rerun workflows on file changes with trigger-aware re-execution:

```bash
wrkflw watch
wrkflw watch --event pull_request --base-branch main --max-concurrency 2
wrkflw watch --ignore-dir .terraform --ignore-dir coverage
```

### 7. Interactive Terminal UI (TUI)

Rich terminal interface with 7 tabs:

| Tab | Purpose |
|-----|---------|
| **Workflows** | Select and toggle multiple workflows, view status |
| **Execution** | Run/validate selected workflows, view progress |
| **DAG** | Visualize job dependency graph |
| **Logs** | Search, filter, and navigate execution logs |
| **Trigger** | Simulate event context, edit inputs, preview curl |
| **Secrets** | Manage secrets configuration |
| **Help** | View keybindings and usage |

### 8. Action Support

- **Docker container actions**: Run actions packaged as Docker images
- **JavaScript actions**: Execute `.js`/`.ts` action files
- **Composite actions**: Multi-step actions with output propagation to caller
- **Local actions**: Reference local action directories from workflow

### 9. Reusable Workflows

Execute and validate reusable workflows with full output propagation:

```yaml
jobs:
  call-local:
    uses: ./.github/workflows/shared.yml
    with:
      foo: bar

  call-remote:
    uses: my-org/my-repo/.github/workflows/shared.yml@v1
    secrets:
      token: ${{ secrets.MY_TOKEN }}
```

### 10. Artifacts, Cache, and Inter-Job Outputs

- **Upload/Download artifacts**: `actions/upload-artifact` and `actions/download-artifact` with shared artifact stores
- **Action caching**: `actions/cache` with cache key evaluation
- **Inter-job outputs**: `needs.<id>.outputs.*` with context variable substitution
- **GitHub context emulation**: `GITHUB_OUTPUT`, `GITHUB_ENV`, `GITHUB_PATH`, `GITHUB_STEP_SUMMARY` environment files

### 11. Matrix Builds

Full matrix expansion support:

- **Include/exclude lists**: Add or remove matrix combinations
- **Fail-fast control**: Optionally cancel remaining jobs on first failure
- **Max parallel**: Limit concurrent job executions
- **Variable interpolation**: Access matrix variables in steps and job properties

### 12. Secrets Management

Multiple storage and retrieval providers:

- **Environment variables**: `$GITHUB_TOKEN` or other env secrets
- **File-based**: JSON, YAML, or .env format from `~/.wrkflw/secrets.yml`
- **HashiCorp Vault**: Integration with Vault server
- **AWS Secrets Manager**: Fetch secrets from AWS
- **Azure Key Vault**: Fetch from Azure
- **Google Cloud Secret Manager**: Fetch from GCP
- **Encryption**: AES-256-GCM encrypted storage
- **Masking**: Automatic replacement of secret values in logs

### 13. Remote Triggering

Trigger `workflow_dispatch` runs on GitHub or GitLab:

```bash
# GitHub (requires GITHUB_TOKEN)
wrkflw trigger workflow-name --branch main --input key=value

# GitLab (requires GITLAB_TOKEN)
wrkflw trigger-gitlab --branch main --variable key=value
```

### 14. GitLab CI Support

Validate and trigger GitLab CI pipelines:

```bash
wrkflw validate .gitlab-ci.yml --gitlab
```

---

## Technical Architecture

### Core Components (Rust Crates Workspace)

wrkflw is structured as a Rust Cargo workspace with 15 specialized crates. The workspace includes:

- **wrkflw**: CLI binary and library entry point — main interface for all commands
- **wrkflw-executor**: Workflow execution engine — Docker/Podman/emulation runtime selection and execution orchestration
- **wrkflw-parser**: YAML parsing and JSON Schema validation — GitHub/GitLab workflow file parsing
- **wrkflw-evaluator**: Structural evaluation of workflow files — pre-execution syntax and structure validation
- **wrkflw-validators**: Validation rules — job, step, trigger, matrix validation rules
- **wrkflw-runtime**: Container and emulation abstractions — runtime implementation (Docker, Podman, emulation, secure sandbox)
- **wrkflw-trigger-filter**: Event and change-set matching — parses `on:` blocks and matches against simulated events
- **wrkflw-watcher**: File change monitoring — `wrkflw watch` file monitoring and trigger-aware re-execution
- **wrkflw-ui**: Terminal UI (ratatui-based) — interactive TUI with 7 tabs
- **wrkflw-models**: Shared data structures — `ValidationResult`, workflow models, GitLab models
- **wrkflw-matrix**: Matrix expansion — `include`, `exclude`, `fail-fast`, `max-parallel` logic
- **wrkflw-secrets**: Secrets management — multiple provider backends, encryption, masking
- **wrkflw-github**: GitHub API integration — list/trigger workflows on GitHub
- **wrkflw-gitlab**: GitLab API integration — trigger pipelines on GitLab
- **wrkflw-logging**: In-memory logging — thread-safe log aggregation for TUI/CLI

### Data Flow

1. **Input**: Workflow YAML file + optional event/change-set context
2. **Parse**: YAML → internal model via `wrkflw-parser` + JSON Schema validation
3. **Evaluate**: Structural checks via `wrkflw-evaluator` and `wrkflw-validators`
4. **Filter** (optional): Trigger-aware filtering via `wrkflw-trigger-filter` against `on:` block
5. **Execute** (if running): Job graph execution via `wrkflw-executor` with dependency resolution, runtime selection, expression evaluation, action resolution, and artifact/cache management
6. **Log**: Real-time logs aggregated into `wrkflw-logging` for TUI display or CLI output
7. **Report**: Validation results (exit codes 0/1/2) or execution summary with job statuses

### Expression Evaluator

The executor contains a comprehensive expression evaluator supporting:

- **Functions**: `toJSON()`, `fromJSON()`, `contains()`, `startsWith()`, `endsWith()`, `format()`, `join()`, `split()`, `replace()`, `hashFiles()`, `success()`, `failure()`, `always()`, `cancelled()`, `fromJson()`, `toJson()`
- **Context objects**: `github`, `env`, `matrix`, `secrets`, `needs`, `steps`, `job`, `runner`, `inputs`
- **Operators**: Logical (`&&`, `||`, `!`), comparison (`==`, `!=`, `<`, `>`, etc.), ternary (`? :`)
- **Type coercion**: Automatic string ↔ boolean conversion

---

## Installation & Usage

### Installation

```bash
# Via cargo (Rust package manager)
cargo install wrkflw

# Via Homebrew (macOS, Linux)
brew install wrkflw

# Build from source
git clone https://github.com/bahdotsh/wrkflw.git
cd wrkflw
cargo build --release
```

### Quick Start

```bash
# Launch TUI (auto-detects .github/workflows)
wrkflw

# Validate all workflows
wrkflw validate

# Run a specific workflow
wrkflw run .github/workflows/ci.yml

# Watch for changes and rerun
wrkflw watch

# List all detected workflows
wrkflw list
```

### Validation Examples

```bash
# Validate specific workflow
wrkflw validate .github/workflows/ci.yml

# Validate directory
wrkflw validate .github/workflows/

# Verbose output
wrkflw validate --verbose .github/workflows/ci.yml

# GitLab pipelines
wrkflw validate .gitlab-ci.yml --gitlab
```

### Execution Examples

**Basic execution**:
```bash
wrkflw run .github/workflows/ci.yml
```

**With runtime selection**:
```bash
wrkflw run --runtime podman .github/workflows/ci.yml
wrkflw run --runtime secure-emulation .github/workflows/ci.yml
```

**Single job**:
```bash
wrkflw run --job build .github/workflows/ci.yml
wrkflw run --jobs .github/workflows/ci.yml  # List only
```

**Trigger-aware execution (v0.8.0)**:
```bash
# Auto-detect changed files from git
wrkflw run --diff --event push .github/workflows/ci.yml

# Supply explicit change set
wrkflw run --event push --changed-files src/main.rs,Cargo.toml .github/workflows/ci.yml

# Simulate pull_request
wrkflw run --event pull_request --base-branch main --diff .github/workflows/ci.yml
```

---

## Known Limitations

The following features are documented as not yet supported in wrkflw:

1. **GitHub encrypted secrets**: Secrets stored in GitHub repository settings are not accessible. Use local secrets via env vars, files, or external secret managers (Vault, AWS, Azure, GCP).
2. **Fine-grained permissions**: GitHub Actions fine-grained token permissions are not emulated; all actions run with full permission context.
3. **Event triggers beyond `workflow_dispatch`**: Remote `trigger` command only supports `workflow_dispatch` events, not `push`, `pull_request`, or other event types.
4. **Private repositories in reusable workflows**: `uses: owner/repo/path@ref` clones over unauthenticated HTTPS. Private repos cannot be accessed unless a GitHub token is configured.
5. **Concurrency groups**: `concurrency:` blocks and `cancel-in-progress` are parsed but not enforced during execution.
6. **Service containers**: `services:` block is parsed but containers are never started in any runtime mode.
7. **Windows and macOS runners**: `runs-on: windows-*` or `macos-*` is silently mapped to a container image (macOS → Linux, Windows → Windows container). `${{ runner.os }}` reflects host OS, not `runs-on` value.

---

## Relevance to Claude Code Development

### Direct Relevance

1. **Workflow validation in CI/CD pipelines**: Claude Code projects using GitHub Actions can use wrkflw to validate `.github/workflows/` before commit, catching syntax and logic errors early. This is particularly valuable for complex workflows with expression evaluation, matrix builds, or reusable workflow dependencies.

2. **Local testing of GitHub Actions**: Development workflows (CI, testing, linting, deployment) can be tested locally before pushing, reducing iteration time and CI/CD cost. Especially useful for testing custom actions or composite workflows.

3. **Expression debugging**: The expression evaluator can help debug complex `${{ }}` expressions involving `toJSON`, `fromJSON`, context variables, and conditions before they run on GitHub.

4. **Matrix build validation**: Projects with parametrized tests or multi-platform builds can validate matrix expansion locally without triggering CI/CD runs.

### Use Cases in Agent Development

1. **GitHub Actions skill validation**: Skills that generate or modify `.github/workflows/` files could use wrkflw to validate output before committing.

2. **CI/CD automation workflows**: Projects running custom CI/CD actions can test trigger logic locally with `--event` and `--changed-files` flags.

3. **Reusable workflow development**: Teams building shared workflow libraries can iterate locally before publishing to a shared repo.

4. **Debugging workflow failures**: When a GitHub Actions run fails, running the same workflow locally with wrkflw can reproduce and fix the issue without waiting for another CI/CD run.

---

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|-----------|---|---|
| **Identity/Metadata** | high | 2026-04-25 | Version from Cargo.toml, license verified from LICENSE file |
| **Features** | high | 2026-04-25 | Extracted directly from README.md and BREAKING_CHANGES.md (v0.8.0 release notes) |
| **Architecture** | high | 2026-04-25 | Crate structure from crates/README.md and workspace Cargo.toml; data flow inferred from component organization |
| **Installation & Usage** | high | 2026-04-25 | Commands extracted verbatim from README.md |
| **Limitations** | high | 2026-04-25 | "Not yet supported" section from README.md |
| **Relevance** | medium | 2026-04-25 | Inferred from feature set and agent development workflows; not explicitly documented |

### Next Review

**Scheduled**: 2026-07-25 (3 months)

**Triggers for earlier review**: Breaking changes in v0.9.0 (check BREAKING_CHANGES.md), significant architectural changes (check INDEX.md update date), removal of documented limitations.

---

## References

- **GitHub Repository**: <https://github.com/bahdotsh/wrkflw> (accessed 2026-04-25)
- **README.md**: Primary feature and usage documentation (accessed 2026-04-25)
- **Cargo.toml** (root): Workspace structure and version metadata (accessed 2026-04-25)
- **crates/README.md**: Crate organization and responsibilities (accessed 2026-04-25)
- **crates/executor/README.md**: Executor engine API and capabilities (accessed 2026-04-25)
- **crates/parser/README.md**: Parser responsibilities (accessed 2026-04-25)
- **BREAKING_CHANGES.md**: Version 0.8.0 release notes and strict-filter migration guide (accessed 2026-04-25)
- **LICENSE**: MIT License, copyright Gokul (accessed 2026-04-25)
- **INDEX.md**: Codebase structure and file manifest (accessed 2026-04-25)
