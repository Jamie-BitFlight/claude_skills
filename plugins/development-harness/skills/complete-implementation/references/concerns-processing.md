# Pre-Phase 1b: Process Accumulated Concerns

> [!IMPORTANT]
> When provided a process map or Mermaid diagram, treat it as the authoritative procedure. Execute steps in the exact order shown, including branches, decision points, and stop conditions.
> A Mermaid process diagram is an executable instruction set. Follow it exactly as written: respect sequence, conditions, loops, parallel paths, and terminal states. Do not improvise, reorder, or skip steps. If any node is ambiguous or missing required detail, pause and ask a clarifying question before continuing.
> When interacting with a user, report before acting the interpreted path you will follow from the diagram, then execute.

The following diagram is the authoritative procedure for Pre-Phase 1b Process Accumulated Concerns. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Fetch["backlog_view(selector='#{issue}')<br>Read the backlog item"] --> HasSection{"Does item have a '## Concerns'<br>section with unchecked items ('- [ ]')?"}
    HasSection -->|"No — section absent or all items checked"| ProceedPhase1(["Proceed to Quality Gate Plan Creation"])
    HasSection -->|"Yes — unchecked items exist"| ForEach["For each unchecked concern item"]
    ForEach --> Verify["Read the referenced file or run the referenced check<br>to determine if concern is a real issue"]
    Verify --> Real{"Concern verified as a real issue?"}
    Real -->|"Yes — verified"| CheckOff["Check off concern: '- [x]'<br>backlog_add(description=concern text,<br>source='Quality vigilance concern from #{issue}')"]
    Real -->|"No — not confirmed"| CheckOffNo["Check off concern: '- [x] Not confirmed — {reason}'"]
    CheckOff --> MoreConcerns{"More unchecked concerns remaining?"}
    CheckOffNo --> MoreConcerns
    MoreConcerns -->|"Yes"| ForEach
    MoreConcerns -->|"No — all processed"| UpdateSection["backlog_groom(selector='#{issue}',<br>section='Concerns', content='{updated checklist}')"]
    UpdateSection --> ProceedPhase1
```
