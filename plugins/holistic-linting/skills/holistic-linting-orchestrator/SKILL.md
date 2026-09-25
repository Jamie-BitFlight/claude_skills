---
name: holistic-linting-orchestrator
description: Compatibility routing for callers that previously used the holistic-linting orchestrator workflow. Use only when an existing caller explicitly invokes this skill.
---

# Holistic Linting Orchestrator Compatibility Route

Load `holistic-linting:holistic-linting` and follow its quality-gate lifecycle.

Do not create a separate per-file resolver workflow. The core skill owns scope, gate discovery, diagnostic clustering, causal/domain routing, and verification.

When isolated workers are available, parallelize only diagnostic clusters whose correction surfaces are established as independent. Give each worker the original gate evidence and resolved cluster boundary; do not pre-decide its root cause.

This compatibility skill exists for current callers. New integrations should invoke `holistic-linting:holistic-linting` directly.
