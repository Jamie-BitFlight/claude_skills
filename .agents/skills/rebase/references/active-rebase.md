# Active rebase entry

Enter this route only for an explicit continue or abort request, or when a newly started rebase
stops. Inspect the repository before any further mutation:

Replace `<skill-dir>` with the absolute **Base directory for this skill** supplied by the harness;
run this single inspector instead of reconstructing its Git checks:

```bash
uv run --script "<skill-dir>/scripts/rebase_active.py"
```

The inspector derives active state from Git-backed operation metadata
([runtime evidence](./runtime-evidence.json#active-inspection)).

Treat the inspector result as an immediate route:

- `BLOCKED_PREFLIGHT_FAILED`: end without mutation.
- `NO_ACTIVE_REBASE`: make this inspector terminal last; run no rebase or completion check.
- `active`: detached `HEAD` is expected. Bind the complete inspector evidence, then read
  [active rebase operation](./active-rebase-operation.md) and follow it to a terminal.

Completion criterion: the inspector reaches a terminal with no later action, or its `active` route
loads the operation procedure.
