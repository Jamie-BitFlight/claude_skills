# GitHub MCP provider operations

Read when the preferred helper is unavailable and GitHub MCP is available. Use connected tool schemas for invocation.

## Direct-provider working path

- Collect submitted reviews, threads and nested replies, top-level comments, approvals, and resolved history. Check pagination and retain stable references.
- Classify by provider relationship: self-authored review submissions and new threads are inbound; authenticated replies and top-level comments referencing existing findings are response candidates. Match responses to the latest input.
- Keep a compact view of outstanding findings, dispositions, verification, observed replies, and resolution. Reuse assessments whose evidence remains valid.
- Assess shared causes, implement authorized changes, and verify affected behavior and tests before replying or resolving. Group related edits when practical.
- Before a group of provider mutations, refresh relevant state and check every planned action for current target, authorization, and capability. Confirm each reply and resolution separately. If resolution fails after a reply succeeds, retain the reply and resume resolution only.
- Recheck new, edited, unresponded, and unresolved inputs. Use bounded repeated checks when monitoring.

The helper automates these cross-references. MCP establishes the same [review outcomes](./review-cycle-contract.md) through provider observations.
