# GitHub MCP boundary

Use this branch only when the bundled CLI cannot use `gh` and a GitHub MCP connector is available.
MCP can supply read-only diagnostic evidence, but this package exposes no executable ingress that
turns connector responses into a validated canonical `ReviewSnapshot`. The boundary therefore fails
closed: MCP evidence cannot authorize source action, provider mutation, watch state, or completion.

## Canonical source

The exact GitHub predicates live only in `scripts/pr_review_github_logic.py`:

- `CODEX_REACTOR_LOGINS` owns accepted actor identities;
- `CODEX_EMPTY_REVIEW_BODY` and `is_codex_empty_review` own no-findings classification;
- `is_codex_thumbs_up` owns approval-signal classification;
- `latest_revision_at` owns the head-commit/force-push revision boundary;
- `references_review` and `review_effective_timestamp` own provider-backed response matching.

Use those symbols and the bundled GitHub adapter as the canonical source for classification.

## Read-only diagnostic collection

When useful for reporting, collect PR identity, exact head revision, every page of review threads and
nested comments, submitted reviews, PR-level comments, reactions, force-push events, and authenticated
actor identity through one connector. A missing field, page, permission, or stable reference makes the
diagnostic collection incomplete. Report only observed provider facts and identify the missing
surface.

MCP diagnostics remain `SNAPSHOT_INCOMPLETE` until the executable transport produces a complete canonical snapshot. Report observed facts and missing surfaces; if the CLI remains unavailable, report `BLOCKED` with the missing transport. Resume through `fetch` when available.
