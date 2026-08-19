"""Property tests for ordinal_mapper.py's ordinal-path generators.

Guards against #2969 Finding 2: ``_entry_ordinal_for_sub_heading()`` and
``_entry_ordinal_for_code()`` build ordinal-path strings by plain f-string
composition (``f"{parent}.{idx}"`` / ``f"{parent}.code.{k}"``), while
``disclosure_handler._ORDINAL_PATTERN`` independently hand-writes a regex
describing the same shape. Nothing previously enforced that the two agree —
a future change to either side could silently desynchronize them, the same
risk class #2956 fixed for section-key derivation (see
``TestSectionRoundTripProperty`` in ``test_github_sync.py``, whose style this
follows).
"""

from __future__ import annotations

from backlog_core.disclosure_handler import _ORDINAL_PATTERN
from backlog_core.ordinal_mapper import _entry_ordinal_for_code, _entry_ordinal_for_sub_heading
from hypothesis import given, strategies as st

# Root-level ordinals are plain digit strings produced elsewhere in the
# mapper (top-level section index), not by either generator under test.
_root_ordinal = st.integers(min_value=0, max_value=50).map(str)
_idx = st.integers(min_value=0, max_value=50)


@st.composite
def _heading_path(draw: st.DrawFn) -> str:
    """Build a nested heading ordinal the way OrdinalPathMapper does.

    Mirrors the recursive call in ordinal_mapper.py: each level's
    ``sub_ordinal`` becomes the ``parent_ordinal`` for the next level's
    ``_entry_ordinal_for_sub_heading`` call (see the recursion building
    ``child_ordinals``). Depth 0 returns the bare root ordinal.
    """
    ordinal = draw(_root_ordinal)
    for _ in range(draw(st.integers(min_value=0, max_value=5))):
        ordinal = _entry_ordinal_for_sub_heading(ordinal, draw(_idx))
    return ordinal


class TestOrdinalGeneratorValidatorAgreement:
    """Property: every ordinal string the generators can produce matches _ORDINAL_PATTERN."""

    @given(parent=_heading_path(), idx=_idx)
    def test_sub_heading_ordinal_matches_pattern(self, parent: str, idx: int) -> None:
        """A sub-heading ordinal, at any nesting depth, matches the validator regex."""
        ordinal = _entry_ordinal_for_sub_heading(parent, idx)
        assert _ORDINAL_PATTERN.fullmatch(ordinal), f"{ordinal!r} does not match _ORDINAL_PATTERN"

    @given(parent=_heading_path(), k=_idx)
    def test_code_ordinal_matches_pattern(self, parent: str, k: int) -> None:
        """A code-fence ordinal, attached to the root or any nested heading, matches the regex."""
        ordinal = _entry_ordinal_for_code(parent, k)
        assert _ORDINAL_PATTERN.fullmatch(ordinal), f"{ordinal!r} does not match _ORDINAL_PATTERN"
