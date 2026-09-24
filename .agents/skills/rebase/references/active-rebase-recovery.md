# Active rebase recovery

## Rediscover the lifecycle

1. Find the exact worktree and Git dir containing active metadata; bind both and remain there.
2. Observe their metadata, `HEAD`, named refs, unmerged entries, status, and replay progress.
3. For continue, rebind target name, goal, completion predicate, result and publication destinations, authority,
   saved-entry identity, and worker facts required by the remaining path.
4. For abort, rebind only the pre-replay restoration state, saved-entry identity, and required worker facts.
5. Compare rebound names with recorded or observable OIDs. Pause before any mutation needing an absent or
   inconsistent fact.
6. Immediately before continue or abort, reobserve the same worktree/Git-dir metadata and bound saved entry.
7. Use current Git state plus current request and task context. Promise recovery only for facts now observable or
   explicitly rebound, and keep lifecycle state in Git rather than a new lifecycle file.

## Stop with observed state

1. Stop coordinator-issued mutations and preserve the active rebase, conflicts, and bound saved entry.
2. Report the failed command with exit status and complete output.
3. Report every resolvable `HEAD`, source, target, result, and destination ref with its OID.
4. Report active rebase metadata, stopped commit and progress, unmerged entries, and worktree status.
5. Report whether the exact bound saved entry is present, absent, ambiguous, or unobservable.
6. Report every failed observation and the fact it prevented proving. Retry only through the router's gate.
