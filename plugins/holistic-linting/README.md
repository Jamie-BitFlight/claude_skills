<p align="center">
  <img src="./assets/hero.png" alt="Holistic Linting" width="800" />
</p>

# Holistic Linting

This plugin changes how Claude handles code quality. Instead of declaring work done after writing code, Claude automatically discovers your project's linters, formats and lints every modified file, and resolves errors at root cause — before reporting completion.

## Why Install This?

When you ask Claude to write or modify code, Claude sometimes:

- Says "all done!" but leaves linting errors in the code
- Adds `# type: ignore` or `# noqa` comments to silence errors instead of fixing them
- Assumes only two linters exist (mypy and ruff), missing basedpyright, bandit, or pre-commit hooks
- Forgets to run formatters before finishing

This plugin makes linting a required gate, not an afterthought.

## What You Get

### Automatic quality gate

Before marking any task complete, Claude:

1. Scans your project configuration files (`pyproject.toml`, `.pre-commit-config.yaml`, `package.json`, `.eslintrc*`, `.markdownlint.json`, etc.) to discover which linters you actually use
2. Runs formatters (ruff format, prettier) to fix trivial whitespace issues
3. Runs all detected linters concurrently
4. Investigates each error at root cause using the bundled rules knowledge base
5. Re-runs linters to confirm all issues are resolved
6. Reports pre-existing issues found in unmodified files

### Hard suppression gate

Claude is prohibited from resolving linting errors via suppression. All of the following are blocked:

- Inline suppression comments (`# type: ignore`, `# noqa`, `# pyright: ignore`, `# pylint: disable`)
- Configuration-level suppression (adding rules to `[tool.ruff.lint] ignore`, `disable_error_code`, per-file-ignores)
- Severity downgrades in linter config files
- Deleting code to eliminate the error containing it

If an error cannot be resolved through code changes, Claude reports it as UNRESOLVED with documentation of what was attempted, for a human decision.

### Bundled rules knowledge base

The plugin ships with reference documentation for:

- ruff rules, documented by rule family (see `references/rules/ruff/index.md`)
- mypy error codes (organized by category)
- bandit security checks (see `references/rules/bandit/`)

Claude references these during root-cause investigation rather than guessing at fix strategies.

### Skills

| Skill | When it activates |
|---|---|
| `holistic-linting` | Core skill — linter detection, formatting, resolution. Activated automatically on task completion or via `/lint` |
| `holistic-linting-orchestrator` | Guides orchestrators on delegating linting work to concurrent agents |
| `holistic-linting-resolver` | Linter-specific resolution procedures for sub-agents (ruff, mypy, pyright, basedpyright workflows) |

### Agents

| Agent | Purpose |
|---|---|
| `linting-root-cause-resolver` | Investigates and fixes linting errors. Loads project context, researches rule documentation, applies Python 3.11+ standards |
| `post-linting-architecture-reviewer` | Reviews resolution quality after fixes — validates alignment with codebase patterns, identifies systemic improvements |

### Commands

> **Spelling note**: The plugin name is `holistic-linting` — one `l` in `holistic`. A common misspelling is `hollistic` (double `l`), which resolves to nothing. The install name and all skill invocations use the single-`l` spelling.

#### `/lint [files...]`

Shorthand for activating the holistic-linting skill on specific files:

```text
/lint src/auth.py
/lint src/*.py
/lint path/to/directory/
```

Runs the full workflow: linter detection, formatting, linting, root-cause resolution via specialized agents, and verification.

## Installation

First, add the marketplace (one-time setup):

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
```

Then install the plugin:

```bash
/plugin install holistic-linting@jamie-bitflight-skills
```

## Usage

### Automatic behavior

Just install it. Claude applies the quality gate automatically when finishing code tasks.

**For orchestrators** (interactive Claude Code CLI): Claude delegates to `linting-root-cause-resolver` agents — it does not run linters directly. Agents run formatters, lint, and resolve issues; Claude reads their resolution report.

**For sub-agents** (delegated tasks): Claude formats and lints files it modified before completing the task, resolves issues, and verifies the fix.

### Manual invocation

Invoke on specific files when you want linting on demand:

```text
/lint src/auth.py src/utils.py
```

Or invoke the skill directly:

```text
/holistic-linting:holistic-linting src/
```

## Example

**Without this plugin**:

```text
You: "Add authentication to the API"
Claude: [writes auth.py]
Claude: "Done! Authentication middleware added."

You: [runs ruff check]
ruff: 5 errors in auth.py
You: "There are linting errors..."
```

**With this plugin**:

```text
You: "Add authentication to the API"
Claude: [writes auth.py]
Claude: [delegates to linting-root-cause-resolver]
  Agent: ruff format auth.py — clean
  Agent: ruff check auth.py — 3 errors found
  Agent: mypy auth.py — 2 type errors found
  Agent: [investigates each error, fixes at root cause]
  Agent: [re-runs: all checks clean]
Claude: "Done! Authentication middleware added. ruff and mypy both pass."
```

## Supported Linters

| Language | Tools |
|---|---|
| Python | ruff, mypy, pyright, basedpyright, bandit |
| JavaScript / TypeScript | eslint, prettier |
| Shell | shellcheck, shfmt |
| Markdown | markdownlint |
| Pre-commit | pre-commit, prek (takes priority if configured) |

Linter detection is automatic — Claude scans your project configuration files and uses whatever is configured. If `pre-commit` or `prek` is configured, it takes priority and runs all hooks.

## Requirements

- Claude Code v2.0+
- Linters installed in your project (ruff, mypy, eslint, etc.)

---

> **The Ancient Woe**
>
> *The vanity and rage of a Duke who dons his finest velvet doublet, only to find a single, maddening loose thread upon the sleeve.*

> **The Bard's Decree**
>
> *"Thou shalt not present this garment to me and declare it 'finished'! Seamstress, fetch thy shears! We leave the chamber only when the fabric is flawless!"*
