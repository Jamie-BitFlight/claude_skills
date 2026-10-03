# Publication

Start binds authority, remote, destination ref, and the bound destination OID; continue keeps them. A start
request authorizes the exact-lease push of `R` to the rebased branch's own remote destination unless its
wording is local-only. Any other destination or force-push needs explicit authority.

## Pre-replay sync

Run after the start refs are reobserved, before replay.

1. Fetch the exact remote destination and compare its observed OID with the bound destination OID.
2. If it moved, inventory every new destination commit and assign each an evidence-backed disposition.
3. Integrate every compatible remote intent into the source: fast-forward when the source is an ancestor of
   the destination; otherwise replay the source-only commits onto the destination tip. Never create a merge
   commit. Route semantic conflicts through the router's combined-intent branch.
4. Reorient across direct overlaps and affected producers, consumers, interfaces, prompts, and documentation.
5. Rebind the source OID and the bound destination OID to the observed values, then replay onto the target.

## Push attempts

An attempt is one pass through steps 1-4, whether or not it reaches the push command. A re-entry after
conflict resolution is a new attempt.

1. Fetch the destination and compare its observed OID with the bound destination OID. If it moved, run
   Pre-replay sync steps 2-4 against the result `R`, then rebind the bound destination OID.
2. If reconciliation changes the result, bind its new committed OID as `R` and invalidate the earlier
   validation. Run the router's result-bound checks on the isolated committed tree of `R`, not restored or
   uncommitted work; then fetch again.
3. Push only when validation still applies to `R`, the result ref still resolves to `R`, the final destination
   OID equals the bound destination OID, and authority remains bound. An unexpected result-ref change
   stops the attempt for a new decision; never replace the checked OID silently.
4. Use the full validated commit OID `R` as `<result-oid>` below. Tie the destination lease to its final
   observation; the lease protects the remote old value, not the local source or publication authority.

```bash
git push --force-with-lease=<destination-ref>:<observed-destination-oid> \
  <remote> <result-oid>:<destination-ref>
```

## Retry

- A destination that moved at final observation, a rejected lease, or a resolved conflict starts the next
  attempt.
- Cap: 3 attempts per publication. At the cap, stop external mutation and report each attempt, its rejection
  or movement, and the destination OIDs observed.
- Stop earlier, without retrying, when an unresolved semantic conflict, an unclassified remote commit, or an
  unexpected result-ref change appears.
