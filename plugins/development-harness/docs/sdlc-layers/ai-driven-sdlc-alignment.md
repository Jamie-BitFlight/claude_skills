# AI-Driven SDLC Alignment

How the `dh` pipeline maps onto Figure 5, "Traditional SDLC vs. AI-Driven SDLC", in Google's
Kaggle whitepaper, which of the paper's practices `dh` already has, which it lacks, and what was
decided about each gap.

## Source

- **Paper**: *The New SDLC With Vibe Coding — From ad-hoc prompting to Agentic Engineering*,
  Addy Osmani, Shubham Saboo, Sokratis Kartakis, May 2026. Day 1 paper of the Google x Kaggle
  5-Day AI Agents Intensive "Vibe Coding" course.
  SOURCE: [Kaggle whitepaper](https://www.kaggle.com/whitepaper-the-new-SDLC-with-vibe-coding) (accessed 2026-10-17)
- **Where the quotes come from**: the Kaggle page renders its body client-side, so the text could
  not be extracted from it. Every quote and page number below comes from a third-party PDF mirror,
  [Day_1_v3.pdf](https://rocketedge.com/wp-content/uploads/2026/06/Day_1_v3.pdf) (accessed
  2026-10-17; sha256 `e3575d639e3ddaf2e3edb9907230a6029d9dd4e55eb9e02eec254e9e32bd3b2f`).
- **Figure**: page 20, in the section "The new software development life cycle" (pp. 19–25). The
  figure's arc labels ("Specs become eval criteria", "Agent self-corrects", "Continuous
  automation") appear only in the image; the body-text passages quoted below cover each concept.

The paper's framing (p.19): implementation compresses to hours "while requirements,
architecture, and verification remain stubbornly human-paced", and (p.39) "The bottleneck moved
from writing the code to specifying what it should do and verifying that the agents did it."

## Phase mapping

The S1–S7 numbering does not partition the `dh` workflow; the stage sequence and the mapping
between them are in [ARCHITECTURE.md](../../ARCHITECTURE.md) ("Stages" and the S1–S7 mapping
table). This table maps each figure phase to the stages that do that work.

| Figure phase (AI-Driven row) | `dh` stages | Where it is implemented |
|---|---|---|
| Requirements — "Specification quality is the new bottleneck" | Create, Groom, S1 Discovery, S2 Planning + RT-ICA | [backlog-item-groomer.md](../../agents/backlog-item-groomer.md), [discovery](../../skills/discovery/SKILL.md), [planning](../../skills/planning/SKILL.md), [rt-ica](../../skills/rt-ica/SKILL.md) |
| Design — "Architecture decisions amplified at scale" | S2 Planning, S3 Context Integration | [planning](../../skills/planning/SKILL.md), [context-integration](../../skills/context-integration/SKILL.md) |
| Implementation — "Minutes to hours" | S4 Task Decomposition, Orchestration, S5 Execution | [task-decomposition](../../skills/task-decomposition/SKILL.md), [swarm-task-planner.md](../../agents/swarm-task-planner.md), [dispatch](../../skills/dispatch/SKILL.md), [execution](../../skills/execution/SKILL.md) |
| Testing — "Output Eval" / "Trajectory Eval" | T0/TN bookends, S6 Forensic Review | [t0-baseline-capture.md](../../agents/t0-baseline-capture.md), [tn-verification-gate.md](../../agents/tn-verification-gate.md), [forensic-review](../../skills/forensic-review/SKILL.md) |
| Review — AI first-pass reviewer, human judgement | S6 Forensic Review, S7 Final Verification | [forensic-review](../../skills/forensic-review/SKILL.md), [final-verification](../../skills/final-verification/SKILL.md), [code-reviewer.md](../../agents/code-reviewer.md) |
| Deploy & Maintenance — "Continuous automation" | Closure: `gate-push` ends at the pull request | [gate-push](../../skills/gate-push/SKILL.md), [complete-implementation](../../skills/complete-implementation/SKILL.md) |
| Arc "Specs become eval criteria" | Groom and S2 criteria → S4 `acceptance-criteria-structured` | [swarm-task-planner.md](../../agents/swarm-task-planner.md) "Criterion Traceability" |
| Arc "Agent self-corrects" | Loop: worker self-verification, orchestrator retry | [work-loop.md](../work-ledger/work-loop.md), [execution](../../skills/execution/SKILL.md) |

## Similarities

Each row was checked against the files it cites.

| Paper practice | `dh` equivalent |
|---|---|
| Tests verify deterministic behaviour, checked by code (pp.14–15) | `AcceptanceCriterion` carries a required `check_command` with `expected_baseline`/`expected_final` ([models.py](../../sam_schema/core/models.py), class `AcceptanceCriterion`). T0 runs each command before implementation and TN re-runs it and compares; a regression is FAIL ([t0-baseline-capture.md](../../agents/t0-baseline-capture.md), [tn-verification-gate.md](../../agents/tn-verification-gate.md)). |
| "Feedback loops that route failures back to agents for correction" (p.24); harness routes test failures back to the model (p.30) | S6 NEEDS_WORK creates remediation tasks and re-reviews ([forensic-review](../../skills/forensic-review/SKILL.md)); S7 NOT_CERTIFIED returns to S4 ([final-verification](../../skills/final-verification/SKILL.md)). The orchestrator decides reclaim or acceptance and escalates on `attempts-exhausted` ([work-loop.md](../work-ledger/work-loop.md) J1, J2, J15; default `loop.max_attempts` in [ledger_spec.py](../../dh_core/ledger_spec.py)). A TN FAIL reclaims only the tasks whose changed files overlap the failing criterion (J17). Workers also self-verify inside an attempt ([execution](../../skills/execution/SKILL.md)). |
| AI first-pass review that does not replace human judgement (p.23) | Producer and evaluator are separate: S5 implements, S6 verifies with a separate reviewer agent ([verification-protocol.md](./layer-0/verification-protocol.md), [forensic-review](../../skills/forensic-review/SKILL.md)). |
| Specification quality is the bottleneck (p.19, p.46) | RT-ICA blocks planning while any prerequisite is MISSING, with documented exceptions ([rt-ica](../../skills/rt-ica/SKILL.md)). The groomer requires behavioural, command-verifiable criteria and forbids file-existence criteria ([backlog-item-groomer.md](../../agents/backlog-item-groomer.md)). S2 requires a Given/When/Then acceptance test per goal ([planning](../../skills/planning/SKILL.md) Step 3). |
| Deterministic hooks guard the harness (p.30) | Repository pre-commit hooks and the per-turn Stop-hook output check listed in the Identify phase of [arl-meta-layer.md](./arl-meta-layer.md). |
| Trajectory evaluation of tool-call sequences (p.22) | Exists outside the `dh` pipeline as post-hoc analysis: agentskill-kaizen `check_conformance` checks tool-call sequences against a reference transition model and returns per-trace fitness ([server.py](../../../agentskill-kaizen/mcp/server.py)); the plugin-creator `grader` agent grades skill-eval runs from the execution transcript ([grader.md](../../../plugin-creator/agents/grader.md)). |

## Gaps and adoption decisions

| Gap | Evidence | Decision |
|---|---|---|
| **Specs do not become eval criteria.** Groom and S2 write criteria, but S4 re-derived `acceptance-criteria-structured` from scratch with no link back, so an upstream scenario could silently have no executable check. Paper: "Write the tests and evals before generating the code. Together they are the contract with the AI." (p.43); evals are "the primary mechanism for communicating intent to AI agents" (p.23). | The only producer of `acceptance-criteria-structured` is [swarm-task-planner.md](../../agents/swarm-task-planner.md); no mechanism converted groom or S2 criteria into `AcceptanceCriterion` objects ([completeness.md](../workflow-multigraph/findings/completeness.md)). | **Adopted in this PR.** See "Adopted: criterion traceability" below. |
| **No trajectory gate.** Paper: "Output evaluation checks the final artifact ... Trajectory evaluation checks the full sequence of tool calls and intermediate reasoning. Both are necessary" (p.22); trajectory evals run in CI (p.45). | Trajectory checks exist (Similarities, last row) but no `dh` stage gates task acceptance on them; `dh` reads transcripts only for liveness ([agent-health-check.md](../../skills/implement-feature/references/agent-health-check.md)). | **Tracked for later**: [#4146](https://github.com/Jamie-BitFlight/claude_skills/issues/4146). |
| **No criterion shape for judgement.** Paper: evals are "checked by labelled datasets, scoring rubrics, and LM judges" (p.15); "an eval without a clear rubric measures nothing" (p.44). | [ARCHITECTURE.md](../../ARCHITECTURE.md) "Acceptance criteria" states that an assessment "needs a criterion shape that carries evidence and a judgement instead of an exit code"; `AcceptanceCriterion` has no evidence or judgement field. | **Tracked for later**: [#4147](https://github.com/Jamie-BitFlight/claude_skills/issues/4147). |
| **Spec-quality gate is implemented but not invoked.** | The decomposition-exit gate ([ARCHITECTURE.md](../../ARCHITECTURE.md) "The decomposition-exit gate"; [decomposition_gate.py](../../dh_core/workflow_multigraph/decomposition_gate.py)) has tests, but no skill or agent under `skills/` or `agents/` calls it. | **Tracked for later**: [#4148](https://github.com/Jamie-BitFlight/claude_skills/issues/4148). |
| **Deploy stops at the pull request.** Paper: agents "monitor deployment health, automatically roll back problematic releases" (p.23). | [gate-push](../../skills/gate-push/SKILL.md) ends when the PR exists; the S1–S7 taxonomy ends at S7. Release tooling exists outside `dh` (`bump-marketplace.yml`, the `daily-releases` skill) and is not wired into it. | Not adopted. `dh` delivers to a reviewed pull request; deployment belongs to the target project. |
| **No scheduled maintenance.** Paper: AI agents "systematically migrate codebases ... update deprecated APIs" (p.24); observability tracks "agent drift" (p.30). | Documentation drift audit and update run on every feature completion ([complete-implementation](../../skills/complete-implementation/SKILL.md)), so they are event-driven, not invoke-only. Scheduled workflows cover main-branch CI health and the verification-label audit only. The ARL Probe phase is "(To be designed.)" ([arl-meta-layer.md](./arl-meta-layer.md)). | Not adopted in this PR. The ARL Probe design is owned by [arl-human-probing-design.md](./arl-human-probing-design.md). |

## Adopted: criterion traceability

[swarm-task-planner.md](../../agents/swarm-task-planner.md) "Criterion Traceability" and Phase 4
check 13 now require that:

1. Each `acceptance-criteria-structured` entry derives from an S2 Given/When/Then acceptance test
   (`S2-AT{n}`), a groomed acceptance criterion (`GROOM-AC{n}`), or — for a direct invocation with
   no backlog item or S2 artifact — a criterion in the supplied spec (`SPEC-AC{n}`), and names its
   source.
2. A check that no upstream criterion supports is reported as a specification gap instead of being
   added.
3. Every upstream entry is mapped to the criterion IDs derived from it in a `## Criterion Coverage`
   section of the plan-level `acceptance_criteria` field, and an upstream entry with no derived
   criterion is reported as a coverage gap.

**No schema change.** `AcceptanceCriterion` has no field for the upstream link
([models.py](../../sam_schema/core/models.py)). Adding one would change the plan wire contract
that T0 and TN read, so the link is a prose convention in the existing free-text `description`
field (`Derives from: {ref}.`). A typed field is a candidate once the convention has been
exercised on real plans.

Coverage is prose in the existing plan-level `acceptance_criteria` field, not in `context`.
`context` is shared and set as a whole: `add-new-feature` Phase 6 runs
[dh-context-gathering.md](../../agents/dh-context-gathering.md) after the planner, and its write
replaces the field with the Context Manifest, so a coverage section stored there was erased before
execution. No other step writes `acceptance_criteria`; `plan import` copies it to the ledger, and
`plan status` returns it as `row.acceptance_criteria`. `sam_plan`'s `create` action does not accept
the field, so the planner sets it with an `update` call. That call had silently dropped every plan
field whose wire name differs from its Python name (`acceptance_criteria`, `feature_context`,
`codebase_patterns`, `backend_ref`) on the content store; `dh_core/operations.py` and
`PlanFieldsUpdate` in `sam_schema/core/task_backend_types.py` now accept either spelling.
