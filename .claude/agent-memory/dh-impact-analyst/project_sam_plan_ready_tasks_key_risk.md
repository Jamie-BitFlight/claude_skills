---
name: project_sam_plan_ready_tasks_key_risk
description: sam_plan ready response uses ready_tasks key (not items); consumers in 3 orchestration skills depend on this key name; extraction of _paginate_results must not rename this key
metadata:
  type: project
---

`_sam_plan_ready` returns `{"ready_tasks": [...], "count": ..., "feature": ..., "issue": ...}`. The `_paginate_results` function returns `{"items": [...], "pagination": {...}, ...}`.

These two shapes are incompatible — naive reuse of `_paginate_results` for `ready` silently breaks all consumers.

Consumers confirmed reading `ready_tasks` directly: `implement-feature/SKILL.md`, `complete-implementation/SKILL.md`, `implementation-manager/SKILL.md`.

**Why:** The key rename is a breaking API change with no type-system enforcement — it produces a runtime `KeyError` or returns `None` in agent workflows.

**How to apply:** Any item touching `_sam_plan_ready` or adding pagination to `sam_plan ready` must explicitly confirm that the response key is preserved as `ready_tasks` (not renamed to `items`). This is the highest-risk constraint in SAM pagination changes.

Related: `test_paginate_results_boundary.py` imports `_TOKEN_BUDGET, _enc, _paginate_results` from `sam_schema.server` (line 40) — extraction to `dh_pagination.py` breaks this import at collection time, failing CI before any tests run.
