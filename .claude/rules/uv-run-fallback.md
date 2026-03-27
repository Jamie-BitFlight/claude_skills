# uv run — Fallback When uv Is Not Available

## Standard invocation

Run all project scripts via `uv run`:

```bash
uv run scripts/some_script.py
uvx skilllint@latest check <path>
```

`uv` automatically creates or reuses the project virtual environment and installs all
dependencies declared in `pyproject.toml` before running the script. No manual `pip install`
or `venv activate` is required.

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

1. Read the first 20 lines of the script to find PEP 723 inline script metadata:

   ```python
   # /// script
   # requires-python = ">=3.11"
   # dependencies = [
   #   "ruamel.yaml",
   #   "typer",
   # ]
   # ///
   ```

2. Install the listed `dependencies` using whatever package manager is available on the host:

   ```bash
   # pip (most common)
   pip install ruamel.yaml typer

   # poetry (if pyproject.toml present with poetry config)
   poetry add ruamel.yaml typer

   # pipx (for isolated CLI tools)
   pipx install typer
   ```

   Match the tool to the project convention — check `pyproject.toml` `[build-system]` or
   `[tool.poetry]` to determine which manager is in use.

3. Run the script directly:

   ```bash
   python scripts/some_script.py
   ```

