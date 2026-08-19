#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "httpx>=0.28.1",
#     "ruamel.yaml>=0.18.0",
# ]
# ///
"""Mirror the astral-sh {uv,ruff,ty} `docs/` trees into local reference archives.

Downloads the repo's `main` branch zip from GitHub, extracts only the `docs/`
subtree, grooms each markdown file (strips frontmatter into a title/
description pair, flattens pymdownx admonitions and tabs into plain
markdown), and atomically replaces `references/<tool>/docs/`. Regenerates
the "## Documentation Index" section in `references/<tool>/README.md`.

This is the corpus sync: it produces the actual reference content agents
read offline. It is distinct from `sync_uv_releases.py`, which only
maintains a changelog stub.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import UTC, datetime, timedelta
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated

if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError

console = Console()
error_console = Console(stderr=True, style="bold red")

TOOL_REPOS = {"uv": "astral-sh/uv", "ruff": "astral-sh/ruff", "ty": "astral-sh/ty"}

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE)
ADMONITION_START = re.compile(r'^(!!!|\?\?\?\+?)\s+(\S+)(?:\s+"([^"]*)")?\s*$')
TAB_START = re.compile(r'^===\s+"([^"]*)"\s*$')
INDEX_SECTION_PATTERN = re.compile(r"(^## Documentation Index\s*\n)(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)


class UpdateError(Exception):
    """Base exception for corpus sync errors."""


class DownloadError(UpdateError):
    """Exception raised when the repo archive download fails."""


class ValidationError(UpdateError):
    """Exception raised when the extracted docs/ tree is invalid."""


def check_cooldown(working_dir: Path, tool: str, force: bool) -> bool:
    """Check whether the per-tool sync cooldown has elapsed.

    Returns:
        True if the sync should proceed, False if still in cooldown.
    """
    if force:
        return True

    lock_file = working_dir / f".sync-astral-docs-{tool}.lock"
    if not lock_file.exists():
        return True

    try:
        lock_data = json.loads(lock_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        msg = f"Failed to read lock file {lock_file}: {e}"
        raise UpdateError(msg) from e

    if lock_data.get("last_status") != "success":
        return True

    try:
        last_run = datetime.fromisoformat(lock_data["last_run"])
    except (KeyError, ValueError) as e:
        msg = f"Invalid timestamp in lock file: {e}"
        raise UpdateError(msg) from e

    cooldown_period = timedelta(days=3)
    time_since = datetime.now(UTC) - last_run
    if time_since < cooldown_period:
        remaining = cooldown_period - time_since
        hours = int(remaining.total_seconds() // 3600)
        console.print(
            Panel(
                f":clock3: Last successful sync: {last_run.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f":hourglass: ~{hours}h remaining\n"
                f":rocket: To force now: --force",
                title=f"[{tool}] Cooldown Active",
                border_style="yellow",
            )
        )
        return False

    return True


def update_lock_file(working_dir: Path, tool: str, status: str) -> None:
    """Record this run's timestamp and outcome for the next cooldown check."""
    lock_file = working_dir / f".sync-astral-docs-{tool}.lock"
    temp_lock_file = working_dir / f".sync-astral-docs-{tool}.lock.tmp"
    lock_data = {"last_run": datetime.now(UTC).isoformat(), "last_status": status}
    try:
        temp_lock_file.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")
        temp_lock_file.rename(lock_file)
    except OSError as e:
        msg = f"Failed to write lock file {lock_file}: {e}"
        raise UpdateError(msg) from e


def download_zip(repo: str, output_path: Path) -> None:
    """Download the repo's main-branch zip archive."""
    url = f"https://github.com/{repo}/archive/refs/heads/main.zip"
    try:
        with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as response:
            response.raise_for_status()
            with output_path.open("wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
    except httpx.HTTPStatusError as e:
        msg = f"HTTP {e.response.status_code} downloading {url}"
        raise DownloadError(msg) from e
    except httpx.RequestError as e:
        msg = f"Network error downloading {url}: {e}"
        raise DownloadError(msg) from e


def extract_docs(zip_path: Path, extract_to: Path) -> Path:
    """Extract only the markdown files under docs/ from a repo's main-branch zip.

    Returns:
        extract_to, for chaining.
    """
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if not names:
            msg = f"Empty archive: {zip_path}"
            raise ValidationError(msg)
        root_prefix = names[0].split("/")[0] + "/docs/"
        doc_members = [n for n in names if n.startswith(root_prefix) and n.endswith(".md")]
        if not doc_members:
            msg = f"No docs/ subtree found in {zip_path} (root prefix {root_prefix})"
            raise ValidationError(msg)
        for member in doc_members:
            rel = member[len(root_prefix) :]
            dest = extract_to / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, dest.open("wb") as out:
                out.write(src.read())

    md_files = list(extract_to.rglob("*.md"))
    if not md_files:
        msg = f"No markdown files found under extracted docs/ at {extract_to}"
        raise ValidationError(msg)
    return extract_to


def dedent_block(lines: list[str], indent: int) -> list[str]:
    """Strip a fixed number of leading columns from every line.

    Returns:
        The dedented lines.
    """
    return [line[indent:] if len(line) >= indent else "" for line in lines]


def consume_indented_block(lines: list[str], start: int) -> tuple[list[str], int]:
    """Consume the indented block following a `!!!`/`???`/`===` marker line.

    Returns:
        The dedented block lines, and the index of the first line after the block.
    """
    i = start
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return [], i
    first = lines[i]
    indent = len(first) - len(first.lstrip())
    if indent == 0:
        return [], i

    block: list[str] = []
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and (len(lines[j]) - len(lines[j].lstrip())) >= indent:
                block.append("")
                i += 1
                continue
            break
        if (len(line) - len(line.lstrip())) >= indent:
            block.append(line)
            i += 1
        else:
            break

    return dedent_block(block, indent), i


def groom_admonitions_and_tabs(content: str) -> str:
    """Flatten pymdownx admonition (`!!!`/`???`) and tab (`=== "x"`) blocks into plain markdown.

    Returns:
        The content with every admonition/tab block replaced by plain markdown.
    """
    lines = content.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        adm = ADMONITION_START.match(line)
        tab = TAB_START.match(line)
        if adm:
            kind, title = adm.group(2), adm.group(3)
            label = title or kind.capitalize()
            block, i = consume_indented_block(lines, i + 1)
            block = groom_admonitions_and_tabs("\n".join(block)).split("\n")
            out.extend((f"> **{label}:**", ">"))
            out.extend(f"> {b}" if b.strip() else ">" for b in block)
            out.append("")
        elif tab:
            title = tab.group(1)
            block, i = consume_indented_block(lines, i + 1)
            block = groom_admonitions_and_tabs("\n".join(block)).split("\n")
            out.extend((f"**{title}**", ""))
            out.extend(block)
            out.append("")
        else:
            out.append(line)
            i += 1
    return "\n".join(out)


def extract_frontmatter(content: str) -> tuple[str | None, str | None, str]:
    """Pull title/description out of YAML frontmatter.

    Returns:
        (title, description, body-without-frontmatter).
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return None, None, content

    body = content[match.end() :]
    try:
        yaml = YAML(typ="safe")
        data = yaml.load(match.group(1))
    except ScannerError:
        return None, None, body

    if not isinstance(data, dict):
        return None, None, body

    title = str(data["title"]).strip() if "title" in data else None
    description = str(data["description"]).strip() if "description" in data else None
    if description:
        description = " ".join(description.split())
    return title, description, body


H1_PATTERN = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def groom_markdown_file(content: str) -> tuple[str | None, str | None, str]:
    """Groom one raw markdown file, falling back to the first H1 for a title.

    Returns:
        (title, description, groomed body).
    """
    title, description, body = extract_frontmatter(content)
    body = groom_admonitions_and_tabs(body)
    if not title:
        h1 = H1_PATTERN.search(body)
        if h1:
            title = h1.group(1).strip()
    return title, description, body.strip() + "\n"


def generate_index(entries: list[tuple[str, str | None, str | None]]) -> str:
    """Build a "## Documentation Index"-style bullet list grouped by top-level directory.

    Returns:
        The rendered markdown bullet list.
    """
    by_dir: dict[str, list[tuple[str, str | None, str | None]]] = {}
    for relpath, title, description in sorted(entries):
        top = relpath.split("/")[0] if "/" in relpath else "."
        by_dir.setdefault(top, []).append((relpath, title, description))

    lines: list[str] = []
    for top in sorted(by_dir):
        if top != ".":
            lines.append(f"- **{top}/**")
        for relpath, title, description in by_dir[top]:
            label = title or Path(relpath).stem
            indent = "  " if top != "." else ""
            entry = f"{indent}- [{label}](./docs/{relpath})"
            if description:
                entry += f" — {description}"
            lines.append(entry)
    return "\n".join(lines) + "\n"


def update_readme_index(readme_path: Path, index_md: str) -> None:
    """Replace the archive README's Documentation Index section and generated_at stamp."""
    content = readme_path.read_text(encoding="utf-8")
    section = f"## Documentation Index\n\n{index_md}\n"

    if INDEX_SECTION_PATTERN.search(content):
        content = INDEX_SECTION_PATTERN.sub(section, content)
    else:
        content = content.rstrip() + f"\n\n{section}"

    content = re.sub(r"generated_at:.*", f"generated_at: {datetime.now(UTC).date().isoformat()}", content)
    readme_path.write_text(content, encoding="utf-8")


def atomic_replace(source: Path, target: Path) -> None:
    """Replace target with source, removing whatever target held before."""
    if target.exists():
        shutil.rmtree(target)
    source.rename(target)


def process_tool(tool: str, working_dir: Path, force: bool, no_cleanup: bool) -> int:
    """Sync one tool's docs/ corpus end to end.

    Returns:
        The number of files synced (0 if skipped by cooldown).
    """
    repo = TOOL_REPOS[tool]
    tool_dir = working_dir / "references" / tool
    if not tool_dir.exists():
        msg = f"{tool_dir} does not exist — create references/{tool}/README.md before running the sync"
        raise UpdateError(msg)

    if not check_cooldown(working_dir, tool, force):
        return 0

    tmp_root = Path(tempfile.mkdtemp(prefix=f"astral-docs-{tool}-"))
    zip_path = tmp_root / "repo.zip"
    docs_new = tmp_root / "docs-new"
    docs_new.mkdir()

    try:
        console.print(Panel(f"Downloading {repo}@main", title=f"[{tool}] Download", border_style="blue"))
        download_zip(repo, zip_path)

        console.print(Panel("Extracting docs/ subtree", title=f"[{tool}] Extract", border_style="blue"))
        extract_docs(zip_path, docs_new)

        console.print(Panel("Grooming markdown files", title=f"[{tool}] Groom", border_style="blue"))
        entries: list[tuple[str, str | None, str | None]] = []
        md_files = sorted(docs_new.rglob("*.md"))
        for md_file in md_files:
            relpath = md_file.relative_to(docs_new).as_posix()
            content = md_file.read_text(encoding="utf-8")
            title, description, groomed = groom_markdown_file(content)
            md_file.write_text(groomed, encoding="utf-8")
            entries.append((relpath, title, description))
        console.print(f"[{tool}] Groomed {len(entries)} files")

        console.print(Panel("Updating documentation index", title=f"[{tool}] Index", border_style="blue"))
        index_md = generate_index(entries)
        update_readme_index(tool_dir / "README.md", index_md)

        console.print(Panel(f"Replacing {tool_dir / 'docs'}", title=f"[{tool}] Replace", border_style="blue"))
        atomic_replace(docs_new, tool_dir / "docs")

        console.print(
            Panel(
                f":white_check_mark: Synced {len(entries)} files for {tool}\nSource: {repo}@main",
                title=f"[{tool}] Success",
                border_style="green",
            )
        )
        update_lock_file(working_dir, tool, status="success")
        return len(entries)
    except UpdateError:
        update_lock_file(working_dir, tool, status="failure")
        raise
    except Exception as e:
        update_lock_file(working_dir, tool, status="failure")
        msg = f"Unexpected error syncing {tool}: {e}"
        raise UpdateError(msg) from e
    finally:
        if not no_cleanup and tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=True)


def main(
    tools: Annotated[
        list[str] | None, typer.Argument(help="Which tools to sync (default: all of uv, ruff, ty)")
    ] = None,
    working_dir: Annotated[
        Path | None,
        typer.Option("--working-dir", "-w", help="python3-tools skill directory (default: script's parent's parent)"),
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Bypass the 3-day per-tool cooldown")] = False,
    no_cleanup: Annotated[bool, typer.Option("--no-cleanup", help="Keep temp download/extract dirs")] = False,
) -> None:
    """Mirror astral-sh docs/ trees into references/<tool>/docs/."""
    resolved_dir = working_dir if working_dir is not None else Path(__file__).resolve().parent.parent
    selected = tools or list(TOOL_REPOS)

    unknown = [t for t in selected if t not in TOOL_REPOS]
    if unknown:
        error_console.print(f"Unknown tool(s): {unknown}. Choose from {list(TOOL_REPOS)}.")
        raise typer.Exit(code=1)

    failures = []
    for tool in selected:
        try:
            process_tool(tool, resolved_dir, force, no_cleanup)
        except UpdateError as e:
            error_console.print(Panel(f":cross_mark: {e}", title=f"[{tool}] Sync Failed", border_style="red"))
            failures.append(tool)

    if failures:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    typer.run(main)
