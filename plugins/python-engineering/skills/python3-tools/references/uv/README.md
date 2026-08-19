# uv Reference Archive

This directory is a **cached snapshot of `docs.astral.sh/uv`** — generated, not
authored. Do not hand-edit the prose in the reference files here to correct a
stale fact; refresh from the live docs instead.

## Precedence

When anything in this archive is disputed or ambiguous, resolve in this order:

1. `.claude/rules/astral-tool-overrides.md` — this repo's policy on *how we
   work with uv here*. Wins over both sources below.
2. The live `astral:uv` skill / `docs.astral.sh/uv` — authoritative on *tool
   facts* (current flags, defaults, behavior).
3. This archive — a snapshot of (2). Lowest priority; check the live site
   before trusting a stale-looking claim.

## Version Information

<!-- populated by ../../scripts/sync_uv_releases.py -->

## Refresh cadence

Intended to be refreshed weekly by a scheduled CI job (A10, not yet built as
of this writing) that runs `../../scripts/sync_uv_releases.py` to update the
Version Information section above from the GitHub Releases API.

The reference corpus itself (`cli_reference.md`, `configuration.md`,
`migration-guide.md`, `quick-reference.md`, `troubleshooting.md`) has **no
automated regeneration today** — refreshing it is a manual, reviewed pass
against `docs.astral.sh/uv`, not something this stamp guarantees is current.

generated_at: 2026-08-19
