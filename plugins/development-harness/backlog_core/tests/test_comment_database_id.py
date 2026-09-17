"""Tests that a comment carries the numeric identifier REST addresses it by.

GraphQL names a comment by its node ID (``IC_kwDO...``). REST's comment endpoints
take a number instead, which GraphQL exposes as ``fullDatabaseId`` -- GitHub's
``BigInt`` scalar, not the sibling ``databaseId: Int`` field. A real comment
database ID already exceeds ``Int``'s signed 32-bit range (as does
``5659363376`` below), so selecting ``databaseId`` for a comment risks a
GraphQL error before parsing ever runs; ``fullDatabaseId`` is the field sized
to hold it. GitHub serializes ``BigInt`` as a decimal string on the wire (a
JSON integer is also tolerated) -- see
https://docs.github.com/en/graphql/reference/scalars#bigint. A comment
fetched or created over GraphQL therefore cannot be read or written over REST
unless the query/mutation selected this field and the parser normalized
whichever encoding it arrived in, so all three comment operations (listing,
single-comment lookup, and creation) select it and the parser carries it
through as ``database_id``.

It stays optional. Only GitHub has one: the SQLite and memory backends address
their comments by ``id`` alone, and putting a number there would invent an
identifier that resolves to nothing.

``IssueCommentNode`` is a validated Pydantic model (``strict=True``), so the
class itself — not just ``_parse_comment_node``'s defensive filtering — refuses
a ``database_id`` that is not a plain ``int``. Its own boundary-validation
tests below construct it via ``model_validate()`` against a raw dict rather
than the typed constructor: a raw dict is the actual boundary shape an
unknown/wrong value crosses in production (a raw GraphQL response, not a
Python call site a static type checker has already vetted), and it exercises
the class's runtime validation without asking a static type checker to accept
an argument its own annotation (``int | None``) declares invalid.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backlog_core.backend_types import IssueCommentNode
from backlog_core.gh_client import (
    _ADD_COMMENT_MUTATION,
    _COMMENT_BY_ID_QUERY,
    _ISSUE_COMMENTS_QUERY,
    _add_comment_graphql,
    _parse_comment_node,
    _parse_full_database_id,
)

# Exceeds Int32's signed range (2**31 - 1 == 2_147_483_647) -- the real-world
# case fullDatabaseId (GitHub's BigInt scalar) exists to handle.
_LARGE_DATABASE_ID = 5659363376

_RAW_NODE: dict[str, object] = {
    "id": "IC_kwDOAbCdEf4AbCdEf",
    "fullDatabaseId": _LARGE_DATABASE_ID,
    "body": "A comment body.",
    "url": "https://github.com/owner/repo/issues/1#issuecomment-5659363376",
    "author": {"login": "octocat"},
    "createdAt": "2026-09-14T05:00:00Z",
    "updatedAt": "2026-09-14T05:00:00Z",
}

_MODEL_KWARGS: dict[str, object] = {
    "id": "IC_kwDOAbCdEf4AbCdEf",
    "body": "A comment body.",
    "url": "https://github.com/owner/repo/issues/1#issuecomment-5659363376",
    "author": "octocat",
    "created_at": "2026-09-14T05:00:00Z",
    "updated_at": "2026-09-14T05:00:00Z",
}


class TestAllThreeOperationsSelectTheField:
    """An unselected field is absent from the response, so the query/mutation is the contract."""

    def test_the_listing_query_selects_full_database_id(self):
        assert "fullDatabaseId" in _ISSUE_COMMENTS_QUERY

    def test_the_single_comment_query_selects_full_database_id(self):
        assert "fullDatabaseId" in _COMMENT_BY_ID_QUERY

    def test_the_create_mutation_selects_full_database_id(self):
        assert "fullDatabaseId" in _ADD_COMMENT_MUTATION

    def test_none_of_them_select_the_overflow_prone_int32_field(self):
        """``databaseId: Int`` silently overflows for a real comment ID; nothing should select it."""
        assert "databaseId" not in _ISSUE_COMMENTS_QUERY
        assert "databaseId" not in _COMMENT_BY_ID_QUERY
        assert "databaseId" not in _ADD_COMMENT_MUTATION


class TestParsingCarriesTheIdentifier:
    """The node reaches callers through this parser, so it has to survive it."""

    def test_an_integer_full_database_id_is_carried(self):
        assert _parse_comment_node(_RAW_NODE).database_id == _LARGE_DATABASE_ID

    def test_a_decimal_string_full_database_id_is_carried(self):
        """GitHub's BigInt scalar serializes as a decimal string on the wire.

        This is the whole point of the ``databaseId`` -> ``fullDatabaseId``
        follow-up fix: a response that arrives this way must still resolve to
        the same integer, not be treated as malformed.
        """
        node = {**_RAW_NODE, "fullDatabaseId": str(_LARGE_DATABASE_ID)}

        assert _parse_comment_node(node).database_id == _LARGE_DATABASE_ID

    def test_the_node_id_is_still_carried(self):
        """REST needs the number and the GraphQL mutations still need the node ID."""
        assert _parse_comment_node(_RAW_NODE).id == "IC_kwDOAbCdEf4AbCdEf"

    def test_every_other_field_is_unchanged(self):
        parsed = _parse_comment_node(_RAW_NODE)

        assert parsed.body == "A comment body."
        assert parsed.author == "octocat"
        assert parsed.created_at == "2026-09-14T05:00:00Z"
        assert parsed.updated_at == "2026-09-14T05:00:00Z"

    def test_comment_creation_carries_both_identifiers(self, mocker):
        mocker.patch(
            "backlog_core.gh_client._graphql_request", return_value={"addComment": {"commentEdge": {"node": _RAW_NODE}}}
        )

        comment = _add_comment_graphql(mocker.Mock(), "issue-node", "body")

        assert comment.id == _RAW_NODE["id"]
        assert comment.database_id == _LARGE_DATABASE_ID


class TestAnAbsentOrUnusableValueStaysAbsent:
    """A guessed number addresses some other comment, so nothing is guessed."""

    def test_a_node_without_the_field_omits_it(self):
        node = {key: value for key, value in _RAW_NODE.items() if key != "fullDatabaseId"}

        assert _parse_comment_node(node).database_id is None

    def test_a_null_full_database_id_is_omitted(self):
        assert _parse_comment_node({**_RAW_NODE, "fullDatabaseId": None}).database_id is None

    def test_a_non_digit_string_is_omitted(self):
        """A decimal string is a valid BigInt encoding; a non-digit string means the response is not what it claims."""
        assert _parse_comment_node({**_RAW_NODE, "fullDatabaseId": "not-a-number"}).database_id is None

    def test_a_signed_string_is_omitted(self):
        """GitHub never emits a sign for this field; a negative-looking string is not a real ID."""
        assert _parse_comment_node({**_RAW_NODE, "fullDatabaseId": "-5659363376"}).database_id is None

    def test_a_boolean_is_not_read_as_a_number(self):
        """bool subclasses int, so True would otherwise be carried as comment 1."""
        assert _parse_comment_node({**_RAW_NODE, "fullDatabaseId": True}).database_id is None

    def test_a_float_is_omitted(self):
        """The field is declared BigInt (whole numbers only); a float means the response is not what it claims."""
        assert _parse_comment_node({**_RAW_NODE, "fullDatabaseId": 5659363376.5}).database_id is None


class TestParseFullDatabaseIdDirectly:
    """Unit coverage for the normalizer itself, independent of the surrounding node shape."""

    def test_accepts_a_plain_int(self):
        assert _parse_full_database_id(_LARGE_DATABASE_ID) == _LARGE_DATABASE_ID

    def test_accepts_a_decimal_string(self):
        assert _parse_full_database_id(str(_LARGE_DATABASE_ID)) == _LARGE_DATABASE_ID

    def test_rejects_none(self):
        assert _parse_full_database_id(None) is None

    def test_rejects_a_bool(self):
        assert _parse_full_database_id(True) is None

    def test_rejects_a_float(self):
        assert _parse_full_database_id(5659363376.5) is None

    def test_rejects_a_non_digit_string(self):
        assert _parse_full_database_id("abc") is None


class TestTheModelItselfRejectsANonIntDatabaseId:
    """``IssueCommentNode``'s own ``strict=True`` config is the second line of defense.

    ``_parse_comment_node`` already filters a bad ``fullDatabaseId`` before
    construction, but the model must independently refuse one — otherwise a
    future caller that builds ``IssueCommentNode`` directly (bypassing the
    parser) could silently coerce a bool into an int, per Pydantic's lax-mode
    default (``bool`` subclasses ``int`` in Python).

    Each case validates a raw ``dict`` via ``model_validate()`` rather than
    passing the bad value to the typed constructor: a raw dict is the actual
    boundary shape an untrusted caller crosses in production, and it lets
    Pydantic's runtime ``strict=True`` check do the rejecting instead of
    asking a static type checker to accept an argument its own annotation
    (``int | None``) declares invalid.
    """

    def test_a_valid_int_database_id_is_accepted(self):
        comment = IssueCommentNode.model_validate({**_MODEL_KWARGS, "database_id": 5659363376})

        assert comment.database_id == 5659363376

    def test_a_missing_database_id_defaults_to_none(self):
        comment = IssueCommentNode.model_validate(_MODEL_KWARGS)

        assert comment.database_id is None

    def test_a_bool_database_id_raises_validation_error(self):
        """Strict mode refuses ``True``/``False`` for an ``int`` field — no silent 1/0."""
        with pytest.raises(ValidationError):
            IssueCommentNode.model_validate({**_MODEL_KWARGS, "database_id": True})

    def test_a_string_database_id_raises_validation_error(self):
        """Strict mode refuses a numeric string — no silent coercion to int.

        (The string-to-int coercion for GitHub's decimal-string BigInt
        encoding happens earlier, in ``_parse_full_database_id`` -- the model
        itself still only accepts an already-normalized ``int``.)
        """
        with pytest.raises(ValidationError):
            IssueCommentNode.model_validate({**_MODEL_KWARGS, "database_id": "5659363376"})

    def test_a_float_database_id_raises_validation_error(self):
        with pytest.raises(ValidationError):
            IssueCommentNode.model_validate({**_MODEL_KWARGS, "database_id": 5659363376.0})
