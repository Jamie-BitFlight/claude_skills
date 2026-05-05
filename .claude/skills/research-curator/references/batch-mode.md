# Batch Mode Workflow

Processing multiple URLs in parallel via `--batch`.

---

## Layer Filter

When `--layer 0|1|2` is also present, apply the layer filter to scope category selection. Pass the layer value to each `@research-curator` agent as context so it classifies entries within the appropriate SDLC layer.

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
    RelayCheck --> Results{"Did any agent return status: failed?"}
    Results -->|"No — all succeeded"| SpawnAnalysis["For each successful entry (up to 5 entries concurrently)<br>spawn 3 agents per entry:<br>- @research-insight-extractor 'Extract improvements from {file-path}'<br>- @research-utilization-assessor 'Assess utilization opportunities from {file-path}'<br>- @research-cross-referencer 'Add cross-references to {file-path}'"]
    Results -->|"Yes — one or more failed"| SpawnAnalysisPartial["For each successful entry only (up to 5 concurrently)<br>spawn 3 agents per entry:<br>- @research-insight-extractor<br>- @research-utilization-assessor<br>- @research-cross-referencer<br>Relay each failure with exact reason to user"]
    SpawnAnalysis --> UpdateAll["Update ./research/README.md<br>add all new entries to category tables<br>(concurrent with analysis agents)"]
    SpawnAnalysisPartial --> Partial["Update ./research/README.md<br>with successful entries only<br>(concurrent with analysis agents)"]
    UpdateAll --> WaitAnalysis["Wait for all analysis agents to complete<br>Collect IMMEDIATE_ATTENTION items from insight results<br>Collect PROPOSALS_WRITTEN counts from utilization results<br>Collect CROSS_REFERENCES_ADDED counts from cross-referencer results"]
    Partial --> WaitAnalysis
    WaitAnalysis --> BacklinkPass["For each successful entry in sequence (one at a time):<br>spawn @research-backlink-detector<br>'Add backlinks for {file-path}'<br>wait for completion before spawning next<br>(sequential to prevent write races on shared cited entries)"]
    BacklinkPass --> NotifyUser["If any IMMEDIATE_ATTENTION items exist:<br>report each to user with issue number and reason<br>Otherwise: report total backlog items created count<br>Report total utilization proposals written<br>Report total cross-references added<br>Report total BACKLINKS_ADDED count<br>Relay non-empty SKIPPED lists verbatim"]
    NotifyUser --> PostActions(["Execute Post-Actions — lint, commit, push"])
```

**Wave size**: Maximum 5 concurrent @research-curator agents per wave.

**Sequential waves**: Wait for all agents in current wave to complete before spawning next wave. This prevents overwhelming MCP tool rate limits.

**Analysis phase concurrency**: After all curator waves complete, analysis agents spawn concurrently per entry: up to 5 entries × 3 agents (insight-extractor + utilization-assessor + cross-referencer) = maximum 15 concurrent agents. This is distinct from the 5-agent curator wave limit.

**Backlink phase serialization**: After all analysis agents complete, backlink-detector agents run **sequentially** — one entry at a time. Concurrent backlink passes on multiple entries that cite a shared target file would produce a write race (each agent reads a stale snapshot and the last writer drops the other's row). Sequential execution prevents this.

---

## Error Handling

- **Individual failure**: Log the error, continue with remaining URLs. Do not abort the batch.
- **Agent timeout**: If an agent does not return within reasonable time, mark as failed and continue.
- **Duplicate detection**: Before spawning, check if `./research/` already contains an entry for the URL's resource. If found, skip with info message suggesting `--rerun` instead.

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
Backlinks added: N rows across M entries
Backlink skipped: [(path, reason), ...] (omitted when empty)
```

---

## Post-Batch Actions

These happen ONCE after all waves complete (not per-entry):

1. Update `./research/README.md` with all new entries
2. Run `uv run prek run --files` on README and all new entry files
3. Commit all changes in a single commit
4. Push to current branch
