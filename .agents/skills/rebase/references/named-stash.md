# Named stash

## Bind an entry

1. Create the save with untracked work and message `rebase:<source-ref>:<pre-replay-source-oid>`.
2. Resolve the new stash commit OID and require its message to equal that lifecycle message.
3. List stashes by commit OID, selector, and subject; require exactly one match for both OID and message.
4. Route a failed observation to recovery. Pause when the new entry is absent, duplicated, or unprovable.

```bash
git stash push --include-untracked -m "rebase:<source-ref>:<pre-replay-source-oid>"
git rev-parse --verify stash@{0}^{commit}
git stash list --format='%H %gd %s'
```

## Restore the bound entry

1. Before continue or abort, re-list entries: verified zero binds none; one exact OID/message match binds it.
2. Pause on multiple or unprovable matches. Route failed observation to recovery before mutation.
3. For one bound entry, apply its immutable OID and keep the entry while conflicts or checks remain.
4. Resolve conflicts through the router's combined-intent branch, then rerun affected checks.
5. Reorient to every changed producer, consumer, interface, prompt, and document before resuming work.
6. After a conflict-free apply, re-list and require the same unique match, then drop only its selector.
7. Re-list again and require that exact OID-and-message pair to be absent.

```bash
git stash apply <stash-commit-oid>
git stash list --format='%H %gd %s'
git stash drop <matched-stash-selector>
```
