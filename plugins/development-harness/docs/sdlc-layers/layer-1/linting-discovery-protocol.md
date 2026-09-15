# Linting Discovery Protocol

Run this discovery sequence before you run quality gates — verify each lint, format, and typecheck tool is actually installed and configured rather than assuming it.

---

## Discovery Sequence

1. **Git hook** — Check for pre-commit or similar hooks that run quality gates
2. **CI config** — Check for GitHub Actions, GitLab CI, etc. that define gate commands
3. **Project config** — Read pyproject.toml, package.json, etc. for tool config
4. **Fallback** — Use the default gate for the detected file types. If the tool is not installed, skip that gate and log a warning.

---

## Order of Precedence

| Source | Use when |
|--------|----------|
| Project-local override | `.claude/quality-gates.md` or equivalent exists |
| Git hook, CI config, or project config | The repository names the gate command |
| Inferred from file types | No hook, CI config, or project config names the gate |

---

## Gate Skipping

- **Non-typed language** — Skip the typecheck gate.
- **Tool not found** — Skip gate, log warning, continue pipeline
- **Config missing** — Use the file-type default. Log a warning if the tool fails at runtime.
