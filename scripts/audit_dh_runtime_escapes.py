#!/usr/bin/env python3
"""Report runtime text in development-harness that will not resolve for an installed consumer.

The plugin is distributed. Its runtime text is read by an agent whose working directory is the
consuming repo, which never has this repo's tree. A path into that tree resolves here and
nowhere else.

Runtime text is what loads with the artifact: ``SKILL.md`` bodies, agent bodies, and
``references/**``. Design-time siblings that travel inside the package but do not load
(``SKILL-GOALS.md``, ``MAINTENANCE.md``, ``BENCHMARKS.md``, ``maintenance/**``, ``evals/**``)
are excluded from scanning, and a runtime link pointing *at* one of them is itself reported.

Four escape classes are reported:

* ``repo-path`` — a path into the authoring repo's tree (``scripts/…``, ``rules/…``,
  ``tests/…``, ``docs/…``) that an installed consumer does not have.
* ``cross-plugin-path`` — a filesystem path into a sibling plugin (``plugins/<other>/…``).
* ``cross-plugin-skill`` — a ``<plugin>:<skill>`` activation reference to another plugin.
  Reported with a heuristic guard flag; see ``_GUARD_WORDS``.
* ``design-time-link`` — a runtime link into a design-time artifact that never loads.

``${CLAUDE_PLUGIN_ROOT}`` and ``${CLAUDE_SKILL_DIR}`` substitute at load time, so paths built
on them resolve in any environment and are not reported.

Exit codes:
    0: no escapes found (the state at which this becomes a drift test)
    1: escapes found
    2: the plugin directory does not exist
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

# Repo-root directories that exist only in the authoring checkout.
_REPO_ROOT_DIRS = ("scripts", "rules", "tests", "tests_backlog", "docs", "examples", "research")

# Load-time substitutions resolve anywhere, so a path built on one is portable.
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


def _scan_line(rel_path: str, line_no: int, line: str, sibling_plugins: frozenset[str]) -> list[Escape]:
    """Collect every escape appearing on one line of runtime text.

    Args:
        rel_path: Plugin-relative path of the file being scanned.
        line_no: 1-based line number.
        line: The raw source line.
        sibling_plugins: Directory names of real sibling plugins.

    Returns:
        Every escape found on this line, in detection order.
    """
    found: list[Escape] = []
    stripped = line.strip()

    for target in _MD_LINK_RE.findall(line):
        if _points_at_design_time(target):
            found.append(Escape(rel_path, line_no, "design-time-link", target, stripped))
        elif _escapes_plugin(target):
            found.append(Escape(rel_path, line_no, "repo-path", target, stripped))

    found.extend(
        Escape(rel_path, line_no, "cross-plugin-path", match.group(0), stripped)
        for match in _CROSS_PLUGIN_PATH_RE.finditer(line)
        if match.group(1) != "development-harness"
    )

    for match in _REPO_PATH_RE.finditer(line):
        token = match.group(0)
        if token.startswith(_PORTABLE_PREFIXES) or f"/{token}" in line:
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
                escapes.extend(_scan_line(rel_path, line_no, line, sibling_plugins))
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
        "# development-harness runtime escapes",
        "",
        f"Generated: {datetime.now(UTC).date().isoformat()} by `scripts/audit_dh_runtime_escapes.py`.",
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
        "- Same-plugin (`dh:`) references and `${CLAUDE_PLUGIN_ROOT}`-rooted paths are portable and",
        "  are never reported.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    """Scan the plugin and write the escape report.

    Returns:
        0 when no escapes are found, 1 when any are, 2 when the plugin directory is missing.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--plugin-dir",
        type=Path,
        default=Path("plugins/development-harness"),
        help="Plugin directory to scan (default: plugins/development-harness)",
    )
    parser.add_argument("--out", type=Path, default=None, help="Write the markdown report to this path")
    args = parser.parse_args()

    plugin_dir: Path = args.plugin_dir
    if not plugin_dir.is_dir():
        print(f"error: plugin directory not found: {plugin_dir}", file=sys.stderr)
        return 2

    escapes = collect_escapes(plugin_dir)
    report = render_report(escapes, plugin_dir)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(f"wrote {args.out} ({len(escapes)} escapes)")
    else:
        print(report)

    return 1 if escapes else 0


if __name__ == "__main__":
    sys.exit(main())
