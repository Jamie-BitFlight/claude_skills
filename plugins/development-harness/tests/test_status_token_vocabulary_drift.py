"""Guards the sub-agent STATUS reporting vocabulary against drift.

Two files in this repository are both called some spelling of "sub-agent contract" and they pin
different token sets on purpose. This module tests exactly one of them, named here by path so the
bare name can never be what a reader resolves:

- ``plugins/development-harness/skills/subagent-contract/SKILL.md`` — this plugin's contract, and
  the one every path under ``_SEARCH_ROOTS`` answers to. It pins ``STATUS: DONE`` and
  ``STATUS: BLOCKED``.
- ``plugins/agent-orchestration/skills/delegate/references/sub-agent-contract.md`` — a different
  plugin's contract for delegations with no work ledger behind them. It pins a third token,
  ``STATUS: PARTIAL``. Nothing in this plugin follows it, and no test here scans for it.

Why this plugin's set has no ``PARTIAL``: a dispatch here names a ledger address, and the outcome
of the work is what ``plan finish --result`` records, not what the ``STATUS:`` line says. The
values that command accepts are ``FINISH_RESULTS`` in ``dh_core/ledger/transitions.py``
(``complete``, ``failed``, ``blocked``, ``needs-input`` as of this test's writing) — there is no
partial among them. A worker with three tasks complete and one blocked has already recorded that,
one row per task, and ``docs/work-ledger/work-loop.md``'s judge branches on those rows. A
``STATUS: PARTIAL`` would encode a state the ledger cannot hold, in the one channel a resumed
session never sees. So the two channels stay separate and agree on which outcomes exist.

The ``STATUS:`` line is therefore a delivery signal, not an outcome: ``DONE`` once ``finish`` was
recorded whatever its ``--result``, ``BLOCKED`` when no ``finish`` was possible. No consumer in
this plugin branches on the token — the SubagentStop hook stores the message verbatim as
``settle --return-text`` (see ``skills/implementation-manager/scripts/task_status_hook.py``, whose
module docstring gives the reason), and the judge reads the ledger. The token still has to be one
the humans and agents reading that return text recognise, and it has to be the same token every
producer writes, which is what these tests hold.

``_RETIRED_TOKENS`` is the load-bearing guard. ``PARTIAL``, ``COMPLETE`` and ``FAILED`` were all
written by producers in this plugin and have been removed; that test fails the moment one comes
back, and it is a plain test rather than an xfail so it cannot be masked by the unrelated tokens
the vocabulary sweep has yet to reach.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pytest

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PLUGIN_ROOT.parent.parent

# This plugin's contract, pinned by skills/subagent-contract/SKILL.md.
_CONTRACT = _PLUGIN_ROOT / "skills" / "subagent-contract" / "SKILL.md"
_PINNED_TOKENS = frozenset({"DONE", "BLOCKED"})

# The other plugin's contract, tested only for the fact this module's docstring asserts about it.
_SIBLING_CONTRACT = (
    _REPO_ROOT / "plugins" / "agent-orchestration" / "skills" / "delegate" / "references" / "sub-agent-contract.md"
)
_SIBLING_PINNED_TOKENS = frozenset({"DONE", "PARTIAL", "BLOCKED"})

# Spellings this plugin's producers once wrote and no longer do. Reintroducing any of them
# re-splits the vocabulary, so this set only ever grows.
#
# PARTIAL, COMPLETE and FAILED came from skills/work-milestone — its worker protocol emitted all
# three and its orchestrator branched on the first two. The worker now reports DONE/BLOCKED and the
# orchestrator reads the ledger rows instead.
#
# COMPLETED is deliberately absent: grepped `STATUS: COMPLETED` across plugins/ and found no
# producer, so it was never a spelling in use here and there is nothing to retire.
_RETIRED_TOKENS = frozenset({"PARTIAL", "COMPLETE", "FAILED"})

_ALLOWED_TOKENS = _PINNED_TOKENS

# Matches a reported status token, e.g. "STATUS: DONE" or "STATUS: IN PROGRESS".
# Consumes the full run of upper-case words so a multi-word state is captured whole
# rather than truncated to its first word — a truncated token is a phantom finding.
# Lower-case following prose terminates the match, and the space separator cannot
# cross a newline, so a template's next field (e.g. "TASK:") is never absorbed.
_STATUS_TOKEN_RE = re.compile(r"\bSTATUS:[ \t]*([A-Z][A-Z0-9_]*(?:[ \t-][A-Z][A-Z0-9_]*)*)")

# Tokens that appear only as placeholders in templates describing the format itself,
# never as a status a worker actually reports.
_PLACEHOLDER_TOKENS = frozenset({"X", "TOKEN", "STATUS", "N"})

_SEARCH_ROOTS = ("skills", "agents")


def _collect_status_tokens() -> dict[str, list[str]]:
    """Map each STATUS token found to the paths that write it.

    Returns:
        Token (upper-cased) to sorted list of plugin-relative paths mentioning it.
    """
    found: dict[str, set[str]] = defaultdict(set)
    for root in _SEARCH_ROOTS:
        for path in sorted((_PLUGIN_ROOT / root).rglob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in _STATUS_TOKEN_RE.finditer(text):
                token = match.group(1).upper()
                if token in _PLACEHOLDER_TOKENS:
                    continue
                found[token].add(str(path.relative_to(_PLUGIN_ROOT)))
    return {token: sorted(paths) for token, paths in found.items()}


def test_retired_spellings_have_no_producers() -> None:
    """No file under skills/ or agents/ writes a retired STATUS spelling.

    This is the reintroduction guard, and the reason it is a plain test: the whole-vocabulary
    check below is an xfail while unrelated tokens remain, so a retired spelling coming back
    would not turn it red. Reintroducing one here fails immediately and names the file.
    """
    found = _collect_status_tokens()
    revived = {token: paths for token, paths in found.items() if token in _RETIRED_TOKENS}

    assert not revived, (
        "Retired STATUS spellings are back:\n"
        + "\n".join(f"  STATUS: {token} — {', '.join(paths)}" for token, paths in sorted(revived.items()))
        + "\nThis plugin pins "
        + " and ".join(f"STATUS: {token}" for token in sorted(_PINNED_TOKENS))
        + f"; see {_CONTRACT.relative_to(_PLUGIN_ROOT)} for why, and record the outcome with "
        "`plan finish --result` rather than in the STATUS line."
    )


def test_contract_pins_the_tokens_this_module_guards() -> None:
    """The contract file this module cites still pins exactly the tokens it says it does.

    Without this, ``_PINNED_TOKENS`` is a claim about a file nothing rereads, and the contract
    could widen or narrow without a single test noticing.
    """
    text = _CONTRACT.read_text(encoding="utf-8")
    pinned = {match.group(1).upper() for match in _STATUS_TOKEN_RE.finditer(text)} - _PLACEHOLDER_TOKENS

    assert pinned == set(_PINNED_TOKENS), (
        f"{_CONTRACT.relative_to(_PLUGIN_ROOT)} writes {sorted(pinned)}, "
        f"but this module guards {sorted(_PINNED_TOKENS)}. Reconcile them before the producers drift."
    )


def test_sibling_plugin_contract_still_pins_a_wider_set() -> None:
    """The agent-orchestration contract keeps PARTIAL, which this module's docstring relies on.

    The two contracts share a name and not a vocabulary, and that difference is the whole reason
    this module names its own contract by path. If the sibling ever narrows to DONE/BLOCKED, the
    distinction is gone and the docstring above needs rewriting rather than preserving.
    """
    if not _SIBLING_CONTRACT.exists():
        pytest.skip(f"{_SIBLING_CONTRACT} is not present in this checkout")

    text = _SIBLING_CONTRACT.read_text(encoding="utf-8")
    pinned = {match.group(1).upper() for match in _STATUS_TOKEN_RE.finditer(text)} - _PLACEHOLDER_TOKENS

    assert pinned == set(_SIBLING_PINNED_TOKENS), (
        f"{_SIBLING_CONTRACT} writes {sorted(pinned)}, not {sorted(_SIBLING_PINNED_TOKENS)}. "
        "This module's docstring describes the two contracts as deliberately different; update it "
        "to match what that file now says."
    )


@pytest.mark.xfail(strict=True, reason="status vocabulary sweep pending; see the item tracking it")
def test_every_status_token_is_registered() -> None:
    """Every STATUS token written in skills/ or agents/ is one this plugin's contract pins.

    Marked strict-xfail rather than left red or skipped. A red test trains readers to ignore red,
    and a skipped one hides whether the sweep has progressed. Strict xfail keeps the suite green
    while the sweep is outstanding and turns red the day it lands, so the marker cannot outlive the
    work it stands for. Its failure output is the worklist: each reported path either adopts a
    pinned token or justifies a new one by registering it here.

    A retired spelling coming back is caught by ``test_retired_spellings_have_no_producers``
    instead, which this xfail would otherwise hide.
    """
    found = _collect_status_tokens()
    unregistered = {token: paths for token, paths in found.items() if token not in _ALLOWED_TOKENS}

    assert not unregistered, "Unregistered STATUS tokens found:\n" + "\n".join(
        f"  STATUS: {token} — {', '.join(paths)}" for token, paths in sorted(unregistered.items())
    )
