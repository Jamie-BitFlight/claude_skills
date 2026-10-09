# GitHub MCP provider facts

Read when GitHub MCP is the available fallback, including cloud sandboxes without the preferred helper. Connected tool schemas supply invocation details.

- Submitted reviews and new review threads are inbound even when created by the authenticated account. A standalone comment introducing feedback is inbound; an authenticated top-level comment referencing an existing review is an outbound response candidate. Thread replies are also response candidates matched by their relationship and latest content.
- Review threads include resolved history; retrieve it when examining patterns or outstanding replies. Check pagination and disclose any unavailable surface.
- A response remains relevant across unrelated commits when its supporting evidence still holds. Revisit edited comments and materially changed implementation evidence.
- Confirm posted replies and thread resolution from provider observations. A successful reply followed by failed resolution remains communicated and unresolved.

## Observed cloud-session lessons

In PR #4107, direct MCP successfully retrieved review threads, submitted reviews, and top-level comments; posted evidence-backed replies; resolved threads; and rechecked open work. The failures were procedural: an initial check stopped without implementing authorized fixes, self-authored feedback was initially mistaken for the human user's instruction, top-level same-account replies needed distinct classification from new feedback, and compatibility assertions were repeatedly missed after editing the skill. Keep the review cycle moving through verified changes and responses, classify by provider relationship rather than account name, and verify affected tests before resolving findings. This is observed-use evidence, not a substitute for checking current provider state.

## Work the helper normally performs

When using MCP or another direct provider interface, the agent performs these cross-references itself:

- **Intake census:** Combine submitted reviews, thread roots and nested replies, top-level PR comments, approval signals, and resolved history. Inspect every returned page and retain stable IDs; thread resolution alone does not mean a finding was answered.
- **Direction and response matching:** Distinguish new inbound feedback (including self-authored reviews) from authenticated thread replies and top-level responses referencing existing findings. Compare response references and content with the latest input rather than treating every same-account comment as answered or unanswered.
- **Outstanding view:** Track each finding's disposition, verified fix or no-change evidence, observed response, and resolution independently. This substitutes for the helper's action summary and prevents losing the overview across individual MCP calls.
- **Mutation sequence:** Check current branch and relevant provider state, post the authorized response, confirm it, resolve where eligible, then confirm resolution. If a later step fails, retain earlier confirmed effects and resume only remaining work.
- **Recheck and watch:** Repeat collection of new, edited, unresponded, and unresolved items after actions. Use bounded repeated checks when monitoring; a quiet interval is an observation, not completion.

These are the additional responsibilities of direct tooling, not additional gates or a requirement to reproduce the helper's Python models. Provider tools' own schemas determine the calls.

The helper's GitHub classification implementation is in `scripts/pr_review_github_logic.py`; MCP uses provider observations directly under the [review outcome contract](./review-cycle-contract.md).
