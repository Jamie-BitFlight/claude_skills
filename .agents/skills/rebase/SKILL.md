---
name: rebase
description: Start a local Git rebase when the user explicitly requests replay of a named source ref onto a named target, or continue or abort an active rebase. Use only when local history replay will start or is active; do not use for merge-based branch updates, repository merge settings, pull-request or merge-request merging, or push-only requests.
---

**Keywords**: rebase, git rebase, history replay, rebase conflict, continue rebase, abort rebase, git worktree, rewritten history, authorized force-with-lease publication
```mermaid
flowchart TD
    Start([Explicit start, continue, or abort request]) --> Kind{Request?}
    Kind -->|Start| Bind[Binding stage]; Kind -->|Continue or abort| Active["Inspect lifecycle<br/>references/active-rebase-recovery.md"]
    Bind --> BindResult{Binding result?}
    BindResult -->|Dependent facts and completion predicate bound| Satisfied{Ordinary local relation observation?}; BindResult -->|Missing or ambiguous| Decision([Paused for decision]); BindResult -->|Failure or unobservable| Recover
    Satisfied -->|True; all result and publication destinations match| NoChange([No change]); Satisfied -->|False, transformation goal, or local result differs| Locate
    Satisfied -->|True; only publication destination differs| Locate; Satisfied -->|Failure or unobservable| Recover
    Active --> ActiveResult{Inspection result?}
    ActiveResult -->|No active metadata in worktree and Git dir| NoActive([No active rebase]); ActiveResult -->|Git state proven; dependent contract and predicate rebound| Locate
    ActiveResult -->|Required contract fact missing or inconsistent| Decision; ActiveResult -->|Failure or unobservable| Recover
    Locate[Source-location stage] --> Location{Exact source location?}
    Location -->|Owned local branch| Safe; Location -->|Unowned local branch| BranchWT[Create dedicated branch worktree]
    Location -->|Non-branch ref; result bound| DetachedWT[Create detached worktree at bound OID]; Location -->|Failure or unobservable| Recover
    BranchWT --> WTResult{Creation result?}; DetachedWT --> WTResult
    WTResult -->|HEAD OID equals source; branch attachment also matches when required| Safe; WTResult -->|Failure or unobservable| Recover
    Safe[Worker-safety stage] --> Owner{Worktree-writing command state?}
    Owner -->|None, or pause/end observed| Operation{Operation?}; Owner -->|Observed active| Wait[Wait for checkpoint predicate]; Wait --> Owner
    Owner -->|Unknown or unreachable| Decision
    Operation -->|Start| Prepare[Preparation stage]; Operation -->|Continue| Stop{Current rebase state?}
    Operation -->|Abort| Abort["Abort and restore pre-state<br/>references/active-rebase-recovery.md"]
    Prepare --> PrepResult{Preparation result?}
    PrepResult -->|Status empty, or checkpoint contains all changes and status is empty| Refs; PrepResult -->|Dirty and checkpoint commit blocked| Save["Save and bind exact entry<br/>references/named-stash.md"]
    PrepResult -->|Failure or unobservable| Recover
    Save --> SaveResult{Exact entry verified?}
    SaveResult -->|Yes| Refs
    SaveResult -->|No or unobservable| Recover
    Refs[Reobserve exact source and target] --> RefResult{Ref result?}
    RefResult -->|Bound OIDs unchanged| Next; RefResult -->|Same named refs moved| Account[Account for movement]
    RefResult -->|Failure or unobservable| Recover
    Account --> AccountResult{Moved-commit dispositions complete?}
    AccountResult -->|All classified; no supported conflict| Next; AccountResult -->|Unclassified or conflicting| Decision
    AccountResult -->|Failure or unobservable| Recover
    Next{Reobserved local path?} -->|Replay required| Shape; Next -->|No-replay publication; predicate true| Current[Bind proven current result OID R]
    Next -->|Failure or unobservable| Recover
    Current --> CurrentResult{Named result ref resolves to R?}
    CurrentResult -->|Yes| Saved; CurrentResult -->|No or unobservable| Recover
    Shape{Merge in replay set or Git reports empty/equivalent?} -->|Yes| History["Resolve topology/equivalence<br/>references/history-shape.md"]; Shape -->|No| Replay[Run ordinary Git replay]
    Shape -->|Failure or unobservable| Recover
    History --> HistoryResult{Every special commit has a supported disposition?}
    HistoryResult -->|Yes; no supported conflict| Replay; HistoryResult -->|No or conflicting| Decision
    HistoryResult -->|Failure or unobservable| Recover
    Stop -->|Unmerged index entries| ReplayConflict
    Stop -->|Git reports topology, equivalent, or empty| History
    Stop -->|Metadata active; no unmerged entries; required resolution staged| Replay
    Stop -->|Other failure or unobservable| Recover
    Replay --> ReplayResult{Replay result?}
    ReplayResult -->|Metadata/unmerged absent; observed R bound; result ref resolves to R; predicate true| Saved{Lifecycle saved entry?}
    ReplayResult -->|Unmerged index entries| ReplayConflict["Resolve replay intent<br/>references/conflict-and-ambiguity.md"]
    ReplayResult -->|Topology, equivalent, or empty| History
    ReplayResult -->|Other failure or unobservable| Recover
    ReplayConflict --> ReplayIntent{One semantic outcome class preserves compatible intent and checks?}
    ReplayIntent -->|Exactly one| Replay; ReplayIntent -->|None or incompatible alternatives| Decision
    ReplayIntent -->|Failure or unobservable| Recover
    Abort --> AbortResult{Abort restoration predicate?}
    AbortResult -->|Metadata/unmerged absent; source or HEAD equals pre-replay OID| Saved
    AbortResult -->|Failure or unobservable| Recover
    Saved -->|Verified none| FinishMode{Lifecycle outcome?}; Saved -->|Exact entry bound| Restore["Restore and remove exact entry<br/>references/named-stash.md"]
    Saved -->|Ambiguous or unobservable| Recover
    Restore --> RestoreResult{Restoration result?}
    RestoreResult -->|Command zero; no unmerged entries; exact entry absent| FinishMode
    RestoreResult -->|Conflict; entry preserved| RestoreConflict["Resolve restoration intent<br/>references/conflict-and-ambiguity.md"]
    RestoreResult -->|Other failure or unobservable| Recover
    RestoreConflict --> RestoreIntent{One semantic outcome class preserves compatible intent and checks?}
    RestoreIntent -->|Exactly one| Restore; RestoreIntent -->|None or incompatible alternatives| Decision
    RestoreIntent -->|Failure or unobservable| Recover
    FinishMode -->|Explicit abort request| OrientAbort[Abort reorientation]; FinishMode -->|Completed start or continue| Orient[Reorientation and verification]
    Orient --> VerifyResult{Selected validation set result?}
    VerifyResult -->|All checks zero; no unmerged entries; intersections accounted| Publish{Publication bound and authorized?}
    VerifyResult -->|Failing check identifies one goal-consistent correction| Correct[Correct changed interaction]
    Correct --> CorrectResult{Correction applied?}
    CorrectResult -->|Yes; rerun full selected set| Orient; CorrectResult -->|Failure or unobservable| Recover
    VerifyResult -->|Missing intent or incompatible corrections| Decision
    VerifyResult -->|Failure or unobservable| Recover
    Publish -->|No| Handoff
    Publish -->|Yes| Remote["Reconcile destination<br/>references/publication.md"]
    Remote --> RemoteResult{Remote stage result?}
    RemoteResult -->|Final fetch unchanged; exact lease OID current| Push[Authorized exact-lease push]
    RemoteResult -->|Every moved commit disposed; interactions validated| Orient
    RemoteResult -->|Conflict| RemoteConflict["Resolve remote intent<br/>references/conflict-and-ambiguity.md"]
    RemoteResult -->|Failure or unobservable| Recover
    RemoteConflict --> RemoteIntent{One semantic outcome class preserves compatible intent and checks?}
    RemoteIntent -->|Exactly one| Remote; RemoteIntent -->|None or incompatible alternatives| Decision
    RemoteIntent -->|Failure or unobservable| Recover
    Push --> PushResult{Push result?}
    PushResult -->|Exit zero and post-fetch destination equals result| Handoff; PushResult -->|Lease rejected or destination mismatch| Remote
    PushResult -->|Other failure or unobservable| Recover
    OrientAbort --> Handoff[Worker-handoff stage]
    Handoff --> Worker{Worker exists?}
    Worker -->|Yes| Deliver[Deliver summary and resume]; Worker -->|No| Terminal{Bound path predicate?}
    Worker -->|Unknown or unobservable| Recover
    Deliver --> HandoffResult{Delivery acknowledged or worker resumed with summary?}
    HandoffResult -->|Yes| Terminal; HandoffResult -->|No or unobservable| Recover
    Terminal -->|Abort request and restored pre-state| Aborted([Aborted and restored])
    Terminal -->|Completed start/continue; post-push destination resolves to R| Published([Published completion])
    Terminal -->|Completed start/continue; result ref resolves to R; predicate true; no publication| Local([Local completion])
    Terminal -->|Inconsistent or unobservable| Recover
    Recover["Stop mutations and collect report fields<br/>references/active-rebase-recovery.md"] --> Stopped([Stopped with observed state])
```
