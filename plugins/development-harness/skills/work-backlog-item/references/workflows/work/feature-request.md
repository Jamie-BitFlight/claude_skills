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

**Planner constraint**: Create tasks for every item listed above, or document the exclusion reason inline. The plan is incomplete if any row in the Impact Radius is unaddressed.

**Ecosystem Completeness Checklist** (must all be checked before the plan can be marked complete):
- [ ] Every upstream producer updated or verified compatible
- [ ] Every downstream consumer migrated to new interface
- [ ] Every stale document updated
- [ ] Old interface deprecated or removed (if replacing)
- [ ] CI/config files updated and validated

### Stack Profile (optional)

{stack profile name if --stack specified, e.g., python-fastapi}
```

If `--stack` was specified, append a "Stack profile" line. If `--language` was specified and is not `python`, invoke the corresponding language plugin (e.g., `/typescript-development:add-new-feature` for `typescript`).
