"""Guards repo-root instruction files against path and acronym drift (#2498).

Split out of plugins/development-harness/tests/test_placeholder_vocabulary_drift.py: both
assertions here target repo-root files (`AGENTS.md`, `.claude/CLAUDE.md`) and the whole
`plugins/` tree, not dh plugin code. Under the dh plugin's standalone runner
(`plugins/development-harness/tests/run_pytest.py`), that file's `_REPO_ROOT` resolves to the
install's parent directory rather than this repo's root — the `AGENTS.md` read raised
`FileNotFoundError` there, and the `plugins/` scan silently passed having read zero files. This
repo's own AGENTS.md test-placement rule exists for exactly this failure shape: "A plugin test
placed in root `tests/` runs in CI but is invisible to that plugin's standalone runner, so its
coverage silently disappears" — the inverse applies to a repo-scoped test misplaced in a plugin.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_no_conflicting_rt_ica_acronym_expansion() -> None:
    """ "Real-Time Information Completeness Assessment" never appears under `plugins/`.

    RT-ICA is Reverse Thinking - Information Completeness Assessment (`rt-ica/SKILL.md`'s own
    H1). Two ARL reference files independently spelled out a different expansion; #2498's entry
    22 traced the user's own confusion about what RT-ICA does back to definitions like this one.
    Scanned whole-tree rather than scoped to one plugin: the wrong expansion has already been
    found in `agentskill-kaizen`'s ARL references once, and RT-ICA/Information-Completeness prose
    currently also lives in `plugin-creator`, `python-engineering`, and `the-rewrite-room` — any
    of them could carry the next copy-pasted wrong definition.
    """
    scanned = list((_REPO_ROOT / "plugins").rglob("*.md"))
    assert scanned, "scanned zero markdown files under plugins/ — this guard is not running"

    offenders = [
        str(path.relative_to(_REPO_ROOT))
        for path in scanned
        if "Real-Time Information Completeness" in path.read_text(encoding="utf-8")
    ]

    assert not offenders, (
        "RT-ICA is Reverse Thinking, not Real-Time — see plugins/development-harness/skills/"
        f"rt-ica/SKILL.md's own H1. Conflicting expansion found in: {offenders!r}"
    )


def test_no_stale_dot_claude_rules_path_references() -> None:
    """Every path this repo tells an agent to load under the old `.claude/rules/` prefix is gone.

    The rules directory moved to repo-root `rules/` in `bf4dcd876` ("cross-tool path-scoped
    rules"). AGENTS.md and `.claude/CLAUDE.md` both still told agents to load
    `.claude/rules/*.md` files that no longer exist at that path — an agent following the
    instruction literally (e.g. `.claude/CLAUDE.md:301`'s "load `.claude/rules/skill-substitution.md`
    before editing any SKILL.md") would load nothing and proceed unaware the safety rule never
    loaded. Scoped to `AGENTS.md`, `.claude/CLAUDE.md`, and `rules/prose-file-classification.md`
    — not the whole tree, since most other `.claude/rules/` mentions describe other projects'
    conventions, or (for plugin-shipped files distributed to other repos, e.g.
    `plugins/development-harness/agents/*.md`) intentionally keep the portable `.claude/rules/`
    form rather than this repo's own `rules/` layout.
    """
    targets = [
        _REPO_ROOT / "AGENTS.md",
        _REPO_ROOT / ".claude" / "CLAUDE.md",
        _REPO_ROOT / "rules" / "prose-file-classification.md",
    ]
    offenders = [
        str(path.relative_to(_REPO_ROOT)) for path in targets if ".claude/rules/" in path.read_text(encoding="utf-8")
    ]

    assert not offenders, f"Stale `.claude/rules/` reference (moved to repo-root `rules/`) in: {offenders!r}"
