---
name: backlog-view-architecture
description: backlog_view MCP tool real location, over-budget empty-content trap, and name-keyed sections dict — verified live 2026-06-01
metadata:
  type: project
---

# backlog_view Architecture Traps (development-harness plugin)

Verified by live `fastmcp call` + source read 2026-06-01 (issue #2521 review). Re-verify before acting — large files churn.

**Where the tool lives**: `backlog_view` is `backlog_core/server.py:1933`. `scripts/run_backlog_server.py` is a ~53-line PEP 723 launcher that only does `from backlog_core.server import mcp; mcp.run()`. Specs/plans that attribute the tool change to `run_backlog_server.py` are wrong — the work is in `server.py` + `operations.py`.

**Over-budget directory fallback is in the TOOL WRAPPER, not view_item()**: `server.py` checks `_view_payload_token_count(full_response) > _VIEW_TOKEN_BUDGET` (=4000) and returns `_build_over_budget_view()` (`server.py:1885`) — a directory with `sections=None`, `body=""`, only `sections_index`+`_over_budget`+`_usage`. The underlying `operations.view_item()` (`operations.py:3239`) returns full `body`+`sections` UN-gated. Any feature that needs full content of a large item must call `view_item()` directly, NOT the gated tool. Live #2515 (over budget) via the tool returns empty content; #2521 (under budget) returns full.

**ViewItemResult.sections shape**: `dict[str, SectionEntryMetadata | GroomedSectionMetadata]` — name-keyed dict of TypedDicts, NOT an ordered `Section.entries` list. `SectionEntryMetadata = {entries: list[SectionEntryDict], num_entries, num_struck}`; `SectionEntryDict = {id, struck, content}`. `sections_index` is a separately-built preformatted STRING (`_build_sections_index_from_body`, regex over raw body). Ordering of the dict is implicit — do not assume `dict.keys()` order matches `sections_index` numbering; reconcile or parse `body`.

**GitHub vs YAML fork**: GitHub items → raw `body` + regex `## `/`### ` header matching; `section_filter_miss` set-and-continue (silent fallback) at `operations.py:3020`, `3094`, consumed `~3167`. YAML items → structured sections via `_populate_yaml_item_content` / `_build_sections_from_yaml_item`. Section-miss error-on-miss fix touches all three sites + the `server.py` wrapper, not one.

**est_tokens double-count trap**: per-entry `content` in `sections` duplicates `body` text (`server.py:2073` documents this; #2495 fix). Summing both inflates token measurement. Any new map `total_est_tokens` must sum level-1 sections only.

**Live verify commands**: `FASTMCP_SHOW_SERVER_BANNER=false FASTMCP_LOG_ENABLED=false uv run fastmcp call --command "uv run --script $(pwd)/plugins/development-harness/scripts/run_backlog_server.py" --target backlog_view --input-json '{"selector":"2521","summary":false}'`. Parse `--json` via `json.loads(outer["content"][0]["text"])`.
