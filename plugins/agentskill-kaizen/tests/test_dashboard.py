"""Test suite for dashboard.py — port allocation, health endpoint, state management.

Tests cover:
- get_dashboard_url() public accessor
- HealthHandler Tornado request handler
- _reset_dashboard_state() state cleanup
- _allocate_port() OS port allocation
- start_dashboard() integration (mock-based, no real server)

Strategy:
    Heavy third-party dependencies (panel, holoviews, hvplot, tornado) are
    stubbed at the module level before ``dashboard`` is imported.  This
    allows the test suite to exercise the port allocation, state management,
    health endpoint, and start_dashboard logic without requiring a live
    Panel/Bokeh server.
"""

from __future__ import annotations

import json
import os
import sys
import time
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub third-party modules that are not installed in the test venv.
# Must happen before ``import dashboard``.
# ---------------------------------------------------------------------------

# --- tornado stubs ---
_tornado_mod = types.ModuleType("tornado")
_tornado_web_mod = types.ModuleType("tornado.web")


class _StubRequestHandler:
    """Minimal tornado.web.RequestHandler stand-in for testing."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        self._headers: dict[str, str] = {}
        self._body: str = ""

    def set_header(self, name: str, value: str) -> None:
        self._headers[name] = value

    def write(self, chunk: str | bytes) -> None:
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8")
        self._body += chunk

    def initialize(self, **kwargs: object) -> None:
        pass


vars(_tornado_web_mod).update({"RequestHandler": _StubRequestHandler})
vars(_tornado_mod).update({"web": _tornado_web_mod})

# --- holoviews stubs ---
_hv_mod = types.ModuleType("holoviews")
vars(_hv_mod).update({"extension": MagicMock(), "HLine": MagicMock(), "VLine": MagicMock(), "Text": MagicMock()})

# --- hvplot stubs ---
_hvplot_mod = types.ModuleType("hvplot")
_hvplot_pandas_mod = types.ModuleType("hvplot.pandas")
vars(_hvplot_mod).update({"pandas": _hvplot_pandas_mod})

# --- panel stubs ---
_pn_mod = types.ModuleType("panel")
vars(_pn_mod).update({"extension": MagicMock(), "serve": MagicMock(), "Tabs": MagicMock(), "Column": MagicMock()})

_pn_pane = types.ModuleType("panel.pane")
vars(_pn_pane).update({"Markdown": MagicMock(), "HoloViews": MagicMock()})
vars(_pn_mod).update({"pane": _pn_pane})

_pn_widgets = types.ModuleType("panel.widgets")
vars(_pn_widgets).update({"Tabulator": MagicMock()})
vars(_pn_mod).update({"widgets": _pn_widgets})

_pn_state = MagicMock()
_pn_state.add_periodic_callback = MagicMock()
_pn_state.onload = MagicMock()
vars(_pn_mod).update({"state": _pn_state})

_pn_template = types.ModuleType("panel.template")
vars(_pn_template).update({"FastListTemplate": MagicMock()})
vars(_pn_mod).update({"template": _pn_template})

# Install stubs into sys.modules
sys.modules["tornado"] = _tornado_mod
sys.modules["tornado.web"] = _tornado_web_mod
sys.modules["holoviews"] = _hv_mod
sys.modules["hvplot"] = _hvplot_mod
sys.modules["hvplot.pandas"] = _hvplot_pandas_mod
sys.modules["panel"] = _pn_mod
sys.modules["panel.pane"] = _pn_pane
sys.modules["panel.widgets"] = _pn_widgets
sys.modules["panel.template"] = _pn_template

# Add mcp/ to sys.path so ``import dashboard`` resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp"))

import dashboard

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_module_state() -> Any:
    """Reset dashboard module-level state before and after every test.

    Ensures complete test isolation — no state leaks between tests.
    """
    dashboard._reset_dashboard_state()
    yield
    dashboard._reset_dashboard_state()


# ===================================================================
# Unit Tests: get_dashboard_url()
# ===================================================================


class TestGetDashboardUrl:
    """Tests for get_dashboard_url() public accessor."""

    def test_get_dashboard_url_when_port_is_none(self) -> None:
        """get_dashboard_url() returns None when _dashboard_port is None.

        Tests: Public accessor returns None when no dashboard is running.
        How: Ensure _dashboard_port is None (default state), call accessor.
        Why: MCP tool must detect when dashboard is not running.
        """
        # Arrange — state is already None from autouse fixture

        # Act
        result = dashboard.get_dashboard_url()

        # Assert
        assert result is None

    def test_get_dashboard_url_when_port_is_set(self) -> None:
        """get_dashboard_url() returns correct URL when _dashboard_port is set.

        Tests: Public accessor returns formatted URL string.
        How: Set _dashboard_port to a known value, call accessor.
        Why: MCP tool needs the correct URL to open in the browser.
        """
        # Arrange
        dashboard._dashboard_port = 49152

        # Act
        result = dashboard.get_dashboard_url()

        # Assert
        assert result == "http://localhost:49152/"


# ===================================================================
# Unit Tests: HealthHandler
# ===================================================================


class TestHealthHandler:
    """Tests for HealthHandler Tornado RequestHandler.

    Uses mock-based testing — constructs HealthHandler instances with
    lambda accessors and calls get() directly.  No real Tornado event
    loop or HTTP server is started.
    """

    def _make_handler(
        self,
        *,
        port: int | None = 8080,
        start_time: float | None = None,
        csv_path: Path | None = None,
        csv_rows: int | None = None,
    ) -> dashboard.HealthHandler:
        """Create a HealthHandler with given state accessors.

        Returns an initialised handler instance ready for get() calls.
        """
        handler = dashboard.HealthHandler.__new__(dashboard.HealthHandler)
        # Initialise the stub base class attributes
        handler._headers = {}
        handler._body = ""
        # Call initialize with lambda accessors
        handler.initialize(
            get_port=lambda: port,
            get_start_time=lambda: start_time,
            get_csv_path=lambda: csv_path,
            get_csv_rows=lambda: csv_rows,
        )
        return handler

    def test_health_handler_get_with_all_state(self, tmp_path: Path) -> None:
        """HealthHandler.get() returns 200 with all 7 JSON fields populated.

        Tests: Health endpoint returns complete JSON response.
        How: Create handler with all state set, including an existing CSV file.
        Why: Monitoring tools rely on all fields being present.
        """
        # Arrange
        csv_file = tmp_path / "sentiment.csv"
        csv_file.write_text("header\nrow1\n", encoding="utf-8")
        start_time = time.monotonic() - 10.0
        handler = self._make_handler(port=49152, start_time=start_time, csv_path=csv_file, csv_rows=42)

        # Act
        handler.get()

        # Assert
        assert handler._headers["Content-Type"] == "application/json"
        body = json.loads(handler._body)
        assert body["status"] == "ok"
        assert body["port"] == 49152
        assert body["pid"] == os.getpid()
        assert body["csv_path"] == str(csv_file)
        assert body["csv_exists"] is True
        assert body["csv_rows"] == 42
        assert body["uptime_seconds"] > 0

        # Verify all 7 fields are present
        expected_fields = {"status", "port", "pid", "csv_path", "csv_exists", "csv_rows", "uptime_seconds"}
        assert set(body.keys()) == expected_fields

    def test_health_handler_get_csv_missing(self, tmp_path: Path) -> None:
        """HealthHandler.get() returns 200 with csv_exists=false, csv_rows=null when CSV is missing.

        Tests: Health endpoint handles missing CSV gracefully.
        How: Point csv_path to a non-existent file, set csv_rows to None.
        Why: Dashboard is healthy even if CSV data has not been generated yet.
        """
        # Arrange
        missing_csv = tmp_path / "nonexistent.csv"
        handler = self._make_handler(port=49152, start_time=time.monotonic(), csv_path=missing_csv, csv_rows=None)

        # Act
        handler.get()

        # Assert
        body = json.loads(handler._body)
        assert body["status"] == "ok"
        assert body["csv_exists"] is False
        assert body["csv_rows"] is None

    def test_health_handler_uptime_calculation(self) -> None:
        """HealthHandler.get() returns positive uptime_seconds.

        Tests: Uptime is calculated as monotonic delta.
        How: Set start_time to a past monotonic value, verify uptime > 0.
        Why: Uptime must reflect actual dashboard running time.
        """
        # Arrange
        past_time = time.monotonic() - 5.0
        handler = self._make_handler(port=8080, start_time=past_time, csv_path=None, csv_rows=None)

        # Act
        handler.get()

        # Assert
        body = json.loads(handler._body)
        assert body["uptime_seconds"] >= 4.0
        assert body["uptime_seconds"] < 60.0  # Sanity upper bound


# ===================================================================
# Unit Tests: _reset_dashboard_state()
# ===================================================================


class TestResetDashboardState:
    """Tests for _reset_dashboard_state() state cleanup."""

    def test_reset_dashboard_state(self) -> None:
        """_reset_dashboard_state() sets all 4 module-level variables to None.

        Tests: State reset function clears all dashboard state.
        How: Set all state variables to non-None values, call reset, verify all None.
        Why: After dashboard crash, state must be clean so get_dashboard_url() returns None.
        """
        # Arrange
        dashboard._dashboard_port = 12345
        dashboard._dashboard_start_time = 1000.0
        dashboard._dashboard_csv_path = Path("/tmp/test.csv")
        dashboard._dashboard_csv_rows = 100

        # Act
        dashboard._reset_dashboard_state()

        # Assert
        assert dashboard._dashboard_port is None
        assert dashboard._dashboard_start_time is None
        assert dashboard._dashboard_csv_path is None
        assert dashboard._dashboard_csv_rows is None


# ===================================================================
# Unit Tests: _allocate_port()
# ===================================================================


class TestAllocatePort:
    """Tests for _allocate_port() OS port allocation."""

    def test_allocate_port_returns_valid_port(self) -> None:
        """_allocate_port() returns a port > 0 and < 65536.

        Tests: Port allocation returns a valid ephemeral port.
        How: Call _allocate_port() and verify the returned value is in range.
        Why: Port must be a valid TCP port number for pn.serve() to bind.
        """
        # Arrange — no setup needed

        # Act
        port = dashboard._allocate_port()

        # Assert
        assert isinstance(port, int)
        assert port > 0
        assert port < 65536


# ===================================================================
# Integration Tests: start_dashboard()
# ===================================================================


class TestStartDashboard:
    """Integration tests for start_dashboard() orchestration.

    All tests mock pn.serve and threading.Thread.start to avoid
    starting a real Panel/Bokeh server.  Module-level state is
    verified after each call.
    """

    @patch.object(dashboard.threading.Thread, "start")
    @patch.object(dashboard, "_allocate_port", return_value=55555)
    def test_start_dashboard_called_once(
        self, mock_allocate: MagicMock, mock_thread_start: MagicMock, tmp_path: Path
    ) -> None:
        """start_dashboard() sets module state, returns thread, thread is daemon.

        Tests: First call to start_dashboard sets up everything correctly.
        How: Mock port allocation and thread start, call start_dashboard().
        Why: Module state must be set before thread starts so get_dashboard_url()
             returns a valid URL immediately.
        """
        # Arrange
        csv_file = tmp_path / "sentiment.csv"
        csv_file.write_text(
            "session_id,timestamp,message_index,compound,positive,negative,neutral,message_length,message_preview\n",
            encoding="utf-8",
        )

        # Act
        result = dashboard.start_dashboard(csv_path=csv_file)

        # Assert
        assert result is not None
        assert isinstance(result, dashboard.threading.Thread)
        assert result.daemon is True
        assert result.name == "kaizen-dashboard"
        assert dashboard._dashboard_port == 55555
        assert dashboard._dashboard_start_time is not None
        assert dashboard._dashboard_csv_path == csv_file
        mock_allocate.assert_called_once()
        mock_thread_start.assert_called_once()

    @patch.object(dashboard.threading.Thread, "start")
    @patch.object(dashboard, "_allocate_port", return_value=55555)
    def test_start_dashboard_called_twice(self, mock_allocate: MagicMock, mock_thread_start: MagicMock) -> None:
        """Second call to start_dashboard() returns None, no new thread started.

        Tests: Within-process guard prevents duplicate dashboard instances.
        How: Call start_dashboard() twice, verify second returns None.
        Why: Each process should have at most one dashboard instance.
        """
        # Arrange — first call
        first_result = dashboard.start_dashboard()
        assert first_result is not None

        # Act — second call
        second_result = dashboard.start_dashboard()

        # Assert
        assert second_result is None
        # _allocate_port should only be called once (first invocation)
        mock_allocate.assert_called_once()

    @patch.object(dashboard, "_allocate_port", side_effect=OSError("bind failed"))
    def test_start_dashboard_port_allocation_failure(self, mock_allocate: MagicMock) -> None:
        """start_dashboard() returns None on OSError from _allocate_port().

        Tests: Port allocation failure is handled gracefully.
        How: Mock _allocate_port to raise OSError, verify None return.
        Why: Network issues should not crash the MCP server process.
        """
        # Arrange — mock already set up via decorator

        # Act
        result = dashboard.start_dashboard()

        # Assert
        assert result is None
        assert dashboard._dashboard_port is None
        assert dashboard._dashboard_start_time is None
        assert dashboard._dashboard_csv_path is None
        assert dashboard._dashboard_csv_rows is None


# ===================================================================
# Unit Tests: Thread Safety — _state_lock acquisition
# ===================================================================


class TestStateLock:
    """Tests for _state_lock thread-safety coverage.

    Strategy:
        Patch ``dashboard._state_lock`` with a MagicMock configured to
        behave as a context manager.  This allows asserting that
        ``__enter__`` / ``__exit__`` are called at each lock acquisition
        site without altering control flow.

        Tests for ``_serve()`` (a closure inside ``start_dashboard()``)
        capture the ``target`` callable by patching ``threading.Thread``
        and then invoke it directly in the test thread so the lock
        assertions remain synchronous and deterministic.

        Tests for ``_refresh()`` (a closure inside ``_create_app()``)
        extract the callback via the ``pn.state.onload`` / ``pn.state
        .add_periodic_callback`` mock-capture chain.
    """

    def test_state_lock_exists(self) -> None:
        """dashboard._state_lock is a threading.Lock instance.

        Tests: Module-level lock is present and correctly typed.
        How: Access dashboard._state_lock and check its type.
        Why: All thread-safety guarantees depend on this lock existing.
        """
        # Arrange — lock is declared at module level

        # Act / Assert
        assert isinstance(dashboard._state_lock, type(dashboard.threading.Lock()))

    def test_get_dashboard_url_acquires_lock(self) -> None:
        """get_dashboard_url() acquires _state_lock when reading _dashboard_port.

        Tests: Public URL accessor holds the lock during port read.
        How: Patch _state_lock as a context-manager mock, set _dashboard_port
             to a known value, call get_dashboard_url(), assert __enter__ called.
        Why: Cross-thread reads of _dashboard_port must be serialised by the
             lock to prevent observing a partially-reset state.
        """
        # Arrange
        dashboard._dashboard_port = 49152
        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)

        with patch.object(dashboard, "_state_lock", mock_lock):
            # Act
            result = dashboard.get_dashboard_url()

        # Assert — lock was acquired (context manager entered)
        mock_lock.__enter__.assert_called_once()
        mock_lock.__exit__.assert_called_once()
        assert result == "http://localhost:49152/"

    def test_reset_dashboard_state_acquires_lock(self) -> None:
        """_reset_dashboard_state() acquires _state_lock around all four null writes.

        Tests: State reset function holds the lock while clearing state.
        How: Patch _state_lock as a mock, call _reset_dashboard_state(),
             verify __enter__/__exit__ called, confirm all four vars are None.
        Why: _reset_dashboard_state() runs from the dashboard daemon thread
             on crash; the MCP server thread may concurrently read state.
        """
        # Arrange
        dashboard._dashboard_port = 12345
        dashboard._dashboard_start_time = 9999.0
        dashboard._dashboard_csv_path = Path("/tmp/fake.csv")
        dashboard._dashboard_csv_rows = 7

        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)

        with patch.object(dashboard, "_state_lock", mock_lock):
            # Act
            dashboard._reset_dashboard_state()

        # Assert — lock was acquired exactly once (single with block)
        mock_lock.__enter__.assert_called_once()
        mock_lock.__exit__.assert_called_once()
        # All state cleared
        assert dashboard._dashboard_port is None
        assert dashboard._dashboard_start_time is None
        assert dashboard._dashboard_csv_path is None
        assert dashboard._dashboard_csv_rows is None

    @patch.object(dashboard.threading.Thread, "start")
    @patch.object(dashboard, "_allocate_port", return_value=44444)
    def test_start_dashboard_guard_acquires_lock(self, mock_allocate: MagicMock, mock_thread_start: MagicMock) -> None:
        """start_dashboard() acquires _state_lock for the within-process guard check.

        Tests: Guard-path lock acquisition in start_dashboard().
        How: Set _dashboard_port to simulate a running dashboard, patch
             _state_lock, call start_dashboard(), assert lock __enter__ called.
        Why: The guard check reads _dashboard_port — that read must be inside
             the lock to prevent a TOCTOU race with _reset_dashboard_state().
        """
        # Arrange — simulate dashboard already running
        dashboard._dashboard_port = 44444

        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)

        with patch.object(dashboard, "_state_lock", mock_lock):
            # Act — guard triggers (port is set), returns None
            result = dashboard.start_dashboard()

        # Assert — guard path acquires lock
        assert result is None
        mock_lock.__enter__.assert_called()

    @patch.object(dashboard.threading.Thread, "start")
    @patch.object(dashboard, "_allocate_port", return_value=55566)
    def test_start_dashboard_write_acquires_lock(self, mock_allocate: MagicMock, mock_thread_start: MagicMock) -> None:
        """start_dashboard() acquires _state_lock when writing the four state variables.

        Tests: State write block in start_dashboard() holds the lock.
        How: First call (no running dashboard), patch _state_lock, call
             start_dashboard(), assert lock __enter__ called.
        Why: The four-variable state write must be atomic — no other thread
             should observe a partially initialised state.
        """
        # Arrange — no dashboard running (state reset by autouse fixture)
        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)

        with patch.object(dashboard, "_state_lock", mock_lock):
            # Act
            result = dashboard.start_dashboard()

        # Assert — lock entered at least twice: guard check + state write
        assert result is not None
        assert mock_lock.__enter__.call_count >= 2

    def test_health_handler_no_lock(self, tmp_path: Path) -> None:
        """HealthHandler.get() succeeds without acquiring _state_lock.

        Tests: Health endpoint is intentionally lock-free (IOLoop safety).
        How: Create a HealthHandler with lambda accessors (no module-level
             names), call get(), verify it returns correct JSON without
             touching _state_lock.
        Why: HealthHandler.get() runs on the Tornado IOLoop thread.
             Acquiring the lock there would risk deadlock with
             _reset_dashboard_state() called from the MCP server thread
             after the IOLoop has stopped.  The lambda-accessor pattern
             makes locking unnecessary here.
        """
        # Arrange — build handler using explicit lambda accessors
        csv_file = tmp_path / "s.csv"
        csv_file.write_text("h\nrow\n", encoding="utf-8")
        handler = dashboard.HealthHandler.__new__(dashboard.HealthHandler)
        handler._headers = {}
        handler._body = ""
        handler.initialize(
            get_port=lambda: 7777, get_start_time=lambda: None, get_csv_path=lambda: csv_file, get_csv_rows=lambda: 1
        )

        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)

        with patch.object(dashboard, "_state_lock", mock_lock):
            # Act
            handler.get()

        # Assert — lock was never touched
        mock_lock.__enter__.assert_not_called()
        mock_lock.__exit__.assert_not_called()
        # Response is correct
        body = json.loads(handler._body)
        assert body["status"] == "ok"
        assert body["port"] == 7777

    def test_pn_serve_called_with_threaded_true(self) -> None:
        """pn.serve() is called with threaded=True inside _serve().

        Tests: Track B — threaded=True kwarg is passed to pn.serve.
        How: Patch dashboard.threading.Thread with a MagicMock to capture
             the _serve target callable without starting a real thread.
             Call the captured target directly with a mock pn.serve that
             returns a mock thread.  Verify threaded=True appears in the
             pn.serve call kwargs.
        Why: threaded=True is the critical change that prevents Tornado's
             IOLoop from blocking the daemon thread and hanging MCP operations.
        """
        # Arrange — replace Thread class entirely so Thread(target=...) is captured
        mock_thread_instance = MagicMock()
        mock_thread_class = MagicMock(return_value=mock_thread_instance)

        mock_panel_thread = MagicMock()
        mock_panel_thread.join = MagicMock(return_value=None)
        _pn_mod.serve.return_value = mock_panel_thread
        _pn_mod.serve.reset_mock()

        with (
            patch.object(dashboard, "_allocate_port", return_value=56789),
            patch.object(dashboard.threading, "Thread", mock_thread_class),
        ):
            dashboard.start_dashboard()

        # Extract _serve from the Thread constructor call kwargs
        assert mock_thread_class.called, "threading.Thread was not constructed"
        _, ctor_kwargs = mock_thread_class.call_args
        serve_fn = ctor_kwargs.get("target")
        assert serve_fn is not None, "_serve target was not captured from Thread(...)"

        # Act — invoke _serve directly in the test thread
        serve_fn()

        # Assert — pn.serve received threaded=True
        assert _pn_mod.serve.called
        _, call_kwargs = _pn_mod.serve.call_args
        assert call_kwargs.get("threaded") is True

    def test_refresh_write_inside_lock(self, tmp_path: Path) -> None:
        """_refresh() acquires _state_lock when writing _dashboard_csv_rows.

        Tests: Periodic CSV-refresh callback holds the lock during state write.
        How: Call _create_app() to materialise the _refresh closure, extract
             it via the pn.state mock-capture chain.  Mock _load_sentiment_data
             to avoid hvplot chart-builder calls.  Force a mtime change so the
             update branch fires.  Patch _state_lock and assert __enter__ called.
        Why: _refresh() runs on the Tornado IOLoop thread and writes module-
             level state that get_dashboard_url() reads on the MCP thread.
        """
        # Arrange — any Path will do; mock _load_sentiment_data so _build_dashboard
        # takes the placeholder path (no hvplot chart builders needed).
        csv_file = tmp_path / "sentiment.csv"
        csv_file.write_text("", encoding="utf-8")

        # Reset state mocks before calling _create_app
        _pn_state.onload.reset_mock()
        _pn_state.add_periodic_callback.reset_mock()

        with patch.object(dashboard, "_load_sentiment_data", return_value=None):
            # Build the app — registers _register_periodic via pn.state.onload
            dashboard._create_app(csv_file)

        # Extract _register_periodic from onload mock
        assert _pn_state.onload.called, "pn.state.onload was not called by _create_app"
        register_periodic_fn = _pn_state.onload.call_args[0][0]

        # Call _register_periodic to register _refresh via add_periodic_callback
        register_periodic_fn()
        assert _pn_state.add_periodic_callback.called, "pn.state.add_periodic_callback was not called"
        refresh_fn = _pn_state.add_periodic_callback.call_args[0][0]

        # _initial_load() already called _refresh() once, which set state["last_mtime"]
        # to csv_file's current mtime.  Advance the mtime so the next _refresh()
        # call sees a change and the update branch (with _state_lock) fires.
        future_time = time.time() + 100
        os.utime(csv_file, (future_time, future_time))

        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(dashboard, "_load_sentiment_data", return_value=None),
            patch.object(dashboard, "_build_dashboard", return_value=MagicMock()),
            patch.object(dashboard, "_state_lock", mock_lock),
        ):
            # Act — real mtime != 0.0 so the update branch fires
            refresh_fn()

        # Assert — lock was acquired for the _dashboard_csv_rows write
        mock_lock.__enter__.assert_called()
        mock_lock.__exit__.assert_called()

    def test_no_deadlock_concurrent_reset_and_get_url(self) -> None:
        """Concurrent _reset_dashboard_state() and get_dashboard_url() do not deadlock.

        Tests: No deadlock under concurrent lock contention between two threads.
        How: Launch two threads — one calls _reset_dashboard_state() 50 times,
             another calls get_dashboard_url() 50 times.  Join both with a
             5-second timeout.  Assert both threads completed.
        Why: The coarse lock serialises all state access.  If acquisition order
             or lock re-entrancy were incorrect, this test would hang.
        """
        import threading as stdlib_threading

        errors: list[Exception] = []

        def reset_loop() -> None:
            for _ in range(50):
                try:
                    dashboard._reset_dashboard_state()
                except RuntimeError as exc:
                    errors.append(exc)

        def url_loop() -> None:
            for _ in range(50):
                try:
                    dashboard.get_dashboard_url()
                except RuntimeError as exc:
                    errors.append(exc)

        t1 = stdlib_threading.Thread(target=reset_loop)
        t2 = stdlib_threading.Thread(target=url_loop)

        # Act
        t1.start()
        t2.start()
        t1.join(timeout=5.0)
        t2.join(timeout=5.0)

        # Assert — both threads completed within 5 s (no deadlock)
        assert not t1.is_alive(), "reset thread did not complete — possible deadlock"
        assert not t2.is_alive(), "get_url thread did not complete — possible deadlock"
        assert not errors, f"Exceptions raised in concurrent threads: {errors}"


# ===================================================================
# Unit Tests: _serve() behaviour — threaded=True and state reset
# ===================================================================


class TestServeBehaviour:
    """Tests for _serve() closure behaviour after T2 changes.

    Strategy:
        ``_serve`` is a closure defined inside ``start_dashboard()``.  It
        cannot be imported directly.  Tests capture it by patching
        ``threading.Thread.__init__`` to intercept the ``target`` kwarg
        without starting a real OS thread, then invoke the captured
        callable directly in the test thread.
    """

    def _capture_serve_fn(self) -> tuple[Any, MagicMock]:
        """Helper: call start_dashboard() with Thread patched; return (_serve, mock_pn_serve).

        Replaces ``dashboard.threading.Thread`` with a MagicMock to intercept
        the constructor call and extract the ``target`` kwarg without starting a
        real OS thread.

        Returns:
            Tuple of (serve_callable, mock_pn_serve) where serve_callable
            is the ``_serve`` closure and mock_pn_serve is the patched
            ``dashboard.pn.serve`` MagicMock.
        """
        mock_thread_instance = MagicMock()
        mock_thread_class = MagicMock(return_value=mock_thread_instance)

        with (
            patch.object(dashboard, "_allocate_port", return_value=60001),
            patch.object(dashboard.threading, "Thread", mock_thread_class),
        ):
            dashboard.start_dashboard()

        assert mock_thread_class.called, "threading.Thread was not constructed"
        _, ctor_kwargs = mock_thread_class.call_args
        serve_fn = ctor_kwargs.get("target")
        assert serve_fn is not None, "_serve target was not captured from Thread(...)"
        return serve_fn, _pn_mod.serve

    def test_serve_resets_state_after_panel_thread_exits(self) -> None:
        """_serve() calls _reset_dashboard_state() in the else clause after join().

        Tests: Track B — post-exit state reset via else clause.
        How: Capture _serve closure, mock pn.serve to return a mock thread
             whose join() returns immediately (Panel thread exited normally),
             call _serve(), assert all four state variables are None.
        Why: When the Panel thread exits cleanly, state must be cleared so
             get_dashboard_url() returns None and the MCP tool reports no
             running server.
        """
        # Arrange
        serve_fn, mock_pn_serve = self._capture_serve_fn()

        mock_panel_thread = MagicMock()
        mock_panel_thread.join = MagicMock(return_value=None)
        mock_pn_serve.reset_mock()
        mock_pn_serve.return_value = mock_panel_thread

        # Pre-condition: state is set (simulating running dashboard)
        dashboard._dashboard_port = 60001
        dashboard._dashboard_start_time = 1.0
        dashboard._dashboard_csv_path = Path("/tmp/s.csv")
        dashboard._dashboard_csv_rows = 3

        # Act
        serve_fn()

        # Assert — else clause fired and reset state
        assert dashboard._dashboard_port is None
        assert dashboard._dashboard_start_time is None
        assert dashboard._dashboard_csv_path is None
        assert dashboard._dashboard_csv_rows is None
        mock_panel_thread.join.assert_called_once()

    def test_serve_resets_state_on_oserror(self) -> None:
        """_serve() calls _reset_dashboard_state() when pn.serve raises OSError.

        Tests: Track B — except OSError handler clears state on startup failure.
        How: Capture _serve closure, mock pn.serve to raise OSError, call
             _serve(), assert all four state variables are None.
        Why: A port-in-use error must clear state so the MCP server does not
             report a stale URL pointing to a dead server.
        """
        # Arrange
        serve_fn, mock_pn_serve = self._capture_serve_fn()

        mock_pn_serve.reset_mock()
        mock_pn_serve.side_effect = OSError("port in use")

        # Pre-condition: state is set
        dashboard._dashboard_port = 60001
        dashboard._dashboard_start_time = 1.0
        dashboard._dashboard_csv_path = Path("/tmp/s.csv")
        dashboard._dashboard_csv_rows = 5

        # Act
        serve_fn()

        # Assert — except OSError handler fired and reset state
        assert dashboard._dashboard_port is None
        assert dashboard._dashboard_start_time is None
        assert dashboard._dashboard_csv_path is None
        assert dashboard._dashboard_csv_rows is None
