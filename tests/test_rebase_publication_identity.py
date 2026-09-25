"""Exercise the rebase publication example against isolated local Git remotes.

These tests execute the documented push command, not an agent or the complete
rebase workflow. A lease guards the destination; it does not pin a moving source.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / ".agents/skills/rebase/references/publication.md"
SOURCE = "refs/heads/result"
DESTINATION = "refs/heads/published"


class GitSandbox:
    """A local-only source repository and bare publication destination."""

    def __init__(self, root: Path) -> None:
        """Create repositories without inheriting user Git configuration."""
        self.work = root / "work"
        self.remote = root / "remote.git"
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_TERMINAL_PROMPT="0",
            GIT_AUTHOR_NAME="Publication test",
            GIT_AUTHOR_EMAIL="publication-test@example.invalid",
            GIT_COMMITTER_NAME="Publication test",
            GIT_COMMITTER_EMAIL="publication-test@example.invalid",
        )
        self.work.mkdir()
        self.run("init", "--initial-branch=main")
        self.run("init", "--bare", "--initial-branch=main", str(self.remote))
        self.original = self.commit("original")
        self.run("push", str(self.remote), f"{self.original}:{DESTINATION}")
        self.run("switch", "-c", "result")
        self.validated = self.commit("validated")

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run a bounded Git command and retain its complete result."""
        return subprocess.run(
            ["git", *args],
            cwd=self.work,
            env=self.env,
            capture_output=True,
            text=True,
            check=check,
            timeout=10,
        )

    def commit(self, value: str) -> str:
        """Record one file revision and return its immutable commit ID."""
        (self.work / "value.txt").write_text(value + "\n", encoding="utf-8")
        self.run("add", "value.txt")
        self.run("commit", "-m", value)
        return self.run("rev-parse", "HEAD").stdout.strip()

    def observed_destination(self) -> str:
        """Read the exact publication ref from the local bare remote."""
        return self.run("ls-remote", str(self.remote), DESTINATION).stdout.split()[0]

    def publish_documented_example(self) -> subprocess.CompletedProcess[str]:
        """Substitute fixture identities into the actual documented command."""
        examples = re.findall(r"```bash\n(.*?)\n```", PUBLICATION.read_text(encoding="utf-8"), re.DOTALL)
        pushes = [example for example in examples if example.startswith("git push ")]
        assert len(pushes) == 1, "The publication reference must identify one push example"
        command = pushes[0].replace("\\\n", " ")
        replacements = {
            "<destination-ref>": DESTINATION,
            "<observed-destination-oid>": self.original,
            "<remote>": str(self.remote),
            "<result-ref>": SOURCE,
            "<result-oid>": self.validated,
        }
        # Tokenize before substituting paths, so paths with spaces remain one argv.
        argv = shlex.split(command)
        for index, argument in enumerate(argv):
            for placeholder, value in replacements.items():
                argument = argument.replace(placeholder, value)
            assert "<" not in argument and ">" not in argument, argument
            argv[index] = argument
        assert argv[:2] == ["git", "push"]
        return self.run(*argv[1:], check=False)


@pytest.mark.parametrize("source_moves", [False, True], ids=["stable-source", "moved-source"])
def test_documented_push_sends_validated_commit(tmp_path: Path, source_moves: bool) -> None:
    """A local branch movement cannot change which validated object is sent."""
    sandbox = GitSandbox(tmp_path)
    if source_moves:
        unvalidated = sandbox.commit("unvalidated")
        assert unvalidated != sandbox.validated
    pushed = sandbox.publish_documented_example()
    assert pushed.returncode == 0, pushed.stderr
    assert sandbox.observed_destination() == sandbox.validated


def test_documented_push_preserves_moved_destination(tmp_path: Path) -> None:
    """The explicit lease still rejects an intervening remote writer."""
    sandbox = GitSandbox(tmp_path)
    sandbox.run("switch", "-c", "external")
    intervening = sandbox.commit("another writer")
    sandbox.run("push", str(sandbox.remote), f"{intervening}:{DESTINATION}")
    sandbox.run("switch", "result")
    pushed = sandbox.publish_documented_example()
    assert pushed.returncode != 0
    assert sandbox.observed_destination() == intervening
