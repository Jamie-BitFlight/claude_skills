# Final Handoff Output

> [!IMPORTANT]
> When provided a process map or Mermaid diagram, treat it as the authoritative procedure. Execute steps in the exact order shown, including branches, decision points, and stop conditions.
> A Mermaid process diagram is an executable instruction set. Follow it exactly as written: respect sequence, conditions, loops, parallel paths, and terminal states. Do not improvise, reorder, or skip steps. If any node is ambiguous or missing required detail, pause and ask a clarifying question before continuing.
> When interacting with a user, report before acting the interpreted path you will follow from the diagram, then execute.

The following diagram is the authoritative procedure for Final Handoff Output. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

## Concerns Check — Implementation Notes

The first step reads the Concerns section of the just-resolved item before routing to the next work
item. When the item carries no backend reference, skip that read and go to the slug search; a
missing reference is not a backend failure.

**Selector source (`{item_ref}`)**: `{item_ref}` is what the `complete-implementation` skill stored in **Step 3 -- Extract context for proportional gates**: the `backlog_view` response's opaque `reference`. That step runs on either backend. The value is a GitHub integer on a GitHub backend and a string such as `bd-a3f8` on beads; pass it unchanged as `{item_ref}` in the `backlog_view` call below.

**Call signature**:

```text
backlog_view(selector="{item_ref}", summary=False, section="Concerns")
```

**Active-entry detection**: An entry is active if it is NOT struck-through (`` ~~entry~~ ``) and NOT a checked checkbox (`[x] entry`). Inactive entries were processed during the P6 Concerns verification phase — only active entries are actionable at handoff.

**Display format when active entries exist**:

```text
## Unresolved Concerns from {item_ref}

- {entry text verbatim}
...

Review these concerns before proceeding. You may choose to create backlog items for any that require follow-on work.
```

The Concerns block is displayed first, followed by a blank line separator, before any slug-search output.

**Error handling**: When the call was made and `backlog_view` returns an `error` key, output
`⚠ Could not read Concerns section: {error}` and continue to the slug search. The Concerns check is
advisory — backend errors must not block Final Handoff. Emit no warning when the item carries no
reference, because no call was attempted.

**`section=` caveat**: The `section=` parameter has no effect on GitHub-only items with a raw body — the full body may be returned. When this occurs, scan the response body for a `## Concerns` heading and extract the list items beneath it. Apply active-entry detection to those items only.

```mermaid
flowchart TD
    %% Step 1: Read Concerns from the just-resolved item — MUST run before slug-search routing
    %% {item_ref} = the item reference stored by 'Extract context for proportional gates' Step 3
    Start([Final handoff]) --> HasRef{"Item reference<br>available?"}
    HasRef -->|"No"| Fetch
    HasRef -->|Yes| ConcernsCheck["backlog_view(selector='{item_ref}', summary=False, section='Concerns')<br>Read Concerns from the just-resolved item"]
    ConcernsCheck --> ConcernsError{"Call returned<br>error key?"}
    ConcernsError -->|"Yes — backend error"| WarnContinue["⚠ 'Could not read Concerns section: {error}'<br>Non-blocking — continue to slug search"]
    ConcernsError -->|"No — call succeeded"| HasActiveConcerns{"Active entries in<br>Concerns section?<br>(not strikethrough, not checked)"}
    HasActiveConcerns -->|"Yes — 1+ active entries"| DisplayConcerns["Display concerns block:<br>## Unresolved Concerns from {item_ref}<br>- {each active entry verbatim}<br>Review — you may create backlog items if needed"]
    HasActiveConcerns -->|"No — absent or all processed"| Fetch
    DisplayConcerns --> Fetch
    WarnContinue --> Fetch
    %% The filter is mandatory — do NOT substitute a general P1/P2 listing already in context
    Fetch["backlog_list(title='{slug}')<br>Slug-filtered search — mandatory, not substitutable"] --> ItemFound{"First result returned<br>(item found)?"}
    ItemFound -->|"No — zero results"| NothingQueued["Clear context and run:<br>/dh:work-backlog-item — nothing queued —"]
    ItemFound -->|"Yes"| PlanSet{"item.plan set and non-empty?<br>(boolean check only)"}
    PlanSet -->|"Yes — plan is set"| ResolvePlan["sam_plan(config={'action':'list','search':'{slug}'})<br>Use returned plan address (full stem)<br>Do NOT pass item.plan directly to SAM"]
    PlanSet -->|"No — plan not set"| WorkItem["Clear context and run:<br>/dh:work-backlog-item {item.title}"]
    ResolvePlan --> ImplementFeature["Clear context and run:<br>/dh:implement-feature {plan_address}"]
    ImplementFeature --> Done([Handoff complete])
    WorkItem --> Done
    NothingQueued --> Done
```
