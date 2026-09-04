"""Guards the work-backlog-item placeholder vocabulary and adjacent doc-drift classes (#2498).

A single `/dh:work-backlog-item #2498` run logged 26 workarounds
(`.tmp/dh-workarounds-during-work.rst`). Several trace to the same failure shape: a rename or a
fallback pattern lands in one file and never propagates to its siblings, because nothing enforces
the pattern once it exists. `70c1fa18e` split `<mode/>` into `mode`/`route`/`item_ref`/`user_text`
in `SKILL.md` only, leaving 14 misuse occurrences across `references/workflows/`; `f0ea6f6e1`
added an "Impact Radius" -> "Resources" fallback pair to `groom-check.md` only, leaving
`feasibility-gate.md` to silently count zero files when an item predates that section name.

This test does not attempt to parse per-line semantics of what `<mode/>` "means" — that is
exactly the brittle, line-frozen approach this file's own retro rejected. Each assertion instead
checks a structural invariant that survives an unrelated edit to the surrounding prose: a
placeholder that legitimately carries the auto|interactive value always sits on a line that also
says so; a rename this repo already completed leaves zero fossils in the files it touched; every
placeholder actually used resolves to a schema field; a fallback pattern this repo already adopted
in one file is present in every file reading the same primary key; and a path this repo's own
instructions tell an agent to load actually resolves on disk.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PLUGIN_ROOT.parent.parent
_WORKFLOWS_ROOT = _PLUGIN_ROOT / "skills" / "work-backlog-item" / "references" / "workflows"
_PARSE_SCHEMA = _PLUGIN_ROOT / "skills" / "work-backlog-item" / "scripts" / "parser" / "parse.schema.json"
_ADD_NEW_FEATURE_SKILL = _PLUGIN_ROOT / "skills" / "add-new-feature" / "SKILL.md"

# Files that never legitimately carry the `<mode/>` placeholder after the C2 rename: the
# no-argument path and every route-word trigger use `<item_ref/>`/`<route/>`/plain prose instead.
_MODE_FREE_FILES = frozenset({
    "work/interactive-browser.md",
    "close/start.md",
    "setup-github/start.md",
    "progress/start.md",
    "resume/start.md",
    "quick/start.md",
})

_PLACEHOLDER_RE = re.compile(r"<([a-z_]+)/>")


def _iter_workflow_files() -> list[Path]:
    return sorted(_WORKFLOWS_ROOT.rglob("*.md"))


def test_every_mode_placeholder_line_names_its_own_value() -> None:
    """Every remaining `<mode/>` occurrence sits on a line that says `auto` or `interactive`.

    A file-level allowlist cannot express this: `issue-first.md`, `find-item.md`, and
    `locate.md` each legitimately keep some `<mode/>` occurrences (the auto|interactive sense)
    right alongside lines this repo's C2 fix rewrote to `<item_ref/>`/`<route/>` (the misuse
    sense) — allowlisting the whole file would hide a regression into the very lines just fixed.
    """
    offenders: list[str] = []
    for path in _iter_workflow_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "<mode/>" not in line:
                continue
            if "auto" not in line and "interactive" not in line:
                offenders.append(f"{path.relative_to(_WORKFLOWS_ROOT)}:{lineno}: {line.strip()}")

    assert not offenders, (
        "`<mode/>` used where the surrounding prose does not say `auto` or `interactive` — this "
        "is the item-ref/route-word misuse #2498 found (entry 2), not the mode-value sense. "
        f"Substitute `<item_ref/>`, `<route/>`, or plain prose instead: {offenders!r}"
    )


def test_mode_free_files_stay_mode_free() -> None:
    """The six files the C2 rename cleared entirely never reacquire `<mode/>`."""
    offenders = {
        name: True for name in _MODE_FREE_FILES if "<mode/>" in (_WORKFLOWS_ROOT / name).read_text(encoding="utf-8")
    }

    assert not offenders, (
        "These files were rewritten to use `<item_ref/>`/`<route/>`/plain prose because they "
        f"never legitimately carry the mode-value sense of `<mode/>`: {sorted(offenders)!r}"
    )


def test_every_workflow_placeholder_is_a_declared_schema_field() -> None:
    """Every `<key/>` used under `references/workflows/**` is a `parse.schema.json` property.

    `locate.md` previously used `<invocation_args/>`, which the parser never produces — an
    agent following that line had nothing to substitute. C2 reworded it; this guards the class.
    """
    schema = json.loads(_PARSE_SCHEMA.read_text(encoding="utf-8"))
    declared = set(schema["properties"])

    used: set[str] = set()
    for path in _iter_workflow_files():
        used |= set(_PLACEHOLDER_RE.findall(path.read_text(encoding="utf-8")))

    undeclared = used - declared
    assert not undeclared, (
        f"Placeholder(s) {sorted(undeclared)!r} are used under references/workflows/ but are not "
        f"properties of {_PARSE_SCHEMA.relative_to(_REPO_ROOT)} — nothing in the parsed invocation "
        "ever produces a value for them. Either the placeholder is a typo/fossil (reword the doc) "
        "or the parser is missing a field (add it to parse.schema.json)."
    )


def test_no_conflicting_rt_ica_acronym_expansion() -> None:
    """ "Real-Time Information Completeness Assessment" never appears under `plugins/`.

    RT-ICA is Reverse Thinking - Information Completeness Assessment (`rt-ica/SKILL.md`'s own
    H1). Two ARL reference files independently spelled out a different expansion; #2498's entry
    22 traced the user's own confusion about what RT-ICA does back to definitions like this one.
    """
    offenders = [
        str(path.relative_to(_REPO_ROOT))
        for path in (_REPO_ROOT / "plugins").rglob("*.md")
        if "Real-Time Information Completeness" in path.read_text(encoding="utf-8")
    ]

    assert not offenders, (
        "RT-ICA is Reverse Thinking, not Real-Time — see plugins/development-harness/skills/"
        f"rt-ica/SKILL.md's own H1. Conflicting expansion found in: {offenders!r}"
    )


_IMPACT_RADIUS_EXTRACTION_RE = re.compile(r"""sections\[["']Impact Radius["']\]""")


def test_impact_radius_readers_carry_the_resources_fallback() -> None:
    """Every file that extracts `sections["Impact Radius"]` also names a `Resources` fallback.

    Matches on the bracket-access extraction pattern specifically (`sections["Impact Radius"]`),
    not every prose mention of the term — a table column header or a downstream consumer
    describing already-extracted content isn't the entry-8 bug class; a doc that reads the
    registry key directly and has no fallback is. `groom-check.md` already has the primary/
    fallback pair (added `f0ea6f6e1`, 2026-04-11). `feasibility-gate.md` and `groom-drift.md`
    read the same primary key without it (#2498 entry 8) and silently treat an older-template
    item's Impact Radius section as absent — zero file count — rather than falling back to the
    section older templates actually used.
    """
    offenders = [
        str(path.relative_to(_REPO_ROOT))
        for path in _WORKFLOWS_ROOT.rglob("*.md")
        for text in [path.read_text(encoding="utf-8")]
        if _IMPACT_RADIUS_EXTRACTION_RE.search(text) and "Resources" not in text
    ]

    assert not offenders, (
        "File(s) extract the primary Impact Radius key with no Resources fallback for older "
        f"grooming templates (see groom-check.md's existing pair): {offenders!r}"
    )


def test_start_md_todowrite_mandate_has_a_fallback_chain() -> None:
    """`work/start.md` never mandates `TodoWrite` bare — a fallback chain rides with it.

    `TodoWrite` doesn't exist in Codex/OpenCode, and this repo's own AGENTS.md forbids using it
    in favor of `bd` — the skill mandating it bare is unsatisfiable by design in either context
    (#2498 entry 3). The single remaining mention keeps a conditional phrase alongside it.
    """
    path = _WORKFLOWS_ROOT / "work" / "start.md"
    text = path.read_text(encoding="utf-8")

    offenders = [
        f"{path.relative_to(_WORKFLOWS_ROOT)}:{lineno}: {line.strip()}"
        for lineno, line in enumerate(text.splitlines(), start=1)
        if "TodoWrite" in line and not any(phrase in line for phrase in ("if it exists", "otherwise"))
    ]

    assert not offenders, (
        "`TodoWrite` mentioned without a fallback-chain phrase ('if it exists' / 'otherwise') on "
        f"the same line — this is a bare cross-harness-unsatisfiable mandate again: {offenders!r}"
    )


def test_artifact_registration_count_checks_are_followed_by_a_read_back() -> None:
    """Each `artifact list --artifact-type X` count check is followed by a content read-back.

    A count of 1 does not prove the content is real — entry 15 found `artifact_register` storing
    the literal string `$(cat ...)` as content, invisible to a count-only check. Structural check
    only: the next `artifact read` call for the same `--artifact-type` value must appear within
    the following 20 lines of `add-new-feature/SKILL.md`, not exact prose — the three sites use
    slightly different wording.
    """
    text = _ADD_NEW_FEATURE_SKILL.read_text(encoding="utf-8")
    lines = text.splitlines()

    count_check_re = re.compile(r"artifact list --item-id \{issue\} --artifact-type (\S+)")
    offenders: list[str] = []
    for lineno, line in enumerate(lines):
        match = count_check_re.search(line)
        if not match:
            continue
        artifact_type = match.group(1)
        window = "\n".join(lines[lineno : lineno + 20])
        if f"artifact read --item-id {{issue}} --artifact-type {artifact_type}" not in window:
            offenders.append(f"line {lineno + 1} (--artifact-type {artifact_type})")

    assert not offenders, (
        f"Count-only registration check(s) with no read-back within 20 lines: {offenders!r} — "
        f"a count can't detect a placeholder or empty registration (see {_ADD_NEW_FEATURE_SKILL.name}'s "
        "own 'read state, not by trusting a report' principle)."
    )


def test_no_stale_dot_claude_rules_path_references() -> None:
    """Every path this repo tells an agent to load under the old `.claude/rules/` prefix is gone.

    The rules directory moved to repo-root `rules/` in `bf4dcd876` ("cross-tool path-scoped
    rules"). AGENTS.md and `.claude/CLAUDE.md` both still told agents to load
    `.claude/rules/*.md` files that no longer exist at that path — an agent following the
    instruction literally (e.g. `.claude/CLAUDE.md:301`'s "load `.claude/rules/skill-substitution.md`
    before editing any SKILL.md") would load nothing and proceed unaware the safety rule never
    loaded. Scoped to this repo's own root instruction files, not the whole tree — most other
    `.claude/rules/` mentions in the repo describe a different project's convention or the
    generic Claude Code feature other projects use, which are not stale.
    """
    targets = [_REPO_ROOT / "AGENTS.md", _REPO_ROOT / ".claude" / "CLAUDE.md"]
    offenders = [
        str(path.relative_to(_REPO_ROOT)) for path in targets if ".claude/rules/" in path.read_text(encoding="utf-8")
    ]

    assert not offenders, f"Stale `.claude/rules/` reference (moved to repo-root `rules/`) in: {offenders!r}"
