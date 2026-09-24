---
title: Arrow - Better Dates & Times for Python
library_name: arrow
pypi_package: arrow
category: datetime
python_compatibility: 3.8+
last_updated: '2025-11-02'
official_docs: https://arrow.readthedocs.io
official_repository: https://github.com/arrow-py/arrow
maintenance_status: active
---

# Arrow - Better Dates & Times for Python

## Core Purpose

Arrow provides a sensible, human-friendly approach to creating, manipulating, formatting, and converting dates, times, and timestamps. It addresses critical usability problems in Python's standard datetime ecosystem:

**Problems Arrow Solves:**

- **Module fragmentation**: Eliminates the need to import datetime, time, calendar, dateutil, pytz separately
- **Type complexity**: Provides a single Arrow type instead of managing date, time, datetime, tzinfo, timedelta, relativedelta
- **Timezone verbosity**: Simplifies timezone-aware operations that are cumbersome with standard library
- **Missing functionality**: Built-in ISO 8601 parsing, humanization, and time span operations
- **Timezone naivety**: UTC-aware by default, preventing common timezone bugs

Arrow is a **drop-in replacement for datetime** that consolidates scattered tools into a unified, elegant interface.

## When to Use Arrow

### Use Arrow When

1. **Building user-facing applications** that display relative times ("2 hours ago", "in 3 days")
2. **Working extensively with timezones** - converting between zones, handling DST transitions
3. **Parsing diverse datetime formats** - ISO 8601, timestamps, custom formats
4. **Need cleaner, more readable code** - Arrow's chainable API reduces boilerplate
5. **Generating time ranges or spans** - iterate over hours, days, weeks, months
6. **Internationalization is required** - 75+ locale support for humanized output
7. **API development** where timezone-aware timestamps are standard
8. **Data processing pipelines** that handle datetime transformations frequently

### Use Standard datetime When

1. **Performance is absolutely critical** - Arrow is ~50% slower than datetime.utcnow() @benchmark
2. **Minimal datetime operations** - simple date storage with no manipulation
3. **Library compatibility requirements** mandate standard datetime objects
4. **Memory-constrained environments** - datetime objects have smaller footprint
5. **Working within pandas/numpy** which have optimized datetime64 types
6. **No timezone logic needed** and you're comfortable with datetime's API

## Real-World Usage Patterns

### Pattern 1: Timezone-Aware Timestamp Creation

@source: <https://arrow.readthedocs.io/en/latest/>

```python
import arrow

# Get current time in UTC (default)
utc = arrow.utcnow()
# <Arrow [2013-05-11T21:23:58.970460+00:00]>

# Get current time in specific timezone
local = arrow.now("US/Pacific")
# <Arrow [2013-05-11T13:23:58.970460-07:00]>

# Convert between timezones effortlessly
utc_time = arrow.utcnow()
tokyo_time = utc_time.to("Asia/Tokyo")
ny_time = tokyo_time.to("America/New_York")
```

**Why this matters:** Standard datetime requires verbose pytz.timezone() calls and manual localization. Arrow handles this in one method.

### Pattern 2: Parsing Diverse Formats

@source: Context7 documentation snippets

```python
import arrow

# Parse ISO 8601 automatically
arrow.get("2013-05-11T21:23:58.970460+07:00")

# Parse with format string
arrow.get("2013-05-05 12:30:45", "YYYY-MM-DD HH:mm:ss")

# Parse Unix timestamps (int or float)
arrow.get(1368303838)
arrow.get(1565358758.123413)

# Parse with timezone
arrow.get("2013-05-11T21:23:58", tzinfo="Europe/Paris")

# Handle inconsistent spacing
arrow.get("Jun 1 2005     1:33PM", "MMM D YYYY H:mmA", normalize_whitespace=True)

# Parse ISO week dates
arrow.get("2013-W29-6", "W")  # Year-Week-Day format
```

**Why this matters:** datetime.strptime() requires exact format matching. Arrow intelligently handles variations and timezone strings directly.

### Pattern 3: Humanization for User Interfaces

@source: <https://arrow.readthedocs.io/en/latest/>

```python
import arrow

now = arrow.utcnow()
past = now.shift(hours=-1)
future = now.shift(days=3, hours=2)

# English humanization
past.humanize()  # 'an hour ago'
future.humanize()  # 'in 3 days'

# Localized humanization (75+ locales)
past.humanize(locale="ko-kr")  # '한시간 전'
past.humanize(locale="es")  # 'hace una hora'

# Multiple granularities
later = arrow.utcnow().shift(hours=2, minutes=19)
later.humanize(granularity=["hour", "minute"])
# 'in 2 hours and 19 minutes'

# Quarter granularity (business applications)
four_months = now.shift(months=4)
four_months.humanize(granularity="quarter")  # 'in a quarter'
```

**Why this matters:** Building this with datetime requires third-party libraries or manual logic. Arrow includes it with extensive locale support.

### Pattern 4: Time Shifting and Manipulation

@source: Context7 documentation snippets

```python
import arrow

now = arrow.utcnow()

# Relative shifts (chainable)
future = now.shift(years=1, months=-2, days=5, hours=3)
past = now.shift(weeks=-2)

# Dehumanize - parse human phrases
base = arrow.get("2020-05-27 10:30:35")
base.dehumanize("8 hours ago")
base.dehumanize("in 4 days")
base.dehumanize("hace 2 años", locale="es")  # Spanish: "2 years ago"

# Replace specific components
now.replace(hour=0, minute=0, second=0)  # Start of day
now.replace(year=2025)
```

**Why this matters:** timedelta only supports days/seconds. dateutil.relativedelta is verbose. Arrow combines both with intuitive API.

### Pattern 5: Time Ranges and Spans

@source: Context7 documentation snippets

```python
import arrow
from datetime import datetime

# Generate time ranges
start = arrow.get(2020, 5, 5, 12, 30)
end = arrow.get(2020, 5, 5, 17, 15)

# Iterate by hour
for hour in arrow.Arrow.range("hour", start, end):
    print(hour)

# Get floor and ceiling (span)
now = arrow.utcnow()
now.span("hour")  # Returns (floor, ceiling) tuple
now.floor("hour")  # Start of current hour
now.ceil("day")  # End of current day

# Span ranges - generate (start, end) tuples
for span in arrow.Arrow.span_range("hour", start, end):
    floor, ceiling = span
    print(f"Hour from {floor} to {ceiling}")

# Handle DST transitions correctly
before_dst = arrow.get("2018-03-10 23:00:00", tzinfo="US/Pacific")
after_dst = arrow.get("2018-03-11 04:00:00", tzinfo="US/Pacific")
for t in arrow.Arrow.range("hour", before_dst, after_dst):
    print(f"{t} (UTC: {t.to('UTC')})")
```

**Why this matters:** Standard datetime has no built-in iteration. Arrow handles DST transitions automatically in ranges.

### Pattern 6: Formatting with Built-in Constants

@source: Context7 documentation snippets

```python
import arrow

arw = arrow.utcnow()

# Use predefined format constants
arw.format(arrow.FORMAT_ATOM)  # '2020-05-27 10:30:35+00:00'
arw.format(arrow.FORMAT_COOKIE)  # 'Wednesday, 27-May-2020 10:30:35 UTC'
arw.format(arrow.FORMAT_RFC3339)  # '2020-05-27 10:30:35+00:00'
arw.format(arrow.FORMAT_W3C)  # '2020-05-27 10:30:35+00:00'

# Custom formats with tokens
arw.format("YYYY-MM-DD HH:mm:ss ZZ")  # '2020-05-27 10:30:35 +00:00'

# Escape literal text in formats
arw.format("YYYY-MM-DD h [h] m")  # '2020-05-27 10 h 30'

# Timestamp formats
arw.format("X")  # '1590577835' (seconds)
arw.format("x")  # '1590577835123456' (microseconds)
```

**Why this matters:** datetime.strftime() uses different token syntax (%Y vs YYYY). Arrow uses consistent, JavaScript-inspired tokens.

## Integration Patterns

### Works seamlessly with

**python-dateutil** (required dependency >=2.7.0)

- Arrow uses dateutil.parser internally for flexible parsing
- Timezone objects from dateutil are directly compatible

**pytz** (optional, for Python <3.9)

- Arrow accepts pytz timezone objects in `to()` and `tzinfo` parameters
- Handles pytz's DST quirks automatically

**zoneinfo** (Python 3.9+, via backports.zoneinfo on 3.8)

- Arrow supports ZoneInfo timezone objects natively
- Uses tzdata package on Python 3.9+ for timezone database

**datetime** (standard library)

- `arrow_obj.datetime` returns standard datetime object
- `arrow.get(datetime_obj)` creates Arrow from datetime
- Arrow subclasses datetime, so it works anywhere datetime does

**pandas** (data analysis)

```python
import arrow
import pandas as pd

# Convert Arrow to pandas Timestamp
arrow_time = arrow.utcnow()
pd.Timestamp(arrow_time.datetime)

# Or use Arrow for timezone-aware operations before pandas
df["timestamp"] = df["utc_string"].apply(lambda x: arrow.get(x).to("US/Pacific").datetime)
```

**Django/Flask** (web frameworks)

```python
# Django models - store as DateTimeField
from django.db import models
import arrow


class Event(models.Model):
    created_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        self.created_at = arrow.utcnow().datetime  # Convert to datetime
        super().save(*args, **kwargs)

    @property
    def created_humanized(self):
        return arrow.get(self.created_at).humanize()
```

## Python Version Compatibility

@source: <https://github.com/arrow-py/arrow/blob/master/pyproject.toml>

**Minimum:** Python 3.8 **Tested versions:** 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14 **Status:** Production/Stable across all supported versions

**Version-specific notes:**

- **Python 3.8**: Requires `backports.zoneinfo==0.2.1` for timezone support
- **Python 3.9+**: Uses built-in `zoneinfo` and `tzdata` package
- **Python 3.6-3.7**: No longer supported as of Arrow 1.3.0 (EOL Python versions)

**Dependencies:**

```toml
python-dateutil>=2.7.0
backports.zoneinfo==0.2.1  # Python <3.9 only
tzdata  # Python >=3.9 only
```

## Installation

```bash
# Basic installation
pip install -U arrow

# With uv (recommended)
uv pip install arrow

# In pyproject.toml
[project]
dependencies = [
    "arrow>=1.3.0",
]
```

## When NOT to Use Arrow

### Scenario 1: High-Performance Timestamp Generation

@source: <https://www.dataroc.ca/blog/most-performant-timestamp-functions-python>

**Performance benchmarks show:**

- `time.time()`: Baseline (fastest)
- `datetime.utcnow()`: ~50% slower than time.time()
- Arrow operations: Additional overhead for object wrapping

**Use datetime when:** You're generating millions of timestamps in tight loops (e.g., high-frequency trading, real-time analytics pipelines).

```python
# High-performance scenario - use standard library
import time

timestamp = time.time()  # Fastest for epoch timestamps

import datetime

dt = datetime.datetime.utcnow()  # Faster for datetime objects
```

### Scenario 2: Working with Pandas/NumPy DateTime

@source: Performance analysis and library comparisons

Pandas has highly optimized `datetime64` vectorized operations. Arrow's object-oriented approach doesn't vectorize well.

**Use pandas when:** Processing large datasets with datetime columns.

```python
import pandas as pd

# Pandas is optimized for this
df["date"] = pd.to_datetime(df["date_string"])
df["hour"] = df["date"].dt.hour  # Vectorized operation

# Arrow would require row-by-row operations (slow)
# df['hour'] = df['date'].apply(lambda x: arrow.get(x).hour)
```

### Scenario 3: Simple Date Storage

**Use datetime when:** You only need to store dates with no manipulation:

```python
from datetime import datetime

# Simple storage - datetime is sufficient
user.created_at = datetime.utcnow()
```

### Scenario 4: Library Compatibility Constraints

Some libraries explicitly require standard datetime objects and don't accept subclasses. Always test compatibility.

### Scenario 5: Memory-Constrained Environments

Arrow objects carry additional overhead. For millions of cached datetime objects, standard datetime is lighter.

## Decision Matrix

| Requirement            | Arrow | datetime | Notes                                               |
| ---------------------- | ----- | -------- | --------------------------------------------------- |
| Timezone conversion    | ✓✓✓   | ✓        | Arrow: one-line. datetime: verbose with pytz        |
| ISO 8601 parsing       | ✓✓✓   | ✓✓       | Arrow: automatic. datetime: fromisoformat() limited |
| Humanization           | ✓✓✓   | ✗        | Arrow: built-in with 75+ locales                    |
| Time ranges/iteration  | ✓✓✓   | ✗        | Arrow: native. datetime: manual loops               |
| Performance (creation) | ✓✓    | ✓✓✓      | datetime ~50% faster                                |
| Performance (parsing)  | ✓✓    | ✓✓✓      | datetime.strptime() faster                          |
| Memory footprint       | ✓✓    | ✓✓✓      | datetime objects lighter                            |
| Learning curve         | ✓✓✓   | ✓✓       | Arrow: more intuitive                               |
| Pandas integration     | ✓     | ✓✓✓      | Use pandas.Timestamp for large data                 |
| Standard library       | ✗     | ✓✓✓      | Arrow: requires installation                        |
| Type hints             | ✓✓✓   | ✓✓✓      | Both have full PEP 484 support                      |
| DST handling           | ✓✓✓   | ✓✓       | Arrow: automatic. datetime: manual                  |

**Legend:** ✓✓✓ Excellent | ✓✓ Good | ✓ Adequate | ✗ Not supported

## Quick Decision Guide

<eg>
START: Do you need datetime functionality?
  |
  ├─ Is performance critical? (>100k ops/sec)
  |   └─ YES → Use datetime or time.time()
  |
  ├─ Working with pandas/numpy large datasets?
  |   └─ YES → Use pandas.Timestamp
  |
  ├─ Need any of: humanization, easy timezone conversion, time ranges, multi-locale?
  |   └─ YES → Use Arrow
  |
  ├─ Simple date storage only?
  |   └─ YES → Use datetime
  |
  └─ Building user-facing application with datetime logic?
      └─ YES → Use Arrow (cleaner code, better UX)
</eg>

## Common Gotchas and Solutions

### Gotcha 1: Arrow is timezone-aware by default

@source: Arrow documentation

```python
# This gives you UTC time, not local time
arrow.now()  # <Arrow [2020-05-27T10:30:35.123456+00:00]>

# For local timezone, be explicit
arrow.now("local")  # or arrow.now('America/New_York')
```

### Gotcha 2: Converting to datetime loses Arrow methods

```python
arrow_time = arrow.utcnow()
dt = arrow_time.datetime  # Now a standard datetime object

# This works
arrow_time.humanize()  # ✓

# This fails
dt.humanize()  # ✗ AttributeError
```

### Gotcha 3: Timestamp parsing requires format token in 0.15.0+

@source: Context7 CHANGELOG snippets

```python
# Deprecated (pre-0.15.0)
arrow.get("1565358758")  # ✗ No longer works

# Correct (0.15.0+)
arrow.get("1565358758", "X")  # ✓ Explicit format token
arrow.get(1565358758)  # ✓ Or pass as int/float directly
```

### Gotcha 4: Ambiguous datetimes during DST transitions

@source: Context7 documentation

```python
# During DST "fall back", 2 AM occurs twice
# Use fold parameter (PEP 495)
ambiguous = arrow.Arrow(2017, 10, 29, 2, 0, tzinfo="Europe/Stockholm")
ambiguous.fold  # 0 (first occurrence)

# Specify which occurrence
second_occurrence = arrow.Arrow(2017, 10, 29, 2, 0, tzinfo="Europe/Stockholm", fold=1)
```

## Alternatives Comparison

@source: <https://python.libhunt.com/arrow-alternatives>, <https://aboutsimon.com/blog/2016/08/04/datetime-vs-Arrow-vs-Pendulum-vs-Delorean-vs-udatetime.html>

**Pendulum** (arrow alternative)

- Similar goals: human-friendly datetime
- Better timezone handling in some edge cases
- Slower than Arrow in benchmarks
- Less widely adopted (fewer GitHub stars)

**Maya** (Datetimes for Humans)

- Simpler API, fewer features
- Less actively maintained
- Good for very basic use cases

**udatetime** (performance-focused)

- Written in C for speed (faster than datetime)
- Limited feature set (encode/decode only)
- Use when you need Arrow-like simplicity with datetime-like speed

**Standard datetime** (built-in)

- Always available, no dependencies
- Verbose but performant
- Use when Arrow features aren't needed

**dateutil** (datetime extension)

- Powerful parser, relativedelta for arithmetic
- Often used with datetime for enhanced functionality
- Arrow uses dateutil internally

## Real-World Example Projects

@source: GitHub search results

**arrow-py/arrow** (8,944 stars)

- Official repository with comprehensive examples
- <https://github.com/arrow-py/arrow>

**Common usage in web applications:**

```python
# API endpoint returning human-readable timestamps
from flask import jsonify
import arrow


@app.route("/events")
def get_events():
    events = Event.query.all()
    return jsonify([
        {
            "id": e.id,
            "name": e.name,
            "created": arrow.get(e.created_at).humanize(),
            "start_time": arrow.get(e.start_time).format("YYYY-MM-DD HH:mm ZZ"),
        }
        for e in events
    ])
```

**Data processing pipelines:**

```python
import arrow


def process_log_file(log_path):
    with open(log_path) as f:
        for line in f:
            # Parse diverse timestamp formats
            timestamp_str = extract_timestamp(line)
            timestamp = arrow.get(timestamp_str, normalize_whitespace=True)

            # Convert to consistent timezone
            utc_time = timestamp.to("UTC")

            # Filter by time range
            if utc_time >= arrow.get("2025-01-01"):
                yield utc_time, line
```

## References and Sources

@official_docs: <https://arrow.readthedocs.io/en/latest/> @repository: <https://github.com/arrow-py/arrow> @pypi: <https://pypi.org/project/arrow/> @context7: /arrow-py/arrow @changelog: <https://github.com/arrow-py/arrow/blob/master/CHANGELOG.rst>

**Performance analysis:** @benchmark: <https://www.dataroc.ca/blog/most-performant-timestamp-functions-python> @comparison: <https://aboutsimon.com/blog/2016/08/04/datetime-vs-Arrow-vs-Pendulum-vs-Delorean-vs-udatetime.html>

**Community resources:** @alternatives: <https://python.libhunt.com/arrow-alternatives> @tutorial: <https://code.tutsplus.com/arrow-for-better-date-and-time-in-python--cms-29624t> @guide: <https://stackabuse.com/working-with-datetime-in-python-with-arrow/>

## Summary

Arrow eliminates datetime friction by consolidating Python's fragmented date/time ecosystem into a single, intuitive API. Use it when developer experience and feature richness matter more than raw performance. For high-frequency operations or pandas-scale data processing, stick with the standard library or specialized tools. Arrow shines in web applications, APIs, CLI tools, and any code where humans read the timestamps.

**The reinvented wheel:** Without Arrow, you'd manually implement timezone conversion helpers, humanization logic, flexible parsing, and time range iteration using datetime + dateutil + pytz + custom code. Arrow packages these common patterns into a production-ready library.
