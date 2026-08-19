# ruff Reference Archive

This directory is a **cached snapshot of `docs.astral.sh/ruff`** — generated, not
authored. Do not hand-edit the prose in the reference files here to correct a
stale fact; refresh from the live docs instead.

## Precedence

When anything in this archive is disputed or ambiguous, resolve in this order:

1. The `python-engineering:ruff` skill, if also loaded — this plugin's own policy on *how to work
   with ruff*. Wins over both sources below.
2. The live `astral:ruff` skill / `docs.astral.sh/ruff` — authoritative on *tool
   facts* (current flags, defaults, behavior).
3. This archive — a snapshot of (2). Lowest priority; check the live site
   before trusting a stale-looking claim.

## Documentation Index

- [Configuring Ruff](./docs/configuration.md)
- [FAQ](./docs/faq.md)
- [The Ruff Formatter](./docs/formatter.md)
- [Installing Ruff](./docs/installation.md)
- [Integrations](./docs/integrations.md)
- [The Ruff Linter](./docs/linter.md)
- [Preview](./docs/preview.md)
- [Tutorial](./docs/tutorial.md)
- [Versioning](./docs/versioning.md)
- **editors/**
  - [Features](./docs/editors/features.md)
  - [Editor Integrations](./docs/editors/index.md)
  - [Migrating from `ruff-lsp`](./docs/editors/migration.md)
  - [Settings](./docs/editors/settings.md)
  - [Setup](./docs/editors/setup.md)
- **formatter/**
  - [Known Deviations from Black](./docs/formatter/black.md)

## Refresh cadence

`docs/` and the index above are refreshed weekly by
`.github/workflows/sync-astral-corpus.yml`, which runs
`../../scripts/sync_astral_docs.py ruff` (mirrors `astral-sh/ruff`'s `docs/`
tree) and opens a PR when it changes. ruff has no changelog sync job — only
uv does; see `references/uv/README.md`.

generated_at: 2026-08-19
