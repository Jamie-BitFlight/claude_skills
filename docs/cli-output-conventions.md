# CLI and Script Output Conventions — Agent-Only, Never Human-Facing

Every plugin in this repo exists to be consumed by an AI agent harness (Claude Code, Codex,
OpenCode, GitHub's coding agent) — that is the whole purpose of a Claude Code plugin. No script,
CLI tool, or MCP server under `plugins/**/scripts/` or `plugins/**/skills/*/scripts/` has a human
running it interactively at a terminal, ever. Design output accordingly, not as a dual-audience
guess:

- **Structured/tabular output → JSON, not aligned plain-text tables.** A text table binds each
  value to its meaning via column *position* (nth value = nth header); JSON binds via an explicit
  *repeated key* at each value — a more direct, unambiguous token-level association for an LLM
  parsing the output, with no risk of misparsing when a cell value contains whitespace. Emit
  compact JSON (`json.dumps(data)` / `model_dump_json()`, no `indent=`) for this — output a script
  or CLI emits for an agent to parse. The rule governs JSON a program emits at runtime, nothing
  else. It does not apply to JSON files committed to the repo as configuration or data — every
  harness plugin manifest (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`),
  `package.json`, `marketplace.json`, tool configs, fixtures, snapshots. Humans read and edit
  those, git diffs them line by line, and non-AI tooling consumes them; they keep their existing
  pretty-printed formatting. Never reformat one as part of an unrelated change.
- **`logging` is for debug/trace/forensic output only** — never for primary output a calling agent
  needs to read or parse. Status messages, results, and errors meant to be consumed by the caller
  go through direct stdout/stderr emission (`typer.echo()`, `print()`, structured JSON), not a
  logger.
- **Never add a `--json`/`--format text|json` dual-mode flag "just in case."** There is one
  consumer. Dual-mode output is the right pattern for genuinely mixed-audience tools (`kubectl`,
  `gh`, `docker`) — it is not the right pattern here. Before assuming a tool has a human reader,
  verify by checking actual callers (`grep` for the script name across `plugin.json`, `hooks.json`,
  `SKILL.md` workflow steps) rather than inferring "interactive use" from docstring language.
- **Rich (`rich.console.Console`, `Table`, `Panel`, `Progress`)** defaults to a hardcoded 80-column
  width with no TTY attached (`rich/console.py`: `width = width or 80`), wrapping or truncating
  output — a correctness bug for an agent-only consumer, not a cosmetic one. Prefer plain
  `typer.echo()`/JSON over Rich for agent-facing CLI output. If Rich is genuinely needed (e.g. a
  `--verbose` diagnostic stream), see `python-engineering:python3-cli`'s
  `references/typer-rich-non-tty-patterns.md` for the measure-and-render pattern that keeps it
  data-loss-safe; do not use Rich's TTY-oriented defaults unmodified.
