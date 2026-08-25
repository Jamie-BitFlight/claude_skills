# ADR-9: Close/Resolve Semantic Redesign

**Status**: Decided
**Date**: 2026-03-02
**Supersedes**: ADR-8 (`close --reason` Semantic Correction, in `~/.dh/projects/{slug}/plan/architect-backlog-mcp-migration.md`)

## Context

ADR-8 addressed a narrow bug: CLI `close --reason` was routed to `backlog_resolve` because the
`close` subcommand never accepted `--reason`. That was correct as a migration fix but left the
semantics backwards:

- `close` meant "verified DONE" (requires `checklist_pass`, takes `plan`)
- `resolve` meant "dismissed without completion" (takes `reason`)

This is counterintuitive. "Resolve" naturally means "the problem was solved." "Close" naturally
means "we're done with this item" — which may or may not mean the work was completed. Multiple
callers in skills (groom-backlog-item, work-backlog-item) used `resolve` when discovering
already-completed work, which is semantically wrong — the work IS done, it should be resolved.

## Decision

Invert the semantics:

### `close` — Dismissed without completion

Terminal state for items that will NOT be worked. Requires a categorized reason.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `selector` | `str` | yes | Item selector |
| `reason` | `str` | yes | One of: `duplicate`, `out_of_scope`, `superseded`, `wontfix`, `blocked` |
| `reference` | `str` | no | Related item: `#N`, URL, or title |
| `comment` | `str` | no | Additional context |
| `cleanup` | `bool` | no | Remove local file after close |
| `force` | `bool` | no | Close even if open PRs reference the issue |

**Valid reasons:**

| Reason | When to use |
|--------|-------------|
| `duplicate` | Another item covers the same work |
| `out_of_scope` | Doesn't belong in this project |
| `superseded` | Replaced by a different item or approach |
| `wontfix` | Deliberate decision not to do this |
| `blocked` | Permanently blocked, cannot proceed |

**Metadata**: `{"status": "closed", "close_reason": "{reason}", "close_reference": "{reference}", "close_comment": "{comment}"}` on every backend.
The caller-provided `reference` is the related item and remains distinct from `BacklogItem.reference`, the storage identity.
**GitHub comment**: `Closed ({reason}). Reference: {reference}. {comment}` using the same caller-provided `reference` and `comment`.
**GitHub issue state**: `closed`

### `resolve` — Completed with evidence

Terminal state for items where the work IS done. Requires a summary of what was accomplished.
Creates an audit/retrospective trail.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `selector` | `str` | yes | Item selector |
| `summary` | `str` | yes | What was done (1-2 sentences) |
| `plan` | `str` | no | Plan path or completion reference |
| `method` | `str` | no | How the work was done |
| `notes` | `str` | no | Problems found, surprises, comments |
| `follow_ups` | `str` | no | Created follow-up tickets (comma-separated refs) |
| `findings` | `str` | no | Retrospective learnings |
| `cleanup` | `bool` | no | Remove local file after resolve |
| `force` | `bool` | no | Resolve even if open PRs reference the issue |

Only `summary` is required. For trivial items, a one-liner suffices. The full record
(method, findings, follow_ups) earns its weight on medium+ complexity items.

**Metadata**: `{"status": "done", "priority": "completed", "plan": "{plan}"}`
**GitHub comment**: Structured markdown with non-empty sections only.
**GitHub issue state**: `closed`

## Consequences

### Callers that need updating

- `work-backlog-item/SKILL.md` Step 9c/9d: close+reason calls become `close(reason=...)`;
  completion calls become `resolve(summary=...)`
- `work-backlog-item/references/close-resolve-procedure.md`: Full rewrite of procedure
- `groom-backlog-item/SKILL.md` Steps 2.2/2.3: "Already implemented" discovery should use
  `resolve(summary="Already implemented via PR #N / commit {sha}")`, not `close`
- `backlog/SKILL.md`: Tool documentation updated

### Backwards compatibility

`SKIP_STATUS` in `models.py` includes both old and new terminal values:
`("DONE", "RESOLVED", "COMPLETED", "CLOSED")`. Existing items with `status: resolved` or
`status: done` continue to be recognized as terminal.

### GitHub interaction

Both operations close the GitHub issue. The distinction lives in the structured comment
and optionally in labels (`closed:{reason}` for dismissals, `resolved` for completions).
