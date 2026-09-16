"""Tests for task_status_hook.py — the SubagentStop settle.

Covers:
- extract_launch_from_prompt: the address AND the attempt come from the sub-agent's own prompt
- _call_sam_plan_settle: routes the settle through the SAM CLI subprocess
- handle_subagent_stop: settles the attempt and writes no status
- main(): only SubagentStop reaches the SAM CLI — every other event and tool name issues no
  subprocess (was red at HEAD 58f37d7be, before the step 1a deletion of the PostToolUse handler;
  see plan-posttooluse-activetask.md, step 1a)
- registration: task_status_hook.py is registered only under SubagentStop, across every place
  Claude Code reads a hook registration from
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import re
import sys
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Ensure hook script is importable from repo root.
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

# sam_schema must be on sys.path
_repo_root = _plugin_dir.parent.parent
_sam_packages = str(_repo_root / "packages")
if _sam_packages not in sys.path:
    sys.path.insert(0, _sam_packages)

_hook_path = _plugin_dir / "skills" / "implementation-manager" / "scripts" / "task_status_hook.py"
_spec = importlib.util.spec_from_file_location("task_status_hook", _hook_path)
assert _spec is not None
assert _spec.loader is not None
_hook_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_hook_mod)  # type: ignore[union-attr]

# sam_schema is importable once _plugin_dir is on sys.path (above) — ruamel.yaml per this
# repo's YAML convention (rules/yaml-toml-libraries.md), reusing the reader modules' own
# shared parsing instance rather than a second YAML engine.
from sam_schema.readers._yaml_utils import coerce_to_plain, load_yaml

# Re-export symbols for clarity
Launch = _hook_mod.Launch
_NO_FINAL_MESSAGE = _hook_mod._NO_FINAL_MESSAGE
_call_sam_plan_settle = _hook_mod._call_sam_plan_settle
extract_launch_from_prompt = _hook_mod.extract_launch_from_prompt
handle_subagent_stop = _hook_mod.handle_subagent_stop
_SAM_CLI_PATH = _hook_mod._SAM_CLI_PATH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cli_success_response(data: dict[str, Any]) -> CompletedProcess[str]:
    """Build a successful SAM CLI subprocess response — plain JSON stdout, no envelope."""
    return CompletedProcess(args=[], returncode=0, stdout=json.dumps(data), stderr="")


def _mcp_error_response(returncode: int = 1) -> CompletedProcess[str]:
    """Build a failed SAM CLI subprocess response."""
    return CompletedProcess(args=[], returncode=returncode, stdout="", stderr="error")


def _popen_from_completed(cp: CompletedProcess[str], pid: int = 4242) -> MagicMock:
    """Build a fake Popen instance whose communicate()/.returncode mirror a CompletedProcess.

    The implementation moves off subprocess.run onto subprocess.Popen + communicate() so it
    can redirect a timeout's kill to the whole process group. This adapts tests that already
    express expected results as CompletedProcess to that new contract.
    """
    proc = MagicMock()
    proc.communicate.return_value = (cp.stdout, cp.stderr)
    proc.returncode = cp.returncode
    proc.poll.return_value = cp.returncode
    proc.pid = pid
    proc.__enter__.return_value = proc
    proc.__exit__.return_value = False
    return proc


def _popen_timeout(timeout: float = 8, pid: int = 4242) -> MagicMock:
    """Build a fake Popen instance whose communicate() times out once, then reaps cleanly.

    A list side_effect (rather than a bare exception) tolerates an implementation that calls
    communicate() a second time after killing the process group to reap pipes/avoid warnings.
    """
    proc = MagicMock()
    proc.communicate.side_effect = [TimeoutExpired(cmd="uv", timeout=timeout), ("", "")]
    proc.pid = pid
    proc.__enter__.return_value = proc
    proc.__exit__.return_value = False
    return proc


def _argv_after(cmd: list[str], token: str) -> list[str]:
    """Return the tail of *cmd* starting at the first occurrence of *token*.

    Isolates the subcommand-and-options shape from the uv/script invocation
    prefix, which callers should not need to hardcode.
    """
    return cmd[cmd.index(token) :]


# ---------------------------------------------------------------------------
# Regression guard — no fastmcp invocation left in the hook source
# ---------------------------------------------------------------------------


def test_hook_source_contains_no_fastmcp_invocation() -> None:
    """task_status_hook.py's own source never mentions 'fastmcp'.

    All task-state writes/reads now route through direct SAM CLI subprocess
    calls (see _SAM_CLI_PATH). A reintroduced fastmcp invocation would bring
    back the orphaned-process defect (keep_alive=True) and risk the 60-second
    SubagentStop hook deadline this migration fixed.
    """
    source = _hook_path.read_text(encoding="utf-8")
    assert "fastmcp" not in source.lower()


# ---------------------------------------------------------------------------
# Timeout ordering and process-group cleanup
#
# Two compounding defects this section guards against:
#   1. _call_sam_cli's timeout default is not safely below the outer 60s
#      SubagentStop hook deadline Claude Code itself enforces — the external
#      SIGKILL can beat subprocess's own internal timeout handling.
#   2. subprocess.run(timeout=...) only kills the immediate child (uv); a
#      descendant process uv forks (the real sam_schema/cli.py interpreter)
#      can be left running — the orphaned-process failure mode this whole
#      area of the codebase exists to prevent.
# ---------------------------------------------------------------------------


def test_timeout_defaults_are_below_outer_hook_deadline() -> None:
    """Every _call_sam_cli-family function's own timeout default must be < 60s.

    The outer SubagentStop hook deadline is a hard 60s SIGKILL of the whole
    hook process, enforced externally by Claude Code. An internal subprocess
    timeout default at or above that value can never fire before the outer
    kill does, so subprocess's own timeout/cleanup path never gets a chance
    to run — this is the exact defect already fixed once for the old
    fastmcp-call path, recurring here for the plain-CLI replacement.
    """
    funcs = [_hook_mod._call_sam_cli, _hook_mod._call_sam_plan_settle]
    for func in funcs:
        default = inspect.signature(func).parameters["timeout"].default
        assert default < 60, f"{func.__name__} timeout default is {default!r}, must be < 60"


def test_call_sam_cli_delegates_timeout_cleanup_to_terminate_process_tree(mocker: MockerFixture) -> None:
    """On timeout, _call_sam_cli delegates process-tree cleanup to run_bounded.terminate_process_tree.

    Supersedes the hand-rolled os.killpg(os.getpgid(pid), SIGKILL) approach, which only
    works on POSIX (os.killpg does not exist on Windows) and always jumps straight to
    SIGKILL with no graceful-termination attempt. The repo already solves this — see
    scripts/run_bounded.py's terminate_process_tree, already used the same way by
    scripts/validate_codex_plugin_isolated.py.

    os.getpgid/os.killpg are stubbed here too because terminate_process_tree itself calls
    them for real — without the stub this test would SIGKILL a real process group on the
    test machine.
    """
    proc = _popen_timeout(pid=4242)

    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch("subprocess.Popen", return_value=proc)
    mocker.patch("os.getpgid", return_value=4242)
    mocker.patch("os.killpg")
    mock_terminate = mocker.patch.object(_hook_mod, "terminate_process_tree", create=True)

    result = _hook_mod._call_sam_cli(["plan", "read", "--address", "P1/T1"])

    assert result is None
    mock_terminate.assert_called_once_with(proc)


def test_call_sam_cli_uses_posix_session_flag(mocker: MockerFixture) -> None:
    """_call_sam_cli launches its subprocess with start_new_session matching the platform.

    POSIX process groups are the prerequisite for terminate_process_tree's group-wide
    SIGTERM/SIGKILL escalation; Windows has no such concept and terminate_process_tree
    instead walks the OS process tree by PID via taskkill (see
    run_bounded.terminate_windows_process_tree). The assertion is written against
    os.name == "posix" rather than a hardcoded True so it stays correct off of POSIX too.
    """
    proc = _popen_from_completed(CompletedProcess(args=[], returncode=0, stdout="{}", stderr=""), pid=1234)

    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mock_popen = mocker.patch("subprocess.Popen", return_value=proc)

    _hook_mod._call_sam_cli(["plan", "read", "--address", "P1/T1"])

    mock_popen.assert_called_once()
    assert mock_popen.call_args.kwargs.get("start_new_session") == (os.name == "posix")


def test_terminate_process_tree_resolves_from_inside_the_plugin_package() -> None:
    """terminate_process_tree must resolve from inside the plugin package, not repo-root scripts/.

    A marketplace install ships only plugins/development-harness — a sibling
    repo-root scripts/ import would silently break there. Assert the imported
    function's own source file lives inside the plugin directory.
    """
    source_file = Path(_hook_mod.terminate_process_tree.__code__.co_filename).resolve()
    assert _plugin_dir.resolve() in source_file.parents


# ---------------------------------------------------------------------------
# SubagentStop coverage — the hook must fire for any agent that claimed a task
# ---------------------------------------------------------------------------


def test_subagent_stop_hook_is_not_restricted_to_task_worker() -> None:
    """SubagentStop must not filter by agent name.

    execution/SKILL.md dispatches a named specialist whenever one matches the task and
    only falls back to dh:task-worker otherwise. A name-based matcher therefore decides
    task-state tracking by which specialist got picked, and a specialist's task is never
    marked at all. The hook settles only the launch the stopping agent's own prompt names and
    writes nothing else, so running it for every sub-agent adds no status writes.

    A matcher cannot express "dh dispatched this" either way: a SubagentStop matcher takes
    the *agent type name* and nothing else (claude-subagent-reference's cached
    references/hooks-for-subagents.md, "Project-level hooks for subagent lifecycle", accessed
    2026-05-28), and dispatch-contract lets a task name any specialist, so the set of agent
    types dh launches is open. Narrowing the launch this hook acts on is therefore the
    prompt-shape job that extract_launch_from_prompt does, not a matcher's.
    """
    hooks_config = json.loads((_plugin_dir / "hooks" / "hooks.json").read_text(encoding="utf-8"))

    subagent_stop = hooks_config["hooks"]["SubagentStop"]
    assert subagent_stop, "SubagentStop must have at least one hook entry"

    for entry in subagent_stop:
        matcher = entry.get("matcher")
        assert matcher is None, (
            f"SubagentStop must not filter by agent name (found matcher={matcher!r}). "
            "Coverage must depend on whether a SAM task was claimed, not on the agent's name."
        )
        commands = [h.get("command", "") for h in entry.get("hooks", [])]
        assert any("task_status_hook.py" in c for c in commands), "SubagentStop must invoke task_status_hook.py"


# ---------------------------------------------------------------------------
# extract_launch_from_prompt — the address AND the attempt come from the prompt
#
# The attempt number is reachable nowhere else per sub-agent. The active-task record
# is keyed by the parent session's id and carries no attempt field, so a hook that
# read it could neither tell two parallel workers apart nor name the attempt a settle
# records against.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "prompt"),
    [
        ("implement-feature dispatch", "Pdec8934d/T01, attempt 3"),
        ("dispatch skill prose", "Your ROLE_TYPE is sub-agent. You are working on Pdec8934d/T01, attempt 3."),
        ("no comma", "Pdec8934d/T01 attempt 3"),
        ("slash command", "/start-task Pdec8934d --task T01 --attempt 3"),
        ("Skill() wrapper", 'Skill(skill="start-task", args="Pdec8934d --task T01 --attempt 3")'),
        ("namespaced slash command", "/dh:start-task Pdec8934d --task T01 --attempt 3"),
        ("namespaced Skill() wrapper", 'Skill(skill="dh:start-task", args="Pdec8934d --task T01 --attempt 3")'),
    ],
)
def test_every_shipped_launch_shape_yields_address_and_attempt(label: str, prompt: str) -> None:
    """Each prompt shape the orchestrator skills write must yield plan, task AND attempt.

    implement-feature/SKILL.md launches with "{plan_ref}/{task_id}, attempt {attempt}" and
    dispatch/SKILL.md wraps the same address in a sentence. A matcher that only full-matched a
    bare "{plan}/{task}" saw neither, so no settle was possible for either.
    """
    launch = extract_launch_from_prompt(prompt)

    assert launch is not None, label
    assert launch.plan == "Pdec8934d"
    assert launch.task_id == "T01"
    assert launch.attempt == 3
    assert launch.address == "Pdec8934d/T01"
    assert launch.is_ledger_address


def test_bare_address_yields_no_attempt() -> None:
    """A bare address names the task but no attempt, so it cannot be settled."""
    launch = extract_launch_from_prompt("Pdec8934d/T01")

    assert launch is not None
    assert launch.attempt is None


def test_an_address_mentioned_in_passing_is_not_a_launch() -> None:
    """An address inside unrelated prose, with no attempt clause, does not name a launch."""
    assert extract_launch_from_prompt("The blocker was tracked under Pdec8934d/T01 last week.") is None


@pytest.mark.parametrize(
    ("label", "prompt"),
    [
        ("prose continues past the attempt", "Investigate why Pdec8934d/T01, attempt 3 failed to settle."),
        ("attempt quoted mid-sentence", "Compare Pdec8934d/T01, attempt 3 against attempt 2 and report."),
        (
            "launch shape quoted below the first line",
            "Review the settle path.\n\nAn orchestrator launches with: Pdec8934d/T01, attempt 3",
        ),
        (
            "slash command quoted in a task description",
            "Document what /start-task Pdec8934d --task T01 --attempt 3 does for a reader.",
        ),
        (
            "namespaced slash command quoted in a task description",
            "Document what /dh:start-task Pdec8934d --task T01 --attempt 3 does for a reader.",
        ),
        (
            "namespaced slash command on a line after other text",
            "Investigate the failing test.\n\n/dh:start-task Pdec8934d --task T01 --attempt 3",
        ),
        ("a different plugin's namespaced slash command", "/other:start-task Pdec8934d --task T01 --attempt 3"),
    ],
)
def test_an_attempt_clause_in_free_text_is_not_a_launch(label: str, prompt: str) -> None:
    """A sub-agent of any plugin may discuss a dispatch; discussing one must not settle it.

    This hook fires for every sub-agent of every installed plugin, and settling an attempt
    that is still live tells the work loop a worker is gone while it is still working. The
    containment is positional: the launch reference must be the whole of the prompt's first
    line, which is where the dispatch contract writes it and nothing follows it. Free text
    mentioning an attempt runs on past it or sits below the opening line, and a command shape
    naming a plugin other than ``dh`` never matched the ``(?:dh:)?`` prefix in the first place.

    It is containment, not a closure — see the hook module docstring for the residual case
    and for the search that found no dispatcher-owned channel to replace this with.
    """
    assert extract_launch_from_prompt(prompt) is None, label


def test_the_launch_line_may_lead_a_longer_prompt() -> None:
    """A real dispatch whose prompt carries further lines still settles.

    The dispatch contract makes the reference the opening line, not the only line — relaying
    discoveries into a wave's prompts is part of dispatch/SKILL.md — so anchoring to the first
    line must not require a one-line prompt.
    """
    launch = extract_launch_from_prompt(
        "Pdec8934d/T01, attempt 3\n\nOBSERVATIONS: the T40 worker reported the API returns 404 on an empty body."
    )

    assert launch is not None
    assert launch.address == "Pdec8934d/T01"
    assert launch.attempt == 3


def test_a_file_path_plan_is_recognised_but_not_a_ledger_address() -> None:
    """A legacy file-path plan arg parses, and is reported as not settle-able."""
    launch = extract_launch_from_prompt('Skill(skill="start-task", args="plans/tasks-1-foo.yaml --task T2")')

    assert launch is not None
    assert launch.plan == "plans/tasks-1-foo.yaml"
    assert not launch.is_ledger_address


def test_extract_launch_from_prompt_empty_returns_none() -> None:
    """An empty prompt names no launch."""
    assert extract_launch_from_prompt("") is None


# ---------------------------------------------------------------------------
# _call_sam_plan_settle — the orchestrator's command, and the only write this hook makes
# ---------------------------------------------------------------------------


def test_settle_passes_address_attempt_and_return_text() -> None:
    """_call_sam_plan_settle builds `plan settle --address P/T --attempt N --return-text …`."""
    launch = Launch(plan="Pf4281187", task_id="T1", attempt=2)
    response = _cli_success_response({"command": "settle", "plan": "Pf4281187", "task": "T1", "attempt": 2})

    with (
        patch.object(_hook_mod, "_get_uv_executable", return_value="/usr/bin/uv"),
        patch("subprocess.Popen", return_value=_popen_from_completed(response)) as mock_popen,
    ):
        assert _call_sam_plan_settle(launch, "STATUS: DONE") is True

    argv = _argv_after(mock_popen.call_args[0][0], "plan")
    assert argv == ["plan", "settle", "--address", "Pf4281187/T1", "--attempt", "2", "--return-text", "STATUS: DONE"]


def test_settle_treats_already_settled_as_success() -> None:
    """`already-settled` is a no-op code on stdout with exit 0, not a failure.

    It is what the orchestrator's own settle leaves behind when it got there first, so the hook
    and the orchestrator never fight over one attempt.
    """
    response = CompletedProcess(args=[], returncode=0, stdout="already-settled\n", stderr="")

    with (
        patch.object(_hook_mod, "_get_uv_executable", return_value="/usr/bin/uv"),
        patch("subprocess.Popen", return_value=_popen_from_completed(response)),
    ):
        assert _call_sam_plan_settle(Launch(plan="Pf4281187", task_id="T1", attempt=2), "text") is True


def test_settle_failure_is_reported_not_absorbed(capsys: pytest.CaptureFixture[str]) -> None:
    """A settle that cannot land says so on stderr, naming the consequence.

    Silence here is the failure mode this hook exists to prevent: an unsettled attempt reads as
    a worker still at work and the loop waits on an agent that is gone.
    """
    with (
        patch.object(_hook_mod, "_get_uv_executable", return_value="/usr/bin/uv"),
        patch("subprocess.Popen", return_value=_popen_from_completed(_mcp_error_response())),
    ):
        assert _call_sam_plan_settle(Launch(plan="Pf4281187", task_id="T1", attempt=2), "text") is False

    assert "settle failed for Pf4281187/T1 attempt 2" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# handle_subagent_stop — settles, and writes no status
# ---------------------------------------------------------------------------


def _launch_transcript(tmp_path: Path, prompt: str, session_id: str = "sess-1") -> Path:
    """Write a transcript in the JSONL shape the hook parses, carrying *prompt* as the first turn."""
    records: list[dict[str, Any]] = [
        {"type": "user", "sessionId": session_id, "message": {"content": [{"type": "text", "text": prompt}]}},
        {
            "type": "assistant",
            "sessionId": session_id,
            "message": {"content": [{"type": "text", "text": "STATUS: DONE"}]},
        },
    ]
    transcript = tmp_path / f"{session_id}.jsonl"
    transcript.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return transcript


def test_subagent_stop_settles_the_attempt_the_prompt_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The stop settles P/T at the attempt its own prompt named, with the final message as evidence."""
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    transcript = _launch_transcript(tmp_path, "Pf4281187/T1, attempt 2")
    hook_input = {
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
        "last_assistant_message": "STATUS: DONE\nall criteria met",
    }

    with patch.object(_hook_mod, "_call_sam_plan_settle", return_value=True) as mock_settle:
        handle_subagent_stop(hook_input)

    settled_launch, return_text = mock_settle.call_args[0]
    assert settled_launch.address == "Pf4281187/T1"
    assert settled_launch.attempt == 2
    assert return_text == "STATUS: DONE\nall criteria met"


def test_subagent_stop_writes_no_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No `plan state` and no `plan update` reaches the CLI on a stop — settle is the only write.

    Status has two writers already: the runner's `finish` records the outcome and the judge's
    `accept`/`reclaim` records the verdict. A third writer here would be a second encoding of the
    same fact, and the runner contract guarantees it would disagree — a worker returns
    "STATUS: DONE" once `finish` was recorded, whatever its `--result`.
    """
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    transcript = _launch_transcript(tmp_path, "Pf4281187/T1, attempt 2")
    hook_input = {
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
        "last_assistant_message": "STATUS: DONE\nfinish was recorded with --result failed",
    }

    with (
        patch.object(_hook_mod, "_get_uv_executable", return_value="/usr/bin/uv"),
        patch(
            "subprocess.Popen", return_value=_popen_from_completed(_cli_success_response({"command": "settle"}))
        ) as mock_popen,
    ):
        handle_subagent_stop(hook_input)

    subcommands = [_argv_after(call[0][0], "plan")[:2] for call in mock_popen.call_args_list]
    assert subcommands == [["plan", "settle"]], subcommands


def test_subagent_stop_settles_a_launch_that_returned_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A launch that produced no final message is still settled, with a marker as return text.

    The work loop settles "including when the response is empty or the agent crashed" — that a
    launch ended is exactly the fact a crashed runner cannot report for itself.
    """
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    transcript = tmp_path / "sess-crash.jsonl"
    transcript.write_text(
        json.dumps({
            "type": "user",
            "sessionId": "sess-crash",
            "message": {"content": [{"type": "text", "text": "Pf4281187/T1, attempt 1"}]},
        })
        + "\n",
        encoding="utf-8",
    )
    hook_input = {"hook_event_name": "SubagentStop", "agent_transcript_path": str(transcript)}

    with patch.object(_hook_mod, "_call_sam_plan_settle", return_value=True) as mock_settle:
        handle_subagent_stop(hook_input)

    assert mock_settle.call_args[0][1] == _NO_FINAL_MESSAGE


def test_subagent_stop_says_why_it_could_not_settle_without_an_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A launch whose prompt named no attempt is reported on stderr, never absorbed."""
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    transcript = _launch_transcript(tmp_path, "Pf4281187/T1")
    hook_input = {"hook_event_name": "SubagentStop", "agent_transcript_path": str(transcript)}

    with patch.object(_hook_mod, "_call_sam_plan_settle") as mock_settle:
        handle_subagent_stop(hook_input)

    mock_settle.assert_not_called()
    assert "without an attempt number in its prompt" in capsys.readouterr().err


def test_subagent_stop_stays_quiet_for_an_unrelated_sub_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The hook settles only a launch named in the prompt. An unrelated sub-agent's stop runs no subprocess."""
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    transcript = _launch_transcript(tmp_path, "Please review the README for typos.", session_id="sess-1")
    hook_input = {
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
        "last_assistant_message": "STATUS: VERIFIED",
    }

    with patch("subprocess.Popen") as mock_popen:
        handle_subagent_stop(hook_input)

    mock_popen.assert_not_called()


def test_subagent_stop_without_a_transcript_path_reports_it(capsys: pytest.CaptureFixture[str]) -> None:
    """With no agent_transcript_path there is no correlation at all, and the hook says so."""
    handle_subagent_stop({"hook_event_name": "SubagentStop"})

    assert "no agent_transcript_path" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Regression guard — the hook makes no status write of its own
# ---------------------------------------------------------------------------


def test_hook_source_issues_no_plan_state_command() -> None:
    """task_status_hook.py's own source never builds a `plan state` invocation.

    `plan state` is the runner-less status move, and this hook always runs behind a runner the
    orchestrator dispatched. Reintroducing it would reinstate two writers of one fact — and on a
    ledger plan it would also fail outright, because `state` requires `--reason`.
    """
    source = _hook_path.read_text(encoding="utf-8")

    assert '"state"' not in source, "the hook must not issue `plan state`"
    assert '"--new-status"' not in source, "the hook must not set a task status"


# ---------------------------------------------------------------------------
# main() event routing — only SubagentStop reaches the SAM CLI
#
# Was red at HEAD 58f37d7be: main() sent PostToolUse + Bash to handle_activity_update, which
# drove two _call_sam_cli calls — `plan read` (via _call_sam_task_status) then `plan update
# --last-activity` (via _call_sam_task_update) — the false liveness signal ARCHITECTURE.md says
# a hook must not approximate. The runner renews its own lease through the ledger on each
# read/update/renew --attempt instead (docs/work-ledger/runner-contract.md), so no event but
# SubagentStop has anything left to do here. Step 1a deletes the handler and both of its
# registrations and puts nothing in their place.
# ---------------------------------------------------------------------------

_NON_SETTLE_EVENTS = (
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "UserPromptSubmit",
    "Stop",
    "SubagentStart",
    "SessionStart",
    "SessionEnd",
    "Notification",
    "TaskCompleted",
)


@pytest.mark.parametrize("tool_name", ["Bash", "Write", "Edit", "MultiEdit", "Read"])
@pytest.mark.parametrize("event", _NON_SETTLE_EVENTS)
def test_only_subagent_stop_reaches_the_sam_cli(
    event: str,
    tool_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No event but SubagentStop, for any tool name, issues a subprocess or touches disk.

    Patches subprocess.Popen AND subprocess.run — one layer below _call_sam_cli — rather than
    _call_sam_cli itself, so this stays red however a reintroduced handler reached the CLI:
    _call_sam_cli's own implementation calls subprocess.Popen (task_status_hook.py:393), and a
    handler that built its own subprocess.run call instead is caught the same way. The mtime
    sweep over tmp_path (used as `cwd`) catches an in-process write that used no subprocess at
    all — a third way a reintroduced handler could leave the "false liveness signal"
    ARCHITECTURE.md prohibits.
    """
    # Arrange
    monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    payload = {
        "hook_event_name": event,
        "tool_name": tool_name,
        "session_id": "sess-1",
        "cwd": str(tmp_path),
        "tool_input": {"command": "pytest"},
    }
    mocker.patch.object(_hook_mod, "parse_hook_input", return_value=payload)
    popen = mocker.patch("subprocess.Popen", side_effect=AssertionError("hook spawned a process"))
    run = mocker.patch("subprocess.run", side_effect=AssertionError("hook spawned a process"))
    before = sorted((p.relative_to(tmp_path), p.stat().st_mtime_ns) for p in tmp_path.rglob("*"))

    # Act
    with pytest.raises(SystemExit) as exc_info:
        _hook_mod.main()

    # Assert
    assert exc_info.value.code == 0
    popen.assert_not_called()
    run.assert_not_called()
    after = sorted((p.relative_to(tmp_path), p.stat().st_mtime_ns) for p in tmp_path.rglob("*"))
    assert after == before
    assert capsys.readouterr() == ("", "")


# ---------------------------------------------------------------------------
# Registration — task_status_hook.py is registered only under SubagentStop
#
# Was red at HEAD 58f37d7be: hooks.json also registered it under PostToolUse (hooks.json:42),
# and start-task/SKILL.md's own frontmatter carried a second PostToolUse registration writing
# the same content-store field. hooks.json already fires in every sub-agent of the session, so
# the frontmatter copy added no coverage of its own — only a second write. Step 1a deletes both.
# ---------------------------------------------------------------------------

_HOOK_SCRIPT = "task_status_hook.py"


def _frontmatter(path: Path) -> dict[str, Any]:
    """Return a skill's or agent's parsed YAML frontmatter dict, or `{}` when it has none.

    Anchored to a leading `---` line and its own closing `---` line on its own line — unlike
    an unanchored ``text.split("---", 2)[1]``, a bare `---` appearing inside a value (a
    `description:` string, for instance) cannot end the block early.

    Args:
        path: A `SKILL.md` or agent `.md` file.

    Returns:
        The parsed frontmatter mapping, or `{}` when the file has no frontmatter block or the
        block does not parse to a mapping.
    """
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A\ufeff?---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not match:
        return {}
    parsed = coerce_to_plain(load_yaml(match.group(1)))
    return parsed if isinstance(parsed, dict) else {}


def _hook_sources() -> list[tuple[str, dict[str, Any]]]:
    """Return every `(source label, hooks mapping)` this plugin could register a hook through.

    Covers the three places Claude Code reads a plugin's hook registrations from: `hooks/*.json`,
    every `*-plugin/plugin.json` manifest (`hooks` inline as an object, or as a string path to
    another JSON file — both forms are valid per the plugin.json schema), and any skill's or
    agent's own frontmatter `hooks:` key.

    Returns:
        One entry per source file that carries a `hooks` mapping, keyed by that file's path (or,
        for a manifest's `hooks`-by-path form, the referenced file's own path).
    """
    sources: list[tuple[str, dict[str, Any]]] = []

    for hooks_file in sorted((_plugin_dir / "hooks").glob("*.json")):
        hooks = json.loads(hooks_file.read_text(encoding="utf-8")).get("hooks")
        if isinstance(hooks, dict):
            sources.append((str(hooks_file), hooks))

    for manifest in sorted(_plugin_dir.glob(".*-plugin/plugin.json")):
        raw_hooks = json.loads(manifest.read_text(encoding="utf-8")).get("hooks")
        if isinstance(raw_hooks, dict):
            sources.append((str(manifest), raw_hooks))
        elif isinstance(raw_hooks, str):
            referenced = (manifest.parent / raw_hooks).resolve()
            hooks = json.loads(referenced.read_text(encoding="utf-8")).get("hooks")
            if isinstance(hooks, dict):
                sources.append((str(referenced), hooks))

    markdown_files = (
        *sorted((_plugin_dir / "skills").rglob("SKILL.md")),
        *sorted((_plugin_dir / "agents").glob("*.md")),
    )
    for md_path in markdown_files:
        fm_hooks = _frontmatter(md_path).get("hooks")
        if isinstance(fm_hooks, dict):
            sources.append((str(md_path), fm_hooks))

    return sources


def _registrations_of(hook_script: str, sources: list[tuple[str, dict[str, Any]]]) -> set[tuple[str, str]]:
    """Return the `(source, event)` pairs where *hook_script* appears in that event's hook groups.

    Args:
        hook_script: The command-line substring identifying the hook script (its filename).
        sources: The `(source label, hooks mapping)` pairs `_hook_sources` returns.

    Returns:
        One `(source, event)` pair per event whose hook-group JSON mentions `hook_script`.
    """
    return {
        (source, event)
        for source, hooks in sources
        for event, groups in hooks.items()
        if hook_script in json.dumps(groups)
    }


def test_task_status_hook_is_registered_only_for_subagent_stop() -> None:
    """Every registration of task_status_hook.py, across every place Claude Code reads one from,
    names SubagentStop and nothing else — not the plugin manifests, not a second `hooks/*.json`,
    and not any skill's or agent's own frontmatter.
    """
    registrations = _registrations_of(_HOOK_SCRIPT, _hook_sources())

    assert registrations, "task_status_hook.py must be registered somewhere"
    assert {event for _, event in registrations} == {"SubagentStop"}, registrations


def test_hook_sources_reads_hooks_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The hooks/*.json branch of `_hook_sources`, in isolation, flags a PostToolUse entry.

    Exercises the mechanism against a scratch plugin tree — never the real `hooks.json` — so a
    reintroduced `task_status_hook.py` registration under PostToolUse there is caught by this
    branch alone, independent of the manifest and frontmatter branches (I4).
    """
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "hooks.json").write_text(
        json.dumps({"hooks": {"PostToolUse": [{"hooks": [{"command": f"uv run {_HOOK_SCRIPT}"}]}]}}), encoding="utf-8"
    )
    (tmp_path / "skills").mkdir()
    (tmp_path / "agents").mkdir()
    monkeypatch.setattr(sys.modules[__name__], "_plugin_dir", tmp_path)

    registrations = _registrations_of(_HOOK_SCRIPT, _hook_sources())

    assert "PostToolUse" in {event for _, event in registrations}


def test_hook_sources_reads_inline_manifest_hooks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A `*-plugin/plugin.json`'s inline `"hooks"` object is read, on its own (I4)."""
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"hooks": {"PostToolUse": [{"hooks": [{"command": f"uv run {_HOOK_SCRIPT}"}]}]}}), encoding="utf-8"
    )
    (tmp_path / "hooks").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / "agents").mkdir()
    monkeypatch.setattr(sys.modules[__name__], "_plugin_dir", tmp_path)

    registrations = _registrations_of(_HOOK_SCRIPT, _hook_sources())

    assert "PostToolUse" in {event for _, event in registrations}


def test_hook_sources_reads_manifest_hooks_by_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A `*-plugin/plugin.json`'s `"hooks"` string is followed to its referenced file (I4)."""
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"hooks": "./other-hooks.json"}), encoding="utf-8"
    )
    (tmp_path / ".claude-plugin" / "other-hooks.json").write_text(
        json.dumps({"hooks": {"PostToolUse": [{"hooks": [{"command": f"uv run {_HOOK_SCRIPT}"}]}]}}), encoding="utf-8"
    )
    (tmp_path / "hooks").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / "agents").mkdir()
    monkeypatch.setattr(sys.modules[__name__], "_plugin_dir", tmp_path)

    registrations = _registrations_of(_HOOK_SCRIPT, _hook_sources())

    assert "PostToolUse" in {event for _, event in registrations}


def test_hook_sources_reads_skill_frontmatter_and_is_not_fooled_by_a_mid_value_delimiter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A skill's own frontmatter `hooks:` key is read, on its own, and a `---` inside an
    unrelated frontmatter value does not end the block early (I4's frontmatter-fragility point).
    """
    skill_dir = tmp_path / "skills" / "some-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: some-skill\n"
        'description: "use --- as a separator here"\n'
        "hooks:\n"
        "  PostToolUse:\n"
        "    - hooks:\n"
        f'        - command: "uv run {_HOOK_SCRIPT}"\n'
        "---\n\n# Body\n",
        encoding="utf-8",
    )
    (tmp_path / "hooks").mkdir()
    (tmp_path / "agents").mkdir()
    monkeypatch.setattr(sys.modules[__name__], "_plugin_dir", tmp_path)

    registrations = _registrations_of(_HOOK_SCRIPT, _hook_sources())

    assert "PostToolUse" in {event for _, event in registrations}
