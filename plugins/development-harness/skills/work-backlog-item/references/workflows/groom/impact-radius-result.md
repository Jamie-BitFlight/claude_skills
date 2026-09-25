# Impact Radius Contract

This reference owns the Development Harness serialization and persistence contract for an impact-analysis result. The reusable `dh:analyze-change-impact` skill owns the analysis method.

## Persistence

In backlog mode, replace the previous active snapshot:

```text
mcp__plugin_dh_backlog__backlog_groom(
    selector=<value>,
    section="Impact Radius",
    content=<impact-radius-content>,
    replace_section=True,
    reason="impact analysis refreshed"
)
```

Replacing the section strikes the previous snapshot while preserving history. Do not append a second active report: downstream conflict detection reads active `Systems Inventory` entries.

Do not include `## Impact Radius` in `<impact-radius-content>`; the named section supplies it. Direct mode returns the report inline and does not write backlog state.

## Required leading records

```text
SCOPE_EXPANSION: Found {N} systems outside the starting impact set - {summary}. This expands fact-check scope to: {list}.
IMPACT_RADIUS_COMPLETE: {Written to item {selector}|Returned inline for {change boundary}}. Overall risk: {LOW|MEDIUM|HIGH}. Highest-risk: {top systems}.
```

When scope does not expand, use `SCOPE_EXPANSION: None.`.

## Report schema

```markdown
### Change Frame
- Baseline: ...
- Delta: ...
- Intended outcome: ...
- Non-goals: ...
- Time horizon and rollback boundary: ...

### Impact Pathways
- `change -> edge -> changed state or decision -> outcome -> stakeholder` | Owner: ... | Evidence: ... | Confidence: OBSERVED|INFERRED|UNKNOWN | Verification: ...

### Code - Producers
- `{path}::{symbol}` - {consequence and obligation} | Risk: {level} | Why: {reason}

### Code - Consumers
- `{path}::{symbol}` - {consequence and obligation} | Risk: {level} | Why: {reason}

### Code - Other References
- `{path}` - {consequence and obligation} | Risk: {level} | Why: {reason}

### Tests
- `{path}` - {interaction covered or missing and resulting obligation} | Risk: {level} | Why: {reason}

### Documentation
- `{path}` - {claim or guidance affected} | Risk: {level} | Why: {reason}

### Configuration / CI
- `{path}` - {runtime, deployment, validation, or release effect} | Risk: {level} | Why: {reason}

### Agent Instructions
- `{path}` - {instruction or workflow effect} | Risk: {level} | Why: {reason}

### Data / State / Runtime
- `{system}` - {transition, compatibility, rollback, or operational effect} | Risk: {level} | Why: {reason}

### Models / Prompts / Context
- `{system}` - {evaluation, drift, retrieval, tool, context, or downstream decision effect} | Risk: {level} | Why: {reason}

### People / Process / Controls
- `{system}` - {role, handoff, approval, policy, control, or customer effect} | Risk: {level} | Why: {reason}

### Systems Inventory
- `{system}` | Role: {role} | Propagation: {causal path} | Outcome: {result} | Stakeholder: {who or what} | Owner: {role or system} | Evidence: {source} | Confidence: {OBSERVED|INFERRED|UNKNOWN} | Verification: {post-change check} | Action: {action} | Risk: {level} | pattern: '{optional exact literal}' | pattern_count: {optional baseline count}

### Excluded Candidates and Unknown Frontier
- Excluded: `{system}` - {evidence that contains the path}
- Unknown: `{path or boundary}` - {missing evidence and why the path remains credible} | Owner: {role or system} | Closure: {evidence or action that resolves the unknown}

### Transition, Rollback, and Observability
- Transition states: ...
- Irreversible state and rollback limit: ...
- Leading indicators and failure signals: ...
- Paired baseline/candidate comparison: ...
- Post-change review owner and trigger: ...

### Risk Summary
- Overall system risk: {LOW|MEDIUM|HIGH}
- Highest-risk systems: ...
- Main risk themes: ...
- Scope expansion: ...

### Ecosystem Completeness Checklist
- [ ] Every material propagation path has evidence or an explicit unknown
- [ ] Producers, consumers, state owners, and downstream decisions checked
- [ ] Tests, docs, config, CI, operations, and agent instructions checked
- [ ] Applicable data, model, prompt, context, people, process, and control effects checked
- [ ] Transition, rollback, delayed effects, and observability checked
- [ ] Replacement or removal preserves the purpose of existing capabilities and controls
```

For an empty category, write `None identified.` plus the evidence boundary. `Systems Inventory` is the canonical machine-readable estimated impact set; include each affected system exactly once. Categorized sections are human-readable views and do not define scope.

Use repository-relative paths. Bare `Dockerfile` and `Makefile` are conventional extensionless root files. Prefix other one-segment repository paths with `./` so they remain distinguishable from logical systems.

Do not place excluded candidates in the inventory. Put unresolved credible paths in the unknown frontier with an owner and closure condition.

Optional `pattern:` / `pattern_count:` fields are lexical staleness probes only. Add them only when one fixed literal precisely enumerates the row's scope; never use the count as evidence of impact or risk.

## Validation and completion

After backlog persistence, read the item again. In direct mode, inspect the report. Verify both leading records and every required heading are present before reporting completion.

Backlog mode returns `STATUS: BLOCKED` if the item cannot be read or updated. Otherwise return `STATUS: DONE` plus overall risk, highest-risk systems, estimated impact-set count, and unknown-frontier count.
