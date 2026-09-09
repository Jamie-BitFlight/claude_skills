# URL Fetch Specification

## SOURCE: URL Extraction

The upstream drift agent (`plugin-creator:skill-content-updater` in read role) extracts URLs from skill content matching these patterns:

```text
SOURCE: <url> (accessed YYYY-MM-DD)
SOURCE: [Title](url) (accessed YYYY-MM-DD)
SOURCE: url
```

Extract the URL portion (not the surrounding text) for fetching.

## Fetch Behavior

| HTTP Status | First action | If first action fails |
|---|---|---|
| 200 | Assess content (see below) | — |
| 301/302 | Follow redirect, then assess | — |
| 404 | Apply fallback chain (see below) | UNVERIFIABLE after all tiers exhausted |
| 403/401 | Apply fallback chain — 403 often means AI scraping block | UNVERIFIABLE after all tiers exhausted |
| Timeout (>10s) | Apply fallback chain | UNVERIFIABLE after all tiers exhausted |
| DNS failure | UNVERIFIABLE immediately | — |

**Key rule**: Non-200 responses never block the pipeline. Work through the fallback chain, then mark UNVERIFIABLE only when all tiers are exhausted.

## URL Fallback Chain

When a URL returns 404, 403, or times out, apply these tiers in order. Stop at the first tier that returns usable content.

**Tier 1 — Ref MCP**

```
mcp__Ref__ref_read_url(<url>)
```

Handles many docs sites that block direct HTTP clients but respond to Ref.

**Tier 2 — Exa search**

Search for the page title or URL to find the content at its current location (docs sites reorganize between versions):

```
mcp__exa__web_search_exa(query: "site:<domain> <page-title-or-slug>")
```

If Exa returns a new URL for the same content, fetch that URL via `ctx_fetch_and_index` and record the canonical URL in the change plan citation.

**Tier 3 — agent-browser or Claude in Chrome**

For JavaScript-rendered sites that return 403 to headless clients:

Activate `agent-browser` and follow its browser workflow.

or use `mcp__claude-in-chrome__*` tools if a browser session is active. Extract the rendered text content.

**Tier 4 — GitHub repo docs mining**

If multiple URLs from the same domain are failing (pattern: 403 on several pages from one site), the site may be blocking AI scrapers. Docs sites frequently generate from a `docs/` directory in a public GitHub repository.

Detection heuristic:
1. Search for the project's GitHub repo: `mcp__exa__web_search_exa(query: "<project-name> site:github.com docs")`
2. Confirm the repo has a `docs/` or similar directory that matches the URL structure

If confirmed, activate `rwr:doc-to-skill` with the repository URL as `source` and an explicit absent
`output_skill_directory`. Pass the complete source boundary rather than a summary. The conversion
workflow creates a fresh temporary clone, inventories every source file by format and capability,
and promotes a portable skill only after its source-to-output ledger reconciles.
Retain the source/atom coverage ledgers and the complete leaf terminal report, including `STATUS`,
`OUTPUT`, `COVERAGE`, `UNRESOLVED`, `VALIDATION`, `SUPPORT`, and `GUIDANCE`. Proceed with the converted
skill only on `STATUS: DONE`; preserve `DEGRADED` or `BLOCKED` diagnostics as evidence.

Apply Tier 4 when **3 or more** URLs from the same domain fail — not for a single 404 (which is more likely a moved page than a block).

## Content Comparison (200 responses)

1. Locate the section in the fetched page that addresses the same topic as the skill claim
2. Compare semantically — not character-for-character
3. Skill claim matches upstream intent: `VERIFIED`
4. Upstream text supersedes or contradicts skill claim: `STALE` — quote the upstream text in the report
5. Upstream contains new relevant material not in the skill: `NEW` — quote the new text in the report

## Access Date Updates

When including a VERIFIED or STALE claim in the change plan: update the access date in the SOURCE: line to the current date.

## Fetch Responsibilities by Stage

The drift scanner (`skill-content-updater` in read role) fetches only the SOURCE: citation URLs already present in the skill — the URLs it is comparing against upstream docs. It does not fetch docs indexes or validate NEW citation URLs.

Docs-index validation and source content pre-fetch are handled by the `skill-sync-source-validator` agent in Stage 4.5. The write agent (`skill-content-updater` in write role) reads from the source-material file produced by Stage 4.5 and does not fetch any URLs itself.
