# Groom: Intake

Validate the item identified by <item_ref/> is eligible for grooming, and extract its details.

## Load Item

Verify <item_ref/> exists via `uv run --script "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog view --selector "{item_ref}"`
(the CLI has no `summary` parameter — it always returns full content). If error, report and stop.

To extract the integer for tools that require `issue_number` (int):
`issue_number = int(item_ref.lstrip('#'))`

## Validate: Pre-Groom Checks

Run these checks in order per item. First failure → SKIP.

**Check A — Prior implementation**:

```bash
git log --oneline --all -50 --grep='{title keywords}'
```

```bash
uv run --script "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog merged-prs --search "{title keywords}"
```

If commits or merged PRs reference this item:

```bash
uv run --script "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog resolve --selector "{item_ref}" --summary "Completed via PR #{pr} / commit {sha}"
```

If the active backend supports comments, also record evidence:

```bash
uv run --script "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog comment-issue --issue-number {issue_number} --body "Completed via {evidence}"
```

Result: **SKIP**.

**Check B — Location validity**:

If item has `suggested_location`: run `Glob(suggested_location)`.

- Path exists OR no `suggested_location` in item → continue.
- Path not found: `Grep` codebase for module/class name from the path.
  - Substitute found: update via `backlog_groom(selector='{item_ref}', section='Suggested Location', content='{substitute}')` → continue.
  - No substitute: **SKIP** — report "suggested_location gone with no substitute."

**Check C — Age and activity**:

Condition: `metadata.added` older than 90 days AND `metadata.groomed` absent AND no
comments on the item AND no `plan` field.

If condition met: search `backlog_list` for keyword overlap with items added in last 30 days.

- Overlap found:
  - When <mode/> is `auto`: log `[AUTO] WARN: possibly superseded by '{newer title}' — proceeding` → continue.
  - Otherwise: `AskUserQuestion` — "Possibly superseded by '{newer title}'. Proceed?" → user decides.
- No overlap: continue.

If condition not met: continue.

**Check D — Item state**:

Check the item's state:

```bash
uv run --script "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog view --selector "{item_ref}"
```

Note: the CLI's `backlog view` has no `summary` parameter — it always returns full content
(simpler/flatter than MCP's progressive-disclosure view).

- `state: open` → continue.
- `state: closed` → search for evidence:

```bash
git log --oneline --all -20 --grep='{item_ref}'
```

```bash
uv run --script "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog merged-prs --search "{item_ref}"
```

- Evidence found: `backlog_resolve(selector='{item_ref}', summary='...')` → **SKIP**.
- No evidence: report "issue {item_ref} closed but no commit/PR found — recommend manual review" → **SKIP**.

**Check E — Already groomed today**:

If `groomed == today's date` AND item has required groomed sections → **DRIFT**.
Route to [groom-drift.md](./groom-drift.md).

If `groomed` absent, empty, or not today → **PROCEED**.

## Extract Item Details

```bash
uv run --script "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" backlog view --selector "{item_ref}"
```

Note: the CLI's `backlog view` has no `summary` parameter — it always returns full content
(simpler/flatter than MCP's progressive-disclosure view).

From the response, extract:

| Field | Source |
|---|---|
| `title` | `title` field |
| `description` | `description` field |
| `source` | `source` field (optional) |
| `suggested_location` | body, `**Suggested location**:` line (optional) |
| `priority` | `priority` field |
| `item_ref` | `issue` field — already `#N` format |
| `issue_number` | `int(item_ref.lstrip('#'))` — integer for artifact tools |
| `plan` | `plan` field (optional) |
| `labels` | `labels` list |
| `groomed` | `groomed` field |
| `research_first` | body, lines starting with `**Research first**:` or `Research first:` (accept both formats) |

## Outputs

On success, the agent continues to `analyze.md` with:
- All extracted fields above
- <item_ref/> and `issue_number`

On SKIP: report reason and stop.
On DRIFT: route to `groom-drift.md` and stop.
