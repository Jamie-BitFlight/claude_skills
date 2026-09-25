---
name: holistic-linting-resolver
description: Compatibility route for existing callers that supply files/scope or quality-gate evidence and need diagnosis and resolution.
---

# Holistic Linting Resolver Compatibility Route

Load `holistic-linting:holistic-linting`.

Accept either:

- **file/scope input** - enter the core at discovery/execution and gather fresh gate evidence;
- **supplied diagnostic evidence** - validate scope, revision/config/tool provenance and freshness, then enter classification/diagnosis. If provenance is insufficient, regather evidence or return a blocker.

Use shared causal/domain capabilities only when actually available. Their absence is not permission to guess; return an explicit missing-capability blocker only when local evidence cannot establish a safe correction.

Before choosing a fix, establish rule meaning from the configured tool/version where practical. Ruff prefers installed `ruff rule <CODE>`; MyPy prefers matching-version documentation and may fall back offline to the core skill's bundled MyPy index/vendored docs with version uncertainty; Bandit may use its bundled index offline. For typing failures, trace expected/actual types and relevant stubs/configuration.

Do not autonomously weaken configured quality gates. Follow the core integrity and unresolved/out-of-scope handoff contracts.

Return the core workflow report with explicit `Workflow status: DONE` or `Workflow status: BLOCKED`, including an explicit no-diagnostics/no-findings result when applicable.

This compatibility skill exists for current callers. New integrations should invoke `holistic-linting:holistic-linting` directly.
