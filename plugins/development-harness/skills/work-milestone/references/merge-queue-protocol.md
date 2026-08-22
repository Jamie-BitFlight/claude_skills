# Merge Queue Protocol

> **Signaling model**: Completion signaling is via Agent call return. Agents are synchronous
> from the orchestrator's perspective — the Agent tool call blocks until the agent finishes.
> The orchestrator merges worktree branches sequentially after all wave agents return.
> Workers do not exist between waves — each wave spawns fresh worktree agents that terminate on completion.

The orchestrator owns the merge slot. Only one merge proceeds at a time. Agents return when complete; the orchestrator processes returns sequentially.

## Merge Slot Lifecycle

```mermaid
flowchart TD
    Signal(["Agent returns with completion report"]) --> Queue["Add to merge queue<br>(ordered by return time)"]
    Queue --> Slot{"Merge slot free?"}
    Slot -->|"Busy — another merge in progress"| Wait["Queue this completion.<br>Continue processing<br>other agent returns."]
    Wait --> Slot
    Slot -->|"Free — acquire slot"| PreVerify

    PreVerify{"Pre-Verification Check<br>Agent's base commit matches<br>current integration branch HEAD?"}
    PreVerify -->|"Matches — skip re-test"| AttemptMerge
    PreVerify -->|"Diverged — rebase and run gates"| RunGates

    RunGates["Rebase worktree branch onto<br>integration branch HEAD.<br>Run quality gate commands<br>from dispatch plan pre_merge list."]
    RunGates --> GatesResult{"Gates pass?"}
    GatesResult -->|"All pass"| AttemptMerge
    GatesResult -->|"Any fail"| GateFail["Orchestrator spawns fix agent<br>in worktree on integration branch.<br>Fix agent resolves gate failures.<br>Release merge slot."]
    GateFail --> Wait

    AttemptMerge["Squash merge worktree branch<br>into integration branch.<br>Commit message: conventional commit<br>with item title and issue number."]
    AttemptMerge --> MergeResult{"Merge result?"}

    MergeResult -->|"Clean"| Success["Push integration branch.<br>Update item status via backlog MCP.<br>Release merge slot.<br>Clean up worktree branch."]

    MergeResult -->|"1-2 files conflicting"| Classify["Classify conflict severity"]
    Classify --> Severity{"Conflict type"}

    Severity -->|"Trivial — whitespace,<br>import order, adjacent additions"| AutoResolve["Auto-resolve.<br>Run quality gates after resolve."]
    Severity -->|"Medium — same function<br>edited differently"| AutoResolve
    AutoResolve --> AutoResult{"Resolve succeeded?"}
    AutoResult -->|"Yes"| Success
    AutoResult -->|"No"| AssignBack

    Severity -->|"Heavy — file refactored<br>by multiple worktrees"| AssignBack
    MergeResult -->|"3+ files conflicting"| AssignBack

    AssignBack["Abort merge.<br>Create backlog item for conflict resolution.<br>Add to current milestone for next wave.<br>Report to user: conflicting files, both agents' approaches.<br>Release merge slot."]
    AssignBack --> Done(["Slot released"])
    Success --> Done
```

## Conflict Severity Classification

```mermaid
flowchart TD
    Conflict(["Merge conflict detected"]) --> Count{"How many files<br>have conflicts?"}

    Count -->|"0 files — clean merge"| Clean(["No conflict — proceed"])

    Count -->|"1-2 files"| Severity{"Conflict type?<br>Observable: git diff<br>conflict markers"}

    Severity -->|"Whitespace, import order,<br>adjacent-line additions"| Trivial["TRIVIAL — auto-resolve"]
    Severity -->|"Same function/block<br>edited differently"| Medium["MEDIUM — spawn conflict-resolution agent<br>in worktree on integration branch"]
    Severity -->|"File restructured or<br>refactored differently<br>by both worktrees"| Heavy["HEAVY — assign_back<br>Create backlog item for design review"]

    Count -->|"3+ files"| Heavy

    Trivial --> AutoResolve(["Orchestrator resolves<br>and runs gates"])
    Medium --> AutoResolve
    Heavy --> BacklogItem(["Abort merge.<br>Create backlog item + add to milestone."])
```

## Assign Back Details

When a heavy conflict triggers assign_back:

1. Abort the in-progress merge: `git merge --abort`
2. Do NOT push the worktree branch — branches are local-only, never pushed to origin
3. Create a backlog item for the conflict resolution task:
   - Title: `Resolve merge conflict: {item A title} vs {item B title}`
   - Body: conflicting files list, both agents' approaches (from their completion reports), worktree branch names for reference
   - Label: `conflict-resolution`
   - Assign to current milestone
4. Report to user: conflict resolution backlog item link, conflict file list
5. Release merge slot

The resolution backlog item is added to the current milestone and dispatched in the next wave like any other item. The orchestrator assigns it a worktree agent with the conflicting diffs embedded in the prompt. The agent can make a design decision and implement a clean merge.

> No PR is created (branches are local-only). No mid-flight agent notification is possible — agents have already terminated before merging begins. Conflict resolution becomes a new backlog item dispatched in the next wave.

## Quality Gate Commands

Gate commands are defined in the dispatch plan under `quality_gates`:

```yaml
quality_gates:
  pre_merge:
    - "uv run prek run --all-files"
    - "uv run ruff check ."
  post_merge:
    - "uv run pytest tests/ -x"
```

`pre_merge` gates run before each individual item merge. `post_merge` gates run once on the full integration branch before landing to main.

A gate failure on an individual merge causes the orchestrator to spawn a fix agent in a worktree on the integration branch. The fix agent resolves the failures and the merge retries.

A `post_merge` failure on the integration branch triggers a specialist agent delegation in a worktree on the integration branch. The orchestrator does not attempt self-repair.

## Integration Branch Landing

After all waves complete:

1. Run full `pre_merge` + `post_merge` gate suite on integration branch
2. If any gate fails: delegate fix to specialist agent in worktree on integration branch, re-run gates
3. If all gates pass:

```bash
git switch main
git merge --no-ff milestone/{N}-{slug}
git push origin main
```

4. Delete integration branch: `git push origin --delete milestone/{N}-{slug}`
5. Invoke `/complete-milestone {N}`
