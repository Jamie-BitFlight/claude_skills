# Validation Rules

Checks performed by `./scripts/validate_research.py` and severity mapping for the `/research-curator` skill. Severity in the JSON output is fixed and mode-independent; *handling* differs by mode — [Validation Gate for New/Refreshed Entries](#validation-gate-for-newrefreshed-entries) below for an entry a `@research-curator` agent just created or rewrote this invocation, Validate Mode's Issue Handling in `SKILL.md` for pre-existing entries.

---

## Check Definitions

### Error Severity (must fix)

- **section_completeness**: All required `##`-level sections must exist. The authoritative list is `REQUIRED_BODY_SECTIONS` (plus `_REQUIRED_SECTIONS_TEXT_HEADER_ONLY` for legacy text-header entries) in `validate_research.py`; the same sections appear in `entry-template.md`'s Entry File Template. Header fields (Research Date, Source URL, etc.) are checked separately via **header_fields**.
- **empty_sections**: Section heading exists but contains no content below it before the next heading

### Warning Severity (should fix)

- **header_fields**: Header block must contain Research Date, Source URL, Version at Research, License
- **access_dates**: Every URL in the References section must have an access date in format `(accessed YYYY-MM-DD)` or `(YYYY-MM-DD)`
- **freshness_tracking**: Freshness Tracking section must contain Last Verified, Version at Verification, Next Review Recommended fields
- **url_format**: All URLs must be valid `http://` or `https://` format
- **cross_references_absent**: Entry does not contain a `## Cross-References` section. Expected for entries created or last verified on or after 2026-03-12. Entries with Research Date or Last Verified before this date are exempt. Gated on the Research Date or Last Verified field value in `validate_research.py`'s `_check_cross_references`.
- **repo_path_unresolved**: A gap-analysis file (`research/insights/`, `research/utilization/`) asserts that a capability already exists in this repository, citing a repository-relative path or a skill name as evidence, and that path/skill does not exist. See [Repository Path Citations](#repository-path-citations) below for scope, detection, and the measured false-positive rate.

> **Handling differs by mode, not by severity.** `header_fields`, `access_dates`, `freshness_tracking`, and `url_format` stay warning-severity in the JSON output no matter who calls the script. For an entry that Default Mode, Batch Mode, or Rerun Mode created or refreshed *this invocation*, these four are must-fix before the entry is reported complete — see [Validation Gate for New/Refreshed Entries](#validation-gate-for-newrefreshed-entries) below. `cross_references_absent` is excluded from this must-fix rule; its own date-based exemption above is unaffected. `repo_path_unresolved` is also excluded from this must-fix rule — it is produced by `research-insight-extractor` and `research-utilization-assessor`, not by `@research-curator`'s Default/Batch/Rerun modes, so it sits outside that gate's scope entirely rather than being folded into it. For pre-existing entries that Validate Mode scans, all four gated checks remain report-only, per Validate Mode's Issue Handling in `SKILL.md`.

### Info Severity (optional)

- **formatting_suggestions**: Minor markdown formatting issues (missing blank lines around fences, inconsistent heading levels)

---

## Repository Path Citations

`repo_path_unresolved` detects a specific harmful pattern found in a corpus survey of the research vault: a gap-analysis file records an "Already covered" (or equivalent) verdict — skipping a proposal because the repository supposedly already does the thing — and the only evidence for that verdict is a repository path or skill name that does not exist. Two such clusters were confirmed in the corpus: citations to `.claude/rules/` (moved to root-level `rules/` on 2026-09-04, and in several cases never existed as `.claude/rules/` in the first place) and citations to a family of skill names that has never existed in this repo (`swarm-operations`, `swarm-patterns`, `swarm-orchestrating`, `swarm-spawning`, `swarm-from-markdown`, `orchestrating-swarms`, `backlog-tools-administrator`).

### What counts as a citation

A candidate is a repository-relative path whose first path segment is a real top-level entry of this repo (`.claude`, `plugins`, `research`, `rules`, `docs`, `scripts`, `tests`, …) followed by at least one more `/segment`. That top-level set is derived at runtime from `git ls-files` rather than hardcoded, so it never drifts out of sync with the actual directory layout. Tracked paths, not a filesystem walk: a walk also sees gitignored and transient directories (`.venv/`, `.tmp/`, `plan/`, nested `git worktree` checkouts), which would make the same file validate differently on a developer machine and in a fresh CI clone. When `git` is unavailable the code falls back to a filesystem scan. This distinguishes a path citation from:

- **A URL** — the candidate pattern's negative lookbehind refuses to start a match when the preceding character is a path/URL character (`/`, `.`, a word character, `-`), so `https://github.com/x/research/y` never matches at `research` (it is preceded by `/`).
- **A code identifier** — a bare word with no `/` after the top-level segment never matches; `research-curator` alone is not a candidate, `research/x` is.
- **An illustrative/template example** — a placeholder like `research/{category}/{name}.md` cannot match because `{` is not in the segment character class, so template text in reference docs is inert by construction.

A second, narrower pattern (`_BARE_SKILL_CITATION`) catches the corpus's shorthand for citing a skill without its directory path — a backtick-quoted `` `{slug}/SKILL.md` `` or `` `{slug} SKILL.md` ``. Backtick-quoting is required: during measurement, an unquoted version matched ordinary prose ("the *self-contained* SKILL.md approach") as a false skill name. Requiring backticks trades a small amount of recall (some genuine unquoted bare mentions go undetected) for zero observed false positives on descriptive prose.

### Severity

Warning, matching the existing scheme's other heuristic/regex-based checks (`access_dates`, `url_format`, `freshness_tracking`) rather than `section_completeness`/`empty_sections`' error tier. The check produces false negatives (it misses genuine bad citations that don't carry a recognized marker phrase) and a small residual false-positive rate (see below), so it is a report-only signal that never blocks a file — every hit still needs a human or agent to confirm before a fix is applied.

### Scope: analysis files, not entries

This check runs on `research/insights/*.md` and `research/utilization/*.md` gap-analysis files only — **not** on research entries, and not on `research/design-notes/`. `_NON_ENTRY_DIRS` previously excluded `insights/` and `utilization/` from validation entirely; they are now collected and validated by a separate, lighter path (`collect_analysis_files` / `validate_analysis_file`) that runs only this check, not the entry-template structural checks those files were never meant to satisfy.

This is a deliberate scoping decision, not an oversight, based on measuring both scopes against the real corpus while designing this check:

- **Entries mix description of the researched tool with commentary about this repo in the same paragraph** ("their `tests/skill-triggering/` dir offers a pattern for our skill tests"). Restricting the scan to an entry's `## Relevance to Claude Code Development` section and checking every path mention there still produced a measured **~86% false-positive rate** (19 of 22 flagged entries cited the *researched* tool's own paths — e.g. `docs/architecture.md` describing the subject tool, not this repo). Telling "our path" from "their analogous path" needs semantic judgment a regex cannot carry. Entries are left to the manual "Path exists" step in `entry-review-rubric.md`'s Gate 4, which already covers this exact question with human judgment.
- **`-improvements.md` / `-utilization.md` files exist only to compare a researched tool against this repo** (this is Gate 4's own stated scope: "the entry's 'Relevance to Claude Code Development' section and every proposal in the `-improvements.md` and `-utilization.md` files"). A path cited there is far more likely to be a genuine self-referential claim. Gating further on an existing-state assertion phrase and excluding negated/aspirational phrasing (below) drops the false-positive rate in this scope from ~86% to a few percent: a run against the full real corpus (506 files) finds 142 `repo_path_unresolved` issues across 67 files, of which a manual audit traced all but three to genuine drift (a moved/renamed/never-existed path).

The three known residual false-positive shapes, which reviewers should expect and dismiss rather than "fix":

| Shape | Corpus example | Why the regex misreads it |
|---|---|---|
| External tool's own path on a mixed line | `2026-04-29-mattpocock-skills-improvements.md:146` cites `docs/adr/` as *mattpocock/skills*' layout; the line is scanned only because a later clause says "already exists" | Marker gating is per line, so one existing-state clause pulls in every path on the line |
| Path relative to a skill or plugin, not to the repo root | `2026-05-02-claude-brain-improvements.md:8` cites `scripts/session_query.py` — real, at `.claude/skills/session-historian/scripts/session_query.py` | Resolution is always repo-root-relative |
| Prose `word/word` where the first word is a top-level directory name | "tasks grouped by plan/feature slug" reads as a path when a `plan/` directory exists | Generic directory names (`docs`, `data`, `plan`, `tests`, `scripts`) collide with ordinary English |

### Avoiding false positives within scope: existing-state and negation/aspirational gating

Even within `insights/`/`utilization/`, a bare path mention is not necessarily a false existing-state claim — many are legitimate: a proposed *new* file that doesn't exist yet, or a "Target state" / "Current state" description of the researched tool. The check only inspects a line when it carries an **existing-state marker** — "already covered/implements/uses/has/exists/provides", "currently implements/uses", or a `**Local system**:`/`**Caller**:` field label (the corpus's own recurring template labels for this exact kind of claim) — and skips it anyway if the same line also carries a **negation or proposal marker**: an explicit absence statement ("does not exist/occur", "no such", "absence of") or forward-looking phrasing ("integration point", "could/would add", "new skill/hook", "target state", "to be created", "not yet created/exist"). The negation guard exists because an entry can correctly assert non-existence in the same breath it names a fictional path (`research/insights/2026-05-04-waza-improvements.md` names a hypothetical `` `source-root SKILL.md` `` variant and explicitly says it "does not occur in this repo" — flagging that would penalize a correct absence statement).

### Path/skill resolution

A path candidate resolves via `Path.exists()` against the real repository root (located by walking up from the script's own file location to the directory containing `pyproject.toml` — not the `research/` root a caller passes in, since a citation must resolve against the real tree regardless of which subdirectory is being validated). A candidate containing a `*` wildcard (e.g. `plugins/development-harness/skills/code-review-*/`, used in the corpus to reference a family of skills) resolves via `Path.glob()`, succeeding if the glob matches at least one real path; a candidate that is not a valid glob pattern counts as unresolved rather than aborting the run. A bare skill citation resolves against the set of every tracked directory name that is the parent of a `SKILL.md`.

Repo-root lookup, the top-level entry set, and the skill-name set are all computed lazily on the first citation check and cached, not at import. A copy of this script placed outside any project tree therefore still runs every other check; `repo_path_unresolved` alone is skipped when no `pyproject.toml` is found above the script.

---

## Validation Gate for New/Refreshed Entries

Applies only when Default Mode, Batch Mode, or Rerun Mode is the reason an entry file exists in its current form this invocation — a `@research-curator` agent just created or rewrote it. Does not apply to Validate Mode scanning entries this invocation did not itself write; those follow the lighter report-only handling in Validate Mode's Issue Handling (`SKILL.md`). It also does not apply to `repo_path_unresolved` — see the note under Warning Severity above.

This is the authoritative procedure for what the orchestrator does with the `fix_research_formatting.py` + `validate_research.py --json` output on such a file:

```mermaid
flowchart TD
    Start(["fix_research_formatting.py + validate_research.py --json<br>ran on an entry this invocation just created or refreshed"]) --> HasErr{"Any error-severity issue<br>in the JSON output?"}
    HasErr -->|"Yes"| MarkIssues(["Mark entry created/refreshed with issues<br>Skip analysis-agent fan-out for this entry<br>Report exact error text from JSON to user"])
    HasErr -->|"No"| HasGatedWarn{"Any warning-severity issue from<br>header_fields, access_dates,<br>freshness_tracking, or url_format?<br>(cross_references_absent excluded)"}
    HasGatedWarn -->|"No"| Proceed(["Entry is complete — proceed to<br>analysis-agent fan-out"])
    HasGatedWarn -->|"Yes"| SpawnFix["Spawn @research-curator with --fix flag<br>PLUS the exact warning issue list from JSON<br>(the agent already has these facts: today's<br>research/verification date, the source URL,<br>the version and access dates it just gathered)"]
    SpawnFix --> Rerun["Re-run fix_research_formatting.py<br>then validate_research.py --json on the same file"]
    Rerun --> HasErr2{"Any error-severity issue,<br>or any warning from the four<br>gated checks, remaining?"}
    HasErr2 -->|"Yes"| MarkIssues
    HasErr2 -->|"No"| Proceed
```

Reaching `MarkIssues` after the retry means a genuinely un-fillable field — report it as an issue on the entry rather than accepting it as a warning to leave open.
