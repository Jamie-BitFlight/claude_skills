---
name: SAM bookend bookend_type enum validation
description: Task.bookend_type is typed as bare str instead of an enum. A typo like 't0-basline' would silently pass validation and produce a task invisible to BookendValidator (neither T0 nor TN). The field should use a StrEnum or Literal type constrained to the documented values ('t0-baseline', 'tn-verification'). BookendValidator already checks bookend_type values, but the model itself does not enforce valid values at construction time.
metadata:
  topic: sam-bookend-bookendtype-enum-validation
  source: Code review — SAM bookend validation implementation (followup-1)
  added: '2026-03-15'
  priority: P2
  type: Refactor
  status: open
  plan: plan/tasks-696-sam-bookend-validation-followup-1.md
  issue: '#721'
---