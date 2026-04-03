# Installation

All methods for installing ty, adding it to a project, updating it, and integrating it with editors. Load when the user asks how to install ty, add it to a project, or connect it to an editor.

## Table of Contents

1. [Without Installation](#without-installation)
2. [Add to Project with uv](#add-to-project-with-uv)
3. [Global Installation Methods](#global-installation-methods)
4. [Docker](#docker)
5. [Shell Autocompletion](#shell-autocompletion)
6. [Editor Integration](#editor-integration)

---

## Without Installation

Run ty directly without installing it:

```bash
uvx ty check
```

---

## Add to Project with uv

Adding ty as a project dev dependency ensures all developers use the same version:

```bash
uv add --dev ty
```

Run with uv:

```bash
uv run ty check
```

Update to latest version:

```bash
uv lock --upgrade-package ty
```

---

## Global Installation Methods

### uv tool install

```bash
uv tool install ty@latest
```

Update:

```bash
uv tool upgrade ty
```

### Standalone installer (macOS and Linux)

```bash
curl -LsSf https://astral.sh/ty/install.sh | sh
# or with wget:
wget -qO- https://astral.sh/ty/install.sh | sh
```

Specific version:

```bash
curl -LsSf https://astral.sh/ty/0.0.18/install.sh | sh
```

### Standalone installer (Windows)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/ty/install.ps1 | iex"
```

Specific version:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/ty/0.0.18/install.ps1 | iex"
```

### pipx

```bash
pipx install ty
```

Update:

```bash
pipx upgrade ty
```

### pip

```bash
pip install ty
```

### mise

```bash
mise install ty
mise use --global ty
```

### GitHub Releases

Download binaries directly from <https://github.com/astral-sh/ty/releases>.

---

## Docker

Copy the ty binary from the official image:

```dockerfile
COPY --from=ghcr.io/astral-sh/ty:latest /ty /bin/
```

Available image tags:

- `ghcr.io/astral-sh/ty:latest`
- `ghcr.io/astral-sh/ty:{major}.{minor}.{patch}` (e.g., `ghcr.io/astral-sh/ty:0.0.18`)
- `ghcr.io/astral-sh/ty:{major}.{minor}` (e.g., `ghcr.io/astral-sh/ty:0.0` — latest patch)

---

## Shell Autocompletion

Run the setup command once, then restart the shell or source the config file.

```bash
# Bash
echo 'eval "$(ty generate-shell-completion bash)"' >> ~/.bashrc

# Zsh
echo 'eval "$(ty generate-shell-completion zsh)"' >> ~/.zshrc

# fish
echo 'ty generate-shell-completion fish | source' > ~/.config/fish/completions/ty.fish

# Elvish
echo 'eval (ty generate-shell-completion elvish | slurp)' >> ~/.elvish/rc.elv
```

```powershell
# PowerShell / pwsh
if (!(Test-Path -Path $PROFILE)) {
  New-Item -ItemType File -Path $PROFILE -Force
}
Add-Content -Path $PROFILE -Value '(& ty generate-shell-completion powershell) | Out-String | Invoke-Expression'
```

---

## Editor Integration

### VS Code

Install the [ty extension](https://marketplace.visualstudio.com/items?itemName=astral-sh.ty) from the VS Code Marketplace.

The extension automatically disables the Python extension's built-in language server (`python.languageServer` set to `"None"`).

To use ty only for type checking and keep another language server for completions/hover:

```jsonc
{
  "python.languageServer": "Pylance",
  "ty.disableLanguageServices": true
}
```

### Neovim (nvim-lspconfig, version >= 0.11)

```lua
-- Optional settings configuration
vim.lsp.config('ty', {
  settings = {
    ty = {
      -- ty language server settings go here
    }
  }
})

-- Enable the language server
vim.lsp.enable('ty')
```

For Neovim < 0.11:

```lua
require('lspconfig').ty.setup({
  settings = {
    ty = {}
  }
})
```

### Zed

ty is included out of the box. Enable ty and disable basedpyright in `settings.json`:

```json
{
  "languages": {
    "Python": {
      "language_servers": [
        "ty",
        "!basedpyright",
        "..."
      ]
    }
  }
}
```

Override ty executable path:

```json
{
  "lsp": {
    "ty": {
      "binary": {
        "path": "/home/user/.local/bin/ty",
        "arguments": ["server"]
      }
    }
  }
}
```

### PyCharm (version 2025.3+)

1. Go to **Python | Tools | ty** in Settings
2. Select the **Enable** checkbox
3. Choose **Execution mode**: `Interpreter` (searches project interpreter) or `Path` (searches `$PATH`)
4. Configure desired options

### Any LSP-compatible editor

Start the language server:

```bash
ty server
```

Then configure your editor to connect to the ty LSP server.
