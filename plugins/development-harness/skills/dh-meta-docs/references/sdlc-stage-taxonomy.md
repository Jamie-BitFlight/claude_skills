# SDLC Stage Naming Taxonomy

Canonical reference for stage naming conventions in the development-harness (dh) plugin. Agents must use these definitions when naming workflow skills and dispatch prompts.

---

## Section 1: Layer 1 — Cross-Cutting Stage Names

The 7 bare stage names used as workflow skill directory names under `plugins/development-harness/skills/`. These names are namespace-independent — they do not carry a plugin prefix.

| stage_id | name | purpose | workflow skill path |
|----------|------|---------|---------------------|
| S1 | `discovery` | Understand the feature request, identify constraints, and survey the codebase state before any planning occurs. | `plugins/development-harness/skills/discovery/SKILL.md` |
| S2 | `planning` | Produce a structured plan covering solution architecture, acceptance tests, risk assessment, and RT-ICA completeness gate. | `plugins/development-harness/skills/planning/SKILL.md` |
| S3 | `context-integration` | Validate the S2 plan against actual codebase state, resolving gaps and updating the plan artifact before task decomposition. | `plugins/development-harness/skills/context-integration/SKILL.md` |
| S4 | `task-decomposition` | Break the validated plan into executable, independently-delegatable task records with acceptance criteria and dependency ordering. | `plugins/development-harness/skills/task-decomposition/SKILL.md` |
| S5 | `execution` | Implement each task using language-appropriate specialist agents; produce execution artifacts per task. | `plugins/development-harness/skills/execution/SKILL.md` |
| S6 | `forensic-review` | Verify each executed task against its acceptance criteria; identify regressions, gaps, and quality violations. | `plugins/development-harness/skills/forensic-review/SKILL.md` |
| S7 | `final-verification` | Certify the complete feature against the original discovery and acceptance criteria; produce a CERTIFIED or NOT_CERTIFIED verdict. | `plugins/development-harness/skills/final-verification/SKILL.md` |

### Per-Stage Detail

#### S1 — `discovery`

```yaml
stage_id: S1
name: discovery
skill_activation: /dh:discovery
purpose: Understand the feature request, identify constraints, and survey the codebase state before any planning occurs.
inputs: Feature description, codebase root path, any prior context files
outputs: DISCOVERY artifact containing problem framing, constraint inventory, affected surfaces, and open questions
artifact_access: artifact_register(item_id=item_id, artifact_type="feature-context", artifact_id=artifact_id, agent=agent, content=content) / artifact_read(item_id=item_id, artifact_type="feature-context")
```

#### S2 — `planning`

```yaml
stage_id: S2
name: planning
skill_activation: /dh:planning
purpose: Produce a structured plan covering solution architecture, acceptance tests, risk assessment, and RT-ICA completeness gate.
inputs: DISCOVERY artifact, codebase context
outputs: PLAN artifact with architecture, acceptance tests in Given/When/Then format, risk assessment, task skeletons, and RT-ICA gate result
artifact_access: artifact_register(item_id=item_id, artifact_type="architect", artifact_id=artifact_id, agent=agent, content=content) / artifact_read(item_id=item_id, artifact_type="architect")
```

#### S3 — `context-integration`

```yaml
stage_id: S3
name: context-integration
skill_activation: /dh:context-integration
purpose: Validate the S2 plan against actual codebase state, resolving gaps and updating the plan artifact before task decomposition.
inputs: PLAN artifact, live codebase read access
outputs: Amended PLAN artifact with resolved gaps, confirmed assumptions, and updated constraints
artifact_access: artifact_read(item_id=item_id, artifact_type="architect") / artifact_register(item_id=item_id, artifact_type="architect", artifact_id=artifact_id, agent=agent, content=content)
```

#### S4 — `task-decomposition`

```yaml
stage_id: S4
name: task-decomposition
skill_activation: /dh:task-decomposition
purpose: Break the validated plan into executable, independently-delegatable task records with acceptance criteria and dependency ordering.
inputs: Amended PLAN artifact
outputs: One TASK record per work unit, with acceptance criteria, agent routing, and dependency graph
artifact_access: sam_plan(config={"action": "create", "slug": slug, "goal": goal, "tasks": tasks, "issue": issue_number}) / sam_task(plan=plan_ref, task=task_id, config={"action": "read"})
```

#### S5 — `execution`

```yaml
stage_id: S5
name: execution
skill_activation: /dh:execution
purpose: Implement each task using language-appropriate specialist agents; produce execution artifacts per task.
inputs: TASK record, quality gate commands from language manifest
outputs: EXECUTION artifact per task containing implementation evidence and quality gate results
artifact_access: sam_task(plan=plan_ref, task=task_id, config={"action": "read"}) / sam_task(plan=plan_ref, task=task_id, config={"action": "update", "append_section": "Execution Results", "section_content": content})
```

#### S6 — `forensic-review`

```yaml
stage_id: S6
name: forensic-review
skill_activation: /dh:forensic-review
purpose: Verify each executed task against its acceptance criteria; identify regressions, gaps, and quality violations.
inputs: TASK record, EXECUTION artifact, codebase diff
outputs: REVIEW artifact per task with pass/fail per acceptance criterion and remediation instructions
artifact_access: sam_task(plan=plan_ref, task=task_id, config={"action": "read"}) / sam_task(plan=plan_ref, task=task_id, config={"action": "update", "append_section": "Review Results", "section_content": content})
```

#### S7 — `final-verification`

```yaml
stage_id: S7
name: final-verification
skill_activation: /dh:final-verification
purpose: Certify the complete feature against the original discovery and acceptance criteria; produce a CERTIFIED or NOT_CERTIFIED verdict.
inputs: DISCOVERY artifact, all REVIEW artifacts, codebase state
outputs: VERIFICATION artifact with per-criterion verdict and overall CERTIFIED or NOT_CERTIFIED determination
artifact_access: sam_task(plan=plan_ref, task=task_id, config={"action": "read"}) / sam_task(plan=plan_ref, task=task_id, config={"action": "update", "append_section": "Final Verification", "section_content": content})
```

---

## Section 2: Naming Convention Rules

Numbered rules for determining the correct form for a stage-related name.

1. **Workflow skill directories** under `plugins/development-harness/skills/` use **bare Layer 1 stage names only**. Example: `plugins/development-harness/skills/final-verification/SKILL.md`, not `plugins/development-harness/skills/testing-final-verification/SKILL.md`.

2. **Cross-cutting stage skills** provided by the dh plugin use bare Layer 1 names. They are activated as `/dh:{stage-name}`.

Removed: the domain-prefixed Layer 2 naming scheme (`{domain}-{sdlc-stage}` keys like
`planning-context-integration`, `testing-forensic-review`) existed solely to name `stage_skills`
manifest keys for `generic-stage-agent`. That agent and its dispatch pipeline
(`manifest_resolver.py`, `dispatch_helper.py`) were built as a proof of concept in March 2026 and
never got a live caller — both deleted. See [./language-manifest-schema.md](./language-manifest-schema.md)
for what a language manifest actually declares today.

---

## Sources

- Language manifest schema: [./language-manifest-schema.md](./language-manifest-schema.md)
- IEEE 12207:2017 — Systems and software engineering — Software life cycle processes
- ISO 15288:2023 — Systems and software engineering — System life cycle processes
- SAFe 6.0 — Scaled Agile Framework practices (scaledagileframework.com)
