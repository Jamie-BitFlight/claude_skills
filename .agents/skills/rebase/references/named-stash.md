# Named stash

## Bind an entry

1. Create the save with untracked work and message `rebase:<source-ref>:<pre-replay-source-oid>`.
2. Resolve its stash commit OID and bind Git's exact subject; require the subject to end with that lifecycle token.
3. List stashes by commit OID, selector, and subject; require exactly one match for the OID and bound subject.
4. Route a failed observation to recovery. Pause when the new entry is absent, duplicated, or unprovable.

```bash
git stash push --include-untracked -m "rebase:<source-ref>:<pre-replay-source-oid>"
git rev-parse --verify stash@{0}^{commit}
git stash list --format='%H %gd %s'
```

## Apply the bound entry

1. Before continue or abort, re-list entries: verified zero binds none; one exact OID/subject match binds it.
2. Pause on multiple or unprovable matches. Route failed observation to recovery before mutation.
3. For one bound entry, apply its immutable OID and keep the entry while conflicts or checks remain.
4. On conflict, resolve through the router and proceed to finalization without applying the stash again.

## Finalize a conflict-free or resolved apply

1. Verify the resolved tree, repository-required checks, and checks for changed producers/consumers/interfaces.
2. Re-list and require the same unique OID/subject match, then drop only its current selector.
3. Re-list again and require that exact OID-and-subject pair to be absent.

```bash
git stash apply <stash-commit-oid>
git stash list --format='%H %gd %s'
git stash drop <matched-stash-selector>
```
