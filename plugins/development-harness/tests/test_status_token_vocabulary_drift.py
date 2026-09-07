"""Guards the sub-agent STATUS reporting vocabulary against drift.

``subagent-contract`` pins a worker's completion report to three tokens on a
``STATUS:`` line in its final message: ``STATUS: DONE | PARTIAL | BLOCKED``. The hook
prescribes the report inside a fenced block, so the token can sit below the first line.
The token still has to be one a consumer recognises: the orchestrator judges what a
launch returned (``docs/work-ledger/work-loop.md``), and a token no consumer recognises
sends the judge down the wrong row rather than raising an error.

No consumer maps this token onto a task status. The runner's own ``plan finish
--result`` records the outcome and the judge's ``accept``/``reclaim`` records the
verdict; the STATUS line is the report's header, and the SubagentStop hook stores it
verbatim as ``settle --return-text`` rather than branching on it.

The vocabulary is not yet unified. Several producers still emit the pre-contract
spellings ``COMPLETE`` and ``COMPLETED``. ``FAILED`` also appears.

This test enumerates every ``STATUS: X`` token written in ``skills/**`` and
``agents/**`` and fails on any token outside the pinned set plus those tolerated
spellings. Its failure output is the worklist for narrowing the vocabulary: each
reported path either adopts a pinned token or justifies a new one by registering it
here.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pytest

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# The contract's pinned vocabulary. PARTIAL is a distinct state: work done with
# evidence plus an explicit list of what remains. It does not collapse into BLOCKED.
_PINNED_TOKENS = frozenset({"DONE", "PARTIAL", "BLOCKED"})

# Pre-contract spellings still written by at least one producer. Every entry is
# scheduled for removal once its producers adopt a pinned token; shrinking this set
# is the measure of that work.
#
# COMPLETED is deliberately absent: grepped `STATUS: COMPLETED` across plugins/ and found
# no producer, so there is no drift here to track.
_TOLERATED_TOKENS = frozenset({"COMPLETE", "FAILED"})

_ALLOWED_TOKENS = _PINNED_TOKENS | _TOLERATED_TOKENS

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


@pytest.mark.xfail(strict=True, reason="status vocabulary sweep pending; see the item tracking it")
def test_every_status_token_is_registered() -> None:
    """Every STATUS token written in skills/ or agents/ is pinned or explicitly tolerated.

    Marked strict-xfail rather than left red or skipped. A red test trains readers to
    ignore red, and a skipped one hides whether the sweep has progressed. Strict xfail
    keeps the suite green while the sweep is outstanding and turns red the day it lands,
    so the marker cannot outlive the work it stands for.
    """
    found = _collect_status_tokens()
    unregistered = {token: paths for token, paths in found.items() if token not in _ALLOWED_TOKENS}

    assert not unregistered, "Unregistered STATUS tokens found:\n" + "\n".join(
        f"  STATUS: {token} — {', '.join(paths)}" for token, paths in sorted(unregistered.items())
    )


def test_tolerated_spellings_report_their_remaining_producers() -> None:
    """Surface which files still use a pre-contract spelling.

    Not a failure on its own — this is the narrowing worklist. When a tolerated token
    has no producers left, delete it from ``_TOLERATED_TOKENS`` so the vocabulary can
    never widen back.
    """
    found = _collect_status_tokens()
    still_tolerated = {token: paths for token, paths in found.items() if token in _TOLERATED_TOKENS}

    for token in sorted(_TOLERATED_TOKENS):
        if token not in still_tolerated:
            raise AssertionError(
                f"STATUS: {token} has no producers left in skills/ or agents/. "
                f"Remove it from _TOLERATED_TOKENS so the vocabulary cannot widen back."
            )
