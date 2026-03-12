# Validation Rules

Checks performed by `./scripts/validate_research.py` and severity mapping for the `/research-curator --validate` mode.

---

## Check Definitions

### Error Severity (must fix)

- **section_completeness**: All 9 required `##`-level sections must exist — Overview, Problem Addressed, Key Statistics, Key Features, Technical Architecture, Installation & Usage, Relevance to Claude Code Development, References, Freshness Tracking. Header fields (Research Date, Source URL, etc.) are checked separately via **header_fields**.
- **header_fields**: Header block must contain Research Date, Source URL, Version at Research, License
- **empty_sections**: Section heading exists but contains no content below it before the next heading

### Warning Severity (should fix)

- **access_dates**: Every URL in the References section must have an access date in format `(accessed YYYY-MM-DD)` or `(YYYY-MM-DD)`
- **freshness_tracking**: Freshness Tracking section must contain Last Verified, Version at Verification, Next Review Recommended fields
- **statistics_currency**: Dates in Key Statistics section older than 6 months from today trigger a staleness warning
- **url_format**: All URLs must be valid `http://` or `https://` format
- **cross_references_absent**: Entry does not contain a `## Cross-References` section. Expected for entries created or last verified on or after 2026-03-12. Entries with Research Date or Last Verified before this date are exempt. Note for `validate_research.py` implementers: gate this warning on the Research Date or Last Verified field value — exempt entries with dates before 2026-03-12.

### Info Severity (optional)

- **formatting_suggestions**: Minor markdown formatting issues (missing blank lines around fences, inconsistent heading levels)

---

## Script vs Agent Responsibility

```mermaid
flowchart TD
    Start([Validation issue found]) --> Q{Can it be fixed mechanically?}
    Q -->|Yes — formatting, missing dates, structure| Script[Script reports issue with file:line]
    Q -->|No — needs fresh research, content generation| Agent[Spawn @research-curator with --fix flag]
    Script --> Report[Include in JSON output for orchestrator]
    Agent --> Report
```

**Script handles detection only** — it identifies issues and reports them with file path, line number, severity, and message.

**Agent handles fixes** that require:

- Gathering fresh statistics (re-research)
- Writing missing section content
- Updating stale references with current URLs
- Refreshing version numbers from upstream

**Orchestrator decides** which issues to auto-fix vs report to user based on severity.

---

## JSON Output Schema

```json
{
  "summary": {
    "total": "number of entries scanned",
    "passed": "entries with zero errors",
    "errors": "total error-severity issues",
    "warnings": "total warning-severity issues",
    "info": "total info-severity observations"
  },
  "entries": [
    {
      "file": "category/filename.md (relative to research/)",
      "status": "pass | fail",
      "issues": [
        {
          "check": "check name from definitions above",
          "severity": "error | warning | info",
          "message": "human-readable description",
          "line": "line number or null"
        }
      ]
    }
  ]
}
```
