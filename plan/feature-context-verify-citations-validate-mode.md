# Feature Context: Add --verify-citations Flag to Validate Mode

## Document Metadata

- **Generated**: 2026-03-19
- **Input Type**: simple_description
- **Source**: GitHub Issue #845 — Add `--verify-citations` flag to research-curator validate mode
- **Status**: DISCOVERY_COMPLETE

---

## Original Request

Add an opt-in `--verify-citations` flag to the `validate_research.py` script that performs network-based citation checks: HTTP HEAD for URL reachability, arXiv ID format validation, DOI resolution via CrossRef public API. Findings are warning-severity in the JSON output.

A developer can run:

```bash
uv run .claude/skills/research-curator/scripts/validate_research.py --json --verify-citations ./research/agent-frameworks/AutoResearchClaw.md
```

and receive JSON output with a `citation_verification` section showing per-URL/arXiv/DOI status. Dead or hallucinated references produce warning-severity issues in the existing issues list. The flag defaults to off so CI pipelines are not affected.

---

## Core Intent Analysis

### WHO (Target Users)

Developers and researchers who curate research entries and want to confirm that cited sources are reachable and non-fabricated before committing or publishing. Also AI agents running in validate mode who need to surface broken references without triggering CI failures.

### WHAT (Desired Outcome)

When `--verify-citations` is passed, the validator performs live network checks against references extracted from the entry and emits findings as warning-severity issues inside the existing issues list. A new `citation_verification` section in the JSON output presents per-reference results (URL/arXiv/DOI, check type, status).

Pass/fail status of the entry is not altered by citation check failures because findings are warning-severity, not error-severity. CI pipelines that do not pass `--verify-citations` observe identical behavior to today.

### WHEN (Trigger Conditions)

- A developer runs `--validate` and suspects a research entry may contain hallucinated or dead references
- An agent or human reviewer wants to confirm reference quality before merging a new research entry
- Periodic audits of existing research entries for link rot

### WHY (Problem Being Solved)

The validate mode is the quality gate for research entries, but it currently checks only structure — it cannot detect references that were fabricated or have since died. Research entries can contain:

- URLs that never existed (hallucinated by an AI researcher)
- arXiv IDs that do not match any real paper
- DOIs that do not resolve through CrossRef

Without citation verification, validate mode passes entries containing broken or fabricated references, giving false confidence in entry quality. The AutoResearchClaw research entry (referenced in this feature's source) demonstrates a 4-layer citation verification pattern used to prevent hallucinated references in AI-generated content.

---

## Codebase Research

### Similar Patterns Found

#### Pattern 1: Warning-Severity Issues (existing checks)

- **Location**: `.claude/skills/research-curator/scripts/validate_research.py:175-200` (`_check_access_dates`) and lines `203-230` (`_check_freshness_tracking`)
- **Relevance**: Existing warning-severity checks follow the same `Issue` TypedDict schema — `check`, `severity`, `message`, `line`. Citation verification findings would use the same schema at `severity: "warning"`.
- **Reusable**: The `Issue` TypedDict at line 20-26 and the pattern of returning `list[Issue]` from a check function are the extension point.

#### Pattern 2: URL Extraction (URL_PATTERN regex)

- **Location**: `.claude/skills/research-curator/scripts/validate_research.py:56` — `URL_PATTERN = re.compile(r"https?://[^\s>)\]]+")`
- **Relevance**: The script already extracts URLs from lines for `_check_access_dates`. Citation verification would need to extract URLs from the References section for network probing.
- **Reusable**: `URL_PATTERN` and the References section extraction logic in `_check_access_dates` (lines 183-199).

#### Pattern 3: PEP 723 Inline Dependencies

- **Location**: `.claude/skills/research-curator/scripts/validate_research.py:1-5`
- **Relevance**: The script declares its own dependencies inline (`typer>=0.21.0`). Any network library needed for citation checks (e.g., `httpx`) would be added to this block.
- **Reusable**: The dependency declaration pattern is established and understood.

#### Pattern 4: validate_file Function Signature and Return Shape

- **Location**: `.claude/skills/research-curator/scripts/validate_research.py:327-353`
- **Relevance**: `validate_file` returns `{"file": ..., "status": ..., "issues": [...]}`. The feature adds a `citation_verification` key to this dict. The `main()` function aggregates results; a new `citation_checks` counter in the summary section may be needed.
- **Reusable**: The existing return shape is the direct extension point.

#### Pattern 5: Validation Rules Reference Document

- **Location**: `.claude/skills/research-curator/references/validation-rules.md:14-22`
- **Relevance**: All existing check types are documented with severity and description. A `citation_verification` check type would need to be added here to complete the documentation contract.
- **Reusable**: The check definition table structure is the template for documenting the new check.

### Existing Infrastructure

- `validate_file()` at line 327 accumulates issues from all checks and returns them in a unified structure. Adding citation verification means adding a new check function that returns `list[Issue]` and calling it from `validate_file()` when `--verify-citations` is set.
- The `main()` Typer command at line 373 accepts the `path`, `--json`, and `--verbose` options. A `--verify-citations` option would follow the same `typer.Option(False, ...)` pattern as `_JSON_OPT` and `_VERBOSE_OPT`.
- The JSON output schema is documented in `validation-rules.md:55-79`. A `citation_verification` section per entry is new and not in the current schema.
- SKILL.md's Validate Mode section (lines 275-350) documents what gets checked and what the workflow does with warning-severity findings — citation warnings would flow through the same "Warnings (manual review recommended)" path already defined.

### Code References

- `.claude/skills/research-curator/scripts/validate_research.py:20-26` — `Issue` TypedDict definition
- `.claude/skills/research-curator/scripts/validate_research.py:56` — `URL_PATTERN` regex
- `.claude/skills/research-curator/scripts/validate_research.py:175-200` — `_check_access_dates` (References section URL extraction pattern)
- `.claude/skills/research-curator/scripts/validate_research.py:327-353` — `validate_file` return shape
- `.claude/skills/research-curator/scripts/validate_research.py:368-374` — Typer option declarations
- `.claude/skills/research-curator/references/validation-rules.md:14-22` — existing warning check definitions
- `.claude/skills/research-curator/references/validation-rules.md:55-79` — JSON output schema
- `.claude/skills/research-curator/SKILL.md:286-349` — Validate Mode workflow and severity handling

---

## Use Scenarios

### Scenario 1: Developer Validates a New AI-Generated Entry

**Actor**: Developer who received a research entry written by an AI agent
**Trigger**: About to merge a new research entry for a tool they have not personally verified
**Goal**: Confirm the URLs and arXiv IDs cited in the References section are real and reachable before merging
**Expected Outcome**: Running `--verify-citations` against the entry produces a list of per-reference check results. Any dead URL or unresolvable DOI appears as a warning in the issues list. Developer decides whether to investigate further before merging.

### Scenario 2: CI Pipeline Runs Validate Without Network Checks

**Actor**: CI pipeline (GitHub Actions)
**Trigger**: Pull request opened with a new or modified research entry
**Goal**: Enforce structural quality without incurring network latency or flakiness
**Expected Outcome**: `--verify-citations` is not passed; the script runs identically to today. No citation checks are performed. Exit codes and issue counts are unaffected.

### Scenario 3: Periodic Link-Rot Audit

**Actor**: Research curator running maintenance
**Trigger**: Running a scheduled or manual audit of all research entries
**Goal**: Identify entries where previously-valid URLs have since gone dead
**Expected Outcome**: Running `--verify-citations` against `./research/` (entire directory) produces a summary of all citation check failures across all entries, each as a warning-severity issue in its entry's issues list.

### Scenario 4: Investigating a Specific Suspect Entry

**Actor**: Developer investigating a report that an entry contains fabricated references
**Trigger**: Issue filed or observation that a cited arXiv paper does not exist
**Goal**: Get machine-readable per-reference status to pass to a fix agent
**Expected Outcome**: The `citation_verification` section in JSON output shows the exact arXiv ID checked, the check type (arXiv ID format validation or API lookup), and the failure reason, so a fix agent receives actionable input.

---

## Gap Analysis

### Identified Gaps

| # | Category | Gap Description | Impact |
|---|----------|-----------------|--------|
| 1 | Behavior | What citation types are extracted: only URLs in References section, or also arXiv IDs and DOIs embedded in prose sections? | Determines scope of parsing logic and which parts of the file are scanned |
| 2 | Behavior | arXiv ID validation: is format-only check sufficient, or must the ID be confirmed to exist via arXiv API? | Determines whether network calls are made for arXiv IDs |
| 3 | Behavior | DOI resolution: CrossRef public API only, or also fallback to doi.org redirect? | Determines number of network calls per DOI and failure definition |
| 4 | Behavior | What constitutes a "dead" URL — HTTP non-2xx, connection refused, timeout, or DNS failure? How should redirects be treated? | Determines pass/fail criteria for URL checks |
| 5 | Behavior | Should the `citation_verification` section appear in JSON output even when `--verify-citations` is not set? (As an empty section, or omitted entirely?) | Affects JSON schema stability for consumers |
| 6 | Scope | Does `--verify-citations` apply only to the References section, or also to `Source URL` in the header block? | Determines what gets checked |
| 7 | Integration | When combined with `--fix` mode and citation warnings are emitted, should fix agents attempt to update dead URLs or only report them? | Determines whether fix agent behavior changes |
| 8 | Behavior | What timeout and retry policy governs network checks? (Single-entry use vs directory-wide use has very different performance implications.) | Affects user experience and script reliability |
| 9 | Behavior | Should per-reference check results surface in the `issues` list only, or also in a dedicated `citation_verification` per-entry section, or both? | Affects JSON schema for downstream consumers (SKILL.md documents validate output format) |
| 10 | Scope | Is `--verify-citations` compatible with `--verbose` (human-readable) output, or only with `--json`? | Determines whether SKILL.md validate mode output section needs updating |

---

## Questions Requiring Resolution

### Q1: What citation types are in scope?

- **Category**: Scope
- **Gap**: The feature description names three types (URLs, arXiv IDs, DOIs) but does not specify whether all three must be extracted from all sections or only from the References section.
- **Question**: Should citation verification scan only the References section, or also inline citations in prose sections (Overview, Technical Architecture, etc.)? Should the Source URL header field also be checked?
- **Options**:
  - A) References section only (aligns with existing `_check_access_dates` scope)
  - B) References section plus Source URL header field
  - C) Full-document scan for all citation types
- **Why It Matters**: Option A is a narrower, lower-risk scope. Option C produces more findings but requires scanning every section and distinguishing citation patterns from incidental mentions.
- **Resolution**: _pending_

### Q2: arXiv ID check depth — format only or API lookup?

- **Category**: Behavior
- **Gap**: "arXiv ID format validation" could mean regex-only (does the string match `\d{4}\.\d{4,5}` pattern) or a live check against the arXiv API (does a paper with this ID actually exist).
- **Question**: For arXiv IDs, is a format/pattern check sufficient, or must the feature confirm the paper exists via the arXiv API?
- **Options**:
  - A) Format validation only — no network call for arXiv
  - B) Live arXiv API lookup to confirm paper existence
- **Why It Matters**: Option A adds no latency but misses fabricated-but-validly-formatted IDs (the core hallucination risk). Option B detects fabricated IDs but adds network calls and a new API dependency.
- **Resolution**: _pending_

### Q3: What does a URL check failure mean?

- **Category**: Behavior
- **Gap**: "HTTP HEAD for URL reachability" does not define the failure criteria (timeout threshold, which status codes fail, how redirects are treated).
- **Question**: Which outcomes constitute a failed URL check? HTTP 4xx? 5xx? Timeout? DNS failure? Should 301/302 redirects be followed or flagged?
- **Options**:
  - A) Any non-2xx final response after following redirects = fail
  - B) Connection error or timeout = fail; HTTP errors (4xx/5xx) = warn with status code
  - C) Treat permanent redirects (301) as a warning (URL has moved) separate from dead URLs (404)
- **Why It Matters**: Affects what "dead reference" means in the output and whether the fix agent has actionable information (e.g., "URL permanently moved to X" is fixable; "DNS failure" may be transient).
- **Resolution**: _pending_

### Q4: JSON output schema — dedicated section or issues-list only?

- **Category**: Integration
- **Gap**: The feature description mentions both a `citation_verification` section in JSON output and warning-severity issues in the existing issues list. It is unclear whether these are the same data in two locations or different data.
- **Question**: Should citation check results appear in both the existing `issues` array and a dedicated `citation_verification` per-entry section, or only in the `issues` array?
- **Options**:
  - A) Issues array only (consistent with all other check types; no schema change to entry shape)
  - B) Both — per-reference details in `citation_verification`, summary as warning issues in `issues` array
  - C) `citation_verification` section only, separate from issues
- **Why It Matters**: Option A requires no schema change to `validation-rules.md` or the entry return shape. Option B requires documenting a new schema field. Downstream consumers (SKILL.md validate mode output section) depend on schema stability.
- **Resolution**: _pending_

### Q5: Timeout and concurrency for directory-wide use?

- **Category**: Behavior
- **Gap**: A single-entry run against one file with 5-10 URLs is low-risk. Running `--verify-citations` against `./research/` (potentially 50+ entries with hundreds of URLs) raises latency and reliability questions.
- **Question**: Is there a desired timeout per URL check? Should URL checks within a single file run concurrently, or sequentially? Is there a cap on total network calls per invocation?
- **Why It Matters**: Without defined bounds, a directory-wide citation check could take many minutes or hang on slow endpoints, making the flag impractical for bulk use.
- **Resolution**: _pending_

---

## Goals (Pending Resolution)

_These goals will be finalized after questions Q1-Q5 are resolved._

1. Add `--verify-citations` flag (default: off) to `validate_research.py` that triggers network-based citation checks without altering existing behavior when the flag is absent.
2. Extract citation references (URLs, arXiv IDs, DOIs) from the applicable sections of a research entry.
3. Perform reachability and validity checks per reference type: HTTP HEAD for URLs, format/API check for arXiv IDs, CrossRef API for DOIs.
4. Emit findings as warning-severity issues in the existing issues list so CI pipelines observe no change when `--verify-citations` is not passed.
5. Produce per-reference check results in JSON output (exact schema pending Q4 resolution).
6. Update `validation-rules.md` to document the new `citation_verification` check type and any JSON schema additions.
7. Update `SKILL.md` validate mode documentation to describe `--verify-citations` usage and output.

---

## Next Steps

After questions are resolved:

1. Update "Resolution" fields in Questions section above
2. Finalize Goals section
3. Proceed to RT-ICA assessment
4. Then proceed to architecture design via `@python3-development:python-cli-design-spec`
