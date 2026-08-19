#!/usr/bin/env python3
"""Validate Codex plugin installation and runtime behavior in isolation."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import git

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_ROOT = REPO_ROOT / "plugins"
MARKETPLACE_NAME = "isolated-codex-plugin-validation"
DEFAULT_PLUGIN = "xdg-base-directory"
DEFAULT_PROMPT = (
    "You are validating the xdg-base-directory plugin in an isolated Codex install. "
    "Answer with the correct XDG directories for config, data, cache, state, and runtime "
    "files. Do not read the source repository by path or use repo-relative plugin files."
)
DEFAULT_PATH_PREFIX = "~/.local/bin:~/.volta/bin"


class HarnessError(RuntimeError):
    """Raised when the isolated validation harness cannot proceed."""


@dataclass(frozen=True)
class ValidationWorkspace:
    """Paths for a single isolated marketplace validation run."""

    root: Path
    mode: str
    marketplace_name: str
    marketplace_source: Path
    marketplace_path: Path
    plugin_dir: Path
    plugin_id: str
    project_dir: Path
    codex_home: Path


def create_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Build an isolated temp marketplace tree for exactly one Codex plugin, then "
            "either print or execute the Codex marketplace/install/exec smoke sequence. "
            "Use --package-only to stop after marketplace registration and installation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/validate_codex_plugin_isolated.py\n"
            "  python scripts/validate_codex_plugin_isolated.py --plugin xdg-base-directory --zip-unzip\n"
            "  python scripts/validate_codex_plugin_isolated.py --run --output-file /tmp/xdg.txt\n"
        ),
    )
    parser.add_argument(
        "--plugin",
        default=DEFAULT_PLUGIN,
        help="Plugin directory name under plugins/ to validate (default: xdg-base-directory).",
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Smoke prompt to send to codex exec.")
    parser.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help=("Path for codex exec's -o output file. Defaults to <cwd>/<plugin>.codex-smoke.txt."),
    )
    parser.add_argument(
        "--path-prefix",
        default=DEFAULT_PATH_PREFIX,
        help=("PATH prefix to prepend before invoking Codex. Defaults to ~/.local/bin:~/.volta/bin."),
    )
    parser.add_argument(
        "--distribution-mode",
        choices=("repo", "copy"),
        default="repo",
        help=(
            "Validation source: 'repo' uses the repository marketplace root as the Codex "
            "install source; 'copy' copies exactly one plugin into a temp marketplace tree. "
            "Default: repo."
        ),
    )
    parser.add_argument(
        "--zip-unzip",
        action="store_true",
        help=(
            "Zip and re-extract the copied plugin before installation to simulate distribution. "
            "Valid only with --distribution-mode copy."
        ),
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the Codex marketplace/install/exec smoke flow instead of printing commands.",
    )
    parser.add_argument(
        "--package-only",
        action="store_true",
        help=(
            "With --run, register and install the plugin but skip codex exec/model work. "
            "Cannot be combined with --copy-auth-from-current-home."
        ),
    )
    parser.add_argument(
        "--copy-auth-from-current-home",
        action="store_true",
        help=(
            "Copy auth.json from the current Codex home into the temp CODEX_HOME before "
            "running. This is opt-in because auth.json contains credentials."
        ),
    )
    parser.add_argument(
        "--keep-tempdir",
        action="store_true",
        help=(
            "Preserve the generated temp workspace after a run. Avoid combining this with "
            "--copy-auth-from-current-home unless you intend to keep a temp copy of auth.json."
        ),
    )
    parser.add_argument(
        "--git-project",
        action="store_true",
        help="Initialize the isolated project directory as a Git repository before running Codex.",
    )
    return parser


def resolve_plugin_dir(plugin_name: str) -> Path:
    """Resolve the source plugin directory from the repository.

    Returns:
        The plugin directory path.
    """
    plugin_dir = PLUGINS_ROOT / plugin_name
    if not plugin_dir.is_dir():
        available = ", ".join(sorted(entry.name for entry in PLUGINS_ROOT.iterdir() if entry.is_dir()))
        raise HarnessError(f"Plugin '{plugin_name}' was not found under {PLUGINS_ROOT}. Available plugins: {available}")
    return plugin_dir


def load_plugin_id(plugin_dir: Path) -> str:
    """Read and validate the Codex plugin ID from a plugin manifest.

    Returns:
        The plugin identifier.
    """
    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    if not manifest_path.is_file():
        raise HarnessError(f"Plugin manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise HarnessError(f"Plugin manifest must be a JSON object: {manifest_path}")
    plugin_id = manifest.get("name")
    if not isinstance(plugin_id, str) or not plugin_id:
        raise HarnessError(f"Plugin name is missing in {manifest_path}")
    return plugin_id


def expand_path_prefix(path_prefix: str) -> str:
    """Expand a PATH prefix string without mutating the user's shell environment.

    Returns:
        The expanded, path-separated prefix.
    """
    parts = [str(Path(part).expanduser()) for part in path_prefix.split(os.pathsep) if part]
    return os.pathsep.join(parts)


def create_temp_workspace(plugin_name: str) -> ValidationWorkspace:
    """Create an isolated temp tree that owns its copied plugin and marketplace metadata.

    Returns:
        The isolated validation workspace.
    """
    root = Path(tempfile.mkdtemp(prefix=f"codex-plugin-{plugin_name}-"))
    plugins_root = root / "plugins"
    plugins_root.mkdir(parents=True, exist_ok=True)

    source_plugin_dir = resolve_plugin_dir(plugin_name)
    for source_path in source_plugin_dir.rglob("*"):
        if ".venv" in source_path.relative_to(source_plugin_dir).parts:
            continue
        if source_path.is_symlink() and not source_path.resolve().is_relative_to(source_plugin_dir.resolve()):
            raise HarnessError(f"Plugin contains a symlink outside its distribution: {source_path}")
    copied_plugin_dir = plugins_root / plugin_name
    shutil.copytree(source_plugin_dir, copied_plugin_dir, ignore=shutil.ignore_patterns(".venv", "__pycache__"))
    plugin_id = load_plugin_id(copied_plugin_dir)

    marketplace_root = root / ".agents" / "plugins"
    marketplace_root.mkdir(parents=True, exist_ok=True)
    marketplace_path = marketplace_root / "marketplace.json"
    write_marketplace_json(marketplace_path, plugin_id, plugin_name)

    project_dir = root / "project"
    project_dir.mkdir(parents=True, exist_ok=True)

    codex_home = root / "codex-home"
    codex_home.mkdir(parents=True, exist_ok=True)

    return ValidationWorkspace(
        root=root,
        mode="copy",
        marketplace_name=MARKETPLACE_NAME,
        marketplace_source=root,
        marketplace_path=marketplace_path,
        plugin_dir=copied_plugin_dir,
        plugin_id=plugin_id,
        project_dir=project_dir,
        codex_home=codex_home,
    )


def load_repo_marketplace_name() -> str:
    """Read the repository marketplace name from .agents/plugins/marketplace.json.

    Returns:
        The marketplace identifier.
    """
    marketplace_path = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
    if not marketplace_path.is_file():
        raise HarnessError(f"Repository marketplace file is missing: {marketplace_path}")
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    name = marketplace.get("name")
    if not isinstance(name, str) or not name:
        raise HarnessError(f"Repository marketplace name is missing in {marketplace_path}")
    return name


def create_repo_workspace(plugin_name: str) -> ValidationWorkspace:
    """Create an isolated temp Codex home that installs from the repository marketplace root.

    Returns:
        The isolated validation workspace.
    """
    root = Path(tempfile.mkdtemp(prefix=f"codex-plugin-{plugin_name}-"))
    project_dir = root / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    codex_home = root / "codex-home"
    codex_home.mkdir(parents=True, exist_ok=True)
    plugin_dir = resolve_plugin_dir(plugin_name)
    marketplace_path = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
    plugin_id = load_plugin_id(plugin_dir)

    return ValidationWorkspace(
        root=root,
        mode="repo",
        marketplace_name=load_repo_marketplace_name(),
        marketplace_source=REPO_ROOT,
        marketplace_path=marketplace_path,
        plugin_dir=plugin_dir,
        plugin_id=plugin_id,
        project_dir=project_dir,
        codex_home=codex_home,
    )


def _initialize_git_project(workspace: ValidationWorkspace) -> None:
    git.Repo.init(workspace.project_dir)


def write_marketplace_json(marketplace_path: Path, plugin_id: str, plugin_name: str) -> None:
    """Write the smallest marketplace file needed to expose one isolated plugin."""
    marketplace = {
        "name": MARKETPLACE_NAME,
        "interface": {"displayName": "Isolated Codex Plugin Validation"},
        "plugins": [
            {
                "name": plugin_id,
                "source": {"source": "local", "path": f"./plugins/{plugin_name}"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Developer Tools",
            }
        ],
    }
    marketplace_path.write_text(json.dumps(marketplace, indent=2) + "\n", encoding="utf-8")


def maybe_zip_unzip_plugin(workspace: ValidationWorkspace, plugin_name: str) -> Path:
    """Round-trip the copied plugin through zip/unzip inside the temp tree.

    Returns:
        The temporary archive path.
    """
    plugin_dir = workspace.plugin_dir
    archive_path = workspace.root / f"{plugin_name}.zip"

    with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(plugin_dir.rglob("*")):
            relative = path.relative_to(plugin_dir.parent)
            if path.is_dir():
                continue
            archive.write(path, relative)

    shutil.rmtree(plugin_dir)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(workspace.plugin_dir.parent)

    return archive_path


def default_output_file(plugin_name: str) -> Path:
    """Choose a stable output file path outside the temp workspace.

    Returns:
        The default smoke output path.
    """
    return Path.cwd() / f"{plugin_name}.codex-smoke.txt"


def _resolve_output_file(output_file: Path | None, plugin_name: str) -> Path:
    return (output_file or default_output_file(plugin_name)).expanduser().resolve()


def current_codex_home() -> Path:
    """Return the active Codex home outside the temp validation workspace."""
    return Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()


def copy_auth_from_current_home(workspace: ValidationWorkspace) -> Path:
    """Copy file-backed Codex auth into the temp CODEX_HOME when explicitly requested.

    Returns:
        The copied authentication file path.
    """
    source_auth = current_codex_home() / "auth.json"
    if not source_auth.is_file():
        raise HarnessError(
            f"Cannot copy auth: {source_auth} does not exist. "
            "Use CODEX_ACCESS_TOKEN in the environment or log in with Codex first."
        )

    destination_auth = workspace.codex_home / "auth.json"
    shutil.copy2(source_auth, destination_auth)
    destination_auth.chmod(0o600)
    return destination_auth


def build_command_strings(
    workspace: ValidationWorkspace, prompt: str, output_file: Path, path_prefix: str
) -> list[str]:
    """Return shell-readable command strings for the isolated validation flow."""
    expanded_prefix = expand_path_prefix(path_prefix)
    env_parts = [f"CODEX_HOME={shlex.quote(str(workspace.codex_home))}"]
    if expanded_prefix:
        env_parts.append(f"PATH={shlex.quote(expanded_prefix)}:$PATH")
    env_prefix = " ".join(env_parts)
    marketplace_cmd = f"{env_prefix} codex plugin marketplace add {shlex.quote(str(workspace.marketplace_source))}"
    install_cmd = f"{env_prefix} codex plugin add {shlex.quote(f'{workspace.plugin_id}@{workspace.marketplace_name}')}"
    exec_cmd = f"{env_prefix} codex exec --skip-git-repo-check -o {shlex.quote(str(output_file))} {shlex.quote(prompt)}"
    return [marketplace_cmd, install_cmd, exec_cmd]


def build_env(path_prefix: str, codex_home: Path) -> dict[str, str]:
    """Prepare the subprocess environment for Codex commands.

    Returns:
        The environment mapping for subprocess execution.
    """
    env = os.environ.copy()
    expanded_prefix = expand_path_prefix(path_prefix)
    if expanded_prefix:
        env["PATH"] = f"{expanded_prefix}{os.pathsep}{env.get('PATH', '')}" if env.get("PATH") else expanded_prefix
    env["CODEX_HOME"] = str(codex_home)
    return env


def run_command(argv: list[str], *, cwd: Path, env: dict[str, str], label: str) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and echo its output in a readable form.

    Returns:
        The completed subprocess result.
    """
    print(f"[{label}] {' '.join(shlex.quote(part) for part in argv)}")
    completed = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(completed.stderr, end="" if completed.stderr.endswith("\n") else "\n", file=sys.stderr)
    if completed.returncode != 0:
        raise HarnessError(f"{label} failed with exit code {completed.returncode}")
    return completed


def print_plan(
    workspace: ValidationWorkspace, prompt: str, output_file: Path, path_prefix: str, zip_archive: Path | None
) -> None:
    """Print the dry-run plan and commands."""
    print("Isolated Codex plugin validation plan")
    print(f"  distribution:   {workspace.mode}")
    print(f"  temp workspace: {workspace.root}")
    print(f"  plugin source:  {workspace.plugin_dir}")
    print(f"  plugin id:      {workspace.plugin_id}")
    print(f"  marketplace:    {workspace.marketplace_path}")
    print(f"  source root:    {workspace.marketplace_source}")
    print(f"  marketplace id: {workspace.marketplace_name}")
    print(f"  codex home:     {workspace.codex_home}")
    print(f"  project dir:    {workspace.project_dir}")
    print(f"  output file:    {output_file}")
    if zip_archive is not None:
        print(f"  zip archive:    {zip_archive}")
    print("  auth:           not copied in dry-run output")
    print()
    print("Commands to run:")
    for command in build_command_strings(workspace, prompt, output_file, path_prefix):
        print(f"  {command}")


def cleanup_workspace(workspace: ValidationWorkspace) -> None:
    """Remove the temp tree only when it is safe to do so."""
    if workspace.root.is_dir() and workspace.root.name.startswith("codex-plugin-"):
        shutil.rmtree(workspace.root)


def validate_args(args: argparse.Namespace) -> None:
    """Reject combinations that cannot produce a valid isolated run."""
    if args.package_only and not args.run:
        raise HarnessError("--package-only requires --run")
    if args.package_only and args.copy_auth_from_current_home:
        raise HarnessError("--package-only cannot be combined with --copy-auth-from-current-home")
    if args.zip_unzip and args.distribution_mode != "copy":
        raise HarnessError("--zip-unzip requires --distribution-mode copy")


def main() -> int:
    """Run the isolated Codex plugin validation harness.

    Returns:
        Zero on success, otherwise one.
    """
    parser = create_parser()
    args = parser.parse_args()
    workspace: ValidationWorkspace | None = None

    try:
        validate_args(args)
        workspace = (
            create_repo_workspace(args.plugin)
            if args.distribution_mode == "repo"
            else create_temp_workspace(args.plugin)
        )
        if args.git_project:
            _initialize_git_project(workspace)
        zip_archive = maybe_zip_unzip_plugin(workspace, args.plugin) if args.zip_unzip else None
        output_file = _resolve_output_file(args.output_file, args.plugin)

        if not args.run:
            print_plan(workspace, args.prompt, output_file, args.path_prefix, zip_archive)
            print()
            print("Dry run only: temp workspace preserved so the printed commands remain usable.")
            if args.copy_auth_from_current_home:
                print(
                    "Note: --copy-auth-from-current-home is only applied with --run; "
                    "no auth file was copied during this dry run."
                )
            return 0

        if args.copy_auth_from_current_home:
            copied_auth = copy_auth_from_current_home(workspace)
            print(f"Copied Codex auth into temp home: {copied_auth}")

        env = build_env(args.path_prefix, workspace.codex_home)
        print(f"Workspace: {workspace.root}")
        if zip_archive is not None:
            print(f"Distribution archive: {zip_archive}")

        run_command(
            ["codex", "plugin", "marketplace", "add", str(workspace.marketplace_source)],
            cwd=workspace.project_dir,
            env=env,
            label="marketplace",
        )
        run_command(
            ["codex", "plugin", "add", f"{workspace.plugin_id}@{workspace.marketplace_name}"],
            cwd=workspace.project_dir,
            env=env,
            label="install",
        )
        if args.package_only:
            print("Package-only validation complete: marketplace registered and plugin installed; codex exec skipped.")
            return 0

        run_command(
            ["codex", "exec", "--skip-git-repo-check", "-o", str(output_file), args.prompt],
            cwd=workspace.project_dir,
            env=env,
            label="exec",
        )
    except (HarnessError, OSError, subprocess.SubprocessError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    else:
        print(f"Smoke output written to: {output_file}")
        return 0
    finally:
        if workspace is not None and args.run and not args.keep_tempdir:
            cleanup_workspace(workspace)


if __name__ == "__main__":
    raise SystemExit(main())
