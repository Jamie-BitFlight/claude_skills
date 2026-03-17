# Feature Context: Backlog Semantic Matching

**GitHub Issue**: #745
**Priority**: P1 (defect)
**Classification**: Defect with traceable failure mechanism (5-whys root cause analysis)

---

## Problem Space

### What Fails

`/work-backlog-item` Step 1 finds backlog items by calling `mcp__backlog__backlog_list` and performing case-insensitive substring matching against the `title` field only. This fails when users describe items semantically rather than using exact title words.

**Verified failure mechanism** (fact-check report, 2026-03-15):

```python
# operations.py line 1024 — the entire matching logic
open_items = [it for it in open_items if title_lower in it.title.lower()]
```

Substring matching cannot compare meaning. A query for "fix login issue" will never match a title like "Authentication failure on SSO redirect" because no character sequence overlaps.

### When It Fails

The defect manifests in two scenarios:

1. **Synonym queries** -- User describes a problem using different words than the title. "fix login issue" vs. "Authentication failure on SSO redirect". Zero matches returned despite a semantically identical item existing.

2. **Topic-based navigation** -- User wants to work on "all the backlog CLI items" or "anything related to MCP servers". No filter exists for `type` or `topic`, so the user must scan the full list manually. The `backlog_list` tool accepts `section` (priority) and `status` filters but not `type` or `topic`, despite these fields existing in every item's frontmatter.

### Scale Context

Verified measurements (fact-check report, 2026-03-15):

- **245 open items** (253 total, 8 completed) -- corrected from original claim of 197
- **~86 lines average** per item file -- corrected from original claim of ~200
- **~259K tokens** total across all backlog files (1,035,004 characters at ~4 chars/token) -- corrected from original claim of ~512K
- `backlog_list` returns items **without descriptions** -- only title, priority, issue, plan, file_path, groomed, and optional status/milestone

### Critical Finding: Metadata Already Exists

The original issue framing stated "no categorization metadata exists for filtering." This was **refuted** by the fact-check report. Backlog item frontmatter already contains:

```yaml
metadata:
  topic: <categorization-slug>
  source: <source description>
  added: <date>
  priority: <priority-level>
  type: Feature|Bug|Refactor|Docs|Chore
  status: open|done|resolved|etc
  issue: <github-issue-number>
  last_synced: <timestamp>
  groomed: <boolean-or-date>
```

The `type` and `topic` fields are present in frontmatter but are **not exposed** by `backlog_list` in its response and are **not accepted** as filter parameters. The gap is not missing data -- it is unexposed data.

---

## Stakeholders

### Direct Users (invoke matching)

- **`/work-backlog-item` Step 1** -- Primary consumer. Calls `backlog_list`, searches title field for case-insensitive match. Handles zero/one/multiple match cases. This is the skill users invoke directly to start working on an item.

- **`/complete-implementation` Step 2 (follow-up routing)** -- Uses the same title-based substring matching pattern to find existing backlog items when routing follow-up task files created by code review. Documents: "case-insensitive substring match in the item's title field."

### Indirect Users (read matching results)

- **`backlog.py` CLI** -- Thin wrapper around `backlog_core.operations.list_items()`. Exposes `list` command with current filter parameters (section, status, title, label). Would need new CLI arguments for any new filter parameters.

- **`server.py` MCP server** -- Exposes `backlog_list` tool with current schema. Tool schema must be updated if new filter parameters are added.

### Data Producers (write items that get matched)

- **`/create-backlog-item`** -- Creates new backlog items. Currently writes `type` in frontmatter. If matching uses `topic`, this skill may need to derive or ask for topic during creation.

- **`/groom-backlog-item`** -- Grooms items, writes Impact Radius and other sections. Could derive `topic` from grooming analysis if not already populated.

### Supporting Systems

- **`parsing.py`** -- Contains `find_item()` helper for substring matching. Used by operations that resolve a selector to a single item (view, update, close, resolve, groom).

- **Test suite** -- 4 test files cover matching behavior: `test_backlog_core_server.py`, `test_scenarios.py`, `test_integration_reconciliation.py`, `test_backlog_gh_first.py`. All test current substring-only matching.

---

## Desired Outcome

### Layer 1: Expose Existing Metadata as Filters

`backlog_list` accepts `type` and `topic` as optional filter parameters. The response for each item includes `type` and `topic` fields when populated. Users and skills can narrow results before applying title matching.

**Acceptance criteria**:

- `backlog_list(type="Bug")` returns only items with `metadata.type: Bug`
- `backlog_list(topic="backlog-cli")` returns only items with matching topic
- Filters compose: `backlog_list(section="P1", type="Feature")` returns P1 features
- Response entries include `type` and `topic` fields
- CLI `list` command accepts `--type` and `--topic` arguments
- Existing callers that pass no new parameters see identical behavior (backward compatible)

### Layer 2: Semantic Matching

When substring matching returns zero results, a semantic matching fallback finds items whose title or description is semantically related to the query.

**Acceptance criteria**:

- Query "fix login issue" finds "Authentication failure on SSO redirect" when no substring match exists
- Semantic matching is a fallback -- substring matches are returned first if they exist
- `/work-backlog-item` Step 1 uses the new matching capability
- `/complete-implementation` follow-up routing uses the new matching capability
- Matching does not require loading all 259K tokens of descriptions into a single context

### Layer 3: Vector Retrieval (DEFERRED)

Vector embedding-based retrieval via zvec or similar. Deferred because:

- zvec source documentation was not found during fact-checking (INCONCLUSIVE verdict)
- Embedding model selection is a design choice not yet made
- Layers 1 and 2 address the immediate defect without embedding infrastructure

---

## Constraints

### Backward Compatibility (HARD)

- Title-only substring matching must continue working. All existing callers that pass `title=` to `backlog_list` must see identical results.
- `backlog_list` response schema is additive only -- new fields may be added, existing fields must not change shape or meaning.
- CLI commands must accept existing arguments unchanged; new arguments are additive.

### Scale (MEASURED)

- 245 open items, ~259K tokens total. Bulk-loading all descriptions into a single LLM context is feasible but expensive. Prefer filter-first strategies that narrow before semantic comparison.
- `backlog_list` intentionally omits descriptions from its response (per backlog item #330). Semantic matching must work without requiring `backlog_list` to return full descriptions.

### GitHub Sync

- Backlog items sync with GitHub Issues. Any new metadata exposed in `backlog_list` must remain consistent with GitHub issue state. The `type` and `topic` fields live in local frontmatter only (not in GitHub labels currently). If these fields are added to GitHub labels in the future, sync logic must be updated, but that is out of scope for this feature.

### Token Budget

- Semantic matching should not require the orchestrator to load all 245 item descriptions. The matching logic should run server-side (in `operations.py` or a helper module) and return ranked results.

---

## Open Questions

1. **Topic field population rate** -- How many of the 245 open items have `metadata.topic` populated? If coverage is low, the `topic` filter has limited utility until items are backfilled. The fact-check report confirmed the field exists in sampled items but did not measure population rate across all items.

2. **Semantic matching mechanism** -- Layer 2 requires a mechanism to compare query meaning against item titles/descriptions. Options include:
   - LLM-based comparison (send query + candidate titles to an LLM for ranking)
   - TF-IDF or keyword extraction (lightweight, no external dependencies)
   - Fuzzy string matching (Levenshtein distance, token overlap)
   - Vector embeddings (deferred to Layer 3)

   The architecture phase should evaluate these based on latency, cost, and accuracy trade-offs.

3. **Description access pattern for semantic matching** -- Semantic matching needs access to item content beyond titles. Options: read individual item files on demand, build an in-memory index at server startup, or maintain a pre-computed summary field. This is an architecture decision.

4. **User UX for multiple semantic matches** -- When semantic matching returns several candidates with similar relevance, how should `/work-backlog-item` present them? Current behavior lists multiple substring matches and asks the user to pick. The same pattern could apply, but semantic match confidence scores might help ranking.

---

## Related Systems (from Impact Radius)

The impact radius analysis identified **16 affected systems** across 5 categories. The full inventory is in [.claude/reports/groom-745-impact-radius.md](../.claude/reports/groom-745-impact-radius.md).

### Systems Requiring Code Changes (8)

- `operations.py` -- `list_items()` function and `_build_list_entry()` must expose `type`/`topic` fields and accept new filter parameters
- `server.py` -- MCP tool schema for `backlog_list` must add new parameters
- `backlog.py` -- CLI `list` command must add `--type` and `--topic` arguments
- `parsing.py` -- `find_item()` may need semantic matching support
- `/work-backlog-item` SKILL.md -- Step 1 matching logic must use new filters and semantic fallback
- `/complete-implementation` SKILL.md -- Step 2 follow-up routing must use new matching
- `/create-backlog-item` SKILL.md -- May need to derive/validate `topic` during creation
- `/groom-backlog-item` SKILL.md -- May need to populate `topic` during grooming

### Documentation Becoming Stale (7)

- `/work-backlog-item` Step 1 procedure description
- `/complete-implementation` follow-up routing description
- `/work-backlog-item` reference files (step-procedures.md)
- Backlog README matching behavior examples
- `/create-backlog-item` item field documentation
- `/groom-backlog-item` categorization workflow
- 2 agent context files (swarm-task-planner, backlog-mcp-validator)

### Test Coverage Gaps (4 files)

- `test_backlog_core_server.py` -- needs tests for new filter parameters and semantic matching
- `test_scenarios.py` -- needs integration scenarios for semantic queries
- `test_integration_reconciliation.py` -- needs backward compatibility verification
- New test file or expanded coverage for matching algorithm unit tests

---

## Root Cause Summary

From the 5-whys analysis (classification report):

1. **Primary**: Substring matching algorithm has no semantic understanding -- by design, it compares character sequences, not meaning
2. **Secondary**: No strategy abstraction in Step 1 matching -- it directly calls the tool without a filter-first pattern
3. **Tertiary**: Existing categorization metadata (`priority`, `type`, `status`, `topic`) is present in frontmatter but not exposed to or used by the matching system
4. **Quaternary**: No instrumentation to surface matching failures -- the problem was discovered retroactively after 245 items accumulated

---

## Source Reports

- Impact Radius: [.claude/reports/groom-745-impact-radius.md](../.claude/reports/groom-745-impact-radius.md)
- Fact-Check: [.claude/reports/groom-745-fact-check.md](../.claude/reports/groom-745-fact-check.md)
- Classification: [.claude/reports/groom-745-classification.md](../.claude/reports/groom-745-classification.md)
- RT-ICA Assessment: [.claude/reports/groom-745-rtica.md](../.claude/reports/groom-745-rtica.md)
