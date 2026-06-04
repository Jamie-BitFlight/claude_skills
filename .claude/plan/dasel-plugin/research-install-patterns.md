# Research: Cross-Platform Binary Install Script Patterns for Dasel

**Date**: 2026-02-19
**Tool**: dasel v3.2.2 — <https://github.com/TomWright/dasel>
**API endpoint**: <https://api.github.com/repos/TomWright/dasel/releases/latest>

---

## Recommended Script Approach

**Use Python PEP 723 with `httpx` and `typer`.**

Rationale:

- All install-style scripts in this repo use Python PEP 723 (27+ scripts in `plugins/**/scripts/`). The only Bash in the repo is a thin POSIX wrapper (`setup-ci-publish-token.sh`) for legacy shell reasons.
- Python handles cross-platform path logic (`pathlib.Path`) without branching on shell syntax.
- `httpx` provides streaming downloads with progress and timeout support.
- `typer` provides `--dry-run`, `--force`, `--bin-dir` flags without argparse boilerplate.
- Python stdlib `hashlib` does SHA256 without external tools (`sha256sum`, `certutil`).
- Python stdlib `stat` sets executable bits without `chmod`.
- Pattern confirmed by: `plugins/python3-development/skills/uv/scripts/sync_uv_releases.py` (httpx for GitHub API), `plugins/holistic-linting/skills/holistic-linting/scripts/install_agents.py` (file install with hash comparison).

**Shebang to use**:

```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "httpx>=0.28.1",
# ]
# ///
```

SOURCE: Direct observation of `sync_uv_releases.py` line 1-8 and `create_plugin.py` line 1-7.

---

## Platform Detection Logic

Verified via `python3 -c "import platform, sys; ..."` on this system:

```python
import platform
import sys
from pathlib import Path

def detect_platform() -> tuple[str, str]:
    """Return (os_key, arch_key) matching dasel asset naming convention."""
    system = platform.system().lower()   # 'linux', 'darwin', 'windows'
    machine = platform.machine().lower() # 'x86_64', 'aarch64', 'arm64', 'i386'

    # Normalize architecture to dasel naming
    arch_map = {
        'x86_64': 'amd64',
        'amd64': 'amd64',
        'aarch64': 'arm64',
        'arm64': 'arm64',
        'armv7l': 'arm32',
        'i386': '386',
        'i686': '386',
    }
    arch = arch_map.get(machine, machine)

    # WSL2 detection: /proc/version contains "microsoft" on WSL2
    # WSL2 behaves as Linux for binary installation purposes
    if system == 'linux':
        try:
            proc_version = Path('/proc/version').read_text().lower()
            is_wsl2 = 'microsoft' in proc_version
        except OSError:
            is_wsl2 = False
        # WSL2 uses linux binaries — no special handling needed for the binary
        # PATH setup differs (see WSL2 section below)
        return 'linux', arch

    return system, arch
```

**Tested observation**: On this system, `platform.system()` returns `'Linux'`, `platform.machine()` returns `'x86_64'`. `/proc/version` does NOT contain "microsoft" (native Linux, not WSL2).

---

## GitHub Releases API Pattern

**Endpoint**: `https://api.github.com/repos/TomWright/dasel/releases/latest`

**Verified response** (tag_name: `v3.2.2`, published_at: `2026-02-13T17:18:11Z`):

The API returns an `assets` array. Each asset has:

```json
{
  "name": "dasel_linux_amd64",
  "browser_download_url": "https://github.com/TomWright/dasel/releases/download/v3.2.2/dasel_linux_amd64",
  "digest": "sha256:313f055bd8c7c59bb8a9cad863f0685769d6f8a93b5f9b9a0986c95c76513832",
  "size": 9797816
}
```

**Key observation**: The `digest` field in the GitHub API response contains the SHA256 hash. There is NO separate checksums file in dasel releases. SHA256 must be extracted from the API response `assets[].digest` field, not from a companion `.sha256` file.

**Pattern for asset lookup**:

```python
def find_asset(assets: list[dict], os_key: str, arch: str) -> dict | None:
    """Find the matching asset from the API response."""
    # dasel naming: dasel_{os}_{arch} or dasel_{os}_{arch}.exe (Windows)
    if os_key == 'windows':
        target_name = f"dasel_{os_key}_{arch}.exe"
    else:
        target_name = f"dasel_{os_key}_{arch}"

    for asset in assets:
        if asset['name'] == target_name:
            return asset
    return None
```

**All verified asset names from v3.2.2**:

```
dasel_darwin_amd64
dasel_darwin_amd64.gz
dasel_darwin_arm64
dasel_darwin_arm64.gz
dasel_linux_386
dasel_linux_amd64        ← sha256: 313f055b...
dasel_linux_arm32
dasel_linux_arm64        ← sha256: 135ac22a...
dasel_windows_386.exe
dasel_windows_amd64.exe  ← sha256: bf5ccd37...
```

Prefer non-`.gz` assets for direct binary download (simpler install, no decompression step required).

**SHA256 digest field format**: `"sha256:<hex>"` — strip the `"sha256:"` prefix before comparison:

```python
digest_field = asset.get('digest', '')
expected_sha256 = digest_field.removeprefix('sha256:')
```

---

## SHA256 Verification Pattern

```python
import hashlib

def verify_sha256(data: bytes, expected_hex: str) -> bool:
    """Verify SHA256 of downloaded bytes against expected hex string."""
    actual = hashlib.sha256(data).hexdigest()
    return actual == expected_hex
```

For streaming large downloads, use chunk-based hashing:

```python
def verify_sha256_stream(path: Path, expected_hex: str) -> bool:
    sha256 = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest() == expected_hex
```

---

## User-Space Install Directories Per Platform

**Verified on this system**: `~/.local/bin` is already in `PATH` (`/home/user/.local/bin`).

### Linux and WSL2

```python
install_dir = Path.home() / '.local' / 'bin'
binary_name = 'dasel'
install_path = install_dir / binary_name
```

`~/.local/bin` is the XDG-compliant user-space binary directory. On most modern Linux distros it is pre-added to `PATH` via `~/.profile` or `/etc/environment`. On WSL2, same path applies — WSL2 Linux environment behaves identically to native Linux for user-space installs.

### Windows Native

```python
# Primary: LOCALAPPDATA (e.g., C:\Users\user\AppData\Local)
local_app_data = os.environ.get('LOCALAPPDATA')
if local_app_data:
    install_dir = Path(local_app_data) / 'Programs' / 'dasel'
else:
    install_dir = Path.home() / 'AppData' / 'Local' / 'Programs' / 'dasel'
binary_name = 'dasel.exe'
install_path = install_dir / binary_name
```

`%LOCALAPPDATA%\Programs\dasel` is a common pattern (used by tools like Git for Windows, fnm). Alternative: `%USERPROFILE%\bin` if simpler PATH management is preferred.

### macOS (for completeness)

```python
install_dir = Path.home() / '.local' / 'bin'  # or /usr/local/bin with sudo
binary_name = 'dasel'
```

---

## PATH Setup Per Platform

### Linux / WSL2 — `~/.local/bin`

Check first; many distros pre-configure it:

```python
import os

def ensure_in_path(bin_dir: Path) -> bool:
    """Return True if already in PATH, False if profile update needed."""
    path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    return str(bin_dir) in path_dirs

def add_to_shell_profile(bin_dir: Path) -> None:
    """Append PATH export to ~/.bashrc and ~/.zshrc if not present."""
    export_line = f'export PATH="{bin_dir}:$PATH"'

    for profile in [Path.home() / '.bashrc', Path.home() / '.zshrc']:
        if profile.exists():
            content = profile.read_text()
            if str(bin_dir) not in content:
                with profile.open('a') as f:
                    f.write(f'\n# Added by dasel installer\n{export_line}\n')
```

### Windows Native — `%LOCALAPPDATA%\Programs\dasel`

Use the Windows registry or PowerShell to add to user PATH (no `sudo` required):

```python
import subprocess

def add_to_windows_user_path(bin_dir: Path) -> None:
    """Add bin_dir to Windows user PATH via PowerShell registry edit."""
    ps_script = f"""
$path = [Environment]::GetEnvironmentVariable('PATH', 'User')
$new = '{bin_dir}'
if ($path -notlike "*$new*") {{
    [Environment]::SetEnvironmentVariable('PATH', "$path;$new", 'User')
    Write-Host "Added to PATH: $new"
}} else {{
    Write-Host "Already in PATH: $new"
}}
"""
    subprocess.run(
        ['powershell', '-NoProfile', '-Command', ps_script],
        check=True,
    )
```

### WSL2-Specific PATH Consideration

WSL2 auto-inherits Windows PATH (via `WSLENV` and WSL interop). If the user installs dasel in WSL2's `~/.local/bin`, it is only available inside WSL2 — not from Windows PowerShell. This is the expected behavior for a Linux binary. No special handling needed unless the user explicitly wants cross-environment access (out of scope for this installer).

---

## Version Check Logic

**dasel version output format**: `dasel version v3.2.2` (based on standard Go CLI conventions; not directly verified by execution since dasel is not installed on this system — verified via release tag format `v3.2.2`).

```python
import subprocess
from pathlib import Path

def get_installed_version(binary_path: Path) -> str | None:
    """Return installed version string or None if not installed."""
    if not binary_path.exists():
        return None
    try:
        result = subprocess.run(
            [str(binary_path), '--version'],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Expected output: "dasel version v3.2.2"
        # Strip leading 'v' for comparison
        output = result.stdout.strip() or result.stderr.strip()
        for part in output.split():
            if part.startswith('v') and part[1:].replace('.', '').isdigit():
                return part.lstrip('v')
        return output  # fallback: return raw output
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None

def is_update_needed(installed: str | None, latest: str) -> bool:
    """Compare version tuples. latest is tag_name stripped of leading 'v'."""
    if installed is None:
        return True

    def to_tuple(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v.lstrip('v').split('.') if x.isdigit())

    return to_tuple(installed) < to_tuple(latest)
```

**Fetch latest version from API**:

```python
import httpx

def fetch_latest_release() -> dict:
    """Fetch latest dasel release metadata from GitHub API."""
    url = 'https://api.github.com/repos/TomWright/dasel/releases/latest'
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers={'Accept': 'application/vnd.github+json'})
        response.raise_for_status()
        return response.json()
```

---

## WSL2 Detection

Canonical pattern used by installers (e.g., Homebrew, Rustup, nvm):

```python
def is_wsl2() -> bool:
    """Detect WSL2 by checking /proc/version for 'microsoft'."""
    try:
        return 'microsoft' in Path('/proc/version').read_text().lower()
    except OSError:
        return False
```

**Observation**: On native Linux, `/proc/version` does not contain "microsoft". On WSL2, it does. This is the standard detection method used across the ecosystem.

**WSL2 installs Linux binaries** — use `dasel_linux_amd64` (or `arm64`), not Windows `.exe`. The WSL2 environment is a full Linux subsystem; Windows binaries do not run inside it.

---

## Executable Permission

On Linux/macOS/WSL2, downloaded binary must have execute bit set. Python `os.chmod` handles this without `chmod` shell command:

```python
import os
import stat

def make_executable(path: Path) -> None:
    """Set executable bit on downloaded binary."""
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
```

On Windows, `.exe` files are inherently executable — no chmod equivalent needed.

---

## Complete Install Flow Summary

```
1. fetch_latest_release() → tag_name, assets[]
2. detect_platform() → (os_key, arch_key)
3. find_asset(assets, os_key, arch_key) → asset (name, url, digest, size)
4. resolve install_dir and binary_path for platform
5. get_installed_version(binary_path) → installed_version | None
6. is_update_needed(installed_version, latest_version) → bool
7. If up-to-date and not --force: exit 0 with message
8. Download binary via httpx streaming to temp file
9. verify_sha256_stream(temp_path, expected_sha256) → bool
10. If verification fails: delete temp file, exit 1 with error
11. install_dir.mkdir(parents=True, exist_ok=True)
12. temp_path.rename(install_path)  # atomic on same filesystem
13. make_executable(install_path)  # Linux/macOS/WSL2 only
14. ensure_in_path(install_dir) → if False: add_to_shell_profile(install_dir)
15. Print success: installed version, path, PATH status
```

---

## Script Skeleton

```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "httpx>=0.28.1",
# ]
# ///
"""Install or update dasel binary from GitHub Releases.

Supports: Linux x86_64/arm64, macOS amd64/arm64, Windows amd64, WSL2.
Installs to user-space (~/.local/bin on Linux/WSL2/macOS, %LOCALAPPDATA%\Programs\dasel on Windows).
Verifies SHA256 from GitHub API asset digest field.
"""
from __future__ import annotations

import hashlib
import os
import platform
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.console import Console

GITHUB_API_URL = 'https://api.github.com/repos/TomWright/dasel/releases/latest'

console = Console()
error_console = Console(stderr=True, style='bold red')

app = typer.Typer(help='Install or update dasel binary')

@app.command()
def main(
    force: Annotated[bool, typer.Option('--force', help='Reinstall even if already at latest')] = False,
    dry_run: Annotated[bool, typer.Option('--dry-run', help='Show what would happen without installing')] = False,
    bin_dir: Annotated[Path | None, typer.Option('--bin-dir', help='Override install directory')] = None,
) -> None:
    ...

if __name__ == '__main__':
    app()
```

---

## Sources

- GitHub Releases API response for TomWright/dasel — fetched 2026-02-19, tag v3.2.2
- `/proc/version` content on this system — read directly 2026-02-19
- `platform.system()`, `platform.machine()` output — executed 2026-02-19
- `os.environ['PATH']` on this system — `~/.local/bin` confirmed in PATH
- `plugins/python3-development/skills/uv/scripts/sync_uv_releases.py` — PEP 723 shebang pattern and httpx GitHub API pattern, lines 1-8, 190-233
- `plugins/holistic-linting/skills/holistic-linting/scripts/install_agents.py` — file install with hash comparison, lines 65-81, 110-168
- `plugins/gitlab-skill/commands/setup-ci-publish-token.sh` — only Bash install script in repo (POSIX sh, legacy)
- Project CLAUDE.md: "Language Conventions" section — Python PEP 723 for companion scripts, confirmed by "27+ scripts in plugins/**/scripts/"
