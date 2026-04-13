# SDLC Stage Naming Taxonomy

Canonical reference for stage naming conventions in the development-harness (dh) plugin. Agents and language plugin authors must use these definitions when naming workflow skills, manifest `stage_skills` keys, and dispatch prompts.

---

## Section 1: Layer 1 — Cross-Cutting Stage Names

The 7 bare stage names used as workflow skill directory names under `plugins/development-harness/skills/` and as input 2 (cross-cutting stage skill) of the generic-stage-agent. These names are namespace-independent — they do not carry a plugin prefix.

| stage_id | name | purpose | workflow skill path |
|----------|------|---------|---------------------|
| S1 | `discovery` | Understand the feature request, identify constraints, and survey the codebase state before any planning occurs. | `plugins/development-harness/skills/discovery/SKILL.md` |
| S2 | `planning` | Produce a structured plan covering solution architecture, acceptance tests, risk assessment, and RT-ICA completeness gate. | `plugins/development-harness/skills/planning/SKILL.md` |
| S3 | `context-integration` | Validate the S2 plan against actual codebase state, resolving gaps and updating the plan artifact before task decomposition. | `plugins/development-harness/skills/context-integration/SKILL.md` |
| S4 | `task-decomposition` | Break the validated plan into executable, independently-delegatable task files with acceptance criteria and dependency ordering. | `plugins/development-harness/skills/task-decomposition/SKILL.md` |
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
artifact_access: artifact_register(issue_number, "feature-context", path, agent, content=...) / artifact_read(issue_number, "feature-context")
```

#### S2 — `planning`

```yaml
stage_id: S2
name: planning
skill_activation: /dh:planning
purpose: Produce a structured plan covering solution architecture, acceptance tests, risk assessment, and RT-ICA completeness gate.
inputs: DISCOVERY artifact, codebase context
outputs: PLAN artifact with architecture, acceptance tests in Given/When/Then format, risk assessment, task skeletons, and RT-ICA gate result
artifact_access: artifact_register(issue_number, "architect", path, agent, content=...) / artifact_read(issue_number, "architect")
```

#### S3 — `context-integration`

```yaml
stage_id: S3
name: context-integration
skill_activation: /dh:context-integration
purpose: Validate the S2 plan against actual codebase state, resolving gaps and updating the plan artifact before task decomposition.
inputs: PLAN artifact, live codebase read access
outputs: Amended PLAN artifact with resolved gaps, confirmed assumptions, and updated constraints
artifact_access: artifact_read(issue_number, "architect") / artifact_register(issue_number, "architect", path, agent, content=...)
```

#### S4 — `task-decomposition`

```yaml
stage_id: S4
name: task-decomposition
skill_activation: /dh:task-decomposition
purpose: Break the validated plan into executable, independently-delegatable task files with acceptance criteria and dependency ordering.
inputs: Amended PLAN artifact
outputs: One TASK file per work unit, with acceptance criteria, agent routing, and dependency graph
artifact_access: sam_plan(action=create, slug, goal, tasks=[...], issue=issue_number) / sam_task(plan, task, config={action:read})
```

#### S5 — `execution`

```yaml
stage_id: S5
name: execution
skill_activation: /dh:execution
purpose: Implement each task using language-appropriate specialist agents; produce execution artifacts per task.
inputs: TASK file, quality gate commands from language manifest
outputs: EXECUTION artifact per task containing implementation evidence and quality gate results
artifact_access: sam_task(plan, task, config={action:read}) / sam_task(plan, task, config={action:update, append_section="Execution Results", section_content=...})
```

#### S6 — `forensic-review`

```yaml
stage_id: S6
name: forensic-review
skill_activation: /dh:forensic-review
purpose: Verify each executed task against its acceptance criteria; identify regressions, gaps, and quality violations.
inputs: TASK file, EXECUTION artifact, codebase diff
outputs: REVIEW artifact per task with pass/fail per acceptance criterion and remediation instructions
artifact_access: sam_task(plan, task, config={action:read}) / sam_task(plan, task, config={action:update, append_section="Review Results", section_content=...})
```

#### S7 — `final-verification`

```yaml
stage_id: S7
name: final-verification
skill_activation: /dh:final-verification
purpose: Certify the complete feature against the original discovery and acceptance criteria; produce a CERTIFIED or NOT_CERTIFIED verdict.
inputs: DISCOVERY artifact, all REVIEW artifacts, codebase state
outputs: VERIFICATION artifact with per-criterion verdict and overall CERTIFIED or NOT_CERTIFIED determination
artifact_access: sam_task(plan, task, config={action:read}) / sam_task(plan, task, config={action:update, append_section="Final Verification", section_content=...})
```

---

## Section 2: Layer 2 — Domain-Prefixed Skill Names

Domain-prefixed names are used as `stage_skills` keys in language plugin manifests. They are the strings passed as input 3 (domain skills) to the generic-stage-agent.

### Pattern

```text
{domain}-{sdlc-stage}
```

Where `{domain}` is drawn from the closed list below and `{sdlc-stage}` is one of the 7 bare Layer 1 names.

### Closed Domain Prefix List

This list is exhaustive. Adding a new domain requires updating this document and the manifest schema validation.

| Domain | Covers stages | Rationale |
|--------|--------------|-----------|
| `planning` | S2 planning, S3 context-integration, S4 task-decomposition | Pre-implementation planning activities involving design, scope, and decomposition |
| `design` | S1 discovery, S2 planning | Architectural and structural design decisions that shape the solution |
| `implementation` | S5 execution | Skills for writing and modifying source code |
| `testing` | S6 forensic-review, S7 final-verification | Verification and validation activities — both per-task review and feature-level certification |
| `review` | S6 forensic-review | Code review, quality inspection, and audit |

### Composition Rules

1. **Bare stage name** (e.g., `discovery`): Use when a skill applies to exactly one stage and that stage name alone is unambiguous in the manifest.
2. **Bare domain name** (e.g., `implementation`): Use when a domain covers exactly one stage in the manifest and no disambiguation is needed.
3. **Domain-prefixed** (e.g., `planning-context-integration`): Required when a domain covers multiple stages in the same manifest to identify which stage the skill list applies to.
4. **Adding a new domain**: Requires adding the domain to the closed list in this document and updating manifest schema validation.

### Examples

| Manifest key | Domain | SDLC stage | Valid? | Notes |
|-------------|--------|------------|--------|-------|
| `discovery` | (bare stage) | `discovery` | Yes | Unambiguous single-stage |
| `design` | (bare domain) | S2 planning (implied) | Yes | Domain covers one stage in manifest |
| `planning-context-integration` | `planning` | `context-integration` | Yes | Disambiguates among planning-domain stages |
| `planning-task-decomposition` | `planning` | `task-decomposition` | Yes | Disambiguates among planning-domain stages |
| `implementation` | (bare domain) | `execution` | Yes | Domain covers one stage |
| `testing-forensic-review` | `testing` | `forensic-review` | Yes | Disambiguates among testing-domain stages |
| `testing-final-verification` | `testing` | `final-verification` | Yes | Correct full form |
| `testing-verification` | `testing` | `final-verification` | **No** | Incorrect — the stage name is `final-verification`, not `verification`. Use `testing-final-verification`. |

---

## Section 3: Standard Terminology Mappings

Maps the 7 bare stage names to closest equivalents in IEEE 12207, ISO 15288, and SAFe. These mappings are approximate. The SAM pipeline stages are composite activities that may span multiple processes in formal standards. The mapping establishes terminology correspondence, not process equivalence.

| Stage | IEEE 12207 Process | ISO 15288 Process | SAFe Practice |
|-------|-------------------|-------------------|---------------|
| `discovery` | Stakeholder Needs Definition (6.4.1) | Stakeholder Needs and Requirements Definition (6.4.1) | Explore / Define |
| `planning` | System Requirements Analysis (6.4.2) | System Requirements Definition (6.4.2) | Plan / PI Planning |
| `context-integration` | Architecture Definition (6.4.3) | Architecture Definition (6.4.3) | Architect / Enable |
| `task-decomposition` | Implementation Planning (7.2.1) | Project Planning (6.3.1) | Plan / Iteration Planning |
| `execution` | Software Construction (7.1.5) | Implementation (6.4.7) | Implement / Build |
| `forensic-review` | Software Verification (7.2.4) | Verification (6.4.6) | Inspect / Review |
| `final-verification` | Software Validation (7.2.5) | Validation (6.4.8) | Demonstrate / Inspect & Adapt |

**Match quality notes:**

- `discovery` → IEEE/ISO 6.4.1 is an approximate match. IEEE 12207 defines this as a formal elicitation process; SAM discovery is lighter-weight but equivalent in purpose.
- `context-integration` → IEEE/ISO Architecture Definition is the closest parallel. SAM context-integration does not produce a full architecture specification; it validates an existing plan against codebase reality.
- `task-decomposition` → IEEE 7.2.1 / ISO 6.3.1 cover planning at project scope. SAM task-decomposition is narrower (feature-level), so this is an approximate match.
- `forensic-review` → IEEE 7.2.4 / ISO 6.4.6 cover formal verification against requirements. SAM forensic-review is per-task and evidence-driven, making this a close but not exact match.

---

## Section 4: Naming Convention Rules

Numbered rules for determining the correct form for any stage-related name.

1. **Workflow skill directories** under `plugins/development-harness/skills/` use **bare Layer 1 stage names only**. Example: `plugins/development-harness/skills/final-verification/SKILL.md`, not `plugins/development-harness/skills/testing-final-verification/SKILL.md`.

2. **Language manifest `stage_skills` keys** use **domain-prefixed Layer 2 names** when disambiguating, **bare names** when unambiguous (see Section 2 composition rules).

3. **Cross-cutting stage skills** provided by the dh plugin use bare Layer 1 names. They are activated as `/dh:{stage-name}`.

4. **Language-specific stage skills** provided by language plugins use Layer 2 domain-prefixed names. They appear as values in the manifest `stage_skills` map.

5. **`testing-final-verification` is correct; `testing-verification` is wrong.** The Layer 1 stage name is `final-verification`. The bare form `verification` is not a recognized alias and must not appear as a manifest key.

6. **YAML keys in manifests use hyphens, not underscores.** `planning-context-integration` is correct; `planning_context_integration` is not.

7. **Domain prefix must come from the closed list in Section 2.** Keys using unlisted domain prefixes are invalid. Adding a new domain requires updating Section 2 and the manifest schema validation.

8. **Extends-based overrides** must use the same key form as the base manifest key they override. If the base manifest declares `testing-final-verification`, the extending manifest must use the same key.

### Worked Example — Complete `stage_skills` Block

This example shows a valid `stage_skills` block for a hypothetical Python manifest. All keys use the forms defined in Sections 1 and 2.

```yaml
stage_skills:
  # Bare stage name — unambiguous single-stage skill
  discovery:
    - python3-discovery

  # Bare domain name — design domain covers one stage (S2 planning) in this manifest
  design:
    - python3-design

  # Domain-prefixed — planning domain covers multiple stages; must disambiguate
  planning-context-integration:
    - python3-implementation

  planning-task-decomposition:
    - python3-planning-task-decomposition

  # Bare domain name — implementation domain covers one stage (S5 execution)
  implementation:
    - python3-implementation

  # Domain-prefixed — testing domain covers multiple stages; must disambiguate
  testing-forensic-review:
    - python3-testing-forensic-review

  # Correct form — NOT testing-verification
  testing-final-verification:
    - python3-testing
```

---

## Sources

- Architecture spec: [plan/architect-development-harness-phase1.md](../../../../../plan/architect-development-harness-phase1.md) (Deliverable 1 section, Sections 1–4 content and exact mappings)
- Language manifest schema: [./language-manifest-schema.md](./language-manifest-schema.md)
- Generic stage agent: [../../agents/generic-stage-agent.md](../../agents/generic-stage-agent.md) (inputs 2 and 3 reference this taxonomy)
- IEEE 12207:2017 — Systems and software engineering — Software life cycle processes
- ISO 15288:2023 — Systems and software engineering — System life cycle processes
- SAFe 6.0 — Scaled Agile Framework practices (scaledagileframework.com)
