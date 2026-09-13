# Utilization Proposals: Skylos

**Research entry**: ./research/code-auditing/skylos.md
**Generated**: 2026-09-13
**Integration surfaces found**: 3 (CLI | pip dependency | MCP)
**Proposals written**: 2
**Skipped**: 3 — resolver duplicates the execution gate; cognitive pre-action verification has no code-scan role; agent-definition generation is not an executable agent codebase

---

## Utilization 1: Development Harness execution → Skylos combined static scan

**Research entry**: ./research/code-auditing/skylos.md
**Caller**: `./plugins/development-harness/skills/execution/SKILL.md`
**Integration mechanism**: CLI subprocess
**Replaces or adds**: Adds a changed-work static-analysis gate for dead code, security, secrets, dependency, configuration, quality, and AI-code-defect checks; it does not replace format, lint, typecheck, or tests.
**Setup cost**: Low (package installation; no API key required for documented local static analysis)
**Integration surface**: `pip install skylos`; `skylos . -a --diff origin/main`

### Why this caller

`execution/SKILL.md` defines the post-task deterministic backpressure gate and currently requires format, lint, typecheck, and test checks from the project's language manifest or standard tooling. Those gates do not prescribe a combined dead-code, secret, deployment-configuration, or AI-code-defect scan. The Skylos entry documents `skylos . -a --diff origin/main` as a changed-work combined scan, so it fits this existing quality-gate location without substituting for the task's existing language-native checks. The caller must scope the command to repositories and changed paths for which its maintainers accept Skylos findings as blocking or report-only evidence.

### Integration sketch

```bash
# Run after the existing format, lint, typecheck, and test gates.
# Install once in the project's verification environment.
pip install skylos

# Scan changed work with Skylos's documented combined analysis surface.
skylos . -a --diff origin/main
```

## Utilization 2: Development Harness feature verifier → Skylos deterministic code verification

**Research entry**: ./research/code-auditing/skylos.md
**Caller**: `./plugins/development-harness/agents/feature-verifier.md`
**Integration mechanism**: CLI subprocess
**Replaces or adds**: Adds deterministic local/workspace API, dependency, and phantom-symbol proof for supported changed source files; it does not replace the agent's goal-backward observable-truth, artifact, key-link, edge-case, or live-delivery checks.
**Setup cost**: Low (package installation; no API key required for documented local verification)
**Integration surface**: `skylos verify . --file src/app.py --range 40:75 --project-context`

### Why this caller

`feature-verifier.md` verifies a completed feature by checking observable truths, substantive artifacts, wiring, edge cases, and a delivery surface. Its structural checks rely on file inspection and targeted commands; it has no documented deterministic proof step for whether an edited supported-language file references nonexistent local symbols or unsupported package APIs. Skylos documents that exact narrow verification surface and an explicit `incomplete` result when proof cannot be established. The verifier can attach that result as additional evidence only for Python, TypeScript/JavaScript, Go, and Java; for other documented languages, or an `incomplete` result, it must record the limitation rather than treating it as a pass.

### Integration sketch

```bash
# For each changed Python, TypeScript/JavaScript, Go, or Java source range
# whose API and dependency claims need deterministic local proof:
skylos verify . --file src/app.py --range 40:75 --project-context

# Interpret the documented result states as evidence:
# pass       -> attach completed coverage to feature-verification evidence
# fail       -> report a feature-verification gap
# incomplete -> record unsupported or missing proof; do not claim verification passed
```

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `./plugins/holistic-linting/agents/linting-root-cause-resolver.md` | This agent remediates findings from the configured formatter and linters. Adding the same broad scan here would duplicate the execution quality gate and blur ownership between detection and remediation. |
| `./plugins/verification-gate/skills/verification-gate/SKILL.md` | This skill checks hypothesis-to-action alignment before a write-capable action. It has no post-edit static-analysis or quality-gate role for a Skylos command to add. |
| `./plugins/plugin-creator/agents/agent-creator.md` | It generates Markdown agent definitions, whereas the documented `skylos defend` and `skylos agent test` surfaces assess an implemented agent codebase and observed runtime behavior. The research entry does not establish that they evaluate Claude agent-definition Markdown. |
