#!/usr/bin/env python3

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
    marketplace_path: Path
    copied_plugin_dir: Path
    project_dir: Path
    codex_home: Path


def create_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Build an isolated temp marketplace tree for exactly one Codex plugin, then "
            "either print or execute the Codex marketplace/install/exec smoke sequence."
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
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Smoke prompt to send to codex exec.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help=(
            "Path for codex exec's -o output file. Defaults to <cwd>/<plugin>.codex-smoke.txt."
        ),
    )
    parser.add_argument(
        "--path-prefix",
        default=DEFAULT_PATH_PREFIX,
        help=(
            "PATH prefix to prepend before invoking Codex. "
            "Defaults to ~/.local/bin:~/.volta/bin."
        ),
    )
    parser.add_argument(
        "--zip-unzip",
        action="store_true",
        help="Zip and re-extract the copied plugin before installation to simulate distribution.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the Codex marketplace/install/exec smoke flow instead of printing commands.",
    )
    parser.add_argument(
        "--keep-tempdir",
        action="store_true",
        help="Preserve the generated temp workspace after a run.",
    )
    return parser


def title_case_from_kebab(name: str) -> str:
    """Return a simple title-cased label for a kebab-case identifier."""

    return " ".join(part.capitalize() for part in name.split("-") if part)


def resolve_plugin_dir(plugin_name: str) -> Path:
    """Resolve the source plugin directory from the repository."""

    plugin_dir = PLUGINS_ROOT / plugin_name
    if not plugin_dir.is_dir():
        available = ", ".join(sorted(entry.name for entry in PLUGINS_ROOT.iterdir() if entry.is_dir()))
        raise HarnessError(
            f"Plugin '{plugin_name}' was not found under {PLUGINS_ROOT}. "
            f"Available plugins: {available}"
        )
    return plugin_dir


def expand_path_prefix(path_prefix: str) -> str:
    """Expand a PATH prefix string without mutating the user's shell environment."""

    parts = [os.path.expanduser(part) for part in path_prefix.split(os.pathsep) if part]
    return os.pathsep.join(parts)


def create_temp_workspace(plugin_name: str) -> ValidationWorkspace:
    """Create an isolated temp tree that owns its copied plugin and marketplace metadata."""

    root = Path(tempfile.mkdtemp(prefix=f"codex-plugin-{plugin_name}-"))
    plugins_root = root / "plugins"
    plugins_root.mkdir(parents=True, exist_ok=True)

    source_plugin_dir = resolve_plugin_dir(plugin_name)
    copied_plugin_dir = plugins_root / plugin_name
    shutil.copytree(source_plugin_dir, copied_plugin_dir)

    marketplace_root = root / ".agents" / "plugins"
    marketplace_root.mkdir(parents=True, exist_ok=True)
    marketplace_path = marketplace_root / "marketplace.json"
    write_marketplace_json(marketplace_path, plugin_name)

    project_dir = root / "project"
    project_dir.mkdir(parents=True, exist_ok=True)

    codex_home = root / "codex-home"
    codex_home.mkdir(parents=True, exist_ok=True)

    return ValidationWorkspace(
        root=root,
        marketplace_path=marketplace_path,
        copied_plugin_dir=copied_plugin_dir,
        project_dir=project_dir,
        codex_home=codex_home,
    )


def write_marketplace_json(marketplace_path: Path, plugin_name: str) -> None:
    """Write the smallest marketplace file needed to expose one isolated plugin."""

    marketplace = {
        "name": MARKETPLACE_NAME,
        "interface": {
            "displayName": "Isolated Codex Plugin Validation",
        },
        "plugins": [
            {
                "name": plugin_name,
                "source": {
                    "source": "local",
                    "path": f"./plugins/{plugin_name}",
                },
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": "Developer Tools",
            }
        ],
    }
    marketplace_path.write_text(json.dumps(marketplace, indent=2) + "\n", encoding="utf-8")


def maybe_zip_unzip_plugin(workspace: ValidationWorkspace, plugin_name: str) -> Path:
    """Round-trip the copied plugin through zip/unzip inside the temp tree."""

    plugin_dir = workspace.copied_plugin_dir
    archive_path = workspace.root / f"{plugin_name}.zip"

    with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(plugin_dir.rglob("*")):
            relative = path.relative_to(plugin_dir.parent)
            if path.is_dir():
                continue
            archive.write(path, relative)

    shutil.rmtree(plugin_dir)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(workspace.copied_plugin_dir.parent)

    return archive_path


def default_output_file(plugin_name: str) -> Path:
    """Choose a stable output file path outside the temp workspace."""

    return Path.cwd() / f"{plugin_name}.codex-smoke.txt"


def build_command_strings(
    workspace: ValidationWorkspace,
    plugin_name: str,
    prompt: str,
    output_file: Path,
    path_prefix: str,
) -> list[str]:
    """Return shell-readable command strings for the isolated validation flow."""

    expanded_prefix = expand_path_prefix(path_prefix)
    env_parts = [f"CODEX_HOME={shlex.quote(str(workspace.codex_home))}"]
    if expanded_prefix:
        env_parts.append(f"PATH={shlex.quote(expanded_prefix)}:$PATH")
    env_prefix = " ".join(env_parts)
    marketplace_cmd = (
        f"{env_prefix} codex plugin marketplace add {shlex.quote(str(workspace.marketplace_path))}"
    )
    install_cmd = (
        f"{env_prefix} codex plugin add {shlex.quote(f'{plugin_name}@{MARKETPLACE_NAME}')}"
    )
    exec_cmd = (
        f"{env_prefix} codex exec --skip-git-repo-check -o {shlex.quote(str(output_file))} "
        f"{shlex.quote(prompt)}"
    )
    return [marketplace_cmd, install_cmd, exec_cmd]


def build_env(path_prefix: str, codex_home: Path) -> dict[str, str]:
    """Prepare the subprocess environment for Codex commands."""

    env = os.environ.copy()
    expanded_prefix = expand_path_prefix(path_prefix)
    if expanded_prefix:
        env["PATH"] = (
            f"{expanded_prefix}{os.pathsep}{env.get('PATH', '')}" if env.get("PATH") else expanded_prefix
        )
    env["CODEX_HOME"] = str(codex_home)
    return env


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    label: str,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and echo its output in a readable form."""

    print(f"[{label}] {' '.join(shlex.quote(part) for part in argv)}")
    completed = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(completed.stderr, end="" if completed.stderr.endswith("\n") else "\n", file=sys.stderr)
    if completed.returncode != 0:
        raise HarnessError(f"{label} failed with exit code {completed.returncode}")
    return completed


def print_plan(
    workspace: ValidationWorkspace,
    plugin_name: str,
    prompt: str,
    output_file: Path,
    path_prefix: str,
    zip_archive: Path | None,
) -> None:
    """Print the dry-run plan and commands."""

    print("Isolated Codex plugin validation plan")
    print(f"  temp workspace: {workspace.root}")
    print(f"  plugin source:  {workspace.copied_plugin_dir}")
    print(f"  marketplace:    {workspace.marketplace_path}")
    print(f"  codex home:     {workspace.codex_home}")
    print(f"  project dir:    {workspace.project_dir}")
    print(f"  output file:    {output_file}")
    if zip_archive is not None:
        print(f"  zip archive:    {zip_archive}")
    print()
    print("Commands to run:")
    for command in build_command_strings(workspace, plugin_name, prompt, output_file, path_prefix):
        print(f"  {command}")


def cleanup_workspace(workspace: ValidationWorkspace) -> None:
    """Remove the temp tree only when it is safe to do so."""

    if workspace.root.is_dir() and workspace.root.name.startswith("codex-plugin-"):
        shutil.rmtree(workspace.root)


def main() -> int:
    """Run the isolated Codex plugin validation harness."""

    parser = create_parser()
    args = parser.parse_args()
    workspace: ValidationWorkspace | None = None

    try:
        workspace = create_temp_workspace(args.plugin)
        zip_archive = maybe_zip_unzip_plugin(workspace, args.plugin) if args.zip_unzip else None
        output_file = args.output_file or default_output_file(args.plugin)

        if not args.run:
            print_plan(
                workspace,
                args.plugin,
                args.prompt,
                output_file,
                args.path_prefix,
                zip_archive,
            )
            print()
            print(
                "Dry run only: temp workspace preserved so the printed commands remain usable."
            )
            return 0

        env = build_env(args.path_prefix, workspace.codex_home)
        print(f"Workspace: {workspace.root}")
        if zip_archive is not None:
            print(f"Distribution archive: {zip_archive}")

        run_command(
            [
                "codex",
                "plugin",
                "marketplace",
                "add",
                str(workspace.marketplace_path),
            ],
            cwd=workspace.project_dir,
            env=env,
            label="marketplace",
        )
        run_command(
            [
                "codex",
                "plugin",
                "add",
                f"{args.plugin}@{MARKETPLACE_NAME}",
            ],
            cwd=workspace.project_dir,
            env=env,
            label="install",
        )
        run_command(
            [
                "codex",
                "exec",
                "--skip-git-repo-check",
                "-o",
                str(output_file),
                args.prompt,
            ],
            cwd=workspace.project_dir,
            env=env,
            label="exec",
        )
        print(f"Smoke output written to: {output_file}")
        return 0
    except (HarnessError, OSError, subprocess.SubprocessError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    finally:
        if workspace is not None and args.run and not args.keep_tempdir:
            cleanup_workspace(workspace)


if __name__ == "__main__":
    raise SystemExit(main())
