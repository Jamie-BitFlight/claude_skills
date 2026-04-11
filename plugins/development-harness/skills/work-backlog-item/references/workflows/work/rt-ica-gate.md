# RT-ICA Gate (Step 3.2)

## RT-ICA Staleness Policy

An RT-ICA result is stale and must be re-run if either condition is true: (a) the `Date:` header in the RT-ICA section is older than 7 calendar days, or (b) the item's `metadata.updated_at` field is newer than the RT-ICA section date. A stale RT-ICA result is treated as absent — `dh:rt-ica` is re-run before proceeding to [feasibility-gate.md](./feasibility-gate.md). The 7-day threshold applies regardless of whether the item description has changed, because codebase context may have changed even if the item text has not.

```mermaid
flowchart TD
    RCheck(["Step 3.2: RT-ICA Freshness Check"]) --> Get["Read backlog_view(selector=title, summary=false).sections['RT-ICA']"]
    Get --> Absent{"sections['RT-ICA'] key present and non-empty?"}
    Absent -->|"No"| RunRTICA(["Run dh:rt-ica — section absent"])
    Absent -->|"Yes"| ParseDate["Extract date using regex 'Date: YYYY-MM-DD' from section<br>If no match: try first ISO date in top 3 lines of section"]
    ParseDate --> DateFound{"ISO date parseable?"}
    DateFound -->|"No — date not found"| RunRTICA
    DateFound -->|"Yes — date D extracted"| Check1{"D older than 7 calendar days?"}
    Check1 -->|"Yes"| RunRTICA
    Check1 -->|"No — within 7 days"| Check2{"backlog_view metadata.updated_at present<br>AND metadata.updated_at greater than D?"}
    Check2 -->|"updated_at greater than D"| RunRTICA
    Check2 -->|"updated_at less than or equal to D OR field absent"| UseCache(["RT-ICA is fresh — use cached result"])
```

When the flowchart routes to "Run dh:rt-ica":

```text
Skill(skill: "dh:rt-ica", args: "{item_ref}")
```

Pass `{item_ref}` (the `#N` identifier) so the skill can load item context via `backlog_view`
before running — without it the skill returns BLOCKED immediately asking for context.

Log re-run reason: `RT-ICA re-run: {staleness reason — date older than 7 days / updated_at
newer than RT-ICA date}` to the item's RT-ICA section as a prefix before the new result.

- **Present and fresh** — use the APPROVED/BLOCKED decision from the cached result. Carry DERIVABLE items forward as "Assumptions to confirm" in the feature request.
- **BLOCKED** — stop. Do not proceed to [feasibility-gate.md](./feasibility-gate.md) until all MISSING conditions are resolved.
