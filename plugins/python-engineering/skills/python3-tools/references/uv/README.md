# uv Reference Archive

This directory is a **cached snapshot of `docs.astral.sh/uv`** — generated, not
authored. Do not hand-edit the prose in the reference files here to correct a
stale fact; refresh from the live docs instead.

## Precedence

When anything in this archive is disputed or ambiguous, resolve in this order:

1. The `python-engineering:uv` skill, if also loaded — this plugin's own policy on *how to work
   with uv*. Wins over both sources below.
2. The live `astral:uv` skill / `docs.astral.sh/uv` — authoritative on *tool
   facts* (current flags, defaults, behavior).
3. This archive — a snapshot of (2). Lowest priority; check the live site
   before trusting a stale-looking claim.

## Version Information

<!-- populated by ../../scripts/sync_uv_releases.py -->

## Documentation Index

- [uv](./docs/index.md)
- **concepts/**
  - [TLS certificates](./docs/concepts/authentication/certificates.md)
  - [The `uv auth` CLI](./docs/concepts/authentication/cli.md)
  - [Git credentials](./docs/concepts/authentication/git.md)
  - [HTTP credentials](./docs/concepts/authentication/http.md)
  - [Authentication](./docs/concepts/authentication/index.md)
  - [Third-party services](./docs/concepts/authentication/third-party.md)
  - [The uv build backend](./docs/concepts/build-backend.md)
  - [Caching](./docs/concepts/cache.md)
  - [Configuration files](./docs/concepts/configuration-files.md)
  - [Concepts overview](./docs/concepts/index.md)
  - [Package indexes](./docs/concepts/indexes.md)
  - [Preview features](./docs/concepts/preview.md)
  - [Building distributions](./docs/concepts/projects/build.md)
  - [Configuring projects](./docs/concepts/projects/config.md)
  - [Managing dependencies](./docs/concepts/projects/dependencies.md)
  - [Exporting a lockfile](./docs/concepts/projects/export.md) — Exporting a lockfile to different formats
  - [Projects](./docs/concepts/projects/index.md)
  - [Creating projects](./docs/concepts/projects/init.md)
  - [Project structure and files](./docs/concepts/projects/layout.md)
  - [Running commands in projects](./docs/concepts/projects/run.md)
  - [Locking and syncing](./docs/concepts/projects/sync.md)
  - [Using workspaces](./docs/concepts/projects/workspaces.md)
  - [Python versions](./docs/concepts/python-versions.md)
  - [Resolution](./docs/concepts/resolution.md)
  - [Tools](./docs/concepts/tools.md)
- **getting-started/**
  - [Features](./docs/getting-started/features.md)
  - [First steps with uv](./docs/getting-started/first-steps.md)
  - [Getting help](./docs/getting-started/help.md)
  - [Getting started](./docs/getting-started/index.md)
  - [Installing uv](./docs/getting-started/installation.md)
- **guides/**
  - [Guides overview](./docs/guides/index.md)
  - [Installing and managing Python](./docs/guides/install-python.md) — A guide to using uv to install Python, including requesting specific versions, automatic installation, viewing installed versions, and more.
  - [Using uv with AWS Lambda](./docs/guides/integration/aws-lambda.md) — A complete guide to using uv with AWS Lambda to manage Python dependencies and deploy serverless functions via Docker containers or zip archives.
  - [AWS CodeArtifact](./docs/guides/integration/aws.md) — Using uv with AWS CodeArtifact for installing and publishing Python packages.
  - [Azure Artifacts](./docs/guides/integration/azure.md) — Using uv with Azure Artifacts for installing and publishing Python packages.
  - [Using uv with Bazel](./docs/guides/integration/bazel.md) — Using uv to power package resolution with Bazel
  - [Using uv with Coiled](./docs/guides/integration/coiled.md) — A complete guide to using uv with Coiled to manage Python dependencies and deploy serverless scripts.
  - [Using uv with Dependabot](./docs/guides/integration/dependabot.md) — A guide to using uv with the Dependabot dependency bot.
  - [Using uv in Docker](./docs/guides/integration/docker.md) — A complete guide to using uv in Docker to manage Python dependencies while optimizing build times and image size via multi-stage builds, intermediate layers, and more.
  - [Using uv with FastAPI](./docs/guides/integration/fastapi.md) — A guide to using uv with FastAPI to manage Python dependencies, run applications, and deploy with Docker.
  - [Using uv in GitHub Actions](./docs/guides/integration/github.md) — A guide to using uv in GitHub Actions, including installation, setting up Python, installing dependencies, and more.
  - [Using uv in GitLab CI/CD](./docs/guides/integration/gitlab.md) — A guide to using uv in GitLab CI/CD, including installation, setting up Python, installing dependencies, and more.
  - [Google Artifact Registry](./docs/guides/integration/google.md) — Using uv with Google Artifact Registry for installing and publishing Python packages.
  - [Integration guides](./docs/guides/integration/index.md)
  - [JFrog Artifactory](./docs/guides/integration/jfrog.md) — Using uv with JFrog Artifactory for installing and publishing Python packages.
  - [Using uv with Jupyter](./docs/guides/integration/jupyter.md) — A complete guide to using uv with Jupyter notebooks for interactive computing, data analysis, and visualization, including kernel management and virtual environment integration.
  - [Using uv with marimo](./docs/guides/integration/marimo.md) — A complete guide to using uv with marimo notebooks for interactive computing, script execution, and data apps.
  - [Using uv with pre-commit](./docs/guides/integration/pre-commit.md) — A guide to using uv with pre-commit to automatically update lock files, export requirements, and compile requirements files.
  - [Using uv with PyTorch](./docs/guides/integration/pytorch.md) — A guide to using uv with PyTorch, including installing PyTorch, configuring per-platform and per-accelerator builds, and installing GPU-enabled PyTorch extensions.
  - [Using uv with Renovate](./docs/guides/integration/renovate.md) — A guide to using uv with the Renovate dependency bot.
  - [Migration guides](./docs/guides/migration/index.md)
  - [Migrating from pip to a uv project](./docs/guides/migration/pip-to-project.md)
  - [Building and publishing a package](./docs/guides/package.md) — A guide to using uv to build and publish Python packages to a package index, like PyPI.
  - [Working on projects](./docs/guides/projects.md) — A guide to using uv to create and manage Python projects, including adding dependencies, running commands, and building publishable distributions.
  - [Running scripts](./docs/guides/scripts.md) — A guide to using uv to run Python scripts, including support for inline dependency metadata, reproducible scripts, and more.
  - [Using tools](./docs/guides/tools.md) — A guide to using uv to run tools published as Python packages, including one-off invocations with uvx, requesting specific tool versions, installing tools, upgrading tools, and more.
- **pip/**
  - [Compatibility with `pip` and `pip-tools`](./docs/pip/compatibility.md)
  - [Locking environments](./docs/pip/compile.md)
  - [Declaring dependencies](./docs/pip/dependencies.md)
  - [Using Python environments](./docs/pip/environments.md)
  - [The pip interface](./docs/pip/index.md)
  - [Inspecting environments](./docs/pip/inspection.md)
  - [Managing packages](./docs/pip/packages.md)
- **reference/**
  - [Benchmarks](./docs/reference/benchmarks.md)
  - [contributing](./docs/reference/contributing.md)
  - [Reference](./docs/reference/index.md)
  - [The uv installer](./docs/reference/installer.md)
  - [Internals](./docs/reference/internals/index.md)
  - [Workspace metadata](./docs/reference/internals/metadata.md)
  - [Resolver internals](./docs/reference/internals/resolver.md)
  - [Policies](./docs/reference/policies/index.md)
  - [License](./docs/reference/policies/license.md)
  - [Platform support](./docs/reference/policies/platforms.md)
  - [Python support](./docs/reference/policies/python.md)
  - [Rust support](./docs/reference/policies/rust.md)
  - [Versioning](./docs/reference/policies/versioning.md)
  - [Storage](./docs/reference/storage.md)
  - [Troubleshooting build failures](./docs/reference/troubleshooting/build-failures.md)
  - [Troubleshooting](./docs/reference/troubleshooting/index.md)
  - [Reproducible examples](./docs/reference/troubleshooting/reproducible-examples.md)

## Refresh cadence

Both sections above are refreshed weekly by `.github/workflows/sync-astral-corpus.yml`
and open a PR when they change: the Version Information section by
`../../scripts/sync_uv_releases.py` (GitHub Releases API), and the
Documentation Index plus `docs/` corpus by
`../../scripts/sync_astral_docs.py uv` (mirrors `astral-sh/uv`'s `docs/`
tree).

generated_at: 2026-08-19
