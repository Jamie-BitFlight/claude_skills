#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "httpx>=0.28.1",
# ]
# ///
r"""Install or update the dasel binary from GitHub Releases.

Supports Linux x86_64/arm64, macOS amd64/arm64, Windows amd64, and WSL2.
Installs to user-space (~/.local/bin on Linux/WSL2/macOS,
%LOCALAPPDATA%\\Programs\\dasel on Windows).
Verifies SHA256 from the GitHub API asset digest field.
"""

from __future__ import annotations

import hashlib
import os
import platform
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx
import typer
from rich.console import Console

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GITHUB_API_URL = "https://api.github.com/repos/TomWright/dasel/releases/latest"
BINARY_NAME = "dasel"
DOWNLOAD_CHUNK_SIZE = 8192
HTTP_OK = 200

ARCH_MAP: dict[str, str] = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
    "armv7l": "arm32",
    "i386": "386",
    "i686": "386",
}

# ---------------------------------------------------------------------------
# Console setup
# ---------------------------------------------------------------------------
console = Console()
error_console = Console(stderr=True, style="bold red")

app = typer.Typer(
    name="install_dasel", help="Install or update the dasel binary from GitHub Releases.", rich_markup_mode="rich"
)


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------
class UnsupportedPlatformError(Exception):
    """Raised when the current platform or architecture is not supported."""


def is_wsl2() -> bool:
    """Detect WSL2 by checking /proc/version for 'microsoft'.

    Returns:
        True if running inside WSL2, False otherwise.
    """
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def detect_platform() -> tuple[str, str]:
    """Detect the OS and architecture, normalized to dasel asset naming.

    Returns:
        Tuple of (os_key, arch_key) matching dasel release asset names.

    Raises:
        UnsupportedPlatformError: If the architecture cannot be mapped.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    arch = ARCH_MAP.get(machine)
    if arch is None:
        msg = f"Unsupported architecture: {machine}"
        raise UnsupportedPlatformError(msg)

    # WSL2 uses Linux binaries -- no special handling needed
    if system == "linux":
        # Detection is informational; binary selection is linux regardless
        _ = is_wsl2()
        return "linux", arch

    if system not in {"darwin", "windows"}:
        msg = f"Unsupported operating system: {system}"
        raise UnsupportedPlatformError(msg)

    return system, arch


# ---------------------------------------------------------------------------
# Install directory resolution
# ---------------------------------------------------------------------------
def default_install_dir(os_key: str) -> Path:
    """Return the platform-appropriate default install directory.

    Args:
        os_key: Operating system key ('linux', 'darwin', or 'windows').

    Returns:
        Path to the default binary install directory.
    """
    if os_key == "windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "Programs" / "dasel"
        return Path.home() / "AppData" / "Local" / "Programs" / "dasel"
    # Linux, macOS, WSL2
    return Path.home() / ".local" / "bin"


def binary_filename(os_key: str) -> str:
    """Return the binary filename for the platform.

    Args:
        os_key: Operating system key.

    Returns:
        'dasel.exe' on Windows, 'dasel' otherwise.
    """
    return f"{BINARY_NAME}.exe" if os_key == "windows" else BINARY_NAME


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    """Metadata for a single GitHub release asset."""

    name: str
    url: str
    digest: str
    size: int


class GitHubAPIError(Exception):
    """Raised when the GitHub Releases API returns an unexpected response."""


def fetch_latest_release(timeout: float = 30.0) -> tuple[str, list[ReleaseAsset]]:
    """Fetch the latest dasel release metadata from GitHub.

    Args:
        timeout: HTTP request timeout in seconds.

    Returns:
        Tuple of (version_tag, list_of_assets).

    Raises:
        GitHubAPIError: On non-200 responses or missing fields.
        httpx.HTTPError: On network-level failures.
    """
    with httpx.Client(timeout=timeout) as client:
        response = client.get(GITHUB_API_URL, headers={"Accept": "application/vnd.github+json"})
        if response.status_code != HTTP_OK:
            msg = f"GitHub API returned status {response.status_code}: {response.text}"
            raise GitHubAPIError(msg)

        data = response.json()

    tag_name: str = data.get("tag_name", "")
    if not tag_name:
        msg = "GitHub API response missing 'tag_name'"
        raise GitHubAPIError(msg)

    assets: list[ReleaseAsset] = [
        ReleaseAsset(
            name=raw.get("name", ""),
            url=raw.get("browser_download_url", ""),
            digest=raw.get("digest", ""),
            size=raw.get("size", 0),
        )
        for raw in data.get("assets", [])
    ]

    return tag_name, assets


def find_asset(assets: list[ReleaseAsset], os_key: str, arch: str) -> ReleaseAsset | None:
    """Find the matching binary asset for the given platform.

    Args:
        assets: List of release assets from the GitHub API.
        os_key: Operating system key.
        arch: Architecture key.

    Returns:
        Matching ReleaseAsset, or None if no match found.
    """
    target_name = f"dasel_{os_key}_{arch}.exe" if os_key == "windows" else f"dasel_{os_key}_{arch}"

    for asset in assets:
        if asset.name == target_name:
            return asset
    return None


# ---------------------------------------------------------------------------
# Version comparison
# ---------------------------------------------------------------------------
def parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a version string into a comparable tuple of integers.

    Strips leading 'v' and splits on '.', keeping only numeric parts.

    Args:
        version_str: Version string such as 'v3.2.2' or '3.2.2'.

    Returns:
        Tuple of integers for comparison.
    """
    cleaned = version_str.lstrip("v")
    return tuple(int(part) for part in cleaned.split(".") if part.isdigit())


def get_installed_version(binary_path: Path) -> str | None:
    """Get the version of the currently installed dasel binary.

    Args:
        binary_path: Full path to the dasel binary.

    Returns:
        Version string without leading 'v', or None if not installed.
    """
    if not binary_path.exists():
        return None
    try:
        result = subprocess.run([str(binary_path), "--version"], check=False, capture_output=True, text=True, timeout=5)
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    else:
        output = result.stdout.strip() or result.stderr.strip()
        # Expected: "dasel version v3.2.2"
        for part in output.split():
            if part.startswith("v") and part[1:].replace(".", "").isdigit():
                return part.lstrip("v")
        return output or None


# ---------------------------------------------------------------------------
# Download and verification
# ---------------------------------------------------------------------------
class SHA256MismatchError(Exception):
    """Raised when SHA256 verification fails."""


def download_binary(url: str, dest: Path, timeout: float = 120.0) -> None:
    """Stream-download a binary from the given URL to a local file.

    Args:
        url: Download URL for the binary asset.
        dest: Local file path to write to.
        timeout: HTTP request timeout in seconds.

    Raises:
        httpx.HTTPStatusError: On non-2xx responses.
        httpx.HTTPError: On network-level failures.
    """
    with httpx.Client(timeout=timeout, follow_redirects=True) as client, client.stream("GET", url) as response:
        response.raise_for_status()
        with dest.open("wb") as f:
            for chunk in response.iter_bytes(chunk_size=DOWNLOAD_CHUNK_SIZE):
                f.write(chunk)


def verify_sha256(file_path: Path, expected_hex: str) -> None:
    """Verify the SHA256 hash of a downloaded file.

    Args:
        file_path: Path to the file to verify.
        expected_hex: Expected SHA256 hex digest.

    Raises:
        SHA256MismatchError: If the computed hash does not match.
    """
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(DOWNLOAD_CHUNK_SIZE):
            sha256.update(chunk)

    actual = sha256.hexdigest()
    if actual != expected_hex:
        msg = f"SHA256 mismatch: expected {expected_hex}, got {actual}"
        raise SHA256MismatchError(msg)


# ---------------------------------------------------------------------------
# Post-install
# ---------------------------------------------------------------------------
def make_executable(path: Path) -> None:
    """Set the executable bit on a file (Linux/macOS/WSL2).

    Args:
        path: Path to the binary file.
    """
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def check_path(bin_dir: Path) -> bool:
    """Check whether a directory is on the current PATH.

    Args:
        bin_dir: Directory to check.

    Returns:
        True if bin_dir is in PATH, False otherwise.
    """
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    return str(bin_dir) in path_dirs


def suggest_path_update(install_dir: Path, os_key: str) -> None:
    """Print PATH update suggestions if the install directory is not in PATH.

    Args:
        install_dir: Directory where the binary was installed.
        os_key: Operating system key.
    """
    if check_path(install_dir):
        return

    console.print(f"\n:warning: [yellow]{install_dir} is not in your PATH.[/yellow]\n  Add it to your shell profile:")
    if os_key == "windows":
        console.print(f'  [dim]$env:PATH += ";{install_dir}"[/dim]  (PowerShell, temporary)')
    else:
        console.print(f'  [dim]export PATH="{install_dir}:$PATH"[/dim]  (add to ~/.bashrc or ~/.zshrc)')


# ---------------------------------------------------------------------------
# Resolve release context (fetching, matching, validating)
# ---------------------------------------------------------------------------
def resolve_release(os_key: str, arch: str) -> tuple[str, ReleaseAsset, str]:
    """Fetch the latest release and locate the matching asset.

    Args:
        os_key: Operating system key.
        arch: Architecture key.

    Returns:
        Tuple of (latest_version, asset, expected_sha256).

    Raises:
        typer.Exit: On API errors, missing assets, or missing digests.
    """
    console.print(":globe_with_meridians: Fetching latest dasel release...")
    try:
        tag, assets = fetch_latest_release()
    except (GitHubAPIError, httpx.HTTPError) as exc:
        error_console.print(f":cross_mark: Failed to fetch release info: {exc}")
        raise typer.Exit(code=1) from exc

    latest_version = tag.lstrip("v")
    console.print(f":package: Latest version: [green]v{latest_version}[/green]")

    asset = find_asset(assets, os_key, arch)
    if asset is None:
        error_console.print(f":cross_mark: No binary found for {os_key}_{arch} in release {tag}")
        raise typer.Exit(code=1)

    expected_sha256 = asset.digest.removeprefix("sha256:")
    if not expected_sha256 or expected_sha256 == asset.digest:
        error_console.print(":cross_mark: Release asset is missing a sha256 digest")
        raise typer.Exit(code=1)

    return latest_version, asset, expected_sha256


def print_dry_run_summary(
    asset: ReleaseAsset, expected_sha256: str, install_dir: Path, install_path: Path, os_key: str
) -> None:
    """Print what would happen during a real install.

    Args:
        asset: The matched release asset.
        expected_sha256: Expected SHA256 hex digest.
        install_dir: Target install directory.
        install_path: Full binary path.
        os_key: Operating system key.
    """
    console.print("\n[bold]Dry-run summary:[/bold]")
    console.print(f"  Asset:       {asset.name}")
    console.print(f"  URL:         {asset.url}")
    console.print(f"  SHA256:      {expected_sha256}")
    console.print(f"  Size:        {asset.size:,} bytes")
    console.print(f"  Install dir: {install_dir}")
    console.print(f"  Binary path: {install_path}")
    if os_key != "windows":
        console.print("  Executable:  chmod +x will be applied")
    in_path = check_path(install_dir)
    console.print(f"  In PATH:     {'yes' if in_path else 'no'}")


def download_and_install(
    asset: ReleaseAsset, expected_sha256: str, install_dir: Path, install_path: Path, os_key: str, latest_version: str
) -> None:
    """Download, verify, and install the dasel binary.

    Args:
        asset: The matched release asset.
        expected_sha256: Expected SHA256 hex digest.
        install_dir: Target install directory.
        install_path: Full binary path.
        os_key: Operating system key.
        latest_version: Version string for the installed binary.

    Raises:
        typer.Exit: On download or verification failure.
    """
    install_dir.mkdir(parents=True, exist_ok=True)

    # Download to temp file in same directory (for atomic rename)
    console.print(f":arrow_down: Downloading {asset.name} ({asset.size:,} bytes)...")
    tmp_fd, tmp_path_str = tempfile.mkstemp(dir=install_dir, prefix=".dasel_tmp_")
    tmp_path = Path(tmp_path_str)
    os.close(tmp_fd)

    try:
        download_binary(asset.url, tmp_path)
    except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
        tmp_path.unlink(missing_ok=True)
        error_console.print(f":cross_mark: Download failed: {exc}")
        raise typer.Exit(code=1) from exc

    # Verify SHA256
    console.print(":lock: Verifying SHA256 checksum...")
    try:
        verify_sha256(tmp_path, expected_sha256)
    except SHA256MismatchError as exc:
        tmp_path.unlink(missing_ok=True)
        error_console.print(f":cross_mark: {exc}")
        raise typer.Exit(code=1) from exc

    console.print(":white_check_mark: SHA256 verified")

    # Move to final location
    tmp_path.replace(install_path)

    # Set executable bit (non-Windows)
    if os_key != "windows":
        make_executable(install_path)

    console.print(f":white_check_mark: [green]dasel v{latest_version} installed to {install_path}[/green]")


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------
@app.command()
def main(
    force: Annotated[bool, typer.Option("--force", help="Reinstall even if already at latest version")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would happen without installing")] = False,
    bin_dir: Annotated[
        Path | None,
        typer.Option(
            "--bin-dir", help="Override install directory (default: ~/.local/bin or %%LOCALAPPDATA%%\\Programs\\dasel)"
        ),
    ] = None,
) -> None:
    """Install or update the dasel binary from GitHub Releases.

    Detects the current platform and architecture, fetches the latest release,
    verifies the SHA256 checksum, and installs the binary to a user-space
    directory.

    Args:
        force: Reinstall even if the installed version matches the latest.
        dry_run: Print planned actions without performing them.
        bin_dir: Override the default install directory.

    Raises:
        typer.Exit: On any failure condition.
    """
    # 1. Detect platform
    try:
        os_key, arch = detect_platform()
    except UnsupportedPlatformError as exc:
        error_console.print(f":cross_mark: {exc}")
        raise typer.Exit(code=1) from exc

    wsl2 = os_key == "linux" and is_wsl2()
    platform_label = f"{os_key}/{arch}" + (" (WSL2)" if wsl2 else "")
    console.print(f":magnifying_glass_tilted_left: Detected platform: [cyan]{platform_label}[/cyan]")

    # 2. Resolve install directory and binary path
    install_dir = bin_dir if bin_dir is not None else default_install_dir(os_key)
    install_path = install_dir / binary_filename(os_key)

    # 3. Fetch latest release and find matching asset
    latest_version, asset, expected_sha256 = resolve_release(os_key, arch)

    # 4. Check installed version
    installed_version = get_installed_version(install_path)
    if installed_version:
        console.print(f":floppy_disk: Installed version: [yellow]v{installed_version}[/yellow]")
    else:
        console.print(":floppy_disk: dasel is not currently installed")

    needs_update = installed_version is None or parse_version(installed_version) < parse_version(latest_version)

    if not needs_update and not force:
        console.print(":white_check_mark: [green]dasel is already up to date[/green]")
        raise typer.Exit(code=0)

    if not needs_update and force:
        console.print(":arrows_counterclockwise: Force-reinstalling latest version")

    # 5. Dry-run or install
    if dry_run:
        print_dry_run_summary(asset, expected_sha256, install_dir, install_path, os_key)
        raise typer.Exit(code=0)

    download_and_install(asset, expected_sha256, install_dir, install_path, os_key, latest_version)
    suggest_path_update(install_dir, os_key)


if __name__ == "__main__":
    app()
