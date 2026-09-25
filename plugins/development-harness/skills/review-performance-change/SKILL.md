---
name: review-performance-change
description: Review a change for material performance regressions or unbounded resource behavior. Use for an independent performance perspective on a defined change set.
---
# Review Performance Change

Review only the supplied change scope. Identify changed hot paths, I/O boundaries, queries, allocation/collection growth, concurrency, caching, and algorithmic work. Look for N+1 operations, blocking work on async paths, repeated expensive work, unbounded growth, and changed complexity where consequence is material. Do not reject on stylistic micro-optimization. Return APPROVE, REJECT, or SKIP when the change has no plausible performance-relevant execution path. Support blockers with a concrete path and evidence; request measurement when static inspection cannot establish impact.
