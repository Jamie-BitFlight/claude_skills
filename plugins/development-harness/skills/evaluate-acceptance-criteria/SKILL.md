---
name: evaluate-acceptance-criteria
description: Execute structured acceptance checks and record their observed results for later comparison. Use to capture a pre-change baseline or a post-change verification state without treating expected nonzero baseline results as execution failure.
---
# Evaluate Acceptance Criteria

Resolve the structured acceptance criteria and their executable checks. Run each check in the specified environment without changing the system merely to make it pass. Record command/check identity, exit/result, relevant output, and observation time. A nonzero or failing result is an observation, not a harness failure, unless the check itself could not execute. When a baseline is supplied, compare criterion-by-criterion and distinguish improvement, unchanged state, regression, and unexecutable evidence. Return machine-comparable per-criterion observations plus an overall verdict only when the caller's acceptance policy defines one.
