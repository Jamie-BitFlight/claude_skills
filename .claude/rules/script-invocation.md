---
paths:
- '**/scripts/**'
- .claude/hooks/**
---

# Script Invocation

Every script has a shebang and executable permission (enforced by pre-commit).

Run scripts directly, not as library modules and not via bare `python3`:

1. `./plugins/plugin-creator/scripts/auto_sync_manifests.py --reconcile --dry-run`
2. If direct execution fails, `uv run plugins/plugin-creator/scripts/check_agent_auto_discovery.py`

Never `python3 script.py` — it skips PEP 723 dependency resolution and may use the wrong
interpreter. Never `node .claude/hooks/session-start-backlog.cjs` in place of its own invocation
mechanism.

## Canonical PEP 723 Shebang

```text
#!/usr/bin/env -S uv run --quiet --script
```

Never `--active`, in any position. It pollutes the shared `.venv` with the script's own
dependencies instead of using an isolated ephemeral environment — empirically verified on uv
0.12.5 (AGENTS.md Gotcha #11). `--quiet`/`-q` is a global flag and order-independent.
