# Review principles

Apply this policy before universal or specialist review checks. Use it to decide whether a
candidate concern is an applicable, evidenced finding. Keep the caller's review scope, verdict,
artifact destination, and terminal response contract.

## Authority and applicability

Establish the target's supported behavior and environment from its requirements, interfaces,
callers, configuration, and active checks. Apply constraints in this order:

1. Explicit user requirements and applicable safety/security constraints.
2. The target project's supported versions, public contracts, architecture, dependency policy,
   active CI/lint/type-check gates, and established conventions.
3. The relevant runtime, framework, library, or host specification.
4. Specialist defaults and design preferences.

Resolve conflicts against the governing source and name the conflict when it affects the
review. A project preference cannot change a runtime or host's actual capabilities; report an
unsupported configuration as a compatibility conflict. Existing code and tests establish observed behavior; they do not automatically establish
approved intent. An existing convention cannot justify a demonstrated security or correctness
defect. Conversely, a different preferred framework, type shape, module system, tool, or layout
does not make a coherent supported choice defective.

Use language and runtime checks together when both apply. Determine applicability from the
changed source and relevant execution/configuration paths; a package manifest or file extension
alone does not establish every runtime in the project. Record unavailable specialist coverage.

Do not require a migration, new dependency, abstraction, file split, or additional permanent
test merely to satisfy a default. A measured limitation, incompatible contract, demonstrated
maintenance problem, or active project gate can justify that recommendation; cite its basis.

## Evidence and consequence

Treat a checklist pattern as a candidate to investigate. Before assigning blocking status:

1. Locate the affected code and applicable obligation, including the source of a required gate.
2. Identify the supported input, state, operation, or consumer for which the concern matters.
3. Inspect the relevant guard, caller, recovery path, or documented exception that could refute it.
4. State the concrete consequence and supporting evidence, or identify what remains unvalidated.

A static source trace, incompatible schema, or failure of an applicable deterministic gate can
establish a defect without reproducing a runtime failure. State what that evidence establishes;
do not label an unexecuted probe or authored test as observed behavior. Before recommending an
error-handling change, identify who owns recovery and whether an error signal or forbidden side
effect actually escapes the relevant boundary.

Make a finding blocking when it establishes a violated required contract, active project gate,
or material correctness/security property. Explain the affected behavior or policy and the
correction needed. Keep optional improvements distinct. Derive urgency from consequence and
exposure, not from a syntax match, topology metric, arbitrary score, or reviewer count.

Preserve material unresolved concerns with their evidence, uncertainty, and cheapest
discriminating next check in the caller's report. Do not silently discard an uncorroborated
concern or promote it to a confirmed defect. Missing evidence for a required acceptance
criterion remains subject to the caller's existing partial/unmet verdict rule.

## Review boundary

Read the actual source independently. Reuse supplied context and evidence as pointers to verify,
not conclusions to inherit. Distinguish new defects, existing defects exposed by the change,
and unrelated existing issues using the declared scope.

Keep review read-only for the target code, tests, documentation, and generated state. Do not
run autofix or destructive probes as part of review. Use safe authorized checks and record
unavailable evidence. A separately authorized disposable experiment must preserve the original
target and report its own boundary; a tool's presence is not permission to modify the target.

For test effectiveness, use `/dh:test-reviewer`; for causal investigation that needs more than
the bounded source trace, use `/dh:root-cause-tracing-process`. Carry the applicable contract
and evidence into those existing procedures. Return their relevant findings through the
caller's existing protocol rather than creating another verdict or tracking system.
