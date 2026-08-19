#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Validate explicit, cache-provenanced Codex skill activation without MCP."""

from __future__ import annotations

import argparse
import hashlib
import json
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import validate_codex_plugin_isolated as isolated

REPO_ROOT = Path(__file__).resolve().parent.parent
MATRIX_PATH = REPO_ROOT / "tests" / "fixtures" / "codex-skill-activation-matrix.jsonl"
MCP_CONFIG_NAMES = frozenset({".mcp.json", ".mcp.codex.json"})
BLOCKED_ITEM_TYPES = frozenset({"commandExecution", "fileChange", "mcpToolCall"})
APP_SERVER_COMMAND = ("codex", "--disable", "apps", "app-server")


# Reuse the harness module's exception type rather than redefining it — two
# identically-named-but-distinct classes would make this module's `except
# HarnessError` blind to failures isolated.py itself raises (e.g. from
# create_temp_workspace / copy_auth_from_current_home, both called below).
HarnessError = isolated.HarnessError


@dataclass(frozen=True)
class InstalledSkill:
    """A verified skill in an isolated installed plugin cache."""

    path: Path
    relative_path: Path
    sha256: str
    tree_sha256: str


@dataclass(frozen=True)
class ActivationResult:
    """Redactable outcome of a completed app-server turn."""

    observed_methods: tuple[str, ...]
    response_text: str


def create_parser() -> argparse.ArgumentParser:
    """Build the activation-harness command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin", default="xdg-base-directory")
    parser.add_argument("--target", required=True, help="Matrix target: <plugin-id>:<skill>.")
    parser.add_argument("--expect-contains", action="append", default=[])
    parser.add_argument("--evidence-file", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    parser.add_argument("--path-prefix", default=isolated.DEFAULT_PATH_PREFIX)
    parser.add_argument("--copy-auth-from-current-home", action="store_true")
    return parser


def sha256_file(path: Path) -> str:
    """Return the content digest of one regular file without decoding it."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65_536):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(root: Path) -> str:
    """Hash the complete regular-file tree and reject every symbolic link."""
    if root.is_symlink() or not root.is_dir():
        raise HarnessError(f"Plugin tree is not a regular directory: {root.name}")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise HarnessError(f"Plugin tree contains a symbolic link: {path.relative_to(root)}")
        relative = path.relative_to(root).as_posix().encode("utf-8")
        if path.is_dir():
            digest.update(b"D\0" + relative + b"\0")
        elif path.is_file():
            digest.update(b"F\0" + relative + b"\0")
            with path.open("rb") as stream:
                while chunk := stream.read(65_536):
                    digest.update(chunk)
        else:
            raise HarnessError(f"Plugin tree contains an unsupported entry: {path.relative_to(root)}")
    return digest.hexdigest()


def resolve_installed_skill(plugin_cache_root: Path, skill_name: str) -> InstalledSkill:
    """Resolve one skill from exactly one installed plugin version."""
    versions = [path for path in plugin_cache_root.iterdir() if path.is_dir() and not path.is_symlink()]
    if len(versions) != 1:
        raise HarnessError(f"Expected one installed plugin version, found {len(versions)}")
    plugin_root = versions[0]
    skill_path = plugin_root / "skills" / skill_name / "SKILL.md"
    if skill_path.is_symlink():
        raise HarnessError("Installed skill is a symbolic link")
    resolved_root = plugin_root.resolve(strict=True)
    resolved_skill = skill_path.resolve(strict=True)
    if not resolved_skill.is_relative_to(resolved_root):
        raise HarnessError("Installed skill escapes the plugin cache")
    if not resolved_skill.is_file():
        raise HarnessError("Installed skill is not a regular file")
    return InstalledSkill(
        path=resolved_skill,
        relative_path=resolved_skill.relative_to(plugin_cache_root.resolve(strict=True)),
        sha256=sha256_file(resolved_skill),
        tree_sha256=tree_sha256(resolved_root),
    )


def load_matrix_target(target: str) -> dict[str, object]:
    """Load a mapped task oracle without reading the tested skill instructions."""
    if not MATRIX_PATH.is_file():
        raise HarnessError("Activation matrix is missing")
    for line in MATRIX_PATH.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if isinstance(row, dict) and row.get("target") == target:
            if row.get("status") != "MAPPED":
                raise HarnessError(f"Target is not mapped: {target}")
            if not isinstance(row.get("task_text"), str) or not row["task_text"]:
                raise HarnessError(f"Mapped target has no task: {target}")
            return row
    raise HarnessError(f"Target is missing from activation matrix: {target}")


def ensure_no_mcp_configuration(plugin_root: Path) -> None:
    """Keep MCP-bearing plugins in the separate FastMCP validation lane."""
    names = [path.name for path in plugin_root.rglob("*") if path.name in MCP_CONFIG_NAMES]
    if names:
        raise HarnessError("Plugin declares MCP configuration; use the FastMCP validation lane")


def build_turn_request(
    *, thread_id: str, skill_name: str, skill_path: Path, task_text: str, project_dir: Path
) -> dict[str, object]:
    """Create the documented explicit-skill app-server turn request."""
    return {
        "method": "turn/start",
        "id": 3,
        "params": {
            "threadId": thread_id,
            "input": [
                {"type": "text", "text": f"${skill_name} {task_text}"},
                {"type": "skill", "name": skill_name, "path": str(skill_path)},
            ],
            "cwd": str(project_dir),
            "approvalPolicy": "never",
            "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
        },
    }


def observe_event(message: dict[str, object], *, observed_methods: list[str], response_fragments: list[str]) -> None:
    """Record safe event metadata and reject behavior outside this test lane."""
    method = message.get("method")
    if not isinstance(method, str):
        return
    observed_methods.append(method)
    params = message.get("params")
    if not isinstance(params, dict):
        raise HarnessError(f"Malformed app-server event: {method}")
    if method.startswith("mcpServer/"):
        server_name = params.get("name")
        detail = f" for {server_name}" if isinstance(server_name, str) else ""
        raise HarnessError(f"MCP event observed in read-only activation lane: {method}{detail}")
    if method.endswith("/requestApproval"):
        raise HarnessError(f"Unexpected approval request: {method}")
    item = params.get("item")
    if isinstance(item, dict):
        item_type = item.get("type")
        if item_type in BLOCKED_ITEM_TYPES:
            raise HarnessError(f"Blocked item type observed: {item_type}")
    if method == "item/agentMessage/delta":
        delta = params.get("delta")
        if isinstance(delta, str):
            response_fragments.append(delta)
    if method == "error":
        raise HarnessError("App-server emitted an error event")


def pop_jsonl_message(buffer: bytes) -> tuple[dict[str, object] | None, bytes]:
    """Decode one complete JSONL message while retaining any following bytes."""
    line, separator, remaining = buffer.partition(b"\n")
    if not separator:
        return None, buffer
    message = json.loads(line)
    if not isinstance(message, dict):
        raise HarnessError("App-server emitted a non-object JSON message")
    return message, remaining


class AppServerClient:
    """Small JSONL client with request correlation and bounded reads."""

    def __init__(self, process: subprocess.Popen[bytes], deadline: float) -> None:
        self.process = process
        self.deadline = deadline
        self.buffer = b""
        if process.stdout is None:
            raise HarnessError("App-server stdout is unavailable")
        self._stdout_chunks: queue.Queue[bytes | None] = queue.Queue()
        threading.Thread(target=self._read_stdout, daemon=True).start()

    def _read_stdout(self) -> None:
        if self.process.stdout is None:
            return
        for line in iter(self.process.stdout.readline, b""):
            self._stdout_chunks.put(line)
        self._stdout_chunks.put(None)

    def send(self, message: dict[str, object]) -> None:
        if self.process.stdin is None:
            raise HarnessError("App-server stdin is unavailable")
        self.process.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
        self.process.stdin.flush()

    def receive(self) -> dict[str, object]:
        while True:
            message, self.buffer = pop_jsonl_message(self.buffer)
            if message is not None:
                return message
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise HarnessError("Timed out waiting for app-server")
            try:
                chunk = self._stdout_chunks.get(timeout=remaining)
            except queue.Empty:
                raise HarnessError("Timed out waiting for app-server") from None
            if chunk is None:
                raise HarnessError("App-server closed stdout before completing the turn")
            self.buffer += chunk

    def request(
        self, message: dict[str, object], *, observed_methods: list[str], response_fragments: list[str]
    ) -> dict[str, object]:
        self.send(message)
        request_id = message["id"]
        while True:
            response = self.receive()
            observe_event(response, observed_methods=observed_methods, response_fragments=response_fragments)
            if "id" not in response:
                continue
            if response["id"] != request_id:
                raise HarnessError("App-server returned an unexpected response id")
            if "error" in response:
                raise HarnessError("App-server rejected a protocol request")
            result = response.get("result")
            if not isinstance(result, dict):
                raise HarnessError("App-server response has no object result")
            return {str(key): value for key, value in result.items()}


def run_app_server(
    *, env: dict[str, str], project_dir: Path, skill_name: str, skill_path: Path, task_text: str, timeout_seconds: float
) -> ActivationResult:
    """Run one explicit skill turn and reject any unsafe event category."""
    process = subprocess.Popen(
        APP_SERVER_COMMAND,
        cwd=project_dir,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    observed_methods: list[str] = []
    response_fragments: list[str] = []
    client = AppServerClient(process, time.monotonic() + timeout_seconds)
    try:
        client.request(
            {
                "method": "initialize",
                "id": 1,
                "params": {"clientInfo": {"name": "codex-plugin-activation-validator", "version": "1"}},
            },
            observed_methods=observed_methods,
            response_fragments=response_fragments,
        )
        client.send({"method": "initialized", "params": {}})
        thread_result = client.request(
            {
                "method": "thread/start",
                "id": 2,
                "params": {"cwd": str(project_dir), "approvalPolicy": "never", "sandbox": "read-only"},
            },
            observed_methods=observed_methods,
            response_fragments=response_fragments,
        )
        thread = thread_result.get("thread")
        if not isinstance(thread, dict) or not isinstance(thread.get("id"), str):
            raise HarnessError("App-server did not return a thread id")
        thread_id = thread.get("id")
        if not isinstance(thread_id, str):
            raise HarnessError("App-server did not return a thread id")
        turn_request = build_turn_request(
            thread_id=thread_id,
            skill_name=skill_name,
            skill_path=skill_path,
            task_text=task_text,
            project_dir=project_dir,
        )
        turn_result = client.request(
            turn_request, observed_methods=observed_methods, response_fragments=response_fragments
        )
        turn = turn_result.get("turn")
        if not isinstance(turn, dict) or not isinstance(turn.get("id"), str):
            raise HarnessError("App-server did not return a turn id")
        turn_id = turn.get("id")
        if not isinstance(turn_id, str):
            raise HarnessError("App-server did not return a turn id")
        while True:
            event = client.receive()
            observe_event(event, observed_methods=observed_methods, response_fragments=response_fragments)
            if event.get("method") != "turn/completed":
                continue
            params = event.get("params")
            if not isinstance(params, dict) or not isinstance(params.get("turn"), dict):
                raise HarnessError("Malformed turn completion event")
            completed_turn = params.get("turn")
            if not isinstance(completed_turn, dict):
                raise HarnessError("Malformed turn completion event")
            if completed_turn.get("id") != turn_id or completed_turn.get("status") != "completed":
                raise HarnessError("Skill turn did not complete successfully")
            break
        response_text = "".join(response_fragments)
        if not response_text:
            raise HarnessError("Skill turn completed without an agent response")
        return ActivationResult(tuple(observed_methods), response_text)
    finally:
        if process.stdin is not None:
            process.stdin.close()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def run_silent(argv: list[str], *, cwd: Path, env: dict[str, str], label: str) -> None:
    """Run a setup command without exposing its output or ambient credentials."""
    completed = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise HarnessError(f"{label} failed with exit code {completed.returncode}")


def write_evidence(path: Path, evidence: dict[str, object]) -> None:
    """Write only redacted, commit-safe activation evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    """Install, provenance-check, and explicitly activate one mapped skill."""
    args = create_parser().parse_args()
    workspace: isolated.ValidationWorkspace | None = None
    try:
        target = load_matrix_target(args.target)
        workspace = isolated.create_temp_workspace(args.plugin)
        if not args.target.startswith(f"{workspace.plugin_id}:"):
            raise HarnessError("Target plugin id does not match the selected plugin directory")
        skill_name = args.target.removeprefix(f"{workspace.plugin_id}:")
        if not skill_name or "/" in skill_name:
            raise HarnessError("Target skill name is invalid")
        ensure_no_mcp_configuration(workspace.plugin_dir)
        source_digest = tree_sha256(workspace.plugin_dir)
        env = isolated.build_env(args.path_prefix, workspace.codex_home)
        run_silent(
            ["codex", "plugin", "marketplace", "add", str(workspace.marketplace_source)],
            cwd=workspace.project_dir,
            env=env,
            label="marketplace registration",
        )
        run_silent(
            ["codex", "plugin", "add", f"{workspace.plugin_id}@{workspace.marketplace_name}"],
            cwd=workspace.project_dir,
            env=env,
            label="plugin installation",
        )
        cache_root = workspace.codex_home / "plugins" / "cache" / workspace.marketplace_name / workspace.plugin_id
        installed = resolve_installed_skill(cache_root, skill_name)
        if installed.tree_sha256 != source_digest:
            raise HarnessError("Installed cache tree does not match the distributed plugin tree")
        if args.copy_auth_from_current_home:
            isolated.copy_auth_from_current_home(workspace)
        task_text = target.get("task_text")
        if not isinstance(task_text, str):
            raise HarnessError("Mapped target has no task text")
        result = run_app_server(
            env=env,
            project_dir=workspace.project_dir,
            skill_name=skill_name,
            skill_path=installed.path,
            task_text=task_text,
            timeout_seconds=args.timeout_seconds,
        )
        matched = [token for token in args.expect_contains if token.casefold() in result.response_text.casefold()]
        if len(matched) != len(args.expect_contains):
            raise HarnessError("Skill response did not meet the supplied behavioral assertion")
        write_evidence(
            args.evidence_file,
            {
                "cache_relative_skill": installed.relative_path.as_posix(),
                "expected_tokens_matched": len(matched),
                "expected_tokens_requested": len(args.expect_contains),
                "installed_tree_sha256": installed.tree_sha256,
                "observed_methods": list(result.observed_methods),
                "response_characters": len(result.response_text),
                "response_sha256": hashlib.sha256(result.response_text.encode()).hexdigest(),
                "skill_sha256": installed.sha256,
                "source_tree_sha256": source_digest,
                "status": "PASSED",
                "target": args.target,
            },
        )
        print(f"Activation evidence written to: {args.evidence_file}")
        return 0
    except (HarnessError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    finally:
        if workspace is not None:
            isolated.cleanup_workspace(workspace)


if __name__ == "__main__":
    raise SystemExit(main())
