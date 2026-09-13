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

Apply this to EVERY section: features, architecture, installation steps, usage examples, limitations. Numbers, version strings, benchmark figures, and configuration values MUST be quoted verbatim from source — never paraphrased or estimated.

**Relevance values**: Use the exact section names from [Entry Template](./entry-template.md) — Overview, Problem Addressed, Key Features, Technical Architecture, Installation & Usage, Relevance to Claude Code Development, References, Freshness Tracking. This enables the doc-sufficiency check after Phase 1 to filter extracts by section.

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

Read this repo the same way Phase 1 read the resource: extract first, characterise second. Three
steps, budget six Read calls.

1. Derive 3-6 search terms from your own Phase 1 extracts — the mechanisms named in
   `Problem Addressed` and `Key Features`, not the resource's brand name, which by definition
   will not appear here. A browser-automation resource yields `playwright`, `headless`, `browser`,
   `screenshot`, `WebFetch`; a serialization library yields `pydantic`, `dataclass`, `TypedDict`,
   `serializ`. Record which extract each term came from — a term with no extract behind it was
   guessed, not derived, and its result anchors nothing.

   Pair every narrow, resource-specific term with a broader term for the same capability:
   `similarity search` with `embedding`, `reranking` with `vector`. The narrow term is the more
   defensible description of the resource and the less likely to appear here, so searched alone it
   manufactures absences — `similarity search` and `reranking` both return zero in a repo that
   ships `plugins/python3-development/skills/semantic-code-search/SKILL.md`.

2. Search each term over the tracked corpus:

   ```bash
   git grep -il "{term}" -- plugins/ .claude/skills/ .claude/agents/ rules/ docs/ AGENTS.md ':!research/'
   ```

   `git grep`, never plain `grep`. `git grep` searches tracked files only, so it skips
   `.claude/worktrees/` and every other gitignored directory by construction; plain `grep` over
   the same scope returns mostly worktree copies, which lets an entry cite a path that exists in
   no clone and lets the entry being written match itself.

   The scope is the six paths above and no others. Wholesale `.claude/` pulls in gitignored
   `agent-memory/`, `audits/`, `backlog/`, `plan/`, `smells/`, and `reports/`, none of which is in
   any clone; `':!research/'` keeps the research corpus out by any route, since an entry anchored
   to another entry says nothing about the repo. Measured at this writing, the term `refusal`
   returned 43 files under `grep -ril` over `plugins/ .claude/ rules/ docs/ AGENTS.md`, 3 under
   `git grep -il` over that same over-broad scope, and 1 under the command above — and that 1,
   `plugins/plugin-creator/skills/mission-statement/SKILL.md`, is the only one a fresh clone has.

   Record the match count for every term, matched or not.

3. Read matched files and quote one exact line from each. Selection is fixed, not a preference:

   - One Read per term, in the order the terms were derived. The budget is six Reads total; a
     seventh term goes unsearched and is reported.
   - Within a term's match list take the first path of a preferred type — `AGENTS.md`,
     `rules/*.md`, `SKILL.md`, agent definitions — that no earlier term already consumed. Never
     anchor two terms to the same file: four anchors drawn from one document that merely shares CI
     vocabulary is one observation wearing four hats.
   - A term whose match list holds no unconsumed preferred-type path yields no anchor. Record it
     as unanchored and move on; do not fall back to a script or to a file already read.

   The quoted line must contain the search term. A line that does not is evidence about something
   else: a GUI `widget` anchored to a tmux menu widget, or an SDL2 `simulator` anchored to an iOS
   Simulator, clears every other check and states nothing true.

   Reject the quote and take the next match when the line is a frontmatter field (`description:`,
   `name:`, `allowed-tools:`), a bullet in a link list or index table, or a sample argument inside
   a code fence — each carries the term without asserting anything about this repo's behaviour.
   Reject it too when it is not a unique locator: `true`, `3`, or a lone heading word cannot be
   re-found by the reader checking it.

Record anchors alongside the Phase 1 extracts, in this format:

```text
REPO ANCHORS — {resource-name}

A1. Term: {term}  From: {the Phase 1 extract this term came from}
    Path: {repo-relative path}
    Today: "{exact line read from that path, containing the term}"
    Feeds: {which Relevance item}

A2. Terms: {narrow term} + {broader term}  From: {the Phase 1 extract these came from}
    Scope: git grep -il over plugins/ .claude/skills/ .claude/agents/ rules/ docs/ AGENTS.md
    Today: both → 0 matches
    Feeds: {which Relevance item}
```

An absence anchor needs both the narrow term and its broader pair at zero. When the broader term
matches, there is no absence to record — read that file and write a presence anchor instead. An
absence anchor reports that these terms returned nothing in this scope; it never reports that the
capability is missing here. Asserting nonexistence from a keyword search is the defect this pass
exists to stop reproducing, not a shortcut it licenses one layer up.

An A-record carrying neither a quoted line nor a search command is not an anchor. Drop it rather
than writing it into the entry.

Scope of this pass versus the downstream analysis agents: `research-insight-extractor` and
`research-utilization-assessor` run after the entry is written and do the deep repo-grounded work
— gap assessment, confidence scoring, backlog items, integration sketches. This pass does not
duplicate them and must not try to. It finds the paths and quotes the lines; six Reads is its
whole budget. Its output is what those agents start from instead of re-deriving the mapping from
an entry that named nothing.

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
