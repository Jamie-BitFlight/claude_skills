# Improvement Proposals: Awesome Codex Skills — Issue Triage

**Research entry**: ./research/skill-generation-tools/awesome-codex-skills-issue-triage.md
**Generated**: 2026-05-10
**Patterns assessed**: 7
**Backlog items created**: 1 (issues: #2244)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 5

---

## Improvement 1: Cluster open backlog items into duplicate groups via a new MCP tool

**Source pattern**: "Cluster by title similarity and labels. The agent groups likely duplicates locally." — research entry "Local Deduplication" section, sourcing SKILL.md line 67.
**Local system**: `plugins/development-harness/backlog_core/operations.py` (calls `find_fuzzy_duplicates`), `plugins/development-harness/backlog_core/parsing.py:481` (`find_fuzzy_duplicates` definition), `plugins/development-harness/backlog_core/server.py` (MCP tool surface)
**Confidence**: High
**Impact**: Medium
**Backlog**: #2244 created (priority P1)

### Current state

`find_fuzzy_duplicates(title, items, threshold)` exists in `parsing.py:481-516` and uses `difflib.SequenceMatcher` on normalized titles. It is called only by `_check_for_duplicates` in `operations.py:1621-1637`, which runs at item-creation time inside `backlog_add`. There is **no** MCP tool that takes the set of open items and returns duplicate clusters. Verified by grep: `find_fuzzy_duplicates` has exactly 2 callsites — its definition in `parsing.py:481` and its sole caller `_check_for_duplicates` in `operations.py:1634`. Server tool surface (`server.py`) registers no `backlog_cluster_duplicates`, `backlog_find_duplicates`, or equivalent. Result: an agent triaging an existing 305-issue open backlog (current state per `backlog_list` output) cannot identify near-duplicate clusters without manually invoking `backlog_add(force=False)` for each candidate title — a usage that is destructive (creates an item if no duplicate is found) and quadratic in tool calls.

### Target state

A new MCP tool `backlog_find_duplicates(threshold: float = FUZZY_DUPLICATE_THRESHOLD, section: str | None = None, limit: int = 0) -> dict` exposes pairwise-clustered duplicates among **existing** open items. Implementation reuses `find_fuzzy_duplicates` over the cross-product of open items (or items filtered by `section`), produces a list of `{cluster_id, member_count, members: [{issue, title, similarity_to_canonical}]}` groups sorted by member count descending, and returns the top `limit` clusters. The tool is read-only — it does not mutate any item. New file: `plugins/development-harness/backlog_core/server.py` gains a tool function and registration; logic added to `operations.py` as `find_existing_duplicate_clusters(items, threshold) -> list[DuplicateCluster]`.

### Measurable signal

Run from the repo root:

```bash
FASTMCP_SHOW_SERVER_BANNER=false FASTMCP_LOG_ENABLED=false uv run fastmcp call \
  --command "uv run --script plugins/development-harness/scripts/run_backlog_server.py" \
  --target backlog_find_duplicates \
  --input-json '{"threshold": 0.75, "limit": 5}'
```

Output contains a `clusters` key with at least 0 entries (zero is valid — high threshold may yield no clusters), `total_clusters`, and `total_items_examined`. Calling with `threshold=0.50` against the current 305 open items returns `total_items_examined >= 305`. Cluster members each contain `issue` (int), `title` (str), and `similarity_to_canonical` (float in [threshold, 1.0]).

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Cross-tool sync (Sentry → Linear / PagerDuty → Jira) ingestion into local backlog | Low | The research entry describes this as a Composio composition pattern using `composio run` with multiple toolkit slugs. Mapping to local would require new external API clients (Sentry, PagerDuty), credential storage outside the existing GitHub/GitLab/Linear backend abstraction, and a clear use case for ingesting observability data into a code backlog — none of which are evidenced in the current repo. The architectural fit is unclear without further design work. Would need: confirmed user demand, decision on whether observability ingestion belongs in the backlog system at all, and whether existing #982 (`~/.dh/` config + secrets) covers credential storage. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Pluggable toolkit / backend model (`composio link <tool>`) | Already tracked: `BacklogBackend` Protocol exists with `github`, `sqlite`, `memory` backends in `plugins/development-harness/backlog_core/backends/`. Linear backend code exists at `backlog_core/linear_client.py`. Formalisation tracked in #1177 ("Formalise IssueBackend Protocol and audit BacklogItem field portability across backends"). |
| Schema discovery (`composio execute <SLUG> --get-schema`) | Already covered: `fastmcp list` and `fastmcp call --target <tool>` against MCP servers provides equivalent schema introspection. Documented in `plugins/development-harness/CLAUDE.md` "Testing MCP Servers Against Fresh Source Code" section. |
| Stale item detection with auto-comment ("stale for 14+ days, please assign or close") | Already tracked: #1136 (`/dh:scan-stale-backlog` skill — batch triage of open P0/P1 items for staleness) covers this exact pattern, including stale-by-date triage and report generation. |
| Bulk mutations with 250ms inter-call sleep workaround | Architectural mismatch: local backend abstraction uses GraphQL batching (`gh_client.py`, `linear_client.py`) and PyGithub pagination — native batching is stronger than serial loops with sleep. Composio's 250ms sleep is a workaround for lack of native batching. Adopting it would be a regression. |
| TypeScript workflow scripts (`composio run --file scripts/triage.ts`) | Architectural mismatch: this repo uses Python 3.11+ for all scripts per `.claude/rules/language-conventions.md`. PEP 723 inline scripts already serve the same role. No improvement available without violating the language convention. |
