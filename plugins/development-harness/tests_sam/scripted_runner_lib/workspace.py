"""What one run resolves before it issues a command: the toolchain, the state root, the fixtures.

Nothing here reaches the ledger. It resolves the two programs the run needs, reads the commit the
plan records as its base, lays out a state root the run owns, and reads the loop-plan fixture files
the loop feeds to ``sam plan``.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel

from tests_sam.scripted_runner_lib.errors import (
    CommandTimeoutError,
    FixtureMissingError,
    ScriptedRunnerError,
    ToolchainMissingError,
)

LIBRARY_DIRECTORY: Path = Path(__file__).resolve().parent
"""Where the runner's own modules live; the source-reading tests scan every ``.py`` file in it."""

TESTS_DIRECTORY: Path = LIBRARY_DIRECTORY.parent
"""The ``tests_sam`` directory holding the entry script, this package and the fixtures."""

FIXTURE_DIRECTORY: Path = TESTS_DIRECTORY / "fixtures" / "loop-plan"
"""The loop-plan fixture: the plan's fields, the report sections and the send-back response."""

DEFAULT_PLUGIN_ROOT: Path = TESTS_DIRECTORY.parent
"""The development-harness checkout this script belongs to, which holds ``sam_schema/cli.py``."""

RUN_TIMEOUT_SECONDS: int = 300
"""How long one ``sam plan`` command may take before the run is abandoned."""


class Workspace(BaseModel):
    """The temporary state root a run owns, so a hand run touches no real ledger."""

    root: Path
    state_home: Path
    worktrees: Path
    environment: dict[str, str]

    def worktree_for(self, task: str) -> Path:
        """Return the worktree ``dispatch`` records for one task.

        Args:
            task: The task identifier, such as ``T1``.

        Returns:
            The directory that task's attempts run in.
        """
        return self.worktrees / task


class Toolchain(BaseModel):
    """The programs and paths one run needs before it can reach the ledger."""

    uv: Path
    git: Path
    plugin_root: Path
    cli_path: Path
    base_sha: str


class Preparation(BaseModel):
    """Everything :func:`prepare_workspace` resolved before the loop starts."""

    workspace: Workspace
    toolchain: Toolchain


class Fixtures:
    """Reads the loop-plan fixture files, refusing to hand back an absent one as empty text."""

    def __init__(self, directory: Path) -> None:
        """Bind the reader to one fixture directory.

        Args:
            directory: The loop-plan fixture root.
        """
        self.directory = directory

    def path(self, *parts: str) -> Path:
        """Return where one fixture file sits.

        Args:
            *parts: The path segments below the fixture root.

        Returns:
            The fixture file's path.
        """
        return self.directory.joinpath(*parts)

    def has(self, *parts: str) -> bool:
        """Return whether one fixture file exists.

        Args:
            *parts: The path segments below the fixture root.

        Returns:
            True when the file is there.
        """
        return self.path(*parts).is_file()

    def read(self, *parts: str) -> str:
        """Return one fixture file's text, without the trailing newline the file convention adds.

        Args:
            *parts: The path segments below the fixture root.

        Returns:
            The file's text as a ledger field, report section or send-back response.

        Raises:
            FixtureMissingError: When the file is absent.
        """
        target = self.path(*parts)
        if not target.is_file():
            raise FixtureMissingError(f"the loop-plan fixture has no {'/'.join(parts)}")
        return target.read_text(encoding="utf-8").rstrip("\n")


def resolve_program(name: str, purpose: str) -> Path:
    """Return where one program the run needs sits.

    Args:
        name: The program's name, resolved on PATH.
        purpose: Why the run needs it, for the failure message.

    Returns:
        The program's path.

    Raises:
        ToolchainMissingError: When PATH holds no such program.
    """
    found = shutil.which(name)
    if found is None:
        raise ToolchainMissingError(f"{name} is not on PATH; {purpose}")
    return Path(found)


def nearest_repository(start: Path) -> Path:
    """Return the nearest ancestor of one directory holding a ``.git`` entry.

    Args:
        start: Where to start looking.

    Returns:
        The repository root.

    Raises:
        ScriptedRunnerError: When no ancestor holds one, so ``DH_PROJECT_ROOT`` cannot resolve.
    """
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    raise ScriptedRunnerError(f"no ancestor of {start} holds a .git entry; set DH_PROJECT_ROOT")


def base_commit(git: Path, plugin_root: Path, timeout_seconds: int) -> str:
    """Return the commit ``create --base-sha`` records for the judge to diff a report against.

    Args:
        git: The resolved ``git`` program.
        plugin_root: The checkout to read HEAD from.
        timeout_seconds: How long the read may take.

    Returns:
        The commit sha.

    Raises:
        ScriptedRunnerError: When the checkout has no commit to name.
        CommandTimeoutError: When the read does not finish inside the run's per-command limit.
    """
    try:
        completed = subprocess.run(
            [str(git), "-C", str(plugin_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        raise CommandTimeoutError(
            f"reading HEAD of {plugin_root} did not finish within {timeout_seconds} seconds"
        ) from expired
    sha = completed.stdout.strip()
    if completed.returncode != 0 or not sha:
        raise ScriptedRunnerError(
            f"no commit at {plugin_root} to diff reports against; point --plugin-root at a checkout\n"
            f"stderr: {completed.stderr}"
        )
    return sha


def prepare_workspace(
    work_dir: Path,
    *,
    plugin_root: Path | None = None,
    project_root: Path | None = None,
    timeout_seconds: int = RUN_TIMEOUT_SECONDS,
) -> Preparation:
    """Resolve the toolchain and lay out the state root one run owns.

    Args:
        work_dir: The directory the run writes everything into.
        plugin_root: The development-harness checkout holding ``sam_schema/cli.py``.
        project_root: What ``DH_PROJECT_ROOT`` names; the nearest ancestor holding ``.git`` by default.
        timeout_seconds: How long the base-commit read may take.

    Returns:
        The workspace and the toolchain the loop runs against.

    Raises:
        ScriptedRunnerError: When the checkout holds no CLI at the documented path.
    """
    uv = resolve_program("uv", "it is how sam_schema/cli.py resolves its dependencies")
    git = resolve_program("git", "the plan needs a base commit for --base-sha")
    root = plugin_root if plugin_root is not None else DEFAULT_PLUGIN_ROOT
    cli_path = root / "sam_schema" / "cli.py"
    if not cli_path.is_file():
        raise ScriptedRunnerError(f"no CLI at {cli_path}; point --plugin-root at the development-harness plugin")
    toolchain = Toolchain(
        uv=uv, git=git, plugin_root=root, cli_path=cli_path, base_sha=base_commit(git, root, timeout_seconds)
    )
    state_home = work_dir / "state"
    worktrees = work_dir / "worktrees"
    state_home.mkdir(parents=True, exist_ok=True)
    worktrees.mkdir(parents=True, exist_ok=True)
    repository = project_root if project_root is not None else nearest_repository(TESTS_DIRECTORY)
    workspace = Workspace(
        root=work_dir,
        state_home=state_home,
        worktrees=worktrees,
        # `export` writes through the configured backlog backend. SQLite keeps its database under
        # DH_STATE_HOME, so the run reaches no network and no shared store; the default is GitHub,
        # which needs credentials this script has no business holding.
        environment={"DH_STATE_HOME": str(state_home), "BACKLOG_BACKEND": "sqlite", "DH_PROJECT_ROOT": str(repository)},
    )
    return Preparation(workspace=workspace, toolchain=toolchain)
