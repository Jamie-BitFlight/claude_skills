# Overlap Scan

The one-off step that runs once per entry, after the entry is created and Entry Review returns PASS.
It compares a semantic analysis of the researched resource against this repository's projects and
systems, and files each finding as a GitHub issue.

The repository changes constantly, so a committed record of overlap goes stale the day it is
written. An issue is dated by nature and tracked by the backlog; a file under `./research/` is not.
`@research-insight-extractor` and `@research-utilization-assessor` each run this scan with their own
lens; this file states everything they share.

## Procedure

1. Read the entry at the path given. Derive what the resource offers from it.
2. Orient with `ARCHITECTURE.md` if it helps; it is a suggestion, not a required read.
3. Scan the repository semantically with the best tooling the environment offers: the `ccc` skill,
   graphify, other search skills, plugins, MCP servers. Use every one that works; fall back to
   anything else that searches (Grep, Glob, `git grep`, reading files).
4. Open every file a finding cites before citing it.
5. Check for an existing issue on the same finding before filing: open and closed, by topic.
6. File each finding that survives as a GitHub issue.

## Issue

A concept or idea, stated as:

- **Offers**: what the researched resource provides, with the entry path.
- **Touches**: which repository system or goal it overlaps.
- **Could change**: what the repository could adopt, reuse, call, or stop maintaining.
- **Evidence**: paths, queries, and exact lines read, from this scan. A finding of absence reads
  "not found by these searches" and lists every tool and query run.

Issue text states findings plainly: no hedged or causal claims ("might", "because", "therefore"),
no percentages, no invented figures; quote the entry when attributing a claim to it.

File through the first route that works, in this order: the backlog MCP tools, the GitHub MCP tools,
`gh`. When a route fails, name the route and its exact error in the return block, then try the next.

## Output

Write nothing under `./research/` and commit nothing. Return the issue numbers and URLs, plus every
failed route. When no route can file, return the findings in the final message, in the shape above;
a scratch copy under `.tmp/scratch/` is permitted.
