---
name: project_dh_backlog_add_gate_token
description: Gate token pattern for backlog_add — all consumers, test files, and skill files that embed the static value
metadata:
  type: project
---

The `backlog_add` MCP tool in `backlog_core/server.py` has a gate token mechanism:
- Constant defined at line 1141: `_BACKLOG_ADD_GATE_PHRASE = "problems-not-solutions"`
- Field description at line 1171 embeds the static value
- Validation at line 1184: `if gate_token != _BACKLOG_ADD_GATE_PHRASE`

**All consumers of the static token value (as of 2026-05-15):**

Tests that hardcode `"problems-not-solutions"`:
- `tests/test_backlog_core_server.py` — 8 call sites (lines 100, 129, 148, 170, 1690, 1724, 1802, 1834)
- `tests/test_scenarios.py` — 9 call sites (lines 53, 579, 623, 646, 661, 680, 707, 765, 810)

Test that imports the symbol directly:
- `tests/test_live_validation.py` line 22: `from backlog_core.server import _BACKLOG_ADD_GATE_PHRASE`
  Uses at lines 170, 292. **Import failure at collection time if symbol removed.**

AI skill instructions hardcoding the value:
- `skills/work-backlog-item/references/workflows/create/start.md` lines 119, 129
- `skills/work-backlog-item/references/workflows/quick/start.md` line 7

Reference docs:
- `docs/dh-backend-beads/comparison-research/03-dh-github-backlog.md` lines 128, 138, 1014, 1057

**Why:** Issue #2284 is replacing the static constant with a dynamic session-scoped token. All above files must be updated when that change ships.

**How to apply:** When assessing impact of any backlog_add or gate token change, check all 7 of these files. The critical risk is `test_live_validation.py` (symbol import) and the two workflow skill files (AI instruction poisoning).
