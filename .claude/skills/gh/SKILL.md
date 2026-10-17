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

Resolve `GH_SETUP_SCRIPT` to the absolute `scripts/setup_gh.py` path beneath this loaded skill. Run it from the target project directory; resolving the packaged executable does not change that directory.

```bash
uv run "$GH_SETUP_SCRIPT" --detect-only
```

`--detect-only` reads `GITHUB_REPO` or the target project's current Git remote and prints rendered examples. It does not install `gh`, contact the network, or write configuration. To install or update the CLI, run `uv run "$GH_SETUP_SCRIPT"`. Add `--configure-repo` only when the detected repository should be written to the target project's `.dh/config.yaml`. When `gh` is already installed, `--configure-repo` without `--force` performs this local configuration directly: it does not resolve releases, require platform/install-directory discovery, download, or reinstall. `--dry-run` never writes configuration; `--force` retains installation behavior.

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

Git remotes can point to a local proxy (`127.0.0.1`) rather than `github.com`, so a repository-scoped command that supports `-R` or `--repo` must receive an explicit repository:

```bash
gh issue list -R OWNER/REPO
gh pr list --repo OWNER/REPO
```

Do not pass `-R` to verbs that do not support it:

- REST API calls embed the target in the endpoint: `gh api repos/OWNER/REPO/issues`.
- GraphQL calls supply explicit `owner` and `name` variables in the query/request.
- Projects V2 uses `--owner OWNER` and the project number where required.
- `gh auth` and `gh version` are not repository-scoped.

Use `gh <verb> --help` when adding a command; pass an explicit repository only through that verb's supported interface.

</repo_detection>

---

## Common commands

Use the detected or explicitly supplied `OWNER/REPO` on every `gh` command when the remote is a proxy:

```bash
gh issue list -R OWNER/REPO
gh pr list -R OWNER/REPO
```

## Automation — Python Script

Resolve `GH_PROJECT_HELPER` to the absolute `scripts/github_project_setup.py` path beneath this loaded skill and invoke it without leaving the target project directory. It uses PyGithub for repository, issue, label, and milestone operations; its Projects V2 status update uses the installed `gh` CLI for GraphQL.

```bash
uv run "$GH_PROJECT_HELPER" labels --repo OWNER/REPO
uv run "$GH_PROJECT_HELPER" milestone list --repo OWNER/REPO
uv run "$GH_PROJECT_HELPER" milestone create --repo OWNER/REPO --title "v1.0" --due 2026-03-31
uv run "$GH_PROJECT_HELPER" issue list --repo OWNER/REPO --priority p1
uv run "$GH_PROJECT_HELPER" issue create --repo OWNER/REPO --title "feat: X" --priority-label priority:p1
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
