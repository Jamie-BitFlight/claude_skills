---
name: review-security-change
description: Review a change for security defects such as secret exposure, injection, authentication/authorization failures, unsafe deserialization, and dependency risk. Use for an independent security perspective on a defined change set.
---
# Review Security Change

Review only the supplied change scope. Establish trust boundaries and changed attack surfaces before scanning patterns. Check secret handling, injection paths, authentication/authorization, unsafe parsing/deserialization, sensitive data exposure, dependency changes, and privilege transitions when applicable. Distinguish demonstrated defects from hypotheses requiring validation. Return APPROVE when no blocking security defect is found, REJECT for demonstrated blocking defects, and SKIP only when the supplied scope has no security-relevant executable/configuration surface. Cite file/line evidence and a concrete exploit/failure path for blockers where practical.
