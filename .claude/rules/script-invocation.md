---
paths:
- '**/scripts/**'
- .claude/hooks/**
---

# Script Invocation

All scripts have shebangs and executable permissions (enforced by `check-executables-have-shebangs`, `check-shebang-scripts-are-executable` pre-commit hooks).

**Invocation Priority:**

1. Direct execution: `./plugins/plugin-creator/scripts/auto_sync_manifests.py --reconcile --dry-run`
2. Via uv run (PEP 723 scripts): `uv run plugins/plugin-creator/scripts/check_agent_auto_discovery.py`

Use direct execution first. Scripts are self-contained executables, not library modules.

**Why**: `uv run` resolves PEP 723 inline dependencies. Shebangs may specify `uv run --script` (handles venv and deps). Bare `python3` skips dependency resolution and may use wrong interpreter.

## Canonical PEP 723 Shebang

```text
#!/usr/bin/env -S uv run --quiet --script
```

Never `#!/usr/bin/env -S uv run --active --script` (or any flag order carrying `--active`).
`--active` makes `uv run` prefer an ambient activated virtual environment over an isolated
ephemeral one — when a caller's shell has `VIRTUAL_ENV` set, the script's dependencies install
into that venv instead, drifting `.venv` from `uv.lock`. Empirically verified (uv 0.12.5): with
`--active`, a probe script's dependency installed into `.venv/lib/python3.13/site-packages/`; with
it omitted, the same probe resolved into an isolated `~/.cache/uv/environments-v2/` environment,
leaving `.venv` untouched. `--quiet`/`-q` is a global option and order-independent; `--active` is
the only semantic difference between the two forms in use across this repo.

SOURCE: empirical uv 0.12.5 probe; corroborates AGENTS.md Gotcha #11.

**Wrong — bypasses shebang and PEP 723 dependency resolution:**

```bash
python3 plugins/plugin-creator/scripts/auto_sync_manifests.py --reconcile
node .claude/hooks/session-start-backlog.cjs
```
