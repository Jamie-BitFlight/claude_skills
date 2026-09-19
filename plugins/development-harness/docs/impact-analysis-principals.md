# Change-impact analysis across technical and business systems

Change-impact analysis is the disciplined process of predicting, testing, and then observing how a proposed change alters system outcomes.

It is broader than identifying modified files, components, models, prompts, or process steps. Those tell us where implementation occurs. Impact analysis asks where consequences propagate.

A useful framing question is:

> If we introduce this change into the current baseline, which outcomes could change, for whom, through which propagation paths, over what period, with what uncertainty, and how will we detect and control those effects?

## The current state of practice

As of September 2026, there is no single standard that covers software, physical systems, ML, generative AI, and business processes equally well. There is, however, strong convergence across the disciplines:

- NASA’s engineering guidance traces changes through requirements, architecture, interfaces, operations, safety, cost, schedule, stakeholders, tests, and documentation. It also asks teams to compare the risk of making the change with the risk of not making it. [NASA requirements-change guidance](https://swehb.nasa.gov/spaces/7150/pages/16449679/SWE-053%2B-%2BManage%2BRequirements%2BChanges)
- ISO 31000 treats risk as contextual, tied to objectives, integrated with decision-making, inclusive of stakeholders and human factors, and subject to continual review. [ISO 31000](https://www.iso.org/standard/65694.html)
- NIST’s AI Risk Management Framework organizes AI risk work around governance, mapping, measurement, and management throughout the lifecycle, including after deployment. [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- Production ML research highlights entanglement, undeclared consumers, data dependencies, external change, and feedback loops that ordinary code dependency analysis misses. [Google Research on ML technical debt](https://research.google/pubs/machine-learning-the-high-interest-credit-card-of-technical-debt/)
- Modern context engineering treats prompts, tools, retrieved data, memory, message history, and runtime state as one behavioral system. [Anthropic on context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Production engineering increasingly validates changes through controlled exposure, representative measurements, and comparison with an unchanged control population. [Google SRE on canary releases](https://sre.google/workbook/canarying-releases/)
- Business-process guidance emphasizes mapping actual work, information flows, roles, external interfaces, policies, dependencies, and performance, then validating the map with people who perform the work. [US GAO Business Process Reengineering Guide](https://www.gao.gov/assets/aimd-10.1.15.pdf)

My synthesis is that the state of the art has moved from a one-time “affected items” checklist toward a continuous, evidence-linked analysis of a whole socio-technical system.

## Core principles

### 1. Analyze a delta against a named baseline

“Add a new model,” “change the approval process,” or “improve the prompt” is not precise enough.

Describe:

- The current baseline and its version.
- The exact proposed delta.
- The intended outcome.
- What should remain invariant.
- Assumptions about the operating environment.
- Explicit non-goals.
- When and how the change will be introduced.

Impact is a difference between outcomes under the baseline and candidate conditions. Without a baseline, teams cannot distinguish improvement, regression, unrelated environmental variation, or pre-existing failure.

The baseline must include actual behavior, not only documented behavior. Undocumented workarounds, shadow processes, configuration, tribal knowledge, data conventions, and downstream consumers all count.

### 2. Start from outcomes, not implementation artifacts

A dependency graph tells us what may be reached. It does not tell us why the reach matters.

Define the outcomes and constraints against which impact will be judged:

- Mission or business outcome.
- Functional correctness.
- Reliability and availability.
- Performance, capacity, latency, and cost.
- Safety and environmental consequences.
- Security, privacy, and regulatory obligations.
- Accessibility, usability, and human workload.
- Fairness or distributional effects.
- Maintainability and operational burden.

Include intended benefits and potential harms. Also assess the consequences of leaving the system unchanged.

### 3. Treat the system as socio-technical

The system boundary normally includes more than the artifact being edited:

- Software, infrastructure, hardware, models, prompts, and tools.
- Data sources, schemas, labels, caches, and retained state.
- Users, operators, reviewers, support staff, and decision-makers.
- Policies, incentives, responsibilities, training, and handoffs.
- Suppliers, clients, regulators, and other external actors.
- The physical, commercial, and regulatory environment.

The boundary is a working hypothesis. When analysis discovers another consequential dependency, expand the boundary.

For an AI assistant, for example, “the system” is not merely the model. It includes the system prompt, context assembly, retrieval sources, tool definitions, authorization, orchestration code, user interface, human escalation process, logs, evaluators, and people affected by its decisions.

### 4. Trace causal propagation, not just adjacency

A useful impact map identifies how a change could produce a consequence:

```text
change
  → altered component, rule, data, or behavior
  → affected interface or decision
  → changed downstream action or state
  → consequence for an outcome or stakeholder
```

Trace several kinds of paths:

- Direct: the changed element behaves differently.
- Downstream: consumers receive different data or behavior.
- Upstream: producers must meet a new contract or quality requirement.
- Shared-resource: load, cost, capacity, or contention changes.
- Control: authorization, validation, audit, or safety controls change.
- Human: workload, incentives, responsibility, or decisions change.
- Feedback: the output changes future input, behavior, labels, or demand.
- External: suppliers, regulations, markets, or adversaries respond.

ML systems deserve particular attention here. Changing rankings may alter what users see, which changes user behavior, which changes future training data. The resulting effect is a loop, not a linear dependency.

### 5. Analyze time and transition states

Teams often analyze only the desired steady state. Many failures occur during the move to it.

Consider at least:

1. Preparation and migration.
2. Mixed-version or coexistence operation.
3. Cutover.
4. Steady-state operation.
5. Dependency or operator failure.
6. Rollback and recovery.
7. Retirement and removal of the old path.

Examples include dual database schemas, old and new clients using one API, staff learning a new procedure, caches containing old values, a model receiving partially migrated features, or an agent using a new prompt with an old retrieval index.

A rollback plan is not credible until the team has considered whether state changes, data migrations, customer actions, and external notifications can actually be reversed.

### 6. Express uncertainty rather than hiding it in a score

For each material scenario, record:

- Consequence severity.
- Number and type of people or systems exposed.
- Likelihood or frequency.
- Detectability and time to detection.
- Reversibility and recovery time.
- Evidence quality.
- Confidence in the assessment.

Do not collapse these automatically into a single magic number. NASA explicitly warns that simple risk matrices do not represent interactions, aggregate risk, or uncertainty well. They are communication aids, not complete assessment models. [NASA Systems Engineering Handbook](https://www.nasa.gov/wp-content/uploads/2018/09/nasa_systems_engineering_handbook_0.pdf)

A rare, catastrophic, hard-to-detect, irreversible failure may deserve more attention than a common, harmless, immediately reversible one.

Classify important statements as:

- **Known:** directly supported by current evidence.
- **Assumed:** plausible but not yet verified.
- **Unknown:** recognized gap requiring investigation or monitoring.

### 7. Scale the analysis to criticality and reversibility

Not every change requires a committee or a fifty-page document.

A lightweight review may be sufficient when the change is local, observable, reversible, familiar, and outside critical controls.

Analysis should deepen when the change has one or more of these characteristics:

- Broad or poorly understood reach.
- Safety, security, privacy, legal, or financial consequences.
- Irreversible data or physical effects.
- High autonomy.
- Low observability or slow feedback.
- Novel technology or operating conditions.
- Numerous downstream consumers.
- Important human or organizational changes.
- Strong feedback loops.
- Simultaneous interacting changes.

The purpose is decision quality, not documentation volume.

### 8. Treat claims about impact as hypotheses requiring evidence

Different claims need different evidence:

| Claim | Useful evidence |
|---|---|
| A contract remains compatible | Schema checks, contract tests, consumer tests |
| A safety or security invariant remains true | Threat or hazard analysis, static analysis, formal checks, adversarial tests |
| Performance remains acceptable | Representative load test and production telemetry |
| A model improves | Held-out and slice evaluations, calibration, repeated trials, online comparison |
| A prompt behaves better | Representative eval set, adversarial cases, transcript review, repeated trials |
| A process reduces cycle time | Baseline timing, pilot data, queue measurements |
| Operators can execute the procedure | Simulation, tabletop exercise, observed rehearsal |
| Customers prefer the change | User research or controlled experiment |
| A rollout caused an observed effect | Candidate-versus-control comparison with attributable metrics |

For generative systems, output variability makes single-example demonstrations particularly weak evidence. Current evaluation practice emphasizes real-world cases, explicit criteria, expert-labelled examples, continuous evaluation, production monitoring, and human calibration. [OpenAI’s Specify, Measure, Improve approach](https://openai.com/index/evals-drive-next-chapter-of-ai/) and [Anthropic’s agent-evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) both reflect this lifecycle approach.

### 9. Make observability, containment, and recovery part of the change

If a harmful impact would be invisible, the change is riskier than the same change with reliable detection.

Useful controls include:

- Invariants and validation at system boundaries.
- Least privilege and limited action scopes.
- Shadow execution or dry runs.
- Feature flags or policy switches.
- Partial rollout or pilot groups.
- Canary populations with an unchanged control.
- Human approval for consequential cases.
- Rate, spend, or exposure caps.
- Versioned configurations and artifacts.
- Explicit rollback thresholds.
- Incident and contingency procedures.

A canary is useful only when its population is representative, its metrics are attributable to the candidate change, and the observation window is long enough to expose the relevant behavior.

### 10. Close the change only after observing the system

Deployment or policy publication is not completion.

After release:

- Compare observed outcomes with the baseline and acceptance thresholds.
- Review both aggregate results and important subgroups.
- Look for unexpected downstream effects.
- Check assumptions and residual risks.
- Sample logs, cases, decisions, or process instances.
- Update tests, evals, process maps, documentation, and ownership records.
- Define triggers that reopen the analysis, such as drift, a supplier change, a new regulation, or a rising error rate.

NIST applies this explicitly to security: analyze potential security effects before implementation and verify afterward that security requirements remain satisfied. [NIST SP 800-171 Rev. 3, Impact Analyses](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/800-171r3/NIST.SP.800-171r3.html)

## A reusable eight-step process

### 1. Frame the change

Produce a concise change statement:

```text
From baseline:
To candidate:
Objective:
Expected benefit:
Must remain unchanged:
Assumptions:
Out of scope:
Owner:
Decision deadline:
```

### 2. Map the actual system

Map components, interfaces, data and state, people and roles, controls, suppliers, external actors, and feedback loops.

Validate the map with the people who build, operate, consume, and experience the system.

### 3. Trace propagation paths

For every changed element, ask:

- Who or what reads its output?
- Who supplies its input?
- What state does it create or mutate?
- Which decisions depend on it?
- Which controls constrain it?
- Which metrics observe it?
- What documentation, training, and support assume its current behavior?
- Can its output affect its future input?

Stop tracing a branch when it cannot materially affect an identified outcome, not merely when it crosses a team boundary.

### 4. Construct scenarios

Cover:

- Normal and boundary cases.
- Invalid, stale, missing, or adversarial input.
- Overload and resource exhaustion.
- Dependency failure.
- Operator or user error.
- Foreseeable misuse.
- Partial deployment.
- Recovery and rollback.
- Long-term drift or environmental change.

### 5. Assess consequences and uncertainty

For each scenario, record the propagation path, affected outcome, stakeholders, benefit or harm, exposure, likelihood, severity, detectability, reversibility, confidence, and owner.

Prioritize scenarios where consequences are severe, exposure is broad, detection is difficult, recovery is slow, or confidence is weak.

### 6. Design treatment and evidence

Choose among avoiding, reducing, isolating, staging, monitoring, transferring, accepting, or rejecting the risk.

Every material claim should have:

- A validation method.
- A success threshold.
- An owner.
- A point in time when the evidence will exist.

### 7. Decide and stage the change

Record:

- Go and no-go criteria.
- Residual risks and the authority accepting them.
- Rollout stages.
- Abort and rollback thresholds.
- Communication and training.
- Incident ownership.
- Which concurrent changes would invalidate the evidence.

### 8. Observe and update

Measure real outcomes, investigate discrepancies, add newly discovered cases to tests or evals, and update the impact map.

The resulting artifact can remain small:

| Path | Outcome and stakeholder | Scenario | Assessment and confidence | Control | Evidence and threshold | Owner and review trigger |
|---|---|---|---|---|---|---|

## How the method applies in each domain

| Domain and example change | Propagation paths | Important impacts | Evidence and rollout |
|---|---|---|---|
| **Software:** Change an authentication library | Token formats, identity providers, session state, authorization middleware, clients, audit logs, key rotation, incident tooling | Login failures, privilege errors, latency, compatibility, security posture, support load | Contract and negative-path tests, rotation and rollback rehearsal, security review, canary release, authentication and authorization telemetry |
| **Machine learning:** Replace a ranking model | Features, training data, serving pipeline, exposed content, user behavior, moderation, revenue, future labels | Overall and subgroup quality, calibration, latency, exposure distribution, abuse, feedback loops, training-serving skew | Data validation, offline and slice evaluation, repeated trials, shadow inference, capped online experiment, drift and outcome monitoring |
| **Prompt/context engineering:** Add a retrieval source and action tool | System instructions, retrieval ranking, source provenance, token budget, tool selection, permissions, external state, transcript history | Grounding, stale information, instruction conflicts, prompt injection, unauthorized actions, cost, latency, refusal and escalation behavior | Canonical and adversarial evals, multiple trials, state-based graders, tool-call inspection, human transcript review, sandbox or read-only pilot, kill switch |
| **Business process:** Remove one invoice-approval step | Roles, handoffs, segregation of duties, exception queues, audit records, finance systems, suppliers, staff workload | Cycle time, fraud and error exposure, accountability, workload distribution, compliance evidence, supplier experience | Current/to-be process map, operator validation, historical case replay, limited pilot, queue and error measurement, audit sample, contingency procedure |
| **Integrated system:** Deploy an AI customer-support agent | Software, model, prompt, retrieval, customer records, action tools, policies, agents, supervisors, compliance, customer behavior | Resolution quality, erroneous actions, privacy, fraud, staff workload, escalation rates, cost, customer trust, future training data | End-to-end scenarios, access-control enforcement, representative evals, shadow mode, human approval, limited cohort, business and technical telemetry, rollback |

## One integrated worked example

Suppose an organization wants an AI support agent to issue refunds up to $250 instead of escalating every request.

The superficial description is “change the refund limit.” The impact analysis reveals at least five coupled changes:

1. A business policy changes who may authorize a refund.
2. Software and tool permissions allow the agent to mutate financial state.
3. The prompt and retrieved policy guide the agent’s decision.
4. Fraud, audit, finance, and customer-support processes receive different work.
5. Customer behavior and future support data may change in response.

The dependency map includes the refund API, identity and authorization, payment processor, order state, system prompt, retrieval corpus, fraud rules, customer history, duplicate-request handling, audit logs, escalation queues, support staff, and finance reconciliation.

Material scenarios include:

- A valid refund.
- A refund outside the permitted category.
- A duplicate or replayed action.
- Conflicting policy documents.
- Prompt injection in customer-supplied text.
- A payment processor timeout after partial completion.
- A user disputing a completed refund.
- Fraudsters learning the automated threshold.
- Disabling the feature after refunds have already changed external state.

Appropriate controls could include server-side enforcement of the limit, least-privilege credentials, idempotency, authoritative policy retrieval, human approval between $100 and $250 during the pilot, a rate cap, a representative historical eval set, adversarial cases, shadow execution, sampled transcript review, a small customer cohort, and a tool-level kill switch.

Success must include more than the model saying the right thing. Relevant outcomes include whether the correct financial state exists, duplicate refunds remain prevented, prohibited cases are escalated, resolution time improves, fraud remains within tolerance, reconciliation succeeds, and affected customers receive accurate communication.

That is change-impact analysis across software, AI, context, and business process as one system.

## Common failure modes

- Treating the implementation diff as the complete impact boundary.
- Mapping components without explaining how consequences propagate.
- Testing only intended behavior and the final steady state.
- Measuring averages while hiding affected subgroups or rare severe cases.
- Assigning precise-looking risk scores without evidence or confidence.
- Treating documentation, staffing, training, and support as deployment chores rather than system dependencies.
- Calling rollback a control when irreversible state has already escaped the system.
- Evaluating an ML model without its data and feedback loops.
- Evaluating a prompt without its tools, context assembly, permissions, and runtime environment.
- Closing the change when it ships instead of when outcomes are observed.

The compact rule I would leave with the group is:

> Trace from the proposed delta to outcomes through the real system, make uncertainty visible, demand evidence proportional to consequence, constrain exposure, and continue the analysis until operational results confirm or revise the prediction.

The supporting primary-source research and evidence table are in [change-impact-analysis-research.md](/Users/jamienelson/change-impact-analysis-research.md).

Research basis: official standards bodies, government engineering guidance, original research, and first-party engineering publications. Examples and the unified process are my synthesis. No direct quotations were used.

STATUS: DONE
