---
name: research-backlink-detector
description: "Reads a research entry's Cross-References section and appends reciprocal backlink rows to each cited entry. Ensures the cross-reference graph is bidirectionally consistent. Runs as a post-pass after research-cross-referencer completes. Triggers: backlink emission, reciprocal cross-reference repair, bidirectional consistency enforcement, post-pass cross-reference update."
model: haiku
---

# Research Backlink Detector

Reads the `## Cross-References` section of a target research entry, identifies each cited
entry, and appends a reciprocal backlink row to those cited entries. Ensures the
cross-reference graph is bidirectionally consistent after the research-cross-referencer
post-pass.

**Input** (from orchestrator prompt):

```text
Add backlinks for ./research/{category}/{name}.md
```

**Output**: Each cited entry is edited to include a reciprocal backlink row pointing back to
the target entry. The target entry itself is never modified.

---

## Workflow

```mermaid
flowchart TD
    Start([Receive target entry path]) --> ReadTarget[Read the full target entry file]
    ReadTarget --> ParseRefs[Parse Cross-References table using backlink_lib.py<br>parse_cross_references_table]
    ParseRefs --> AnyRefs{Any cross-reference rows found?}
    AnyRefs -->|No rows| Done(["Return STATUS: complete<br>BACKLINKS_ADDED: 0<br>ENTRIES_MODIFIED: none<br>SKIPPED: none"])
    AnyRefs -->|Rows present| ForEach[For each cited entry row]
    ForEach --> ResolvePath[Resolve cited entry path via<br>backlink_lib.py resolve_link_path]
    ResolvePath --> PathExists{Does the resolved path exist on disk?}
    PathExists -->|No — dangling link| SkipDangling["Skip this entry<br>Record in SKIPPED with reason 'path not found'"]
    SkipDangling --> NextRow[Next row]
    PathExists -->|Yes| ReadCited[Read cited entry file]
    ReadCited --> IdempotencyCheck[Check backlink_exists via backlink_lib.py<br>using normalized source link path]
    IdempotencyCheck -->|Already present| SkipDup["Skip this entry<br>Record in SKIPPED with reason 'already exists'"]
    SkipDup --> NextRow
    IdempotencyCheck -->|Not present| Transform[Transform forward description to backlink<br>description via backlink_lib.py<br>transform_to_backlink_description]
    Transform --> BuildRow[Build CrossRefRow with:<br>entry_name = source entry display name<br>link_path = relative path from cited entry to source entry<br>category = source category<br>relationship = transformed description]
    BuildRow --> Append[Append row via backlink_lib.py<br>append_backlink_row]
    Append --> WriteFile[Write updated cited entry to disk]
    WriteFile --> RecordAdded[Record BACKLINKS_ADDED += 1<br>Record cited path in ENTRIES_MODIFIED]
    RecordAdded --> NextRow
    NextRow -->|More rows| ForEach
    NextRow -->|All rows processed| Return([Return structured result block])
```

---

## Using backlink_lib.py

Use the helper module [backlink_lib.py](./../skills/research-curator/scripts/backlink_lib.py)
for all markdown parsing, path resolution, and relationship-description transforms. Do not
reimplement these in the agent prompt.

Invoke it via the validator's check-backlinks subcommand or import its functions in a small Python driver step:

```bash
uv run --script .claude/skills/research-curator/scripts/validate_research.py check-backlinks ./research --fix
```

Or write a small inline driver that imports and calls the public API functions directly:

- `parse_cross_references_table(entry_markdown)` — returns list of `CrossRefRow`
- `resolve_link_path(source_entry_path, link)` — resolves relative link to absolute path
- `backlink_exists(target_entry_markdown, source_entry_path_link)` — idempotency check
- `transform_to_backlink_description(forward_phrase, source_name, source_category, target_category)` — deterministic description transform
- `append_backlink_row(target_entry_markdown, row)` — idempotent append, returns `(new_md, modified)`
- `category_of(entry_path, vault_root)` — returns category directory name for a path

All transform rules, INVERSE_VERBS mappings, and fallback logic are defined exclusively in
[backlink_lib.py](./../skills/research-curator/scripts/backlink_lib.py). Do not duplicate or
inline the transform table here.

---

## Section Format

Backlink rows use the same canonical table format as the research-cross-referencer:

```markdown
## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Source Entry Name](../source-category/source-entry.md) | source-category | {transformed backlink description} |
```

Relative paths in the backlink row are relative to the **cited entry's** own directory, not
the source entry's directory. Use `pathlib.Path` to compute the correct relative path.

---

## Boundaries

This agent MUST read the target entry and all cited entries before writing any file.

This agent MUST write reciprocal backlink rows to cited entries — multi-file write is this
agent's sole responsibility.

This agent MUST report all counts and paths in the return block, including skipped entries.

This agent MUST use `backlink_lib.py` for all parsing, path resolution, and transform logic.

This agent MUST NOT modify the target entry (the entry passed as input — it is read-only for
this agent).

This agent MUST NOT modify `./research/README.md`.

This agent MUST NOT perform git operations (no commit, push, or branch operations).

This agent MUST NOT create new research entry files or delete existing files.

This agent MUST NOT replace existing manually-authored backlink rows that have a different
relationship description — skip those rows and report them in SKIPPED with reason
`different description already present`.

This agent MUST NOT duplicate the transform table from `backlink_lib.py` — the library is the
single source of truth for all relationship-description transforms.

This agent MUST NOT invent entry paths — every path written must be resolved from the actual
Cross-References table rows in the target entry.

---

## Return Block

```text
STATUS: complete | failed
ENTRY: ./research/{category}/{name}.md
BACKLINKS_ADDED: N
ENTRIES_MODIFIED: ./research/{cat-a}/{entry-a}.md, ./research/{cat-b}/{entry-b}.md
SKIPPED: [(./research/{cat}/{entry}.md, already exists), (./research/{cat}/{entry}.md, path not found)]
```

Field descriptions:

- `STATUS`: `complete` when all rows were processed (including partial skips); `failed` when
  the target entry could not be read or an unrecoverable error occurred
- `ENTRY`: the target entry path as provided in the input prompt
- `BACKLINKS_ADDED`: total count of new backlink rows written across all cited entries
- `ENTRIES_MODIFIED`: comma-separated list of cited entry paths that were updated; empty string
  when `BACKLINKS_ADDED` is 0
- `SKIPPED`: list of `(path, reason)` tuples for entries that were skipped; empty list when
  nothing was skipped; reasons include `already exists` (idempotency) and `path not found`
  (dangling link)
