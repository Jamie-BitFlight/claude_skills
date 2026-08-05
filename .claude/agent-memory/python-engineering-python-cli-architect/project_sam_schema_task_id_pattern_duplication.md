---
name: project_sam_schema_task_id_pattern_duplication
description: sam_schema had 3 hard-coded copies of a narrower task-ID regex than the canonical TASK_ID_PATTERN; a delegating task assumed only one copy existed
metadata:
  type: project
---

`plugins/development-harness/sam_schema/core/models.py` defines the canonical
`TASK_ID_PATTERN` (permits letter-suffixed `T10a` and slash-compound `T10a/T10b`,
`P1/T3` IDs). Before the fix landed (commit `edbbbd7f` on `feat/phase5-parity-continue`),
a narrower literal `r"^[A-Za-z]?\d+(\.\d+)?$"` was hard-coded in 3 separate places instead
of referencing `TASK_ID_PATTERN.pattern`:

1. `Task.id` field pattern in `models.py` (the "authoritative" model itself — NOT just
   `TaskDefinition`'s override).
2. `TaskDefinition.id` field pattern in `action_models.py` (duplicated the same narrow
   literal, not actually narrower than the parent).
3. `SchemaGap.expected` message literal in `readers/normalize.py`.

**Why this matters**: A Codex review finding assumed `Task` already used the wide
`TASK_ID_PATTERN` and that fixing `TaskDefinition`'s override alone would suffice. It would
not have — `Task.id`'s own field pattern was equally narrow, so `TaskDefinition` inheriting
from `Task` (even with the override removed) would still reject `T10a`. Verified by
constructing `Task(id="T10a", ...)` directly before touching any code — this reproduction
step caught the wrong assumption.

**Fix pattern**: single source of truth — `Field(..., pattern=TASK_ID_PATTERN.pattern)` in
both `Task.id` and `TaskDefinition.id`, plus an f-string reference in the `normalize.py` gap
message, instead of re-typing the regex literal.

**Still narrower, deliberately out of scope**: `plugins/development-harness/skills/
implementation-manager/scripts/task_format.py` defines its own separate `TASK_ID_PATTERN`
(no letter-suffix/compound support) sourced from a different doc (`TASK_FILE_FORMAT.md` line
272 JSON schema) — a different subsystem, not verified to exhibit the same practical bug in
its own call sites. Left untouched per evidence-action-proportionality; flag if a similar
report surfaces there.

**Test-suite gotcha found while fixing**: `sam_schema/readers/normalize.py`'s
`normalize_task` always calls `_detect_gaps` (records "missing" gaps for absent optional
fields) even for successfully-validated tasks — so `assert not any(g.task_id == X for g in
gaps)` is the wrong regression check after widening an ID pattern. Filter to
`gap_type == "invalid_value"` when asserting "this ID is no longer rejected."
