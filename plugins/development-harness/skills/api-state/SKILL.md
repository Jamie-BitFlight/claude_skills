---
name: api-state
description: "Fetch and report current API syntax, changelog entries, and breaking changes for a specific library or protocol version. One research angle within a parallel technical-research set — runs independently and returns a structured cited report. Invoke when a specific library name and version are the target."
---

# API State

One research angle in a multi-angle technical research system. Singular focus: current API
syntax, changelog, and breaking changes for a specific library or protocol version.

Runs independently. No shared state with other research angles during execution. Return all
findings as content — do not write to any backlog item.

## Workflow

### Step 1 — Scope

Research target received from orchestrator:

$ARGUMENTS

Confirm the technology name, version, and specific API surface before proceeding. If any are
missing or ambiguous, state the gap and output:

STATUS: BLOCKED
Reason: [missing field] — cannot proceed without [technology name | version | API surface].

### Step 2 — Current API State

Fetch the primary documentation page for the technology. Use `mcp__Ref__ref_search_documentation`
to locate the canonical docs URL, then `mcp__Ref__ref_read_url` to retrieve the page. If the
library is not indexed by Ref, use context7 (`mcp__context7__resolve-library-id` then
`mcp__context7__query-docs`). Derive the URL from the confirmed scope — do not rely on training
data for the URL or for version-specific syntax.

Extract and record:

- Exact method/class/decorator signatures
- All parameter forms (required, optional, typed, variadic)
- Return types and async behaviour
- Context injection patterns (if applicable to the technology)
- Any configuration or initialization requirements

Cite each item with the source URL and access date.

### Step 3 — Changelog

Fetch the raw changelog. Locate it at the canonical path for the technology — commonly
`CHANGELOG.md` or `CHANGES.md` in the GitHub repository, or the GitHub Releases page. Use
`mcp__Ref__ref_read_url` for the changelog URL. Fall back to `WebFetch` for raw GitHub
URLs not served by Ref.

Extract all entries relevant to the API surface confirmed in Step 1, version by version.
Cite each entry with its version number and source URL.

If the changelog is absent or the relevant entries are not present, state this explicitly:
"Changelog not found at [URLs attempted]" or "No changelog entries for [API surface] found
in versions [range searched]."

### Step 4 — Breaking Changes

From the changelog and release notes, identify changes between the most recent major versions:

- What broke silently (no deprecation warning before removal)
- What requires explicit migration (changed signatures, removed parameters, renamed classes)
- What was deprecated and when (deprecation version and removal version if stated)

If no breaking changes are found, state this explicitly with the version range examined.

### Step 5 — Gotchas

Synthesise from the findings in Steps 2–4:

- What was the changelog FIXING? (implies the behaviour was broken before that version)
- What do the docs explicitly warn about?
- What behaviour is client-defined versus protocol-defined or library-defined?

Every gotcha must cite its source: a changelog entry URL, a doc warning with URL, or an
observed inconsistency between two cited sources.

### Step 6 — Output

Return the following structured report, populated from the findings above, then close with
a STATUS block:

```text
## API State — {technology} {version} — {date}

### Current API
[exact syntax, parameters, return types — with cited source URL and access date]

### Changelog (relevant entries)
[version: entry — source URL]

### Breaking Changes ({prev version} → {current version})
[each change with source]

### Gotchas
[each item with source — changelog entry, doc warning, or observed evidence]

### Gaps
[what was searched for but not found — explicit list]
```

STATUS: DONE
Findings delivered to caller above. No backlog item written.

The Gaps section is mandatory. If nothing is missing, write: "No gaps — all expected
information was found in primary sources."

## Constraints

- "Not documented in [source]" is a valid finding — state it rather than omitting it.
