# Kaizen Dashboard -- View Specifications

Companion to [kaizen-dashboard-redesign-spec.md](./kaizen-dashboard-redesign-spec.md).

---

## Tab Structure

The dashboard uses `pn.Tabs` with `dynamic=True` (lazy loading). Five tabs replace the current four.

| Tab | Purpose | Primary Widget | Data Source |
|-----|---------|---------------|-------------|
| Findings | Browse detected anti-patterns | Tabulator + sidebar bar chart | `findings`, `finding_evidence` |
| Interventions | Visualize intervention flow | HoloViews Graph + Tabulator detail | `state_transitions`, `interventions` |
| Fix Tracker | Track fix effectiveness | Tabulator + line chart | `fixes`, `fix_measurements` |
| Sessions | Drill into individual sessions | Tabulator + timeline plot | `sessions`, `state_transitions` |
| Sentiment | Compact sentiment signal | Line plot + histogram | `sentiment` |

---

## Tab 1: Findings Browser

### Layout

```
+------------------------------------------------------------------+
| [Dimension Filter v] [Severity Filter v] [Status Filter v]       |
+------------------------------------------------------------------+
| Dimension Summary          | Findings Table (Tabulator)           |
| (stacked bar chart)        | finding_id | dim | sev | title |    |
| 10 bars, colored by        | freq | first_seen | last_seen |     |
| severity                   | recommendation | status | fix_status |
|                            |                                      |
| (width: 250px)             | (stretch_width)                      |
+----------------------------+--------------------------------------+
| Evidence Panel (below, shown when a finding row is selected)      |
| +--------------------------------------------------------------+ |
| | session_id | timestamp | tool | excerpt | context             | |
| +--------------------------------------------------------------+ |
+------------------------------------------------------------------+
```

### Components

**Filters** (top row):
- `pn.widgets.Select` for dimension (values from `FindingDimension` enum + "All")
- `pn.widgets.Select` for severity (critical / warning / info / All)
- `pn.widgets.Select` for status (open / fixed / wont_fix / duplicate / All)
- Filters are linked to the Tabulator via `pn.bind()` -- changing a filter re-queries via `KaizenDB.findings()`

**Dimension Summary** (left sidebar):
- `hvplot.bar` horizontal stacked bar chart
- X-axis: count of findings
- Y-axis: dimension names (10 bars)
- Color: severity (red=critical, orange=warning, blue=info)
- Clicking a bar sets the dimension filter
- Data from `KaizenDB.dimension_summary()`

**Findings Table** (main area):
- `pn.widgets.Tabulator` with `pagination='remote'`, `page_size=50`
- Columns: dimension, severity (color-coded cell background), title, frequency, first_seen, last_seen, recommendation, status, fix_status
- Sortable by all columns
- Row selection triggers evidence panel update
- `frozen_columns=["title"]`
- Severity column uses Tabulator formatters for color coding

**Evidence Panel** (bottom, conditional):
- `pn.widgets.Tabulator` showing `finding_evidence` rows for the selected finding
- Hidden when no finding is selected
- Columns: session_id (clickable -- navigates to Sessions tab), timestamp, tool_name, excerpt (wrapping enabled), context_summary

### Interactions

1. Select dimension/severity/status filter -> Tabulator re-queries `KaizenDB.findings(filter)`
2. Click a bar in Dimension Summary -> sets dimension filter
3. Click a Findings row -> Evidence Panel loads `KaizenDB.finding_evidence(finding_id)`
4. Click session_id in Evidence Panel -> switches to Sessions tab with that session selected

---

## Tab 2: Interventions (Intervention Flow)

### Layout

```
+------------------------------------------------------------------+
| [View Mode: v Aggregate | Per-Session]  [Session: v ...]          |
| [Finding Filter: v ...]  [Min Edge Weight: [slider]]              |
+------------------------------------------------------------------+
| Flow Graph (HoloViews Graph)                                      |
|                                                                    |
|   [Read] --success--> [Edit] --success--> [Bash]                  |
|     \                                        |                    |
|      \--intervention--> [user correction]    |--error-->          |
|                                              |                    |
| Nodes = action_tool, sized by frequency                           |
| Edges = transitions, colored by outcome                           |
|   green = success, red = intervention, orange = error             |
|                                                                    |
| (responsive, height=500)                                          |
+------------------------------------------------------------------+
| Intervention Detail (Tabulator, below graph)                      |
| type | trigger_preview | preceding_tool | outcome | context       |
+------------------------------------------------------------------+
| Intervention Rate (line chart, bottom)                            |
| X: session order, Y: rolling avg intervention count               |
+------------------------------------------------------------------+
```

### Components

**View Mode Toggle**:
- `pn.widgets.Select` with options: "Aggregate" (cross-session), "Per-Session"
- In Aggregate mode: nodes are tool names, edges are weighted by frequency across all sessions
- In Per-Session mode: session selector appears, graph shows one session's flow

**Session Selector** (visible in Per-Session mode):
- `pn.widgets.Select` populated from `KaizenDB.sessions()`
- Shows `{session_id[:8]} -- {project_name} -- {date}`

**Finding Filter**:
- `pn.widgets.Select` showing finding titles
- When selected, graph highlights transitions associated with that finding

**Min Edge Weight Slider** (Aggregate mode only):
- `pn.widgets.IntSlider(start=1, end=50, value=3)`
- Filters out low-frequency edges to reduce visual clutter

**Flow Graph**:
- `hv.Graph` with Bokeh renderer
- Nodes: `action_tool` values, sized proportional to frequency
- Node color: based on intervention rate (green = low, red = high)
- Edges: directed, colored by outcome (green=success, red=intervention, orange=error, gray=abandoned)
- Edge width: proportional to frequency (Aggregate) or constant (Per-Session)
- Hover tooltip on nodes: tool name, total uses, intervention count, intervention %
- Hover tooltip on edges: from->to, count, outcome breakdown
- Layout: hierarchical (left-to-right) using `hv.Graph` with explicit node positions calculated by topological sort

**Intervention Detail**:
- `pn.widgets.Tabulator` showing recent interventions
- Filtered by selected session or finding
- Columns: intervention_type, trigger_preview, preceding_tool, outcome, context_summary
- `max_height=300`

**Intervention Rate Chart**:
- `hvplot.line` showing rolling average intervention count per session over time
- X-axis: session order (chronological)
- Y-axis: rolling average (window=10 sessions)
- Horizontal reference line at overall mean
- Data from `KaizenDB.intervention_rate_over_time()`

---

## Tab 3: Fix Tracker

### Layout

```
+------------------------------------------------------------------+
| [Status Filter: v All | proposed | applied | verified | ...]      |
+------------------------------------------------------------------+
| Fixes Table (Tabulator)                                           |
| fix_type | title | finding_title | dimension | severity |         |
| applied_at | status | rate_before | rate_after | change_pct      |
+------------------------------------------------------------------+
| Fix Effectiveness Chart (shown when a fix row is selected)        |
|                                                                    |
| Line chart: measurement_date vs rate_change_pct                   |
| Horizontal line at 0% (no change)                                 |
| Green zone below 0 (improvement), red zone above (regression)     |
|                                                                    |
| (responsive, height=300)                                          |
+------------------------------------------------------------------+
```

### Components

**Status Filter**:
- `pn.widgets.Select` with FixStatus values + "All"

**Fixes Table**:
- `pn.widgets.Tabulator` with all fix records
- Columns: fix_type (icon), title, finding_title, dimension, severity, applied_at, status, rate_before, rate_after, rate_change_pct
- `rate_change_pct` column uses conditional formatting (green if negative, red if positive)
- Row selection triggers effectiveness chart update

**Fix Effectiveness Chart**:
- `hvplot.line` showing measurement history for the selected fix
- X-axis: measurement date
- Y-axis: rate_change_pct
- Green background band below 0% (improvement zone)
- Red background band above 0% (regression zone)
- Points at each measurement with hover showing window sizes and counts
- Dashed line at 0% (baseline)
- Hidden when no fix is selected

---

## Tab 4: Sessions (Session Explorer)

### Layout

```
+------------------------------------------------------------------+
| [Project Filter: v] [Date Range: from [__] to [__]]              |
| [Show only sessions with interventions: [ ]]                      |
+------------------------------------------------------------------+
| Sessions Table (Tabulator)                                        |
| session_id | project | date | turns | tools | errors |            |
| interventions | findings | model | branch                        |
+------------------------------------------------------------------+
| Session Timeline (shown when a session row is selected)           |
|                                                                    |
| Vertical sequence of state transitions:                           |
| [context] --> [action: tool_name] --> [outcome]                   |
|   |                                      |                        |
|   +-- intervention marker (if any) ------+                        |
|                                                                    |
| Rendered as annotated scatter/step plot                            |
| X: sequence_index, Y: categorical (context/action/outcome)       |
| Color: outcome (green/red/orange/gray)                            |
| Intervention markers: red diamond overlay                         |
|                                                                    |
| (responsive, height=400)                                          |
+------------------------------------------------------------------+
```

### Components

**Filters**:
- `pn.widgets.Select` for project_name (populated from distinct project names)
- `pn.widgets.DatePicker` for date range (from/to)
- `pn.widgets.Checkbox` for "Show only sessions with interventions"

**Sessions Table**:
- `pn.widgets.Tabulator` with `pagination='remote'`, `page_size=30`
- Columns: session_id (last 8 chars + slug), project_name, first_timestamp, total_turns, tool_call_count, error_count, intervention_count (color-coded), finding_count, model, git_branch
- Sortable by all columns
- intervention_count column: red background when > 0
- Row selection triggers timeline update

**Session Timeline**:
- Vertical step plot or annotated scatter
- X-axis: sequence_index (0, 1, 2, ...)
- Each step shows: context_type -> action_tool -> outcome
- Color coding: success=green dots, error=orange dots, intervention=red diamonds, abandoned=gray dots
- Hover tooltips show: context_summary, action_summary, outcome_detail
- Intervention markers are visually prominent (larger, different shape)
- Connected by lines showing flow direction
- Hidden when no session is selected

---

## Tab 5: Sentiment Signal

### Layout

```
+------------------------------------------------------------------+
| Sentiment Trend (rolling mean)                                    |
|                                                                    |
| Scatter (gray, alpha=0.15) + rolling mean line (steelblue)        |
| Zero reference line (red dashed)                                  |
| X: message_index, Y: compound score [-1, 1]                      |
|                                                                    |
| (responsive, height=350)                                          |
+------------------------------------------------------------------+
| Distribution (histogram)                                          |
|                                                                    |
| Histogram of compound scores with mean/median lines               |
| Same as current _build_distribution()                             |
|                                                                    |
| (responsive, height=250)                                          |
+------------------------------------------------------------------+
```

### Components

This tab is a compacted version of the current dashboard. Two views (trend + distribution) replace the current four (timeline, heatmap, distribution, hot spots). The heatmap and hot spots are subsumed by the Findings Browser and Session Explorer tabs.

**Sentiment Trend**:
- Same implementation as current `_build_timeline()` but reading from DuckDB `sentiment` table instead of CSV
- Scatter plot with rolling mean overlay
- Zero reference line

**Distribution**:
- Same implementation as current `_build_distribution()`
- Histogram with mean/median vertical lines

### Data Source Change

Current: `_load_sentiment_data(csv_path)` reads CSV and returns DataFrame.
New: `KaizenDB.sentiment()` queries DuckDB and returns DataFrame with identical columns.

---

## Dashboard Shell

### FastListTemplate Configuration

```python
pn.template.FastListTemplate(
    title="Kaizen Findings Dashboard",  # renamed from "Kaizen Sentiment Dashboard"
    main=[dashboard_container],
    accent="#4c78a8",
    main_layout=None,
    theme="default",
    header_background="#2c3e50",  # darker header for forensic tool feel
)
```

### Auto-Refresh

- Polling interval: 30 seconds (up from 5 seconds)
- Change detection: DuckDB table row counts instead of CSV mtime
- On change detected: rebuild active tab only (not all tabs)
- `pn.state.add_periodic_callback(_refresh, period=30000)`

### Health Endpoint Update

The `/health` endpoint response adds DuckDB status:

```json
{
    "status": "ok",
    "port": 49152,
    "pid": 12345,
    "db_path": "/home/user/.claude/kaizen/kaizen.duckdb",
    "db_exists": true,
    "table_counts": {
        "sessions": 487,
        "findings": 2103,
        "interventions": 3021,
        "fixes": 47,
        "sentiment": 98432
    },
    "last_ingested": "2026-03-12T14:30:00Z",
    "uptime_seconds": 3600.5
}
```

### Empty State Handling

When the database exists but contains no findings (first run before ingestion):

```
## No Findings Available

The kaizen database exists but contains no analysis findings yet.

**To populate it**, run the analysis and ingestion pipeline:

1. Run transcript analysis:
   ```
   [transcript-analyst agent instructions]
   ```

2. Run the ingestion script:
   ```bash
   uv run scripts/ingest-findings.py --db ~/.claude/kaizen/kaizen.duckdb
   ```

The dashboard will automatically pick up the data within 30 seconds.
```

When the database file does not exist at all:

```
## No Database Found

The kaizen database was not found at:
    ~/.claude/kaizen/kaizen.duckdb

**To create it**, run the sentiment scoring script:
    uv run scripts/sentiment-score.py

Then run the ingestion script:
    uv run scripts/ingest-findings.py
```

---

## Cross-Tab Navigation

Several interactions navigate between tabs:

| Source | Trigger | Target | State Passed |
|--------|---------|--------|-------------|
| Findings Browser | Click session_id in evidence | Sessions tab | session_id pre-selected |
| Findings Browser | Click finding with fix | Fix Tracker tab | fix_id pre-selected |
| Fix Tracker | Click finding_title | Findings tab | finding_id filter applied |
| Sessions | Click intervention count (>0) | Interventions tab | session_id filter, Per-Session mode |

Implementation: use `pn.state.location` or shared reactive values (`pn.rx()`) to communicate selection state between tabs.
