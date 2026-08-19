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

## Documentation Index

- [Coming from mypy or pyright](./docs/coming-from-mypy-or-pyright.md)
- [Configuration](./docs/configuration.md)
- [Editor integration](./docs/editors.md)
- [Excluding files](./docs/exclusions.md)
- [ty](./docs/index.md)
- [Installing ty](./docs/installation.md)
- [Module discovery](./docs/modules.md)
- [Python version](./docs/python-version.md)
- [Rules](./docs/rules.md)
- [Suppression](./docs/suppression.md)
- [Type checking](./docs/type-checking.md)
- **features/**
  - [Diagnostics](./docs/features/diagnostics.md)
  - [Language server](./docs/features/language-server.md)
  - [Type system](./docs/features/type-system.md)
- **reference/**
  - [CLI Reference](./docs/reference/cli.md)
  - [Configuration](./docs/reference/configuration.md)
  - [Editor settings](./docs/reference/editor-settings.md)
  - [Environment variables](./docs/reference/environment.md)
  - [Exit codes](./docs/reference/exit-codes.md)
  - [Rules](./docs/reference/rules.md)
  - [Typing FAQ](./docs/reference/typing-faq.md)

## Refresh cadence

`docs/` and the index above are refreshed weekly by
`.github/workflows/sync-astral-corpus.yml`, which runs
`../../scripts/sync_astral_docs.py ty` (mirrors `astral-sh/ty`'s `docs/`
tree) and opens a PR when it changes. ty has no changelog sync job — only uv
does; see `references/uv/README.md`.

generated_at: 2026-08-19
