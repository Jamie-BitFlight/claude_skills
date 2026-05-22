---
name: holistic-linting
description: Comprehensive linting and formatting verification workflows. Provides automatic format-lint-resolve pipelines for orchestrators and sub-agents. Use when running linters, fixing ruff/mypy/bandit errors, ensuring code quality before completion, or resolving linting issues systematically.
---

# Holistic Linting Skill

This skill embeds comprehensive linting and formatting verification into Claude Code's workflow, preventing the common pattern where code is claimed "production ready" without actually running quality checks.

## Purpose

Prevent Claude from:

- Completing tasks without formatting and linting modified files
- Claiming code is "production quality" based on pattern-matching rather than verification
- Assuming only 2 linters exist (mypy + ruff) when projects may have 4+ linting tools (basedpyright, bandit, etc.)
- Suppressing linting errors with `# type: ignore` or `# noqa` comments without understanding root causes

Ensure Claude:

- Automatically formats and lints all modified files before task completion
- Discovers project linters by scanning configuration files (pyproject.toml, .pre-commit-config.yaml, package.json)
- Resolves linting issues systematically using root-cause analysis
- Orchestrates concurrent linting agents when multiple files have issues

## When This Skill Applies

This skill applies to **all code editing tasks** in projects with linting configuration. It provides different behavior based on Claude's role:

### For Orchestrators (Interactive Claude Code CLI)

After completing implementation work, orchestrators MUST delegate to specialized agents. See the [holistic-linting-orchestrator skill](../holistic-linting-orchestrator/SKILL.md) for complete delegation workflows.

**Quick reference**:

1. **Delegate immediately** - Launch linting-root-cause-resolver agent for modified files
2. **Read reports** - Agent produces resolution reports in `.claude/reports/`
3. **Delegate review** - Launch post-linting-architecture-reviewer to validate resolution quality
4. **Iterate if needed** - Re-delegate to resolver if reviewer identifies issues

**CRITICAL**: Orchestrators do NOT run formatting or linting commands themselves. The agent gathers its own linting data, formats files, runs linters, and resolves issues. Orchestrators only delegate tasks and read completion reports.

### For Sub-Agents (Task-delegated agents)

Before completing any task that involved Edit/Write:

1. **Format touched files** - Run formatters on files the agent modified
2. **Lint touched files** - Run linters on files the agent modified
3. **Resolve issues directly** - Use linting tools directly to fix issues
4. **Don't complete** - Don't mark task complete until all linting issues in touched files are resolved

For detailed resolution workflows, see the [holistic-linting-resolver skill](../holistic-linting-resolver/SKILL.md).

## How to Use This Skill

### Automatic Behavior

This skill modifies Claude's standard workflow to include automatic quality checks:

**Before this skill**:

```text
[User request] → [Code changes] → [Task complete ✓]
```

**With this skill (Orchestrator)**:

```text
[User request] → [Code changes] → [Delegate to linting agent] → [Read reports] → [Task complete ✓]
```

**With this skill (Sub-Agent)**:

```text
[Task assigned] → [Code changes] → [Format] → [Lint] → [Resolve issues] → [Task complete ✓]
```

### Linter Detection

Linter detection is handled automatically by scanning project configuration files. The linting hook's `ConfigurationDetector` identifies available tools at runtime by checking:

| Config File                    | Tools Detected                                       |
| ------------------------------ | ---------------------------------------------------- |
| `.pre-commit-config.yaml`      | pre-commit/prek hooks (takes priority, skips others) |
| `.husky/` directory            | Husky git hooks                                      |
| `pyproject.toml`               | Ruff, MyPy, basedpyright, bandit                     |
| `package.json`, `.eslintrc*`   | ESLint                                               |
| `package.json`, `.prettierrc*` | Prettier                                             |
| `.clang-format`                | clang-format (C/C++)                                 |
| `.rubocop.yml`                 | RuboCop (Ruby)                                       |
| `.shellcheckrc`                | ShellCheck (shell scripts)                           |
| `.markdownlint.json/.yaml`     | markdownlint                                         |

**Detection Priority** (highest to lowest):

1. Pre-commit/prek (if found, uses hooks exclusively)
2. Husky
3. Language-specific tools (Python → JS/TS → Shell → etc.)

The detection uses caching with a 5-minute TTL to avoid repeated disk reads.

### Running Formatters and Linters

**Git Hook Tool Detection** (if `.pre-commit-config.yaml` exists):

Use the detection script to identify and run the correct tool:

```bash
# Detect tool (outputs 'prek' or 'pre-commit')
uv run ./scripts/detect_hook_tool.py

# Run detected tool with arguments
uv run ./scripts/detect_hook_tool.py run --files path/to/file.py

# Check different repository on specific files
uv run ./scripts/detect_hook_tool.py --directory /path/to/repo run --files path/to/file.py
```

**Important - Scoped Operations**: Always use `--files` or staged file patterns rather than `--all-files`. Running hooks on all files formats code outside your current branch, causing:

- **Diff pollution**: Unrelated formatting changes appear in merge requests
- **Merge conflicts**: Changes to files not part of your feature
- **Broken git blame**: History attribution lost for mass-formatted files

Use `--all-files` ONLY when explicitly requested by the user for repository-wide cleanup.

Detection logic: reads `.git/hooks/pre-commit` line 2, token 5 identifies the tool. Defaults to `prek` if file missing.

**Note**: prek is a Rust-based drop-in replacement for pre-commit. Both tools use the same `.pre-commit-config.yaml` and have identical CLI interfaces.

**For Python files**:

```bash
# Format first (auto-fixes trivial issues)
uv run ruff format path/to/file.py

# Then lint (reports substantive issues)
uv run ruff check path/to/file.py
uv run mypy path/to/file.py
uv run pyright path/to/file.py
```

**For JavaScript/TypeScript files**:

```bash
# Format first
npx prettier --write path/to/file.ts

# Then lint
npx eslint path/to/file.ts
```

**For Shell scripts**:

```bash
# Format first
shfmt -w path/to/script.sh

# Then lint
shellcheck path/to/script.sh
```

**For Markdown**:

```bash
# Lint and auto-fix
npx markdownlint-cli2 --fix path/to/file.md
```

### Resolving Linting Issues

**For Orchestrators**: Delegate immediately to linting-root-cause-resolver WITHOUT running linters yourself. See the [holistic-linting-orchestrator skill](../holistic-linting-orchestrator/SKILL.md) for complete delegation workflows.

```claude
Agent(subagent_type="holistic-linting:linting-root-cause-resolver", prompt="Format, lint, and resolve any issues in file1.py")
Agent(subagent_type="holistic-linting:linting-root-cause-resolver", prompt="Format, lint, and resolve any issues in file2.py")
```

Do NOT run `ruff check` or `mypy` before delegating. The agent gathers its own linting data.

**For Sub-Agents**: Follow the linter-specific resolution workflow documented in the [holistic-linting-resolver skill](../holistic-linting-resolver/SKILL.md) based on the linting tool reporting the issue.

## Bundled Resources

### Agent: linting-root-cause-resolver

Location: [`../../agents/linting-root-cause-resolver.md`](../../agents/linting-root-cause-resolver.md)

This agent systematically investigates and resolves linting errors by understanding root causes rather than suppressing them with ignore comments.

**To install the agent**:

```bash
# Install to user scope (~/.claude/agents/)
uv run ./scripts/install_agents.py --scope user

# Install to project scope (<git-root>/.claude/agents/)
uv run ./scripts/install_agents.py --scope project

# Overwrite existing agent file
uv run ./scripts/install_agents.py --scope user --force
```

**Philosophy**:

- Linting errors are symptoms of deeper issues
- Never silence errors without understanding them
- Always verify assumptions through investigation
- Prioritize clarity and correctness over quick fixes

### Rules Knowledge Base

Comprehensive documentation of linting rules from three major tools:

#### Ruff Rules (933 rules documented)

Location: [`./references/rules/ruff/index.md`](./references/rules/ruff/index.md)

Covers all Ruff rule families including:

- **E/W** (pycodestyle errors and warnings)
- **F** (Pyflakes logical errors)
- **B** (flake8-bugbear common bugs)
- **S** (Bandit security checks)
- **I** (isort import sorting)
- **UP** (pyupgrade modern Python patterns)
- And 13 more families

Each rule documents:

- What it prevents (design principle)
- When it's a violation (examples)
- When it's NOT a violation (edge cases)
- Violating code examples
- Resolved code examples
- Configuration options

#### MyPy Error Codes

Location: [`./references/rules/mypy/index.md`](./references/rules/mypy/index.md)

Comprehensive type checking error documentation organized by category:

- Attribute access errors
- Name resolution errors
- Function call type checking
- Assignment compatibility
- Collection type checking
- Operator usage
- Import resolution
- Abstract class enforcement
- Async/await patterns

Each error code documents:

- Type safety principle it enforces
- When this is an error (type violations)
- When this is NOT an error (valid patterns)
- Error-producing code examples
- Corrected code examples
- Configuration options (mypy.ini, pyproject.toml)

#### Bandit Security Checks (65+ checks documented)

Location: [`./references/rules/bandit/index.md`](./references/rules/bandit/index.md)

Security vulnerability documentation organized by category:

- Credentials and secrets
- Cryptography weaknesses
- SSL/TLS vulnerabilities
- Injection attacks (command, SQL, XML)
- Deserialization risks
- File permissions
- Unsafe functions
- Framework configuration
- Dangerous imports

Each check documents:

- Security risk (what vulnerability it prevents)
- When this is vulnerable (insecure patterns)
- When this is NOT vulnerable (safe usage)
- Vulnerable code examples
- Secure code examples with mitigations
- Severity level (LOW, MEDIUM, HIGH)

### Scripts

Available in [`./scripts/`](./scripts/):

1. **install_agents.py** - Install the linting-root-cause-resolver agent to user or project scope
2. **detect_hook_tool.py** - Detect and run the correct git hook tool (prek vs pre-commit)

## Slash Commands

### `/lint` Command

The `/lint` command is a shorthand that activates this skill with optional file/directory path arguments.

**Usage**:

```bash
/lint                    # Activate holistic-linting for current task's modified files
/lint path/to/file.py    # Activate holistic-linting for specific file
/lint path/to/directory  # Activate holistic-linting for all files in directory
```

The command loads this skill and follows the workflows documented above. It is equivalent to activating `/holistic-linting:holistic-linting` directly.

## Integration with Claude Code Hooks

This skill complements the [claude-linting-hook](https://github.com/yourrepo/claude-linting-hook) which provides automatic PostToolUse linting via Claude Code hooks. The hook and skill serve different purposes:

**claude-linting-hook** (PostToolUse hook):

- Triggers automatically after Edit/Write
- Provides immediate feedback during development
- Blocks on substantive issues
- Runs in hook execution context

**holistic-linting skill** (Workflow guidance):

- Guides Claude's task completion workflow
- Ensures linting happens before claiming "done"
- Provides rules knowledge base for investigation
- Includes systematic resolution process via linting-root-cause-resolver agent

Use both together for comprehensive linting coverage:

1. Hook catches issues immediately during editing
2. Skill ensures systematic resolution before task completion
3. Knowledge base supports root-cause analysis

## Examples

### Example 1: Orchestrator completes Python feature implementation

```text
User: "Add authentication middleware to the API"

Orchestrator:
1. [Implements authentication middleware in auth.py]
2. [Implementation complete, now applying holistic-linting skill]
3. [Delegates to linting agent WITHOUT running linters]
4. Agent(subagent_type="holistic-linting:linting-root-cause-resolver", prompt="Format, lint, and resolve any issues in auth.py")
5. [Agent formats with ruff format, runs ruff check + mypy]
6. [Agent finds 3 ruff errors, 2 mypy type issues]
7. [Agent resolves all 5 issues at root cause]
8. [Agent verifies: ruff check + mypy - clean]
9. [Agent produces resolution report in .claude/reports/]
10. [Orchestrator reads report confirming clean resolution]
11. Task complete ✓
```

### Example 2: Sub-agent writes Python module

```text
Orchestrator delegates: "Create database connection pool module"

Sub-agent:
1. [Writes db_pool.py with connection logic]
2. [Before completing, applies holistic-linting skill]
3. Formatting: uv run ruff format db_pool.py
4. Linting: uv run ruff check db_pool.py && uv run mypy db_pool.py
5. [Finds 1 mypy error: Missing return type annotation]
6. [Investigates: function should return ConnectionPool]
7. [Fixes: Adds -> ConnectionPool annotation]
8. [Verifies: uv run mypy db_pool.py - clean]
9. Returns to orchestrator with completed, lint-free module ✓
```

## Pre-Existing Issues Protocol

When a linter run reveals issues in files the current agent did not modify, "pre-existing issues not related to my changes" is a trigger to act — not a reason to skip. Every detected problem gets recorded. No detected issue silently disappears.

**Two outcomes based on whether the issue blocks the pipeline:**

- **Blocking** (linter exits nonzero, CI would fail, or current task verification cannot pass) → apply a pre-fix check before touching any file: (1) load the domain skill for the affected file, (2) state in one sentence how the fix aligns with that plugin's mission, (3) classify complexity. Trivial (one file, obvious root cause): fix now. Multi-file or design-decision: route to planning for an in-session fix, or mark the current run BLOCKED if the fix cannot be scoped to this session.
- **Non-blocking** (advisory warning, file unrelated to current task) → discover the repo's tracking system and record it

**Discover the tracking system** (search in order): `.claude/backlog/` per-item files, `.claude/tasks/`, `TODO.md`, `TODO`, `docs/TODO.md`, `.gsd/`, `sam.md`. If none exists, create a per-item file in `.claude/backlog/`.

**Record each non-blocking issue** with: tool, rule code, file:line, exact linter message, discovery date.

**Report all pre-existing activity** in the resolution report — both issues fixed and issues recorded.

For the full triage pipeline (groom → reproduce → plan → execute), see [Pre-Existing Issues Protocol](./references/pre-existing-issues-protocol.md).

When uncertain whether an issue is blocking: treat it as blocking and fix it.

## Best Practices

1. **Orchestrators delegate immediately** - Do NOT run formatters or linters before delegating. Agent gathers its own context.
2. **Let detection find your linters** - The ConfigurationDetector scans project config files automatically. Don't assume which linters are available.
3. **Format before linting (Sub-Agents only)** - Formatters auto-fix trivial issues (end-of-file, whitespace)
4. **Run linters concurrently (Sub-Agents only)** - Use parallel execution for multiple files or multiple linters
5. **Use the rules knowledge base** - Reference official rule documentation when investigating
6. **Never suppress** - Agents must not add `# type: ignore`, `# noqa`, suppression comments, or modify linter config to reduce rule severity. If a code change cannot resolve the issue, escalate as UNRESOLVED with documentation of what was tried
7. **Never delete to fix** - Removing a function, test, or class to eliminate a linting error is prohibited. Document it as a cleanup recommendation instead
8. **Record pre-existing issues** - Every linting issue discovered — whether in files you touched or not — gets recorded. Apply the Pre-Existing Issues Protocol
9. **Orchestrators delegate, sub-agents execute** - Orchestrators launch agents and read reports. Sub-agents run formatters, linters, and resolve issues.
10. **Check UNRESOLVED items before architecture review** - Orchestrators read the resolution report and surface UNRESOLVED items to the user before delegating to the architecture reviewer
11. **Verify after fixes (Sub-Agents only)** - Re-run linters on primary file AND any incidentally touched files to confirm all are clean
12. **Trust agent verification (Orchestrators)** - Read resolution reports instead of re-running linters to verify

## Troubleshooting

**Problem**: "I don't know which linters this project uses"
**Solution**: Linters are detected automatically by scanning config files (pyproject.toml, package.json, .pre-commit-config.yaml, etc.). Check the Linter Detection section for supported tools.

**Problem**: "Linting errors but I don't understand the rule"
**Solution**: Reference the rules knowledge base at `./references/rules/{ruff,mypy,bandit}/index.md`

**Problem**: "Multiple files with linting errors"
**Solution**: If orchestrator, launch concurrent linting-root-cause-resolver agents (one per file). If sub-agent, resolve each file sequentially.

**Problem**: "Linter not found (command not available)"
**Solution**: Check that linters are installed. Use `uv run <tool>` for Python tools to ensure virtual environment activation.

**`error[unresolved-import]: Cannot resolve imported module 'X'`** — Add the directory containing module `X` to `[tool.ty.environment] extra-paths` in `pyproject.toml`; run `uv run ty check <path>` to verify; if errors persist, confirm `pyproject.toml` is the config ty is reading (a `ty.toml` in the project root takes precedence and `pyproject.toml` will be ignored).

**Problem**: "False positive linting error"
**Solution**: Investigate using the rule's documentation. If the rule fires on code that is genuinely correct, document what you tried and why each approach failed, then return UNRESOLVED. The user decides whether to reconfigure the rule — agents do not modify linter configuration autonomously.

**Problem**: "No code change resolves the linting error"
**Solution**: This is expected for some issues (e.g., platform-conditional imports where ruff can't evaluate `sys.platform`). Mark the issue as UNRESOLVED in the resolution report with: (1) approaches attempted, (2) why each failed, (3) the fundamental constraint. The orchestrator will present this to the user for a human decision on suppression vs. rule reconfiguration.

## Skill Activation

This skill is automatically loaded when installed in `~/.claude/skills/holistic-linting`.

To manually reference this skill in a session:

```text
Activate the holistic-linting skill: Skill(skill: "holistic-linting:holistic-linting")
```

## Related Skills

- [holistic-linting-orchestrator](../holistic-linting-orchestrator/SKILL.md) - Orchestrator delegation workflows for linting tasks
- [holistic-linting-resolver](../holistic-linting-resolver/SKILL.md) - Linter-specific resolution workflows for sub-agents
- **python3-development** - Modern Python development patterns and best practices
- **uv** - Python package and project management with uv
