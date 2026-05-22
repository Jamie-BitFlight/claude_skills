---
name: gh
description: 'Install and configure the GitHub CLI (gh) for AI agent environments where gh may not be pre-installed and git remotes use local proxies instead of github.com. Provides auto-install script with SHA256 verification and GITHUB_TOKEN auth with anonymous fallback. Use when gh command not found, shutil.which("gh") returns None, need GitHub API access (issues, PRs, releases, workflow runs), or repository operations fail with "failed to determine base repo" error. Documents required -R flag for all gh commands in proxy environments. Includes project management: GitHub Projects V2 (gh project), milestones (REST API), issue stories (lifecycle and templates), and label taxonomy management.'
---

# GitHub CLI (gh) — Setup and Usage

## Purpose

Ensures the GitHub CLI (`gh`) is available and provides correct usage patterns for AI agents operating in environments where `gh` may not be pre-installed and where git remotes point to local proxies instead of `github.com`.

## When to Use

- `gh` command not found or `shutil.which("gh")` returns None
- Need to interact with GitHub API (issues, PRs, releases, workflows)
- Repository remote does not point to `github.com` (proxy environments)
- Need authenticated GitHub operations with `GITHUB_TOKEN`
- Managing GitHub Issues, Projects V2, Milestones, or Labels

---

## Installation

If `gh` is not installed, run the setup script:

```bash
uv run .claude/skills/gh/scripts/setup_gh.py
```

The script:

1. Checks if `gh` is already installed via `shutil.which`
2. Detects platform (Linux, macOS, Windows) and architecture
3. Fetches the latest release from `https://github.com/cli/cli/releases/latest`
4. Downloads the correct archive with SHA256 verification from checksums file
5. Extracts and installs the binary to a writable PATH directory
6. Uses `GITHUB_TOKEN` for authenticated requests; falls back to anonymous if auth fails (401/403)

**CLI options:**

```text
--force          Reinstall even if already at latest version
--dry-run        Show what would happen without installing
--bin-dir        Override install directory (default: auto-detect from PATH)
--detect-only    Detect owner/repo, refresh .dh/config.yaml and gh-examples.md, print examples to stdout. No network calls.
```

---

## Authentication

`GITHUB_TOKEN` environment variable provides automatic authentication. No manual `gh auth login` needed.

```bash
# Verify authentication
gh auth status
```

If `GITHUB_TOKEN` is set, `gh` authenticates automatically for all API calls.

---

## Repository Detection

<repo_detection>

Git remote points to a local proxy (`127.0.0.1`), NOT `github.com`. Every `gh` command fails without explicit repo specification:

```text
failed to determine base repo: none of the git remotes configured for this
repository point to a known GitHub host.
```

**RULE: Pass `-R` (or `--repo`) on EVERY `gh` command:**

```bash
gh <command> -R <owner/repo>
```

This applies to ALL `gh` subcommands: `pr`, `issue`, `run`, `api`, `release`, `project`, etc.

</repo_detection>

---

## Common Commands

!`uv run --script .claude/skills/gh/scripts/setup_gh.py --detect-only 2>/dev/null`

---

## Automation — Python Script

For multi-step operations (label setup, milestone creation, project init, issue import), use:

```bash
# Full project setup
uv run .claude/skills/gh/scripts/github_project_setup.py setup

# Labels only
uv run .claude/skills/gh/scripts/github_project_setup.py labels

# Milestone management
uv run .claude/skills/gh/scripts/github_project_setup.py milestone list
uv run .claude/skills/gh/scripts/github_project_setup.py milestone create --title "v1.0" --due 2026-03-31

# Issue management
uv run .claude/skills/gh/scripts/github_project_setup.py issue list --priority p1
uv run .claude/skills/gh/scripts/github_project_setup.py issue create --title "feat: X" --priority-label priority:p1
```

The script delegates all GitHub operations to the authenticated `gh` CLI — no separate API tokens or Python HTTP clients needed.

---

## Reference Files

- [labels.md](./references/labels.md) — Label taxonomy (priority, type, status), color codes, bulk setup
- [milestones.md](./references/milestones.md) — Milestone CRUD via REST API, naming conventions
- [projects-v2.md](./references/projects-v2.md) — GitHub Projects V2 commands, custom fields, GraphQL queries
- [issue-stories.md](./references/issue-stories.md) — Issue as story format, body template, lifecycle, backlog item field mapping

---

## Sources

- [GitHub CLI Manual](https://cli.github.com/manual) — official reference
- [GitHub CLI Releases](https://github.com/cli/cli/releases) — binary downloads
- [GitHub REST API — Issues](https://docs.github.com/en/rest/issues) — milestones, labels, issues
- [GitHub Projects V2 API](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects) — GraphQL API
- `gh version 2.87.2 (2026-02-20)` — version verified by installation test
