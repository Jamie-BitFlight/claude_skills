---
name: Add automated citation verification to research-curator validate mode
description: <div><sub>2026-03-19T02:20:14Z</sub>
metadata:
  topic: add-automated-citation-verification-to-research-curator-vali
  source: 'Research entry: ./research/agent-frameworks/AutoResearchClaw.md -- pattern: 4-layer citation verification'
  added: '2026-03-19'
  priority: P2
  type: Feature
  status: in-progress
  issue: '#845'
  last_synced: '2026-03-21T08:07:31Z'
  groomed: '2026-03-19'
  plan: plan/tasks-6-verify-citations-validate-mode.md
---

## RT-ICA

<div><sub>2026-03-19T02:20:14Z</sub>

RT-ICA Snapshot: Add automated citation verification to research-curator validate mode
Goal: Add `--verify-citations` flag to `validate_research.py` that checks URL reachability, arXiv ID format, and DOI resolution, flagging dead/hallucinated references as warning-severity issues in JSON output.

Conditions:
1. `validate_research.py` CLI interface, Issue TypedDict, JSON output schema | Status: DERIVABLE
2. Citation formats in research entries (URL/arXiv/DOI patterns in .md files) | Status: DERIVABLE
3. CrossRef/DataCite API endpoints and response format | Status: DERIVABLE
4. arXiv ID format spec (`\d{4}\.\d{4,5}(v\d+)?`) | Status: AVAILABLE
5. HTTP library in script dependencies (currently `typer` only; new dep needed) | Status: DERIVABLE
6. `--verify-citations` flag integration with existing `--json` and validate workflow | Status: DERIVABLE
7. Warning-severity issues are reported but not auto-fixed (from SKILL.md spec) | Status: AVAILABLE

AVAILABLE count: 2
DERIVABLE count: 5
MISSING count: 0
</div>

## Groomed (2026-03-19)

### Impact Radius

<div><sub>2026-03-19T02:21:29Z</sub>

### Scope

<div><sub>2026-03-19T02:23:25Z</sub>

**In scope:**
- `--verify-citations` flag added to `validate_research.py` (off by default)
- URL reachability check via HTTP HEAD request (report non-2xx status)
- arXiv ID format validation via regex (`\d{4}\.\d{4,5}(v\d+)?`)
- DOI resolution via CrossRef public API (`https://api.crossref.org/works/{doi}`)
- Warning-severity JSON output in a new `citation_verification` section
- `SKILL.md` validate mode section update to document the new flag and output schema
- `references/validation-rules.md` update with new check definitions and severity mapping
- `research-curator.md` agent instruction update to handle `citation_verification` issue type

**Out of scope:**
- Auto-fixing dead or hallucinated citations (warnings only; user decides)
- Email or ORCID verification
- Authenticated API calls (CrossRef public API is used unauthenticated)
- Changes to existing error-severity checks or the existing `--validate` output schema
</div>

### Acceptance Criteria

<div><sub>2026-03-19T02:23:35Z</sub>

- [ ] Running `uv run .claude/skills/research-curator/scripts/validate_research.py --json --verify-citations ./research/agent-frameworks/AutoResearchClaw.md` produces JSON output containing a `citation_verification` section with per-URL status entries (each entry includes: URL, status (`reachable` / `unreachable` / `invalid-format`), and HTTP status code or error reason where applicable).
- [ ] At least one entry with a fabricated or dead URL in the target file produces a warning-severity finding in the `citation_verification` section.
- [ ] The `--verify-citations` flag is off by default: running without it makes no network calls and produces no `citation_verification` section in output.
- [ ] Existing `--validate` behavior is unchanged: all structural checks (missing fields, broken local links, malformed frontmatter) continue to produce identical output when `--verify-citations` is absent.
- [ ] Valid arXiv IDs matching `\d{4}\.\d{4,5}(v\d+)?` pass format validation; malformed IDs produce a warning-severity finding.
- [ ] Valid DOIs return 200 from CrossRef `/works/{doi}` and are recorded as `reachable`; DOIs returning 404 are recorded as `unreachable` with a warning-severity finding.
- [ ] `SKILL.md` validate mode section documents the `--verify-citations` flag, its effect, and includes an updated JSON output example showing the `citation_verification` section.
- [ ] `references/validation-rules.md` contains a `citation_verification` check definition with severity mapping (warning) and expected JSON schema.
- [ ] `research-curator.md` agent instructions cover how to handle `citation_verification` warning issues (distinguish mechanical fixes from research-required fixes).
</div>

### Files

<div><sub>2026-03-19T02:23:47Z</sub>

- `.claude/skills/research-curator/scripts/validate_research.py` — add `--verify-citations` CLI flag; implement `_check_url_reachability()` (HTTP HEAD), `_check_arxiv_id()` (regex validation), `_check_doi()` (CrossRef API lookup); extend JSON output with `citation_verification` section containing per-URL status entries
- `.claude/skills/research-curator/SKILL.md` — document `--verify-citations` flag in validate mode section; update "What Gets Checked" bullet list; update JSON output schema examples to show `citation_verification` section and warning-severity findings
- `.claude/skills/research-curator/references/validation-rules.md` — add `citation_verification` check definitions (URL reachability, arXiv format, DOI resolution); document severity mapping (warning); document expected JSON schema for `citation_verification` entries; add rule that citation verification warnings are reported but not auto-fixed
- `.claude/agents/research-curator.md` — update fix-mode instructions to recognize and handle `citation_verification` issue type; distinguish mechanical fixes (add access date, fix arXiv format) from research-required fixes (locate replacement URL, verify DOI exists)
</div>

### Dependencies

<div><sub>2026-03-19T02:23:51Z</sub>

- `httpx>=0.27.0` — add as PEP 723 inline dependency in `validate_research.py`. Preferred over `requests`: async-capable, modern API, widely used in Python tooling. Both `httpx.head()` and `httpx.get()` are available for sync use.
- CrossRef public API (`https://api.crossref.org/works/{doi}`) — no authentication required; rate limit is generous for validation use.
- arXiv ID format validation — stdlib `re` module; no external dependency.
- No new infrastructure dependencies (no database, no secrets, no CI job changes required).
</div>

### Effort

<div><sub>2026-03-19T02:24:01Z</sub>

**Estimate**: Medium

- Script changes are self-contained: one file (`validate_research.py`), one new CLI flag, three verification functions (URL HEAD check, arXiv regex, DOI CrossRef lookup). No existing logic is altered.
- Documentation updates are mechanical: SKILL.md validate section and validation-rules.md both have clear, bounded update targets.
- Agent instruction update is small: one new issue type and its handling rules added to `research-curator.md`.
- No migration required: feature is additive and backward-compatible (flag off by default).
- No new infrastructure: single PEP 723 dep addition (`httpx`), public API (no auth).

**Estimated**: 1 focused implementation session.
</div>

### Research

<div><sub>2026-03-19T02:24:14Z</sub>

Key findings from Wave 1 fact-check (2026-03-19):

**CrossRef DOI API**: Use `https://api.crossref.org/works/{doi}` — returns 200 on valid DOI, 404 on invalid. No authentication required. DataCite provides a parallel endpoint at `https://api.datacite.org/dois/{id}` as fallback. SOURCE: [CrossRef REST API Docs](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) (accessed 2026-03-19).

**arXiv ID regex**: Era-dependent format — 4-digit sequence pre-2015 (`YYMM.NNNN`), 5-digit from January 2015 onward (`YYMM.NNNNN`). Combined regex: `\d{4}\.\d{4,5}(v\d+)?`. Optional version suffix `vN` is valid. SOURCE: [arXiv Identifier Help](https://info.arxiv.org/help/arxiv_identifier.html) (accessed 2026-03-19).

**HTTP HEAD reachability**: Standard practice for link checking (used by Sphinx linkcheck, MkDocs, lychee). Returns headers only — no body download. Reports 2xx (reachable), non-2xx (unreachable), connection error (unreachable). SOURCE: [MDN HEAD method](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/HEAD).

**httpx preference**: `httpx.head()` available sync and async; `httpx.get()` as fallback for servers that reject HEAD. Preferred over `requests`: async-capable, modern API. Both verified to support HEAD as a first-class method. SOURCE: [HTTPX API Docs](https://www.python-httpx.org/api/).

**Opt-in flag pattern**: Standard in Python validation tooling. Sphinx uses `-b linkcheck` (explicit invocation), lychee uses `--offline` to disable, MkDocs uses configuration-gated link validation. `--verify-citations` (off by default) follows this established convention.
</div>

### Prior Work

<div><sub>2026-03-19T02:24:26Z</sub>

**Self-healing / auto-fix**: Tracked separately in backlog items #449, #448, #87, #85. Citation verification (this item) is distinct — it detects and reports dead/hallucinated citations as warnings; it does not auto-fix them. No prior overlap.

**Citation verification specifically**: No prior backlog item found for automated citation checking in research-curator validate mode. This is a net-new capability.

**Source pattern**: The 4-layer citation verification model in `./research/agent-frameworks/AutoResearchClaw.md` (arXiv lookup → CrossRef/DOI → Semantic Scholar → LLM relevance) was the direct inspiration. This item implements layers 1–3 (format/reachability checks) as a static validator; layer 4 (LLM relevance) is explicitly out of scope.
</div>


## Impact Radius

### Code Producers

**File**: `.claude/skills/research-curator/scripts/validate_research.py`

**Impact of adding `--verify-citations` flag**:

1. **Will it break?** No. Flag is new, defaults to off. Existing `--json`, `--verbose` flags unaffected. Backward compatible.
2. **Will it become stale?** No. Script is the implementation source; documentation derives from it.
3. **Code change needed?** Yes. Add `--verify-citations` CLI option, `_verify_citations()` function(s), new HTTP request logic for URL/arXiv/DOI checks.
4. **Content update needed?** No (code-only change).
5. **Test coverage?** Unknown. No test file found. Recommend adding test suite: `tests/test_validate_research.py` with cases for reachable/unreachable URLs, valid/invalid arXiv IDs, DOI resolution.

---

### Code Consumers

#### 1. `.claude/skills/research-curator/SKILL.md` — Validate Mode orchestration (lines 275–350)

**Impact of feature addition**:

1. **Will it break?** No. Existing `--validate` invocation unaffected (new flag is optional).
2. **Will it become stale?** Yes. Documentation describes current behavior (structural checks only). Once `--verify-citations` is live, examples and JSON output schema must be updated to show the new citation_verification section and warning-severity findings.
3. **Code change needed?** No (documentation file).
4. **Content update needed?** Yes. Update:
   - "What Gets Checked" section: add bullet for citation verification (off by default)
   - Validation Workflow diagram: cite new flag option in script invocation
   - JSON output schema in references/validation-rules.md: extend Issue TypedDict with optional citation verification fields
   - Example JSON output: show citation_verification issues in entries
5. **Test coverage?** Not applicable (documentation).

**Stale risks**: If SKILL.md is not updated when `--verify-citations` is added, users will not know the flag exists or how to use it. Documentation drift will prevent feature adoption.

---

#### 2. `.claude/agents/research-curator.md` — Fix agent (receives validation issues)

**Impact of feature addition**:

1. **Will it break?** Possibly. Agent currently receives error-severity issues only (e.g., missing sections, empty fields). When `--verify-citations` runs, citation-verification warnings may be included in the fix request. Agent must handle new issue types.
2. **Will it become stale?** Yes. Agent instructions must note how to handle citation verification issues (e.g., update References with live URLs, add access dates, validate arXiv IDs).
3. **Code change needed?** Yes. Agent prompt must be updated to:
   - Recognize citation verification warnings (new issue type)
   - Know how to respond (update URL, add access date, verify arXiv ID format, check DOI exists)
   - Distinguish mechanical fixes (missing access date) from research-required fixes (update stale URL)
4. **Content update needed?** Yes. Add section describing how agent responds to citation verification issues.
5. **Test coverage?** Unknown. Depends on agent test setup (not found in standard locations).

**Stale risks**: If agent is not updated, it will reject citation verification issues as unknown, or attempt to fix them without understanding they require research/verification.

---

### Documentation

#### 1. `.claude/skills/research-curator/references/validation-rules.md` — Check definitions

**Impact of feature addition**:

1. **Will it break?** No. Reference file is descriptive, not executable.
2. **Will it become stale?** Yes. Must document the new citation verification checks: URL reachability (HTTP HEAD), arXiv ID format, DOI resolution. These are new checks, not currently listed.
3. **Code change needed?** No.
4. **Content update needed?** Yes. Add new section:
   - **citation_verification** (warning severity): Documents URL reachability check, arXiv format validation, DOI API lookup, expected JSON schema for results.
   - Update JSON Output Schema to include `citation_verification` field in Issue TypedDict.
   - Add rule: citation verification warnings are reported but not auto-fixed (user decides whether to update).
5. **Test coverage?** Not applicable.

**Stale risks**: Critical. If validation rules are not updated, the orchestrator (SKILL.md Validate Mode section) will not know how to interpret citation verification issues from the JSON output.

---

#### 2. `.claude/skills/research-curator/SKILL.md` — Validate Mode section (lines 275–350)

*Already covered above under Code Consumers.*

---

### Configuration / CI

**Finding**: No CI workflows directly invoke `validate_research.py`. Validation is orchestrator-driven via `/research-curator --validate` skill invocation, which is manual or backlog-triggered, not automated.

**Impact of feature addition**:

1. **Will it break?** No. No CI dependencies.
2. **Will it become stale?** N/A.
3. **Code change needed?** No. (Recommendation: Consider adding optional CI job to validate research entries on PRs, but not required for this feature.)
4. **Content update needed?** No.
5. **Test coverage?** N/A.

---

### Agent Instructions

#### `.claude/agents/research-curator.md` — Already analyzed above under Code Consumers.

---

### Systems Inventory

| System | File | Role | Impact | Stale Risk |
|--------|------|------|--------|-----------|
| Validator script | `.claude/skills/research-curator/scripts/validate_research.py` | Producer | Add citation verification logic | Low (code is source) |
| SKILL.md Validate Mode | `.claude/skills/research-curator/SKILL.md` lines 275–350 | Consumer (orchestrator) | Update workflow docs & examples | High (must document new flag) |
| Validation rules reference | `.claude/skills/research-curator/references/validation-rules.md` | Consumer (documentation) | Add citation verification check definitions | High (orchestrator depends on it) |
| research-curator agent | `.claude/agents/research-curator.md` | Consumer (fix implementation) | Handle new citation verification issue types | High (must know new issue types) |
| CI workflows | `.github/workflows/*.yml` | Not directly used | No change required | N/A |

---

### Ecosystem Completeness Checklist

- [x] **1. Will `--verify-citations` break existing code?** No. Flag is additive; defaults to off.
- [x] **2. Will documentation become stale?** Yes (HIGH). SKILL.md, validation-rules.md, and research-curator.md must be updated to document flag, new checks, and agent fix logic.
- [x] **3. Does the script need code changes?** Yes. Add CLI flag, citation verification functions (HTTP HEAD, arXiv format check, DOI API lookup).
- [x] **4. Does the orchestrator (SKILL.md) need content updates?** Yes. Update "What Gets Checked", workflow diagram, JSON schema, example output.
- [x] **5. Does the agent need to be updated?** Yes. Must handle citation verification issues; distinguish mechanical fixes from research-required ones.
- [x] **6. Is there test coverage for the interaction?** No tests found. Recommend adding `tests/test_validate_research.py` and agent fix test cases.
- [x] **7. Are there downstream systems that depend on validator output?** Yes. research-curator agent receives JSON output; orchestrator (SKILL.md) parses JSON. Both must understand new citation_verification issues.
- [ ] **8. Are there rollback concerns?** No. Feature is additive and off-by-default.

**Completeness Score**: 3/3 critical updates required (script, SKILL.md, validation-rules.md); 1 high recommendation (agent); 1 test gap.

**Critical Path**:
1. Implement script changes + new CLI flag
2. Update validation-rules.md with new check definitions and JSON schema
3. Update SKILL.md Validate Mode section with flag documentation and updated examples
4. Update research-curator agent prompt to handle citation verification issues
5. Add test suite covering citation verification behavior
</div>

## Fact-Check

<div><sub>2026-03-19T02:21:46Z</sub>

## Fact-Check Results (2026-03-19)

### Claim 1: CrossRef provides a DOI resolution API
**Status**: PARTIALLY VERIFIED

**Evidence**: CrossRef provides a REST API that retrieves metadata for specific DOIs via the `/works/{doi}` endpoint (e.g., `https://api.crossref.org/works/doi/10.1128/mbio.01735-25`), not a traditional DOI resolution service. Traditional DOI resolution uses `https://doi.org/{doi}` which redirects to landing pages. For citation verification purposes, the metadata retrieval API is sufficient.

**Sources**:
- [CrossRef REST API Documentation](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [GitHub CrossRef REST API Docs](https://github.com/CrossRef/rest-api-doc)

**Note**: DataCite also provides similar metadata retrieval via `/dois/{id}` endpoint at `https://api.datacite.org`.

---

### Claim 2: arXiv IDs follow format `YYMM.NNNNN` (4-digit year-month + 4-5 digit number)
**Status**: PARTIALLY INACCURATE

**Evidence**: The arXiv identifier format is `YYMM.number` where:
- YY = 2-digit year
- MM = 2-digit month (01-12)
- number = **4 digits (0001-9999) from April 2007 through December 2014**
- number = **5 digits (00001-99999) from January 2015 onward**

The claim states "4-digit year-month + 4-5 digit number" which correctly describes `YYMM` (4 chars) but is ambiguous about the sequence number format. **The sequence number varies by era: 4 digits for pre-2015, 5 digits for 2015 onward.**

**Source**: [arXiv Identifier Help Page](https://info.arxiv.org/help/arxiv_identifier.html) (accessed 2026-03-19)

**Recommendation**: Update specification to clarify dual format or use 5-digit format as the canonical modern representation.

---

### Claim 3: HTTP HEAD requests are sufficient to check URL reachability without downloading content
**Status**: VERIFIED

**Evidence**: HTTP HEAD requests return only headers without the response body, making them efficient for checking URL reachability. They are used by URL validation tools, uptime monitors, and link checkers to verify resource availability and metadata (status code, headers) without bandwidth overhead.

**Sources**:
- [MDN: HEAD HTTP Method](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/HEAD)
- [DEV Community: HTTP HEAD Requests Guide](https://dev.to/mdhabibur/mastering-http-head-requests-with-curl-developers-guide-to-efficiency-automation-5gin)

---

### Claim 4: Python `httpx` and `requests` can perform HTTP HEAD requests
**Status**: VERIFIED

**Evidence**:
- **httpx**: Provides `httpx.head()` method for both sync and async operations. HEAD requests do not support request body (per HTTP spec).
- **requests**: Provides `requests.head()` method with full parameter support (headers, auth, timeouts, proxies, cookies).

Both libraries fully support HEAD requests as a first-class method.

**Sources**:
- [HTTPX API Documentation](https://www.python-httpx.org/api/)
- [Python requests HEAD Method - Real Python](https://realpython.com/python-requests/)
- [W3Schools: Python Requests head Method](https://www.w3schools.com/python/ref_requests_head.asp)

---

### Claim 5: Opt-in network validation flag pattern is correct for network-dependent validators
**Status**: VERIFIED

**Evidence**: Existing Python validation tools use opt-in patterns for network operations:
- **Sphinx linkcheck builder**: Invoked explicitly via `-b linkcheck` command (not enabled by default). Configuration supports `linkcheck_ignore`, `linkcheck_workers`, and timeout tuning.
- **MkDocs**: Configuration for validation.links with warn/info/ignore levels, invoked with `mkdocs build` (network checks can be made fail-fast with `--strict`).
- **lychee**: Supports `--offline` flag to disable network requests; by default performs network validation.

The opt-in pattern (explicit flag or command, not always-on) is standard practice to avoid surprising users with network I/O or dependency on external services during validation.

**Sources**:
- [Sphinx Builders Documentation](https://www.sphinx-doc.org/en/master/usage/builders/index.html)
- [Sphinx Configuration Options](https://www.sphinx-doc.org/en/master/usage/configuration.html)
- [MkDocs Configuration](https://www.mkdocs.org/user-guide/configuration/)
- [lychee Link Checker GitHub](https://github.com/lycheeverse/lychee)

---

## Summary

| Claim | Status | Confidence | Action |
|-------|--------|-----------|--------|
| CrossRef DOI API | ✓ VERIFIED | High | Use `/works/{doi}` endpoint for metadata retrieval |
| arXiv format | ⚠ PARTIALLY INACCURATE | Medium | Clarify 4-digit (pre-2015) vs 5-digit (2015+) sequence number |
| HTTP HEAD efficiency | ✓ VERIFIED | High | Use as specified |
| httpx/requests HEAD support | ✓ VERIFIED | High | Both libraries supported; no dependency issue |
| Opt-in flag pattern | ✓ VERIFIED | High | Pattern is standard; `--verify-citations` flag is appropriate |

**Recommendation**: Update arXiv identifier specification in design doc to explicitly note the date-dependent sequence number format. All other claims are sound.
</div>

## RT-ICA

<div><sub>2026-03-19T02:22:33Z</sub>

RT-ICA Final: Add automated citation verification to research-curator validate mode
Goal: Add `--verify-citations` flag to `validate_research.py` that checks URL reachability, arXiv ID format, and DOI resolution, flagging dead/hallucinated references as warning-severity issues in JSON output.

Conditions:
1. `validate_research.py` CLI interface, Issue TypedDict, JSON output schema | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: impact-analyst read file, mapped Issue TypedDict, CLI flags, and JSON schema
2. Citation formats in research entries (URL/arXiv/DOI patterns) | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: fact-checker verified arXiv format (4-digit seq pre-2015, 5-digit 2015+); CrossRef DOI pattern confirmed
3. CrossRef/DataCite API endpoints | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: fact-checker verified `/works/{doi}` endpoint (CrossRef), accessed 2026-03-19
4. arXiv ID format spec | Snapshot: AVAILABLE → Final: AVAILABLE | Clarified: sequence numbers are 4-digit pre-2015, 5-digit from 2015 onward
5. HTTP library for script | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: fact-checker verified both `httpx` and `requests` provide `.head()` method; either can be added as PEP 723 dep
6. `--verify-citations` flag integration with existing workflow | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: impact-analyst identified 4 critical systems and documented backward-compatible (off by default) integration pattern
7. Warning-severity issues are reported but not auto-fixed | Snapshot: AVAILABLE → Final: AVAILABLE | Source: SKILL.md validate mode spec

Changes from snapshot:
- Conditions 1, 2, 3, 5, 6: DERIVABLE → AVAILABLE (resolved by Wave 1 swarm)
- Condition 4: arXiv format clarified with era-dependent digit count

Decision: APPROVED — 7/7 AVAILABLE, 0 MISSING, 0 BLOCKED
</div>
