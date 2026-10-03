# Publication

Start/continue binds authority, remote, destination ref, and initial destination OID. A rebase request
authorizes the exact-lease push of `R` to the rebased branch's own remote destination. Any other
destination or force-push needs explicit authority.

## Remote sync

Run before replay and again before each push attempt.

1. Fetch the exact remote destination and compare its observed OID with the bound destination OID.
2. If it moved, inventory every new destination commit and assign each an evidence-backed disposition.
3. Integrate every compatible remote intent; route semantic conflicts through the router's combined-intent
   branch.
4. Reorient across direct overlaps and affected producers, consumers, interfaces, prompts, and documentation.
5. Rebind the destination OID to the observed value. Before replay, integrate into the source, then rebind
   the source OID and replay onto the target.

## Push attempt

1. Run Remote sync.
2. If reconciliation changes the result, bind its new committed OID as `R` and invalidate the earlier
   validation. Run the router's result-bound checks on the isolated committed tree of `R`, not restored or
   uncommitted work; then fetch again.
3. Push only when validation still applies to `R`, the result ref still resolves to `R`, the final destination
   OID equals the reconciled destination OID, and authority remains explicit. An unexpected result-ref change
   stops the attempt for a new decision; never replace the checked OID silently.
4. Use the full validated commit OID `R` as `<result-oid>` below. Tie the destination lease to its final
   observation; the lease protects the remote old value, not the local source or publication authority.

```bash
git push --force-with-lease=<destination-ref>:<observed-destination-oid> \
  <remote> <result-oid>:<destination-ref>
```

## Retry

- A destination that moved at final observation or a rejected lease starts another attempt: fetch, integrate
  per Remote sync, revalidate, push.
- Cap: 3 attempts per publication. At the cap, stop external mutation and report each attempt, the
  rejection, and the destination OIDs observed.
- Stop earlier, without retrying, when an unresolved semantic conflict, an unclassified remote commit, or an
  unexpected result-ref change appears.
