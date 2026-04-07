# Workflow: Create Backlog Item

Use this workflow only when the current request does not already map to an existing backlog item reference. Create the item via `mcp__plugin_dh_backlog__backlog_add`.

Read [scope.md](./scope.md) before proceeding. All create actions operate within that scope boundary.

## Inputs

Required workflow inputs:
- `mode`: optional; allowed values are `interactive` or `auto`. If omitted, use `interactive`.
- `item_title`: required for `auto`
- user-provided problem description or equivalent creation input

Optional inputs:
- research context, if available
- existing backlog items returned by `backlog_list`

This workflow does not apply to an existing `item_ref`. If an existing backlog item reference is already available, stop and return control to the calling stage.

## Modes

| Mode | Behavior |
|---|---|
| `interactive` | Use `AskUserQuestion` to collect missing fields. Default when mode is omitted. |
| `auto` | Do not call `AskUserQuestion`. Derive fields from available inputs and log each decision. |

## Step 1: Collect fields

### Mode: `auto`

`auto` = Do not call `AskUserQuestion`.

Inputs:
- `item_title`: required
- user input
- research context, if available
- existing backlog items via `backlog_list`, for duplicate detection only

Field derivation:

| Field | Rule |
|---|---|
| `title` | Use `item_title` exactly after trimming outer whitespace. |
| `priority` | Use explicit user-provided priority if present and valid. Otherwise assign `P1` only when the input contains explicit urgency evidence such as `critical`, `required`, `must`, or an explicit priority flag. Assign `P2` for `nice to have` or `optional`. Otherwise default to `P2`. Do not infer `P0` unless the user explicitly stated `P0`. |
| `description` | Write a problem-only summary from the user input and research context. Keep only: what is broken, missing, or requested; where it was observed; and what impact it has. Remove implementation steps, architecture ideas, suggested fixes, and file-level prescriptions as defined by the scope boundary rules above. If the user supplied a possible fix, preserve it as `**User-provided context**: {verbatim text}` and not as a requirement. If the input contains lines beginning with `?` or `Research:`, preserve them under `**Research first**: {content}`. |
| `source` | If a research file was used, set `source` to `Agent task - auto-derived from research/{filename}`. Otherwise set `source` to `Agent task - auto-derived from input`. |
| `type` | Assign `Bug` for defect reports, `Feature` for new requested capability, `Refactor` for restructuring-only work, `Docs` for documentation-only work, and `Chore` otherwise. |

Research search, when applicable:
1. Search only under `research/` relative to the workflow root.
2. Rank matches in this order: exact title match, then filename keyword overlap, then content keyword overlap.
3. If multiple matches tie at the same rank, choose the shortest path name; if still tied, choose the lexicographically first filename.
4. Read only the top-ranked match.
5. If no useful match exists, continue without research context.

Log each derived field as:
`[AUTO] {field}: {decision} - {evidence}`

### Mode: `interactive`

Use `AskUserQuestion` to collect any missing required fields:

1. Title: "What is the title for this backlog item?"
2. Priority: "What priority? P0 (must-have), P1 (should-have), P2 (could-have), or Ideas (exploratory)"
3. Description: "Describe the item. Cover: (1) what is broken, missing, or requested, (2) where it was observed, and (3) what impact it has. Do not describe the fix or implementation approach."
4. Source: "Where did this come from? (for example: session observation, user report, CI failure)"
5. Type: "What type? Feature, Bug, Refactor, Docs, or Chore"

If the user supplies implementation details, extract only the problem statement into `description`. Preserve the removed content as:
`**User-provided context**: {verbatim text}`

## Step 2: Validate inputs

Required fields before write:
- `title`: non-empty after trimming
- `priority`: one of `P0`, `P1`, `P2`, or `Ideas`
- `description`: non-empty after trimming

Validation rules:
- Strip implementation instructions from `description` using the scope boundary rules above.
- If stripping leaves `description` empty, stop and request a problem-only description.
- Treat `warnings` as non-blocking unless the tool also returns `error` or non-empty `errors`.

## Step 3: Duplicate detection

Duplicate detection uses boolean substring matching, not semantic matching.

1. Extract 2 to 4 key concepts from `title`.
2. If fewer than 2 usable concepts exist, use all usable non-trivial concepts.
3. Build search string:
   `{concept1} OR {concept2} OR {concept3}`
4. Call:
   `mcp__plugin_dh_backlog__backlog_list(search="{concept1} OR {concept2} OR {concept3}", match_context=true)`

Match handling:
- If no overlaps are found, continue.
- If one or more overlaps are found, use the highest-confidence returned match first.
- In `interactive` mode, ask:
  `Possible duplicate: '{existing_title}' ({item_ref}) in {location}. Proceed anyway?`
- In `auto` mode, log:
  `[AUTO] STOP - duplicate detected: '{existing_title}' ({item_ref}) in {location}`
  and stop.

If the user chooses not to proceed, stop without writing.

Do not use `force=true` unless the user has already confirmed proceeding despite the duplicate.

## Step 4: Write via MCP

Call:

```text
mcp__plugin_dh_backlog__backlog_add(
    title='{title}',
    priority='{priority}',
    description='{description}',
    source='{source}',
    type='{type}',
    gate_token='problems-not-solutions'
)
```

Tool parameters:
- `title`: required
- `priority`: required; must be `P0`, `P1`, `P2`, or `Ideas`
- `description`: required
- `source`: optional; defaults to `Not specified`
- `type`: optional; one of `Feature`, `Bug`, `Refactor`, `Docs`, `Chore`
- `gate_token`: must be `problems-not-solutions`
- `force`: optional; default false

If the result contains `error` or non-empty `errors`, report the error and stop.

## Step 5: Use `item_ref` from the response

The `backlog_add` response contains `item_ref` — use that value directly for all downstream workflows and selector parameters.

## Step 6: Confirm write

Report:

```text
Backlog item created.

Title   : {title}
Item    : {item_ref}
Priority: {priority}
Type    : {type}

Next steps:
  /dh:work-backlog-item groom {item_ref}
  /dh:work-backlog-item work {item_ref}
```

## Error handling

Stop and report on:
- scope.md not readable or scope boundary missing from scope.md
- missing required field after validation
- invalid priority value
- duplicate detected and the user chose not to proceed
- duplicate detected in `auto` mode
- MCP tool result contains `error` or non-empty `errors`

## Completion criteria

Creation is complete only when:
- `backlog_add` returns success with no `error` and no non-empty `errors`
- `item_ref` is normalized to `#N`
- confirmation with `item_ref` is shown to the user
