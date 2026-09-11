# Improvement Proposals: zvec-grep

**Research entry**: ./research/ai-research-tools/zvec-grep.md
**Generated**: 2026-09-11
**Patterns assessed**: 7
**Backlog items created**: 2 — `p1-semantic-code-search-routes-lexical-and-semantic-search-as-m`, `p1-codebase-analyzer-gates-its-primary-search-tool-on-an-unveri`
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 3

> **Backlog sync note (2026-09-11)**: both items were stored in the backlog, but GitHub issue
> creation failed for each with `GitHub GraphQL is not available from Claude Code sessions`, so
> neither carries an issue number yet. They are addressable by the slug references above. Run
> `mcp__plugin_dh_backlog__backlog_sync` (or `backlog_pull`) from a session with REST-backed issue
> creation to assign numbers, then replace the slugs here.

---

## Improvement 1: semantic-code-search routes lexical and semantic search as mutually exclusive, with no combined path for cross-file questions

**Source pattern**: "Hybrid Search with Multiple Retrieval Paths" — `zg --fts "loadTheme" --vector "where user prefs are restored" --fuse` combines multiple groups and fuses results into a single ranked output; the entry's Problem Addressed section quotes the README: "zg works best when evidence spans files or modules and the target location is unknown, especially for call-chain, data-flow, and architectural questions."
**Local system**: `/home/user/claude_skills/plugins/python3-development/skills/semantic-code-search/SKILL.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: created as `p1-semantic-code-search-routes-lexical-and-semantic-search-as-m` (P1, Feature) — GitHub issue number pending, see sync note above

### Current state

`semantic-code-search/SKILL.md` is an 18-line file whose entire routing rule is line 14:

> Prefer Grep/Glob when you know exact identifiers, filenames, or string literals. Prefer semantic search when you know what the code *does* but not what it's *called*.

This is a two-branch exclusive router keyed on one variable — whether the agent knows the identifier. It has no third branch, and the "when to use" list at lines 9-12 (search by meaning, explore unfamiliar parts, find implementations without exact names, find similar patterns) describes only single-path semantic use.

The question shape zvec-grep names as its best case — evidence spanning files or modules where the target location is unknown (call-chain, data-flow, architectural questions) — is not addressed by either branch. An agent holding a partial identifier *and* a behavioral description is instructed to pick one path, not to run both and reconcile.

The agent wrapper at `/home/user/claude_skills/plugins/python3-development/agents/semantic-code-search.md` line 9 reinforces the exclusivity from the other direction: "If the tool is unavailable, report BLOCKED — do not fall back to pattern-based search."

Note on partial coverage: `/home/user/claude_skills/plugins/development-harness/agents/codebase-analyzer.md` does show both paths side by side per focus area (e.g. its "For conventions focus" block pairs `ccc search error handling exception raise catch` with `Grep(pattern="raise |except |try:")`), and its Search Tool Priority (line 118) says to use Grep "after ccc narrows the search space". That is a sequential narrowing recipe inside one agent, not a routing rule in the skill that owns the decision — and it exists only in that agent, not in the skill other callers load.

### Target state

`semantic-code-search/SKILL.md` carries a third routing branch for the cross-file / unknown-location question shape, stating that both retrieval paths run and their results are reconciled rather than one being chosen. The branch names the question shapes that trigger it (call-chain, data-flow, architectural / "where does X end up" questions) and says what reconciliation means for the agent: run the semantic query, run the lexical query for any identifier fragment in hand, and treat a file surfaced by both as higher-confidence than one surfaced by either alone.

### Measurable signal

- `grep -c 'Prefer' /home/user/claude_skills/plugins/python3-development/skills/semantic-code-search/SKILL.md` — the file contains a branch beyond the two `Prefer ...` sentences on line 14.
- `grep -n 'call-chain\|data-flow\|both' /home/user/claude_skills/plugins/python3-development/skills/semantic-code-search/SKILL.md` returns at least one match in a routing branch.
- The new branch states a reconciliation rule, verifiable by reading the file: an instruction covering what to do when the two paths return overlapping or disjoint file sets.

---

## Improvement 2: codebase-analyzer gates its primary search tool on an unverifiable freshness judgment with no index-state probe

**Source pattern**: "Index Refresh Strategies" (`--refresh wait` / `background` / `off`) and the CLI's `zg --status [root]`: "Inspect index state and readiness."
**Local system**: `/home/user/claude_skills/plugins/development-harness/agents/codebase-analyzer.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: created as `p1-codebase-analyzer-gates-its-primary-search-tool-on-an-unveri` (P1, Refactor) — GitHub issue number pending, see sync note above

### Current state

`codebase-analyzer.md` line 116 makes `ccc search` the highest-priority exploration tool and conditions its correctness on a judgment the agent cannot evaluate:

> 1. **ccc search** — semantic search for concepts, behaviors, and patterns across the full codebase. Preferred for "find all places that do X" questions. Requires the index to be current — run `ccc index` at session start if the codebase has changed recently.

"if the codebase has changed recently" is not observable from anything the agent has. There is no probe named, no threshold, and no stated behavior for the stale case. A stale index returns a well-formed, ranked, confidently-worded result set that silently omits code added since the last index run — and that result set feeds the PATTERNS.md / ARCHITECTURE.md artifacts the agent registers (Step 4: Register Artifact), which downstream stages then read as authoritative.

A readiness probe pattern already exists elsewhere in the repo but checks a different condition. `/home/user/claude_skills/plugins/development-harness/skills/codebase-auditor/SKILL.md` lines 60-63 run `ccc search "test" --limit 1` and, on `"Not in an initialized project directory"`, run `ccc init` then `ccc index`. That detects *absence* of an index, not *staleness* of one — an index built a hundred commits ago passes that probe.

zvec-grep makes both states first-class: `zg --status` reports index state and readiness as data, and `--refresh wait|background|off` makes the stale-index policy an explicit, named choice rather than an unstated default.

Relationship to existing backlog: issue #1042 ("feat: Incremental commit-anchored codebase analysis") covers staleness of the *analysis artifact* — storing `commit_sha` on `ArtifactEntry` and diffing `{sha}..HEAD` so unchanged files are not re-analyzed. Its acceptance criteria name only `backlog_core/models.py`, `artifact_list`, and the differential-analysis path; none touch `ccc index` or search-index currency. This proposal is about the search index that feeds the analysis, not the artifact the analysis produces. The two are adjacent and should reference each other.

### Target state

`codebase-analyzer.md`'s Search Tool Priority replaces the "if the codebase has changed recently" judgment with a probe-and-policy step the agent can execute and report: a named command that reads index state, a stated rule for what counts as stale, and a stated action for each outcome (proceed, reindex first, or proceed and record the search as index-limited in the artifact). The agent's Step 5 return records which outcome occurred, so a consumer of the artifact can tell whether its findings rest on a current index.

### Measurable signal

- `grep -n 'if the codebase has changed recently' /home/user/claude_skills/plugins/development-harness/agents/codebase-analyzer.md` returns no match.
- The Search Tool Priority section names a concrete command whose output the agent reads to decide, and states an action for each outcome — verifiable by reading lines around 112-120.
- The agent's structured return (Step 5: Return Confirmation) includes an index-state field, so a run of the agent produces output naming whether the index was current, was rebuilt, or was used stale.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Symbol-aware retrieval and symbol-type filtering (`--prefer-symbol`; restrict to `module`/`class`/`interface`/`function`/`value`/`alias`) | Medium | The gap is inferred, not observed. `mcp__cocoindex-code__search`'s parameter surface was not read — cocoindex-code is described as AST-based, so equivalent filtering may already be exposed and simply undocumented in `semantic-code-search/SKILL.md`. To raise: read the tool schema for `mcp__cocoindex-code__search` and confirm whether symbol-type narrowing is available but unmentioned (a docs gap) or absent (a capability gap). |
| Local-first embedding with an explicit `--allow-remote` data-egress gate before workspace content leaves the machine | Medium | The pattern is clear in the research entry and `AGENTS.md`'s Security Considerations covers credentials but states no rule about workspace content reaching an embedding provider. Whether a gap exists depends on whether cocoindex-code embeds locally or calls out, which was not verified. To raise: determine cocoindex-code's embedding path from its own source, then check whether any repo rule governs workspace-content egress. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Time-based filtering (`--modified-before` / `--modified-after`) to scope search to recent changes | Already covered. `codebase-analyzer.md` line 117 makes git-forensics MCP the second-priority tool specifically for "co-change analysis and hot spot detection ... churn that Grep cannot find" — recency-scoped discovery is an existing, stronger path (it ranks by change coupling, not just a timestamp cutoff). |
| One-command multi-agent MCP registration (`zg --install --target claude\|codex\|qwen\|qoder\|opencode\|cursor\|all` writing into each agent's config file) | Architecturally incompatible, and the incompatibility is deliberate. `/home/user/claude_skills/docs/cross-harness-smoke-tests.md` ("Common to every harness", step 1) requires installing "through that harness's own install mechanism (not the authoring checkout — an installed consumer is the point of the test)". A self-install path that writes harness config directly would bypass the exact mechanism the repo's verification depends on. |
| Production MCP server implementation patterns — HTTP transport, tool schemas, error handling, authentication | Too abstract to express as an observable before/after state. The research entry's Relevance point 2 says these are "useful patterns" without naming a specific mechanism absent from `plugins/fastmcp-creator/`; no concrete target state can be written from it without first inventing the requirement. |
