"""TDD test that every name in __all__ is documented in the module docstring.

Phase 0, Concern C4. This test is authored INDEPENDENTLY of the fix implementation
(T05) to ensure it validates the desired behavior, not just consistency with the
implementation.

Red-state contract (pre-fix):
  test_all_exports_appear_in_module_docstring FAILS — the current docstring only
  mentions ProgressiveMarkdownNavigator, NavigatorOptions, chunk_text, and
  paginate_results. The remaining 20 names in __all__ are absent.

Green-state contract (post-fix, T05):
  The test passes — the module docstring has been extended to document every name
  in __all__ with at least a one-line description.

Design constraint: The requirement is derived from ``progressive_markdown.__all__``
at runtime so it cannot drift when new exports are added to __all__.
"""

from __future__ import annotations

import progressive_markdown


def test_all_exports_appear_in_module_docstring() -> None:
    """Every name in __all__ must appear as a substring in the module docstring.

    Derives the expected set of documented names from ``progressive_markdown.__all__``
    at runtime — no hardcoded count or literal list — so the test automatically
    catches future additions to __all__ that are not reflected in the docstring.

    PRE-FIX STATE: This test MUST FAIL against the current __init__.py because the
    module docstring only contains ProgressiveMarkdownNavigator, NavigatorOptions,
    chunk_text, and paginate_results. The remaining exported names (exceptions,
    models, providers) are absent from the docstring.

    POST-FIX EXPECTATION (T05): The docstring has been extended to mention every
    name in __all__, at which point this test passes.

    Failure message lists the specific missing names so the implementer knows
    exactly which exports need to be added to the docstring.
    """
    # Arrange
    assert progressive_markdown.__all__ is not None, "__all__ must be defined"
    assert progressive_markdown.__doc__ is not None, "Module docstring must be present"

    # Act — derive missing names from __all__ at runtime (no hardcoded list)
    docstring: str = progressive_markdown.__doc__
    missing: list[str] = [name for name in progressive_markdown.__all__ if name not in docstring]

    # Assert — report the specific missing names so the failure is actionable
    assert not missing, (
        f"{len(missing)} name(s) in progressive_markdown.__all__ are absent from the "
        f"module docstring: {missing}. "
        f"Extend __init__.py's docstring to include a one-line description for each "
        f"missing export (see T05)."
    )
