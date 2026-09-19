# Change-impact analysis gap supplement

This supplement extends [Impact Analysis Principles](./impact-analysis-principals.md) without
altering that document's verbatim briefing. It records the material additions found by comparing
the briefing with the supplied `impact-analysis-principles.md` scratchpad.

Apply only the branches relevant to the change under analysis. A pre-change analysis is complete
when every triggered branch has either current evidence or a named post-change verification owner
and trigger. The full lifecycle closes later, when the actual effects have been compared with the
prediction; do not fabricate those observations during planning.

## Integrated additions

### Scope boundary

Impact analysis determines what needs examination because of one delta. Testing checks selected
behavior, general risk assessment considers the wider system risk profile, and artifact review
examines the proposed implementation. They contribute evidence, but none substitutes for tracing
the delta through the real system.

### Impact-set calibration

Use four sets to make the prediction auditable:

- **Change set:** elements intentionally modified.
- **Starting impact set:** the change set and the first dependencies selected for investigation.
- **Estimated impact set:** elements and outcomes predicted to be affected after tracing
  propagation.
- **Actual impact set:** elements and outcomes observed to have changed after implementation.

The terminology comes from software change-impact analysis, but the model transfers directly to
data, models, prompts, tools, roles, policies, and processes. [Bohner and Arnold's foundational
text](https://dl.acm.org/doi/10.5555/525066) introduced the software formulation; later systems
work describes the same distinction between starting, candidate, and actual impact sets.
[Architecture-based change-impact analysis](https://publikationen.bibliothek.kit.edu/1000098183/62335551)

At post-change review, calculate two kinds of error:

- **False negatives:** actual impacts absent from the estimated set. These reveal missing
  dependencies, scenarios, or measurements.
- **False positives:** estimated impacts absent from the actual set. These reveal review or test
  work that may be narrowed next time.

The objective is calibrated coverage, not an unbounded search for every conceivable effect.
High-consequence false negatives matter most, but persistent false positives also make the process
too expensive to use routinely.

### Implicit contracts and external triggers

Add a dedicated implicit-contract probe to dependency tracing:

- Which observable timing, ordering, formatting, distribution, wording, or error behavior might a
  consumer rely on even though no specification promises it?
- Who would notice if the behavior stopped, slowed down, changed format, or improved?

Also start an impact analysis when an external delta reaches the system. Examples include a model
alias update, input-distribution drift, a changed retrieval corpus, a supplier or regulator change,
an operating-system update, or a third-party API default change. Pin versions and snapshots where
possible; otherwise use continuous baseline checks to make external drift observable. ML research
identifies undeclared consumers, feedback loops, data dependencies, and changes in the external
world as system-level risks. [Hidden Technical Debt in Machine Learning
Systems](https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems)

### Purpose before removal

Before changing or removing an apparently redundant element, establish why it exists. Check
version history, incident records, decision records, operating procedures, and the people who own
the work. Treat an unexplained validation, approval, prompt instruction, feature rule, clipping
rule, delay, or retry as a possible compensating control until evidence establishes otherwise.

Record the recovered purpose in the impact analysis. If it cannot be established, mark that
uncertainty explicitly and increase rollout containment rather than silently assuming the element
has no function.

### Time, persistence, and paired measurement

Classify predicted effects as:

- **Immediate:** visible at deployment or process cutover.
- **Delayed:** visible only after state accumulates, a full business cycle completes, or a rare
  condition occurs.
- **Self-reinforcing:** the change alters future inputs, behavior, labels, memory, incentives, or
  demand.

For every state-writing change, ask: “If we revert in two weeks, what will not return to the
baseline?” Code, prompts, or procedures may be reversible while stored data, issued payments,
trained models, long-term memory, customer expectations, and organizational capability are not.

Measure old and new behavior on the same inputs whenever possible. A paired comparison reduces
input variation and makes smaller behavioral differences visible. For nondeterministic systems,
repeat trials and compare distributions or success rates rather than relying on one output.

### Control-loop hazard probe

Component checks miss failures created by correct components interacting at the wrong time or
under an unsafe control structure. For consequential control actions, supplement dependency
analysis with four questions:

1. Could providing the action cause harm?
2. Could not providing it cause harm?
3. Could providing it too early, too late, or out of sequence cause harm?
4. Could stopping it too soon or applying it too long cause harm?

These questions apply to API calls, model gates, agent tool use, approvals, escalations, physical
controls, and human decisions. They are adapted from Systems-Theoretic Process Analysis, which
analyzes unsafe control actions within system control loops. [MIT STPA
Handbook](https://psas.scripts.mit.edu/home/get_file1.php?name=STPA_Handbook.pdf)

## Additions to the reusable process

Insert these checks into the briefing's eight-step process:

1. During **Frame the change**, state whether the trigger is internal or environmental and record
   the change set. Complete this check when every authored and externally supplied delta is named.
2. Before **Map the actual system**, recover the purpose of each changed or removed control.
   Complete this check when each purpose has evidence or is marked unknown with stronger
   containment.
3. During **Trace propagation paths**, record the starting and estimated impact sets and probe
   implicit contracts. Complete this check when every candidate impact has a propagation path and
   owner.
4. During **Construct scenarios**, classify immediate, delayed, and self-reinforcing effects and
   run the control-action questions where consequences warrant it. Complete this check when every
   material scenario has a time class and every consequential control action has all four outcomes
   assessed.
5. During **Design treatment and evidence**, require paired old-versus-new measurement when the
   same inputs can be replayed. Complete this check when the input set, repetitions, comparison
   metric, and acceptance threshold are recorded.
6. During **Observe and update**, record the actual impact set, false negatives, false positives,
   and the resulting updates to dependency maps, evaluations, and checklists. Complete this check
   when every prediction error has a disposition and owner.

## Compact closure checklist

- Is the delta precise, including externally caused changes?
- Is the purpose of each changed or removed element known?
- Are explicit dependencies, implicit contracts, and feedback loops mapped?
- Are immediate, delayed, persistent, and self-reinforcing effects covered?
- Are baseline and candidate results compared on the same inputs where possible?
- Are consequential control actions checked for omission, commission, timing, ordering, and
  duration hazards?
- Are containment, detection, rollback triggers, and ownership decided before exposure?
- After rollout, were estimated and actual impact sets compared and the analysis process updated?

## Maintainer comparison ledger

This ledger records why the supplement exists. It is provenance for maintainers, not an execution
checklist.

| Comparison claim | Briefing coverage | State | Integrated action |
|---|---|---|---|
| Distinguish impact analysis from testing, general risk assessment, and artifact review | The briefing distinguishes implementation location from propagated consequences, but does not name the three boundaries | MISSING | Add an explicit scope boundary below |
| Record a starting, estimated, and actual impact set | The briefing maps affected elements and later observes outcomes, but does not compare the predicted and actual sets | MISSING | Add the impact-set calibration loop below |
| Treat implicit contracts as a first-class dependency class | The briefing includes undocumented behavior and downstream consumers, but does not give implicit contracts their own review step | PARTIAL | Add an implicit-contract probe below |
| Trigger analysis for external changes | The briefing includes environmental dependencies and drift scenarios, but frames the initiating delta mainly as a proposed internal change | PARTIAL | Add external trigger conditions below |
| Learn why an element or control exists before removing it | The briefing assesses controls but does not require purpose and history discovery before removal | MISSING | Add a purpose-before-removal gate below |
| Separate immediate, delayed, and self-reinforcing effects | The briefing covers transition, steady state, rollback, drift, and feedback loops without this explicit time classification | PARTIAL | Add the temporal classification below |
| Compare old and new behavior on identical inputs | The briefing requires baselines, representative evidence, and candidate-versus-control comparison, but does not require a paired comparison | PARTIAL | Add paired comparison below |
| Analyze unsafe control actions and interactions, not only component failures | The briefing traces control paths but does not provide a control-loop hazard method | MISSING | Add the control-action probe below |

The comparison otherwise matched the briefing on the core method: define the delta and baseline,
set outcome criteria, model the socio-technical boundary, trace propagation, assess multiple impact
dimensions and uncertainty, scale rigor to consequence, stage exposure, preserve recovery paths,
monitor production outcomes, and feed observations back into the analysis.
