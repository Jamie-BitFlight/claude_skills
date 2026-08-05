---
name: dh-mcp-cli-docs
description: development-harness plugin's MCP-vs-CLI documentation structure — canonical mapping source, which docs already pair an MCP reference with a dedicated CLI section, and recurring drift patterns to check for
metadata:
  type: project
---

## Canonical CLI mapping source

`plugins/development-harness/docs/backend-providers.md` "CLI vs MCP Capability Surface" section
is the authoritative, self-declared capability inventory for `sam_schema/cli.py` vs the MCP tools
(backlog + SAM servers). It states explicitly: "Both surfaces delegate the operations they share to
the same `backlog_core.operations` / `sam_schema.core` paths — there is no parallel CLI
implementation." When adding CLI info to any other dh doc, cross-reference this section rather
than duplicating the flag mapping.

`plugins/development-harness/docs/TASK_FILE_FORMAT.md` "DH CLI Usage Guide (Validated Fallback
Reference)" section is the second authoritative CLI doc, specifically for `plan`/`backlog`/
`dispatch`/`artifact`/`active-task` command groups with a runnable bash example block. Its own
"SAM MCP Tools (Structured Adapter)" Quick Reference section a few hundred lines earlier
deliberately documents the MCP composite-tool syntax (`sam_task`/`sam_plan`/`sam_active_task`)
and is NOT meant to be converted to CLI form — the file's own text says "The structured MCP
composites remain MCP-only transport names ... and are not CLI commands." Converting that section
would duplicate/contradict the CLI Usage Guide, not fix drift.

## Pattern: don't wholesale-replace MCP examples in files that already have a paired CLI section

Before converting any MCP call-site example to CLI syntax, check whether the same file (or
backend-providers.md) already documents the CLI equivalent in a separate, clearly-labeled section.
If so:
- Fill gaps in the existing CLI section instead of touching the MCP section (e.g.
  TASK_FILE_FORMAT.md's CLI Usage Guide was missing `active-task` entirely — added it there).
- Add a one-line cross-reference from the MCP-reference bullet list to the authoritative CLI
  section, rather than annotating every bullet inline (matches this repo's own convention in
  backend-providers.md: `` `backlog_add` (`backlog add`) ``-style parenthetical, used only in the
  file that owns the mapping).

## Recurring drift patterns found in dh docs (2026-08-05 pass)

- **Deprecated 8-tool names used as if current**: `sam_read`, `sam_list`, `sam_state`, `sam_claim`,
  `sam_ready`, `sam_update`, `sam_create` (bare, non-composite names) were replaced by the 3
  consolidated tools (`sam_task`, `sam_plan`, `sam_active_task` with a `config={"action":...}`
  discriminator) — see TASK_FILE_FORMAT.md's "Deprecated Tools (migration reference only)" table
  for the authoritative replacement mapping. Found stale `sam_state`/`sam_read`/`sam_list` usage
  in AGENTS.md and backlog-lifecycle.md, used as live shorthand rather than migration references.
- **Overstated parity claims**: backend-providers.md's own capability-surface bullets omitted that
  4 operations are only ⚠️ Partial on the CLI: `backlog_list` (no `--search`), `backlog_update` (no
  `verified`/`entry_id`/`replace_section`/`reason`), `backlog_view` (no ordinal-navigation params:
  `map`/`navigate`/`head`/`skip_tokens`/`sections`/`summary`/`include_content`), `sam_plan` create
  (one inline task per call vs MCP's `tasks=[...]` list). Verify against a real, current
  MCP-tool-to-CLI mapping before trusting a doc's "both surfaces" claim — check `--help` output or
  a freshly-built mapping, don't assume an existing capability table is complete.
- **Extraction-rule blind spot for CLI-form call sites**: graph-schema.md's workflow-graph
  assembler rule ("MCP tool nodes are extracted from `mcp_calls[]` strings starting with `mcp__`")
  and prd-workflow-extractor.md's "How MCP tools appear in source" section only recognized MCP
  call syntax (full `mcp__plugin_dh_*__tool(...)` form and short `tool(...)` form), not the CLI
  form (`uv run plugins/development-harness/sam_schema/cli.py <command>`). This is a real gap
  since some workflow reference files (`skills/work-backlog-item/references/workflows/quick/
  start.md`, `create/start.md`, converted in commit 3f8fe38b) now use CLI form for some steps —
  those tool-call edges are currently invisible to the workflow-graph extraction pipeline. Flagged
  but not fixed in the actual extraction script (out of scope — those are doc-only edits; the
  script itself is a separate implementation task).

## Convention: don't touch examples tied to still-unconverted source files

graph-schema.md and prd-workflow-extractor.md contain literal JSON/example strings copied from
specific still-unconverted workflow files (e.g. `groom/swarm.md`, `impact-analyst.md`,
`rt-ica-gate.md`). Leave these as MCP-form — they are accurate citations of the current state of
those source files. Only quick/start.md and create/start.md have been converted to CLI form so
far (as of 2026-08-05); check `git log` / the actual referenced file before assuming any other
workflow file has switched.
