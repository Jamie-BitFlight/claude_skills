---
name: review-quality-change
description: Review a code change for correctness-maintainability defects not owned by a narrower security/performance/accessibility perspective. Use for an independent quality perspective on a defined change set.
---
# Review Quality Change

Review the supplied change scope for demonstrated maintainability/correctness risks: swallowed failures, dead or unreachable behavior, unclear ownership, duplicated logic that can diverge, missing tests for consequential new behavior, misleading names/contracts, and unnecessary coupling. Scale findings to consequence; do not use arbitrary function-length, identifier-length, or universal test-per-symbol thresholds. Return APPROVE unless a demonstrated blocking defect justifies REJECT. Keep minor findings separate and cite precise evidence.
