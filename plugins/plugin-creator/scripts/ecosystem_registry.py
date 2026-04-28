"""Ecosystem registry for non-Claude-Code frontmatter field ownership.

This module declares which top-level YAML frontmatter keys belong to external
AI tool ecosystems (e.g. OpenCode) rather than to Claude Code itself.  The
plugin validator imports this registry to skip FM009 rewrites on ecosystem-
owned keys, preventing silent mutation of valid third-party configuration.

Registered ecosystem:
  opencode — source_url: https://github.com/sst/opencode
              verified_date: 2026-03-06
              skill_frontmatter_keys: {"mcp"}

  The ``mcp:`` key carries OpenCode MCP server configuration (stdio and http
  transport formats) directly in SKILL.md frontmatter.  AmpCode is *not*
  listed as a separate entry because its compatibility with the ``mcp:``
  inline frontmatter schema has not been independently verified; it must not
  be assumed equivalent to OpenCode without a citable source.

Usage (from a sibling script)::

    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from ecosystem_registry import get_ecosystem_owned_skill_keys, get_ecosystem_for_key

    if get_ecosystem_for_key("mcp") is not None:
        # skip FM009 rewrite for this key
        ...
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EcosystemSpec:
    """Specification for a single non-Claude-Code AI tool ecosystem.

    Attributes:
        display_name: Human-readable ecosystem name for error messages and docs.
        source_url: Canonical URL documenting the ecosystem's frontmatter usage.
        verified_date: ISO 8601 date (YYYY-MM-DD) when the source was last checked.
        skill_frontmatter_keys: Top-level YAML keys owned by this ecosystem in SKILL.md.
        agent_frontmatter_keys: Top-level YAML keys owned by this ecosystem in agent files.
        notes: Free-form notes including verification caveats and compatibility warnings.
    """

    display_name: str
    source_url: str
    verified_date: str
    skill_frontmatter_keys: frozenset[str]
    agent_frontmatter_keys: frozenset[str]
    notes: str


_REGISTRY: dict[str, EcosystemSpec] = {
    "opencode": EcosystemSpec(
        display_name="OpenCode",
        source_url="https://github.com/sst/opencode",
        verified_date="2026-03-06",
        skill_frontmatter_keys=frozenset({"mcp"}),
        agent_frontmatter_keys=frozenset(),
        notes=(
            "The 'mcp' top-level key carries MCP server configuration in OpenCode SKILL.md "
            "frontmatter (both stdio and http transport formats). "
            "AmpCode compatibility with inline mcp: frontmatter is UNVERIFIED — "
            "AmpCode must NOT be assumed equivalent to OpenCode without a citable source."
        ),
    )
}


def get_ecosystem_owned_skill_keys() -> frozenset[str]:
    """Return the union of all ecosystem-owned frontmatter keys across every registered ecosystem.

    Covers both ``skill_frontmatter_keys`` and ``agent_frontmatter_keys`` from all
    registered ecosystems, matching the behaviour of :func:`get_ecosystem_for_key`.

    Computed from ``_REGISTRY`` on each call so that tests can patch ``_REGISTRY``
    and observe the change through this function.

    Returns:
        Immutable frozenset of top-level YAML key names owned by any registered
        ecosystem in either ``skill_frontmatter_keys`` or ``agent_frontmatter_keys``.
        Callers can safely check ``key in get_ecosystem_owned_skill_keys()`` without
        risk of accidental mutation.
    """
    return frozenset().union(
        *(spec.skill_frontmatter_keys | spec.agent_frontmatter_keys for spec in _REGISTRY.values())
    )


def get_ecosystem_for_key(key: str) -> str | None:
    """Return the ecosystem name that owns ``key``, or None if unowned.

    Checks both ``skill_frontmatter_keys`` and ``agent_frontmatter_keys`` for
    each registered ecosystem.

    Args:
        key: A top-level YAML frontmatter key name (e.g. ``"mcp"``).

    Returns:
        The dict key of the owning ecosystem (e.g. ``"opencode"``), or ``None``
        if no registered ecosystem claims ownership of ``key``.
    """
    for ecosystem_name, spec in _REGISTRY.items():
        if key in spec.skill_frontmatter_keys or key in spec.agent_frontmatter_keys:
            return ecosystem_name
    return None
