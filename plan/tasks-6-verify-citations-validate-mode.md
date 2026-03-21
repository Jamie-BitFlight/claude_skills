---
feature: verify-citations-validate-mode
slug: verify-citations-validate-mode
github_issue: 845
parent_issue_number: 845
total_tasks: 8
acceptance_criteria_structured:
  - criterion-id: AC1
    description: "--verify-citations flag exists and appears in --help output"
    check_command: "uv run .claude/skills/research-curator/scripts/validate_research.py --help"
    pass_condition: "output contains --verify-citations"
  - criterion-id: AC2
    description: "Without flag: no network calls, existing behaviour unchanged"
    check_command: "uv run .claude/skills/research-curator/scripts/validate_research.py --json ./research/agent-frameworks/AutoResearchClaw.md"
    pass_condition: "exit 0, output does not contain citation_verification"
  - criterion-id: AC3
    description: "With flag: JSON output includes citation_verification section"
    check_command: "uv run .claude/skills/research-curator/scripts/validate_research.py --json --verify-citations ./research/agent-frameworks/AutoResearchClaw.md"
    pass_condition: "output contains citation_verification"
  - criterion-id: AC4
    description: "SKILL.md documents --verify-citations flag"
    check_command: "grep -c 'verify-citations' .claude/skills/research-curator/SKILL.md"
    pass_condition: "exit 0, count >= 1"
  - criterion-id: AC5
    description: "validation-rules.md defines citation verification rules"
    check_command: "grep -c 'citation' .claude/skills/research-curator/references/validation-rules.md"
    pass_condition: "exit 0, count >= 3"
  - criterion-id: AC6
    description: "research-curator agent documents citation_verification as non-fixable"
    check_command: "grep -c 'citation_verification' .claude/agents/research-curator.md"
    pass_condition: "exit 0, count >= 1"
---

# Task Plan: verify-citations-validate-mode

## Task T0: Baseline Capture

---
task: T0
status: NOT STARTED
dependencies: []
priority: 1
complexity: Low
agent: python3-development:t0-baseline-capture
---

Capture baseline state of all acceptance criteria before implementation begins.

Run each check_command from acceptance_criteria_structured and record results to `plan/T0-baseline-verify-citations-validate-mode.yaml`.

**Acceptance Criteria**:

- All 6 check_commands executed and results recorded
- plan/T0-baseline-verify-citations-validate-mode.yaml created
- Non-zero exit codes recorded without failure

**Verification Steps**:

- Run: `cat plan/T0-baseline-verify-citations-validate-mode.yaml`
- Confirm file exists and contains 6 criterion entries
- Confirm each entry has exit_code, stdout, stderr fields

## Task T1: Add CitationResult TypedDict and _extract_citations function

---
task: T1
status: NOT STARTED
dependencies: [T0]
priority: 1
complexity: Medium
agent: python3-development:python-cli-architect
---

Add the `CitationResult` TypedDict and `_extract_citations` function to `validate_research.py`, and add `httpx>=0.27.0` to the PEP 723 inline dependency block.

**Implementation details:**

Update the PEP 723 `# /// script` block so the `dependencies` list reads:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.21.0",
#   "httpx>=0.27.0",
# ]
# ///
```

Add `from __future__ import annotations` and a `TYPE_CHECKING` guard for the lazy `httpx` import:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx
```

Insert the `CitationResult` TypedDict immediately after the existing `Issue` TypedDict definition:

```python
class CitationResult(TypedDict):
    """Per-reference outcome from --verify-citations checks."""

    url: str
    """The canonical string that was checked: full URL, arXiv ID, or DOI."""

    status: str
    """Outcome: reachable | unreachable | invalid-format | invalid-arxiv | invalid-doi"""

    http_status: int | None
    """HTTP response code from HEAD/GET request, or None when no request was made."""

    check_type: str
    """Which checker was applied: url | arxiv | doi"""
```

Add three new module-level regex constants alongside the existing `URL_PATTERN`:

```python
_ARXIV_PATTERN = re.compile(r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b")
_ARXIV_VALID = re.compile(r"^\d{4}\.\d{4,5}(?:v\d+)?$")
_DOI_PATTERN = re.compile(r"\b(10\.\d{4,}/\S+)\b")
```

Implement `_extract_citations(content: str) -> list[dict[str, str]]` that:

- Scans the entire document (not restricted to the References section)
- Extracts URLs via the existing `URL_PATTERN`
- Extracts arXiv IDs via `_ARXIV_PATTERN.findall(content)`
- Extracts DOIs via `_DOI_PATTERN.findall(content)`
- Deduplicates using a `set` of `(check_type, url)` tuples
- Returns dicts with exactly two keys: `url` and `check_type`
- Ordering guarantee: URLs first (document order), then arXiv IDs, then DOIs

**Files**: `.claude/skills/research-curator/scripts/validate_research.py`

**Acceptance Criteria**:

- `CitationResult` TypedDict present in script after `Issue` TypedDict
- `httpx>=0.27.0` present in PEP 723 `dependencies` block
- `_ARXIV_PATTERN`, `_ARXIV_VALID`, `_DOI_PATTERN` constants defined at module level
- `_extract_citations` function defined with correct signature
- `_extract_citations("")` returns `[]`
- `_extract_citations` deduplicates: same URL appearing twice yields one entry
- Script still runs without error: `uv run .claude/skills/research-curator/scripts/validate_research.py --help`

**Verification Steps**:

- Run: `uv run .claude/skills/research-curator/scripts/validate_research.py --help`
- Confirm exit 0
- Run: `uv run python -c "import ast; ast.parse(open('.claude/skills/research-curator/scripts/validate_research.py').read()); print('parse ok')"`
- Confirm "parse ok"

## Task T2: Add three citation checker functions

---
task: T2
status: NOT STARTED
dependencies: [T1]
priority: 2
complexity: Medium
agent: python3-development:python-cli-architect
---

Add `_check_url_reachability`, `_check_arxiv_id`, and `_check_doi` to `validate_research.py`.

**Implementation details:**

`_check_url_reachability(url: str, client: httpx.Client) -> CitationResult`:

- Validates that `url` starts with `http://` or `https://`; if not, return `CitationResult(url=url, status="invalid-format", http_status=None, check_type="url")` without making a network request
- Sends an HTTP HEAD request via the shared `client` (which has `follow_redirects=True` and `httpx.Timeout(10.0)` configured)
- 2xx final response → `status="reachable"`, `http_status=<code>`
- Non-2xx final response → `status="unreachable"`, `http_status=<code>`
- Any `httpx.TimeoutException` or `httpx.RequestError` → `status="unreachable"`, `http_status=None`

`_check_arxiv_id(arxiv_id: str) -> CitationResult`:

- No network request made
- Apply `re.fullmatch(_ARXIV_VALID, arxiv_id)`; match → `status="reachable"`, no match → `status="invalid-arxiv"`
- `http_status` is always `None`
- `check_type` is always `"arxiv"`

`_check_doi(doi: str, client: httpx.Client) -> CitationResult`:

- Sends `GET https://api.crossref.org/works/{doi}` via the shared `client`
- HTTP 200 → `status="reachable"`, `http_status=200`
- HTTP 404 → `status="invalid-doi"`, `http_status=404`
- Any other HTTP status → `status="unreachable"`, `http_status=<code>`
- Any `httpx.TimeoutException` or `httpx.RequestError` → `status="unreachable"`, `http_status=None`
- The `User-Agent: research-curator-validator/1.0` header is set on the shared client at construction time (not per-request here)

**Files**: `.claude/skills/research-curator/scripts/validate_research.py`

**Acceptance Criteria**:

- `_check_url_reachability` defined with correct signature `(url: str, client: httpx.Client) -> CitationResult`
- `_check_arxiv_id` defined with correct signature `(arxiv_id: str) -> CitationResult`
- `_check_doi` defined with correct signature `(doi: str, client: httpx.Client) -> CitationResult`
- Script parses without error after changes
- `_check_arxiv_id("2301.12345")` returns `status="reachable"` (verifiable via unit test or inline check)
- `_check_arxiv_id("not-an-id")` returns `status="invalid-arxiv"`

**Verification Steps**:

- Run: `uv run python -c "import ast; ast.parse(open('.claude/skills/research-curator/scripts/validate_research.py').read()); print('parse ok')"`
- Confirm "parse ok"
- Run: `uv run .claude/skills/research-curator/scripts/validate_research.py --help`
- Confirm exit 0 and `--verify-citations` not yet present (flag added in T3)

## Task T3: Integrate citation verification into validate_file and main

---
task: T3
status: NOT STARTED
dependencies: [T2]
priority: 2
complexity: High
agent: python3-development:python-cli-architect
---

Wire the citation verification path into `validate_file` and `main`, add the `--verify-citations` CLI flag, implement `_verify_entry_citations`, and ensure the lazy `httpx` import pattern is correct.

**Implementation details:**

Add `_VERIFY_CITATIONS_OPT` module-level constant:

```python
_VERIFY_CITATIONS_OPT: bool = typer.Option(
    False,
    "--verify-citations",
    help=(
        "Check URL reachability, arXiv ID format, and DOI resolution via CrossRef "
        "(requires network access; omit in CI pipelines)"
    ),
)
```

Implement `_verify_entry_citations(entry_path: Path, client: httpx.Client) -> list[CitationResult]`:

- Reads the entry file via `entry_path.read_text()`
- Calls `_extract_citations(content)` to get the deduplicated citation list
- Dispatches each item to the appropriate checker based on `check_type`:
  - `"url"` → `_check_url_reachability(item["url"], client)`
  - `"arxiv"` → `_check_arxiv_id(item["url"])`
  - `"doi"` → `_check_doi(item["url"], client)`
- Returns `list[CitationResult]` in same order as `_extract_citations` output (URLs, arXiv, DOIs)
- Returns `[]` if the file contains no extractable citations

Update `validate_file` signature from:

```python
def validate_file(path: Path, research_root: Path) -> dict[str, Any]:
```

to:

```python
def validate_file(
    path: Path,
    research_root: Path,
    verify_citations: bool = False,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
```

Inside `validate_file`, after all existing checks, add:

```python
if verify_citations and http_client is not None:
    citation_results = _verify_entry_citations(path, http_client)
    for result in citation_results:
        if result["status"] not in ("reachable",):
            all_issues.append({
                "check": "citation_verification",
                "severity": "warning",
                "message": f"{result['check_type']} {result['url']}: {result['status']}",
                "line": None,
            })
    entry_dict["citation_verification"] = citation_results
```

Update the `main` command signature to include the new option:

```python
@app.command()
def main(
    path: Path = _PATH_ARG,
    output_json: bool = _JSON_OPT,
    verbose: bool = _VERBOSE_OPT,
    verify_citations: bool = _VERIFY_CITATIONS_OPT,
) -> None:
```

Inside `main`, add the lazy import and `try/finally` client lifecycle:

```python
http_client: httpx.Client | None = None
if verify_citations:
    import httpx  # lazy import — only when flag is active
    http_client = httpx.Client(
        follow_redirects=True,
        timeout=httpx.Timeout(10.0),
        headers={"User-Agent": "research-curator-validator/1.0"},
    )

try:
    for file_path in files:
        entry = validate_file(
            file_path,
            research_root,
            verify_citations=verify_citations,
            http_client=http_client,
        )
        entries.append(entry)
finally:
    if http_client is not None:
        http_client.close()
```

**Files**: `.claude/skills/research-curator/scripts/validate_research.py`

**Acceptance Criteria**:

- `uv run .claude/skills/research-curator/scripts/validate_research.py --help` exits 0 and output contains `--verify-citations`
- `uv run .claude/skills/research-curator/scripts/validate_research.py --json ./research/agent-frameworks/AutoResearchClaw.md` exits 0 and output does NOT contain `citation_verification`
- `uv run .claude/skills/research-curator/scripts/validate_research.py --json --verify-citations ./research/agent-frameworks/AutoResearchClaw.md` exits 0 and output contains `citation_verification`
- Script parses without error
- `_verify_entry_citations` function defined with correct signature

**Verification Steps**:

- Run: `uv run .claude/skills/research-curator/scripts/validate_research.py --help`
- Confirm exit 0 and `--verify-citations` present in output (AC1 satisfied)
- Run: `uv run .claude/skills/research-curator/scripts/validate_research.py --json ./research/agent-frameworks/AutoResearchClaw.md`
- Confirm exit 0 and `citation_verification` absent from output (AC2 satisfied)
- Run: `uv run .claude/skills/research-curator/scripts/validate_research.py --json --verify-citations ./research/agent-frameworks/AutoResearchClaw.md`
- Confirm exit 0 and `citation_verification` present in output (AC3 satisfied)

## Task T4: Update SKILL.md validate mode documentation

---
task: T4
status: NOT STARTED
dependencies: [T3]
priority: 3
complexity: Low
agent: plugin-creator:contextual-ai-documentation-optimizer
---

Update `.claude/skills/research-curator/SKILL.md` to document the `--verify-citations` flag in the validate mode section.

**Implementation details:**

Locate the "What Gets Checked" table inside the `## Validate Mode` section. Add a new row:

```text
| Citation verification | Warning | When `--verify-citations` is passed: checks URL reachability via HTTP HEAD, validates arXiv ID format, and resolves DOIs via CrossRef API. Results appear in `citation_verification` per-entry JSON key and as warning issues. Does not affect `pass`/`fail` status. |
```

Locate the bash invocation examples subsection. After the existing single-file and directory examples, add:

```bash
# Citation verification (requires network; adds citation_verification to JSON output)
uv run .claude/skills/research-curator/scripts/validate_research.py --json --verify-citations ./research/{category}/{name}.md

# Directory-wide link-rot audit
uv run .claude/skills/research-curator/scripts/validate_research.py --json --verify-citations ./research/
```

Locate the JSON output example in the Validate Mode section. After the existing example, add a supplementary example under the heading "JSON output with --verify-citations" showing the extended shape when `--verify-citations` is active. The example must show the `citation_verification` array with entries covering `url`, `status`, `http_status`, and `check_type` fields, including at least one `reachable` URL result and one `unreachable` URL result with a citation_verification warning in the `issues` list.

Add a note confirming that citation verification warnings (`citation_verification` check) follow the same handling path as other warnings: reported to the user but not auto-fixed by `--fix` mode.

**Files**: `.claude/skills/research-curator/SKILL.md`

**Acceptance Criteria**:

- `grep -c 'verify-citations' .claude/skills/research-curator/SKILL.md` exits 0 with count >= 1 (AC4 satisfied)
- The "What Gets Checked" table contains a "Citation verification" row
- At least one invocation example with `--verify-citations` is present
- JSON output example showing `citation_verification` key is present
- Note about warnings not being auto-fixable is present

**Verification Steps**:

- Run: `grep -c 'verify-citations' .claude/skills/research-curator/SKILL.md`
- Confirm exit 0 and count >= 1
- Run: `uv run prek run --files .claude/skills/research-curator/SKILL.md`
- Confirm no linting errors

## Task T5: Update validation-rules.md with citation verification rules

---
task: T5
status: NOT STARTED
dependencies: [T3]
priority: 3
complexity: Low
agent: plugin-creator:contextual-ai-documentation-optimizer
---

Update `.claude/skills/research-curator/references/validation-rules.md` to define the three citation verification rules and extend the JSON schema section with the `CitationResult` object definition.

**Implementation details:**

Locate the Warning severity subsection (which currently includes `access_dates`, `freshness_tracking`, `statistics_currency`, `url_format`, `cross_references_absent`). Add three new entries in a logical grouping under a "Citation Verification warnings (when `--verify-citations` is active)" subheading:

- `citation_url_unreachable` — A URL in the entry returned a non-2xx HTTP response or could not be reached (timeout, DNS failure, TLS error). Severity: `warning`. The `CitationResult.status` value is `unreachable` or `invalid-format`.

- `citation_arxiv_invalid` — An arXiv ID in the entry does not match the expected format (`YYMM.NNNNN` with optional `vN` suffix). Severity: `warning`. The `CitationResult.status` value is `invalid-arxiv`.

- `citation_doi_invalid` — A DOI in the entry returned HTTP 404 from the CrossRef API (`https://api.crossref.org/works/{doi}`). Severity: `warning`. The `CitationResult.status` value is `invalid-doi`.

Include a note clarifying that the `check` field in the emitted `Issue` TypedDict is always `"citation_verification"` for all three cases, and the distinction between URL/arXiv/DOI is carried by the `CitationResult` `check_type` and `status` fields.

Locate the JSON output schema section. After the existing entry dict schema, add a "Per-Entry `citation_verification` key (when `--verify-citations` active)" subsection with a table documenting the `CitationResult` object fields:

| Field | Type | Values |
|-------|------|--------|
| `url` | `string` | The checked string: full URL, arXiv ID (e.g. `2301.12345`), or DOI (e.g. `10.1234/x`) |
| `status` | `string` | `reachable` \| `unreachable` \| `invalid-format` \| `invalid-arxiv` \| `invalid-doi` |
| `http_status` | `integer \| null` | HTTP response code, or `null` when no network request was made |
| `check_type` | `string` | `url` \| `arxiv` \| `doi` |

Include a note that the key is absent from the entry dict when `--verify-citations` is not passed.

**Files**: `.claude/skills/research-curator/references/validation-rules.md`

**Acceptance Criteria**:

- `grep -c 'citation' .claude/skills/research-curator/references/validation-rules.md` exits 0 with count >= 3 (AC5 satisfied)
- `citation_url_unreachable` rule entry present
- `citation_arxiv_invalid` rule entry present
- `citation_doi_invalid` rule entry present
- `CitationResult` JSON schema table present

**Verification Steps**:

- Run: `grep -c 'citation' .claude/skills/research-curator/references/validation-rules.md`
- Confirm exit 0 and count >= 3
- Run: `uv run prek run --files .claude/skills/research-curator/references/validation-rules.md`
- Confirm no linting errors

## Task T6: Update research-curator agent with citation_verification non-fixable rule

---
task: T6
status: NOT STARTED
dependencies: [T3]
priority: 3
complexity: Low
agent: plugin-creator:contextual-ai-documentation-optimizer
---

Update `.claude/agents/research-curator.md` to document that `citation_verification` issues are warning-only and NOT auto-fixable by `--fix` mode.

**Implementation details:**

Locate the `--fix` mode section (at approximately lines 431-437 based on the architecture spec). After the existing fix instructions (which cover structural errors and warnings that can be auto-repaired), add a clearly separated subsection:

```markdown
### Citation Verification Issues (--verify-citations findings)

Issues with `"check": "citation_verification"` are **warning-severity only** and are
**never auto-fixable**. When the orchestrator passes citation verification issues in the
issues list, the agent must:

1. Include them in the validation report output under a "Citation Warnings" heading.
2. Describe each finding: which URL/arXiv ID/DOI failed, and what the failure status was.
3. NOT attempt to modify the research entry file to fix or remove the citations.
4. NOT emit any "fix applied" record for citation_verification issues.

Citation verification failures require human judgment — a URL may be temporarily down,
an arXiv ID may be in a format that is valid but from an older era, or a DOI may resolve
via an alternative registry. The agent surfaces the findings; the human decides the action.
```

**Files**: `.claude/agents/research-curator.md`

**Acceptance Criteria**:

- `grep -c 'citation_verification' .claude/agents/research-curator.md` exits 0 with count >= 1 (AC6 satisfied)
- "Citation Verification Issues" subsection present in the `--fix` mode section
- Rule explicitly states issues are NOT auto-fixable
- Four-point list of required agent behaviours present

**Verification Steps**:

- Run: `grep -c 'citation_verification' .claude/agents/research-curator.md`
- Confirm exit 0 and count >= 1
- Run: `uv run prek run --files .claude/agents/research-curator.md`
- Confirm no linting errors

## Task T7: Verification Gate

---
task: T7
status: NOT STARTED
dependencies: [T4, T5, T6]
priority: 4
complexity: Low
agent: python3-development:tn-verification-gate
---

Read `plan/T0-baseline-verify-citations-validate-mode.yaml`, re-run all 6 check_commands, classify each criterion against the 4-cell matrix, and write `plan/TN-verification-verify-citations-validate-mode.yaml`.

**Implementation details:**

Read `plan/T0-baseline-verify-citations-validate-mode.yaml` to retrieve the baseline exit codes, stdout, and stderr for all 6 criteria.

Re-run each `check_command` from `acceptance_criteria_structured` and capture exit code, stdout, and stderr.

Classify each criterion using the 4-cell matrix:

- T0 pass + TN pass → `passed`
- T0 pass + TN fail → `regressed` (blocks release)
- T0 fail + TN fail → `pre-existing-fail`
- T0 fail + TN pass → `newly-passing`

Determine pass/fail for each criterion by evaluating `pass_condition` against the TN run output.

Write `plan/TN-verification-verify-citations-validate-mode.yaml` as a list of `BookendVerification` records, one per criterion, each with fields: `criterion_id`, `check_command`, `t0_exit_code`, `tn_exit_code`, `status`, `stdout_diff_summary`.

**Acceptance Criteria**:

- `plan/TN-verification-verify-citations-validate-mode.yaml` created
- All 6 criteria present in the output file
- Each entry has `criterion_id`, `check_command`, `t0_exit_code`, `tn_exit_code`, `status`, `stdout_diff_summary`
- No criterion has `status: regressed`
- AC1 (--verify-citations in --help): `status: newly-passing` or `passed`
- AC2 (no citation_verification without flag): `status: newly-passing` or `passed`
- AC3 (citation_verification with flag): `status: newly-passing` or `passed`
- AC4 (SKILL.md documents flag): `status: newly-passing` or `passed`
- AC5 (validation-rules.md defines rules): `status: newly-passing` or `passed`
- AC6 (agent documents non-fixable): `status: newly-passing` or `passed`

**Verification Steps**:

- Run: `cat plan/TN-verification-verify-citations-validate-mode.yaml`
- Confirm file exists and contains 6 criterion entries
- Confirm no entry has `status: regressed`
- Confirm all 6 criteria are `newly-passing` or `passed`

---

## Context Manifest

Generated by context-gathering agent on 2026-03-19

### How This Currently Works: Citation Verification in validate_research.py

The validate_research.py script is a PEP 723 standalone Python script (requires >=3.11) that validates research entry markdown files against the research-curator quality standard. The current implementation (without --verify-citations) performs purely structural validation:

**Current Validation Flow:**
1. CLI entry point via Typer: the main() command accepts path, --json, and --verbose options
2. File collection: collect_files() traverses directories or validates single files, excluding README.md
3. Per-file validation in validate_file(): orchestrates sequential checks, each returning list[Issue]
4. Existing checks (in order): section_completeness → header_fields → empty_sections → access_dates → freshness_tracking → statistics_currency → url_format → formatting_suggestions
5. Results aggregation: each Issue has check (string), severity (error/warning/info), message, line number
6. Output: JSON summary + per-entry dict with file, status (pass/fail), issues list; or human-readable text with markers
7. Exit code: 1 if any error-severity issues, else 0

**Key Existing Patterns to Follow:**
- Issues are returned as list[Issue] TypedDict (check, severity, message, line)
- Warning-severity issues do not cause fail status; only error-severity does
- URL extraction via URL_PATTERN regex already exists at module level
- References section extraction logic is in _check_access_dates (lines 175-200) — iterates ref_section line range and finds URLs
- Typer option declarations follow _PATH_ARG, _JSON_OPT, _VERBOSE_OPT pattern
- validate_file signature is (path, research_root, today) → dict[str, Any]

**When --verify-citations is added:**
The feature extends this flow with an optional network-based citation verification step. The three citation types (URLs, arXiv IDs, DOIs) are extracted from the FULL DOCUMENT (per architecture spec, ADR-003), not just References section. Each extracted citation is dispatched to an appropriate checker function that returns a CitationResult dict. Failed results generate warning-severity Issues. All results (pass + fail) are collected in a new citation_verification key added to the entry dict.

### For New Feature Implementation: Citation Verification Integration Points

**New TypedDict: CitationResult**
Added immediately after existing Issue definition (around line 26):
- url: str (the matched string: full URL, arXiv ID like 2301.12345, or DOI like 10.1234/x)
- status: str (one of: reachable, unreachable, invalid-format, invalid-arxiv, invalid-doi)
- http_status: int | None (HTTP response code, or None when no request made)
- check_type: str (one of: url, arxiv, doi)

**New Module-Level Constants:**
- _VERIFY_CITATIONS_OPT: typer.Option for the CLI flag
- _ARXIV_PATTERN: regex pattern for extracting arXiv IDs
- _ARXIV_VALID: regex for format validation of arXiv IDs
- _DOI_PATTERN: regex for extracting DOIs

**New PEP 723 Dependency:**
httpx>=0.27.0 is added to the existing dependencies block. httpx is imported lazily inside the --verify-citations branch only to avoid overhead when flag is absent.

**Five New Private Functions:**

1. _extract_citations(content: str) → list[dict[str, str]]
   - Reads full document content
   - Extracts URLs via URL_PATTERN.findall(), arXiv IDs via _ARXIV_PATTERN.findall(), DOIs via _DOI_PATTERN.findall()
   - Deduplicates and returns list of {url, check_type} dicts in order: URLs, arXiv, DOIs

2. _check_url_reachability(url: str, client: httpx.Client) → CitationResult
   - Validates URL scheme without making request if invalid
   - Makes HTTP HEAD request via client (follow_redirects=True, timeout=10s)
   - Returns CitationResult with appropriate status and http_status

3. _check_arxiv_id(arxiv_id: str) → CitationResult
   - No network request made
   - Format validation only via regex fullmatch
   - Returns status=reachable or status=invalid-arxiv

4. _check_doi(doi: str, client: httpx.Client) → CitationResult
   - Makes GET to https://api.crossref.org/works/{doi}
   - User-Agent header set on client at construction
   - Returns appropriate status based on response

5. _verify_entry_citations(entry_path: Path, client: httpx.Client) → list[CitationResult]
   - Reads file, extracts citations, dispatches each to appropriate checker
   - Returns list of CitationResult dicts

**Modified Functions:**

validate_file() signature changes to accept verify_citations bool and http_client optional parameter. When flag is True, citation verification is performed and results added to entry dict under citation_verification key. Failed results generate warning-severity Issues.

main() signature adds verify_citations parameter. When True, httpx.Client is created lazily and shared across all file validations. Client is closed in finally block.

**httpx.Client Configuration:**
- follow_redirects=True
- timeout=httpx.Timeout(10.0) for 10-second total timeout
- headers with User-Agent: research-curator-validator/1.0
- verify=True (default TLS verification)

**JSON Output Schema:**
- citation_verification key present only when --verify-citations is active
- Key contains list of CitationResult dicts with all check results (pass + fail)
- Failed results also appear as warning-severity Issues in issues list
- Entry status (pass/fail) unchanged by citation failures

**Documentation Changes:**
Three files require updates:
1. SKILL.md: Add citation verification to validation checks table, add --verify-citations examples, show citation_verification JSON key, confirm warnings not auto-fixed
2. validation-rules.md: Add three citation verification rules (citation_url_unreachable, citation_arxiv_invalid, citation_doi_invalid) and CitationResult JSON schema
3. research-curator.md: Add rule that citation_verification issues are WARNING-ONLY and NEVER auto-fixable

### Technical Reference Details

**File Paths (relative to repo root):**
- Implementation: .claude/skills/research-curator/scripts/validate_research.py
- SKILL.md: .claude/skills/research-curator/SKILL.md
- Validation rules: .claude/skills/research-curator/references/validation-rules.md
- Agent: .claude/agents/research-curator.md

**Import Pattern with TYPE_CHECKING:**
Use TYPE_CHECKING guard to allow type annotations of httpx.Client without runtime import at module level.

**Regex Patterns:**
- URL_PATTERN (existing): https?://[^\s>)\]]+
- _ARXIV_PATTERN: \b(\d{4}\.\d{4,5}(?:v\d+)?)\b
- _ARXIV_VALID: ^\d{4}\.\d{4,5}(?:v\d+)?$
- _DOI_PATTERN: \b(10\.\d{4,}/\S+)\b

**Status Values per Check Type:**
- url: reachable, unreachable, invalid-format
- arxiv: reachable, invalid-arxiv
- doi: reachable, invalid-doi, unreachable

**Acceptance Criteria:**
AC1-AC6 are testable via grep commands and JSON structure validation as specified in task file lines 10-31. Each task in the plan (T1-T6) directly implements these criteria.
