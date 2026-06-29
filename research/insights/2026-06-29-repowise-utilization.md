---
title: "Utilization Proposals: repowise"
---

## Utilization 1: doc-drift-auditor → repowise

**Research entry**: ./research/mcp-ecosystem/repowise.md
**Caller**: ./.claude/agents/doc-drift-auditor.md
**Integration mechanism**: MCP tool call
**Replaces or adds**: Enhances code discovery phase with deterministic symbol extraction and context enrichment instead of grep-only pattern matching
**Setup cost**: Medium (MCP server init + repowise index on target repo, <30s incremental after first run)
**Integration surface**: `get_symbol("path::Name")` (exact source bytes with line bounds), `search_codebase(query, kind?)` (semantic search over generated wiki), `get_context(targets, include?)` (triage cards with docs, signatures, hotspot bits)

### Why this caller

The doc-drift-auditor agent currently performs static code discovery via grep and file reads to extract function/class definitions and catalog implemented features (lines 39-94, parse Python source for classes, functions, decorators). This approach is language-specific, relies on regex fragility, and lacks semantic context—it cannot easily answer "is this function actually exported as public API?" or "does this documented module truly exist at the documented path?". repowise's `get_symbol()` MCP tool returns exact source bytes with line bounds (avoiding the need for Read + offset math), and `search_codebase()` provides semantic search across auto-generated documentation, catching semantic naming mismatches and undocumented interfaces. When the auditor identifies documented functions but cannot find them in source, `get_symbol()` will either return the exact bytes (confirming existence) or raise NotFound (confirming documentation claims an unimplemented function). The `get_context()` tool includes "hotspot bits" and "governing decisions" that directly enrich the auditor's documentation-claim analysis: if docs describe an architectural decision but repowise flags it as stale or conflicted, the auditor can surface that mismatch in its drift report.

### Integration sketch

```python
# Current approach (doc-drift-auditor.md lines 77-94):
# Parse Python source via grep and manual regex
grep -n "^class \|^def " implementation_file.py
# Output: unreliable for multi-language codebases, no validation

# New approach with repowise:
from repowise import RepoClient

client = RepoClient(repo_path="/path/to/codebase")
client.init()  # Index repo once (<30s)

# Extract exact source for a documented symbol
try:
    symbol_source = client.get_symbol("src/api/handlers::authenticate_user")
    # Returns: {source: "def authenticate_user(...):\n...",
    #           line_start: 45, line_end: 62, path: "src/api/handlers.py"}
    print(f"Function exists at {symbol_source.path}:{symbol_source.line_start}")
except NotFound:
    print("ERROR: Docs describe authenticate_user but it doesn't exist")

# Search for documented functions that exist but not under expected path
results = client.search_codebase("authenticate user", kind="implementation")
# Returns: [{name: "auth_handler", path: "...", doc: "...", type: "function"}]
# Can detect name changes, path changes, or complete disappearance

# Get governance context for documented design patterns
context = client.get_context(["src/api/routes.ts"], include=["governing_decisions"])
# Returns: triage card including "Key Decisions" section from architectural records
# If docs describe pattern but repowise flags decision as stale, audit can surface this

# Validate documented hot spots match actual code churn
# (repowise automatically flags high-churn, high-complexity files)
# Drift auditor can verify: "Docs identify api/core.py as stable, but repowise
# marks it as hotspot (high churn + complexity)" → document mismatch
```

---

## Utilization 2: code-review → repowise

**Research entry**: ./research/mcp-ecosystem/repowise.md
**Caller**: ./.claude/agents/code-review.md
**Integration mechanism**: MCP tool call + CLI subprocess
**Replaces or adds**: Adds defect-prediction scoring and hotspot risk assessment to supplement quality review logic
**Setup cost**: Medium (MCP server init + repowise health index, <30s incremental)
**Integration surface**: `get_health(targets?, include?)` (25-biomarker scores with defect prediction), `get_risk(targets, changed_files?)` (hotspot scores, dependents, PR-mode directives with `will_break`, `missing_cochanges`, `missing_tests`, `governance_risk`)

### Why this caller

The code-review agent reviews code changes for security, performance, and pattern adherence (`.claude/agents/code-review.md` lines 19-90). Currently, it relies on semantic code reading and manual inspection of changed files—a process that catches style violations and logic errors but has no persistent codebase context for risk assessment. repowise's `get_health()` tool provides a defect-prediction score (AUC 0.731 across 21 repos, research entry lines 85-91) calibrated against real defect corpus, identifying "Alert" files with 17× defect rate vs. "Healthy" files. When code-review is evaluating a PR that modifies an Alert-tier file, it can escalate scrutiny proportionally. The `get_risk()` tool in PR mode returns directive blocks (`will_break`, `missing_cochanges`, `missing_tests`, `governance_risk`) that flag structural risks the agent cannot detect via static analysis alone: missing co-changes (files that always change together but are absent in this PR), dependency breaks (changes to widely-used symbols), and governance violations (changes contradicting documented decisions). This transforms code review from "does this code look correct?" to "does this code change break the system and violate architectural constraints?"

### Integration sketch

```python
# Current approach (code-review.md):
# Agent reads changed files and reviews for security, performance, patterns
# No persistent risk context, no defect prediction

# New approach with repowise:
from repowise import RepoClient

client = RepoClient(repo_path="/path/to/repo")

# Get health scores for changed files
changed_files = ["src/api/handlers.py", "src/db/schema.py"]
health = client.get_health(changed_files, include=["biomarkers", "coverage", "trends"])
# Returns: {
#   "src/api/handlers.py": {score: 3.2, tier: "Alert", biomarkers: {...},
#                           prior_defect_rate: 0.15},
#   "src/db/schema.py": {score: 8.5, tier: "Healthy", biomarkers: {...},
#                        prior_defect_rate: 0.02}
# }

# Alert: handlers.py is high-risk based on historical defect correlation
if health["src/api/handlers.py"]["tier"] == "Alert":
    print("⚠️ ESCALATED REVIEW: This file has 17x avg defect rate. Scrutinize carefully.")

# Get PR-mode risk assessment
risk = client.get_risk(changed_files, changed_files=changed_files)
# Returns directive block:
# {will_break: ["process_payment() called by 7 endpoints, missing tests"],
#  missing_cochanges: ["auth.py always changes with handlers.py, but is missing"],
#  missing_tests: ["no tests for schema migration"],
#  governance_risk: ["contradicts caching-decision #ADR-23"]}

# Append PR review findings
if risk.will_break:
    print(f"❌ BREAKING CHANGE RISK: {risk.will_break}")
if risk.missing_cochanges:
    print(f"⚠️ INCOMPLETE PR: Missing co-changes to {risk.missing_cochanges}")
if risk.governance_risk:
    print(f"📋 GOVERNANCE: {risk.governance_risk}")

# Compare historical trend
if health["src/api/handlers.py"].get("trend") == "declining":
    print("📈 WARNING: This file's health is declining—prioritize refactoring")
```

---

## Utilization 3: dh:impact-analyst → repowise

**Research entry**: ./research/mcp-ecosystem/repowise.md
**Caller**: (potential new/enhanced agent or skill in development-harness plugin)
**Integration mechanism**: MCP tool call
**Replaces or adds**: Extends blast-radius analysis with deterministic co-change detection and dependency graph querying
**Setup cost**: Medium (MCP server init + repowise index)
**Integration surface**: `get_context(targets, include=["callers", "dependents"])` (triage cards showing dependents), `get_risk(targets, changed_files?)` (PR-mode directives including `missing_cochanges`, `will_break`), `get_overview()` (module map, entry points, hotspots)

### Why this caller

The impact-analyst agent builds the affected systems inventory for backlog grooming and writes the Impact Radius section (research entry notes this as a key capability gap, lines 277-282: agents need trust signals for code health and impact before merging). Currently, impact-analyst uses Grep/Glob/Read to manually trace files and infer dependencies—a process prone to missing cross-module coupling, hidden call chains through dependency injection, and dynamic imports. repowise's `get_risk()` tool directly answers "what breaks if I change this?" with concrete directives (will_break, missing_cochanges, missing_tests, governance_risk). The `get_context()` tool with `include=["callers", "dependents"]` returns exact lists of functions and modules that depend on a change target, eliminating false negatives. When impact-analyst is assessing the blast radius of modifying a core utility, repowise can return "this change affects 14 files via co-change patterns" with exact file list, vs. the current manual grep-based estimate.

### Integration sketch

```python
# Current approach (impact-analyst reads files and infers dependencies):
# Uses Grep/Glob/Read to manually trace call chains
# Incomplete on large codebases, prone to missing implicit dependencies

# New approach with repowise:
from repowise import RepoClient

client = RepoClient(repo_path="/path/to/repo")

# Get detailed impact for a backlog item targeting a specific module/function
target = "src/payment/process_payment"
context = client.get_context([target], include=["callers", "dependents"])
# Returns: triage card with exact callers, callees, hotspot status
# {
#   name: "process_payment",
#   path: "src/payment/__init__.py",
#   callers: [
#     {name: "order_handler", path: "src/orders/api.py", type: "function"},
#     {name: "CartService", path: "src/cart/service.py", type: "class"},
#     ...
#   ],
#   hotspot: true,
#   governance: [{decision: "payment-idempotency", status: "verified"}],
# }

# Get PR-mode risk directive
risk = client.get_risk([target], changed_files=[target])
# Returns: {
#   will_break: ["refund_transaction() at src/refund/api.py line 42"],
#   missing_cochanges: ["src/audit/log.py (always changes with process_payment)"],
#   missing_tests: ["test_process_payment_with_retry.py"],
#   governance_risk: []
# }

# Assemble impact-radius for backlog item
impact_radius = {
    "direct_callers": len(context.callers),
    "files_to_test": find_tests_from_callers(context.callers),
    "co_change_risk": len(risk.missing_cochanges),
    "governance_constraints": context.governance,
    "hotspot_flag": context.hotspot,  # Warn if modifying high-defect-rate file
}

# Write to backlog item Impact Radius section with confidence
# vs. current grep-based heuristics with "maybe affected" caveats
```

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| context-gathering (`./.claude/agents/context-gathering.md`) | The agent builds context manifests for new tasks by reading code paths and tracing flows (lines 16-127). While repowise's `get_context()` tool would enrich this with exact symbol boundaries and governance context, the agent's core responsibility is bootstrapping context for a SINGLE new task—a narrow scope where manual file reads are sufficient and repowise's indexing overhead (even <30s) is disproportionate. The agent runs once per task startup; indexing a large repo would dominate session time with no corresponding win. Defer to a specialized "indexing preparation" workflow where repowise indexing happens during project setup, not per-task. |
| dh:code-reviewer (in development-harness plugin) | The code-review skill for dh:code-reviewer agents checks type contracts, implementation quality, and SOLID violations via direct code reading (SKILL.md not available, but pattern from python-engineering:code-reviewer scope). While repowise's `get_health()` scores would supplement this, the reviewer's core loop is reading code diffs—a high-context, low-latency operation that MCP calls would interrupt. repowise is better suited for POST-review (e.g., alerting humans when a low-health file was reviewed) than inline review. The integration value is low. |

---

## Integration Path Forward

repowise v0.20.0 is production-ready (GA release, research entry line 8). Before integrating:

1. **Proof of Concept**: Test repowise MCP server startup on a 500-file repo, verify `get_health()` accuracy via manual inspection of Alert-tier files, validate `get_risk()` directives against actual co-change patterns
2. **Setup Protocol**: Document the `repowise init` and MCP registration workflow in `.claude/rules/` for agents to follow; clarify when to index (once per project vs. per-session)
3. **Prioritized Integration**: Start with **code-review** (narrow integration point, high value—defect prediction directly improves PR safety); then **doc-drift-auditor** (read-only, no side effects); then **impact-analyst** (enhances blast radius, medium complexity)
4. **Incremental Sync**: Use repowise's `<30s incremental update` to keep health/risk data fresh during development without re-indexing from scratch
5. **Validate PR Directives**: Before relying on `get_risk()` `missing_cochanges` and `will_break` in production, manually verify against 5-10 real PRs to ensure co-change detection is accurate

The MCP server mode is the best integration path (vs. CLI subprocess) because it avoids spawning separate processes and provides streaming results with `.meta` envelope (index_age_days, stale_warning) for confidence tracking.
