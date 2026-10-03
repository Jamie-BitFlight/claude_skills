# Extractive Research Methodology

Extract before abstracting. Every claim in a research entry traces back to a passage pulled
verbatim from a primary source, recorded before any prose is written. Writing a section from
memory, from inference, or from a model's prior knowledge of the resource is FORBIDDEN.

The phases run in order: Phase 1 → Doc-Sufficiency Check → (Phase 1b, conditional) → Phase 1c → Phase 2.

Phases 1 and 1b extract from the resource being researched. Phase 1c extracts from this repo. A
`Relevance to Claude Code Development` section written without Phase 1c has nothing real to name,
and degrades into claims true of any repository and checkable against none.

The content bar each written section must then clear is in [Entry Quality Standards](./entry-quality-standards.md).

---

## Phase 1: Extract Key Passages

BEFORE writing any section of the entry, extract relevant quotes and data points from primary sources. Record each extract with its source.

Use this format during extraction (internal working notes, not written to the entry file):

```text
EXTRACTED PASSAGES — {resource-name}

1. "{exact quote or data point}"
   Source: {URL or tool + section}
   Relevance: {which entry section this feeds}

2. "{exact quote or data point}"
   Source: {URL or tool + section}
   Relevance: {which entry section this feeds}
```

Apply this to EVERY section: features, architecture, installation steps, usage examples, limitations. Numbers, version strings, benchmark figures, and configuration values MUST be quoted verbatim from source — never paraphrased or estimated. Star, download, fork, and contributor counts are the exception (Rule 2a): never extract them, including from badges and quoted passages.

**Relevance values**: Use the exact section names from [Entry Template](./entry-template.md) — Overview, Problem Addressed, Key Features, Technical Architecture, Installation & Usage, Limitations and Caveats, Relevance to Claude Code Development, References, Freshness Tracking. This enables the doc-sufficiency check after Phase 1 to filter extracts by section.

---

## Doc-Sufficiency Check

Run immediately after Phase 1 completes. Record the result as a working note — do NOT write it to the entry file.

1. Scan your Phase 1 extracts tagged with `Relevance: Technical Architecture` or `Relevance: Key Features`.
2. Answer each question YES or NO:
   - Q1: Do any extracts name at least 2 specific component, module, or class names (not generic descriptions like "has a plugin system")?
   - Q2: Do any extracts describe how data or control flows between at least 2 named components (not generic statements like "processes data")?
   - Q3: Do any extracts name an extension point, plugin interface, hook system, or registration mechanism with its concrete API?
3. If ANY answer is NO: record working note "Architecture depth requirements unsatisfied — triggering code analysis" and proceed to Phase 1b.
4. If ALL answers are YES: record working note "Architecture depth requirements satisfied from docs" and skip to Phase 2.

`--rerun` runs this same check against the re-extracted passages, with the same two outcomes.

---

## Phase 1b: Code Analysis (conditional)

This phase triggers ONLY when the doc-sufficiency check recorded "Architecture depth requirements unsatisfied — triggering code analysis". It reads source files from the shallow clone to extract architectural evidence that documentation did not provide.

**Phase 1b Procedure** (when triggered):

1. **Detect primary language**: Check for `pyproject.toml` (Python), `package.json`
   (Node.js/TypeScript), `Cargo.toml` (Rust), `go.mod` (Go), `pom.xml` / `build.gradle`
   (Java/Kotlin). If none found, count file extensions via Glob to determine the dominant
   language.

2. **Read files in tier order** — stop at 12 files total:

   **Tier 1 — Entrypoints** (read these first):

   - Python: `**/main.py`, `**/cli.py`, `**/app.py`, `**/__main__.py`, `**/server.py`, `**/wsgi.py`, `**/asgi.py`
   - Node/TS: `**/index.ts`, `**/index.js`, `**/main.ts`, `**/main.js`, `**/app.ts`, `**/app.js`, `**/server.ts`, `**/server.js`
   - Go: `**/main.go`, `**/cmd/**/main.go`
   - Rust: `**/main.rs`, `**/lib.rs`
   - Java/Kotlin: `**/Application.java`, `**/Main.java`, `**/App.kt`
   - Ruby: `**/config.ru`, `**/Rakefile`, `**/bin/*`

   **Tier 2 — Type/schema declarations** (read after Tier 1):

   - Python: `**/models.py`, `**/schema.py`, `**/schemas.py`, `**/types.py`, `**/models/*.py`
   - Node/TS: `**/types.ts`, `**/types.d.ts`, `**/schema.ts`, `**/models/*.ts`, `**/interfaces.ts`
   - Go: `**/types.go`, `**/models.go`
   - Rust: `**/types.rs`, `**/models.rs`, `**/schema.rs`
   - Any language: `**/*.proto`, `**/openapi.yaml`, `**/openapi.yml`, `**/openapi.json`, `**/schema.graphql`, `**/schema.json`

   **Tier 3 — Index/barrel files** (read last):

   - Python: `**/__init__.py` (top-level package directories only — skip deeply nested), `**/api.py`, `**/routes.py`, `**/urls.py`
   - Node/TS: `**/index.ts` (in subdirectories — barrel exports), `**/exports.ts`
   - Go: `**/doc.go`
   - Rust: `**/mod.rs`
   - Any language: `**/plugin.py`, `**/plugins/*.py`, `**/extensions/*.ts`, `**/middleware/*.py`, files matching `**/register*`

   **Exclusions** — never read:

   - Test files: `**/test_*.py`, `**/*_test.go`, `**/*.test.ts`, `**/*.spec.ts`, `**/*_test.*`, `**/*.test.*`
   - Dependency dirs: `**/node_modules/**`, `**/.venv/**`, `**/vendor/**`, `**/__pycache__/**`
   - Build artifacts: `**/*.min.js`, `**/*.bundle.js`, `**/dist/**`, `**/build/**`, `**/target/**`
   - Files over 500 lines: skip and note "Skipped {path}: {N} lines (over 500-line limit)"

   **Selection within a tier**: Prefer files in `src/` over root. Prefer shorter paths over
   deeper paths. Read each file fully (do not use line limits). Increment the file counter after
   each Read. Stop when counter reaches 12 or all tiers are exhausted. Record how many candidate
   files remain unread when budget is exhausted.

3. **Extract architectural evidence** from each file read. Record extracts using this format:

   ```text
   N. "{exact code passage — class definition, function signature, import block, or schema}"
      Source: {relative-path}:{start-end lines} — {exported name}
      Relevance: Technical Architecture | Key Features
      Confidence: code-read
   ```

   Focus extraction on:

   - Class/struct definitions with their public methods (architecture)
   - Function signatures that reveal data flow (architecture)
   - Import statements that reveal component dependencies (architecture)
   - Schema/model field definitions (architecture)
   - Registration patterns — decorators, register() calls, plugin lists (extension points)
   - Configuration handling that reveals supported options (features)

4. **Merge code extracts with Phase 1 extracts**. Both sets feed into Phase 2 identically.
   Code extracts are distinguished only by their `Confidence: code-read` tag.

Entries carrying code-derived claims cite them inline and qualify their confidence — formats in [Entry Template](./entry-template.md).

---

## Phase 1c: Repo Anchor Pass

Unconditional — runs for every entry, after Phase 1 (and Phase 1b when it triggered) and before
Phase 2. It produces the anchor records that the `Relevance to Claude Code Development` section is
written from, and nothing else in the entry depends on it.

Its purpose: record what technology the resource offers that may overlap with what this repo builds
now or later, and which repo system or goal each capability touches, so the repo can reduce
friction, maintenance overhead, and gaps. Read this repo the same way Phase 1 read the resource:
extract first, characterise second.

1. Derive **capabilities** from your own Phase 1 extracts — the mechanisms named in
   `Problem Addressed` and `Key Features`, not the resource's brand name, which by definition will
   not appear here. Record which extract each came from; a capability with no extract behind it was
   guessed, not derived, and its result anchors nothing.

2. Search the repo for each capability by meaning, with the best tools this environment offers.
   Discover them at run time: check the skills, plugins, and MCP servers available to you,
   including `ccc` (CocoIndex semantic code search, `.claude/skills/ccc`) and graphify, and use
   every one that works. Fall back to Grep, Glob, `git grep`, or reading files when none do. Query
   with the capability and its synonyms, not only the resource's name. How you search is yours to
   choose. Record each tool, query, and result in a working note; step 3's records draw only from it.

   Hits under gitignored paths (`.worktrees/`, `.claude/worktrees/`) and under `./research/` are not
   evidence of what this repo instructs — an entry cannot anchor to another entry.

3. Open the files the searches surface and quote one exact body line from each that supports the
   claim you make about it. A line that matches the query's words but concerns something else — a
   GUI `widget` anchored to a tmux menu widget — states nothing true. Skip a line that is a
   frontmatter field (`description:`, `name:`, `allowed-tools:`), a bullet in a link list or index
   table, or a sample argument inside a code fence: each carries the words without asserting
   anything about this repo's behaviour. Skip one that cannot be re-found, such as `true`, `3`, or a
   lone heading word. Never anchor two capabilities to the same file: four anchors drawn from one
   document is one observation wearing four hats.

4. For each capability, record the repo goal or system it overlaps and what could change.

Record anchors alongside the Phase 1 extracts, in this format:

```text
REPO ANCHORS — {resource-name}

A1. Capability: {capability}  From: {the Phase 1 extract it came from}
    Found by: {tool} — {query}
    Path: {repo-relative path}
    Today: "{exact body line read from that path that supports the claim}"
    Overlaps: {repo system or goal this touches}
    Feeds: {which Relevance item}

A2. Capability: {capability}  From: {the Phase 1 extract it came from}
    Found by: {tool} — {query}   (one line per search run)
    Today: nothing relevant returned
    Overlaps: {repo system or goal this would touch}
    Feeds: {which Relevance item}
```

An absence record says "not found by these searches" and lists every tool and query run, copied from
step 2's working note — never a result you did not observe. It never says the capability is missing
from this repo (Rule 3). When any search returned a relevant file, read it and write a presence
anchor instead.

A record carrying neither a quoted line nor recorded searches is not an anchor; drop it.

Scope of this pass versus the downstream analysis agents: `research-insight-extractor` and
`research-utilization-assessor` run after the entry is written and do the deep repo-grounded work
— gap assessment, confidence scoring, backlog items, integration sketches. This pass does not
duplicate them. It finds the paths and quotes the lines; its output is what those agents start from
instead of re-deriving the mapping from an entry that named nothing.

---

## Phase 2: Write From Extracts

Write each entry section by organizing the extracted passages for that section, then composing prose or structured content grounded in those extracts.

REQUIRED verification step: Before finalizing a section, confirm that every factual claim in that section traces to at least one extracted passage. If a claim cannot be traced, either find a source passage or remove the claim.

---

## What Counts as a Claim Requiring a Source

- Version numbers ("v2.3.1")
- Performance figures ("processes 10k events/sec")
- Feature descriptions ("supports async/await")
- License type
- Architectural assertions ("uses a DAG-based task graph")
- Installation commands (verify against official docs, not inferred)
- Compatibility statements ("requires Python 3.11+")
- Any statement about this repository ("`rules/` has no worktree guidance", "`parallel-work`
  already covers fan-out") — sourced by a Phase 1c anchor, quoted line or search command, never by
  recall of what a repo like this usually contains

SOURCE: "Extract before abstracting" methodology from [fidelity-rules.md](./../../../../plugins/summarizer/skills/summarizer/references/fidelity-rules.md) Rule 2 (accessed 2026-03-06). Quote-grounding technique from Anthropic prompt engineering documentation (<https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/long-context-tips>, accessed 2026-02-06).
