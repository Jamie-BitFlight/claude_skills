# Kaizen Dashboard Redesign -- Testing Architecture

Companion to [kaizen-dashboard-redesign-spec.md](./kaizen-dashboard-redesign-spec.md).

---

## Testing Stack

```text
pytest>=8.0.0
pytest-cov>=6.0.0
pytest-mock>=3.14.0
duckdb>=1.0.0           # in-memory database for test isolation
```

No `pytest-asyncio` needed -- the dashboard code is synchronous (Panel callbacks run in Tornado's IOLoop, but tests exercise the query/build functions directly).

---

## Test Directory Structure

```text
tests/
  conftest.py                    # shared fixtures: in-memory DuckDB, sample data
  fixtures/
    sample_findings.sql          # INSERT statements for test findings
    sample_transitions.sql       # INSERT statements for test transitions
    sample_interventions.sql     # INSERT statements for test interventions
    sample_fixes.sql             # INSERT statements for test fixes
    sample_sentiment.csv         # existing format for migration testing
  test_db.py                     # KaizenDB query layer tests
  test_views.py                  # view builder function tests
  test_ingest.py                 # ingestion script tests
  test_health.py                 # health endpoint tests
```

---

## Coverage Requirements

| Component | Target | Rationale |
|-----------|--------|-----------|
| `mcp/db.py` (KaizenDB) | 95% | Core data access layer; incorrect queries produce wrong visualizations |
| `mcp/dashboard.py` (view builders) | 80% | UI components; structural correctness matters but pixel-perfect testing is impractical |
| `scripts/ingest-findings.py` | 90% | Data integrity pipeline; parsing errors corrupt the database |
| Overall | 80% | Enforced via `fail_under=80` in pyproject.toml |

---

## Test Categories

### 1. Database Layer Tests (`test_db.py`)

Test the `KaizenDB` class methods against an in-memory DuckDB instance seeded with fixture data.

**Fixtures:**
- `db` -- in-memory DuckDB with all tables created and seeded with sample data
- `empty_db` -- in-memory DuckDB with tables created but no data
- `kaizen_db` -- `KaizenDB` instance wrapping the `db` fixture

**Test cases by method:**

| Method | Test Cases |
|--------|-----------|
| `findings()` | No filter returns all; filter by dimension; filter by severity; filter by status; combined filters; empty result |
| `finding_evidence()` | Returns evidence for valid finding_id; empty for unknown finding_id |
| `interventions()` | All interventions; filter by session_id; empty result |
| `state_transitions()` | All transitions; filter by session_id; filter by finding_id; ordered by sequence_index |
| `fixes()` | All fixes; filter by status; empty result |
| `fix_measurements()` | Returns measurements for valid fix_id; ordered by measured_at; empty for unknown fix_id |
| `sessions()` | All sessions; filter by project_name; filter by has_interventions; filter by date range; combined filters |
| `sentiment()` | All sentiment; filter by session_id; empty result |
| `dimension_summary()` | Returns one row per dimension; counts are correct; severity breakdown correct |
| `intervention_rate_over_time()` | Rolling average is computed correctly; window_sessions parameter works |

**Property-based tests (hypothesis):**
- Not required for this component. The query layer is a thin wrapper over SQL; correctness is validated by specific test cases against known fixture data. Property-based testing would test DuckDB's SQL engine, not our code.

### 2. View Builder Tests (`test_views.py`)

Test that each `_build_*_tab()` function returns the correct Panel component structure. These tests do NOT render to a browser -- they verify the component tree.

**Fixtures:**
- `kaizen_db` -- `KaizenDB` instance with sample data
- `empty_kaizen_db` -- `KaizenDB` instance with empty tables

**Test pattern:**

```python
# Structure validation (not implementation)
def test_findings_tab_structure(kaizen_db):
    tab = _build_findings_tab(kaizen_db)
    # Assert: returns pn.Column
    # Assert: contains filter widgets (Select for dimension, severity, status)
    # Assert: contains Tabulator widget
    # Assert: Tabulator has expected columns


def test_findings_tab_empty_state(empty_kaizen_db):
    tab = _build_findings_tab(empty_kaizen_db)
    # Assert: contains Markdown pane with "No Findings" message
```

**Test cases per tab:**

| Tab Builder | Test Cases |
|-------------|-----------|
| `_build_findings_tab` | Component structure; filter widgets present; Tabulator columns correct; empty state; evidence panel hidden initially |
| `_build_flow_tab` | Component structure; view mode toggle present; graph rendered with nodes/edges; empty state |
| `_build_fix_tracker_tab` | Component structure; Tabulator columns correct; empty state; effectiveness chart hidden initially |
| `_build_session_tab` | Component structure; filter widgets present; Tabulator with pagination; empty state; timeline hidden initially |
| `_build_sentiment_tab` | Component structure; trend plot present; distribution plot present; empty state |
| `_build_dashboard` | Returns pn.Tabs with 5 tabs; tab names correct; dynamic=True |

### 3. Ingestion Script Tests (`test_ingest.py`)

Test the parsing and extraction functions in `scripts/ingest-findings.py`.

**Fixtures:**
- `sample_analysis_md` -- fixture file with a sample analysis markdown in the expected output format
- `sample_jsonl` -- fixture file with sample JSONL session records (subset)
- `in_memory_db` -- empty in-memory DuckDB for write tests

**Test cases:**

| Function | Test Cases |
|----------|-----------|
| Markdown parser | Extracts findings with correct severity, dimension, title, description; handles multiple findings in one file; ignores malformed entries |
| Evidence extractor | Extracts session_id, timestamp, tool_name, excerpt from JSONL; links to correct finding_id; handles missing fields gracefully |
| Intervention extractor | Detects `[Request interrupted by user]`; detects tool denials; detects direct corrections; classifies intervention_type correctly |
| State transition builder | Creates correct sequence_index ordering; maps context/action/outcome correctly; links interventions to transitions |
| Fix linker | Associates fix records with finding IDs; computes before/after measurements correctly |
| Full pipeline | End-to-end: sample markdown + JSONL -> populated DuckDB with correct row counts and relationships |

### 4. Health Endpoint Tests (`test_health.py`)

Test the updated `HealthHandler` response format.

**Test cases:**
- Returns JSON with `status: ok`
- Includes `db_path`, `db_exists`, `table_counts`
- `table_counts` reflects actual row counts
- Returns correct structure when database does not exist
- `last_ingested` reflects most recent `ingested_at` value

---

## pytest Configuration

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=mcp",
    "--cov=scripts",
    "--cov-report=term-missing",
    "-v",
]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests requiring Panel/Tornado setup",
]

[tool.coverage.run]
branch = true

[tool.coverage.report]
show_missing = true
fail_under = 80
```

---

## Integration Testing Notes

Full integration tests (starting the Panel server, rendering tabs in a browser) are NOT part of the automated test suite. They are validated manually using the `agent-browser` protocol documented in the project CLAUDE.md. The automated tests verify component structure and data correctness without browser rendering.

The `agent-browser` validation protocol from CLAUDE.md applies unchanged to the redesigned dashboard, with these updates:

- Tab count assertion changes from 4 to 5
- Dashboard title changes from "Kaizen Sentiment Dashboard" to "Kaizen Findings Dashboard"
- New assertion: verify `table_counts` in `/health` response
- Tabulator widget count assertion: at least 3 Tabulator instances across all tabs (Findings, Interventions detail, Sessions)
