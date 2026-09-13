---
name: git-cliff - Customizable Changelog Generator
description: git-cliff is a highly customizable changelog generator that creates structured changelogs from Git history using conventional commits and regex-powered custom parsers. Built in Rust for performance,...
license: Apache-2.0 / MIT (dual-licensed)
metadata:
  topic: git-cliff
  category: developer-tools
  source_url: https://git-cliff.org
  github: orhun/git-cliff
  version: "v2.12.0"
  verified: "2026-01-26"
  next_review: "2026-04-26"
---

## Overview

git-cliff is a highly customizable changelog generator that creates structured changelogs from Git history using conventional commits and regex-powered custom parsers. Built in Rust for performance, it supports multiple output formats through Tera templating and integrates with GitHub, GitLab, Gitea, and Bitbucket for remote metadata enrichment.

**Core Value Proposition**: Transform Git commit history into professional, customizable changelogs with zero manual effort, supporting both conventional commits and custom parsing rules.

---

## Problem Addressed

| Problem                                                | How git-cliff Solves It                                        |
| ------------------------------------------------------ | -------------------------------------------------------------- |
| Manually writing changelogs is tedious and error-prone | Automatic generation from Git commit messages                  |
| Different projects need different changelog formats    | Highly customizable Tera templates with 10+ built-in presets   |
| Conventional commits aren't universally adopted        | Regex-powered custom parsers work with any commit format       |
| Changelogs lack context like PR numbers and authors    | Remote metadata integration (GitHub, GitLab, Gitea, Bitbucket) |
| Keeping changelogs in sync with releases               | Prepend mode updates existing changelogs incrementally         |
| Monorepos need per-package changelogs                  | Built-in monorepo support with path-based filtering            |

---

## Key Statistics (as of January 26, 2026)

| Metric              | Value                      |
| ------------------- | -------------------------- |
| GitHub Stars        | 11,274                     |
| Forks               | 264                        |
| Contributors        | 30+                        |
| Open Issues         | 107                        |
| Primary Language    | Rust                       |
| Created             | May 2021                   |
| Latest Release      | v2.12.0 (January 20, 2026) |
| Crates.io Downloads | High (mature package)      |

---

## Key Features

### 1. Conventional Commits Support

- **Standard Prefixes**: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, etc.
- **Scopes**: Support for `feat(parser):` style scoped commits
- **Breaking Changes**: Detect `!` suffix (e.g., `feat!:`) and `BREAKING CHANGE:` footers
- **SemVer Correlation**: Automatic mapping to major/minor/patch versions

### 2. Custom Commit Parsers

- **Regex-Powered**: Define custom patterns for non-conventional commits
- **Group Mapping**: Map any commit pattern to changelog groups
- **Skip Patterns**: Filter out commits that shouldn't appear in changelog
- **Field Extraction**: Extract custom fields from commit messages

### 3. Templating System (Tera)

- **10+ Built-in Templates**: Basic, Keep a Changelog, GitHub, Minimal, Detailed, Scoped, etc.
- **Custom Templates**: Full Tera template language support
- **Conditional Logic**: Include/exclude sections based on content
- **Emoji Support**: Optional emoji prefixes for visual categorization

### 4. Remote Integration

- **GitHub**: PR titles, numbers, authors, labels as grouping keys
- **GitLab**: Merge request metadata
- **Gitea**: Self-hosted Git forge support
- **Bitbucket**: Bitbucket PR integration

### 5. Output Modes

- **Full Changelog**: Complete history from first commit
- **Latest Release**: Only changes since last tag
- **Unreleased**: Changes since last tag (for pre-release)
- **Range**: Specific commit range (e.g., `v1.0.0..HEAD`)
- **Prepend**: Update existing changelog with new entries

### 6. Monorepo Support

- **Path Filtering**: Generate changelogs for specific directories
- **Include/Exclude Paths**: Fine-grained control over which changes appear
- **Per-Package Changelogs**: Separate changelogs for monorepo packages

### 7. Configuration

- **TOML/YAML**: Configuration file support
- **Environment Overrides**: Override any config via environment variables
- **Global Config**: User-level defaults at `~/.config/git-cliff/cliff.toml`
- **Project Config**: Repository-level `cliff.toml`

---

## Technical Architecture

<eg>
Git Repository
      │
      ▼
┌─────────────────────────────────────────┐
│           git-cliff CLI                  │
│  ┌─────────────────────────────────┐    │
│  │      Commit Parser               │    │
│  │  - Conventional commits          │    │
│  │  - Custom regex patterns         │    │
│  │  - Scope extraction              │    │
│  └─────────────────────────────────┘    │
│                  │                       │
│                  ▼                       │
│  ┌─────────────────────────────────┐    │
│  │      Remote Metadata             │    │
│  │  - GitHub API                    │    │
│  │  - GitLab API                    │    │
│  │  - PR titles, authors, labels    │    │
│  └─────────────────────────────────┘    │
│                  │                       │
│                  ▼                       │
│  ┌─────────────────────────────────┐    │
│  │      Template Engine (Tera)      │    │
│  │  - Built-in templates            │    │
│  │  - Custom templates              │    │
│  │  - Conditional rendering         │    │
│  └─────────────────────────────────┘    │
│                  │                       │
│                  ▼                       │
│  ┌─────────────────────────────────┐    │
│  │      Output Formatter            │    │
│  │  - Markdown                      │    │
│  │  - JSON                          │    │
│  │  - Prepend/overwrite modes       │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
      │
      ▼
CHANGELOG.md / stdout / JSON
</eg>

---

## Installation & Usage

### Installation Options

```bash
# Cargo (Rust)
cargo install git-cliff

# Homebrew (macOS/Linux)
brew install git-cliff

# Arch Linux
pacman -S git-cliff

# NPM
npm install -g git-cliff

# Docker
docker run -t -v "$(pwd)":/app/ orhunp/git-cliff

# Nix
nix-env -iA nixpkgs.git-cliff
```

### Basic Usage

```bash
# Initialize configuration
git-cliff --init

# Generate full changelog
git-cliff -o CHANGELOG.md

# Generate for latest release only
git-cliff --latest

# Generate unreleased changes with tag
git-cliff --unreleased --tag 1.0.0

# Prepend to existing changelog
git-cliff --unreleased --tag 1.0.0 --prepend CHANGELOG.md
```

### Configuration Example (cliff.toml)

```toml
[changelog]
header = """
# Changelog\n
All notable changes to this project will be documented in this file.\n
"""
body = """
{% for group, commits in commits | group_by(attribute="group") %}
    ### {{ group | upper_first }}
    {% for commit in commits %}
        - {% if commit.scope %}*({{ commit.scope }})* {% endif %}{{ commit.message | upper_first }}
    {% endfor %}
{% endfor %}
"""
footer = """
<!-- generated by git-cliff -->
"""

[git]
conventional_commits = true
filter_unconventional = true
commit_parsers = [
    { message = "^feat", group = "Features" },
    { message = "^fix", group = "Bug Fixes" },
    { message = "^doc", group = "Documentation" },
    { message = "^perf", group = "Performance" },
    { message = "^refactor", group = "Refactor" },
    { message = "^style", group = "Styling" },
    { message = "^test", group = "Testing" },
    { message = "^chore\\(release\\)", skip = true },
]
```

### GitHub Integration Example

```toml
[remote.github]
owner = "orhun"
repo = "git-cliff"
token = "" # or use GITHUB_TOKEN env var

[changelog]
body = """
## What's Changed
{% for commit in commits %}
* {{ commit.message }} by @{{ commit.github.username }} in #{{ commit.github.pr_number }}
{% endfor %}
"""
```

---

## Output Template Examples

### Keep a Changelog Format

```markdown
# Changelog

## [Unreleased]

### Added
- Support multiple file formats

### Changed
- Use cache while fetching pages

## [1.0.1] - 2021-07-18

### Added
- Add release script

### Changed
- Expose string functions
```

### GitHub Release Format

```markdown
## What's Changed
* feat(cache): use cache while fetching pages by @orhun
* feat(config): support multiple file formats by @orhun

**Full Changelog**: https://github.com/owner/repo/compare/v1.0.0...v1.0.1
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Commit Message Skill**: Use git-cliff's conventional commit parsing as reference for commit message validation/generation
2. **Release Automation**: Integrate into plugin release workflows for automatic changelog generation
3. **Monorepo Support**: Pattern for per-plugin changelogs in multi-plugin repositories
4. **GitHub Integration**: PR metadata enrichment patterns applicable to code review workflows

### Patterns Worth Adopting

1. **Conventional Commits**: Standardized commit format improves AI comprehension of changes
2. **Regex-Based Parsing**: Flexible pattern matching for extracting structured data from text
3. **Template-Driven Output**: Tera templating pattern for customizable AI-generated content
4. **Prepend Mode**: Incremental update pattern preserving existing content
5. **Environment Overrides**: Configuration hierarchy (global → project → environment)

### Integration Opportunities

1. **commit-staged skill**: Could validate commits follow conventional format before generation
2. **push skill**: Auto-generate changelog entries on push
3. **Plugin releases**: Automate CHANGELOG.md generation for plugin marketplace
4. **PR descriptions**: Generate "What's Changed" sections from commit history

### Key Insight

git-cliff demonstrates that structured commit messages (conventional commits) enable powerful automation. This principle applies to Claude Code: structured, consistent formats in skills, agents, and commands enable better tooling and AI comprehension.

---

## References

1. **Official Website**: <https://git-cliff.org> (accessed 2026-01-26)
2. **GitHub Repository**: <https://github.com/orhun/git-cliff> (accessed 2026-01-26)
3. **Documentation**: <https://git-cliff.org/docs> (accessed 2026-01-26)
4. **Configuration Guide**: <https://git-cliff.org/docs/configuration> (accessed 2026-01-26)
5. **Template Examples**: <https://git-cliff.org/docs/templating/examples> (accessed 2026-01-26)
6. **Usage Examples**: <https://git-cliff.org/docs/usage/examples> (accessed 2026-01-26)
7. **Conventional Commits Specification**: <https://www.conventionalcommits.org/>
8. **Keep a Changelog**: <https://keepachangelog.com/>
9. **Tera Template Engine**: <https://keats.github.io/tera/>

---


---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [gstack](../agent-frameworks/gstack.md) | agent-frameworks | referenced by gstack (agent-frameworks) |

## Related Tools

| Tool                                                      | Relationship                                         |
| --------------------------------------------------------- | ---------------------------------------------------- |
| [cocogitto](https://github.com/oknozor/cocogitto)         | CLI for conventional commits + semver                |
| [release-plz](https://github.com/MarcoIeni/release-plz)   | Rust release automation using git-cliff              |
| [cliff-jumper](https://github.com/favware/cliff-jumper)   | NodeJS wrapper combining git-cliff + version bumping |
| [git-changelog](https://github.com/pawamoy/git-changelog) | Python alternative using Jinja2                      |
