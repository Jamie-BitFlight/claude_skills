# Research Entry Quality Standards

The content contract every research entry under `./research/` must satisfy, whoever writes it.

Two halves, always consulted together:

- **Fidelity Rules** govern each individual claim — where it came from, how precisely it is stated, and how confident the entry is in it.
- **Depth Requirements** govern each section's coverage — how much a section must say before it counts as written.

Reviewing a finished entry rather than writing one? Use [Entry Review Rubric](./entry-review-rubric.md), which turns both halves into discrete checks.

---

## Fidelity Rules

<fidelity_rules>

### Rule 1: Read Before Writing

NEVER describe a resource based on its name, URL path, or domain alone. ALWAYS fetch and read primary sources before writing any section.

If a source cannot be accessed: write "Unable to access [source]: [reason]" in the entry's References section. Do NOT infer content.

### Rule 2: Preserve Counts and Specifics

Write exact numbers as found in primary sources when the number describes what the resource
does or how well it does it. NEVER substitute vague quantifiers for a capability figure.
Popularity metrics (stars, downloads, forks) are out of scope entirely — see Rule 2a.

| Source Says | Write | NEVER Write |
|-------------|-------|-------------|
| "supports 12 languages" | "supports 12 languages" | "many languages" |
| "v0.8.2, released 2025-11-03" | "v0.8.2 (released 2025-11-03)" | "recent release" |
| "benchmark: 45ms p99 latency" | "45ms p99 latency" | "low latency" |

### Rule 2a: No Popularity Statistics

Do NOT gather or write star counts, download counts, fork counts, or contributor counts.
These describe how popular a resource is, not what it does, how it does it, or why it's
valuable — they don't inform the review or utility judgments this entry exists to support,
and a reader can query them programmatically at any time via `gh api repos/{owner}/{repo}`
if genuinely needed. There is no "Key Statistics" section in the entry template; do not
add one, and do not fold this data into another section.

This rule binds gathering as well as writing: it applies whether the repository is in the
session's authorized GitHub scope or out of it, and no fallback source (web search, package
registry, a badge in the README) makes the data in scope.

### Rule 3: Distinguish Absence from Nonexistence

Use precise language when information is not found in sources.

| Situation | Write | NEVER Write |
|-----------|-------|-------------|
| Searched but not in source | "Not mentioned in documentation" | "Doesn't support X" |
| Source inaccessible | "Unable to access [source]" | "Not available" |
| Source doesn't cover topic | "Outside the scope of reviewed sources" | "Not supported" |
| Contradictory sources | "Source A states X; Source B states Y" | "The answer is X" |

### Rule 4: State Confidence Explicitly

Each major section of the entry MUST have a confidence level. Record this in the entry's Freshness Tracking section as a confidence map.

**Confidence levels**:

- `high` -- full primary source read, official documentation, recent and dated
- `medium` -- partial read, informal source, or single source with no corroboration
- `low` -- inferred, dated source (>12 months), or source conflict

**Factors that reduce confidence**: source truncated, source is informal (blog post vs official docs), sources contradict each other, content required interpretation rather than extraction.

**Factors that increase confidence**: full read of official documentation, multiple sources agree, content is structured/machine-readable (API spec, package manifest), source is dated and recent.

Confidence qualifiers for code-derived claims (`(code-read)`, `(doc + code-read)`) are defined in [Entry Template](./entry-template.md).

SOURCE: Confidence scoring methodology from [fidelity-rules.md](./../../../../plugins/summarizer/skills/summarizer/references/fidelity-rules.md) Rule 6 (accessed 2026-03-06).

</fidelity_rules>

---

## Depth Requirements

<depth_requirements>

Research entries MUST go beyond surface-level feature lists. Each entry section has a minimum depth requirement.

### Architecture Section — REQUIRED depth

Do NOT write "uses a plugin-based architecture" without explaining what that means concretely. MUST include:

- Core components and their relationships (with exact names from source)
- Data flow or execution model
- Key design decisions and their stated rationale (if documented)
- Extension or integration points

### Features Section — REQUIRED depth

For each documented feature:

1. State what it does (extracted from source)
2. State HOW it does it — the mechanism, not just the outcome
3. Include a concrete example if the source provides one
4. Note any configuration or constraints

### Usage Examples Section — REQUIRED depth

MUST include at least one complete, working example extracted verbatim or adapted minimally from official documentation. Examples invented without a source basis are FORBIDDEN.

For installation commands: verify the exact command from official docs. Do NOT construct install commands from assumed package names.

### Limitations and Caveats Section

REQUIRED — not optional. Every tool has limitations. If primary sources document none, write: "No limitations documented in reviewed sources (confidence: low — absence of documented limitations does not confirm absence of limitations)."

</depth_requirements>

---

## Completeness

Every section of [Entry Template](./entry-template.md) MUST be complete with real data gathered from primary sources. Placeholders, "TBD", and bare "N/A" are FORBIDDEN. When data is genuinely unavailable, write what was searched, what was found, and why the data is absent — using the Rule 3 language above.
