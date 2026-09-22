# Improvement Proposals: wigolo

**Research entry**: ./research/mcp-ecosystem/wigolo.md
**Generated**: 2026-09-21
**Patterns assessed**: 5
**Backlog items created**: 2 (references: `p1-mcp-integration-skill-documents-no-configuration-pattern-for`,
`p2-research-curator-agents-tool-list-offers-no-crawl-or-structu` — see [Backlog backend state](#backlog-backend-state))
**Deferred (low confidence)**: 0
**Skipped (already covered or out of scope)**: 3

---

## Backlog backend state

Both items were created through `backlog_add` and are stored in the local backlog cache, but the
GitHub backend returned `403 GitHub GraphQL is not available from Claude Code sessions` on issue
creation, so `item_ref` is empty for both and **no issue numbers were assigned**. The items carry
their slug references instead. Re-run `backlog_sync` (or `backlog_add`'s issue creation path) from
a session where the GitHub backend is reachable to mint the issue numbers.

The same failure disabled the tool-side duplicate check. Duplicate detection was performed instead
by listing all 779 open issues via `gh api repos/Jamie-BitFlight/claude_skills/issues?state=open`
(pages 1–10) and grepping titles for `mcp`, `docker`, `research-curator`, `wigolo`, `web search`,
`fetch`, `plugin-creator`, `transport`, `stdio`, `exa`, `Ref__` — no existing item covers either
proposal. The second `backlog_add` call reported a false-positive duplicate against the first
(degraded cache holding one item) and was re-issued with `force=true`.

---

## Improvement 1: Document the containerized MCP server configuration pattern in the mcp-integration skill

**Source pattern**: Relevance → Applications → "MCP Server Integration and Configuration →
`plugins/plugin-creator/skills/mcp-integration/SKILL.md` … Change: Reference wigolo as a production
MCP server example when documenting MCP configuration patterns, deployment methods (stdio, HTTP,
Docker), and tool integration workflows." Concrete mechanism from the entry's Installation & Usage →
Docker section: `docker run -i --rm -v wigolo-data:/data ghcr.io/knockoutez/wigolo` for stdio, and
`docker run -p 3333:3333 -v wigolo-data:/data -e WIGOLO_API_TOKEN=… ghcr.io/knockoutez/wigolo serve
--host 0.0.0.0` for HTTP.
**Local system**: `plugins/plugin-creator/skills/mcp-integration/SKILL.md` and
`plugins/plugin-creator/skills/mcp-integration/references/server-types-and-patterns.md` (both read)
**Absence evidence**: `git grep -in "docker\|container" -- plugins/plugin-creator/skills/mcp-integration/`
→ 0 matches. `git grep -in "docker\|container\|npx" -- plugins/plugin-creator/skills/mcp-integration/`
→ 1 match, `references/server-types-and-patterns.md:12: "command": "npx"` — the npm-package stdio
example, not a container one.
**Confidence**: High
**Impact**: Medium
**Backlog**: Created — reference `p1-mcp-integration-skill-documents-no-configuration-pattern-for`
(P1, Feature). Issue number pending backend recovery.

### Current state

The skill documents four server types (stdio, SSE, HTTP, WebSocket). Every stdio example assumes
the server is a local executable or an npx-launched npm package:
`references/server-types-and-patterns.md` shows `"command": "npx"` with
`args: ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]`, and
`SKILL.md`'s "Dedicated .mcp.json" example shows `"command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server"`.
`references/server-types-and-patterns.md`'s stdio section states "Best for: file system access,
local database connections, custom MCP servers, NPM-packaged servers" — container distribution is
not in that list and appears nowhere in the skill directory. A plugin author bundling a
container-distributed MCP server therefore has no documented pattern for either of its two shapes:
stdio over `docker run -i`, or an HTTP entry pointing at a separately started local container.

### Target state

`references/server-types-and-patterns.md` gains a container-distribution subsection under stdio,
cross-referenced from its HTTP section, covering: the `docker run -i --rm` invocation expressed as
a `command` + `args` pair in `.mcp.json`; why `-i` is required and `-t` must not be passed (a TTY
breaks JSON-RPC framing over stdio); volume mounting so server-side model/cache state survives
container recreation; and the HTTP variant where the plugin config carries only `url` plus an
`Authorization` header sourced from an environment variable, consistent with the skill's existing
Security Checklist rule "Store tokens in environment variables — never hardcode in config".

### Measurable signal

`git grep -in "docker run -i" -- plugins/plugin-creator/skills/mcp-integration/` returns at least
one match inside a JSON configuration example whose `args` array contains `"-i"`; the same file
states the `-t` prohibition and shows a volume mount; the HTTP section links to that subsection.
`uv run prek run --files plugins/plugin-creator/skills/mcp-integration/references/server-types-and-patterns.md`
passes.

---

## Improvement 2: Give the research-curator agent a crawl / structured-extraction route for multi-page documentation sources

**Source pattern**: Relevance → Applications → "Web Research and Information Gathering →
`.claude/skills/research-curator/SKILL.md` … Change: Integrate wigolo as an optional backend for
research-curator agent's primary source gathering phase; replace manual web search/fetch steps with
tool calls to wigolo's search, fetch, crawl, and extract tools." Concrete mechanisms from Key
Features: `crawl` ("Follow links across a site within configurable depth and page count limits,
useful for large documentation sets") and `extract` (modes `tables`, `structured` — tables +
definition lists + JSON-LD + key-value pairs — or schema-based field extraction).
**Local system**: `.claude/agents/research-curator.md` (the `<research_tools>` block; read). The
Relevance item names `.claude/skills/research-curator/SKILL.md`, which was also read — that file is
the orchestrator (mode routing, relay rules, post-actions) and holds no tool list, so the gap lands
on the agent file it spawns.
**Absence evidence**: `git grep -in "crawl\|structured extraction\|local cache\|vector" --
.claude/agents/research-curator.md .claude/skills/research-curator/` → 1 match, and it is unrelated:
`references/extraction-methodology.md:148`, a term-pairing example listing `vector` as a search
synonym. `git grep -n "WebFetch\|WebSearch\|ref_search_documentation\|ctx_fetch_and_index" --
.claude/agents/research-curator.md .claude/skills/research-curator/` → 3 matches, all in the
search/read family. `git grep -il "wigolo" -- .` → 1 match, `research/README.md` (the entry's own
index row), confirming no existing wiring.
**Confidence**: High
**Impact**: Low
**Backlog**: Created — reference `p2-research-curator-agents-tool-list-offers-no-crawl-or-structu`
(P2, Feature). Issue number pending backend recovery.

### Current state

`.claude/agents/research-curator.md`'s `<research_tools>` block lists three gathering routes:
documentation search/read (`mcp__Ref__ref_search_documentation`, `mcp__Ref__ref_read_url`),
web/code search (`mcp__exa__web_search_exa`, `mcp__exa__get_code_context_exa`), and shallow repo
clone (`git clone --depth 1 {repo-url} ./.worktrees/{repo-name}/`, the documented preferred route).
Nothing in the block follows links across a site within a page budget, and nothing pulls structured
records (HTML tables, JSON-LD, definition lists, key-value blocks) out of a page. The agent's own
workflow diagram has a "Website/docs → Gather via MCP search + read" branch, so a hosted
documentation set with no associated repo is researched page-by-page, and every table-shaped fact
(config variable tables, pricing tiers, compatibility matrices) is transcribed by the agent from
rendered markdown rather than extracted — the transcription path `research/CLAUDE.md` warns about
under "Fabrication reads as plausible, not as wrong".

### Target state

`<research_tools>` carries a fourth, explicitly optional route for multi-page crawl and
schema/table extraction, written under the block's existing precondition ("Check the `<functions>`
list in your system prompt for current MCP tool availability before using any tool. Not all tools
may be available in every session"). It names the tool surface (crawl with depth/page caps; extract
with `tables` / `structured` / schema modes), states when to prefer it over per-page `ref_read_url`
(docs site with no associated repo AND the needed facts are table-shaped or span more than ~3
pages), states the fallback when the tool is absent, and carries the adoption caveats so no reader
installs it unaware: AGPL with commercial use requiring a separate license (entry: Limitations →
"Licensing for commercial use"), Node ≥ 20, ~1.5 GB on-device models, and not currently installed
in this repo.

### Measurable signal

`git grep -in "crawl" -- .claude/agents/research-curator.md` returns a match inside the
`<research_tools>` block; that block states both the availability precondition and the absent-tool
fallback; the AGPL/commercial-license caveat appears alongside it.
`uv run prek run --files .claude/agents/research-curator.md` passes.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| (none) | | Every actionable gap assessed reached High confidence; no proposal was deferred on confidence. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Local-First, Zero-Key Design (Patterns Worth Adopting) | The entry itself resolves this to "Out of scope — this repo documents agent capabilities and skills, not architecture patterns for third-party tools", with its own two `git grep` searches returning 0 matches. No local system to extend. |
| Browser Automation and Headless Testing (Integration Opportunities) | The entry's "Change: None" rests on the claim "this repo does not currently implement browser automation". That claim is wrong for this checkout: `.claude/skills/agent-browser/` exists (`SKILL.md`, `references/commands.md`, `references/authentication.md`, `references/profiling.md`, `references/proxy-support.md`), and `AGENTS.md`'s Situational Rule Triggers routes garbled terminal-browser output to it. The entry's narrow search terms (`"browser pool\|browser automation"`) missed it. Outcome is unchanged — browser work is already covered locally, so wigolo's pool stays external — but the reasoning in the entry should be corrected on its next refresh. |
| Honest failure labeling: `blocked_by_challenge` / degraded-backend reporting instead of content shells | Already implemented, and more strictly, in `.claude/skills/research-curator/SKILL.md` → "Agent Result Relay Rules" → Rule 2 ("Preserve failure reasons"), whose table forbids relaying "HTTP 403 Forbidden" as "not available" or "Rate limited" as "unavailable", plus Rule 1 (preserve exact counts) and Rule 5 (observations vs conclusions). No gap. |
| `npx wigolo doctor` component health check before first use | Covered in spirit by `<research_tools>`'s standing instruction in `.claude/agents/research-curator.md` to check the `<functions>` list for tool availability before use. Also outside the entry's Relevance/Patterns/Integration sections, so not a grounded proposal. |
