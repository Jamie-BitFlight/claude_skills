# Research Entry Quality Standards

The content contract every research entry under `./research/` must satisfy, whoever writes it. Fidelity Rules govern each claim; Depth Requirements govern each section's coverage. Both apply to every entry being written.

This is a writing contract, not an audit checklist. [Entry Review Rubric](./entry-review-rubric.md)
gates the entry on one thing — that a reader can reach the canonical source — because an agent that
needs a fact about the subject reads the source rather than the entry. Everything else below shapes
the entry at writing time and costs nothing to honour while the sources are open, but a finished
entry is never failed, edited, or withheld for it.

**Rule 3 is the exception, and it is deliberate.** A bare nonexistence claim is the one writing
failure that tells the reader, on the writer's word, not to bother going to the source — so it
attacks the very thing the rubric gates, and it is Gate 1's last check. A finished entry *is* failed
and *is* withheld from the index for it. Read the sentence above as covering every rule below except
this one.

The rubric's other gates never touch a finished entry's index row: Gate 2 records repo-claim defects
for repair, and Gate 3 adjudicates the reasoning in the `insights/` and `utilization/` files, which
are not this contract's subject at all.

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

Do NOT gather star counts, download counts, fork counts, or contributor counts. This binds the
agent doing the gathering: it applies whether the repository is in the session's authorized GitHub
scope or out of it, and no fallback source (web search, package registry, a badge in the README)
makes the data in scope. Nothing that was never fetched can be written, so there is no separate
writing prohibition to enforce. There is no "Key Statistics" section in the entry template; do not
add one.

This rule reaches forward only. Statistics already present in existing entries stay exactly where
they are — a figure in a finished entry is not a defect, not a `--fix` target, and never a reason to
edit or withhold that entry. The rule was formerly enforced against finished entries while the
template still required a "Key Statistics" section, which is why entries written before that
section was removed carry one.

SOURCE: the "Key Statistics" block — `GitHub Stars`, `Downloads/month`, `Contributors` — was deleted
from `entry-template.md` in commit `a54eef252` (2026-07-08). Every entry authored before that date
was written against a template that required it.

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

### Relevance to Claude Code Development — the section the review gates

Every other section describes the subject, and a reader who needs the subject reads the subject's own
documentation. This section says something a reader cannot get from the source URL, so it is the only
prose [Entry Review Rubric](./entry-review-rubric.md) audits — claim by claim, against this
repository's actual files.

Write each item so that opening one file could prove it false:

1. **Name the local thing** — a path, skill, agent, command, or workflow that exists in this repo.
   Open it before writing the sentence.
2. **Say what that file does today** — the state the proposal is measured against.
3. **Say what the subject would change about it** — tied to a specific mechanism this entry already
   documented from the source.
4. **Name the signal** — the command to run or the field to read that shows whether the change
   landed.

An item that skips step 1 has nothing to verify and nothing to act on. "Fits well with this project's
architecture", "useful for agent workflows", and "could improve code quality" would each be equally
true of any repository, which is exactly what makes them worthless here. Three items that name files
beat ten that do not. Where the sources support no such item, write "No application to this
repository found in the sources reviewed" rather than filling the section with claims that name
nothing.

The same bar binds every proposal in the `-improvements.md` and `-utilization.md` analysis files,
which are reviewed together with the entry.

</depth_requirements>

---

## Completeness

Every section of [Entry Template](./entry-template.md) MUST be complete with real data gathered from primary sources. Placeholders, "TBD", and bare "N/A" are FORBIDDEN. When data is genuinely unavailable, write what was searched, what was found, and why the data is absent — using the Rule 3 language above.
