---
name: holistic-linting-resolver
description: Compatibility route for diagnosing and resolving quality-gate failures. Use when an existing caller explicitly invokes the resolver skill.
---

# Holistic Linting Resolver Compatibility Route

Load `holistic-linting:holistic-linting` and follow its diagnosis and verification stages using the supplied diagnostic evidence.

Do not use a lint-specific root-cause methodology. When the correction is not mechanically obvious from established intent, route causal investigation through `dh:root-cause-tracing-process` when available.

Route implementation judgment to the owning language/domain capability. For Python, load `python-engineering:standards-for-python-development`; use broader Python review skills only when consequence, uncertainty, or structural scope warrants them.

Do not autonomously weaken configured quality gates. Return unresolved policy/intent questions to the caller with the evidence and decision required.

This compatibility skill exists for current callers. New integrations should invoke `holistic-linting:holistic-linting` directly.
