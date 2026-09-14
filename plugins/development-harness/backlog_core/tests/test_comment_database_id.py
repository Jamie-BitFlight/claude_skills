"""Tests that a comment carries the numeric identifier REST addresses it by.

GraphQL names a comment by its node ID (``IC_kwDO...``). REST's comment endpoints
take a number instead, which GraphQL exposes as ``databaseId``. A comment fetched
over GraphQL therefore cannot be read or written over REST unless the listing
selected that field, so both comment queries select it and the parser carries it
through as ``database_id``.

It stays optional. Only GitHub has one: the SQLite and memory backends address
their comments by ``id`` alone, and putting a number there would invent an
identifier that resolves to nothing.
"""

from __future__ import annotations

from backlog_core.gh_client import _COMMENT_BY_ID_QUERY, _ISSUE_COMMENTS_QUERY, _parse_comment_node

_RAW_NODE: dict[str, object] = {
    "id": "IC_kwDOAbCdEf4AbCdEf",
    "databaseId": 5659363376,
    "body": "A comment body.",
    "url": "https://github.com/owner/repo/issues/1#issuecomment-5659363376",
    "author": {"login": "octocat"},
    "createdAt": "2026-09-14T05:00:00Z",
    "updatedAt": "2026-09-14T05:00:00Z",
}


class TestBothQueriesSelectTheField:
    """An unselected field is absent from the response, so the query is the contract."""

    def test_the_listing_query_selects_database_id(self):
        assert "databaseId" in _ISSUE_COMMENTS_QUERY

    def test_the_single_comment_query_selects_database_id(self):
        assert "databaseId" in _COMMENT_BY_ID_QUERY


class TestParsingCarriesTheIdentifier:
    """The node reaches callers through this parser, so it has to survive it."""

    def test_an_integer_database_id_is_carried(self):
        assert _parse_comment_node(_RAW_NODE)["database_id"] == 5659363376

    def test_the_node_id_is_still_carried(self):
        """REST needs the number and the GraphQL mutations still need the node ID."""
        assert _parse_comment_node(_RAW_NODE)["id"] == "IC_kwDOAbCdEf4AbCdEf"

    def test_every_other_field_is_unchanged(self):
        parsed = _parse_comment_node(_RAW_NODE)

        assert parsed["body"] == "A comment body."
        assert parsed["author"] == "octocat"
        assert parsed["created_at"] == "2026-09-14T05:00:00Z"
        assert parsed["updated_at"] == "2026-09-14T05:00:00Z"


class TestAnAbsentOrUnusableValueStaysAbsent:
    """A guessed number addresses some other comment, so nothing is guessed."""

    def test_a_node_without_the_field_omits_it(self):
        node = {key: value for key, value in _RAW_NODE.items() if key != "databaseId"}

        assert "database_id" not in _parse_comment_node(node)

    def test_a_null_database_id_is_omitted(self):
        assert "database_id" not in _parse_comment_node({**_RAW_NODE, "databaseId": None})

    def test_a_string_database_id_is_omitted(self):
        """The field is declared Int; a string means the response is not what it claims."""
        assert "database_id" not in _parse_comment_node({**_RAW_NODE, "databaseId": "5659363376"})

    def test_a_boolean_is_not_read_as_a_number(self):
        """bool subclasses int, so True would otherwise be carried as comment 1."""
        assert "database_id" not in _parse_comment_node({**_RAW_NODE, "databaseId": True})
