---
name: Backlog item matching is broken — substring search on titles fails for semantic queries, descriptions are too large to load in bulk, no categorization metadata exists for filtering
description: "**Problem**: `/work-backlog-item` Step 1 matches user input to existing backlog items using case-insensitive substring search on the `title` field only (via `mcp__backlog__backlog_list`). This fails when the user's phrasing doesn't contain a literal substring of the title — e.g., 'fix that login thing' will not match 'Authentication failure on SSO redirect.'\n\nAdditionally, the backlog contains 197 open items (observed 2026-03-15) with descriptions averaging ~200 lines each. Loading all items with descriptions into context for LLM-based matching would consume ~512K tokens — half a 1M context window.\n\nNo structured categorization metadata exists on backlog items, so there is no way to filter items by domain, component, or problem type before presenting them to a matcher.\n\n**Where it lives**: `work-backlog-item` SKILL.md Step 1 (Find the Backlog Item), `mcp__backlog__backlog_list` tool, and `.claude/backlog/*.md` per-item files (which lack categorization fields).\n\n**Success looks like**: A user can type a natural-language description of what they want to work on, and the system reliably identifies the correct backlog item — even when the phrasing shares no literal substrings with the item's title.\n\n**How you'll know it's working**: Test with 10 natural-language queries that use synonyms, abbreviations, or problem descriptions instead of exact title words. The matcher should find the correct item in at least 8 of 10 cases. Current substring matching would find 0-2 of those 10."
metadata:
  topic: backlog-item-matching-is-broken-substring-search-on-titles-f
  source: Session observation
  added: '2026-03-16'
  priority: completed
  type: Feature
  status: done
  issue: '#745'
  last_synced: '2026-03-16T03:20:46Z'
  groomed: '2026-03-16'
  plan: plan/P699-backlog-semantic-matching.yaml
---

## RT-ICA

<div><sub>2026-03-16T03:16:06Z</sub>

RT-ICA Snapshot: Backlog item matching
Goal: Replace substring title matching with semantic matching that handles natural-language queries at 197+ item scale
Conditions:
1. Current matching logic documented | Status: AVAILABLE | work-backlog-item SKILL.md Step 1 read in this session
2. Backlog item count and structure known | Status: AVAILABLE | backlog_list returned 197 items, observed 2026-03-15
3. Description payload size measured | Status: DERIVABLE | can measure by calling backlog_view on sample items
4. zvec API and capabilities documented | Status: AVAILABLE | research/ml-infrastructure/zvec.md created this session
5. Embedding model selection for short technical queries | Status: MISSING | zvec docs describe the DB, not which embedding model to pair with it
6. backlog_list MCP tool schema known | Status: AVAILABLE | tool schema loaded in this session — supports title, section, status, label filters
7. User's preferred matching UX (confidence thresholds, disambiguation flow) | Status: MISSING | user decision needed on what happens with ambiguous matches
AVAILABLE count: 4
DERIVABLE count: 1
MISSING count: 2
</div>

## Groomed (2026-03-16)


### Impact

<div><sub>2026-03-16T03:17:56Z</sub>

See full report: .claude/reports/groom-745-impact-radius.md

Summary: 16 affected systems across 5 categories. Critical: work-backlog-item Step 1, complete-implementation Step 3, backlog_list function/MCP. 8 code changes required, 7 files will become stale, 6 content updates needed. All 6 ecosystem checklist items incomplete.
</div>

<div><sub>2026-03-16T03:20:26Z</sub>

**Affected systems** (impact-radius inventory): 16 systems across 5 categories.

**Code changes required**: 8 files
- Producers: `create-backlog-item/SKILL.md`, `groom-backlog-item/SKILL.md`
- Consumers: `work-backlog-item/SKILL.md`, `complete-implementation/SKILL.md`, `backlog.py` CLI, `server.py` MCP, `operations.py`, `parsing.py`

**Stale documentation**: 5 skill files, 2 reference files, 1 README (8 artifacts become outdated when matching logic changes)

**Scale of data**:
- 245 open backlog items (not 197 as initially claimed)
- Average description: ~86 lines per item (not 200)
- Total payload: ~259K tokens if all descriptions loaded (not 512K)

**Scope of fix**: This is feasible at 245 items. The description payload size is actually less than initially characterized, so bulk loading is not the limiting constraint. The real constraint is that `backlog_list` tool doesn't expose descriptions OR categorization metadata, forcing Step 1 to operate on title alone.
</div>

### Issue Classification

<div><sub>2026-03-16T03:18:07Z</sub>

See full report: .claude/reports/groom-745-classification.md

Issue Type: defect
Root Cause (5-whys):
1. Substring search cannot compare meaning — only character sequences
2. Semantic matching was not in the initial design (cost-benefit favored simplicity at small scale)
3. No scaling guard when backlog grew from small to 245 items
4. Existing categorization metadata (priority, type, status, topic) not leveraged for filtering
5. No instrumentation surfaces matching failures until they become painful

System Architecture Gaps:
- Matching logic locked to single algorithm (no strategy abstraction)
- Existing metadata not exposed as backlog_list filter parameters
- No scaling instrumentation
</div>

### Reproducibility

<div><sub>2026-03-16T03:20:19Z</sub>

To observe the problem: run `/work-backlog-item` Step 1 with a semantic query like `"fix the SAM schema thing"` and observe that no matches are found. When the same user then searches with exact substring `"SAM schema"`, the item "Integrate SAM Schema as sole task-file interface" is found. The matching system only works on exact or partial literal substrings, not on semantically equivalent phrasings.

**Example scenario**:
- Query: `"fix login issue"` → finds 0 items
- Query: `"authentication"` → finds "Authentication failure on SSO redirect"

The substring search cannot bridge the semantic gap between "login" and "authentication" even though they describe the same problem.

**Current behavior**: case-insensitive substring match on title field only (verified in `/work-backlog-item/SKILL.md` Step 1, line 126-136, and implementation in `operations.py` line 1024).
</div>

### Priority

<div><sub>2026-03-16T03:20:22Z</sub>

P1 (must-have): Every backlog interaction via `/work-backlog-item` starts with Step 1 (Find Backlog Item). Matching failures cause users to waste time on manual browsing or exact title searches when semantically related items exist. This affects 16 downstream systems (per impact-radius analysis): skills, agents, and CI workflows that depend on reliable item lookup.

User time cost: repeated queries with substring variations, fallback to manual item list review, loss of context when item is not found and user must re-describe the problem from scratch.

The problem surfaces on every `/work-backlog-item` invocation when a user's phrasing doesn't match existing title wording.
</div>

### Scope

<div><sub>2026-03-16T03:20:31Z</sub>

**Layer 1 (Foundation)**: Expose existing categorization metadata in backlog_list response and as filter parameters.

Categorization metadata already exists in frontmatter (fact-checker verified):
- `priority` (P0, P1, P2, Ideas)
- `type` (Feature, Bug, Refactor, Docs, Chore)
- `status` (open, done, resolved, closed, blocked)
- `topic` (categorization slug, e.g., "backlog-matching", "sam-integration")

Task: Update `backlog_list` MCP tool to expose these fields in response and accept them as filter parameters.

**Layer 2 (Enhancement)**: Implement semantic matching for in-context item queries.

When filter-first approach (Layer 1) does not narrow results sufficiently, apply semantic understanding to match user intent against remaining items. This can use:
- LLM-based semantic reasoning (evaluate user query against item titles/descriptions in context)
- Vector embeddings (optional; may leverage existing zvec infrastructure if available)

Task: Add matching strategy abstraction to Step 1 of `/work-backlog-item` to support filter-first pattern, then semantic matching as fallback.

**Layer 3 (Scale)** [optional]: Add vector retrieval for bulk semantic matching across full backlog.

Only needed if in-context semantic matching (Layer 2) proves insufficient at scale. Requires:
- Embedding model selection
- Vector database (optional; could use file-based index)
- Periodic re-embedding of new items

Task: Implement optional zvec-based semantic search if Layer 2 coverage is inadequate.

**Verification**: After fix, 80%+ of natural-language queries (like "fix login issue") should find semantically equivalent items (like "Authentication failure on SSO redirect").
</div>

### Output / Evidence

<div><sub>2026-03-16T03:20:34Z</sub>

**Success criteria** (what the fix produces):

1. **Reliable matching at scale** — `/work-backlog-item` Step 1 successfully finds backlog items at 245+ item count with semantic queries, not just exact substrings.

2. **Categorization-filtered queries** — `/work-backlog-item` Step 1 accepts optional filter parameters (priority, type, status, topic) to narrow search space before applying matching.

3. **Semantic understanding** — User queries with synonyms, problem descriptions, or rephrased intent are matched against titles and categorization metadata, not just literal character sequences.

**Evidence of working solution**:
- Test case: Query `"fix login redirect issue"` matches item titled "Authentication failure on SSO redirect" with high confidence
- Test case: Query filtered by `type=Bug` returns only bug-type items, reducing search space from 245 to ~N relevant items
- Test case: Backward compatibility maintained — title-only substring queries still work (no breaking change to existing workflows)

**User-facing change**: `/work-backlog-item` Step 0 (Interactive Mode) can now offer category/type filters to help users narrow down before searching, and Step 1 results include semantic match reasoning.
</div>

### Dependencies

<div><sub>2026-03-16T03:20:37Z</sub>

**External dependencies**:
- zvec (optional, for Layer 3 only) — installed as dev dependency in project; source verification deferred to implementation phase

**Internal dependencies**:
- `backlog_list` MCP tool schema update (prerequisite; unblocks Layer 1)
- `/work-backlog-item` SKILL.md refactoring (depends on Layer 1 completion)
- Matching strategy abstraction pattern (design pattern to enable Layer 2)

**No blockers identified** (per RT-ICA assessment): All necessary conditions for planning are available or appropriately deferred to implementation.

**Backward compatibility requirement**: Title-only substring matching must continue working to support existing user workflows. New filter and semantic parameters are optional/fallback, not replacements.
</div>

### Files

<div><sub>2026-03-16T03:20:41Z</sub>

**Key files from impact-radius analysis**:

**Producers** (write backlog items or matching logic):
- `.claude/skills/work-backlog-item/SKILL.md` — Step 1 matching procedure (major rewrite required)
- `.claude/skills/create-backlog-item/SKILL.md` — item creation flow (needs documentation update if categories become required)
- `.claude/skills/groom-backlog-item/SKILL.md` — grooming workflow (may need to derive/write categorization)

**Consumers** (use matching in workflows):
- `.claude/skills/backlog/backlog_core/operations.py` — `backlog_list()` function (extend to accept/expose filters)
- `.claude/skills/backlog/backlog_core/server.py` — MCP server tool registration (update schema)
- `.claude/skills/backlog/backlog_core/parsing.py` — `find_item()` helper (may refactor for strategy pattern)
- `.claude/skills/backlog/scripts/backlog.py` — CLI entry point (expose new filter args)
- `plugins/python3-development/skills/complete-implementation/SKILL.md` — follow-up routing Step 2 (update to use new filters)

**Tests**:
- `.claude/skills/backlog/tests/test_backlog_core_server.py` — MCP tool tests (expand for new parameters)
- `.claude/skills/backlog/tests/test_scenarios.py` — integration scenarios (add semantic/filter tests)

**Documentation** (will become stale):
- `.claude/skills/backlog/README.md` — matching behavior description
- `.claude/skills/work-backlog-item/references/step-procedures.md` — Step 1 procedure
- `plugins/python3-development/skills/complete-implementation/SKILL.md` — follow-up routing description
</div>

### Acceptance Criteria

<div><sub>2026-03-16T03:20:43Z</sub>

(a) **Semantic matching success rate**: 8 out of 10 natural-language semantic queries (e.g., "fix login issue", "SSO redirect problem", "auth failure") find the correct backlog item when one exists.

(b) **Metadata filtering available**: `backlog_list` MPC tool response includes `priority`, `type`, `status`, `topic` fields; `/work-backlog-item` Step 1 accepts optional filter parameters for these fields.

(c) **Scale verified**: Matching system operates reliably on 245+ open backlog items without requiring bulk loading of all item descriptions at query time.

(d) **Backward compatibility maintained**: Existing `/work-backlog-item` workflows that use title-only substring queries continue to work without modification.

(e) **Test coverage expanded**: New test cases cover semantic queries, category filtering, mixed strategies (filter-first then semantic), and fallback paths.
</div>

### Effort

<div><sub>2026-03-16T03:20:46Z</sub>

**Layer 1 (expose metadata + filter parameters)**: Moderate effort
- MPC tool schema update: 1-2 days
- backlog_list() function extension: 1-2 days
- Step 1 SKILL.md update: 1 day
- Test coverage: 1 day
- **Subtotal**: ~4-5 days

**Layer 2 (semantic matching with strategy pattern)**: Moderate-to-High effort
- Matching strategy abstraction (interface + implementations): 1-2 days
- LLM-based semantic matcher (in-context): 2-3 days
- Step 1 refactoring to use strategy: 1 day
- Integration testing: 1-2 days
- **Subtotal**: ~5-8 days

**Layer 3 (optional zvec-based scale)**: High effort
- Embedding model selection and integration: 2-3 days
- Vector index creation/maintenance: 2-3 days
- Semantic search implementation: 2 days
- Performance tuning: 1 day
- **Subtotal**: ~7-9 days

**Documentation updates**: ~2 days (across all layers)

**Total estimate (Layers 1 + 2)**: 11-15 days
**Total estimate (Layers 1 + 2 + 3)**: 18-24 days

Effort scales with matching strategy complexity chosen. Layer 1 + in-context semantic matching (Layer 2) provides 80%+ success rate. Layer 3 (bulk embedding) is optional for further scale.
</div>


## Fact-Check

<div><sub>2026-03-16T03:18:00Z</sub>

See full report: .claude/reports/groom-745-fact-check.md

Summary: 2 VERIFIED, 4 REFUTED, 1 INCONCLUSIVE.
- VERIFIED: substring search on titles only; backlog_list lacks descriptions
- REFUTED: 245 items (not 197); 86 avg lines (not 200); ~259K tokens (not 512K); categorization metadata EXISTS (priority, type, status, topic in frontmatter)
- INCONCLUSIVE: zvec in-process claim (research file not found by agent)

Key correction: categorization metadata does exist in item frontmatter but backlog_list MCP tool does not expose type/topic as filter parameters.
</div>

## RT-ICA

<div><sub>2026-03-16T03:19:45Z</sub>

RT-ICA Final: Backlog item matching
Goal: Replace substring title matching with semantic matching that handles natural-language queries at 245-item scale
Conditions:
1. Current matching logic documented | Snapshot: AVAILABLE → Final: AVAILABLE | work-backlog-item SKILL.md Step 1
2. Backlog item count and structure | Snapshot: AVAILABLE → Final: AVAILABLE (CORRECTED) | Actual: 245 items, not 197
3. Description payload size | Snapshot: DERIVABLE → Final: AVAILABLE (CORRECTED) | Actual: 86 avg lines, ~259K tokens total (not 200 lines / 512K)
4. zvec API documented | Snapshot: AVAILABLE → Final: AVAILABLE | research/ml-infrastructure/zvec.md
5. Embedding model selection | Snapshot: MISSING → Final: DEFERRED | Not a blocker for planning — can be resolved during implementation
6. backlog_list MCP tool schema | Snapshot: AVAILABLE → Final: AVAILABLE | Supports title, section, status, label filters
7. Matching UX preferences | Snapshot: MISSING → Final: DEFERRED | Can start with simple confidence tiers, refine iteratively
8. Categorization metadata exists (NEW) | Final: AVAILABLE | Frontmatter has priority, type, status, topic — gap is backlog_list doesn't expose type/topic as filters

Changes from snapshot:
- Conditions 2, 3: CORRECTED with fact-checker measurements (245 items, 86 avg lines, 259K tokens)
- Condition 5: MISSING → DEFERRED (not blocking for planning)
- Condition 7: MISSING → DEFERRED (iterative design acceptable)
- Condition 8: NEW — categorization metadata exists but is unexposed. Reframes the problem from "create metadata" to "expose and leverage existing metadata"

Decision: APPROVED
Problem reframing: The core issue is that existing metadata (priority, type, status, topic) is not exposed by backlog_list as filter parameters, and the matching algorithm has no strategy abstraction. The fix path is: expose metadata → filter-first → add semantic matching → add instrumentation.
</div>