# ty Reference Archive

This directory is a **cached snapshot of `docs.astral.sh/ty`** — generated, not
authored. Do not hand-edit the prose in the reference files here to correct a
stale fact; refresh from the live docs instead.

## Precedence

When anything in this archive is disputed or ambiguous, resolve in this order:

1. The `python-engineering:ty` skill, if also loaded — this plugin's own policy on *how to work
   with ty*. Wins over both sources below.
2. The live `astral:ty` skill / `docs.astral.sh/ty` — authoritative on *tool
   facts* (current flags, defaults, behavior).
3. This archive — a snapshot of (2). Lowest priority; check the live site
   before trusting a stale-looking claim.

## Refresh cadence

No automated regeneration. Staleness is tracked only by the `generated_at`
stamp below — check `docs.astral.sh/ty` directly for anything time-sensitive.
Each file below is a manual, reviewed pass against `docs.astral.sh/ty`:

- `cli-reference.md`
- `configuration-schema.md`
- `environment-and-modules.md` — import resolution, unresolved imports, virtual environments, environment variables
- `file-selection.md`
- `installation.md`
- `migration-guide.md`
- `quick-reference.md`
- `rules-and-diagnostics.md`
- `troubleshooting.md`

generated_at: 2026-08-20
