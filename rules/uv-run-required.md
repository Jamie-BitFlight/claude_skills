# uv run Is Required — No Fallback When Unavailable

## Standard invocation

Run all project scripts via `uv run`:

```bash
uv run scripts/some_script.py
uvx skilllint@latest check <path>
```

`uv run` resolves whatever environment a script needs at launch — from its own PEP 723
`# /// script` block when it has one (see `rules/python-development.md`), or from the project
environment otherwise. No manual `pip install` or `venv activate` is required.

## If `uv run` fails with "uv not found" or "command not found"

**Preferred fix — install uv (resolves this for all future sessions):**

Ask the user:

```text
uv is not installed. It handles virtual environments and dependency installation
automatically. Would you like me to install it now?
```

If yes, install:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then re-run the original command with `uv run`.

**If uv installation is not an option:**

Stop and tell the user. There is no fallback: `pip`, `poetry`, `pipx`, and bare `python` are all
prohibited substitutes for `uv run` (`astral-tool-overrides.md`'s Package management rule,
`script-invocation.md`). Report which command needed `uv` and wait for the user to make `uv`
available; do not install dependencies or run the script by any other means.
