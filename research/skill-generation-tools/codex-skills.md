---
name: codex-skills
description: codex-skills is a curated skill catalog for the OpenAI Codex CLI, providing drop-in skill folders that extend the agent with specialized workflows. Skills are installed into `~/.agents/skills/` and...
license: MIT
metadata:
  topic: codex-skills
  category: skill-generation-tools
  source_url: https://github.com/jMerta/codex-skills
  github: jMerta/codex-skills
  version: "v2.0.0"
  verified: "2026-02-20"
  next_review: "2026-05-20"
---

## Overview

codex-skills is a curated skill catalog for the OpenAI Codex CLI, providing drop-in skill folders that extend the agent with specialized workflows. Skills are installed into `~/.agents/skills/` and auto-discovered by Codex via `SKILL.md` frontmatter. A companion npm CLI (`npx codex-skills`) enables listing, searching, installing individual skills, and installing entire categories without cloning the repository.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Codex CLI ships with no built-in specialized workflows | Pre-built skills for git, CI, planning, docs, and operations give Codex immediate domain expertise |
| Reusing agent instructions across projects requires manual file copying | `npx codex-skills install <name>` copies a versioned skill folder into the standard catalog location |
| No standard convention for agent-context files (`AGENTS.md`) | `agents-md` skill + `init-ledger` command establish the ledger pattern for cross-session state |
| Prompt injection via invisible Unicode characters in agent inputs | CI pipeline runs `check_invisible_chars.py` on file contents, PR metadata, and commit messages |
| Hard-coded skill locations break when switching between user and repo scope | `--dir <dir>` flag selects between `~/.agents/skills/` (user) and `.agents/skills/` (repo-local) |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 116 | 2026-02-20 |
| Forks | 11 | 2026-02-20 |
| Contributors | 1 (jMerta) | 2026-02-20 |
| Latest Release | v2.0.0 | 2026-02-06 |
| Total Skills in Catalog | 19 | 2026-02-20 |
| npm package | codex-skills | 2026-02-20 |

---

## Key Features

### Skill Catalog (19 skills at v2.0.0)

- `plan-work` -- repo-grounded research, risk analysis, Q&A-gated implementation planning
- `bug-triage` -- reproduce, isolate, and fix bugs with root-cause summary
- `ci-fix` -- diagnose and fix GitHub Actions failures via `gh` CLI
- `commit-work` -- staged splitting + Conventional Commit message generation
- `create-pr` -- branch, lint/build, commit, and PR description with validation steps
- `coding-guidelines-gen` -- generate nested `AGENTS.md` per module, configure formatters/linters
- `coding-guidelines-verify` -- scoped compliance checks, auto-format, lint/test run
- `dependency-upgrader` -- safe incremental bump for Java/Kotlin (Gradle/Maven) and Node/TS
- `docs-sync` -- keep README, API docs, runbooks in sync with code changes
- `release-notes` -- draft changelogs and GitHub Release bodies from git ranges
- `agents-md` -- create/update root and nested `AGENTS.md` with module maps and feature maps
- `branch-cleaner` -- audit and prune stale git branches locally and on remotes
- `rebase-assistant` -- safe rebase onto target branch with conflict triage steps
- `regex-builder` -- build, test, explain regexes using `rg` and Python against sample files
- `vps-checkup` -- read-only Ubuntu VPS health/security report over SSH; applies changes only on confirmation
- `sessions-to-blog` -- convert session logs to MDX blog posts with project style rules
- Third-party: `create-cli` (steipete), `video-transcript-downloader` (steipete), `ui-ux-pro-max` (Next Level Builder)

### Skill Structure Convention

- Each skill is a directory containing `SKILL.md` (YAML frontmatter + Markdown body)
- Frontmatter fields: `name` (<=100 chars, single line), `description` (<=500 chars, single line)
- Optional subdirectories: `references/`, `scripts/`, `assets/`
- Only `name`, `description`, and SKILL.md path are injected into Codex context; bodies are loaded on demand

### CLI Tool (`npx codex-skills`)

- `list` / `ls` -- all skills grouped by category, supports `--json`
- `search <query>` -- search by name/description/category
- `install <name>` -- copy skill to skills directory from GitHub release tarball
- `install-category <category>` -- install all skills in a category
- `install-all` -- install every skill in the catalog
- `install-agent-scripts` -- install shared shell scripts alongside skills
- `init-ledger` -- create `~/.codex/AGENTS.MD` global context ledger
- `verify <name>` -- validate local skill install (SKILL.md + frontmatter)
- `--dir <dir>` flag for user (`~/.agents/skills/`) vs. repo-local (`.agents/skills/`) scope

### Global Ledger Pattern

- `init-ledger` creates `~/.codex/AGENTS.MD` as a cross-project agent context file
- Ledger headings: Goal, Constraints/Assumptions, Key decisions, State, Done/Now/Next, Open questions, Working set
- Not a skill -- applies globally to all Codex sessions across projects

### Security: Prompt-Injection Hardening

- `scripts/check_invisible_chars.py` scans file contents, filenames, PR metadata (title/body), and commit messages for invisible/suspicious Unicode characters (zero-width, directional overrides, etc.)
- GitHub Actions CI runs check on every push and PR
- Run locally: `python3 scripts/check_invisible_chars.py --all`

### Registry Maintenance Pipeline

- `skills-meta.json` -- category/author/license overrides per skill
- `skills.json` -- full machine-readable catalog generated by `scripts/build_skills_json.py`
- `scripts/validate_skills.py` -- validates SKILL.md frontmatter (no PyYAML dependency since v2.0.0)
- GitHub Pages at `https://jmerta.github.io/codex-skills/` publishes the catalog on each release

---

## Technical Architecture

<eg>
codex-skills/
  <skill-name>/
    SKILL.md            # YAML frontmatter (name, description) + Markdown workflow body
    references/         # Extended templates, checklists (loaded on demand)
    scripts/            # Optional helper scripts for the skill
    assets/             # Optional assets
  agent-scripts/        # Shared shell scripts installable via install-agent-scripts
  agents-md/            # agents-md skill
  cli/
    bin/codex-skills.js # npm CLI entry point (Node.js, single dependency: tar)
    package.json        # npm package definition (name: codex-skills, v2.0.0)
    test/               # Node.js built-in test runner
  scripts/
    build_skills_json.py    # Regenerates skills.json from skill folders + skills-meta.json
    validate_skills.py      # Validates SKILL.md frontmatter (stdlib only)
    check_invisible_chars.py # Scans for Unicode prompt-injection vectors
  skills.json           # Machine-readable catalog (version, total, skills array, categories)
  skills-meta.json      # Overrides for category/author/license per skill
  AGENTS.md             # Repo-scoped agent instructions
  LEDGER-PATTERN.md     # Documentation of the cross-session ledger pattern
</eg>

Codex discovery mechanism:

- User scope: `~/.agents/skills/**/SKILL.md` (legacy: `~/.codex/skills/**/SKILL.md`)
- Repo scope: `.agents/skills/**/SKILL.md`
- Only `name`, `description`, and path from frontmatter enter Codex context; full SKILL.md body is read on demand

CLI install mechanism:

- Fetches `skills.json` from the selected GitHub ref (latest release by default, `--ref` to override)
- Downloads repo tarball for the ref via GitHub API
- Extracts only the requested skill folder into the target directory

---

## Installation & Usage

```bash
# Clone entire catalog as user skills
git clone https://github.com/jMerta/codex-skills.git ~/.agents/skills

# Or use npx CLI (no clone required)
npx codex-skills list
npx codex-skills search git
npx codex-skills install commit-work
npx codex-skills install-category development
npx codex-skills install-all
npx codex-skills install-all --dir .agents/skills   # repo-local

# Initialize global ledger
npx codex-skills init-ledger

# Verify a skill install
npx codex-skills verify commit-work

# Install shared agent scripts and add to PATH
npx codex-skills install-agent-scripts
export PATH="$PATH:$HOME/.agents/skills/agent-scripts"
```

```toml
# Enable skills permanently in ~/.codex/config.toml
[features]
skills = true
```

```bash
# Validate the catalog (no external dependencies)
python3 scripts/validate_skills.py

# Rebuild skills.json after adding/renaming skills
python3 scripts/build_skills_json.py

# Scan for invisible Unicode characters
python3 scripts/check_invisible_chars.py --all
```

---

## Relevance to Claude Code Development

### Applications

- Directly analogous to this repository's plugin/skill system: both use SKILL.md (or equivalent) with YAML frontmatter to define name and description, store workflow bodies in Markdown, and keep extended content in `references/` subdirectories
- The ledger pattern (`AGENTS.MD` with Goal/Constraints/State/Done/Now/Next headings) maps to cross-session state management for Claude Code agent workflows
- The `coding-guidelines-gen` and `coding-guidelines-verify` skills demonstrate how to generate and enforce nested `AGENTS.md` per module -- applicable to monorepo plugin structures
- The `ci-fix` skill's approach (inspect `gh` run logs, identify root cause, patch workflow, rerun) mirrors the CI Workflow Modification Protocol in CLAUDE.md

### Patterns Worth Adopting

- **Minimal frontmatter constraint**: name <=100 chars single-line, description <=500 chars single-line -- a stricter bound than currently enforced here; reduces context injection noise
- **Stdlib-only validation**: `validate_skills.py` requires no external dependencies (no PyYAML) -- important for zero-setup CI
- **Prompt-injection CI check**: `check_invisible_chars.py` scanning PR metadata and commit messages is a security pattern applicable to any AI-assisted workflow repository
- **`--dir` scope flag**: user vs. repo-local install target with a single flag -- cleaner UX than two separate install paths
- **Registry as generated artifact**: `skills.json` is regenerated from source of truth (`skills-meta.json` + skill folders) rather than hand-maintained -- reduces drift

### Integration Opportunities

- codex-skills skill definitions (SKILL.md) could be cross-referenced or ported as Claude Code plugin skills, since both formats share the same YAML frontmatter + Markdown body convention
- The `check_invisible_chars.py` script could be added as a pre-commit hook or CI check in this repository's `.pre-commit-config.yaml`
- The `plan-work` skill's Q&A-gate pattern (research -> analysis -> ask before implementing) is a behavioral protocol worth encoding in agent delegation prompts here

---

## References

- [jMerta/codex-skills GitHub repository](https://github.com/jMerta/codex-skills) (accessed 2026-02-20)
- [codex-skills v2.0.0 release notes](https://github.com/jMerta/codex-skills/releases/tag/2.0.0) (accessed 2026-02-20)
- [skills.json catalog (v2.0.0)](https://raw.githubusercontent.com/jMerta/codex-skills/main/skills.json) (accessed 2026-02-20)
- [GitHub Pages catalog](https://jmerta.github.io/codex-skills/) (accessed 2026-02-20)
- [npm: codex-skills](https://www.npmjs.com/package/codex-skills) (accessed 2026-02-20)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [awesome-codex-skills-issue-triage](./awesome-codex-skills-issue-triage.md) | skill-generation-tools | referenced by awesome-codex-skills-issue-triage (skill-generation-tools) |
