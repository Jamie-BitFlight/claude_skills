---
title: "devenv"
research_date: "2026-02-26"
source_url: "https://devenv.sh"
github_url: "https://github.com/cachix/devenv"
version_at_research: "v1.11.2"
license: "Apache-2.0"
last_verified: "2026-02-26"
version_at_verification: "v1.11.2"
next_review: "2026-05-26"
---

## Overview

devenv is a declarative developer environment tool built on Nix that enables teams to define fast, reproducible, and composable development environments in a single `devenv.nix` configuration file. It provides 100,000+ prebuilt packages, built-in process management, task automation, and service orchestration that activate in under 100ms through Nix evaluation caching. The tool targets the "works on my machine" problem by encoding the entire toolchain — languages, services, git hooks, and environment variables — as version-pinned, reproducible declarations.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| "Works on my machine" environment drift between developers | Declarative Nix-based configuration pinned via `devenv.lock`, guaranteeing bit-for-bit reproducibility |
| Slow environment activation blocking developer workflow | Nix evaluation caching delivers sub-100ms activation through direnv integration |
| Managing multiple language runtimes and toolchains per project | 50+ language modules with built-in version management for Python, Rust, Go, Ruby, PHP, Terraform |
| Running local services (databases, message brokers) without Docker overhead | Native service modules for PostgreSQL, Redis, MySQL, Kafka, RabbitMQ, Elasticsearch with no container runtime |
| Inconsistent CI vs local development environments | `devenv test` command runs the same environment definition in CI pipelines |
| Monorepo environment sprawl across frontend/backend components | Composable imports in `devenv.yaml` merge local sub-environment configurations |
| Container configuration duplication | `devcontainer.enable = true` auto-generates `.devcontainer.json` from the same `devenv.nix` |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 6,342 | 2026-02-26 |
| Forks | 467 | 2026-02-26 |
| Contributors | 246 | 2026-02-26 |
| Open Issues | 352 | 2026-02-26 |
| Latest Release | v1.11.2 | 2025-11-27 |
| Repository Created | 2022-10-22 | 2026-02-26 |
| Primary Language | Rust | 2026-02-26 |

SOURCE: [GitHub API repos/cachix/devenv](https://api.github.com/repos/cachix/devenv) (accessed 2026-02-26)

---

## Key Features

### Declarative Environment Configuration

- `devenv.nix` is the single source of truth for packages, languages, services, processes, tasks, git hooks, and environment variables
- `devenv.yaml` defines input sources (nixpkgs revision, custom flake inputs) and composes imports from sub-directories
- `devenv.lock` pins all inputs to exact revisions for reproducible builds
- Profile-based activation allows hostname/username-based environment variants within one configuration

### Language Support (50+ languages)

- Per-language modules with version management: Python (via venv/conda/uv), Rust (toolchain pinning), Go, Ruby, PHP, Terraform, JavaScript/Node.js, Java, Haskell, and 40+ others
- LSP servers, formatters, linters, and compilers enabled declaratively per language
- Python example: `languages.python.enable = true; languages.python.version = "3.12.0";`

### Service Orchestration

- 30+ built-in service modules: PostgreSQL, Redis, MySQL, MongoDB, Kafka, RabbitMQ, Elasticsearch, Memcached, MinIO, and more
- Services run natively in the development environment without requiring Docker or container runtimes
- Each service module exposes typed configuration options (port, data directory, authentication settings)

### Process Management

- Default built-in process manager supports supervision, socket activation, file watching, and dependency ordering
- Alternative process manager backends: process-compose (TUI), hivemind, honcho, overmind, mprocs — switchable via `process.manager.implementation`
- Restart policies: `on_failure` (default), `always`, `never`
- Ready probes: exec commands, HTTP endpoint polling, systemd-style `READY=1` notify probes
- Process dependencies declared with `after`/`before` and temporal suffixes `@started`, `@ready`, `@completed`

### Task Automation System

- Tasks defined in `devenv.nix` with `exec`, `status` (skip-if-zero-exit), `execIfModified` (file hash tracking), and `package` attributes
- Parallel execution with automatic dependency resolution between named tasks
- Inter-task data flow via `$DEVENV_TASK_INPUT`, `$DEVENV_TASKS_OUTPUTS`, `$DEVENV_TASK_OUTPUT_FILE` environment variables
- Processes become tasks automatically under the `devenv:processes:` namespace
- Supports any language for task execution via the `package` attribute

### Git Hooks Integration

- `git-hooks.hooks` module enables pre-commit, commit-msg, and other hook types
- Language-specific linters (black, isort, rustfmt, golangci-lint, eslint) activated per-project
- Uses the upstream `pre-commit` framework's hook registry under the hood

### Composability and Imports

- `devenv.yaml` imports support local relative paths for monorepo subdirectory composition
- At the root, all imported configurations merge so `devenv up` starts unified process set
- Per-subdirectory activation: entering `frontend/` activates only that component's environment
- Remote imports not yet supported in `devenv.yaml` (as of v1.10)

### Container and Codespace Support

- `devcontainer.enable = true` generates `.devcontainer.json` from the same Nix configuration
- Generated devcontainer compatible with GitHub Codespaces and VS Code Dev Containers
- Container/OCI image building from development environment configuration

### Secrets Management

- SecretSpec integration (`secretspec` v0.4.1+ as of v1.11.2) for declarative secrets management
- Secrets injected into environment without hardcoding in version-controlled configuration files

---

## Technical Architecture

devenv is implemented in Rust for the CLI binary, with the module system written in Nix. The evaluation pipeline works as follows:

<eg>
devenv.yaml          devenv.nix            Nix module system
    |                    |                        |
    v                    v                        v
Input pins  ------>  User config  ------>  Merged module options
(devenv.lock)                              (languages, services,
                                            processes, tasks)
                                                  |
                                                  v
                                         Nix derivation graph
                                                  |
                                        +---------+---------+
                                        |                   |
                                        v                   v
                                  Cachix binary        Local build
                                  cache lookup         (Nix store)
                                        |                   |
                                        v                   v
                                   /nix/store/...  <--------+
                                        |
                                        v
                               Shell environment
                             (PATH, env vars, hooks)
                               activated via direnv
</eg>

Key architectural decisions:

- **Nix module system**: All configuration options are typed Nix modules — invalid configurations fail at evaluation time with descriptive errors rather than runtime
- **Binary cache**: Cachix (the same organization) provides a public binary cache (`cachix.cachix.org`) so common packages download as pre-built binaries rather than compiling from source
- **direnv integration**: `.envrc` generated by `devenv init` calls `use devenv`, enabling automatic shell activation when entering the project directory
- **Flakes compatibility**: devenv supports both classic Nix (via `nixpkgs.tarball`) and Nix Flakes for teams already on flakes-based workflows

---

## Installation & Usage

```bash
# Step 1: Install Nix (Linux/macOS daemon mode)
sh <(curl -L https://nixos.org/nix/install) --daemon

# Step 2: Install devenv via nixpkgs unstable
nix-env --install --attr devenv -f https://github.com/NixOS/nixpkgs/tarball/nixpkgs-unstable

# Or via nix profile
nix profile install nixpkgs#devenv

# Step 3 (optional): Add GitHub token to avoid API rate limits
echo "access-tokens = github.com=<GITHUB_TOKEN>" >> ~/.config/nix/nix.conf
```

```bash
# Initialize a new project
devenv init
# Creates: .envrc, devenv.nix, devenv.yaml, .gitignore

# Activate environment (manual)
devenv shell

# Start all configured processes
devenv up

# Run tasks
devenv tasks run myapp:build

# Update pinned inputs
devenv update

# Run environment tests (for CI)
devenv test

# Build container image
devenv container build
```

```nix
# devenv.nix — example configuration
{ pkgs, lib, config, ... }:

{
  # Packages available in the shell
  packages = [ pkgs.git pkgs.jq ];

  # Language runtimes
  languages.python = {
    enable = true;
    version = "3.12.0";
    venv.enable = true;
    venv.requirements = ./requirements.txt;
  };

  languages.rust = {
    enable = true;
    channel = "stable";
  };

  # Local services (no Docker needed)
  services.postgres = {
    enable = true;
    port = 5432;
    initialDatabases = [{ name = "myapp"; }];
  };

  services.redis = {
    enable = true;
    port = 6379;
  };

  # Processes
  processes = {
    web.exec = "python manage.py runserver";
    worker.exec = "celery -A myapp worker";
  };

  # Tasks
  tasks = {
    "myapp:migrate" = {
      exec = "python manage.py migrate";
      execIfModified = [ "migrations/**/*.py" ];
    };
  };

  # Git hooks
  git-hooks.hooks = {
    black.enable = true;
    ruff.enable = true;
    rustfmt.enable = true;
  };

  # Environment variables
  env.DATABASE_URL = "postgresql://localhost:5432/myapp";

  # DevContainer support
  devcontainer.enable = true;
}
```

```yaml
# devenv.yaml — input composition
inputs:
  nixpkgs:
    url: github:NixOS/nixpkgs/nixpkgs-unstable

imports:
  - ./frontend
  - ./backend
```

---

## Relevance to Claude Code Development

### Applications

- **Reproducible skill development environments**: Each skill plugin that depends on specific Python versions, linting tools (prek, pre-commit), or CLI tools (gh, uv) could be declared in a `devenv.nix` at the repository root, eliminating onboarding friction
- **Consistent pre-commit hook enforcement**: The git-hooks module directly replaces manual `.pre-commit-config.yaml` management by declaring hooks as typed Nix options with automatic installation
- **Local service mocking for tests**: Skills that test against databases or message queues could use devenv's service modules to spin up local PostgreSQL/Redis instances without Docker, matching CI environments
- **Task automation parity with CI**: The task system with `execIfModified` and status caching mirrors the conditional execution patterns needed for efficient CI/CD in skill validation pipelines

### Patterns Worth Adopting

- **Typed configuration with fail-fast validation**: devenv's Nix module system rejects invalid option combinations at evaluation time rather than at runtime — a pattern applicable to skill frontmatter validation
- **`execIfModified` content-hash tracking**: Skipping expensive operations when inputs have not changed (by hash, not just timestamp) is directly applicable to the `validate_research.py` freshness checks
- **Namespace-prefixed task composition**: The `namespace:taskname` convention for task grouping provides a clear model for organizing the research curator's multi-step workflows
- **Inter-task data flow via environment variables**: `$DEVENV_TASK_INPUT` / `$DEVENV_TASK_OUTPUT_FILE` provides a simple, shell-agnostic IPC pattern for agent pipelines

### Integration Opportunities

- **devenv.nix at repository root**: Adding `devenv.nix` to `claude_skills` would provide a single-command environment setup (`devenv shell`) with all required tools (uv, gh, prek, node) pinned to exact versions
- **Replace manual pre-commit setup**: Current `uv run prek install` step in CLAUDE.md session start could be absorbed into `devenv`'s `git-hooks` module, auto-installing hooks on `devenv shell` entry
- **Process management for local agent testing**: Multi-agent skill tests that require concurrent processes (orchestrator + worker agents) could be declared as devenv processes with proper dependency ordering

---

## References

- [devenv official website](https://devenv.sh) (accessed 2026-02-26)
- [devenv Getting Started](https://devenv.sh/getting-started/) (accessed 2026-02-26)
- [devenv Processes documentation](https://devenv.sh/processes/) (accessed 2026-02-26)
- [devenv Tasks documentation](https://devenv.sh/tasks/) (accessed 2026-02-26)
- [devenv Composing using imports](https://devenv.sh/composing-using-imports/) (accessed 2026-02-26)
- [devenv Codespaces/DevContainer integration](https://devenv.sh/integrations/codespaces-devcontainer/) (accessed 2026-02-26)
- [GitHub repository cachix/devenv](https://github.com/cachix/devenv) (accessed 2026-02-26)
- [GitHub API release v1.11.2](https://github.com/cachix/devenv/releases/tag/v1.11.2) (accessed 2026-02-26)

---
