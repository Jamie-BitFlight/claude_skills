#!/usr/bin/env python3
"""Report plugin runtime text that will not resolve for an installed consumer.

A plugin is distributed. Its runtime text is read by an agent whose working directory is the
consuming repo, which never had the authoring repo checked out. A path into that tree resolves
for the author and for nobody else, so the failure reaches real users and never reaches anyone
testing from the authoring checkout.

Runtime text is what loads with the artifact: ``SKILL.md`` bodies, agent bodies, and
``references/**``. Design-time siblings travel inside the package but never load
(``SKILL-GOALS.md``, ``MAINTENANCE.md``, ``BENCHMARKS.md``, ``maintenance/**``, ``evals/**``);
they are skipped, and a runtime link pointing *at* one of them is itself reported.

Four escape classes:

* ``repo-path`` — a path into the authoring repo's tree (``scripts/…``, ``rules/…``,
  ``tests/…``, ``docs/…``) that an installed consumer does not have.
* ``cross-plugin-path`` — a filesystem path into a sibling plugin.
* ``cross-plugin-skill`` — a ``<plugin>:<skill>`` activation of another plugin, reported with
  a same-line guard heuristic (see ``_GUARD_WORDS``) that triages but does not decide.
* ``design-time-link`` — a runtime link into a design-time artifact that never loads.

Three exemptions, and they are the spec rather than conveniences:

1. **Fenced blocks are never a finding.** The rule governs what the runtime agent is told to
   do. A fenced block shown as an anti-pattern is an illustration, not an instruction, so a
   document may quote every failure verbatim and still pass. Inline code spans and table cells
   are NOT exempt — real paths live in both, and exempting them would blind the check.
2. **Angle-bracket placeholders are exempt.** A token containing ``<`` or ``>``
   (``<plugin>/skills/<name>/SKILL.md``) names a shape, not a location. Generic examples
   belong in this form; an illustrative real path belongs in a fenced block instead.
3. **Variable-built paths are skipped, not verified.** A path on ``${CLAUDE_PLUGIN_ROOT}`` or
   ``${CLAUDE_SKILL_DIR}`` is never reported. Claude Code substitutes both in a ``SKILL.md``
   body; whether any other harness does is unestablished, so this exemption under-reports.
   Tracked as issue #3445.

Cross-plugin references are matched against an allowlist read from the ``plugins/`` directory,
so label values (``state:verified``) and placeholders (``plugin:skill-name``) stay out of the
results without maintaining a denylist of things that merely look like references.

Usage:
    audit_runtime_escapes.py --plugin-dir plugins/<name> [--out REPORT.md]
    audit_runtime_escapes.py --all [--out REPORT.md]

Exit codes:
    0: no escapes found
    1: escapes found
    2: the requested directory does not exist
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Directories under the plugin whose markdown loads at runtime.
_RUNTIME_ROOTS = ("skills", "agents")

# Design-time artifacts: they ship inside the package but never load with SKILL.md.
# Excluded from scanning, and a runtime link into one is reported as design-time-link.
_DESIGN_TIME_NAMES = frozenset({"SKILL-GOALS.md", "MAINTENANCE.md", "BENCHMARKS.md"})
_DESIGN_TIME_DIRS = frozenset({"maintenance", "evals"})

# Directory names that exist only in the authoring checkout, so a bare path into one is an
# escape wherever it appears.
#
# `scripts/` and `docs/` are deliberately absent. Both are valid *inside* a plugin — a skill
# bundles `scripts/`, and Technique 1 places shared docs at the plugin root `docs/` — so a
# bare `scripts/helper.py` in prose usually means the artifact's own, and flagging it reports
# portable code as broken. A genuinely repo-rooted one is caught by the markdown-link and
# `plugins/<other>/` checks instead.
_REPO_ROOT_DIRS = ("rules", "tests", "tests_backlog", "examples", "research")

# Variable-built paths are skipped, not verified — docstring exemption 3, issue #3445.
_PORTABLE_PREFIXES = ("${CLAUDE_PLUGIN_ROOT}", "${CLAUDE_SKILL_DIR}", "$CLAUDE_PLUGIN_ROOT", "$CLAUDE_SKILL_DIR")

# Markdown link target, e.g. [text](./references/foo.md).
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

# A filesystem path into a sibling plugin.
_CROSS_PLUGIN_PATH_RE = re.compile(r"\bplugins/([a-z0-9][a-z0-9-]*)/[\w./-]+")

# A bare path into an authoring-repo directory, e.g. `scripts/foo.py` or rules/bar.md.
_REPO_PATH_RE = re.compile(rf"\b(?:{'|'.join(_REPO_ROOT_DIRS)})/[\w./-]+\.\w+")

# A <plugin>:<skill> activation reference. The plugin segment is captured so
# same-plugin references (dh:…) can be excluded.
_SKILL_REF_RE = re.compile(r"\b([a-z][a-z0-9-]{2,}):([a-z][a-z0-9-]{2,})\b")


# Words that, on the same line, suggest the cross-plugin reference is guarded rather
# than unconditional. A heuristic for triage, not a verdict.
_GUARD_WORDS = ("if ", "when ", "available", "installed", "optional", "present", "fallback", "unless")

# Leading `../` segments at which a relative link leaves the plugin. A reference inside
# skills/<name>/references/ needs three to climb past the plugin root.
_PLUGIN_ESCAPE_DEPTH = 3


def _is_placeholder(token: str) -> bool:
    """Return True when a token names a shape rather than a location.

    Angle brackets mark a generic example (``<plugin>/skills/<name>/SKILL.md``). Nothing
    resolves it, so nothing can break. An illustrative *real* path belongs in a fenced
    block instead, where it reads as an example rather than an instruction.

    Args:
        token: The matched path or reference text.

    Returns:
        True when the token contains an angle-bracket placeholder.
    """
    return "<" in token or ">" in token


@dataclass(frozen=True)
class Escape:
    """One reported escape from the plugin boundary.

    Attributes:
        path: Plugin-relative path of the runtime file.
        line_no: 1-based line number.
        kind: One of repo-path, cross-plugin-path, cross-plugin-skill, design-time-link.
        token: The offending text.
        line: The full source line, stripped.
        guarded: For cross-plugin-skill, whether a guard word appears on the line.
    """

    path: str
    line_no: int
    kind: str
    token: str
    line: str
    guarded: bool = False


def _is_design_time(path: Path) -> bool:
    """Return True when a file is a design-time artifact that never loads at runtime."""
    if path.name in _DESIGN_TIME_NAMES:
        return True
    return any(part in _DESIGN_TIME_DIRS for part in path.parts)


def _points_at_design_time(target: str) -> bool:
    """Return True when a link target names a design-time artifact."""
    tail = target.split("#", 1)[0]
    if Path(tail).name in _DESIGN_TIME_NAMES:
        return True
    return any(f"{d}/" in tail for d in _DESIGN_TIME_DIRS)


def _escapes_plugin(target: str) -> bool:
    """Return True when a relative link target climbs out of the plugin directory.

    Counts ``../`` segments against consumed segments; a target that rises above its
    own start has left the plugin only if it also rises above the plugin root, which
    cannot be known from the string alone. This reports any target with three or more
    leading ``../`` segments, the depth at which a skill reference leaves ``skills/``.
    """
    tail = target.split("#", 1)[0].strip()
    if not tail or tail.startswith(_PORTABLE_PREFIXES):
        return False
    leading = 0
    for segment in tail.split("/"):
        if segment == "..":
            leading += 1
        else:
            break
    return leading >= _PLUGIN_ESCAPE_DEPTH


def sibling_plugin_names(plugin_dir: Path) -> frozenset[str]:
    """Return the directory names of every plugin beside the scanned one.

    A ``word:word`` token is a cross-plugin skill reference only when its prefix names a
    real sibling plugin. Deriving that set from disk keeps label values (``state:verified``)
    and template placeholders (``plugin:skill-name``) out of the results without maintaining
    a denylist of things that merely look like references.

    Args:
        plugin_dir: The plugin being scanned.

    Returns:
        Sibling plugin directory names, excluding the scanned plugin itself.
    """
    plugins_root = plugin_dir.resolve().parent
    return frozenset(
        child.name for child in plugins_root.iterdir() if child.is_dir() and child.name != plugin_dir.resolve().name
    )


def _scan_line(
    rel_path: str, line_no: int, line: str, sibling_plugins: frozenset[str], own_plugin: str
) -> list[Escape]:
    """Collect every escape appearing on one line of runtime text.

    Args:
        rel_path: Plugin-relative path of the file being scanned.
        line_no: 1-based line number.
        line: The raw source line.
        sibling_plugins: Directory names of real sibling plugins.
        own_plugin: Directory name of the plugin being scanned; paths into it are internal.

    Returns:
        Every escape found on this line, in detection order.
    """
    found: list[Escape] = []
    stripped = line.strip()

    for target in _MD_LINK_RE.findall(line):
        if _is_placeholder(target):
            continue
        if _points_at_design_time(target):
            found.append(Escape(rel_path, line_no, "design-time-link", target, stripped))
        elif _escapes_plugin(target):
            found.append(Escape(rel_path, line_no, "repo-path", target, stripped))

    found.extend(
        Escape(rel_path, line_no, "cross-plugin-path", match.group(0), stripped)
        for match in _CROSS_PLUGIN_PATH_RE.finditer(line)
        if match.group(1) != own_plugin and not _is_placeholder(match.group(0))
    )

    for match in _REPO_PATH_RE.finditer(line):
        token = match.group(0)
        if token.startswith(_PORTABLE_PREFIXES) or _is_placeholder(token) or f"/{token}" in line:
            continue
        found.append(Escape(rel_path, line_no, "repo-path", token, stripped))

    guarded = any(word in line.lower() for word in _GUARD_WORDS)
    for match in _SKILL_REF_RE.finditer(line):
        if match.group(1) not in sibling_plugins:
            continue
        found.append(Escape(rel_path, line_no, "cross-plugin-skill", match.group(0), stripped, guarded))

    return found


def collect_escapes(plugin_dir: Path) -> list[Escape]:
    """Walk the plugin's runtime markdown and collect every escape.

    Args:
        plugin_dir: Path to the development-harness plugin directory.

    Returns:
        Every escape found, ordered by file then line.
    """
    escapes: list[Escape] = []
    sibling_plugins = sibling_plugin_names(plugin_dir)
    own_plugin = plugin_dir.resolve().name
    for root in _RUNTIME_ROOTS:
        for path in sorted((plugin_dir / root).rglob("*.md")):
            if _is_design_time(path):
                continue
            rel_path = str(path.relative_to(plugin_dir))
            text = path.read_text(encoding="utf-8", errors="replace")
            in_fence = False
            for line_no, line in enumerate(text.splitlines(), start=1):
                if line.lstrip().startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                escapes.extend(_scan_line(rel_path, line_no, line, sibling_plugins, own_plugin))
    return escapes


def render_report(escapes: list[Escape], plugin_dir: Path) -> str:
    """Render the markdown report body.

    Args:
        escapes: Every escape collected from the plugin's runtime files.
        plugin_dir: The scanned plugin directory, named in the report header.

    Returns:
        The full report as markdown.
    """
    by_kind = Counter(e.kind for e in escapes)
    by_file = Counter(e.path for e in escapes)
    unguarded_skills = [e for e in escapes if e.kind == "cross-plugin-skill" and not e.guarded]

    out: list[str] = [
        f"# {plugin_dir.name} runtime escapes",
        "",
        f"Generated: {datetime.now(UTC).date().isoformat()} by `audit_runtime_escapes.py`.",
        (
            f"Scanned: `{plugin_dir.name}/{{{','.join(_RUNTIME_ROOTS)}}}/**/*.md`, "
            "excluding design-time artifacts and fenced code blocks."
        ),
        "",
        "The plugin is distributed. Runtime text is read by an agent whose working directory is",
        "the consuming repo, which never has this repo's tree. Every entry below resolves in the",
        "authoring checkout and nowhere else.",
        "",
        "## Totals",
        "",
        "| Class | Count |",
        "|---|---|",
    ]
    out.extend(
        f"| `{kind}` | {by_kind.get(kind, 0)} |"
        for kind in ("repo-path", "cross-plugin-path", "cross-plugin-skill", "design-time-link")
    )
    out += [
        f"| **total** | **{len(escapes)}** |",
        "",
        (
            f"Files affected: {len(by_file)}. "
            f"Cross-plugin skill references with no guard word on the line: {len(unguarded_skills)}."
        ),
        "",
        "## Counts by file",
        "",
        "| File | Escapes |",
        "|---|---|",
    ]
    out += [f"| `{path}` | {count} |" for path, count in sorted(by_file.items(), key=lambda kv: (-kv[1], kv[0]))]

    out += ["", "## Detail", ""]
    current = ""
    for escape in escapes:
        if escape.path != current:
            current = escape.path
            out += ["", f"### `{current}`", ""]
        guard = "" if escape.kind != "cross-plugin-skill" else (" [guarded]" if escape.guarded else " [unguarded]")
        out.append(f"- **L{escape.line_no}** `{escape.kind}`{guard} — `{escape.token}`")
        out.append(f"  > {escape.line[:200]}")

    out += [
        "",
        "## Heuristics and limits",
        "",
        (
            "- `cross-plugin-skill` guard detection is a keyword scan of the same line "
            f"({', '.join(repr(w.strip()) for w in _GUARD_WORDS)}). It triages; it does not decide."
        ),
        "- Fenced code blocks are skipped, so illustrative paths inside examples are not counted.",
        "- A relative link is reported when it carries three or more leading `../` segments, the",
        "  depth at which a skill reference leaves `skills/`. Shallower climbs stay inside the plugin.",
        "- Same-plugin (`dh:`) references are never reported. Paths built on `${CLAUDE_PLUGIN_ROOT}` or",
        "  `${CLAUDE_SKILL_DIR}` are skipped, not verified (exemption 3, issue #3445).",
        "",
    ]
    return "\n".join(out)


def render_sweep(counts: dict[str, int]) -> str:
    """Render the cross-plugin summary table.

    Args:
        counts: Plugin directory name to escape count.

    Returns:
        The sweep summary as markdown.
    """
    total = sum(counts.values())
    clean = [name for name, count in counts.items() if count == 0]
    out = [
        "# Runtime escapes across all plugins",
        "",
        f"Generated: {datetime.now(UTC).date().isoformat()} by `audit_runtime_escapes.py --all`.",
        "",
        "| Plugin | Escapes |",
        "|---|---|",
    ]
    out += [f"| `{name}` | {count} |" for name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    out += [
        f"| **total** | **{total}** |",
        "",
        f"Clean plugins ({len(clean)} of {len(counts)}): "
        + (", ".join(f"`{name}`" for name in sorted(clean)) if clean else "none"),
        "",
    ]
    return "\n".join(out)


def main() -> int:
    """Scan one plugin or every plugin and report escapes.

    Returns:
        0 when no escapes are found, 1 when any are, 2 when the requested directory is missing.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plugin-dir", type=Path, default=None, help="Plugin directory to scan")
    parser.add_argument(
        "--all", action="store_true", help="Sweep every plugin under plugins/ and report a count per plugin"
    )
    parser.add_argument("--out", type=Path, default=None, help="Write the markdown report to this path")
    args = parser.parse_args()

    if args.all:
        plugins_root = Path("plugins")
        if not plugins_root.is_dir():
            print(f"error: plugins directory not found: {plugins_root}", file=sys.stderr)
            return 2
        counts = {
            child.name: len(collect_escapes(child))
            for child in sorted(plugins_root.iterdir())
            if child.is_dir() and any((child / root).is_dir() for root in _RUNTIME_ROOTS)
        }
        report = render_sweep(counts)
        total = sum(counts.values())
    else:
        plugin_dir: Path = args.plugin_dir or Path("plugins/development-harness")
        if not plugin_dir.is_dir():
            print(f"error: plugin directory not found: {plugin_dir}", file=sys.stderr)
            return 2
        escapes = collect_escapes(plugin_dir)
        report = render_report(escapes, plugin_dir)
        total = len(escapes)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(f"wrote {args.out} ({total} escapes)")
    else:
        print(report)

    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
