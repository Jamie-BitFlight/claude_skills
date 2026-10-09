# GitHub MCP provider facts

Read when GitHub MCP is the available fallback, including cloud sandboxes without the preferred helper. Connected tool schemas supply invocation details.

- Submitted reviews and new review threads are inbound even when created by the authenticated account. A standalone comment introducing feedback is inbound; an authenticated top-level comment referencing an existing review is an outbound response candidate. Thread replies are also response candidates matched by their relationship and latest content.
- Review threads include resolved history; retrieve it when examining patterns or outstanding replies. Check pagination and disclose any unavailable surface.
- A response remains relevant across unrelated commits when its supporting evidence still holds. Revisit edited comments and materially changed implementation evidence.
- Confirm posted replies and thread resolution from provider observations. A successful reply followed by failed resolution remains communicated and unresolved.

## Observed MCP working path

These shortcuts come from handling PR #4107 through GitHub MCP:

- Fetch review threads, submitted reviews, and top-level PR comments together at intake; check pagination and retain stable references. Top-level comments may contain instructions from another agent.
- Classify by provider relationship, not account name: self-authored review submissions are inbound, while authenticated replies and comments referencing an existing finding may be outbound.
- Keep a compact view of outstanding findings and confirmed responses across calls. Refresh relevant provider state rather than repeatedly reassessing unchanged history.
- Continue from assessment through authorized fixes, verification, replies, and resolution. A review check that only reports findings leaves the requested work unfinished.
- Read affected compatibility tests alongside instruction changes, then run the relevant checks before resolving findings. Coalesce related edits into one reviewed revision when practical to avoid repeated review churn.
- Use combined provider actions when available; otherwise batch independent calls where safe, confirm replies, and resolve eligible threads. Preserve successful replies if a later resolution fails.

## Work the helper normally performs

When using MCP or another direct provider interface, the agent performs these cross-references itself:

- **Intake census:** Combine submitted reviews, thread roots and nested replies, top-level PR comments, approval signals, and resolved history. Inspect every returned page and retain stable IDs; thread resolution alone does not mean a finding was answered.
- **Direction and response matching:** Distinguish new inbound feedback (including self-authored reviews) from authenticated thread replies and top-level responses referencing existing findings. Compare response references and content with the latest input rather than treating every same-account comment as answered or unanswered.
- **Outstanding view:** Track each finding's disposition, verified fix or no-change evidence, observed response, and resolution independently. This substitutes for the helper's action summary and prevents losing the overview across individual MCP calls.
- **Mutation sequence:** Check current branch and relevant provider state, post the authorized response, confirm it, resolve where eligible, then confirm resolution. If a later step fails, retain earlier confirmed effects and resume only remaining work.
- **Recheck and watch:** Repeat collection of new, edited, unresponded, and unresolved items after actions. Use bounded repeated checks when monitoring; a quiet interval is an observation, not completion.

These are the additional responsibilities of direct tooling, not additional gates or a requirement to reproduce the helper's Python models. Provider tools' own schemas determine the calls.

The helper's GitHub classification implementation is in `scripts/pr_review_github_logic.py`; MCP uses provider observations directly under the [review outcome contract](./review-cycle-contract.md).
