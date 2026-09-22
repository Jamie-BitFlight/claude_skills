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
steps. Searching is unbudgeted — `git grep` is a Bash call, so search every term. Reading is
capped at six Read calls, and the cap falls entirely on step 3.

1. Derive 3-6 **capabilities** from your own Phase 1 extracts — the mechanisms named in
   `Problem Addressed` and `Key Features`, not the resource's brand name, which by definition will
   not appear here. Record which extract each came from; a capability with no extract behind it was
   guessed, not derived, and its result anchors nothing.

   Give each capability two search terms: the narrow, resource-specific one and a broader one for
   the same idea — `similarity search` with `embedding`, `reranking` with `vector`, `playwright`
   with `browser`. Both are terms and both get searched, so 3-6 capabilities means 6-12 searches.
   The narrow term is the more defensible description of the resource and the less likely to appear
   here, so searched alone it manufactures absences: `similarity search` and `reranking` both
   return zero in a repo that ships
   `plugins/python3-development/skills/semantic-code-search/SKILL.md`.

2. Search every term — both halves of every capability, no exceptions and no budget:

   ```bash
   git grep --full-name -il "{term}" -- :/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md
   ```

   The `:/` on every pathspec and the `--full-name` are load-bearing. Git resolves a bare pathspec
   against the current directory, so the same command without `:/`, run anywhere below the
   repository root, resolves all six paths to nothing and exits 1 printing no message — a
   manufactured absence on every term, indistinguishable in the output from a real one. `:/`
   anchors each path to the repository root wherever the command runs, and `--full-name` makes the
   output repo-relative so an anchor record's path is usable exactly as printed.

   `git grep`, never plain `grep`, and the scope is those six paths and no others — two separate
   constraints, neither doing the other's job. Measured on the term `refusal` in the primary
   checkout: plain `grep -ril` over `plugins/ .claude/ rules/ docs/ AGENTS.md` returns 73 files,
   `git grep -il` over that same over-broad scope returns 3, and the command above returns 1. The
   73→3 is plain `grep` descending into gitignored `.claude/worktrees/`, which holds more files
   than the rest of the repo combined — paths no clone has, and a route for the entry being
   written to match itself. The 3→1 is the narrowed scope dropping `.claude/agent-memory/`,
   `.claude/audits/`, and `.claude/plan/`: agent scratch output recording what some past agent did,
   not what this repo instructs, and containing tracked files, so `git grep` reaches them and only
   the pathspec excludes them. Over the six paths alone both commands return the same single file,
   so do not read the `git grep` rule as covering the narrowing — it is the backstop that keeps an
   untracked file from becoming an anchor.

   `research/` needs no exclusion and gets none: it lies under none of the six paths, so the corpus
   is already out of scope and an entry cannot anchor to another entry.

   Record the match count for every term, matched or not, in a working note that pairs the exact
   term string with the integer the command actually printed — the number of lines in its output,
   or 0 when `git grep` exits 1. This working note is the only source step 3's A2 records draw
   from: every term and count written into an A2 record must be copied from this note verbatim, so
   the recorded term set can never diverge from the term set actually searched.

3. Read matched files and quote one exact line from each. At most six Reads, and selection is
   fixed, not a preference:

   - Work capabilities in the order derived, at most one anchor each. Six Reads is the only
     budget; a capability is not separately capped at one, because the rejection rule below can
     spend a Read on a file that yields no usable line. Stop at the sixth Read; report any
     capability left unanchored and why.
   - A capability whose narrow term matched uses the narrow term's match list. When only the
     broader term matched, use the broader term's list, and the quoted line must then contain the
     broader term — whichever term produced the list is the term the line must carry.
   - Within that list take paths in `git grep`'s own output order, preferring a `.md` file over a
     script or data file, and among `.md` files preferring `AGENTS.md`, then `rules/*.md`, then
     `SKILL.md` and agent definitions, then any other `.md` (`docs/`, `references/`). Skip any path
     an earlier capability already consumed. Never anchor two capabilities to the same file: four
     anchors drawn from one document that merely shares CI vocabulary is one observation wearing
     four hats.
   - A capability whose list holds no unconsumed `.md` path yields no anchor. Record it as
     unanchored and move on; do not fall back to a script or to a file already read.

   The quoted line must contain the term that produced the list. A line that does not is evidence
   about something else: a GUI `widget` anchored to a tmux menu widget, or an SDL2 `simulator`
   anchored to an iOS Simulator, clears every other check and states nothing true.

   Reject a line and take the next line *in the same file* when it is a frontmatter field
   (`description:`, `name:`, `allowed-tools:`), a bullet in a link list or index table, or a sample
   argument inside a code fence — each carries the term without asserting anything about this
   repo's behaviour. Reject it too when it is not a unique locator: `true`, `3`, or a lone heading
   word cannot be re-found by the reader checking it. When no line in the file qualifies, that file
   is spent: move to the next path in the list, which costs another Read against the six.

Record anchors alongside the Phase 1 extracts, in this format:

```text
REPO ANCHORS — {resource-name}

A1. Capability: {capability}  From: {the Phase 1 extract it came from}
    Term matched: {the term that produced this match list — narrow or broader}
    Path: {repo-relative path}
    Today: "{exact line read from that path, containing that term}"
    Feeds: {which Relevance item}

A2. Capability: {capability}  From: {the Phase 1 extract it came from}
    Today: git grep --full-name -il "{narrow term}" -- :/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md → {narrow term match count} matches
           git grep --full-name -il "{broader term}" -- :/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md → {broader term match count} matches
    Feeds: {which Relevance item}
```

`{narrow term match count}` and `{broader term match count}` are the integers step 2's working
note actually recorded for those two exact terms — never a default of 0 typed in without having
run the command. Write both commands into an A2 record in full, every `:/` prefix included, with
each command's own count copied verbatim next to it. A recorded scope that does not reproduce the
command actually run is not re-runnable, which is the only property an absence anchor has — and a
reader who re-runs a copy with the `:/` prefixes stripped, from a subdirectory, gets a clean zero
that confirms nothing. A written count that disagrees with what the command actually returns is
now mechanically detected, not just reviewer-detectable: `validate_research.py`'s
`relevance_absence_anchor_refuted` check re-executes every A2 command in the checkout and fails the
entry when the recorded count and the command's real output disagree.

An absence anchor needs both the narrow term and its broader pair at zero. When the broader term
matches, there is no absence to record — read that file and write a presence anchor instead. An
absence anchor reports that these two terms returned nothing in this scope; it never reports that
the capability is missing here. Asserting nonexistence from a keyword search is the defect this
pass exists to stop reproducing, not a shortcut it licenses one layer up.

An A-record carrying neither a quoted line nor a search command is not an anchor. An A2 record
whose count was not copied from step 2's working note — including a count guessed or copied from
a template rather than observed — is not an anchor either. Drop it rather than writing it into the
entry.

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
