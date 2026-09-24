# Publication

One attempt starts only after start/continue bound authority, remote, destination ref, and initial OID.

1. Fetch the exact remote destination and compare its observed OID with the initially bound destination OID.
2. If it moved, inventory every new destination commit and assign each an evidence-backed disposition.
3. Integrate every compatible remote intent; route semantic conflicts through the router's combined-intent branch.
4. Reorient across direct overlaps and affected producers, consumers, interfaces, prompts, and documentation.
5. Rerun the full selected validation set, then fetch and observe the exact destination again.
6. Push only when that final OID still equals the reconciled destination OID and authority remains explicit.
7. Tie the lease to that final observation; lease syntax supplies safety, never publication authority.

```bash
git push --force-with-lease=<destination-ref>:<observed-destination-oid> \
  <remote> <result-ref>:<destination-ref>
```

- A rejection or movement after one reconciliation/final observation stops external mutation and is reported.
- Another reconciliation/push attempt requires a new explicit decision and authority for that one attempt.
