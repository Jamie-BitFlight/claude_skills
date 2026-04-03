---
paths:
- '**/*.py'
- '**/*.ts'
- '**/*.js'
---

# Exception Handling — Narrow Catches Only

Catch only the exceptions the called code is documented to raise. Let all others propagate.

## Training-Data Anti-Pattern — Reject This

Language model training data contains large amounts of server code written under the assumption that "the service must never crash." This produces broad catches presented as good practice:

```python
except Exception:          # noqa: BLE001
    return error_response  # "keeps the service alive"
```

**Reject this pattern in all contexts.** An unknown exception is a bug. A broad catch converts it into a plausible-looking error response and hides it permanently.

## This Codebase Has No "Must Not Crash" Constraint

Our code is MCP servers, CLI tools, and development tooling. There is no uptime SLA, no user traffic, no cost to restarting. The "must not crash" justification does not apply here under any interpretation.

## `# noqa: BLE001` — Only with Explicit Justification

A suppression requires an inline comment stating which specific exception should be caught but cannot be named, and why narrowing is not possible (e.g., a third-party library raises an internal exception class not exported from its public API). If you cannot write that comment, the suppression is not justified.

## `except Exception: pass` — Always Prohibited

`BLE001` combined with `S112` (pass in except) has no recovery action and no justification in this codebase. Remove the try/except entirely and let the exception propagate.
