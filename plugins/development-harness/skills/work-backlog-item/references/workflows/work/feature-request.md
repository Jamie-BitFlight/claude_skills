# Feature Request Template (Step 4.1)

Build this string for `add-new-feature`:

```text
## Backlog Item: {title}

**Source**: {source}
**Priority**: {priority section — P0/P1/P2/Ideas}
**Added**: {added date}

### Description

{description text}

### Research Questions

{research_first text, or "None" if absent}

### Suggested Location

{suggested_location text, or "To be determined during architecture phase" if absent}

### RT-ICA Assessment

**Decision**: APPROVED
**Goal**: {goal statement}
**Verified conditions**: {list of AVAILABLE items}
**Assumptions to confirm**: {list of DERIVABLE items, or "None"}

### Grooming Context

{full context manifest from Step 3, if available}

### Impact Radius

{full content of the ## Impact Radius section from the `backlog_view` response — fall back to the
`## Resources` section when Impact Radius is absent (older grooming template; see groom-check.md)}

**Planner constraint**: Address every row under `### Systems Inventory` with an implementation,
verification, content, configuration, agent, process, or other task appropriate to its `Action`
field, or document why an existing task covers it. Do not create tasks for categorized views,
excluded candidates, or evidence citations. Convert each unknown-frontier closure condition into a
research task or an explicit planning assumption. The plan is incomplete when a canonical system
or unresolved unknown has no disposition.

**Ecosystem Completeness Checklist** (must all be checked before the plan can be marked complete):
- [ ] Every upstream producer updated or verified compatible
- [ ] Every downstream consumer migrated to new interface
- [ ] Every stale document updated
- [ ] Old interface deprecated or removed (if replacing)
- [ ] CI/config files updated and validated
```
