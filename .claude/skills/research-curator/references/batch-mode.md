# Batch Mode Workflow

Processing multiple URLs in parallel via `--batch`.

---

## URL Parsing

Extract URLs from the `--batch` argument. Input format:

```text
/research-curator --batch https://url1.com https://url2.com https://url3.com
```

Parse all tokens after `--batch` that match `https?://` as target URLs. Non-URL tokens are ignored with a warning.

---

## Wave Spawning

The following diagram is the authoritative procedure for batch wave spawning. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Start(["Parse deduplicated URLs from --batch"]) --> Count{"How many URLs remain after duplicate check?"}
    Count -->|"1 to 5 — fits in one wave"| Wave1["Spawn all URLs as Wave 1<br>up to 5 parallel @research-curator agents via Agent tool"]
    Count -->|"6 to 10 — fits in two waves"| W1a["Spawn Wave 1 — first 5 URLs<br>up to 5 parallel @research-curator agents"]
    Count -->|"11 or more — requires three or more waves"| WNa["Spawn Wave 1 — URLs 1 through 5<br>up to 5 parallel @research-curator agents"]
    Wave1 --> Collect["Collect structured results from all agents<br>(status, file path, category, key findings)"]
    W1a --> W1aDone["Wait for all Wave 1 agents to complete"]
    W1aDone --> W2a["Spawn Wave 2 — remaining URLs<br>up to 5 parallel @research-curator agents"]
    W2a --> Collect
    WNa --> WNaDone["Wait for current wave to complete"]
    WNaDone --> QMore{"More URLs remaining?"}
    QMore -->|"Yes — advance to next batch of 5"| WNa
    QMore -->|"No — all URLs processed"| Collect
    Collect --> RelayCheck["Apply pre-relay quality checklist<br>to all collected agent results"]
    RelayCheck --> Gate["For each entry with status: succeeded<br>run the Validation Gate for New/Refreshed Entries<br>(validation-rules.md): fix_research_formatting.py<br>+ validate_research.py --json; on a gated warning<br>(header_fields/access_dates/freshness_tracking/url_format)<br>spawn @research-curator --fix and retry once"]
    Gate --> Results{"Per entry: did the curator agent fail,<br>or do errors / gated warnings remain<br>after the validation gate retry?"}
    Results -->|"No for an entry — clean"| SpawnAnalysis["For each clean entry (up to 5 entries concurrently)<br>spawn analysis agents per entry:<br>- @research-insight-extractor 'Extract improvements from {file-path}'<br>- @research-utilization-assessor 'Assess utilization opportunities from {file-path}'<br>- @research-cross-referencer 'Add cross-references to {file-path}'"]
    Results -->|"Yes for an entry — curator failure, or validation issues remain"| SpawnAnalysisPartial["Mark that entry failed or created with issues<br>Skip analysis agents for it<br>Relay the exact failure or issue text to user"]
    SpawnAnalysis --> UpdateAll["Update ./research/README.md<br>add all clean new entries to category tables<br>(concurrent with analysis agents)"]
    SpawnAnalysisPartial --> Partial["Update ./research/README.md<br>with clean entries only<br>(concurrent with analysis agents)"]
    UpdateAll --> WaitAnalysis["Wait for all analysis agents to complete<br>Collect IMMEDIATE_ATTENTION items from insight results<br>Collect PROPOSALS_WRITTEN counts from utilization results<br>Collect CROSS_REFERENCES_ADDED counts from cross-referencer results"]
    Partial --> WaitAnalysis
    WaitAnalysis --> NotifyUser["If any IMMEDIATE_ATTENTION items exist:<br>report each to user with issue number and reason<br>Otherwise: report total backlog items created count<br>Report total utilization proposals written<br>Report total cross-references added<br>Relay non-empty SKIPPED lists verbatim"]
    NotifyUser --> PostActions(["Execute Post-Actions — vault-wide backlink repair, then lint, commit, push (see SKILL.md for the authoritative step order)"])
```

**Wave size**: Maximum 5 concurrent @research-curator agents per wave.

**Sequential waves**: Wait for all agents in current wave to complete before spawning next wave. This prevents overwhelming MCP tool rate limits.

**Analysis phase concurrency**: After all curator waves complete, analysis agents spawn concurrently per entry: up to 5 entries, each spawning its own insight-extractor, utilization-assessor, and cross-referencer. This is distinct from the 5-agent curator wave limit.

**Validation gate**: Every entry a curator agent successfully wrote this wave passes through the [Validation Gate for New/Refreshed Entries](./validation-rules.md#validation-gate-for-newrefreshed-entries) before it is eligible for the analysis-agent fan-out. Error-severity issues, and warning-severity issues from `header_fields`, `access_dates`, `freshness_tracking`, or `url_format`, are must-fix — the researching agent already has the facts (today's date, the source URL, the version and access dates it just gathered), so a single `--fix` retry is spawned for gated warnings before an entry is marked "created with issues." `cross_references_absent` is not part of this gate.

---

## Error Handling

- **Individual failure**: Log the error, continue with remaining URLs. Do not abort the batch.
- **Agent timeout**: If an agent does not return within reasonable time, mark as failed and continue.
- **Duplicate detection**: see [Duplicate Detection](./duplicate-detection.md) — applied before spawning, per URL.

---

## Progress Reporting

After each wave completes, report:

```text
Wave N complete: M/N succeeded
  ✓ category/resource-name.md — created
  ✓ category/resource-name.md — created
  ✗ https://failed-url.com — error: [reason]
```

After all waves:

```text
Batch complete: X/Y total succeeded
Files created: [list]
README updated: Yes
Utilization proposals written: N files
Cross-references added: N entries updated
```

---

## Post-Batch Actions

These happen ONCE after all waves complete (not per-entry). This restates `SKILL.md`'s
Post-Actions section for Batch Mode; SKILL.md's numbered steps there are authoritative for exact
command invocations and ordering.

1. Update `./research/README.md` with all new entries
2. Repair the bidirectional cross-reference graph across the whole vault (`check-backlinks --fix`)
3. Run `uv run prek run --files` on the filtered list -- README, new entry files, and any files
   step 2 repaired
4. Commit all changes in a single commit
5. Push to current branch
