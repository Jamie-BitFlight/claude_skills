---
paths:
- '**/scripts/**'
- .claude/hooks/**
---

# Script Invocation

All scripts have shebangs and executable permissions (enforced by `check-executables-have-shebangs`, `check-shebang-scripts-are-executable` pre-commit hooks).

**Invocation Priority:**

1. Direct execution: `./plugins/plugin-creator/scripts/auto_sync_manifests.py --reconcile --dry-run`
2. Via uv run (PEP 723 scripts): `uv run plugins/python3-development/skills/uv/scripts/sync_uv_releases.py --force`

Use direct execution first. Scripts are self-contained executables, not library modules.

**Why**: `uv run` resolves PEP 723 inline dependencies. Shebangs may specify `uv run --script` (handles venv and deps). Bare `python3` skips dependency resolution and may use wrong interpreter.

**Wrong — bypasses shebang and PEP 723 dependency resolution:**

```bash
python3 plugins/plugin-creator/scripts/auto_sync_manifests.py --reconcile
node .claude/hooks/session-start-backlog.cjs
```

SOURCE: Experimental validation (2026-02-02). Evidence from `.claude/hooks/session-start-backlog.cjs`, `plugins/plugin-creator/scripts/create_plugin.py`.
