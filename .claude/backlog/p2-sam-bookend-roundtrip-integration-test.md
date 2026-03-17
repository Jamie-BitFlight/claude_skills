---
name: SAM bookend roundtrip integration test
description: No explicit round-trip integration test exists for bookend field serialization/deserialization. While individual reader and writer tests pass, there is no test that writes a plan with bookend fields via the writer, reads it back via the reader, and asserts field-level equality on all bookend-specific fields (is_bookend, bookend_type, acceptance_criteria_structured) in a single test case.
metadata:
  topic: sam-bookend-roundtrip-integration-test
  source: Code review — SAM bookend validation implementation (followup-2)
  added: '2026-03-15'
  priority: P2
  type: Chore
  status: open
  plan: plan/tasks-697-sam-bookend-validation-followup-2.md
  issue: '#722'
---