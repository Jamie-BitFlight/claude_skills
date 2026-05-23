# Work: Validate (Phase 2)

Verify item state, sync issue link, and run discovery gate.

## Step 2.1: Already Implemented Check

Before planning, verify the feature/fix hasn't already been implemented (stale open item). Load [already-implemented.md](./already-implemented.md) for git commands, resolve calls, and behavior when <mode/> is `auto`.

## Step 2.2: Issue Link Check

After Step 1.4, check for `**Issue**: #N` in the matched item. Load [github-sync.md](./github-sync.md) for MCP tool calls, yes/no branching, and issue creation.

**Note:** On the Issue-first path (Step 1.2), the `backlog_view` response already contains issue state — carry it forward without re-fetching.

## Step 2.3: Create Linked Issue

Load [github-sync.md](./github-sync.md#step-23-create-linked-issue).

## Step 2.4: Set In-Progress

Load [github-sync.md](./github-sync.md#step-24-set-in-progress).

**Two-part step:** (a) Always run `mcp__plugin_dh_backlog__backlog_update` with `status="in-progress"` for the current item. (b) Run `milestone start` only on explicit user intent to start the whole milestone — it bulk-transitions all open milestone issues, not just the current one.

## Step 2.5: Discovery Gate

Before grooming or planning, check whether a structured discovery artifact exists.

```mermaid
flowchart TD
    InProgress([Step 2.4 complete — status set]) --> HasIssue{"Item has linked<br>issue number?"}
    HasIssue -->|"No"| SkipGate["Skip discovery gate<br>Proceed to Step 3.1"]
    HasIssue -->|"Yes — issue #{N}"| TypeCheck{"Labels include<br>'type:fix' or 'type:bug'?"}
    TypeCheck -->|"Yes — fix/bug type"| SkipGate
    TypeCheck -->|"No — feature/refactor/other"| CheckArtifact["artifact_list(<br>item_id={N},<br>artifact_type='feature-context')"]
    CheckArtifact --> HasDiscovery{"count > 0?"}
    HasDiscovery -->|"Yes"| Proceed["Discovery exists<br>Proceed to Step 3.1"]
    HasDiscovery -->|"No"| InvokeDiscovery["Invoke: Skill(skill='dh:discovery')"]
    InvokeDiscovery --> VerifyDiscovery["Call artifact_list(<br>item_id={N},<br>artifact_type='feature-context')"]
    VerifyDiscovery --> DiscoveryConfirmed{"count > 0?"}
    DiscoveryConfirmed -->|"Yes — artifact registered"| Continue
    DiscoveryConfirmed -->|"No — retry once"| RetryDiscovery["Re-invoke: Skill(skill='dh:discovery')<br>(max 1 retry)"]
    RetryDiscovery --> VerifyRetry["Call artifact_list(<br>item_id={N},<br>artifact_type='feature-context')"]
    VerifyRetry --> RetryConfirmed{"count > 0?"}
    RetryConfirmed -->|"Yes"| Continue
    RetryConfirmed -->|"No — still 0 after retry"| DiscoveryFail(["STOP — report to user:<br>dh:discovery completed but no feature-context<br>artifact was registered for issue #{N}.<br>Re-run /dh:discovery manually and retry."])
    SkipGate --> Continue([Step 3.1 — Auto-Groom])
    Proceed --> Continue
```

The discovery skill gathers WHO/WHAT/WHEN/WHY requirements and registers the result as a
`feature-context` artifact. The exit signal is a non-zero count from
`artifact_list(item_id={N}, artifact_type='feature-context')`.

**When <mode/> is `auto`**: After `dh:discovery` returns, do NOT yield to the user. Immediately
call `artifact_list` to verify the artifact was registered, then proceed to Step 3.1 without
presenting a summary or asking for confirmation. The `dh:discovery` skill skips its user
confirmation gate when <mode/> is `auto` — no additional acknowledgment is needed.

**Interactive mode**: `dh:discovery` presents the ARTIFACT:DISCOVERY summary and requests user
confirmation before completing. After user confirmation, Step 3.1 (Auto-Groom) will detect the
artifact and pass it to the grooming swarm.
