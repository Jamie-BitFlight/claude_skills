# GitHub MCP fallback

Use this branch only when the bundled CLI cannot use `gh` and a GitHub MCP connector is available.
The shared review-cycle contract remains authoritative. Use the connector for the entire snapshot;
fresh and stale partial results never form one snapshot.

## Complete equivalent snapshot

Collect PR identity and exact head revision, every page of review threads and nested comments, every
submitted review, PR-level comments, reactions, force-push timeline events, and authenticated actor
identity. Preserve resolved history. Missing fields, pagination gaps, permission failures, rate limits,
or partial concurrent results produce `SNAPSHOT_INCOMPLETE` or `ERROR`, never an empty or clean state.

Normalize the collected objects into the same models used by `fetch`. Required counts and blocker
state derive from the complete normalized snapshot, not from a single endpoint. A response to a
top-level review counts only when the authenticated actor's later PR comment quotes that review's
exact stable permalink; unavailable permalinks or effective timestamps are errors.

## GitHub Codex input

Retain the bundled GitHub adapter's exact bot-identity, no-findings-wrapper, and current-revision
rules. A Codex `+1` is current only when its observed timestamp is not older than the later of the
head commit timestamp and latest force-push event. The reaction is an approval input in the census;
it requires assessment and communication like every other input. Its presence neither completes nor
blocks an otherwise fully processed cycle.

## Authorized actions

After the shared validation and authority gates pass:

- reply to an inline thread through its opening comment target;
- resolve it through its thread target only after communication succeeds;
- answer a top-level review through a PR comment containing its exact permalink.

Use the connector operation with equivalent semantics if its prefix differs. Scope every operation to
the bound repository and PR. Re-fetch through MCP before the first mutation and reject changed target,
revision, fingerprint, or input state. Apply the shared reply-before-resolve, clarification, recovery,
and partial-failure rules.

For rechecks and bounded watch samples, repeat the same complete MCP collection. Any canonical change
returns to the full census. Completion still comes only from the shared terminal contract, never from
an approval or elapsed sample alone.
