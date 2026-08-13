"""Contract tests for cache-provenanced Codex skill activation."""

from __future__ import annotations

import hashlib
import io
import subprocess
import sys
import time
from pathlib import Path
from typing import cast

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import validate_codex_skill_activation as activation


def test_app_server_disables_host_owned_apps_mcp() -> None:
    """The activation lane suppresses Codex's host-owned Apps MCP server."""
    assert activation.APP_SERVER_COMMAND == ("codex", "--disable", "apps", "app-server")


def test_activation_timeout_defaults_to_a_bounded_model_turn() -> None:
    """The no-MCP sentinel does not retain an unnecessarily long default timeout."""
    args = activation.create_parser().parse_args([
        "--target",
        "xdg-base-directory:xdg-base-directory",
        "--evidence-file",
        "evidence.json",
    ])

    assert args.timeout_seconds == 45.0


def test_jsonl_decoder_keeps_the_next_buffered_protocol_message() -> None:
    """A buffered JSONL read retains an immediately following app-server message."""
    message, remaining = activation.pop_jsonl_message(b'{"id": 1}\n{"id": 2}\n')

    assert message == {"id": 1}
    assert remaining == b'{"id": 2}\n'


def test_app_server_client_reads_pipe_without_select() -> None:
    class FakeProcess:
        stdin = None
        stdout = io.BytesIO(b'{"id": 1}\n')

    client = activation.AppServerClient(cast("subprocess.Popen[bytes]", FakeProcess()), time.monotonic() + 1)

    assert client.receive() == {"id": 1}


def test_installed_skill_resolution_returns_contained_regular_skill_file(tmp_path: Path) -> None:
    """A cache skill must remain a regular file inside the cache root."""
    cache_root = tmp_path / "cache" / "marketplace" / "plugin"
    skill_file = cache_root / "1.0.0" / "skills" / "example" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text("skill instructions\n", encoding="utf-8")

    resolved = activation.resolve_installed_skill(cache_root, "example")

    assert resolved.path == skill_file.resolve()
    assert resolved.relative_path == Path("1.0.0/skills/example/SKILL.md")
    assert resolved.sha256 == hashlib.sha256(b"skill instructions\n").hexdigest()


def test_installed_skill_resolution_rejects_symlink_escape(tmp_path: Path) -> None:
    """A cache entry cannot redirect activation outside the installed plugin cache."""
    cache_root = tmp_path / "cache" / "marketplace" / "plugin"
    outside = tmp_path / "outside.md"
    outside.write_text("not an installed skill\n", encoding="utf-8")
    skill_file = cache_root / "1.0.0" / "skills" / "example" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.symlink_to(outside)

    with pytest.raises(activation.HarnessError, match="symbolic link"):
        activation.resolve_installed_skill(cache_root, "example")


def test_turn_request_injects_the_named_cache_skill(tmp_path: Path) -> None:
    """The app-server turn payload carries both the explicit marker and skill item."""
    skill_file = tmp_path / "cache" / "SKILL.md"
    full_skill_name = "xdg-base-directory:xdg-base-directory"

    request = activation.build_turn_request(
        thread_id="thread-1",
        skill_name=full_skill_name,
        skill_path=skill_file,
        task_text="Where should this app store its database file?",
        project_dir=tmp_path / "project",
    )

    params = request.get("params")
    assert isinstance(params, dict)
    input_items = params.get("input")
    assert isinstance(input_items, list)
    assert input_items[0] == {
        "type": "text",
        "text": ("$xdg-base-directory:xdg-base-directory Where should this app store its database file?"),
    }
    assert input_items[1] == {"type": "skill", "name": full_skill_name, "path": str(skill_file)}
    assert params.get("approvalPolicy") == "never"
    assert params.get("sandboxPolicy") == {"type": "readOnly", "networkAccess": False}


def test_mcp_events_are_rejected_by_the_read_only_activation_lane() -> None:
    """The skill activation lane must not run or wait on plugin MCP activity."""
    with pytest.raises(activation.HarnessError, match="MCP event"):
        activation.observe_event(
            {"method": "mcpServer/elicitation/request", "params": {}}, observed_methods=[], response_fragments=[]
        )
