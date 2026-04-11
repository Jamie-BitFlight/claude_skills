---
name: rt-ica
description: Reverse Thinking - Information Completeness Assessment. Mandatory pre-planning checkpoint that blocks planning until prerequisites are verified. Use when receiving specs, PRDs, tickets, RFCs, architecture designs, or any multi-step engineering task. Integrates with CoVe-style planning pipelines. Invoke BEFORE creating plans, delegating to agents, or defining acceptance criteria.
user-invocable: true
context: fork
---

# RT-ICA: Reverse Thinking - Information Completeness Assessment

## Purpose

RT-ICA surfaces what the executor needs to know before it can act without stopping.

For every goal (top-level and each decomposed sub-goal), the model should:

1. Reverse-think prerequisites from the goal
2. Assess information completeness for each prerequisite
3. Either BLOCK planning until missing inputs are obtained, or APPROVE with explicit assumptions

<core_rule>

RT-ICA should be performed before planning, delegation, or solution design on:

1. The overall goal/request
2. Each decomposed goal or sub-goal that could fail due to missing information

If any required condition is MISSING, stop and request only the missing information.

</core_rule>

## Complexity Model

Task complexity is not implementation difficulty — it is the ratio of project-specific knowledge required to context window available.

Training data provides craft knowledge (language patterns, framework APIs, tooling). That is free. What consumes context budget is everything specific to this project: schemas, conventions, constraints, interfaces, user preferences, existing system behavior. That knowledge must be loaded before the agent can act.

**This changes how RT-ICA results inform task design:**

```mermaid
flowchart TD
    RTICA["RT-ICA conditions enumerated"] --> Measure["Estimate knowledge payload:<br>how much project-specific context<br>must be loaded to satisfy conditions?"]
    Measure --> Ratio{Knowledge payload<br>vs context window?}
    Ratio -->|"< 40% of window<br>Room to work"| Proceed["Single task — execute directly"]
    Ratio -->|"40-70% of window<br>Tight but workable"| Combine["Look for steps sharing<br>the same knowledge payload —<br>combine them into one task"]
    Combine --> Proceed
    Ratio -->|"> 70% of window<br>No room to implement"| Decompose["Decompose into subtasks<br>that each need a smaller<br>subset of the knowledge"]
```

**Step combining:** When two steps need the same project knowledge loaded, combining them is nearly free — the knowledge is loaded once, both steps execute in the remaining space. Splitting them wastes context by loading the same knowledge twice. Step boundaries belong where **information gaps** exist, not where implementation boundaries happen to fall.

**Dynamic vs static constraints:** RT-ICA produces dynamic constraints — discovered fresh from the current goal, disposable after use. These provide visibility into edges that would cause problems if crossed blindly: scope creep, missing user opinions, abstract requirements that need to become definite. This is different from static process constraints (hardcoded gates, enforcement hooks, "MUST do X before Y" rules baked into workflow definitions) which carry maintenance cost and go stale. RT-ICA's value is turning the abstract into the definite for each specific task.

## Self-Initialization from Backlog Item

When invoked with a `#N` argument (e.g., `Skill(skill='dh:rt-ica', args='#42')`):

1. Load item context before doing anything else:

```text
mcp__plugin_dh_backlog__backlog_view(selector="#N", summary=false)
```

2. Extract: `title`, `description`, `sections['acceptance criteria']`,
   `sections['expected behavior']`, `sections['impact radius']`, and any other populated sections.
3. Use the loaded content as the goal input for the RT-ICA procedure below.
4. After completing the assessment, write the RT-ICA result back to the item:

```text
mcp__plugin_dh_backlog__backlog_groom(selector="#N", section="RT-ICA", content="{RT-ICA SUMMARY block}")
```

Without a `#N` arg, the skill expects the goal/input to be provided inline in the invocation
context. Invoking without args and without inline context returns BLOCKED — always pass `#N`
when invoking from a workflow step that has an item reference.

## Activation Triggers

<activation_triggers>

Invoke RT-ICA when receiving ANY of:

- Spec, request, ticket, user story, PRD, architecture design, RFC
- Request to produce a plan, execution order, agent delegation, guardrails, acceptance criteria, or rollout steps
- Any multi-step engineering effort with dependencies, unknowns, constraints, or risk

**Integration Points** (where RT-ICA checkpoints MUST occur):

1. Before creating the top-level plan
2. Before delegating tasks to specialized agents (per-agent input completeness)
3. Before finalizing acceptance criteria (verify testability inputs exist)
4. Before defining rollout/ops steps (verify env and access inputs exist)

</activation_triggers>

## Definitions

<definitions>

| Term                     | Definition                                                             |
| ------------------------ | ---------------------------------------------------------------------- |
| **Goal**                 | A desired outcome the user wants                                       |
| **Condition**            | A prerequisite that must be true to achieve the goal                   |
| **Required Information** | Concrete data needed to confirm or satisfy a condition                 |
| **AVAILABLE**            | Explicitly present in the input material                               |
| **DERIVABLE**            | Inferred with high confidence from provided material (must show basis) |
| **MISSING**              | Not present and not safely inferable                                   |

</definitions>

## RT-ICA Procedure

Apply this procedure to each goal and sub-goal:

<procedure>

### Step 1: Goal Reconstruction

Produce:

- **Goal statement**: One sentence describing the desired outcome
- **Output form**: What deliverable proves success (artifact, behavior, metric, deployment state)
- **Scope boundaries**: In-scope/out-of-scope if stated

### Step 2: Reverse Prerequisite Enumeration

Work backwards from the goal to list ALL conditions required for success.

<condition_categories>

Include conditions in these categories (where applicable):

| Category                    | Example Conditions                                      |
| --------------------------- | ------------------------------------------------------- |
| Functional requirements     | Features, behaviors, user flows                         |
| Non-functional requirements | Latency, throughput, availability, compliance, security |
| Interfaces/Integration      | APIs, schemas, dependencies, external systems           |
| Environment/Runtime         | Cloud, region, OS, language, build system               |
| Data requirements           | Sources, quality, migration, retention                  |
| Access/Permissions          | Repos, secrets, credentials, IAM                        |
| Operational constraints     | SLOs, oncall, monitoring, incident response             |
| Delivery constraints        | Timeline, release process, approvals                    |
| Verification needs          | Tests, canaries, acceptance criteria, observability     |
| Risks/Failure modes         | Rollback, data loss, security exposure                  |
| Replacement coverage        | Full capability inventory of module being replaced, coverage matrix against replacement tool |
| Data Deletion Fidelity      | When goal text signals source data will be deleted (keywords: "delete", "remove", "drop", "migrate from X", "replace X with Y", "convert format", "remove source after migration"): acceptance criteria must include a content completeness check against real production data AND an explicit deletion gate. If absent: classify as MISSING. |

</condition_categories>

For each condition, specify:

- **Condition name**
- **Required information** to verify/satisfy it
- **Why it matters** (one line)

### Step 3: Availability Verification

For each condition, set status:

| Status        | Evidence Required                         |
| ------------- | ----------------------------------------- |
| **AVAILABLE** | Cite exact source snippet or section name |
| **DERIVABLE** | State the inference and basis             |
| **MISSING**   | State exactly what information is needed  |

### Step 4: Completeness Decision

```text
IF any condition is MISSING:
    DECISION = BLOCKED
ELSE:
    DECISION = APPROVED
```

### Step 5: Action Based on Decision

<decision_actions>

**IF BLOCKED:**

1. Do NOT plan
2. Ask ONLY for missing inputs
3. Structure questions by category, ordered by criticality
4. Prefer multiple-choice or constrained questions when possible
5. If user explicitly requests assumption-based planning:
   - Proceed with explicit assumptions for each missing condition
   - Include risk note per assumption
   - Add validation tasks to confirm assumptions early

**IF APPROVED:**

1. Proceed to normal planning
2. Carry forward the validated condition list
3. Mark DERIVABLE items as "assumptions to confirm"
4. Enforce constraints as guardrails

</decision_actions>

</procedure>

## Output Format

<output_format>

The model MUST produce this summary block for each goal/sub-goal:

```text
RT-ICA SUMMARY

Goal:
- [one sentence]

Success Output:
- [deliverable/observable result]

Conditions (reverse prerequisites):
1. [Condition] | Requires: [info] | Why: [1 line]
2. [Condition] | Requires: [info] | Why: [1 line]
...

Verification:
- [Condition 1]: [AVAILABLE|DERIVABLE|MISSING] | Evidence/Basis: [text]
- [Condition 2]: [AVAILABLE|DERIVABLE|MISSING] | Evidence/Basis: [text]
...

Decision:
- [APPROVED|BLOCKED]

--- IF BLOCKED ---
Missing Inputs Requested:

[Category]:
- [missing item question] (why needed)
- [missing item question] (why needed)

[Category]:
- [missing item question] (why needed)

--- IF APPROVED ---
Assumptions to Confirm (DERIVABLE only):
- [assumption] | Basis: [basis] | Validation step: [how to confirm early]
```

</output_format>

## Integration with CoVe-Style Planning

<cove_integration>

Recommended sequence with RT-ICA:

```text
A) RT-ICA on top-level goal
B) Draft plan and decomposition
C) RT-ICA on each major workstream/sub-goal
D) Assign agents with clearly bounded deliverables
E) Verification pass: cross-check plan against conditions and acceptance criteria
F) Refinement pass: resolve gaps, reduce risk, ensure ordering and guardrails
```

</cove_integration>

## Planning Deliverables (After APPROVED)

<planning_deliverables>

After RT-ICA APPROVED decision, produce a plan that includes:

| Section             | Contents                                               |
| ------------------- | ------------------------------------------------------ |
| Workstreams         | Logical groupings and ordering                         |
| Agent Assignment    | Which agent handles each workstream                    |
| Guardrails          | Safety, security, correctness, operational constraints |
| Acceptance Criteria | Testable, measurable success conditions                |
| Risk Register       | Top risks, mitigations, rollback strategy              |
| Dependencies        | Internal and external dependencies                     |
| Verification Plan   | Tests, monitoring, canary, QA                          |
| Change Management   | Rollout, communications, documentation                 |

</planning_deliverables>

## Guardrails

<guardrails>

RT-ICA exists to prevent hallucinated constraints. Without it, models fill knowledge gaps with training data patterns — inventing requirements and presenting them as facts. These guardrails protect that function.

**Redirection rule:**

When you notice yourself generating a value, constraint, or requirement that you cannot source from the input material — that impulse is a discovery, not a mistake. It reveals a gap. Redirect it:

1. The unsourced content becomes a new MISSING condition
2. Add it to the unknowns list with what you were about to fill in as a suggested default
3. Continue the assessment

Speculation is the signal that refinement is needed. The goal is not to suppress gap-filling — it is to catch it happening and route it into the unknowns list instead of into the plan as fact.

**Reflection checkpoint:** Before writing each condition's status (AVAILABLE / DERIVABLE / MISSING), pause and reflect using the sequential-thinking MCP. For each condition, the thinking step should answer: "Can I source this from the input material, or am I generating it from training patterns?" This external reflection makes the redirection rule structural — the pause is a tool call, not an internal decision that can be skipped.

**Never present unsourced content as verified.** Plan with MISSING conditions only when the user explicitly requests assumption-based planning.

**Best practice:**

- Keep missing-input questions minimal and high signal
- Prefer early validation tasks for DERIVABLE items
- Block planning when information is insufficient — localize the block to affected tasks where possible, not the entire plan

**Data Deletion Fidelity is never waivable:**

When any condition in the "Data Deletion Fidelity" category is MISSING, the decision is BLOCKED. This condition is **not eligible for assumption-based planning** (the exception clause in Step 5 does not apply). Deletion of source data without a fidelity gate is not a recoverable assumption — it is an irreversible data loss risk.

</guardrails>

## Question Templates

<question_templates>

When requesting missing inputs, use structured questions:

**Environment/Infrastructure:**

- "What is the target environment (prod/stage/dev), and where will this run (cloud/region/account)?"

**Success Criteria:**

- "What are the success metrics or acceptance criteria (latency, correctness, SLO)?"

**Integration:**

- "Which systems/APIs are in scope, and what are their interface contracts (schema/version)?"

**Technical Constraints:**

- "Are there constraints on language/framework/build tooling?"

**Approvals:**

- "Who owns approvals for release and security review (if required)?"

</question_templates>

## Example: RT-ICA in Action

<example>

**User Request:** "Build a user authentication service"

**RT-ICA Summary:**

```text
RT-ICA SUMMARY

Goal:
- Implement user authentication service for the application

Success Output:
- Deployed service that authenticates users and issues session tokens

Conditions (reverse prerequisites):
1. Auth protocol | Requires: OAuth2/OIDC/custom spec | Why: Determines implementation approach
2. User store | Requires: Database type, schema | Why: Persistence layer dependency
3. Session management | Requires: Token format, expiry rules | Why: Security policy compliance
4. Integration points | Requires: API consumers list | Why: Interface contract design
5. Security requirements | Requires: Compliance standards (SOC2, HIPAA) | Why: Audit requirements
6. Deployment target | Requires: Cloud/region/infra | Why: Runtime configuration

Verification:
- Auth protocol: MISSING | Need: Which protocol to implement
- User store: DERIVABLE | Basis: Project uses PostgreSQL per docker-compose.yml
- Session management: MISSING | Need: Token format and expiry policy
- Integration points: MISSING | Need: List of services calling auth
- Security requirements: MISSING | Need: Compliance requirements if any
- Deployment target: AVAILABLE | Evidence: README specifies AWS us-east-1

Decision:
- BLOCKED

Missing Inputs Requested:

Authentication Design:
- Which auth protocol: OAuth2, OIDC, or custom JWT? (determines implementation)
- Session token expiry policy? (security requirement)

Integration:
- Which services will consume this auth service? (API contract design)

Compliance:
- Are there compliance requirements (SOC2, HIPAA, etc.)? (audit scope)
```

</example>

## Anti-Patterns

<anti_patterns>

**Planning without RT-ICA:**

```text
User: "Build auth service"
Model: "Here's my plan: 1. Create user table, 2. Add login endpoint..."

Problem: Assumed requirements, will likely need rework
```

**Asking too many questions:**

```text
Model asks 20 questions about edge cases before understanding core requirements

Problem: Overwhelms user, delays progress on high-signal items
```

**Proceeding with silent assumptions:**

```text
Model: "I'll assume OAuth2 since that's common..."

Problem: Assumption may be wrong, causes rework or security issues
```

</anti_patterns>

## Related Skills

- `agent-orchestration` - Scientific delegation framework for orchestrator-to-agent workflows
- `subagent-contract` - DONE/BLOCKED signaling protocol for sub-agents

## Sources

| Source                       | Attribution                                                                                                            | Access Date |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ----------- |
| RT-ICA Framework             | [Liu et al., 2025 - Reverse Thinking Enhances Missing Information Detection in LLMs](https://arxiv.org/abs/2512.10273) | 2026-01-20  |
| CoVe (Chain of Verification) | [Dhuliawala et al., 2023 - Chain-of-Verification Reduces Hallucination](https://arxiv.org/abs/2309.11495)              | 2026-01-20  |

**Note**: This skill adapts the RT-ICA (Reverse Thinking for Information Completeness Assessment) framework for planning workflows.
