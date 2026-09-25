# Publication

One attempt starts only after start/continue bound authority, remote, destination ref, and initial OID.

1. Fetch the exact remote destination and compare its observed OID with the initially bound destination OID.
2. If it moved, inventory every new destination commit and assign each an evidence-backed disposition.
3. Integrate every compatible remote intent; route semantic conflicts through the router's combined-intent
   branch.
4. Reorient across direct overlaps and affected producers, consumers, interfaces, prompts, and documentation.
5. If reconciliation changes the result, bind its new committed OID as `R` and invalidate the earlier
   validation. Run the router's result-bound checks on the isolated committed tree of `R`, not restored or
   uncommitted work; then fetch again.
6. Push only when validation still applies to `R`, the result ref still resolves to `R`, the final destination
   OID equals the reconciled destination OID, and authority remains explicit. An unexpected result-ref change
   stops the attempt for a new decision; never replace the checked OID silently.
7. Use the full validated commit OID `R` as `<result-oid>` below. Tie the destination lease to its final
   observation; the lease protects the remote old value, not the local source or publication authority.

```bash
git push --force-with-lease=<destination-ref>:<observed-destination-oid> \
  <remote> <result-oid>:<destination-ref>
```

- A rejection or movement after one reconciliation/final observation stops external mutation and is reported.
- Another reconciliation/push attempt requires a new explicit decision and authority for that one attempt.
