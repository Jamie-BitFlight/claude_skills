# Utilization Proposals: Skylos

**Research entry**: ./research/code-auditing/skylos.md
**Generated**: 2026-09-13
**Integration surfaces found**: 2 (CLI | MCP)
**Proposals written**: 4
**Skipped**: 3 — resolver duplicates the execution gate; cognitive pre-action verification has no code-scan role; agent-definition generation is not an executable agent codebase

---

## Utilization 1: Development Harness execution → Skylos combined static scan

**Research entry**: ./research/code-auditing/skylos.md
**Caller**: `./plugins/development-harness/skills/execution/SKILL.md`
**Integration mechanism**: CLI subprocess
**Replaces or adds**: Adds a changed-work static-analysis gate for dead code, security, secrets, dependency, configuration, quality, and AI-code-defect checks; it does not replace format, lint, typecheck, or tests.
**Setup cost**: Low (no API key required for documented local static analysis)
**Integration surface**: `uvx skylos . -a --diff origin/main`

### Why this caller

`execution/SKILL.md` defines the post-task deterministic backpressure gate and currently requires format, lint, typecheck, and test checks from the project's language manifest or standard tooling. Those gates do not prescribe a combined dead-code, secret, deployment-configuration, or AI-code-defect scan. The Skylos entry documents `skylos . -a --diff origin/main` as a changed-work combined scan, so it fits this existing quality-gate location without substituting for the task's existing language-native checks. The caller must scope the command to repositories and changed paths for which its maintainers accept Skylos findings as blocking or report-only evidence.

### Integration sketch

```bash
# Run after the existing format, lint, typecheck, and test gates.
# Scan changed work with Skylos's documented combined analysis surface.
uvx skylos . -a --diff origin/main
```

## Utilization 2: Development Harness feature verifier → Skylos deterministic code verification

**Research entry**: ./research/code-auditing/skylos.md
**Caller**: `./plugins/development-harness/agents/feature-verifier.md`
**Integration mechanism**: CLI subprocess
**Replaces or adds**: Adds deterministic local/workspace API, dependency, and phantom-symbol proof for supported changed source files; it does not replace the agent's goal-backward observable-truth, artifact, key-link, edge-case, or live-delivery checks.
**Setup cost**: Low (no API key required for documented local verification)
**Integration surface**: `uvx skylos verify . --file src/app.py --range 40:75 --project-context`

### Why this caller

`feature-verifier.md` verifies a completed feature by checking observable truths, substantive artifacts, wiring, edge cases, and a delivery surface. Its structural checks rely on file inspection and targeted commands; it has no documented deterministic proof step for whether an edited supported-language file references nonexistent local symbols or unsupported package APIs. Skylos documents that exact narrow verification surface and an explicit `incomplete` result when proof cannot be established. The verifier can attach that result as additional evidence only for Python, TypeScript/JavaScript, Go, and Java; for other documented languages, or an `incomplete` result, it must record the limitation rather than treating it as a pass.

### Integration sketch

```bash
# For each changed Python, TypeScript/JavaScript, Go, or Java source range
# whose API and dependency claims need deterministic local proof:
uvx skylos verify . --file src/app.py --range 40:75 --project-context

# Interpret the documented result states as evidence:
# pass       -> attach completed coverage to feature-verification evidence
# fail       -> report a feature-verification gap
# incomplete -> record unsupported or missing proof; do not claim verification passed
```

## Utilization 3: Development Harness security reviewer → Skylos combined static scan

**Research entry**: ./research/code-auditing/skylos.md
**Caller**: `./plugins/development-harness/agents/reviewer-security.md`
**Integration mechanism**: CLI subprocess
**Replaces or adds**: Adds deterministic detection in the secret, security-flaw, and dependency categories the entry documents for the `-a` scan; it does not replace the agent's authentication and authorization reading, its false-positive triage, or its prompt-injection check on agent and skill Markdown.
**Setup cost**: Low (no API key required for documented local static analysis)
**Integration surface**: `uvx skylos . -a --diff origin/main`

### Why this caller

`reviewer-security.md` states that its "task body contains a newline-separated list of changed files (relative paths from the repo root). Use this list as your scan target." Its in-scope list covers hardcoded secrets, injection vectors, insecure deserialization, dependency CVEs, and unsafe subprocess usage. The Skylos entry documents the combined `-a` scan as covering the secrets, security-flaw, and dependency *categories*, and documents `--diff origin/main` as its changed-work scoping flag; it does not enumerate which security sub-checks the scan performs, so overlap can be claimed at category level only. Confirming that injection, insecure deserialization, and unsafe subprocess usage are individually covered requires a source pass the entry has not made. This is a diff-level review gate, distinct from the per-task post-edit gate in Utilization 1, and it is a detection step rather than the remediation ownership that keeps `linting-root-cause-resolver.md` out of scope.

Three constraints bind the caller. The agent's scan target is the changed-files list in its task body, not a git ref, so Skylos's diff-scoped output must be intersected with that list rather than widening the agent's scope. `-a` also emits dead-code and quality findings that this agent's definition places out of scope; those belong to the quality perspective and must not enter the security verdict. Authentication and authorization gaps are likewise outside the categories the entry documents for general application code — `skylos defend`'s guardrail checks target an LLM-agent implementation — and the agent's prompt-injection check on Claude agent and skill Markdown is out of Skylos's documented reach for the same reason recorded against `agent-creator.md` below.

### Integration sketch

```bash
# Run alongside the agent's own reading, not in place of it.
# Keep only findings in this perspective's categories, and only for files
# present in the task body's changed-files list.
uvx skylos . -a --diff origin/main
```

## Utilization 4: Development Harness quality reviewer → Skylos dead-code scan

**Research entry**: ./research/code-auditing/skylos.md
**Caller**: `./plugins/development-harness/agents/reviewer-quality.md`
**Integration mechanism**: CLI subprocess
**Replaces or adds**: Adds unreferenced-symbol dead-code detection for changed files; it does not replace the agent's naming, exception-swallowing, test-coverage, or SOLID checks, none of which the research entry documents as Skylos checks.
**Setup cost**: Low (no API key required for documented local static analysis)
**Integration surface**: `uvx skylos . --diff origin/main`

### Why this caller

`reviewer-quality.md` receives "a list of changed files embedded in your task body (newline-separated relative paths, as returned by `git diff --name-only`)" and scans each for, among other classes, "**Dead code**: commented-out blocks, unreachable branches, debug print/log statements left in production paths". Those signals are lexical; the agent has no step that establishes a function, class, or import is unreferenced. Skylos documents dead-code analysis as the behaviour of its default scan and `--diff origin/main` as the changed-work scoping flag, so it supplies a form of proof the agent's documented method does not produce, at the agent's existing scan location.

Use the default scan rather than `-a`. The default is already scoped to this perspective's category; `-a` would add the security and secret findings that `reviewer-security.md` owns and that this agent's verdict must not carry. The agent's other four checks stay with the agent: the research entry names "quality regressions" as a scan category without enumerating its checks, which is not sufficient to claim coverage of naming, exception swallowing, test-coverage gaps, or SOLID violations.

### Integration sketch

```bash
# Default scan is the documented dead-code analysis; -a is deliberately omitted
# so security findings stay with the security perspective. The entry documents
# --diff only in the -a form, so verify the flag against `skylos --help` first.
uvx skylos . --diff origin/main
```

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `./plugins/holistic-linting/agents/linting-root-cause-resolver.md` | This agent remediates findings from the configured formatter and linters. Adding the same broad scan here would duplicate the execution quality gate and blur ownership between detection and remediation. |
| `./plugins/verification-gate/skills/verification-gate/SKILL.md` | This skill checks hypothesis-to-action alignment before a write-capable action. It has no post-edit static-analysis or quality-gate role for a Skylos command to add. |
| `./plugins/plugin-creator/agents/agent-creator.md` | It generates Markdown agent definitions, whereas the documented `skylos defend` and `skylos agent test` surfaces assess an implemented agent codebase and observed runtime behavior. The research entry does not establish that they evaluate Claude agent-definition Markdown. |
