"""FM009 regression tests — mcp: field preservation in frontmatter round-trips.

These tests verify that the local frontmatter processing (frontmatter_utils.py)
correctly handles the ecosystem-owned `mcp:` key:

- Round-trip does not remove or mangle `mcp:` block content (#516)
- Round-trip preserves `mcp: null` scalar value (#517)

Background: FM009 was a warning emitted by the old plugin_validator.py for
unquoted colons in `description`. A state-machine bug caused it to be incorrectly
suppressed for ALL lines after an `mcp:` block — and for NONE of the lines after
`mcp: null` (scalar). The validator was migrated to `skilllint` (upstream); these
tests cover the remaining local processing layer.
"""

from __future__ import annotations


class TestMcpBlockPreservation:
    """Round-trip via loads_frontmatter/dump_frontmatter preserves mcp: blocks."""

    def test_mcp_block_preserved_verbatim(self) -> None:
        """mcp: block content survives a frontmatter round-trip unchanged."""
        from frontmatter_utils import dump_frontmatter, loads_frontmatter

        text = (
            "---\n"
            "name: test-skill\n"
            "description: Does useful things\n"
            "tools: Read, Write\n"
            "mcp:\n"
            "  server: ./scripts/server.py\n"
            "  transport: stdio\n"
            "---\n\n"
            "# Body\n"
        )
        post = loads_frontmatter(text)
        result = dump_frontmatter(post)

        assert "mcp:" in result
        assert "server: ./scripts/server.py" in result
        assert "transport: stdio" in result

    def test_mcp_block_with_nested_colons_not_mangled(self) -> None:
        """mcp: block values containing colons are not incorrectly requoted.

        Includes scalar values with embedded ``": "`` (the YAML key separator
        when unquoted) to exercise the regression path that would mangle
        colons inside values during the round-trip.
        """
        from frontmatter_utils import dump_frontmatter, loads_frontmatter

        text = (
            "---\n"
            "name: test-skill\n"
            "description: A skill\n"
            "tools: Read\n"
            "mcp:\n"
            "  server: ./scripts/mcp_server.py\n"
            '  notes: "URL: https://example.com/docs"\n'
            "  tools:\n"
            "    - name: do_thing\n"
            '      description: "Performs the thing: with colon in value"\n'
            "---\n\n"
            "# Body\n"
        )
        post = loads_frontmatter(text)
        result = dump_frontmatter(post)

        assert "mcp:" in result
        assert "name: do_thing" in result
        # Embedded ": " in scalar values must survive the round-trip.
        assert "Performs the thing: with colon in value" in result
        assert "URL: https://example.com/docs" in result

    def test_mcp_null_scalar_preserved(self) -> None:
        """mcp: null scalar survives a round-trip; reload returns None.

        Verifies both the original parsed metadata and the re-loaded dumped
        output preserve ``None`` on the ``mcp`` key. The exact serialized form
        (``mcp:`` vs ``mcp: null`` vs ``mcp: ~``) is the YAML emitter's choice;
        what matters is that re-loading the dump yields ``None`` and that the
        emitter does not produce a block-mapping (``mcp:`` followed by indented
        child keys), which would change the value from None to a dict.
        """
        from frontmatter_utils import dump_frontmatter, loads_frontmatter

        text = "---\nname: test-skill\ndescription: A skill without mcp\ntools: Read\nmcp: null\n---\n\n# Body\n"
        post = loads_frontmatter(text)
        result = dump_frontmatter(post)
        reloaded = loads_frontmatter(result)

        # Serialized output preserves the mcp key.
        assert "mcp:" in result
        # Both parsed metadata objects MUST contain the mcp key explicitly
        # (.get() would return None for a missing key, which would silently pass).
        assert "mcp" in post.metadata
        assert "mcp" in reloaded.metadata
        # Round-trip preserves None on the original parsed metadata.
        assert post.metadata["mcp"] is None
        # Re-loading the dumped output also returns None (not a dict — the
        # emitter must not have produced a block-mapping).
        assert reloaded.metadata["mcp"] is None

    def test_description_with_colon_still_detected_after_mcp_null(self) -> None:
        """Non-mcp fields after mcp: null are loaded correctly (no state bleed).

        This is the #517 regression: the old state machine treated lines after
        mcp: null as ecosystem-owned, swallowing downstream fields. The ruamel.yaml
        backend has no such state; all fields are parsed independently.
        """
        from frontmatter_utils import loads_frontmatter

        # Place description AFTER mcp: null — if state bled, description would be lost
        text = "---\nname: test-skill\nmcp: null\ndescription: A useful skill\ntools: Read\n---\n\n# Body\n"
        post = loads_frontmatter(text)

        assert post.metadata.get("description") == "A useful skill"
        assert post.metadata.get("mcp") is None
        assert post.metadata.get("tools") == "Read"

    def test_mcp_field_identity_via_ecosystem_registry(self) -> None:
        """ecosystem_registry registers mcp as an ecosystem-owned skill key."""
        from ecosystem_registry import get_ecosystem_owned_skill_keys

        owned = get_ecosystem_owned_skill_keys()
        assert "mcp" in owned
