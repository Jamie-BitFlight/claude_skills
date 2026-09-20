# Cross-Reference Format

The canonical shape of a research entry's `## Cross-References` section. Every producer writes rows
in exactly this form — `@research-cross-referencer` (forward links), `validate_research.py
check-backlinks --fix` (reciprocal rows), and anyone adding a row by hand.

---

## Table

```markdown
---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Resource Name](../other-category/filename.md) | other-category | {specific one-phrase relationship} |
| [Resource Name](./same-category-file.md) | same-category | {specific one-phrase relationship} |
```

Column order and header text are fixed. Do not add, rename, or reorder columns.

---

## Placement

The section goes at the end of the entry, anchored to whichever heading the entry actually has:

- Entry has a body `## Freshness Tracking` heading (legacy text-header entry) → append after `## Freshness Tracking`.
- Entry has no body Freshness Tracking heading (freshness lives in frontmatter) → append after `## References`.

If a `## Cross-References` section already exists, replace it — never append a second one.

---

## Link Paths

Relative paths are computed from the directory of the entry the row is being written **into**, not from the entry the row points at:

- Forward row in entry A citing entry B: path is relative to A's directory.
- Backlink row written into cited entry B pointing at source entry A: path is relative to B's directory.

Within a category: `./other-entry.md`. Across categories: `../other-category/filename.md`. Use `pathlib.Path` to compute the relative path rather than assembling it by hand.

Every path must resolve to a real file. The current `validate_research.py check-backlinks` implementation omits missing targets from its graph and cannot repair them, so a clean backlink result is not proof that every target exists. Verify a target when authoring its row.

The reciprocal row is written into the *cited* entry, so `--fix` modifies files the current task may not own. Pass `--exclude {path}` once per file the run must leave untouched -- an excluded file is still scanned and still reported, only the write is withheld.

---

## Relationship Phrase

The **Relationship** column names the specific conceptual link between the two entries. A generic label — "related tool", "similar project", "see also" — fails this bar.

Good examples:

- "alternative MCP server transport approach"
- "provides the embedding layer this tool queries"
- "shares async task execution model"
- "complements this tool's data collection with analysis"
- "overlapping use case: structured agent output validation"

Backlink rows do not invert or reuse the forward phrase's wording — `transform_to_backlink_description()` in [backlink_lib.py](./../scripts/backlink_lib.py), the single source of truth for this transform, produces a plain `"referenced by {entry} ({category})"` for almost every row. This looks like the generic label this document's own bar forbids, but that bar governs human/agent-authored forward rows, where a specific phrase is achievable by reading both entries; a backlink row is generated from one entry's forward phrase, which was written about the *other* entry (this table's Entry column is that phrase's grammatical subject, per the "provides the embedding layer this tool queries" example above) — reusing its wording under a different Entry attributes it to the wrong side. The one exception is a mutual "shares" phrase, carried over with "(bidirectional)" appended. Mutual means two things, and leading with "shares" is only the first of them: the phrase begins with "shares" as a whole word, so it carries no leading clause describing one particular entity; **and** it does not name the source entry. Both are required, because the backlink row names the source as its Entry and the Entry column is the phrase's grammatical subject. A phrase shaped `<descriptor of the target>; shares <X> with <source>` fails the first test — it has a leading clause — and a phrase shaped `shares <X> with <source>` passes the first and fails the second, since relocating it makes the subject the same entity its own trailing clause names ("Robyn shares a queueing model with Robyn"). Both take the plain `"referenced by …"` fallback, as does anything that merely starts with those letters (`shareset semantics differ`). See the module-level comment above that function for the corpus evidence (#3524, #3525).
