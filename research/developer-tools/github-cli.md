---
name: GitHub CLI (gh)
description: GitHub CLI (gh) is the official command-line interface for GitHub, enabling developers to manage issues, pull requests, repositories, releases, workflows, and extensions directly from the terminal....
license: MIT
metadata:
  topic: github-cli
  category: developer-tools
  source_url: https://cli.github.com
  github: cli/cli
  version: "v2.64.0"
  verified: "2026-02-20"
  next_review: "2026-05-20"
---

## Overview

GitHub CLI (gh) is the official command-line interface for GitHub, enabling developers to manage issues, pull requests, repositories, releases, workflows, and extensions directly from the terminal. Written in Go, it provides a scriptable alternative to the web UI for GitHub operations, with built-in authentication, extension system, and comprehensive API access through `gh api`.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Context switching between terminal and web UI disrupts developer flow | Provides complete GitHub functionality from command line with authentication handled via `GITHUB_TOKEN` or `gh auth login` |
| PR creation requires manual web form filling with loss of terminal context | `gh pr create` with flags or interactive prompts creates PRs with title, body, reviewers, and labels from current branch |
| CI/CD debugging requires navigating web UI to view workflow logs | `gh run list`, `gh run view`, `gh run watch` provide workflow status, logs, and real-time updates in terminal |
| Scriptable GitHub automation requires custom API client implementation | `gh api` provides authenticated REST and GraphQL access with automatic pagination and JSON handling |
| Repository cloning requires manual URL lookup and copying | `gh repo clone owner/repo` clones with authentication, fork detection, and automatic remote configuration |
| Issue management fragmented across web UI and email notifications | `gh issue list`, `gh issue create`, `gh issue view` enable full issue lifecycle management with custom filters and formatting |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 37,800+ | 2026-02-20 |
| Contributors | 500+ | 2026-02-20 |
| Latest Release | v2.64.0 | 2026-02-15 |
| Package Managers | 10+ (apt, yum, brew, winget, conda, scoop) | 2026-02-20 |
| Official Extensions | 50+ in marketplace | 2026-02-20 |
| Supported Platforms | Linux, macOS, Windows, BSD | 2026-02-20 |

---

## Key Features

### Pull Request Management

- `gh pr create` - Create PRs with interactive prompts or flags for title, body, reviewers, assignees, labels, projects, milestone
- `gh pr list` - List PRs with filters (state, author, label, base branch, search query)
- `gh pr view` - Display PR details, comments, status checks, and diff
- `gh pr checkout` - Check out PR branch locally by number or URL
- `gh pr review` - Submit reviews (approve, request changes, comment) from command line
- `gh pr merge` - Merge PRs with merge strategies (merge, squash, rebase) and auto-delete branch
- `gh pr diff` - Show PR file changes in terminal with syntax highlighting
- `gh pr checks` - View status checks and CI/CD results for PR
- `gh pr comment` - Add comments to PRs with markdown support

### Issue Management

- `gh issue create` - Create issues with title, body, assignees, labels, projects, milestone
- `gh issue list` - List issues with filters (state, author, assignee, label, mention, search)
- `gh issue view` - Display issue details, comments, timeline, and linked PRs
- `gh issue close/reopen` - Change issue state with optional comment
- `gh issue comment` - Add comments to issues
- `gh issue edit` - Edit issue title, body, assignees, labels, projects, milestone
- `gh issue transfer` - Transfer issues between repositories
- `gh issue develop` - Create branch and link to issue

### Repository Operations

- `gh repo clone` - Clone repositories with authentication, fork detection, sparse checkout
- `gh repo create` - Create repositories (public/private, with template, .gitignore, license)
- `gh repo fork` - Fork repositories with option to clone and configure upstream
- `gh repo view` - Display repository information (description, URL, stars, forks, topics)
- `gh repo list` - List repositories for user or organization with filters
- `gh repo sync` - Sync fork with upstream
- `gh repo archive/unarchive` - Archive or unarchive repositories
- `gh repo delete` - Delete repositories with confirmation
- `gh repo rename` - Rename repositories

### Workflow and CI/CD

- `gh run list` - List workflow runs with filters (workflow, branch, event, status, created date)
- `gh run view` - Display run details, jobs, steps, and logs
- `gh run watch` - Watch run in real-time with live updates
- `gh run download` - Download workflow run artifacts
- `gh run rerun` - Re-run failed jobs or entire workflow
- `gh run cancel` - Cancel in-progress workflow runs
- `gh workflow list` - List workflows in repository
- `gh workflow view` - Display workflow YAML and recent runs
- `gh workflow run` - Trigger workflow with inputs
- `gh workflow enable/disable` - Enable or disable workflows

### Release Management

- `gh release create` - Create releases with tag, title, notes, assets, prerelease flag
- `gh release list` - List releases with pagination
- `gh release view` - Display release details and assets
- `gh release download` - Download release assets with pattern matching
- `gh release delete` - Delete releases and tags
- `gh release edit` - Edit release title, notes, draft/prerelease status
- `gh release upload` - Upload additional assets to existing release

### API Access

- `gh api` - Make authenticated REST API requests with automatic pagination
- GraphQL support via `gh api graphql` with query from file or stdin
- Response filtering with `--jq` flag for JSON processing
- Custom headers with `--header` flag
- Request methods (GET, POST, PUT, PATCH, DELETE) via `--method` flag
- Templated URLs with variable substitution (e.g., `repos/{owner}/{repo}`)
- Raw mode with `--raw-field` for non-JSON field values
- Automatic authentication using `GITHUB_TOKEN` or `gh auth` credentials

### Extension System

- `gh extension install owner/repo` - Install extensions from GitHub repositories
- `gh extension list` - List installed extensions
- `gh extension upgrade` - Upgrade extensions to latest version
- `gh extension remove` - Uninstall extensions
- `gh extension create` - Scaffold new extension (precompiled Go, script-based)
- `gh extension browse` - Browse extension marketplace
- Extensions written in any language (Go, Bash, Python, Ruby, Node.js)
- Extensions can use `gh` commands and API access
- Local extensions supported via symlinks for development

### Authentication and Configuration

- `gh auth login` - Interactive authentication with GitHub.com or GitHub Enterprise
- `gh auth status` - Display authentication status and token scopes
- `gh auth refresh` - Refresh authentication token with additional scopes
- `gh auth logout` - Remove authentication credentials
- `gh auth setup-git` - Configure git to use gh for authentication
- `GITHUB_TOKEN` environment variable support for non-interactive auth
- Multiple account support with `--hostname` flag
- SSH and HTTPS protocol selection
- `gh config set` - Configure preferences (editor, git protocol, browser)
- `gh config get` - Retrieve configuration values

---

## Technical Architecture

### Core Components

**Command Structure**:
- Top-level commands: `auth`, `repo`, `pr`, `issue`, `release`, `run`, `workflow`, `api`, `extension`, `config`, `alias`
- Sub-commands follow resource-verb pattern: `gh pr create`, `gh issue list`, `gh repo view`
- Flags use consistent naming: `--repo`, `--limit`, `--state`, `--json`, `--jq`, `--web`

**Authentication Flow**:

<eg>
gh command invoked
    ↓
Check for GITHUB_TOKEN in environment
    ↓ (if not found)
Check for credentials in keyring/config (~/.config/gh/hosts.yml)
    ↓ (if not found)
Prompt for authentication via gh auth login
    ↓
Store credentials securely (keyring on macOS/Windows, encrypted file on Linux)
    ↓
Use credentials for API requests with automatic token refresh
</eg>

**API Request Pattern**:

<eg>
gh api repos/cli/cli
    ↓
Parse endpoint URL (REST or GraphQL)
    ↓
Resolve variables ({owner}/{repo} → cli/cli)
    ↓
Add authentication header (Authorization: token <TOKEN>)
    ↓
Make HTTP request to api.github.com
    ↓
Handle pagination if --paginate flag set
    ↓
Filter response with --jq if specified
    ↓
Output JSON or formatted text
</eg>

**Extension Discovery**:

<eg>
gh <extension-name>
    ↓
Check for built-in command
    ↓ (if not found)
Search ~/.local/share/gh/extensions/ for gh-<extension-name>
    ↓ (if found)
Execute extension binary or script
    ↓
Extension can call gh commands recursively
    ↓
Extension output returned to user
</eg>

### Repository Detection

GitHub CLI auto-detects the current repository from:

1. Git remote URLs (`origin` by default, configurable)
2. Current working directory (must be inside git repository)
3. `--repo` flag for explicit specification (`-R owner/repo`)

**Note**: When git remote points to non-GitHub host (e.g., `127.0.0.1` proxy), `gh` cannot auto-detect repository and requires `-R` flag on every command.

### Output Formats

- **Default**: Human-readable formatted text with colors
- **JSON** (`--json`): Machine-readable JSON with field selection
- **Template** (`--template`): Go template formatting
- **JQ** (`--jq`): JSON filtering with jq syntax
- **TSV** (`--tsv`): Tab-separated values for scripting

---

## Installation & Usage

### Installation

```bash
# Debian/Ubuntu
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
  | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install gh

# macOS
brew install gh

# Windows (via winget)
winget install --id GitHub.cli

# From source
go install github.com/cli/cli/v2/cmd/gh@latest
```

### Authentication

```bash
# Interactive login (opens browser for OAuth flow)
gh auth login

# Use token from environment variable
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx

# Check authentication status
gh auth status

# Setup git credential helper
gh auth setup-git
```

### Common Workflows

#### Creating a Pull Request

```bash
# Create PR interactively
gh pr create

# Create PR with flags
gh pr create --title "Add feature X" --body "Implements feature X with tests" \
  --reviewer user1,user2 --label feature --base main

# Create PR with body from file
gh pr create --title "Add feature X" --body-file PR_TEMPLATE.md

# Create draft PR
gh pr create --draft --title "WIP: Feature X"
```

#### Managing Issues

```bash
# List open issues assigned to me
gh issue list --assignee @me --state open

# Create issue with template
gh issue create --template bug_report.md

# View issue with comments
gh issue view 123 --comments

# Close issue with comment
gh issue close 123 --comment "Fixed in #456"
```

#### Working with Workflows

```bash
# List recent workflow runs
gh run list --limit 10

# View specific run with logs
gh run view 12345 --log

# Watch run in real-time
gh run watch

# Download artifacts
gh run download 12345 --name artifact-name

# Re-run failed jobs
gh run rerun 12345 --failed
```

#### Using the API

```bash
# Get repository information
gh api repos/cli/cli

# Get rate limit status
gh api rate_limit

# Create issue via API
gh api repos/cli/cli/issues -f title="Issue title" -f body="Issue description"

# GraphQL query
gh api graphql -f query='
  query {
    viewer {
      login
      name
    }
  }
'

# Paginate through all PRs
gh api repos/cli/cli/pulls --paginate --jq '.[].number'
```

#### Working with Remote Proxy (Claude Code Context)

```bash
# When git remote points to proxy (127.0.0.1), use -R flag
gh run list -R owner/repo --limit 5
gh pr view 123 -R owner/repo
gh api repos/owner/repo -R owner/repo

# Set GH_REPO environment variable to avoid -R on every command
export GH_REPO=owner/repo
gh run list --limit 5
```

---

## Relevance to Claude Code Development

### Applications

**Automated PR Creation in AI Workflows**:
- Claude Code can execute `gh pr create` to create PRs from implemented features
- Supports structured PR body with Summary, Test plan, and session URL
- Enables automated reviewer assignment and label application
- Replaces manual web UI navigation with scriptable PR workflow

**CI/CD Interaction and Debugging**:
- Claude Code can use `gh run view --log-failed` to diagnose workflow failures
- Real-time workflow monitoring with `gh run watch` for immediate feedback
- Artifact download with `gh run download` for post-processing analysis
- Workflow re-triggering with `gh workflow run` for testing CI changes

**Issue Management from Terminal**:
- Claude Code can create issues for discovered bugs with `gh issue create`
- Link PRs to issues automatically with `gh pr create --issue 123`
- Track issue status and comments without context switching
- Close issues with PR references via `gh issue close --comment "Fixed in #PR"`

**Repository Intelligence Gathering**:
- `gh repo view --json` provides repository metadata for analysis
- `gh api repos/{owner}/{repo}` accesses full repository information
- Contributor statistics via `gh api repos/{owner}/{repo}/contributors`
- Release history via `gh release list` for version tracking

**Extension-Based Customization**:
- Claude Code can recommend or install extensions for specialized workflows
- Extensions enable custom commands for project-specific operations
- Script-based extensions allow Python/Bash integration with gh commands
- Local extension development for prototyping new automation

### Patterns Worth Adopting

**Consistent Flag Naming Across Commands**:
- `--repo`/`-R` for repository specification (applies to all commands)
- `--json` for machine-readable output (standardized field names)
- `--jq` for response filtering (consistent across all JSON outputs)
- `--web` flag to open resource in browser (fallback UI option)

**Automatic Repository Detection with Explicit Override**:
- Auto-detect from git remote when possible (reduces friction)
- Provide explicit override (`-R`) when auto-detection fails (proxy scenario)
- Clear error messages when detection fails with remediation steps
- Environment variable override (`GH_REPO`) for session-level defaults

**Pagination Handling**:
- Default limits (30 items) prevent overwhelming output
- `--paginate` flag for complete data retrieval
- `--limit` flag for explicit result count control
- Transparent pagination in API mode with automatic continuation

**Output Format Flexibility**:
- Human-readable default for interactive use
- `--json` with field selection for programmatic consumption
- `--template` for custom formatting requirements
- `--tsv` for shell script integration (easy `cut`/`awk` processing)

**Authentication Abstraction**:
- Single `gh auth login` handles multiple authentication methods (OAuth, token, SSH)
- Credentials stored securely in platform keyring
- `GITHUB_TOKEN` environment variable for CI/CD contexts
- Automatic token refresh with scope expansion on demand

### Integration Opportunities

**Claude Code Hook for PR Verification**:
- Create pre-push hook that uses `gh pr checks` to verify branch has passing CI
- Block pushes if required status checks are failing
- Display check failures inline with suggestions for fixes
- Integration point: `.claude/hooks/pre-push.js`

**Automated PR Workflow Enhancement**:
- Extend current PR creation logic to use `gh pr create --body "$(cat <<'EOF'...)"` pattern
- Replace heredoc commit message pattern with heredoc PR body pattern
- Add `gh pr view <pr-number> --comments` to fetch PR feedback for iteration
- Integration point: Project instructions GitHub PR creation section

**CI/CD Workflow Debugging Skill**:
- New skill that uses `gh run list`, `gh run view --log-failed`, `gh workflow view`
- Analyzes workflow failures and suggests fixes based on error patterns
- Downloads artifacts for local inspection with `gh run download`
- Integration point: New skill in `plugins/developer-tools/skills/ci-debugger/`

**Issue Tracking from Session Context**:
- Hook that creates issues for unresolved errors at session end
- Uses `gh issue create` with structured template (error, context, session URL)
- Labels issues with error type (linting, test failure, build error)
- Integration point: `.claude/hooks/session-end.js`

**Repository Analytics Agent**:
- Agent that uses `gh api` to gather repository metrics (stars, forks, contributors, activity)
- Generates trend analysis using historical data from `gh api repos/{owner}/{repo}/stats`
- Produces reports comparing repository health across multiple repos
- Integration point: New agent in `.claude/agents/repo-analyst.md`

**Extension Development Pattern**:
- Document pattern for creating gh extensions within Claude Code projects
- Extension template with PEP 723 for Python-based extensions
- Integration with existing skill system (skill → gh extension mapping)
- Integration point: Reference in `plugins/plugin-creator/references/extension-patterns.md`

---

## References

- [GitHub CLI Official Documentation](https://cli.github.com/manual/) (accessed 2026-02-20)
- [GitHub CLI Repository - cli/cli](https://github.com/cli/cli) (accessed 2026-02-20)
- [GitHub CLI Manual Pages](https://cli.github.com/manual/gh) (accessed 2026-02-20)
- [GitHub REST API Documentation](https://docs.github.com/en/rest) (accessed 2026-02-20)
- [GitHub CLI Extension Development](https://docs.github.com/en/github-cli/github-cli/creating-github-cli-extensions) (accessed 2026-02-20)
- [Claude Skills Repository - gh CLI Usage](https://github.com/Jamie-BitFlight/claude_skills/blob/main/.claude/CLAUDE.md#github-cli-gh-usage) (accessed 2026-02-20)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [claude-code-cli-power-patterns](./claude-code-cli-power-patterns.md) | developer-tools | referenced by claude-code-cli-power-patterns (developer-tools) |
| [emqutiti](./emqutiti.md) | developer-tools | referenced by emqutiti (developer-tools) |
| [sidecar](./sidecar.md) | developer-tools | referenced by sidecar (developer-tools) |
| [awesome-codex-skills-issue-triage](../skill-generation-tools/awesome-codex-skills-issue-triage.md) | skill-generation-tools | referenced by awesome-codex-skills-issue-triage (skill-generation-tools) |
| [composio-codebase-migrate](../skill-generation-tools/composio-codebase-migrate.md) | skill-generation-tools | referenced by composio-codebase-migrate (skill-generation-tools) |
