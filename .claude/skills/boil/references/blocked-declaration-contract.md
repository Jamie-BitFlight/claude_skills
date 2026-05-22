# BLOCKED Declaration Contract

When a task cannot be completed because the permanent solve is genuinely unreachable,
use the BLOCKED declaration. This is the only legitimate alternative to full completion.

Last verified: 2026-05-22.

---

## Contract: What BLOCKED Means

BLOCKED means the current session cannot complete the permanent solve because of a specific,
named external constraint. It does NOT mean:

- The problem is hard
- The problem would take time
- A workaround exists that avoids the root cause
- The agent is uncertain how to proceed

---

## Required Fields

All four fields are mandatory. Omitting any field makes the declaration incomplete.

```text
BLOCKED: [specific reason the permanent solve cannot be completed now]
- What was completed: [list — must be non-empty or state "nothing"]
- What remains: [list with specific file paths, commands, or steps]
- Unblocking condition: [observable, testable change that enables completion]
```

### Field definitions

**BLOCKED reason**: One sentence stating the external constraint. Must name the constraint
explicitly — not "cannot proceed" but "the dependency `X` is not installed" or "write
permission to `pyproject.toml` is denied in the CI environment."

**What was completed**: Everything done before hitting the constraint. If nothing was done,
state "nothing — constraint was encountered before any work could begin."

**What remains**: The specific remaining steps, with file paths and commands where possible.
Vague items like "fix the tests" are not acceptable — "run `uv run pytest tests/test_runner.py`
after adding `fastmcp[tasks]` to pyproject.toml" is acceptable.

**Unblocking condition**: An observable, testable change. Not "when this is resolved" but
"when `pyproject.toml` is writable and `fastmcp[tasks]` is listed as a dependency."

---

## Wrong vs. Right

```text
# WRONG — workaround instead of BLOCKED declaration
The build fails because the dependency is missing. As a workaround,
comment out the import for now.
```

```text
# WRONG — vague BLOCKED with no actionable path
BLOCKED: cannot complete the task.
- What was completed: some things
- What remains: finish the rest
- Unblocking condition: resolve the issue
```

```text
# RIGHT — specific constraint, actionable path
BLOCKED: `fastmcp[tasks]` is not declared in pyproject.toml and cannot be added
because pyproject.toml is read-only in the current CI environment.
- What was completed: identified failing import at src/runner.py:14; confirmed
  the import requires fastmcp[tasks] extra (not base fastmcp)
- What remains: (1) add `fastmcp[tasks]` to pyproject.toml [tool.uv] dependencies;
  (2) run `uv lock` to regenerate lock file; (3) re-run `uv run pytest tests/ -x`
- Unblocking condition: pyproject.toml is writable and `fastmcp[tasks]` is present
  in the dependency list
```

---

## When BLOCKED Is Not Appropriate

| Situation | Correct action |
|---|---|
| Problem is difficult but solvable | Solve it — difficulty is not a blocker |
| Workaround exists | Apply the real fix, not the workaround |
| Uncertain how to proceed | Load `/find-cause` or `/scientific-method:scientific-thinking` |
| Requires more research | Do the research, then continue |
| Task scope is larger than expected | Extend scope — do not truncate |

---

## Asset: Template

A copy-ready BLOCKED declaration template is in `../assets/blocked-declaration-template.md`.

---

SOURCE: `.claude/CLAUDE.md §Standard of Excellence` — "Boil the ocean" principle establishes
that BLOCKED is a bounded exception, not a general exit. Extracted and formalized 2026-05-22.
