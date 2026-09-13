# Cross-Reference Format

The canonical shape of a research entry's `## Cross-References` section. Every producer writes rows
in exactly this form — `@research-cross-referencer` (forward links), `@research-backlink-detector`
(reciprocal rows), and anyone adding a row by hand.

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

Every path must resolve to a real file. Rows pointing at paths that do not exist on disk are defects — `validate_research.py check-backlinks` reports them, and `@research-backlink-detector` skips them with reason `path not found`.

---

## Relationship Phrase

The **Relationship** column names the specific conceptual link between the two entries. A generic label — "related tool", "similar project", "see also" — fails this bar.

Good examples:

- "alternative MCP server transport approach"
- "provides the embedding layer this tool queries"
- "shares async task execution model"
- "complements this tool's data collection with analysis"
- "overlapping use case: structured agent output validation"

Backlink rows do not invert or reuse the forward phrase's wording — `transform_to_backlink_description()` in [backlink_lib.py](./../scripts/backlink_lib.py), the single source of truth for this transform, produces a plain `"referenced by {entry} ({category})"` for almost every row. This looks like the generic label this document's own bar forbids, but that bar governs human/agent-authored forward rows, where a specific phrase is achievable by reading both entries; a backlink row is generated from one entry's forward phrase, which was written about the *other* entry (this table's Entry column is that phrase's grammatical subject, per the "provides the embedding layer this tool queries" example above) — reusing its wording under a different Entry attributes it to the wrong side. The one exception is a mutual "shares" phrase — one that *begins* with "shares", so it carries no leading clause describing one particular entity — which reads true regardless of which entry is named as subject, and is carried over with "(bidirectional)" appended. A phrase shaped `<descriptor of the target>; shares <X> with <source>` contains the word but is not mutual, and takes the plain `"referenced by …"` fallback like any other. See the module-level comment above that function for the corpus evidence (#3524, #3525).
