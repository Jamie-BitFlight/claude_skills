#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.12.5"]
# ///
"""Classify every declared dependency by the evidence that it is still required.

A module dependency is proved by an import. A tool dependency is proved by an
invocation plus its resolution path. The two need different evidence, so this
script collects both and reports one verdict per declared dependency.

Resolution paths that do NOT consume the project environment, and therefore do
not justify a declaration: `uv run --script` (and plain `uv run file.py` when the
file carries PEP 723 inline metadata), `uv run --with <tool>`, `uvx <tool>`, and
a prek hook that pins its own `repo:`/`rev:`.

Emits compact JSON on stdout. Exits 1 when any dependency lacks evidence.
"""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
import sys
import tomllib
from collections import defaultdict
from importlib.metadata import distributions
from pathlib import Path

from pydantic import BaseModel, Field

SKIP_DIRS = frozenset({
    ".venv",
    "node_modules",
    ".git",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".mypy_cache",
})
TEXT_GLOBS = ("*.md", "*.yml", "*.yaml", "*.toml", "*.json")
NAME_RE = re.compile(r"^([A-Za-z0-9._-]+)")
PEP723_RE = re.compile(r"^# /// script\s*$(.*?)^# ///\s*$", re.MULTILINE | re.DOTALL)
GENERIC_DIRS = frozenset({"tests", "test", "bin", "share", "include", "lib", "etc", "licenses", "data"})


class Dependency(BaseModel):
    """One declared dependency and the evidence gathered for it."""

    name: str
    groups: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    binaries: list[str] = Field(default_factory=list)
    plugin_groups: list[str] = Field(default_factory=list)
    import_sites: list[str] = Field(default_factory=list)
    pep723_sites: list[str] = Field(default_factory=list)
    project_env_invocations: list[str] = Field(default_factory=list)
    with_invocations: int = 0
    required_by: list[str] = Field(default_factory=list)
    verdict: str = "UNUSED"
    reason: str = ""


class Report(BaseModel):
    """The full audit result."""

    pyproject: str
    dependencies: list[Dependency]
    unresolved: list[str] = Field(default_factory=list)


def requirement_name(spec: str) -> str | None:
    """Extract the canonical distribution name from a requirement specifier.

    Args:
        spec: A PEP 508 requirement such as `httpx[cli]>=0.28.1`.

    Returns:
        The canonical name, or None when the specifier has no leading name.
    """
    match = NAME_RE.match(spec)
    return canonical(match.group(1)) if match else None


def canonical(name: str) -> str:
    """Return the PEP 503 canonical form of a distribution name.

    Args:
        name: A distribution name, possibly with extras or underscores.

    Returns:
        The lowercase, hyphen-normalised name.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def declared_dependencies(pyproject: Path) -> dict[str, list[str]]:
    """Read every declared dependency and the groups that declare it.

    Args:
        pyproject: Path to the `pyproject.toml` file.

    Returns:
        A mapping of canonical distribution name to the groups declaring it.
    """
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    found: dict[str, list[str]] = defaultdict(list)
    for spec in data.get("project", {}).get("dependencies", []):
        if name := requirement_name(spec):
            found[name].append("project")
    for group, specs in (data.get("dependency-groups") or {}).items():
        for spec in specs:
            if isinstance(spec, str) and (name := requirement_name(spec)):
                found[name].append(group)
    return dict(found)


def site_packages(root: Path) -> list[str]:
    """Locate the project virtual environment's site-packages directories.

    Args:
        root: Repository root holding the `.venv` directory.

    Returns:
        Search paths for `importlib.metadata`, empty when no `.venv` exists.

    Raises:
        SystemExit: When `.venv` exists but holds no site-packages directory.
    """
    venv = root / ".venv"
    if not venv.is_dir():
        return []
    found = sorted(
        {str(p) for p in venv.glob("lib/python*/site-packages")} | {str(p) for p in venv.glob("Lib/site-packages")}
    )
    if not found:
        raise SystemExit(f"no site-packages directory under {venv}; run `uv sync` first")
    return found


def installed_metadata(search_path: list[str]) -> dict[str, dict[str, list[str]]]:
    """Map each installed distribution to its modules, binaries and plugin groups.

    Args:
        search_path: Site-packages directories to inspect, or empty for the running interpreter.

    Returns:
        A mapping of canonical name to `modules`, `binaries` and `plugin_groups`.
    """
    meta: dict[str, dict[str, list[str]]] = {}
    for dist in distributions(path=search_path) if search_path else distributions():
        name = canonical(dist.metadata["Name"] or "")
        if not name:
            continue
        entry = meta.setdefault(name, {"modules": [], "binaries": [], "plugin_groups": [], "requires": []})
        modules: set[str] = set()
        binaries: set[str] = set()
        for file in dist.files or []:
            parts = file.parts
            if not parts or parts[0].endswith(".dist-info"):
                continue
            if "bin" in parts:
                binaries.add(file.name)
            elif parts[0].endswith(".py"):
                modules.add(parts[0][:-3])
            elif len(parts) > 1 and "." not in parts[0] and parts[0] not in GENERIC_DIRS:
                modules.add(parts[0])
        entry["modules"] = sorted(modules)
        entry["binaries"] = sorted(binaries)
        entry["plugin_groups"] = sorted({
            ep.group for ep in dist.entry_points if ep.group not in {"console_scripts", "gui_scripts"}
        })
        entry["requires"] = sorted({name for req in dist.requires or [] if (name := requirement_name(req)) is not None})
    return resolve_meta_packages(meta)


def resolve_meta_packages(meta: dict[str, dict[str, list[str]]]) -> dict[str, dict[str, list[str]]]:
    """Give a distribution that ships no code the modules of what it requires.

    A meta-package such as `fastmcp` ships only metadata; the importable module
    arrives from a requirement such as `fastmcp-slim`. Without this step the audit
    reports the meta-package as unused while its module is imported everywhere.

    Args:
        meta: The raw metadata map, each entry carrying a `requires` list.

    Returns:
        The same map, with an empty `modules` list filled in from direct requirements.
    """
    for entry in meta.values():
        if entry["modules"] or entry["binaries"]:
            continue
        inherited: set[str] = set()
        for requirement in entry.get("requires", []):
            inherited |= set(meta.get(requirement, {}).get("modules", []))
        entry["modules"] = sorted(inherited)
    return meta


def inline_dependencies(source: str) -> set[str]:
    """Read the dependency names from a file's PEP 723 inline metadata block.

    Args:
        source: The full text of a Python file.

    Returns:
        Canonical distribution names, empty when the file has no valid block.
    """
    block = PEP723_RE.search(source)
    if not block:
        return set()
    stripped = "\n".join(line.lstrip("#").strip() for line in block.group(1).splitlines())
    try:
        specs = tomllib.loads(stripped).get("dependencies", []) or []
    except tomllib.TOMLDecodeError:
        return set()
    return {name for spec in specs if (name := requirement_name(spec)) is not None}


def scan_python(root: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Separate real imports from dependencies declared in PEP 723 inline metadata.

    Args:
        root: Repository root to walk.

    Returns:
        A tuple of `(module -> importing files, distribution -> inline-metadata files)`.
    """
    imports: dict[str, set[str]] = defaultdict(set)
    inline: dict[str, set[str]] = defaultdict(set)
    for path in root.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(root))
        for name in inline_dependencies(source):
            inline[name].add(rel)
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.name.split(".")[0]].add(rel)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imports[node.module.split(".")[0]].add(rel)
    return imports, inline


def grep(root: Path, pattern: str) -> list[str]:
    """Search the text surfaces of the repository for a pattern.

    Args:
        root: Repository root to search.
        pattern: An extended regular expression.

    Returns:
        Repository-relative paths of the matching lines, one entry per match.
    """
    command = [shutil.which("grep") or "/usr/bin/grep", "-rlE", pattern, "--binary-files=without-match"]
    for directory in SKIP_DIRS:
        command += ["--exclude-dir", directory]
    for glob in TEXT_GLOBS:
        command += ["--include", glob]
    command += ["--exclude", "uv.lock", str(root)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return [line.replace(f"{root}/", "") for line in result.stdout.splitlines() if line.strip()]


def reverse_requirements(root: Path, name: str) -> list[str]:
    """Report which installed distributions require the named distribution.

    Args:
        root: Repository root, used as the working directory for `uv`.
        name: Canonical distribution name.

    Returns:
        Names of the distributions that depend on it, excluding the project itself.
    """
    result = subprocess.run(
        [shutil.which("uv") or "uv", "tree", "--invert", "--package", name, "--all-groups", "--depth", "1"],
        capture_output=True,
        text=True,
        cwd=root,
        check=False,
    )
    lines = [line.strip() for line in result.stdout.splitlines()[1:] if line.strip()]
    return [re.sub(r"^[└├─│\s]+", "", line).split(" v")[0] for line in lines[1:]]


def classify(dep: Dependency, project_groups: list[str]) -> None:
    """Assign a verdict to one dependency from the evidence already gathered.

    Args:
        dep: The dependency to classify, with its evidence fields populated.
        project_groups: Every group that declares it.
    """
    if len(set(project_groups)) > 1 and "project" in project_groups:
        dep.verdict = "DUPLICATE"
        dep.reason = "declared in project.dependencies and in a dependency group"
    elif dep.import_sites:
        dep.verdict = "DIRECT_IMPORT"
        dep.reason = f"imported by {len(dep.import_sites)} project-environment file(s)"
    elif dep.plugin_groups and not dep.binaries:
        dep.verdict = "PLUGIN"
        dep.reason = f"discovered through entry-point group(s): {', '.join(dep.plugin_groups)}"
    elif dep.project_env_invocations:
        dep.verdict = "TOOL"
        dep.reason = f"invoked from the project environment in {len(dep.project_env_invocations)} file(s)"
    elif dep.with_invocations:
        dep.verdict = "WITH_SUPPLIED"
        dep.reason = "only reached through `uv run --with` or `uvx`, which supply it independently"
    elif dep.pep723_sites:
        dep.verdict = "PEP723_ONLY"
        dep.reason = (
            f"declared inline by {len(dep.pep723_sites)} PEP 723 script(s); the runtime resolves it "
            "in an isolated environment, but `ty check` resolves the same imports against the project "
            "environment, so the declaration stays required"
        )
    elif dep.required_by:
        dep.verdict = "TRANSITIVE_ONLY"
        dep.reason = f"never imported; required by {', '.join(dep.required_by)}"
    else:
        dep.verdict = "UNUSED"
        dep.reason = "no import, invocation, plugin group or reverse requirement found"


def audit(root: Path) -> Report:
    """Run the full audit over a repository.

    Args:
        root: Repository root holding `pyproject.toml`.

    Returns:
        The populated report.
    """
    pyproject = root / "pyproject.toml"
    declared = declared_dependencies(pyproject)
    meta = installed_metadata(site_packages(root))
    imports, inline = scan_python(root)

    unresolved: list[str] = []
    results: list[Dependency] = []
    for name, groups in sorted(declared.items()):
        info = meta.get(name)
        if info is None:
            unresolved.append(name)
            info = {"modules": [], "binaries": [], "plugin_groups": [], "requires": []}
        dep = Dependency(
            name=name,
            groups=sorted(set(groups)),
            modules=info["modules"],
            binaries=info["binaries"],
            plugin_groups=info["plugin_groups"],
        )
        pep723 = inline.get(name, set())
        sites: set[str] = set()
        for module in info["modules"]:
            sites |= imports.get(module, set())
        dep.pep723_sites = sorted(pep723)
        dep.import_sites = sorted(sites - pep723)

        if info["binaries"]:
            tokens = "|".join(sorted(re.escape(t) for t in set(info["binaries"]) | {name}))
            direct = grep(root, rf"uv run [^|;&]*\b({tokens})\b")
            supplied = set(grep(root, rf"(--with[= ]|uvx )[^|;&]*\b({tokens})\b"))
            dep.project_env_invocations = sorted(set(direct) - supplied)
            dep.with_invocations = len(supplied)
        if not dep.import_sites and not dep.project_env_invocations:
            dep.required_by = reverse_requirements(root, name)
        classify(dep, groups)
        results.append(dep)
    return Report(pyproject=str(pyproject), dependencies=results, unresolved=unresolved)


def main() -> int:
    """Parse arguments, run the audit and print the report.

    Returns:
        1 when any dependency has no evidence of use, otherwise 0.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    report = audit(args.root.resolve())
    print(report.model_dump_json())
    unproven = {"UNUSED", "DUPLICATE", "WITH_SUPPLIED"}
    return 1 if any(dep.verdict in unproven for dep in report.dependencies) else 0


if __name__ == "__main__":
    sys.exit(main())
