"""Guards runtime-read plugin files against retired-term regressions (PR #3427).

Step 1c of PR #3427 deletes the `.dh/language-manifest.yaml` format, the Process Flow
Override manifest section, and the dead Layer 2 stack-profile concept, replacing role and
gate resolution with `mcp__plugin_dh_backlog__profile_list()`. Once a term is retired,
nothing stops a later edit from reintroducing it in a file an installed Claude Code agent
actually reads or runs at runtime. This module is that guard: one row per retired term,
each checked against the same runtime corpus.

Scope (`_iter_runtime_files`): every `.md`, `.json`, `.yaml`, `.yml`, `.py`, `.cjs` and
`.mjs` file under `skills/`, `agents/`, `hooks/`, `templates/` and `docs/`, plus this
plugin's own `AGENTS.md` and `README.md` and the repo-root `.claude/skills/
evaluate-sdlc-layers/` copy — the files an installed agent actually reads or runs, as
opposed to design-time `docs/audits`, `docs/plans`, `docs/workflow-layers` and this test
suite's own `tests/` directory, or a generated graph (`graphify-out/`,
`docs/workflow-result.json`, `docs/dh-workflow-graph.json`). `test_scan_corpus_is_the_plugin`
guards the corpus itself against silently scanning nothing; `_find_hits` matches against a
file's whole text rather than one line at a time, so a term hard-wrapped across two lines
(normal prose in this plugin) is still caught — see `test_hits_span_two_lines`. Each
pattern's own spelling coverage is guarded by `test_retired_term_pattern_matches_its_spellings`,
which also asserts the compound-word strings a naive dash-based pattern would false-positive
on (`full-stack`, `per-stack`) do NOT match.

A retired term's own commit turns its row green by removing the term from the runtime
corpus; a later retirement adds a further row — appending a `RetiredTerm(...)` to
`_RETIRED_TERMS` is a one-line change.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

_PLUGIN_ROOT: Final = Path(__file__).resolve().parent.parent
_REPO_ROOT: Final = _PLUGIN_ROOT.parent.parent

# Design-history and generated-graph paths: their prose describes retired concepts as
# history, or their content is machine-generated from runtime files, so they are not part
# of what an installed agent reads to decide what to do next.
_EXCLUDED_DIR_PARTS: Final = frozenset({"audits", "plans", "workflow-layers", "tests", "graphify-out", "__pycache__"})
_EXCLUDED_FILES: Final = frozenset({
    _PLUGIN_ROOT / "docs" / "workflow-result.json",
    _PLUGIN_ROOT / "docs" / "dh-workflow-graph.json",
})
_SCAN_ROOTS: Final = (
    _PLUGIN_ROOT / "AGENTS.md",
    _PLUGIN_ROOT / "README.md",
    _PLUGIN_ROOT / "skills",
    _PLUGIN_ROOT / "agents",
    _PLUGIN_ROOT / "hooks",
    _PLUGIN_ROOT / "templates",
    _PLUGIN_ROOT / "docs",
    _REPO_ROOT / ".claude" / "skills" / "evaluate-sdlc-layers",
)
_SUFFIXES: Final = frozenset({".md", ".json", ".yaml", ".yml", ".py", ".cjs", ".mjs"})


@dataclass(frozen=True, slots=True)
class RetiredTerm:
    """One term this plugin's runtime files must never reintroduce.

    Attributes:
        label: Short human-readable name, used as the parametrized test id.
        pattern: Compiled regex matched against each runtime file's whole text.
        reason: Why the term is retired, shown in the failure message.
        samples: Spellings `pattern` must match — the regression
            `test_retired_term_pattern_matches_its_spellings` guards against a pattern that
            silently stops matching anything (a typo, an over-narrow rewrite).
        non_samples: Strings `pattern` must NOT match — compound words or adjacent flags
            that share a substring with the retired term but are not it.
    """

    label: str
    pattern: re.Pattern[str]
    reason: str
    samples: tuple[str, ...]
    non_samples: tuple[str, ...] = ()


_RETIRED_TERMS: Final[tuple[RetiredTerm, ...]] = (
    RetiredTerm(
        label="language manifest",
        pattern=re.compile(r"language[-_\s]*manifest", re.IGNORECASE),
        reason=(
            "The `.dh/language-manifest.yaml` format and its schema/template docs are deleted "
            "(PR #3427 step 1c). No code reads that format; roles and quality gates resolve "
            "through `mcp__plugin_dh_backlog__profile_list()` and repository discovery instead."
        ),
        samples=("Language-Manifest", "language\nmanifest", "language_manifest", "LANGUAGE MANIFEST"),
    ),
    RetiredTerm(
        label="Flow Override",
        pattern=re.compile(r"flow[-_\s]*override", re.IGNORECASE),
        reason=(
            "The `Process Flow Override` language-manifest section is deleted with the manifest "
            "schema; nothing loads a language-plugin override."
        ),
        samples=("Flow override", "flow-override", "flow_override", "flow\noverride"),
    ),
    RetiredTerm(
        label="--stack",
        # Two ASCII hyphens (the literal flag), or one-or-two typographic dashes (the shape
        # prose autocorrect leaves behind when it "corrects" "--stack" — M3). The lookbehind
        # keeps a single ASCII hyphen out: "full-stack"/"per-stack"/"multi-stack" are ordinary
        # compound words in this plugin's prose and must not false-positive.
        pattern=re.compile(r"(?<![\w-])(?:--|[" r"\u2013\u2014" r"]{1,2})stack\b"),
        reason=(
            "The `--stack` flag on `work-backlog-item` is deleted: no skill or agent reads the "
            "'Stack profile' line it appends, so it has no runtime effect."
        ),
        samples=("--stack", "--stack=fastapi", "\u2014stack", "\u2013stack"),
        non_samples=("full-stack", "per-stack", "multi-stack web app", "stack-conditional rules"),
    ),
    RetiredTerm(
        label="stack profile",
        pattern=re.compile(r"stack[-_\s]*profile", re.IGNORECASE),
        reason="Layer 2 stack profiles have no runtime consumer; the concept is retired with `--stack`.",
        samples=("Stack Profile", "stack-profile", "stack_profile", "stack\nprofile"),
    ),
    RetiredTerm(
        label="--language",
        # Bounded on both sides so "--language-server" (a real, unrelated flag shape) does not
        # false-positive on the trailing `\b` a plain `--language\b` pattern would accept (M3).
        pattern=re.compile(r"(?<![\w-])--language(?![\w-])"),
        reason=(
            "The `--language` flag exists only to route to "
            "`plugins/typescript-development:add-new-feature`, which does not exist in this "
            "repo's `plugins/` tree, so the flag can never do what it documents."
        ),
        samples=("--language python", "--language=en"),
        non_samples=("--language-server",),
    ),
)


def _iter_runtime_files() -> list[Path]:
    """Return every file an installed Claude Code agent can read or run at runtime.

    See the module docstring for the roots, suffixes and exclusions this applies.

    Returns:
        A sorted, de-duplicated list of runtime file paths.
    """
    files: set[Path] = set()
    for root in _SCAN_ROOTS:
        candidates = [root] if root.is_file() else root.rglob("*")
        for candidate in candidates:
            if not candidate.is_file() or candidate.suffix not in _SUFFIXES:
                continue
            if candidate in _EXCLUDED_FILES:
                continue
            if _EXCLUDED_DIR_PARTS.intersection(candidate.parts):
                continue
            files.add(candidate)
    return sorted(files)


def _relative_label(path: Path) -> str:
    """Return `path` relative to whichever scan root owns it, for a readable failure message.

    Args:
        path: A file `_iter_runtime_files` returned, or a fixture path in a unit test.

    Returns:
        `path` relative to `_PLUGIN_ROOT` or `_REPO_ROOT`, or `str(path)` when neither
        contains it (a fixture path outside the scanned roots).
    """
    for base in (_PLUGIN_ROOT, _REPO_ROOT):
        if path.is_relative_to(base):
            return str(path.relative_to(base))
    return str(path)


def _find_hits(term: RetiredTerm, files: Iterable[Path] | None = None) -> list[str]:
    """Return one `path:line: text` entry per runtime-corpus match of `term`.

    Matches against each file's whole text rather than one line at a time, so a term
    hard-wrapped across two lines is still caught (C1) — normal prose in this plugin, and a
    line-at-a-time scan gave it about the same chance of reintroduction as any other wrap.

    Args:
        term: The retired term to scan for.
        files: The files to scan. Defaults to `_iter_runtime_files()`; a test may pass a
            fixture file list instead to exercise this function in isolation.

    Returns:
        One formatted hit per match, in file order.
    """
    corpus = list(files) if files is not None else _iter_runtime_files()
    hits: list[str] = []
    for path in corpus:
        text = path.read_text(encoding="utf-8")
        for match in term.pattern.finditer(text):
            lineno = text.count("\n", 0, match.start()) + 1
            hits.append(f"{_relative_label(path)}:{lineno}: {match.group(0)!r}")
    return hits


def test_scan_corpus_is_the_plugin() -> None:
    """`_iter_runtime_files` finds a known runtime file and is not accidentally empty.

    Regression (I2): if this test module moved, or a scan-root constant were mistyped,
    `Path.rglob` on a missing directory silently yields nothing and every retired-term row
    would pass by scanning zero files rather than by the term being absent.
    """
    files = _iter_runtime_files()

    assert _PLUGIN_ROOT / "skills" / "start-task" / "SKILL.md" in files
    assert len(files) > 100


@pytest.mark.parametrize("term", _RETIRED_TERMS, ids=[term.label for term in _RETIRED_TERMS])
def test_retired_term_pattern_matches_its_spellings(term: RetiredTerm) -> None:
    """Each retired term's pattern matches every spelling it claims to, and no others.

    Regression (I2): a pattern typo (`r"language[- ]manfest"`) or an over-narrow rewrite
    stays green forever once nothing checks that it still matches anything. The
    `non_samples` half guards the opposite failure (M3): a pattern widened to catch a
    typographic-dash variant must not start matching an unrelated compound word.
    """
    for sample in term.samples:
        assert term.pattern.search(sample), f"{term.label!r} pattern did not match {sample!r}"
    for non_sample in term.non_samples:
        assert not term.pattern.search(non_sample), f"{term.label!r} pattern wrongly matched {non_sample!r}"


def test_hits_span_two_lines(tmp_path: Path) -> None:
    """A retired term hard-wrapped across two lines is still caught.

    Regression (C1): `skills/context-integration/SKILL.md:146-147` reads "the project's
    language" / "manifest to find the appropriate codebase-analysis role" — a runtime skill
    still telling agents to use a language manifest, wrapped exactly like this fixture. A
    line-at-a-time scan reported that file clean; `_find_hits` must not.
    """
    fixture = tmp_path / "wrapped.md"
    fixture.write_text("Use the project's language\nmanifest to find the role.\n", encoding="utf-8")
    term = next(t for t in _RETIRED_TERMS if t.label == "language manifest")

    hits = _find_hits(term, files=[fixture])

    assert len(hits) == 1
    assert hits[0].startswith(f"{fixture}:1:")


@pytest.mark.parametrize("term", _RETIRED_TERMS, ids=[term.label for term in _RETIRED_TERMS])
def test_runtime_files_have_no_retired_term(term: RetiredTerm) -> None:
    """No runtime-read plugin file reintroduces a retired term.

    What: scans every file `_iter_runtime_files` returns for `term.pattern` and fails if
    any match is found. Why: a retired mechanism's docs are easy to half-delete — one
    referrer survives an edit and an agent follows a dead instruction. Listing every
    offending file:line turns that into a concrete edit list instead of a second
    investigation.
    """
    hits = _find_hits(term)

    assert not hits, (
        f"Retired term {term.label!r} still appears in a runtime-read file. {term.reason} "
        "Offending file:line hits:\n" + "\n".join(hits)
    )
