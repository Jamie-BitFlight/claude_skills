# research/ — AI-Facing Knowledge Base

This directory is a knowledge base an AI agent reads while planning or designing systems with the
user — not documentation for a human reader. Write and edit every entry for that use: an agent
mid-plan pulling in a tool's tradeoffs, architecture, and integration surface, not a marketing
summary.

## Evergreen substance, dated snapshots

Split every claim into one of two kinds:

- **Evergreen** — what the tool is, the problem it solves, its architecture, its design
  tradeoffs. This should still be true in a year; write it as such.
- **Snapshot** — star counts, pricing, version numbers, benchmark figures. These go stale. A
  snapshot is not wrong for going stale — it is wrong for going stale *silently*. Every snapshot
  claim carries the date it was true and the source it came from, so a future reader can re-check
  it in seconds instead of trusting a frozen number.

Never state a snapshot fact without both. Never delete a stale snapshot instead of dating it —
deleting it is data loss; dating it is the fix.

## Citation integrity

A citation is a claim the agent hasn't checked is real. Before trusting one already in a file, or
adding a new one: fetch the URL and confirm it both resolves and actually supports the specific
claim attached to it — not just that a plausible-looking page exists. Audit an entry's References
section as its own pass, separate from checking the body prose — a citation can be perfectly
formatted, correctly dated, and pointing at nothing.

## Fabrication reads as plausible, not as wrong

The structural validator (`validate_research.py`) checks that sections exist and citations are
dated — it cannot tell a real CLI flag from an invented one, or a genuine repo URL from a
plausible-looking wrong one. Confirm every specific fact — a flag, a percentage, a URL, a version
— against the tool's actual primary source before it goes in. A number that sounds right and
isn't traces back to training-data recall standing in for a source that was never actually
fetched.

Watch for content written for one entry appearing in another — a section describing one tool's
platform support or install flow copy-pasted onto an unrelated tool's page. Verify each entry's
claims against that entry's own source, not a neighboring entry's template.

## Where the schema lives

Required sections, header fields, and validator rules are defined once in
[entry-template.md](../.claude/skills/research-curator/references/entry-template.md) and
[validation-rules.md](../.claude/skills/research-curator/references/validation-rules.md). Don't
restate them here — read those before creating or fixing an entry, and use `/research-curator` to
create, refresh, or validate entries.
