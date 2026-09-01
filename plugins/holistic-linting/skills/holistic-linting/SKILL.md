---
name: holistic-linting
description: Comprehensive linting and formatting verification workflows. Provides automatic format-lint-resolve pipelines for orchestrators and sub-agents. Use when running linters, fixing ruff/mypy/bandit errors, ensuring code quality before completion, or resolving linting issues systematically.
---

# Holistic Linting Skill

This skill embeds comprehensive linting and formatting verification into Claude Code's workflow, preventing the common pattern where code is claimed "production ready" without actually running quality checks.

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

### Linter Detection

Linter detection is handled automatically by scanning project configuration files. The linting hook's `ConfigurationDetector` identifies available tools at runtime by checking:

| Config File                    | Tools Detected                                       |
| ------------------------------- | ---------------------------------------------------- |
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

**Important - Scoped Operations**: Always use `--files` or staged file patterns rather than `--all-files`. Use `--all-files` ONLY when explicitly requested by the user for repository-wide cleanup.

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

**For Sub-Agents**: Follow the linter-specific resolution workflow documented in the [holistic-linting-resolver skill](../holistic-linting-resolver/SKILL.md) based on the linting tool reporting the issue.

## Bundled Resources

### Agent: linting-root-cause-resolver

Location: [`../../agents/linting-root-cause-resolver.md`](../../agents/linting-root-cause-resolver.md)

**To install the agent**:

```bash
# Install to user scope (~/.claude/agents/)
uv run ./scripts/install_agents.py --scope user

# Install to project scope (<git-root>/.claude/agents/)
uv run ./scripts/install_agents.py --scope project

# Overwrite existing agent file
uv run ./scripts/install_agents.py --scope user --force
```

### Rules Knowledge Base

Comprehensive documentation of linting rules from three major tools:

#### Ruff Rules

Location: [`./references/rules/ruff/index.md`](./references/rules/ruff/index.md)

Covers all Ruff rule families including:

- **E/W** (pycodestyle errors and warnings)
- **F** (Pyflakes logical errors)
- **B** (flake8-bugbear common bugs)
- **S** (Bandit security checks)
- **I** (isort import sorting)
- **UP** (pyupgrade modern Python patterns)
- And 13 more families

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

#### Bandit Security Checks

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

## Pre-Existing Issues Protocol

When a linter run reveals issues in files the current agent did not modify, "pre-existing issues not related to my changes" is a trigger to act — not a reason to skip. Every detected problem gets recorded. No detected issue silently disappears.

**Outcome depends on whether the issue blocks the pipeline:**

- **Blocking** (linter exits nonzero, CI would fail, or current task verification cannot pass) → apply a pre-fix check before touching any file: (1) load the domain skill for the affected file, (2) state in one sentence how the fix aligns with that plugin's mission, (3) classify complexity. Trivial (one file, obvious root cause): fix now. Multi-file or design-decision: route to planning for an in-session fix, or mark the current run BLOCKED if the fix cannot be scoped to this session.
- **Non-blocking** (advisory warning, file unrelated to current task) → discover the repo's tracking system and record it

**Record each non-blocking issue** with: tool, rule code, file:line, exact linter message, discovery date.

**Report all pre-existing activity** in the resolution report — both issues fixed and issues recorded.

See the [Pre-Existing Issues Protocol reference](./references/pre-existing-issues-protocol.md) for the tracking-system search order, the per-item record format, and the full triage pipeline (groom → reproduce → plan → execute).

When uncertain whether an issue is blocking: treat it as blocking and fix it.

## Best Practices

1. **Run linters concurrently (Sub-Agents only)** - Use parallel execution for multiple files or multiple linters
2. **Never suppress** - Agents must not add `# type: ignore`, `# noqa`, `# ruff: ignore[...]`, or any suppression comment, or modify linter config to reduce rule severity. If a fix cannot resolve the issue, escalate as UNRESOLVED with documentation of what was tried
3. **Never delete to fix** - Removing a function, test, or class to eliminate a linting error is prohibited. Document it as a cleanup recommendation instead
4. **Record pre-existing issues** - Every linting issue discovered — whether in files you touched or not — gets recorded. Apply the Pre-Existing Issues Protocol
5. **Orchestrators delegate, sub-agents execute** - Orchestrators launch agents and read reports. Sub-agents run formatters, linters, and resolve issues.
6. **Check UNRESOLVED items before architecture review** - Orchestrators read the resolution report and surface UNRESOLVED items to the user before delegating to the architecture reviewer
7. **Verify after fixes (Sub-Agents only)** - Re-run linters on primary file AND any incidentally touched files to confirm all are clean
8. **Trust agent verification (Orchestrators)** - Read resolution reports instead of re-running linters to verify

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

## Related Skills

- [holistic-linting-orchestrator](../holistic-linting-orchestrator/SKILL.md) - Orchestrator delegation workflows for linting tasks
- [holistic-linting-resolver](../holistic-linting-resolver/SKILL.md) - Linter-specific resolution workflows for sub-agents
- **python3-development** - Modern Python development patterns and best practices
- **uv** - Python package and project management with uv
