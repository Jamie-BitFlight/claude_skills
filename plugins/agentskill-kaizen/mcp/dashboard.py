"""Panel (HoloViz) dashboard for sentiment analysis visualization.

Provides an interactive web dashboard that visualizes VADER sentiment
scores produced by the ``sentiment-score.py`` script. The dashboard
runs as a daemon thread inside the MCP server process and auto-refreshes
when the source CSV changes.

Dashboard views:
    Session Timeline - Compound score per message over time, colored by session.
    Session Heatmap  - Per-session message indices colored by compound score.
    Distribution     - Histogram of compound scores with mean/median lines.
    Hot Spots        - Table of the most negative messages (compound < -0.5).
"""

from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import holoviews as hv
import hvplot.pandas  # noqa: F401
import pandas as pd
import panel as pn
import tornado.web

if TYPE_CHECKING:
    from collections.abc import Callable

    from panel.io.server import StoppableThread


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CSV_COLUMNS: list[str] = [
    "session_id",
    "timestamp",
    "message_index",
    "compound",
    "positive",
    "negative",
    "neutral",
    "message_length",
    "message_preview",
]
_HOTSPOT_THRESHOLD: float = -0.5
_REFRESH_INTERVAL_MS: int = 5000
_SCORE_MIN: float = -1.0
_SCORE_MAX: float = 1.0
_HISTOGRAM_BINS: int = 30

# ---------------------------------------------------------------------------
# Module-level state — written by start_dashboard(), read by HealthHandler
# ---------------------------------------------------------------------------

_dashboard_port: int | None = None
_dashboard_start_time: float | None = None
_dashboard_csv_path: Path | None = None
_dashboard_csv_rows: int | None = None

# Coarse lock protecting all four state variables above.  Acquired by:
#   - start_dashboard()  — guard check (read) and state write block (write)
#   - _reset_dashboard_state() — four null assignments (write)
#   - get_dashboard_url()  — _dashboard_port read (read)
#   - _refresh()           — _dashboard_csv_rows write (write)
# NOT acquired by HealthHandler.get() — see comment at health_state_kwargs.
_state_lock: threading.Lock = threading.Lock()

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _load_sentiment_data(csv_path: Path) -> pd.DataFrame | None:
    """Load sentiment CSV into a DataFrame, returning None if unavailable.

    Parses the ``timestamp`` column as datetime and coerces numeric columns.
    Returns ``None`` when the file does not exist or is empty.

    Args:
        csv_path: Absolute path to the sentiment CSV file.

    Returns:
        A DataFrame with parsed columns, or ``None`` if the file is missing
        or contains no data rows.
    """
    if not csv_path.exists():
        return None

    try:
        df = pd.read_csv(csv_path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return None

    if df.empty:
        return None

    # Coerce types
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ("compound", "positive", "negative", "neutral"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["message_index"] = pd.to_numeric(df["message_index"], errors="coerce").astype("Int64")
    df["message_length"] = pd.to_numeric(df["message_length"], errors="coerce").astype("Int64")

    # Drop rows where critical columns are NaN
    df = df.dropna(subset=["compound", "session_id"])
    return df if not df.empty else None


# ---------------------------------------------------------------------------
# Dashboard views
# ---------------------------------------------------------------------------


def _build_placeholder(csv_path: Path) -> pn.pane.Markdown:
    """Build a placeholder pane shown when sentiment data is unavailable.

    Args:
        csv_path: The path where the CSV is expected.

    Returns:
        A Markdown pane with instructions for the user.
    """
    return pn.pane.Markdown(
        f"""
## No Sentiment Data Available

The sentiment CSV was not found at:

```
{csv_path}
```

**To generate it**, run the sentiment scoring script:

```bash
uv run scripts/sentiment-score.py --output {csv_path}
```

The dashboard will automatically pick up the data once the file exists.
""",
        sizing_mode="stretch_width",
    )


_ROLLING_WINDOW: int = 50


def _build_timeline(df: pd.DataFrame) -> pn.pane.HoloViews:
    """Build the Session Timeline with a smoothed trend line overlay.

    Renders two layers on a shared x-axis (message_index, integer sequence):

    * **Background scatter** — all raw compound scores at low opacity so
      individual outliers remain visible without dominating the chart.
    * **Trend line** — rolling mean of compound score (window=50 messages)
      drawn in steelblue.  Message-order-based windowing (not time-based)
      ensures the rolling window is uniform regardless of session density.

    A dashed red zero-reference line marks the neutral boundary.

    Args:
        df: Sentiment DataFrame with columns ``session_id``, ``timestamp``,
            ``message_index``, ``compound``, and ``message_preview``.

    Returns:
        A HoloViews pane containing the interactive composite plot.
    """
    # Sort by message_index for correct temporal ordering and rolling window
    plot_df = df.copy()
    plot_df = plot_df.sort_values("message_index").reset_index(drop=True)
    plot_df["preview"] = plot_df["message_preview"]

    # Compute rolling mean on the sorted sequence
    plot_df["rolling_mean"] = plot_df["compound"].rolling(window=_ROLLING_WINDOW, min_periods=1, center=True).mean()

    # Background scatter — faded gray context dots, no colorbar, no legend
    scatter = plot_df.hvplot.scatter(
        x="message_index",
        y="compound",
        color="gray",
        alpha=0.15,
        size=4,
        hover_cols=["session_id", "preview", "timestamp"],
        title="Sentiment Trend (rolling mean, window=50)",
        xlabel="Message Index",
        ylabel="Compound Score",
        ylim=(_SCORE_MIN, _SCORE_MAX),
        height=450,
        responsive=True,
        colorbar=False,
        legend=False,
    )

    # Trend line — rolling mean in steelblue, solid, no colorbar
    trend = plot_df.hvplot.line(
        x="message_index", y="rolling_mean", color="steelblue", line_width=2, hover=False, legend=False
    )

    # Zero reference line — dashed red at y=0
    zero_line = hv.HLine(0).opts(color="red", line_dash="dashed", line_width=1)

    return pn.pane.HoloViews(scatter * trend * zero_line, sizing_mode="stretch_width")


def _build_heatmap(df: pd.DataFrame) -> pn.pane.HoloViews:
    """Build the Session Heatmap.

    Creates a heatmap with one row per session and columns as message
    indices. Color intensity represents the compound sentiment score,
    making it easy to spot sessions with sentiment drops.

    Args:
        df: Sentiment DataFrame with columns ``session_id``,
            ``message_index``, and ``compound``.

    Returns:
        A HoloViews pane containing the heatmap.
    """
    # Shorten session IDs for display (last 8 chars), aggregate duplicates
    plot_df = df.copy()
    plot_df["session_short"] = plot_df["session_id"].str[-8:]
    plot_df = plot_df.groupby(["session_short", "message_index"], as_index=False)["compound"].mean()

    heatmap = plot_df.hvplot.heatmap(
        x="message_index",
        y="session_short",
        C="compound",
        cmap="RdYlGn",
        clim=(_SCORE_MIN, _SCORE_MAX),
        title="Sentiment by Session and Message Index",
        xlabel="Message Index",
        ylabel="Session (last 8 chars)",
        height=max(300, len(plot_df["session_short"].unique()) * 25 + 100),
        responsive=True,
        colorbar=True,
    )

    return pn.pane.HoloViews(heatmap, sizing_mode="stretch_width")


def _build_distribution(df: pd.DataFrame) -> pn.pane.HoloViews:
    """Build the compound score distribution histogram.

    Shows a histogram of all compound scores with vertical lines for
    the mean and median values.

    Args:
        df: Sentiment DataFrame with a ``compound`` column.

    Returns:
        A HoloViews pane containing the histogram with annotation lines.
    """
    hist = df.hvplot.hist(
        y="compound",
        bins=_HISTOGRAM_BINS,
        title="Distribution of Compound Sentiment Scores",
        xlabel="Compound Score",
        ylabel="Count",
        color="#4c78a8",
        height=400,
        responsive=True,
    )

    mean_val = float(df["compound"].mean())
    median_val = float(df["compound"].median())

    mean_line = hv.VLine(mean_val).opts(color="red", line_dash="dashed", line_width=2)
    median_line = hv.VLine(median_val).opts(color="orange", line_dash="dotted", line_width=2)

    # Labels for the lines
    mean_label = hv.Text(mean_val, 0, f"Mean: {mean_val:.3f}", halign="left", fontsize=9).opts(color="red")
    median_label = hv.Text(median_val, 0, f"Median: {median_val:.3f}", halign="right", fontsize=9).opts(color="orange")

    overlay = hist * mean_line * median_line * mean_label * median_label
    return pn.pane.HoloViews(overlay, sizing_mode="stretch_width")


def _build_hotspots(df: pd.DataFrame) -> pn.pane.Markdown | pn.Column:
    """Build the Hot Spots table of most negative messages.

    Filters messages with compound score below the threshold and displays
    them sorted by compound ascending (most negative first).

    Args:
        df: Sentiment DataFrame.

    Returns:
        A Markdown pane with an informational message when no hot spots are
        found, or a Column containing a Tabulator widget showing the hot spot
        messages sorted most-negative first. The Column carries an explicit
        ``height=500`` anchor so Panel can compute stretch sizing correctly
        even when the tab is first activated from a hidden state.
    """
    hotspots = (
        df
        .loc[df["compound"] < _HOTSPOT_THRESHOLD, ["session_id", "timestamp", "compound", "message_preview"]]
        .sort_values("compound", ascending=True)
        .reset_index(drop=True)
    )

    if hotspots.empty:
        return pn.pane.Markdown(
            f"**No hot spots found.** All messages have compound scores >= {_HOTSPOT_THRESHOLD}.",
            sizing_mode="stretch_width",
        )

    # Format compound for display
    hotspots["compound"] = hotspots["compound"].round(4)

    table = pn.widgets.Tabulator(
        hotspots,
        sizing_mode="stretch_width",
        max_height=500,
        show_index=False,
        frozen_columns=["session_id"],
        text_align={"compound": "right"},
        titles={
            "session_id": "Session ID",
            "timestamp": "Timestamp",
            "compound": "Compound",
            "message_preview": "Message Preview",
        },
    )
    # Wrap in a Column with an explicit height to prevent layout miscalculation
    # when the tab is rendered for the first time (Panel cannot compute stretch
    # sizing on hidden containers without an anchor height).
    return pn.Column(table, sizing_mode="stretch_width", height=500)


# ---------------------------------------------------------------------------
# Dashboard assembly
# ---------------------------------------------------------------------------


def _build_dashboard(csv_path: Path, df: pd.DataFrame | None = None) -> pn.Tabs:
    """Assemble the full dashboard with all four views.

    Reads the CSV and builds each tab. If the CSV is missing, returns
    a placeholder tab with instructions.

    When called from ``_refresh()`` the pre-loaded *df* is passed in so
    the CSV is not read a second time.  When *df* is not provided (e.g.
    the initial build in ``_create_app()``), the function loads the data
    internally via ``_load_sentiment_data()``.

    Args:
        csv_path: Path to the sentiment CSV file.
        df: Optional pre-loaded sentiment DataFrame.  When ``None``
            (the default), data is loaded from *csv_path*.

    Returns:
        A Panel Tabs component containing all dashboard views.
    """
    if df is None:
        df = _load_sentiment_data(csv_path)

    if df is None:
        return pn.Tabs(("Overview", _build_placeholder(csv_path)))

    return pn.Tabs(
        ("Session Timeline", _build_timeline(df)),
        ("Session Heatmap", _build_heatmap(df)),
        ("Distribution", _build_distribution(df)),
        ("Hot Spots", _build_hotspots(df)),
    )


def _create_app(csv_path: Path) -> pn.template.FastListTemplate:
    """Create the Panel application with auto-refresh capability.

    Called by ``pn.serve`` as a factory function **after** the Tornado
    event loop is running, which allows ``pn.state.add_periodic_callback``
    to succeed. Calling this function eagerly (before ``pn.serve``) would
    raise ``RuntimeError: no running event loop``.

    Args:
        csv_path: Path to the sentiment CSV file.

    Returns:
        A Panel FastListTemplate ready to be served.
    """
    cast("Callable[..., Any]", hv.extension)("bokeh")
    pn.extension("tabulator")

    # Track file modification time for change detection
    state: dict[str, float] = {"last_mtime": 0.0}

    # Start with an empty container — data loads async via onload so the page
    # shell is delivered to the browser immediately without blocking on CSV I/O
    # and chart rendering.
    dashboard_container = pn.Column(
        pn.pane.Markdown("Loading…", sizing_mode="stretch_width"), sizing_mode="stretch_width"
    )

    def _refresh() -> None:
        """Check if the CSV has changed and rebuild the dashboard if so."""
        global _dashboard_csv_rows  # noqa: PLW0603
        try:
            current_mtime = csv_path.stat().st_mtime if csv_path.exists() else 0.0
        except OSError:
            current_mtime = 0.0

        if current_mtime != state["last_mtime"]:
            state["last_mtime"] = current_mtime
            df = _load_sentiment_data(csv_path)
            with _state_lock:
                _dashboard_csv_rows = len(df) if df is not None else None
            dashboard_container.objects = [_build_dashboard(csv_path, df)]

    def _initial_load() -> None:
        """Load data and register the periodic refresh after the page is served."""
        _refresh()
        pn.state.add_periodic_callback(_refresh, period=_REFRESH_INTERVAL_MS)

    # pn.state.onload runs after the Bokeh/Tornado event loop is active and
    # the page shell has been delivered to the browser.  Heavy CSV I/O and
    # chart rendering happen here, not during _create_app(), so the browser
    # receives the page structure immediately.
    pn.state.onload(_initial_load)

    return pn.template.FastListTemplate(
        title="Kaizen Sentiment Dashboard",
        main=[dashboard_container],
        accent="#4c78a8",
        main_layout=None,
        theme="default",
    )


# ---------------------------------------------------------------------------
# Port allocation and state management
# ---------------------------------------------------------------------------


def _allocate_port() -> int:
    """Allocate a free ephemeral port from the OS.

    Creates a TCP socket, sets ``SO_REUSEADDR``, binds to localhost on
    port 0 (OS picks a free port), reads the assigned port, and closes
    the socket.  The caller should pass the returned port to
    ``pn.serve(port=...)`` promptly to minimise the TOCTOU window.

    Returns:
        The OS-assigned port number.

    Raises:
        OSError: If the socket cannot be created or bound.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("localhost", 0))
        port: int = sock.getsockname()[1]
    finally:
        sock.close()
    return port


def _reset_dashboard_state() -> None:
    """Reset all module-level dashboard state variables to ``None``.

    Called from ``_serve()`` exception handlers when the dashboard
    fails to start or crashes, so that ``get_dashboard_url()`` returns
    ``None`` and the ``open_dashboard`` MCP tool reports the dashboard
    as not running.
    """
    global _dashboard_port, _dashboard_start_time, _dashboard_csv_path, _dashboard_csv_rows  # noqa: PLW0603
    with _state_lock:
        _dashboard_port = None
        _dashboard_start_time = None
        _dashboard_csv_path = None
        _dashboard_csv_rows = None


def get_dashboard_url() -> str | None:
    """Return the dashboard URL if the dashboard is running, else ``None``.

    This is the public accessor that ``server.py`` imports and calls
    from the ``open_dashboard`` MCP tool.

    Returns:
        The full URL string (e.g. ``"http://localhost:49152/"``) when
        ``_dashboard_port`` is set, or ``None`` when no dashboard is
        running in this process.
    """
    with _state_lock:
        port = _dashboard_port
    if port is not None:
        return f"http://localhost:{port}/"
    return None


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class HealthHandler(tornado.web.RequestHandler):
    """Tornado handler for the ``GET /health`` endpoint.

    Returns JSON with dashboard status, port, PID, CSV info, and uptime.
    Registered via ``pn.serve(..., extra_patterns=[("/health", HealthHandler, kwargs)])``.

    The handler receives lambda-based accessors for module-level state via
    ``initialize()`` kwargs, ensuring it always reads current values rather
    than stale copies captured at thread-start time.
    """

    _body: bytes
    _get_port: Callable[[], int | None]
    _get_start_time: Callable[[], float | None]
    _get_csv_path: Callable[[], Path | None]
    _get_csv_rows: Callable[[], int | None]

    def initialize(
        self,
        get_port: Callable[[], int | None],
        get_start_time: Callable[[], float | None],
        get_csv_path: Callable[[], Path | None],
        get_csv_rows: Callable[[], int | None],
    ) -> None:
        """Store accessor lambdas for module-level dashboard state.

        Args:
            get_port: Returns the current dashboard port or ``None``.
            get_start_time: Returns the monotonic start time or ``None``.
            get_csv_path: Returns the CSV path or ``None``.
            get_csv_rows: Returns the cached CSV row count or ``None``.
        """
        self._get_port = get_port
        self._get_start_time = get_start_time
        self._get_csv_path = get_csv_path
        self._get_csv_rows = get_csv_rows

    def get(self) -> None:
        """Handle ``GET /health`` — return JSON with dashboard status.

        Always returns HTTP 200 when the handler is reachable.  The
        ``csv_exists`` field uses a live ``Path.exists()`` check; all other
        fields are read from cached module-level state.
        """
        port = self._get_port()
        start_time = self._get_start_time()
        csv_path = self._get_csv_path()
        csv_rows = self._get_csv_rows()

        csv_path_obj = Path(csv_path) if csv_path is not None else None
        csv_exists = csv_path_obj.exists() if csv_path_obj is not None else False

        uptime = (time.monotonic() - start_time) if start_time is not None else 0.0

        response = {
            "status": "ok",
            "port": port,
            "pid": os.getpid(),
            "csv_path": str(csv_path) if csv_path is not None else None,
            "csv_exists": csv_exists,
            "csv_rows": csv_rows,
            "uptime_seconds": round(uptime, 2),
        }

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(response))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def start_dashboard(csv_path: Path | None = None) -> threading.Thread | None:
    """Start the Panel dashboard server in a daemon thread.

    Args:
        csv_path: Path to the sentiment CSV. Defaults to
            ``~/.claude/kaizen/sentiment.csv``.

    Returns:
        The daemon ``threading.Thread`` running the server, or ``None``
        if the dashboard could not be started.
    """
    global _dashboard_port, _dashboard_start_time, _dashboard_csv_path, _dashboard_csv_rows  # noqa: PLW0603

    with _state_lock:
        if _dashboard_port is not None:
            logger.info("Dashboard already running on http://localhost:%d/", _dashboard_port)
            return None

    resolved_path = (csv_path or Path("~/.claude/kaizen/sentiment.csv")).expanduser()

    try:
        port = _allocate_port()
    except OSError:
        logger.warning("Failed to allocate a port for the dashboard")
        return None

    # Pre-count CSV rows if the file exists (outside the lock — pure I/O).
    df = _load_sentiment_data(resolved_path)

    with _state_lock:
        _dashboard_port = port
        _dashboard_start_time = time.monotonic()
        _dashboard_csv_path = resolved_path
        _dashboard_csv_rows = len(df) if df is not None else None

    def _serve() -> None:
        """Target function for the daemon thread."""
        try:

            def _app_factory() -> pn.template.FastListTemplate:
                return _create_app(resolved_path)

            # HealthHandler.get() does NOT acquire _state_lock — intentionally.
            # All four lambdas below are called from Tornado's IOLoop thread,
            # which is the same thread that runs _refresh().  Because Tornado's
            # IOLoop is single-threaded, HealthHandler.get() and _refresh()
            # cannot interleave with each other.  The startup writes
            # (_dashboard_port, _dashboard_start_time, etc.) happen before
            # pn.serve() is called — before the IOLoop is even accepting
            # requests.  The crash-path writes in _reset_dashboard_state() happen
            # after the IOLoop has already stopped.  There is therefore no window
            # in which HealthHandler.get() can observe a partially-reset state.
            # Adding the lock here would be incorrect: _reset_dashboard_state()
            # can be called from the MCP server thread while the IOLoop thread
            # is still draining — the lock would not protect against that race
            # any better than the architectural guarantee above.
            health_state_kwargs = {
                "get_port": lambda: _dashboard_port,
                "get_start_time": lambda: _dashboard_start_time,
                "get_csv_path": lambda: _dashboard_csv_path,
                "get_csv_rows": lambda: _dashboard_csv_rows,
            }

            # pn.serve(threaded=True) starts Panel's Tornado IOLoop on a
            # StoppableThread and returns that thread immediately.  We join
            # it so _serve() — and therefore this daemon thread — blocks
            # until the Panel thread exits.  That makes the else clause
            # below a reliable post-exit cleanup point.
            #
            # StoppableThread inherits daemon status from its creator thread
            # (this daemon thread), so it is also a daemon thread — the
            # process will not be kept alive by it.
            panel_thread = cast(
                "StoppableThread",
                pn.serve(
                    {"/": _app_factory},
                    address="localhost",
                    port=port,
                    show=False,
                    start=True,
                    threaded=True,
                    verbose=False,
                    extra_patterns=[("/health", HealthHandler, health_state_kwargs)],
                ),
            )
            panel_thread.join()
        except OSError as exc:
            _reset_dashboard_state()
            logger.warning("Dashboard server failed to start: %s", exc)
        except Exception:
            _reset_dashboard_state()
            logger.exception("Unexpected error in dashboard server")
        else:
            # The Panel thread exited normally (stop() was called or the
            # IOLoop returned).  Reset state so get_dashboard_url() returns
            # None and the open_dashboard MCP tool reports no running server.
            _reset_dashboard_state()
            logger.info("Dashboard server stopped")

    thread = threading.Thread(target=_serve, name="kaizen-dashboard", daemon=True)
    thread.start()
    logger.info("Sentiment dashboard starting on http://localhost:%d/", port)
    return thread
