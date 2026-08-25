"""Pure detection functions for MCP call-shape drift in shipped markdown (#3162).

Shipped agent and skill markdown instructs MCP calls in prose. A wrong tool name or a
wrong enum literal reads as correct to an author and a reviewer because the surrounding
tool is real; only calling it reveals the shape. These functions resolve every instructed
name against the servers' live tool listing and against the real ``ArtifactType`` /
``ArtifactStatus`` members, so drift fails a test instead of failing at dispatch time.

Detection is deliberately narrow. A general keyword-argument parser was built, measured
against the whole shipped corpus, and rejected: it reached only 78.5% of call sites and
produced a 34.7% false-positive rate. These three checks target names with a closed,
mechanically resolvable value domain, which is why they carry no false positives.

The functions are pure ``(text) -> list[Defect]`` so the same code path runs against the
real corpus and against injected mutations under ``tmp_path``.
"""

from __future__ import annotations

import asyncio
import re
import shlex
from typing import TYPE_CHECKING, Final, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = [
    "Defect",
    "DefectKind",
    "ToolSurface",
    "find_artifact_enum_defects",
    "find_tool_call_defects",
    "find_tool_grant_defects",
    "load_tool_surface",
]

# Server key used in the ``mcp__plugin_dh_<server>__<tool>`` grant token.
_BACKLOG_SERVER: Final = "backlog"
_SAM_SERVER: Final = "sam"

# Which guard produced a defect. Closed set — a new value means a new guard, not a new string.
DefectKind: TypeAlias = Literal["tool_grant", "tool_call", "artifact_enum"]

_GRANT_RE: Final = re.compile(r"mcp__plugin_dh_(backlog|sam)__([A-Za-z0-9_]+)")

# An instructed call: an optionally server-prefixed tool name followed by "(".
# The prefix alternative must be tried first — a word-boundary anchor cannot match
# after the "_" that ends the prefix, which silently skipped every prefixed site in
# an earlier probe of this same corpus.
#
# The lookbehind also excludes a preceding "." — an MCP tool is always invoked as a bare
# name, so an attribute call such as ``dh_paths.backlog_dir()`` is Python, not an
# instructed tool call.
_NOT_AN_IDENTIFIER_TAIL: Final = r"(?<![A-Za-z0-9_.])"

_CALL_RE: Final = re.compile(
    _NOT_AN_IDENTIFIER_TAIL + r"(?:mcp__plugin_dh_(?:backlog|sam)__)?"
    r"((?:sam|artifact|backlog|dispatch|profile)_[A-Za-z0-9_]+)\s*\("
)

_ARTIFACT_CALL_RE: Final = re.compile(
    _NOT_AN_IDENTIFIER_TAIL + r"(?:mcp__plugin_dh_backlog__)?(artifact_[A-Za-z0-9_]+)\s*\("
)

_ARTIFACT_TYPE_KWARG_RE: Final = re.compile(r"""artifact_type\s*=\s*["']([^"']*)["']""")
_STATUS_KWARG_RE: Final = re.compile(r"""status\s*=\s*["']([^"']*)["']""")
# Characters that mark a literal as an authoring placeholder rather than a real value.
_PLACEHOLDER_CHARS: Final = frozenset("{}<>$|")

# How far past a call opener to keep scanning for its arguments when the parentheses
# never balance — prose call sites are routinely truncated or wrapped mid-argument.
_MAX_CALL_SPAN: Final = 600


class ToolSurface(BaseModel):
    """The tool names each dh MCP server actually exposes at runtime."""

    model_config = ConfigDict(frozen=True)

    backlog: frozenset[str] = Field(description="Tool names exposed by the backlog server.")
    sam: frozenset[str] = Field(description="Tool names exposed by the SAM server.")

    @property
    def all_names(self) -> frozenset[str]:
        """Every tool name exposed by either server."""
        return self.backlog | self.sam

    def server_for(self, server_key: str) -> frozenset[str]:
        """Return the tool names for a ``mcp__plugin_dh_<server_key>__`` prefix.

        Args:
            server_key: The server segment of a grant token — ``backlog`` or ``sam``.

        Returns:
            The tool names that server exposes.

        Raises:
            KeyError: ``server_key`` names no dh server. Resolving an unrecognised prefix to
                a default listing would let a whole prefix go unchecked without saying so.
        """
        return {_BACKLOG_SERVER: self.backlog, _SAM_SERVER: self.sam}[server_key]


class Defect(BaseModel):
    """One instructed call shape that does not exist at runtime."""

    model_config = ConfigDict(frozen=True)

    kind: DefectKind = Field(description="Which guard produced this defect.")
    found: str = Field(description="The literal name or value as written in the markdown.")
    detail: str = Field(description="Why it is wrong, naming the values that would be accepted.")

    def __str__(self) -> str:
        """Render as a single line for a pytest assertion message."""
        return f"[{self.kind}] {self.found}: {self.detail}"


def load_tool_surface() -> ToolSurface:
    """Read the live tool listing from both dh MCP servers.

    Importing the server modules registers their tools; ``list_tools`` reports what a
    calling agent can actually reach, so the guards resolve against the runtime surface
    rather than a hand-maintained list that can drift from it.

    Returns:
        The tool names exposed by the backlog and SAM servers.
    """
    import backlog_core.server as backlog_server
    import sam_schema.server as sam_server

    async def _listings() -> tuple[frozenset[str], frozenset[str]]:
        backlog_tools = await backlog_server.mcp.list_tools()
        sam_tools = await sam_server.mcp.list_tools()
        return frozenset(t.name for t in backlog_tools), frozenset(t.name for t in sam_tools)

    backlog_names, sam_names = asyncio.run(_listings())
    return ToolSurface(backlog=backlog_names, sam=sam_names)


def _is_placeholder(value: str) -> bool:
    """Report whether a literal is an authoring placeholder rather than a real value."""
    return (
        not value
        or "..." in value
        or any(char in _PLACEHOLDER_CHARS for char in value)
        or not any(char.isalpha() for char in value)
    )


def find_tool_grant_defects(text: str, surface: ToolSurface) -> list[Defect]:
    """Flag ``mcp__plugin_dh_*__`` tokens that name no tool on the server they address.

    A frontmatter grant for a tool that does not exist is dropped silently and the rest of
    the grant survives, so the agent starts without the capability its own file claims.
    The same token in prose instructs a call that cannot dispatch. Wildcard grants
    (``mcp__plugin_dh_backlog__*``) name no specific tool and are not checked.

    Args:
        text: Full markdown text of one shipped file.
        surface: The live tool listing from both servers.

    Returns:
        One defect per token naming a tool absent from the server it addresses.
    """
    defects: list[Defect] = []
    for match in _GRANT_RE.finditer(text):
        server_key, tool_name = match.group(1), match.group(2)
        if tool_name in surface.server_for(server_key):
            continue
        other_server = _SAM_SERVER if server_key == _BACKLOG_SERVER else _BACKLOG_SERVER
        detail = (
            f"names no tool on the {server_key} server"
            if tool_name not in surface.all_names
            else f"is a {other_server} server tool, granted under the {server_key} prefix"
        )
        defects.append(Defect(kind="tool_grant", found=match.group(0), detail=detail))
    return defects


def find_tool_call_defects(text: str, surface: ToolSurface) -> list[Defect]:
    """Flag instructed ``tool(...)`` calls whose tool name is absent from both servers.

    Args:
        text: Full markdown text of one shipped file.
        surface: The live tool listing from both servers.

    Returns:
        One defect per call site naming a tool neither server exposes.
    """
    live = surface.all_names
    return [
        Defect(kind="tool_call", found=f"{match.group(1)}(", detail="names no tool on either dh MCP server")
        for match in _CALL_RE.finditer(text)
        if match.group(1) not in live
    ]


def _call_span(text: str, start: int) -> str:
    """Return the argument text of a call whose opening paren sits at ``start``.

    Stops at the matching close paren, at a blank line, or after ``_MAX_CALL_SPAN``
    characters — prose call sites are frequently wrapped or truncated mid-argument, so a
    strictly balanced scan would silently skip them.
    """
    depth = 0
    for index in range(start, min(len(text), start + _MAX_CALL_SPAN)):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
        elif text.startswith("\n\n", index):
            return text[start:index]
    return text[start : start + _MAX_CALL_SPAN]


def _artifact_call_spans(text: str) -> Iterator[str]:
    """Yield the argument text of every instructed ``artifact_*`` call."""
    for match in _ARTIFACT_CALL_RE.finditer(text):
        yield _call_span(text, match.end() - 1)


def _is_shell_comment_start(text: str, index: int) -> bool:
    return index == 0 or text[index - 1].isspace()


def _skip_whitespace(text: str, start: int) -> int:
    while start < len(text) and text[start].isspace():
        start += 1
    return start


def _matches_artifact_register(text: str, start: int) -> bool:
    if not text.startswith("artifact", start):
        return False
    cursor = start + len("artifact")
    if cursor == len(text) or not text[cursor].isspace():
        return False
    cursor = _skip_whitespace(text, cursor)
    if not text.startswith("register", cursor):
        return False
    cursor += len("register")
    if cursor == len(text) or not text[cursor].isspace():
        return False
    cursor = _skip_whitespace(text, cursor)
    return text.startswith("--", cursor) or (cursor < len(text) and text[cursor] == "\\")


def _uv_run_arguments_start(text: str, start: int) -> int | None:
    if not text.startswith("uv", start):
        return None
    cursor = start + len("uv")
    if cursor == len(text) or not text[cursor].isspace():
        return None
    cursor = _skip_whitespace(text, cursor)
    if not text.startswith("run", cursor):
        return None
    cursor += len("run")
    if cursor == len(text) or not text[cursor].isspace():
        return None
    return cursor


def _matches_uv_artifact_register(text: str, start: int) -> bool:
    cursor = _uv_run_arguments_start(text, start)
    if cursor is None:
        return False

    quote = ""
    escaped = False
    while cursor < len(text):
        char = text[cursor]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char in ";&|#\n`":
            return False
        elif (cursor == start or text[cursor - 1].isspace()) and _matches_artifact_register(text, cursor):
            return True
        cursor += 1
    return False


def _cli_scan_character(char: str, quote: str, escaped: bool, artifact_command: bool) -> tuple[str, str, bool]:
    if not artifact_command:
        return char, quote, escaped
    if escaped:
        return " ", quote, False
    if char == "\\":
        return " ", quote, True
    if quote:
        return " ", "" if char == quote else quote, False
    if char in "\"'":
        return " ", char, False
    return char, quote, escaped


def _artifact_register_cli_starts(text: str) -> Iterator[tuple[int, bool]]:
    index = 0
    command_start = True
    quote = ""
    escaped = False
    artifact_command = False
    while index < len(text):
        char, quote, escaped = _cli_scan_character(text[index], quote, escaped, artifact_command)
        if command_start:
            index = _skip_whitespace(text, index)
            if index == len(text):
                return
            char = text[index]
            if text[index] == "`":
                index += 1
                continue
            if text[index] == "#":
                index = text.find("\n", index)
                if index == -1:
                    return
                command_start = True
                index += 1
                continue
            if _matches_artifact_register(text, index) or _matches_uv_artifact_register(text, index):
                inline = index > 0 and text[index - 1] == "`"
                yield index, inline
                artifact_command = True
            command_start = False

        if char == "`":
            command_start = True
            artifact_command = False
        elif char == "#" and _is_shell_comment_start(text, index):
            newline = text.find("\n", index)
            if newline == -1:
                return
            command_start = True
            artifact_command = False
            index = newline
        elif char in ";&|" or (char == "\n" and not text[:index].rstrip().endswith("\\")):
            command_start = True
            artifact_command = False
        index += 1


def _cli_command_span(text: str, start: int, inline: bool) -> tuple[str, str]:
    quote = ""
    escaped = False
    end = start
    while end < len(text):
        char = text[end]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "\n":
            if not text[start:end].rstrip().endswith("\\"):
                break
        elif quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char in ";&|" or (char == "#" and _is_shell_comment_start(text, end)) or (inline and char == "`"):
            break
        end += 1
    return text[start:end], quote


def _artifact_register_cli_defects(text: str, artifact_statuses: frozenset[str]) -> Iterator[Defect]:
    for start, inline in _artifact_register_cli_starts(text):
        span, quote = _cli_command_span(text, start, inline)
        if quote:
            yield Defect(
                kind="artifact_enum",
                found="artifact register",
                detail=f"has malformed artifact register CLI tokenization: unterminated {quote!r} quote",
            )
            continue

        try:
            tokens = shlex.split(span, posix=False)
        except ValueError as exc:
            yield Defect(
                kind="artifact_enum",
                found="artifact register",
                detail=f"has malformed artifact register CLI tokenization: {exc}",
            )
            continue

        for index, token in enumerate(tokens):
            if token == "--status" and index + 1 < len(tokens) and not tokens[index + 1].startswith("--"):
                raw_value = tokens[index + 1]
                found, value = f"--status {raw_value}", raw_value.strip("\"'")
            elif token.startswith("--status="):
                found, value = token, token.partition("=")[2].strip("\"'")
            else:
                continue
            if not _is_placeholder(value) and value not in artifact_statuses:
                yield Defect(
                    kind="artifact_enum",
                    found=found,
                    detail=f"is not an ArtifactStatus; valid values are {sorted(artifact_statuses)}",
                )


def find_artifact_enum_defects(
    text: str, artifact_types: frozenset[str], artifact_statuses: frozenset[str]
) -> list[Defect]:
    """Flag ``artifact_type=`` and ``status=`` literals that are not enum members.

    ``artifact_type=`` is checked wherever it appears — that keyword is unique to the
    artifact tools. ``status=`` is checked only inside an ``artifact_*`` call span, and
    ``--status`` only inside an ``artifact register`` CLI command, because the same
    values carry unrelated domains on the backlog and task tools.

    Args:
        text: Full markdown text of one shipped file.
        artifact_types: Valid ``ArtifactType`` values.
        artifact_statuses: Valid ``ArtifactStatus`` values.

    Returns:
        One defect per literal outside its enum.
    """
    defects: list[Defect] = [
        Defect(
            kind="artifact_enum",
            found=f'artifact_type="{value}"',
            detail=f"is not an ArtifactType; valid values are {sorted(artifact_types)}",
        )
        for value in _ARTIFACT_TYPE_KWARG_RE.findall(text)
        if not _is_placeholder(value) and value not in artifact_types
    ]
    defects.extend(
        Defect(
            kind="artifact_enum",
            found=f'status="{value}"',
            detail=f"is not an ArtifactStatus; valid values are {sorted(artifact_statuses)}",
        )
        for span in _artifact_call_spans(text)
        for value in _STATUS_KWARG_RE.findall(span)
        if not _is_placeholder(value) and value not in artifact_statuses
    )
    defects.extend(_artifact_register_cli_defects(text, artifact_statuses))
    return defects
