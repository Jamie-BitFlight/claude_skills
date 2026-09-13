# Extractive Research Methodology

Extract before abstracting. Every claim in a research entry traces back to a passage pulled
verbatim from a primary source, recorded before any prose is written. Writing a section from
memory, from inference, or from a model's prior knowledge of the resource is FORBIDDEN.

The phases run in order: Phase 1 → Doc-Sufficiency Check → (Phase 1b, conditional) → Phase 2.

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

SOURCE: "Extract before abstracting" methodology from [fidelity-rules.md](./../../../../plugins/summarizer/skills/summarizer/references/fidelity-rules.md) Rule 2 (accessed 2026-03-06). Quote-grounding technique from Anthropic prompt engineering documentation (<https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/long-context-tips>, accessed 2026-02-06).
