# Final Handoff Output

> [!IMPORTANT]
> When provided a process map or Mermaid diagram, treat it as the authoritative procedure. Execute steps in the exact order shown, including branches, decision points, and stop conditions.
> A Mermaid process diagram is an executable instruction set. Follow it exactly as written: respect sequence, conditions, loops, parallel paths, and terminal states. Do not improvise, reorder, or skip steps. If any node is ambiguous or missing required detail, pause and ask a clarifying question before continuing.
> When interacting with a user, report before acting the interpreted path you will follow from the diagram, then execute.

The following diagram is the authoritative procedure for Final Handoff Output. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    %% The filter is mandatory — do NOT substitute a general P1/P2 listing already in context
    Fetch["backlog_list(title='{slug}')<br>Slug-filtered search — mandatory, not substitutable"] --> ItemFound{"First result returned<br>(item found)?"}
    ItemFound -->|"No — zero results"| NothingQueued["Clear context and run:<br>/dh:work-backlog-item — nothing queued —"]
    ItemFound -->|"Yes"| PlanSet{"item.plan set and non-empty?<br>(boolean check only)"}
    PlanSet -->|"Yes — plan is set"| ResolvePlan["sam_list(search='{slug}')<br>Use returned plan address P{id}<br>Do NOT pass item.plan directly to SAM"]
    PlanSet -->|"No — plan not set"| WorkItem["Clear context and run:<br>/dh:work-backlog-item {item.title}"]
    ResolvePlan --> ImplementFeature["Clear context and run:<br>/dh:implement-feature P{id}"]
    ImplementFeature --> Done([Handoff complete])
    WorkItem --> Done
    NothingQueued --> Done
```
