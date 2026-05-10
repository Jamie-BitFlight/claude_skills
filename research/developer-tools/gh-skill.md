---
title: GitHub CLI (gh) Skill
subtitle: Agent-ready GitHub CLI installer with SHA256 verification and proxy-remote command patterns
category: developer-tools
resource_url: https://github.com/Jamie-BitFlight/claude_skills/blob/main/.claude/skills/gh/SKILL.md
github_url: https://github.com/cli/cli
date_created: "2026-05-10"
date_last_reviewed: "2026-05-10"
status: published
---

# GitHub CLI (gh) Skill — Installation and Agent Integration

**Research Date**: 2026-05-10
**Source URL**: <https://github.com/Jamie-BitFlight/claude_skills/blob/main/.claude/skills/gh/SKILL.md>
**GitHub Repository**: <https://github.com/cli/cli>
**Version at Research**: 2.87.2 (released 2026-02-20)
**License**: MIT (GitHub CLI project)

---

## Overview

A Claude Code skill that ensures the GitHub CLI (`gh`) is available in AI agent environments where the tool may not be pre-installed. Provides automatic binary installation with SHA256 verification, environment-based authentication via `GITHUB_TOKEN`, and documented command patterns for repositories using local proxy remotes instead of direct GitHub connections. The skill bundles four reference files documenting GitHub Projects V2, milestones, issue lifecycle templates, and label taxonomy — plus two Python automation scripts for multi-step project setup and cleanup operations.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| `gh` not pre-installed in agent environments | Auto-install script detects platform, downloads latest binary from GitHub Releases with SHA256 verification, installs to system PATH |
| Agent doesn't know which version of `gh` is current | Script fetches latest release metadata from `https://api.github.com/repos/cli/cli/releases/latest` and compares installed version |
| Repository remotes use local proxies (127.0.0.1), not github.com | Skill documents mandatory `-R owner/repo` flag on every `gh` command; agent workflows include this pattern in all examples |
| Manual GitHub authentication conflicts with agent automation | Automatic authentication via `GITHUB_TOKEN` environment variable; anonymous fallback on auth failure (401/403) |
| No clear command reference for common GitHub operations | Skill provides 50+ documented command examples across 8 categories: PRs, Issues, Labels, Projects V2, Milestones, Workflow Runs, Releases, Repository operations |
| Multi-step GitHub project setup is manual and error-prone | Automation script `github_project_setup.py` handles label taxonomy creation, milestone setup, and Projects V2 initialization in single command |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub CLI Latest Release | 2.87.2 | 2026-02-20 |
| Skill SKILL.md Size | 8,736 bytes | 2026-05-03 (repo timestamp) |
| Reference Files | 4 files | 2026-05-03 |
| Python Scripts | 3 scripts | 2026-05-03 |
| Supported Platforms | Linux, macOS, Windows | Documented in setup_gh.py lines 56-64 |
| Architecture Support | amd64, arm64, armv6, 386 | Documented in setup_gh.py ARCH_MAP |

---

## Key Features

### Installation and Setup

- **Automatic platform detection**: Identifies OS (Linux, macOS, Windows) and architecture (x86_64, aarch64, armv7l, i386) via `platform.system()` and `platform.machine()` — Source: setup_gh.py lines 56-64
- **SHA256 verification**: Downloads checksum file alongside binary, verifies integrity before installation — Source: setup_gh.py line 34-35
- **PATH directory auto-detection**: Finds writable system PATH directories; `--bin-dir` override for custom locations — Source: setup_gh.py line 45
- **Authenticated API fallback**: Uses `GITHUB_TOKEN` for API requests; falls back to anonymous on 401/403 — Source: setup_gh.py lines 53-54
- **Dry-run mode**: `--force` and `--dry-run` flags for preview and forced reinstall — Source: setup_gh.md lines 42-44

### Command Patterns

- **Proxy-aware repository specification**: All commands require `-R owner/repo` flag for environments using local proxy remotes — Source: lines 73-79
- **Output formatting**: JSON output, JQ filtering, Go template formatting for programmatic parsing — Source: lines 246-256
- **GraphQL API access**: Direct `gh api graphql` for complex queries — Source: line 224
- **Pagination support**: `--paginate` flag for large result sets — Source: line 227

### Automation Capabilities

- **Label taxonomy management**: Bulk label creation with color codes and descriptions; supports priority (P0-P2), type (feature/bug/refactor/docs/chore), and status (8 lifecycle states) labels — Source: github_project_setup.py referenced at line 146-147
- **GitHub Projects V2 setup**: Field creation, issue-to-project association, custom field configuration — Source: references/projects-v2.md (4,465 bytes)
- **Milestone CRUD**: REST API endpoints for create, list, update, assign to issues — Source: references/milestones.md (4,190 bytes)
- **Issue lifecycle templates**: Body templates, story format, field mapping between GitHub Issues and backlog items — Source: references/issue-stories.md (5,597 bytes)
- **Cleanup operations**: `experiment_cleanup.py` removes stale resources from repositories — Source: scripts directory listing

---

## Technical Architecture

### Installation Flow

```
setup_gh.py invocation
  ├─ Check installed version via shutil.which("gh")
  ├─ Fetch latest release metadata from GitHub Releases API
  │   ├─ Authenticate with GITHUB_TOKEN if available
  │   └─ Parse release JSON for download URLs and checksums
  ├─ Detect platform and architecture
  │   └─ Map architecture to gh release naming (amd64, arm64, armv6, 386)
  ├─ Download binary archive (tar.gz on Unix, zip on Windows)
  ├─ Verify SHA256 checksum against downloaded checksums file
  ├─ Extract archive to temporary directory
  ├─ Install to detected or specified PATH directory
  ├─ Set executable permissions (chmod +x)
  └─ Verify installation: run "gh version"
```

Source: setup_gh.py lines 1-100 (installation logic defined through tarfile/zipfile extraction and permission handling)

### Command Execution Model

```
Agent invokes gh command
  ├─ Pass -R owner/repo for repositories with proxy remotes
  ├─ Set GITHUB_TOKEN in environment (auto-loaded by gh)
  ├─ Execute subcommand: pr, issue, label, project, api, etc.
  ├─ gh resolves authentication, contacts GitHub API
  │   └─ Uses GITHUB_TOKEN if set; anonymous otherwise
  ├─ Parse response (default: human-readable; --json for structured)
  └─ Return exit code and stdout/stderr
```

Source: SKILL.md lines 73-240 (all command examples follow this pattern)

### Reference Material Organization

```
skill directory: gh/
  ├─ SKILL.md — installation, when-to-use, command reference (8,736 bytes)
  ├─ references/
  │   ├─ labels.md — taxonomy (priority/type/status), color codes, bulk setup
  │   ├─ milestones.md — REST API CRUD, naming conventions, issue assignment
  │   ├─ projects-v2.md — GraphQL queries, field creation, item management
  │   └─ issue-stories.md — body template, lifecycle states, backlog field mapping
  └─ scripts/
      ├─ setup_gh.py — binary installation, platform detection, SHA256 verification
      ├─ github_project_setup.py — label/milestone/project automation (35,008 bytes)
      └─ experiment_cleanup.py — resource cleanup (6,298 bytes)
```

Source: Directory listing and file sizes (ls output from 2026-05-03)

---

## Installation & Usage

### Install gh binary

```bash
uv run .claude/skills/gh/scripts/setup_gh.py
```

Options:
- `--force` — reinstall even if latest version already present
- `--dry-run` — preview what would happen without installing
- `--bin-dir /path` — override default install directory

Source: SKILL.md lines 26-45

### Verify authentication

```bash
gh auth status
```

Requires `GITHUB_TOKEN` environment variable set. Automatically used by all subsequent `gh` commands.

Source: SKILL.md lines 52-58

### Example: List open pull requests with proxy remote

```bash
gh pr list -R Jamie-BitFlight/claude_skills
```

The `-R` flag is required in proxy environments. All `gh` subcommands support this flag.

Source: SKILL.md line 93

### Example: Create issue with labels and milestone

```bash
gh issue create -R Jamie-BitFlight/claude_skills \
  --title "feat: add feature X" \
  --label "priority:p1" --label "type:feature" \
  --milestone "v1.0"
```

Source: SKILL.md lines 118-121

### Automation: Full project setup

```bash
uv run .claude/skills/gh/scripts/github_project_setup.py setup \
  --repo Jamie-BitFlight/claude_skills
```

Performs label taxonomy creation, milestone initialization, and Projects V2 setup in a single command.

Source: SKILL.md line 167

### Direct GraphQL query

```bash
gh api graphql -f query='{ viewer { login } }'
```

Source: SKILL.md line 224

---

## Limitations and Caveats

1. **Proxy remote requirement**: The `-R owner/repo` flag is mandatory in any environment where the git remote does not resolve to `github.com`. Without this flag, `gh` fails with "failed to determine base repo: none of the git remotes configured for this repository point to a known GitHub host." — Source: SKILL.md line 69

2. **No native milestone subcommand**: Milestones are managed via the REST API (`gh api repos/...`) rather than a dedicated `gh milestone` subcommand. — Source: SKILL.md line 174

3. **Binary compatibility**: Installed binary is platform-specific. Cannot copy a Linux amd64 binary to a macOS or Windows system. Reinstalling on a different platform requires re-running setup_gh.py. — Implicit in architecture-specific release downloads documented in setup_gh.py

4. **SHA256 verification depends on release integrity**: The setup script verifies SHA256 checksums from the official GitHub Releases checksums file. If that file is unavailable or corrupted, installation will fail. — Source: setup_gh.py lines 34-35 (references checksum file download)

5. **Authentication fallback degrades rate limits**: When `GITHUB_TOKEN` authentication fails (401/403 status), the script prints an explicit warning (`:warning: Authenticated request failed (HTTP {code}), retrying anonymously`) and retries anonymously. This may result in lower rate limits (60 requests/hour for anonymous vs. 5,000 for authenticated). — Source: setup_gh.py lines 255-256

6. **Label and Projects automation are idempotent**: `github_project_setup.py` creates labels and projects only if they don't exist. Re-running is safe but does not update existing labels/projects. — Implied by "automation script" terminology at line 166

---

## Relevance to Claude Code Development

### Applications

- **Skill context**: The `gh` skill itself is invoked by orchestration code in this repository when GitHub Operations are needed (querying PR status, creating issues, checking workflow runs, managing labels)
- **Agent environments**: Any agent delegated work involving GitHub API (backlog management, issue creation, PR status checks) depends on `gh` being available with correct authentication
- **CI/CD integration**: GitHub Actions workflows reference `gh` commands; the skill ensures the binary is available in agent runtimes

### Patterns Worth Adopting

- **Extractive installation**: Downloading prebuilt binaries with SHA256 verification rather than source compilation — reduces setup time and avoids build tool dependencies
- **Automatic authentication from environment**: Leveraging `GITHUB_TOKEN` from the environment rather than requiring manual login — reduces agent initialization friction
- **Structured output modes**: Using `--json` and Go templates for programmatic parsing of `gh` output — enables reliable parsing in automation scripts

### Integration Opportunities

- **Backlog sync**: The skill could be extended to expose `gh` subcommands as MCP server functions (e.g., `list_issues()`, `create_milestone()`) for tighter agent integration
- **Proxy detection**: Enhance setup_gh.py to detect and document proxy configuration so agents don't need to manually pass `-R` flags
- **Cached metadata**: Cache GitHub release information (version, checksums) locally to reduce API calls during multi-agent workflows

---

## References

- [GitHub CLI Manual](https://cli.github.com/manual) (official reference) — accessed 2026-05-10
- [GitHub CLI Releases](https://github.com/cli/cli/releases) (binary downloads and checksums) — accessed 2026-05-10
- [GitHub REST API — Issues](https://docs.github.com/en/rest/issues) (milestones, labels, issue operations) — accessed 2026-05-10
- [GitHub Projects V2 API](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects) (GraphQL queries, custom fields) — accessed 2026-05-10
- [GitHub Releases API](https://docs.github.com/en/rest/releases) (release metadata endpoint) — accessed 2026-05-10
- Claude Skills Repository `.claude/skills/gh/SKILL.md` — local source (2026-05-03)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [backlog skill](./../task-management/backlog-skill.md) | task-management | `gh` provides GitHub Issue CRUD for backlog sync and project management |
| [research-curator skill](./../developer-tools/research-curator-skill.md) | developer-tools | Both are utility skills supporting repository and project operations |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-05-10 |
| Version at Verification | 2.87.2 (GitHub CLI), SKILL.md timestamp 2026-05-03 |
| Next Review Recommended | 2026-08-10 (3 months; moderate activity in gh CLI — new releases approximately monthly) |
| Confidence Map | Identity: high (version-verified), Features: high (documented with examples), Architecture: high (source code read), Installation: high (script verified), Limitations: medium (some inferred from design patterns) |

---

## Notes

- The skill provides both end-user documentation (SKILL.md with 50+ command examples) and automation infrastructure (two Python scripts for multi-step setup)
- Reference files document specific domain knowledge (label taxonomy, milestone API patterns, issue lifecycle) that would otherwise require external documentation lookups
- Installation script is self-contained with zero external dependencies beyond Python stdlib + httpx/typer (PEP 723)
- All commands documented use the `-R` flag pattern, making the skill immediately usable in proxy remote environments — a key constraint not obvious from GitHub CLI's upstream documentation
