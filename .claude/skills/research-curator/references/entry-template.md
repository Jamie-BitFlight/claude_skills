# Research Entry Template

Standard format for all research entries in `./research/`.

Content scope: [Entry Quality Standards](./entry-quality-standards.md#scope).

---

## Category Selection

Pick the existing directory under `./research/` whose name best matches the resource's primary
function (list them with `ls ./research/`). `VALID_CATEGORIES` in `research/knowledge-explorer.py`
is the set that script accepts. When `developer-tools` and `developer-tooling` both fit, use
`developer-tools`. Create a new category directory only when no existing one fits.

---

## Entry File Template

File location: `./research/{category}/{resource-name}.md`

````markdown
---
name: {resource-name-slug}
title: {Official resource name}
subtitle: {What a reader finds inside — the key capability, finding, or differentiator, in 5-10 words}
research_date: YYYY-MM-DD
source_url: https://...
github_repository: https://github.com/... # if applicable
version_at_research: vX.Y.Z
license: {License type}
freshness_tracking:
  last_verified: YYYY-MM-DD
  version_at_verification: vX.Y.Z
  next_review: YYYY-MM-DD
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high, Technical Architecture: medium (code-read), Installation & Usage: high, Limitations and Caveats: low"
---

# {Resource Name}

## Overview

2-3 sentence description of the resource, its purpose, and primary value proposition.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| {Problem 1} | {How this resource solves it} |
| {Problem 2} | {How this resource solves it} |

---

## Key Features

### {Feature Category 1}

- {what it does} — {the mechanism}; example and constraints when the source gives them
- {what it does} — {the mechanism}; example and constraints when the source gives them

### {Feature Category 2}

- {what it does} — {the mechanism}; example and constraints when the source gives them

---

## Technical Architecture

Core components by exact source name, data flow or execution model, documented design rationale, extension points. Diagrams if helpful.

---

## Limitations and Caveats

Documented limitations, or the low-confidence absence statement from [Entry Quality Standards](./entry-quality-standards.md).

---

## Installation & Usage

```bash
# Installation command
```

```python
# Usage example
```

---

## References

- [{Source Name}]({URL}) (accessed YYYY-MM-DD)
- [{Source Name}]({URL}) (accessed YYYY-MM-DD)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Resource Name](../category/filename.md) | category-name | {one-phrase relationship} |
````

> **Confidence qualifiers**: When a section's claims derive from code analysis rather than
> documentation, append `(code-read)` to the confidence level — e.g., `Architecture: medium
> (code-read)`. This distinguishes entries where architectural claims come from source code
> inspection (verifiable but potentially incomplete) versus official documentation (authoritative
> but potentially outdated). Sections with mixed sources use the lower confidence level and
> note both qualifiers: `Architecture: medium (doc + code-read)`. A `(code-read)` section is never `high`.

> **Fields and absent sections**: The validator requires `research_date`, `source_url`,
> `version_at_research`, `license` and the `freshness_tracking` keys; `name`, `title`, `subtitle`
> and `github_repository` are not checked by it. `confidence_map` and `## Limitations and Caveats`
> are checked by the reviewer only. When the resource has no architecture, install step, version or
> license, write the Rule 3 absence sentence from
> [Entry Quality Standards](./entry-quality-standards.md) in that section or field instead of
> leaving it empty. A snapshot (a version, figure or status) carries its date and source, for
> example `Latest release v1.4.2 (accessed 2026-10-03, source: GitHub releases page)`.

> **Architecture section citations**: When Technical Architecture or Key Features items derive
> from code analysis, cite the source inline using the format:
> `Source: {relative-path} — {exported-name}`
> The path is relative to the researched resource's own clone root, not to this repository.
>
> Examples:
>
> - `Source: src/core/engine.py — class TaskEngine`
> - `Source: src/api/routes.py — register_routes()`
> - `Source: proto/schema.proto — message EventPayload`
>
> When multiple code files corroborate a single architectural claim, list sources comma-separated:
> `Source: src/core/engine.py — class TaskEngine, src/core/graph.py — class DependencyGraph`

> **Note**: `## Cross-References` is populated by `@research-cross-referencer` (forward rows) and
> `validate_research.py check-backlinks --fix` (reciprocal rows); add it by hand for a manually created entry.
> Row shape, placement anchor, relative-path rules and the relationship-phrase bar:
> [Cross-Reference Format](./cross-reference-format.md).

> **Note**: `freshness_tracking.next_review` informs scheduling; it never gates anything. An
> explicit re-research request — `--rerun`, `--batch` URL resubmission, or `--all` — proceeds
> regardless of this date.

---

## Setting Next Review

Default to 3 months from the research date — a conservative baseline for stable or slow-moving
projects. Calibrate to the resource's observed release cadence: a repository with frequent
major/minor releases or active breaking API changes warrants 4–6 weeks instead.
