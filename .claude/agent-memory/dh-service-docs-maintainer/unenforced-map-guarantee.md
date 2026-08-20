---
name: unenforced-map-guarantee
description: backlog_view map mode's "under 2,000 tokens" claim is not enforced by disclosure_handler.py — where the false claim lives, and the tracking issue
metadata:
  type: project
---

`BacklogViewDisclosureHandler._handle_map` in
`plugins/development-harness/backlog_core/disclosure_handler.py` joins every ordinal entry into
`map_text` unconditionally (`"\n".join(mapper.format_map_line(e) for e in entries)`) with no
truncation or pagination. `over_budget` is computed (`total_est_tokens > TOKEN_BUDGET`) but never
acts on the text — a large item's map response is returned in full regardless of size.

**Why**: R2 of `plugins/development-harness/docs/agent-markdown-consumption-contract.md` (as of
2026-08-20, only on the unmerged `docs/component-architecture-map` branch, not yet on `main`)
requires everything to paginate, nothing to drop. The map handler predates that contract and was
never updated to match it.

**How to apply**: Do not describe the map response as bounded/capped in any doc without checking
this handler first — several places asserted the false bound independently: `SKILL.md` and
`references/progressive-disclosure.md` in the `backlog` skill (fixed PR #3051), plus (still
unfixed as of this writing) `disclosure_types.py`'s `MapResponse`/docstrings and
`docs/mcp-progressive-disclosure-contract.md` line ~192 — all tracked under issue #3059, whose
acceptance criteria now also require "no docstring or document asserts a bound the implementation
does not enforce." Check #3059's current state before re-fixing these — it may already be closed.
