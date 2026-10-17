---
name: gh
description: "Install and configure the GitHub CLI (gh) for AI agent environments where gh may not be pre-installed and git remotes use local proxies instead of github.com. Use when gh command not found, shutil.which returns None, need GitHub API access for issues or PRs or releases or workflow runs, or repository operations fail with 'failed to determine base repo' error. Provides auto-install script with SHA256 verification, GITHUB_TOKEN auth with anonymous fallback, and the required -R flag pattern for proxy environments. Covers project management via GitHub Projects V2, milestones via REST API, issue lifecycle templates, and label taxonomy management."
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

## Installation and detection

Run the packaged script from this skill's active directory; `scripts/` is skill-local on every supported harness. Do not substitute a target-project `.claude/skills` path.

```bash
scripts/setup_gh.py --detect-only
```

`--detect-only` reads `GITHUB_REPO` or the current Git remote and prints rendered examples. It does not install `gh`, contact the network, or write configuration. To install or update the CLI, run `scripts/setup_gh.py`. Add `--configure-repo` only when the detected repository should be written to `.dh/config.yaml`.

```text
--force             Reinstall even if already at latest version
--dry-run           Show installation actions without installing or writing configuration
--bin-dir PATH      Override install directory (default: auto-detect from PATH)
--detect-only       Detect owner/repo and print command examples without side effects
--configure-repo    Explicitly write the detected owner/repo to .dh/config.yaml
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

## Common commands

Use the detected or explicitly supplied `OWNER/REPO` on every `gh` command when the remote is a proxy:

```bash
gh issue list -R OWNER/REPO
gh pr list -R OWNER/REPO
```

## Automation — Python Script

For multi-step GitHub administration, run the packaged `scripts/github_project_setup.py` with an explicit repository. It uses PyGithub for repository, issue, label, and milestone operations; its Projects V2 status update uses the installed `gh` CLI for GraphQL.

```bash
scripts/github_project_setup.py labels --repo OWNER/REPO
scripts/github_project_setup.py milestone list --repo OWNER/REPO
scripts/github_project_setup.py milestone create --repo OWNER/REPO --title "v1.0" --due 2026-03-31
scripts/github_project_setup.py issue list --repo OWNER/REPO --priority p1
scripts/github_project_setup.py issue create --repo OWNER/REPO --title "feat: X" --priority-label priority:p1
```

Use the configured DH backend for durable backlog lifecycle operations; this administration helper is not a second backlog store.

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
