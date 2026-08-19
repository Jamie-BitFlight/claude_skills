# ty Reference Archive

This directory is a **cached snapshot of `docs.astral.sh/ty`** — generated, not
authored. Do not hand-edit the prose in the reference files here to correct a
stale fact; refresh from the live docs instead.

## Precedence

When anything in this archive is disputed or ambiguous, resolve in this order:

1. `.claude/rules/astral-tool-overrides.md` — this repo's policy on *how we
   work with ty here*. Wins over both sources below.
2. The live `astral:ty` skill / `docs.astral.sh/ty` — authoritative on *tool
   facts* (current flags, defaults, behavior).
3. This archive — a snapshot of (2). Lowest priority; check the live site
   before trusting a stale-looking claim.

## Version Information

No automated changelog sync exists for ty today. `sync_ty_releases.py` — the
would-be ty counterpart to `../../scripts/sync_uv_releases.py` — was deleted
during the Astral plugin migration: it targeted a `## Version Information`
section that never existed in the skill it wrote to, so it had never
successfully run. If ty changelog tracking is wanted later, parameterize
`sync_uv_releases.py` with a `--repo` flag rather than reintroducing a
near-duplicate script.

## Refresh cadence

`.github/workflows/sync-astral-corpus.yml` runs weekly but only covers uv
today — ty has no changelog sync job. This archive's staleness is tracked
only by the `generated_at` stamp below — check `docs.astral.sh/ty` directly
for anything time-sensitive.

The reference corpus itself (`cli-reference.md`, `configuration-schema.md`,
`environment-and-modules.md`, `file-selection.md`, `installation.md`,
`migration-guide.md`, `quick-reference.md`, `rules-and-diagnostics.md`,
`troubleshooting.md`) has **no automated regeneration today** — refreshing it
is a manual, reviewed pass against `docs.astral.sh/ty`.

generated_at: 2026-08-19
