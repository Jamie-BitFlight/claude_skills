---
title: 'Datasette: Instant JSON API for Your SQLite Data'
library_name: datasette
pypi_package: datasette
category: data_exploration
python_compatibility: 3.10+
last_updated: '2025-11-02'
official_docs: https://docs.datasette.io
official_repository: https://github.com/simonw/datasette
maintenance_status: active
---

# Datasette - Instant Data Publishing and Exploration

## Executive Summary

Datasette is an open-source tool for exploring and publishing data. It transforms any SQLite database into an interactive website with a full JSON API, requiring zero code. Designed for data journalists, museum curators, archivists, local governments, scientists, and researchers, Datasette makes data sharing and exploration accessible to anyone with data to publish.

**Core Value Proposition**: Take data of any shape or size and instantly publish it as an explorable website with a corresponding API, without writing application code.

## Official Information

- **Repository**: <https://github.com/simonw/datasette> @ simonw/datasette
- **PyPI**: `datasette` @ <https://pypi.org/project/datasette/>
- **Current Development Version**: 1.0a19 (alpha)
- **Current Stable Version**: 0.65.1
- **Documentation**: <https://docs.datasette.io/> @ docs.datasette.io
- **License**: Apache License 2.0 @ <https://github.com/simonw/datasette/blob/main/LICENSE>
- **Maintenance Status**: Actively maintained (647 open issues, last updated 2025-10-21)
- **Community**: Discord @ <https://datasette.io/discord>, Newsletter @ <https://datasette.substack.com/>

## What Problem Does Datasette Solve?

### The Problem

Organizations and individuals have valuable data in SQLite databases, CSV files, or other formats, but:

- Building a web interface to explore data requires significant development effort
- Creating APIs for data access requires backend development expertise
- Publishing data in an accessible, explorable format is time-consuming
- Sharing data insights requires custom visualization tools
- Data exploration often requires SQL knowledge or specialized tools

### The Solution

Datasette provides:

1. **Instant Web Interface**: Automatic web UI for any SQLite database
2. **Automatic API**: Full JSON API with no code required
3. **SQL Query Interface**: Built-in SQL editor with query sharing
4. **Plugin Ecosystem**: 300+ plugins for extending functionality @ <https://datasette.io/plugins>
5. **One-Command Publishing**: Deploy to cloud platforms with a single command
6. **Zero-Setup Exploration**: Browse, filter, and facet data immediately

### What Would Be Reinventing the Wheel

Without Datasette, you would need to build:

- Custom web application for data browsing
- RESTful API endpoints for data access
- SQL query interface with security controls
- Data export functionality (JSON, CSV)
- Full-text search integration
- Authentication and authorization system
- Pagination and filtering logic
- Deployment configuration and hosting setup

**Example**: Publishing a dataset of 100,000 records would require weeks of development work. With Datasette: `datasette publish cloudrun mydata.db --service=mydata`

## Real-World Usage Patterns

### Pattern 1: Publishing Open Data (Government/Research)

**Context**: @ <https://github.com/simonw/covid-19-datasette>

```bash
# Convert CSV to SQLite
csvs-to-sqlite covid-data.csv covid.db

# Publish to Cloud Run with metadata
datasette publish cloudrun covid.db \
  --service=covid-tracker \
  --metadata metadata.json \
  --install=datasette-vega
```

**Use Case**: Local governments publishing COVID-19 statistics, election results, or public records.

### Pattern 2: Personal Data Archives (Dogsheep Pattern)

**Context**: @ <https://github.com/dogsheep>

```bash
# Export Twitter data to SQLite
twitter-to-sqlite user-timeline twitter.db

# Export GitHub activity
github-to-sqlite repos github.db

# Export Apple Health data
healthkit-to-sqlite export.zip health.db

# Explore everything together
datasette twitter.db github.db health.db --crossdb
```

**Use Case**: Personal data liberation - exploring your own data from various platforms.

### Pattern 3: Data Journalism and Investigation

**Context**: @ <https://github.com/simonw/laion-aesthetic-datasette>

```python
# Load and explore LAION training data
import sqlite_utils

db = sqlite_utils.Database("images.db")
db["images"].insert_all(image_data)
db["images"].enable_fts(["caption", "url"])

# Launch with custom template
datasette images.db \
  --template-dir templates/ \
  --metadata metadata.json
```

**Use Case**: Exploring large datasets like Stable Diffusion training data, analyzing patterns.

### Pattern 4: Internal Tools and Dashboards

**Context**: @ <https://github.com/rclement/datasette-dashboards>

```yaml
# datasette.yaml - Configure dashboards
databases:
  analytics:
    queries:
      daily_users:
        sql: |
          SELECT date, count(*) as users
          FROM events
          WHERE event_type = 'login'
          GROUP BY date
          ORDER BY date DESC
        title: Daily Active Users
```

**Installation**:

```bash
datasette install datasette-dashboards
datasette analytics.db --config datasette.yaml
```

**Use Case**: Building internal analytics dashboards without BI tools.

### Pattern 5: API Backend for Applications

**Context**: @ <https://github.com/simonw/datasette-graphql>

```bash
# Install GraphQL plugin
datasette install datasette-graphql

# Launch with authentication
datasette data.db \
  --root \
  --cors \
  --setting default_cache_ttl 3600
```

**GraphQL Query**:

```graphql
{
  products(first: 10, where: { price_gt: 100 }) {
    nodes {
      id
      name
      price
    }
  }
}
```

**Use Case**: Using Datasette as a read-only API backend for mobile/web apps.

## Integration Patterns

### Core Data Integrations

1. **SQLite Native**:

```python
import sqlite3

conn = sqlite3.connect("data.db")
# Datasette reads directly
```

2. **CSV/JSON Import** via `sqlite-utils` @ <https://github.com/simonw/sqlite-utils>:

```bash
sqlite-utils insert data.db records records.json
csvs-to-sqlite *.csv data.db
```

3. **Database Migration** via `db-to-sqlite` @ <https://github.com/simonw/db-to-sqlite>:

```bash
# Export from PostgreSQL
db-to-sqlite "postgresql://user:pass@host/db" data.db --table=events

# Export from MySQL
db-to-sqlite "mysql://user:pass@host/db" data.db --all
```

### Companion Libraries

- **sqlite-utils**: Database manipulation @ <https://github.com/simonw/sqlite-utils>
- **csvs-to-sqlite**: CSV import @ <https://github.com/simonw/csvs-to-sqlite>
- **datasette-extract**: AI-powered data extraction @ <https://github.com/datasette/datasette-extract>
- **datasette-parquet**: Parquet/DuckDB support @ <https://github.com/cldellow/datasette-parquet>

### Deployment Patterns

**Cloud Run** @ <https://docs.datasette.io/en/stable/publish.html>:

```bash
datasette publish cloudrun data.db \
  --service=myapp \
  --install=datasette-vega \
  --install=datasette-cluster-map \
  --metadata metadata.json
```

**Vercel** via `datasette-publish-vercel` @ <https://github.com/simonw/datasette-publish-vercel>:

```bash
pip install datasette-publish-vercel
datasette publish vercel data.db --project my-data
```

**Fly.io** via `datasette-publish-fly` @ <https://github.com/simonw/datasette-publish-fly>:

```bash
pip install datasette-publish-fly
datasette publish fly data.db --app=my-datasette
```

**Docker**:

```dockerfile
FROM datasetteproject/datasette
COPY *.db /data/
RUN datasette install datasette-vega
CMD datasette serve /data/*.db --host 0.0.0.0 --cors
```

## Python Version Compatibility

### Official Support Matrix

| Python Version | Status               | Notes                               |
| -------------- | -------------------- | ----------------------------------- |
| 3.10           | **Minimum Required** | @ setup.py python_requires=">=3.10" |
| 3.11           | ✅ Fully Supported   | Recommended for production          |
| 3.12           | ✅ Fully Supported   | Tested in CI                        |
| 3.13           | ✅ Fully Supported   | Tested in CI                        |
| 3.14           | ✅ Fully Supported   | Tested in CI                        |
| 3.9 and below  | ❌ Not Supported     | Deprecated as of v1.0               |

### Version-Specific Considerations

**Python 3.10+**:

- Uses `importlib.metadata` for plugin loading
- Native `match/case` statements in codebase (likely in v1.0+)
- Type hints using modern syntax

**Python 3.11+ Benefits**:

- Better async performance (important for ASGI)
- Faster startup times
- Improved error messages

**No Breaking Changes Expected**: Datasette maintains backward compatibility within major versions.

## Usage Examples

### Basic Usage

```bash
# Install
pip install datasette
# or
brew install datasette

# Serve a database
datasette data.db

# Open in browser automatically
datasette data.db -o

# Serve multiple databases
datasette db1.db db2.db db3.db

# Enable cross-database queries
datasette db1.db db2.db --crossdb
```

### Configuration Example

**metadata.json** @ <https://docs.datasette.io/en/stable/metadata.html>:

```json
{
  "title": "My Data Project",
  "description": "Exploring public datasets",
  "license": "CC BY 4.0",
  "license_url": "https://creativecommons.org/licenses/by/4.0/",
  "source": "Data Sources",
  "source_url": "https://example.com/sources",
  "databases": {
    "mydb": {
      "tables": {
        "events": {
          "title": "Event Log",
          "description": "System event records",
          "hidden": false
        }
      }
    }
  }
}
```

**datasette.yaml** @ <https://docs.datasette.io/en/stable/configuration.html>:

```yaml
settings:
  default_page_size: 50
  sql_time_limit_ms: 3500
  max_returned_rows: 2000

plugins:
  datasette-cluster-map:
    latitude_column: lat
    longitude_column: lng

databases:
  mydb:
    queries:
      popular_events:
        sql: |
          SELECT event_type, COUNT(*) as count
          FROM events
          GROUP BY event_type
          ORDER BY count DESC
          LIMIT 10
        title: Most Popular Events
```

### Plugin Development Example

**Simple Plugin** @ <https://docs.datasette.io/en/stable/writing_plugins.html>:

```python
from datasette import hookimpl


@hookimpl
def prepare_connection(conn):
    """Add custom SQL functions"""
    conn.create_function("is_even", 1, lambda x: x % 2 == 0)


@hookimpl
def extra_template_vars(request):
    """Add variables to templates"""
    return {"custom_message": "Hello from plugin!"}
```

**setup.py**:

```python
setup(
    name="datasette-my-plugin",
    version="0.1",
    py_modules=["datasette_my_plugin"],
    entry_points={"datasette": ["my_plugin = datasette_my_plugin"]},
    install_requires=["datasette>=0.60"],
)
```

### Advanced: Python API Usage

**Programmatic Access** @ <https://docs.datasette.io/en/stable/internals.html>:

```python
from datasette.app import Datasette
import asyncio


async def explore_data():
    # Initialize Datasette
    ds = Datasette(files=["data.db"])

    # Execute query
    result = await ds.execute("data", "SELECT * FROM users WHERE age > :age", {"age": 18})

    # Access rows
    for row in result.rows:
        print(dict(row))

    # Get table info
    db = ds.get_database("data")
    tables = await db.table_names()
    print(f"Tables: {tables}")


asyncio.run(explore_data())
```

### Testing Plugins

**pytest Example** @ <https://docs.datasette.io/en/stable/testing_plugins.html>:

```python
import pytest
from datasette.app import Datasette


@pytest.mark.asyncio
async def test_homepage():
    ds = Datasette(memory=True)
    await ds.invoke_startup()

    response = await ds.client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text


@pytest.mark.asyncio
async def test_json_api():
    ds = Datasette(memory=True)

    # Create test data
    db = ds.add_database(Database(ds, memory_name="test"))
    await db.execute_write("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")

    # Query via API
    response = await ds.client.get("/test/items.json")
    assert response.status_code == 200
    data = response.json()
    assert data["rows"] == []
```

## When NOT to Use Datasette

### ❌ Scenarios Where Datasette Is Inappropriate

1. **High-Write Applications**

   - Datasette is optimized for read-heavy workloads
   - SQLite has write limitations with concurrent access
   - **Better Alternative**: PostgreSQL with PostgREST, or Django REST Framework

2. **Real-Time Collaborative Editing**

   - No built-in support for concurrent data editing
   - Read-only by default (writes require plugins)
   - **Better Alternative**: Airtable, Retool, or custom CRUD application

3. **Large-Scale Data Warehousing**

   - SQLite works well up to ~100GB, struggles beyond
   - Not designed for massive analytical workloads
   - **Better Alternative**: DuckDB with MotherDuck, or BigQuery with Looker

4. **Complex BI Dashboards**

   - Limited visualization capabilities without plugins
   - Not a replacement for full BI platforms
   - **Better Alternative**: Apache Superset @ <https://github.com/apache/superset>, Metabase @ <https://github.com/metabase/metabase>, or Grafana

5. **Transactional Systems**

   - Not designed for OLTP workloads
   - Limited transaction support
   - **Better Alternative**: Django ORM with PostgreSQL, or FastAPI with SQLAlchemy

6. **User Authentication and Authorization**

   - Basic auth support, but not a full auth system
   - RBAC requires plugins and configuration
   - **Better Alternative**: Use Datasette behind proxy with auth, or use Metabase for built-in user management

7. **Non-Relational Data**
   - Optimized for relational SQLite data
   - Document stores require workarounds
   - **Better Alternative**: MongoDB with Mongo Express, or Elasticsearch with Kibana

### ⚠️ Use With Caution

1. **Sensitive Data Without Proper Access Controls**

   - Default is public access
   - Requires careful permission configuration
   - **Mitigation**: Use `--root` for admin access, configure permissions @ <https://docs.datasette.io/en/stable/authentication.html>

2. **Production Without Rate Limiting**
   - No built-in rate limiting
   - Can be overwhelmed by traffic
   - **Mitigation**: Deploy behind reverse proxy with rate limiting, or use Cloud Run with concurrency limits

## Decision Matrix

### ✅ Use Datasette When

| Scenario                               | Why Datasette Excels                                 |
| -------------------------------------- | ---------------------------------------------------- |
| Publishing static/semi-static datasets | Zero-code instant publication                        |
| Data journalism and investigation      | SQL interface + full-text search + shareable queries |
| Personal data exploration (Dogsheep)   | Cross-database queries, plugin ecosystem             |
| Internal read-only dashboards          | Fast setup, minimal infrastructure                   |
| Prototyping data APIs                  | Instant JSON API, no backend code                    |
| Open data portals                      | Built-in metadata, documentation, CSV export         |
| SQLite file exploration                | Best-in-class SQLite web interface                   |
| Low-traffic reference data             | Excellent for datasets < 100GB                       |

### ❌ Don't Use Datasette When

| Scenario                      | Why It's Not Suitable                    | Better Alternative           |
| ----------------------------- | ---------------------------------------- | ---------------------------- |
| Building a CRUD application   | Read-focused, limited write support      | Django, FastAPI + SQLAlchemy |
| Real-time analytics           | Not designed for streaming data          | InfluxDB, TimescaleDB        |
| Multi-tenant SaaS app         | Limited isolation, no row-level security | PostgreSQL + RLS             |
| Heavy concurrent writes       | SQLite write limitations                 | PostgreSQL, MySQL            |
| Terabyte-scale data           | SQLite size constraints                  | DuckDB, BigQuery, Snowflake  |
| Enterprise BI with governance | Limited data modeling layer              | Looker, dbt + Metabase       |
| Complex visualization needs   | Basic charts without plugins             | Apache Superset, Tableau     |
| Document/graph data           | Relational focus                         | MongoDB, Neo4j               |

## Comparison with Alternatives

### vs. Apache Superset @ <https://github.com/apache/superset>

**When to use Superset over Datasette**:

- Need advanced visualizations (50+ chart types vs. basic plugins)
- Enterprise BI with complex dashboards
- Multiple data source types (not just SQLite)
- Large team collaboration with RBAC

**When to use Datasette over Superset**:

- Simpler deployment and setup
- Focus on data exploration over dashboarding
- Primarily working with SQLite databases
- Want instant API alongside web interface

### vs. Metabase @ <https://github.com/metabase/metabase>

**When to use Metabase over Datasette**:

- Need business user-friendly query builder
- Want built-in email reports and scheduling
- Require user management and permissions UI
- Need mobile app support

**When to use Datasette over Metabase**:

- Working primarily with SQLite
- Want plugin extensibility
- Need instant deployment (lighter weight)
- Want API-first design

### vs. Custom Flask/FastAPI Application

**When to build custom over Datasette**:

- Complex business logic required
- Heavy write operations
- Custom authentication flows
- Specific UX requirements

**When to use Datasette over custom**:

- Rapid prototyping (hours vs. weeks)
- Standard data exploration needs
- Focus on data, not application development
- Leverage plugin ecosystem

## Key Insights and Recommendations

### Core Strengths

1. **Speed to Value**: From data to published website in minutes
2. **Plugin Ecosystem**: 300+ plugins for extending functionality @ <https://datasette.io/plugins>
3. **API-First Design**: JSON API is a first-class citizen
4. **Deployment Simplicity**: One command to cloud platforms
5. **Open Source Community**: Active development, responsive maintainer

### Best Practices

1. **Use sqlite-utils for data prep** @ <https://github.com/simonw/sqlite-utils>:

   ```bash
   sqlite-utils insert data.db table data.json --pk=id
   sqlite-utils enable-fts data.db table column1 column2
   ```

2. **Configure permissions properly**:

   ```yaml
   databases:
     private:
       allow:
         id: admin_user
   ```

3. **Use immutable mode for static data**:

   ```bash
   datasette data.db --immutable
   ```

4. **Leverage canned queries for common patterns**:

   ```yaml
   queries:
     search:
       sql: SELECT * FROM items WHERE name LIKE :query
   ```

5. **Install datasette-hashed-urls for caching** @ <https://github.com/simonw/datasette-hashed-urls>:
   ```bash
   datasette install datasette-hashed-urls
   ```

### Migration Path

**From spreadsheets to Datasette**:

```bash
csvs-to-sqlite data.csv data.db
datasette data.db
```

**From PostgreSQL to Datasette**:

```bash
db-to-sqlite "postgresql://user:pass@host/db" data.db
datasette data.db
```

**From Datasette to production app**:

- Use Datasette for prototyping and exploration
- Migrate to FastAPI/Django when write operations become critical
- Keep Datasette for read-only reporting interface

## Summary

Datasette excels at making data instantly explorable and shareable. It's the fastest path from data to published website with API. Use it for read-heavy workflows, data journalism, personal data archives, and rapid prototyping. Avoid it for write-heavy applications, enterprise BI, or large-scale data warehousing.

**TL;DR**: If you have data and want to publish it or explore it quickly without writing application code, use Datasette. If you need complex transactions, real-time collaboration, or enterprise BI features, choose a different tool.

## References

- Official Documentation @ <https://docs.datasette.io/>
- GitHub Repository @ <https://github.com/simonw/datasette>
- Plugin Directory @ <https://datasette.io/plugins>
- Context7 Documentation @ /simonw/datasette (949 code snippets)
- Dogsheep Project @ <https://github.com/dogsheep> (Personal data toolkit)
- Datasette Lite (WebAssembly) @ <https://lite.datasette.io/>
- Community Discord @ <https://datasette.io/discord>
- Newsletter @ <https://datasette.substack.com/>
