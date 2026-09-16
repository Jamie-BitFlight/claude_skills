# Research Entry Quality Standards

The content contract every research entry under `./research/` must satisfy, whoever writes it. Fidelity Rules govern each claim; Depth Requirements govern each section's coverage. Both apply to every entry.

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

Leave star counts, download counts, fork counts, and contributor counts ungathered. The entry
template has no "Key Statistics" section; write the entry without one, and keep this data out
of the other sections too.

The rule binds an agent at gather time: it applies whether the repository is in the session's
authorized GitHub scope or out of it, and no fallback source (web search, package registry, a
badge in the README) makes the data in scope.

It reaches no further than that. Figures a finished entry already carries stay as written —
the entry template required a `Key Statistics` block of `GitHub Stars`, `Downloads/month`, and
`Contributors` until commit `a54eef252` (2026-07-08) removed it, so every entry written before
that date carries the section because its template demanded it. Such a figure is not a defect,
not a `--fix` target, and not a reason to edit or withhold an entry. A refresh of one of these
entries keeps the section it found and adds nothing to it.

SOURCE: `git show a54eef252 -- .claude/skills/research-curator/references/entry-template.md`
(commit dated 2026-07-08, PR #2723) — the diff that deleted the `Key Statistics` block.

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
