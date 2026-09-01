"""Structural contract tests for the BacklogBackend capability properties.

Enforces three contracts across every backend registered in
``backend_protocol._VALID_BACKENDS``:

1. Any backend where ``supports_batch_status_fetch == False`` MUST raise
   ``NotImplementedError`` from ``batch_fetch_statuses()``.
2. Any backend where ``supports_batch_status_fetch == True`` MUST NOT raise
   ``NotImplementedError`` from ``batch_fetch_statuses()``.
3. All concrete backends expose ``supports_batch_status_fetch: bool`` and
   ``issue_id_type: Literal["integer", "string"]`` with the correct types.

Parametrization is driven by ``_bp._VALID_BACKENDS`` — the factory's own
source of truth — so any backend added to that tuple is automatically
enrolled in these contracts without any change to this file.

``batch_fetch_statuses`` is called with an empty list ``[]``.  All
``True``-capability backends loop over the input; an empty list returns
``{}`` without touching network, disk, or any external resource.  The
``False``-capability backend (``BeadsBackend``) raises unconditionally
before inspecting the argument, so the empty list still exercises the
contract.  This keeps every test fully offline.

GitHubBackend delegates to ``gh_client.batch_fetch_statuses``.  That
function is patched at the module level so no network credentials or
HTTP connections are required.

See ``backlog_core/backend_protocol.py`` for the protocol definition and
``backlog_core/backends/`` for the concrete implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import backlog_core.backend_protocol as _bp
import pytest
from backlog_core.backend_protocol import create_backend, require_github_extras
from backlog_core.models import UnsupportedBackendCapabilityError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_gh_client_batch_fetch(mocker: MockerFixture) -> None:
    """Patch ``gh_client.batch_fetch_statuses`` to return an empty dict.

    Applied to every test in this module (``autouse=True``) so that
    GitHubBackend tests never attempt a real GitHub API connection.
    Backends that do not call ``gh_client`` ignore the patch silently.
    """
    mocker.patch("backlog_core.gh_client.batch_fetch_statuses", return_value={})


# ---------------------------------------------------------------------------
# TestBacklogBackendCapabilityContract
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBacklogBackendCapabilityContract:
    """Parametrized contract suite for BacklogBackend capability properties.

    Every backend in ``_bp._VALID_BACKENDS`` is constructed via
    ``create_backend(name)`` and exercised against three contracts.
    Future backends added to that tuple are enrolled automatically.
    """

    # ------------------------------------------------------------------
    # Contract 3 — property types
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("name", _bp._VALID_BACKENDS)
    def test_supports_batch_status_fetch_is_bool(self, name: str) -> None:
        """``supports_batch_status_fetch`` must be a ``bool`` on every backend.

        Why: Protocol consumers use the truthiness of this flag to gate
        ``batch_fetch_statuses`` calls.  A non-bool truthy value (e.g. an
        int ``1``) could pass a truthiness check while failing an
        ``isinstance(flag, bool)`` check, masking a type error.
        """
        backend = create_backend(name)

        assert isinstance(backend.supports_batch_status_fetch, bool), (
            f"{type(backend).__name__}.supports_batch_status_fetch is "
            f"{type(backend.supports_batch_status_fetch).__name__!r}, expected bool"
        )

    @pytest.mark.parametrize("name", _bp._VALID_BACKENDS)
    def test_issue_id_type_is_valid_literal(self, name: str) -> None:
        """``issue_id_type`` must be exactly ``"integer"`` or ``"string"`` on every backend.

        Why: Callers branch on this value when deciding whether integer-keyed
        operations are meaningful.  An unexpected value would fall through
        silently and produce incorrect behaviour.
        """
        backend = create_backend(name)
        valid_values = {"integer", "string"}

        assert backend.issue_id_type in valid_values, (
            f"{type(backend).__name__}.issue_id_type is {backend.issue_id_type!r}, "
            f"expected one of {sorted(valid_values)}"
        )

    # ------------------------------------------------------------------
    # Contract 1 — False flag MUST raise NotImplementedError
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("name", list(_bp._VALID_BACKENDS))
    def test_false_flag_raises_not_implemented(self, name: str) -> None:
        """Backends declaring ``supports_batch_status_fetch == False`` MUST raise.

        Contract: When ``supports_batch_status_fetch`` is ``False``, calling
        ``batch_fetch_statuses([])`` MUST raise ``NotImplementedError``.  Any
        backend that declares ``False`` but does not raise violates the
        contract and would cause operations.py to silently skip a batch fetch
        for a backend that actually supports it.

        Why the test only runs the assertion when the flag is ``False``:
        The contract is conditional on the declared value — ``True``-flag
        backends are covered by Contract 2.
        """
        backend = create_backend(name)

        if not backend.supports_batch_status_fetch:
            with pytest.raises(NotImplementedError):
                backend.batch_fetch_statuses([])

    # ------------------------------------------------------------------
    # Contract 2 — True flag MUST NOT raise NotImplementedError
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("name", list(_bp._VALID_BACKENDS))
    def test_true_flag_does_not_raise_not_implemented(self, name: str) -> None:
        """Backends declaring ``supports_batch_status_fetch == True`` MUST NOT raise NotImplementedError.

        Contract: When ``supports_batch_status_fetch`` is ``True``, calling
        ``batch_fetch_statuses([])`` must complete without raising
        ``NotImplementedError``.  Other exceptions from misconfigured
        environments would be acceptable, but ``NotImplementedError``
        indicates the method is a stub — contradicting the ``True`` flag.

        ``batch_fetch_statuses([])`` is used because:
        - All ``True`` backends iterate over ``items``; an empty list returns
          ``{}`` without touching external resources.
        - The ``False`` backend (BeadsBackend) raises before reading the
          argument, so this call would still exercise that contract if the
          flag were accidentally flipped to ``True``.

        The narrow ``except NotImplementedError`` catch is intentional and
        compliant with the exception-handling policy: it is the sole
        exception type that violates this specific contract.  All other
        exceptions (e.g. ``RuntimeError`` from an unconfigured GitHub token)
        are allowed to propagate and are not caught here.
        """
        backend = create_backend(name)

        if backend.supports_batch_status_fetch:
            try:
                backend.batch_fetch_statuses([])
            except NotImplementedError as exc:
                pytest.fail(
                    f"{type(backend).__name__}.supports_batch_status_fetch is True "
                    f"but batch_fetch_statuses([]) raised NotImplementedError: {exc}"
                )

    # ------------------------------------------------------------------
    # Contract cohesion — flag and behaviour must agree
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("name", _bp._VALID_BACKENDS)
    def test_flag_and_behaviour_are_consistent(self, name: str) -> None:
        """The declared flag and actual ``batch_fetch_statuses`` behaviour must agree.

        This test is the regression target described in the task brief: it
        fails when a backend's ``supports_batch_status_fetch`` declaration
        does not match whether ``batch_fetch_statuses([])`` raises
        ``NotImplementedError``.

        A backend is consistent when exactly one of the following holds:
        - ``flag is False`` and the call raises ``NotImplementedError``
        - ``flag is True`` and the call does NOT raise ``NotImplementedError``

        Note: This test is the primary regression net.  The two preceding
        contract tests independently verify each half; this test verifies
        that both halves form a consistent pair on the same backend instance.
        """
        backend = create_backend(name)
        raised_not_implemented: bool

        try:
            backend.batch_fetch_statuses([])
            raised_not_implemented = False
        except NotImplementedError:
            raised_not_implemented = True

        flag: bool = backend.supports_batch_status_fetch

        assert flag != raised_not_implemented, (
            f"{type(backend).__name__}: supports_batch_status_fetch={flag} but "
            f"batch_fetch_statuses([]) "
            + ("did NOT raise" if flag is False else "raised")
            + " NotImplementedError — flag and behaviour are inconsistent"
        )


# ---------------------------------------------------------------------------
# TestGitHubExtrasCapabilityContract
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGitHubExtrasCapabilityContract:
    """Parametrized contract suite for the ``supports_github_extras`` flag.

    Mirrors ``TestBacklogBackendCapabilityContract``'s Contract 1/Contract 2
    pair above, for the ``GitHubExtras`` capability gate
    (``require_github_extras``, re-exported from ``backend_protocol.py``)
    instead of ``supports_batch_status_fetch``. Every backend in
    ``_bp._VALID_BACKENDS`` is enrolled automatically.

    Unlike ``supports_batch_status_fetch``, the ``GitHubExtras`` gate is not
    self-checked inside the backend's own ``get_github()`` — it is enforced by
    the caller-side ``require_github_extras()`` helper (this is precisely the
    defect backlog #2287 reports: ``isinstance(backend, GitHubExtras)`` alone
    lets a structurally-compliant backend reach its own bare ``RuntimeError``
    stub). These tests therefore exercise ``require_github_extras()`` rather
    than the backend method directly.
    """

    @pytest.mark.parametrize("name", list(_bp._VALID_BACKENDS))
    def test_false_flag_raises_unsupported_capability(self, name: str) -> None:
        """Backends declaring ``supports_github_extras == False`` MUST raise.

        Contract: When ``supports_github_extras`` is ``False``,
        ``require_github_extras(backend, ...)`` MUST raise
        ``UnsupportedBackendCapabilityError``.
        """
        backend = create_backend(name)

        if not backend.supports_github_extras:
            with pytest.raises(UnsupportedBackendCapabilityError) as exc_info:
                require_github_extras(backend, "get_github")
            assert exc_info.value.capability == "github_extras"
            assert exc_info.value.backend == type(backend).__name__
            assert exc_info.value.protocol_mismatch is False, (
                "a flag-False backend is a genuinely unsupported capability, not a protocol mismatch"
            )

    @pytest.mark.parametrize("name", list(_bp._VALID_BACKENDS))
    def test_true_flag_does_not_raise_unsupported_capability(self, name: str) -> None:
        """Backends declaring ``supports_github_extras == True`` MUST NOT raise it.

        Contract: When ``supports_github_extras`` is ``True``,
        ``require_github_extras(backend, ...)`` must not raise
        ``UnsupportedBackendCapabilityError`` and must return the backend
        unchanged. The gate is checked without calling ``get_github()`` itself,
        so no network or credential dependency is required even for
        ``GitHubBackend``.
        """
        backend = create_backend(name)

        if backend.supports_github_extras:
            try:
                narrowed = require_github_extras(backend, "get_github")
            except UnsupportedBackendCapabilityError as exc:
                pytest.fail(
                    f"{type(backend).__name__}.supports_github_extras is True but "
                    f"require_github_extras() raised UnsupportedBackendCapabilityError: {exc}"
                )
            else:
                assert narrowed is backend

    def test_protocol_mismatch_flag_distinguishes_backend_bug_from_unsupported(self) -> None:
        """A True flag paired with a non-conforming backend raises protocol_mismatch=True.

        Contract: no backend in ``_bp._VALID_BACKENDS`` currently exhibits this
        inconsistency (each one's flag matches its actual method set), so this
        test builds a minimal stub that lies about its own capability —
        ``supports_github_extras = True`` but none of the ``GitHubExtras``
        methods implemented — to exercise the ``isinstance`` branch directly.

        Why: a flag-``False`` backend is a normal, expected "this capability
        isn't offered" outcome; a flag-``True`` backend that fails the
        ``isinstance`` check is a backend implementation bug (the flag lied).
        Conflating the two in one message misleads whoever reads it — this
        was raised in code review on PR #3360.
        """

        class _LyingBackend:
            supports_github_extras = True

        with pytest.raises(UnsupportedBackendCapabilityError) as exc_info:
            require_github_extras(_LyingBackend(), "get_github")  # type: ignore[arg-type]

        assert exc_info.value.protocol_mismatch is True
        assert "backend bug" in str(exc_info.value)
        assert "GitHubExtras" in str(exc_info.value), (
            "message should name the actual Protocol class, not just the opaque "
            "capability flag string 'github_extras' — raised in code review on PR #3360"
        )
