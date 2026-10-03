# Research Entry Review Rubric

How to review a finished research entry and the analysis files produced from it, and which findings the reviewer fixes itself.

Writing an entry rather than reviewing one? Use [Entry Quality Standards](./entry-quality-standards.md) and [Extraction Methodology](./extraction-methodology.md) instead — this rubric is the audit that runs afterwards.

**Review scope** — every file the entry's creation touched:

- The entry: `./research/{category}/{name}.md`
- Improvement proposals, when present: `./research/insights/{YYYY-MM-DD}-{name}-improvements.md`
- Utilization proposals, when present: `./research/insights/{YYYY-MM-DD}-{name}-utilization.md`
- Cited entries, when the entry added cross-references to them

**Completion criterion**: every gate below has been run and its result recorded. A gate you skipped is a gate that FAILED — record it as `NOT RUN` with the reason, never as a pass.

**Defect** = a finding the entry's author controlled: text that was wrong when it was written. Record every defect as `{file}:{line} — {gate} — {exact quoted text} — {required correction}`. Quote the offending text verbatim; paraphrase loses the reviewer's evidence.

**Repair** = a finding the author could not have controlled: text that was accurate when written and that a later repository change invalidated. Record every repair as `{file}:{line} — {gate} — {exact quoted text} — {the change that invalidated it} — {required correction}`, and count repairs separately from defects. A repair schedules work against the citing file and leaves the verdict where it stood.

---

## Gate 1 — Mechanical Checks

Run the formatter. The orchestrator runs the validator after every pass, appending its remaining issues to the scratch document as `D` lines, and repairs cross-reference reciprocity before review; an orchestrated review (it names a scratch document) skips those two commands, and a standalone `--review` runs all three. Report output as **exact counts per severity and the verbatim issue lines** — "mostly clean", "a few warnings", and "passes validation" are not review output.

```bash
uv run --script .claude/skills/research-curator/scripts/fix_research_formatting.py --check ./research/{category}/{name}.md
uv run --script .claude/skills/research-curator/scripts/validate_research.py main --json ./research/{category}/{name}.md
uv run --script .claude/skills/research-curator/scripts/validate_research.py check-backlinks ./research
```

| Command | What a defect looks like | Record |
|---|---|---|
| `fix_research_formatting.py --check` | Non-zero exit — the file needs formatting fixes | Every path the tool named, and the fix it wanted. Run it without `--check`: this review applies fixes, so a path it reformatted is a checked finding |
| `validate_research.py main --json` | Any issue in the JSON `entries[].issues[]` array except `cross_references_absent`, non-blocking per [Validation Rules](./validation-rules.md), and except `relevance_anchor_path_missing` for a path `git log --all --full-history` shows moved, which is an `R` line | `errors: N, warnings: N` from `summary`, then every issue's `check`, `severity`, `message`, and `line`, quoted |
| `validate_research.py check-backlinks ./research` | A residual asymmetric cross-reference involving this entry, or any file the scan could not read or parse | Each object in JSON `edges`, and every object in `skips` when `scan_skipped_files` is non-zero. `--fix` retains the original `edges` and adds repair outcome fields |

A non-zero `scan_skipped_files` field fails this command on its own, because a file dropped from
the scan was never compared -- exit 0 would claim coverage the scan did not have. Treat those
paths as Gate 1 defects, not as noise.

**Cross-reference reciprocity** is measured by `check-backlinks`, not by eye, and repaired by the orchestrator; the reviewer reports only a residual pair. An entry that cites B while B does not cite back is a defect against this entry even though the missing row lives in B. Row format: [Cross-Reference Format](./cross-reference-format.md). A pair whose missing row is in an `--exclude`d or unwritable file is recorded as an unchecked `R` line, not a `D` line; the final verdict block relays unchecked `R` lines to the user, and no worker acts on them.

---

## Gate 2 — Fidelity Rules

Each rule in [Entry Quality Standards](./entry-quality-standards.md) is a separate check with its own verdict. Run every rule below; one rule's pass says nothing about another's.

| Check | Question | Defect |
|---|---|---|
| **Rule 1 — Read Before Writing** | Does every section's content trace to a source listed in References, and was that source actually reachable? | A claim whose only possible basis is the resource's name, URL path, or domain. An inaccessible source whose absence is not stated in References |
| **Rule 2 — Preserve Counts** | Are capability figures written as the exact number the source gives? | A vague quantifier ("many languages", "recent release", "low latency") standing where the source has a figure |
| **Rule 3 — Absence vs Nonexistence** | Where information was not found, does the entry say it was not found? | "Doesn't support X" / "Not available" / "Not supported" where the honest statement is "Not mentioned in documentation" or "Unable to access {source}". Applies to the entry's repo claims too: `-> not found by these searches` (or the older `-> nothing in {scope}`) reports that those searches returned nothing, and an item reading it as "this repo has no X" is a Rule 3 defect |
| **Rule 4 — Explicit Confidence** | Does every major section carry a confidence level in the confidence map? | A section missing from the map. A `high` on a section whose sources are informal, partial, contradictory, or code-read |

---

## Gate 3 — Depth

Score each section against its bar in [Entry Quality Standards](./entry-quality-standards.md#depth-requirements). Present-but-thin is a defect; the section existing is not the bar.

| Section | Passes when | Defect |
|---|---|---|
| **Technical Architecture** | Names components with their exact source names, describes data flow or execution model, and names extension or integration points | "Uses a plugin-based architecture" with no component named and no mechanism given |
| **Key Features** | Each feature states what it does AND the mechanism by which it does it | A feature list that is a list of outcomes with no mechanism |
| **Installation & Usage** | At least one complete example taken verbatim or near-verbatim from official docs; install command verified against official docs | An install command assembled from a guessed package name. A usage example with no source behind it |
| **Limitations and Caveats** | Present, with either documented limitations or the explicit low-confidence absence statement | Section missing, empty, or filled with "N/A" |

---

## Gate 4 — Repo Claims Verified Against the Repo

Every statement an entry or an analysis file makes about **this repository** is a claim to verify against the actual files, not a claim to accept. This gate covers the entry's "Relevance to Claude Code Development" section and every proposal in the `-improvements.md` and `-utilization.md` files.

For each repo claim, in order:

1. **Path exists** — open the path first. If it opens, step 2 applies: verify what it says against
   what is actually there. If it does not open, three outcomes are available, and which one applies
   is settled by `git log --all --full-history -- {path}` plus the claim's own wording:

   - **Never existed** — a claim about **what is there now** ("`X` already does Y", "the hook in
     `Z` writes the field") whose path the log has never seen. Record a **defect**: what was named,
     and what is actually there. Record the path exactly as written; a near-miss is the writer's to
     correct, not the reviewer's to guess at.
   - **Existed and moved** — the same kind of claim, but the log returns the commits that once held
     the path. The entry was accurate when written and a repository change since then moved or
     removed the path. Record a **repair** against the citing file, naming the commit the log gives.
     The writer's verdict stands.
   - **A place to create something** — the file's absence is the reason the proposal exists, which is
     the entire purpose of an Integration Opportunities item. "Integration point:
     `.claude/hooks/pre-push.js`", "new skill in `plugins/developer-tools/skills/ci-debugger/`", "new
     file at", "target state", "could add", "consider adding" all read this way. Check instead that
     the parent location it would go into exists, and let step 3 settle whether something already
     implements it.

   Opening first, then consulting the log, is what keeps a path the repository renamed out from under
   a correct entry in the repair column rather than the defect column.
2. **Path is described correctly** — the file's real contents match what the claim says about them. A proposal that names a real path but misdescribes what lives there is a defect of the same severity as an invented path. So is a quoted `Source pattern` or `Current state` line that no longer exists in the entry or the file.
3. **Gap is real** — where a proposal says the local system lacks a capability, the file confirms the absence. A capability the file already implements makes the proposal a defect, not a low-confidence proposal.
4. **Measurable signal is runnable** — where a proposal names a command or an observable field as its completion signal, that command runs and that field is reachable.
5. **Quote supports the claim** — each present-anchor Relevance item carries a `Found by:` line naming the tool and query that surfaced the file ([Entry Template](./entry-template.md)'s Relevance item shape). Open the path, find the quoted body line, and check that it supports what the item says about this repo. A line that shares the query's words but concerns something else is a defect no matter how real the path is: a GUI `widget` anchored to a tmux menu widget, an SDL2 `simulator` anchored to an iOS Simulator. An item with no `Found by:` line is itself the defect. An entry written before this shape carries a `Term:` line instead; check that its quote contains that Term.
6. **Quote is an assertion and a locator** — reject a quoted line that is a frontmatter field (`description:`, `name:`, `allowed-tools:`), a bullet in a link list or index table, or a sample argument inside a code fence. Each carries the words without asserting anything about this repo's behaviour. Reject one that cannot be re-found either — `true`, `3`, a lone heading word.
7. **Paths are distinct** — no two Relevance items anchor to the same file. Repeated paths multiply one observation into several findings; count them as one and record the rest as defects.

Record each verified claim with the path you read. A gate 4 pass asserts you opened the files; it cannot be reached by reading the proposal alone.

---

## Gate 5 — Did the Analysis Engage This Repo?

Judgment check, applied to the entry's "Relevance to Claude Code Development" section and to both analysis files.

Ask: **was this text produced by running something against this repository?**

Two item shapes pass, and they pass for different reasons.

- A **presence anchor** passes when it names a specific file, skill, agent, or workflow of this repo and says something about it that is true here and would be false elsewhere.
- An **absence anchor** passes when it lists every tool and query run, and you re-run at least one of them — a semantic tool when one is available — and nothing relevant comes back. Its "nothing relevant returned" is true of most repositories, so it never satisfies the would-be-false-elsewhere test; re-running the searches is what makes it a finding rather than a claim. An anchor you could not re-run is `NOT RUN`, not a pass. An anchor that lists no tool or query, or whose searches now return a relevant file, is a defect: report it as a stale anchor, and do not restate it as "the entry claims this repo has no X" — per Gate 2 Rule 3, the entry claims no such thing. An entry written before this shape records `git grep` commands with counts; the validator's absence-anchor checks re-run those, and this gate spends its judgment on whether the recorded searches fit the capability.
- **FAILS** when an item carries neither shape — text that would survive a find-and-replace of this repo's name, generic advice ("could improve code quality", "useful for agent workflows", "fits well with this project's architecture") dressed as repo-specific findings.

An entry whose Relevance section is entirely absence anchors passes this gate when every re-run comes back empty. It is a thin entry, not a failing one; record the count so the thinness is visible.

A gate 5 failure is a defect even when every individual sentence in gate 4 verified.

---

## Gate 6 — Hallucination Triggers

Scan the entry and both analysis files for each trigger. Quote every hit.

| Trigger | Scan for | Defect unless | Required correction |
|---|---|---|---|
| **Speculation language** | "I think", "likely", "probably", "seems", "should be", "assume", "maybe", "might" | The phrase sits inside a verbatim quotation from a primary source, attributed as such | Replace with what the source states, with "Not mentioned in documentation" per Rule 3, or with the steps taken and what was observed |
| **Causality without evidence** | "because", "due to", "caused by", "therefore", "this means", "as a result" | The sentence cites the specific observation behind it — a source passage, a file and line, a command's output | Rewrite as an observation alone, or as an explicit hypothesis plus the verification step that would settle it |
| **Pseudo-quantification** | Scores and percentages — "8.5/10", "70% faster", "100% coverage" | The figure is quoted from a primary source with its method, or the entry states the method used to produce it | Replace with the measured evidence, or remove the figure |
| **Completeness overclaims** | "all files checked", "comprehensive analysis", "fully resolved", "everything fixed", "every skill reviewed" | The text lists the concrete checks performed and their scope | List what was inspected and with what scope, or narrow the claim to what was actually covered |

These four triggers are copied in **by decision, not by fallback, and scoped to Gate 6 only** —
this does not contradict `AGENTS.md`'s skill-policy table routing "Reviewing agent output" to
`/hallucination-detector:hallucination-audit` for other review contexts. Nothing under
`.claude/skills/research-curator/`, or in the agents it spawns, calls that plugin; the plugin is not
in `enabledPlugins` in `.claude/settings.json`, so `/hallucination-detector:hallucination-audit` is
not reachable in this checkout; and, after following the generation prerequisite in `AGENTS.md`, the
generated `harness_compatibility.json` view carries no entry for it, so it is reachable in no other
harness either. Whether it is enabled is therefore not a question this gate's
behaviour turns on. Do not re-open it, and do not replace this table with a call to that plugin or
any other out-of-skill route: everything Gate 6 needs lives under
`.claude/skills/research-curator/`.

SOURCE: Triggers 1–4 adapted for research-entry content from the `hallucination-detector` plugin's `commands/hallucination-audit.md` (<https://github.com/bitflight-devops/hallucination-detector>, accessed 2026-09-13) — copied in and re-scoped, not referenced. Plugin availability read from `.claude-plugin/marketplace.json`, `.claude/settings.json` `enabledPlugins`, and the generated `harness_compatibility.json` view (2026-09-13); follow the `AGENTS.md` generation prerequisite before reading that view. `AGENTS.md` Repository Overview states the plugin is "not enabled by default in every install".

---

## Findings Document

One per entry, at the path the invocation names, kept across rounds; the reviewer and the `--fix` worker both write it. The reviewer writes every defect and repair as an unchecked line before fixing any. Whoever acts on a line adds `did:` with a short action note, and checks the line off once its fix is re-found in the file.

```text
- [ ] D1 | gate {N} | {file}:{line} | "{exact quoted text}" | {required correction}
- [x] D2 | gate {N} | {file}:{line} | "{exact quoted text}" | {required correction} | did: {what changed}
- [ ] D3 | gate {N} | {file}:{line} | "{exact quoted text}" | needs: {data to gather, and from where} | did: {what was tried}
```

`D` marks a defect, `R` a repair; ids stay fixed across rounds. The reviewer writes only the entry, its analysis files, and this document.

**Fix with no additional research:** reword; restructure; add a missing section from material already in the entry or in files already cited or opened; fix a quote re-found in a file already available; remove a claim that cannot be sourced. Re-running a recorded command to check it is verification, not research.

**Leave unchecked** any correction that needs data gathering to validate — fetching upstream sources, re-running a repo anchor pass for new evidence — with `needs:` stating the data. A finding in a file outside the writable set is also left unchecked, naming that file.

**Rounds after the first** (the invocation says which): review the worker's changes and research, not only the lines. Run every gate over the files again and check each `did:` note against the file and the source it cites; a checked line whose fix is absent or wrong reopens unchecked. Add a line only for a defect a gate defines; prose no gate names is not a finding. A closed finding set is what lets rounds converge. A gate whose findings recur across rounds marks creator and reviewer instructions that disagree; the orchestrator reports its id.

---

## Verdict

Report in this form. Gate lines record the state after this pass's fixes; the defects themselves live in the findings document.

```text
REVIEW: ./research/{category}/{name}.md
SCRATCH: {findings document path}

GATE 1 mechanical:    PASS | FAIL | NOT RUN ({reason})
  fix_research_formatting:         exit {N}
  validate_research main --json:   orchestrator | errors {N}, warnings {N}
  check-backlinks:                 orchestrator | {N} asymmetric pairs, {N} scan-skipped files
GATE 2 fidelity:      PASS | FAIL — rules failed: {1|2|3|4}
GATE 3 depth:         PASS | FAIL — sections failed: {names}
GATE 4 repo claims:   PASS | FAIL — {N} claims verified, {N} defective, {N} for repair
GATE 5 engagement:    PASS | FAIL
GATE 6 triggers:      PASS | FAIL — triggers hit: {names}

DEFECTS: {N} found, {N} checked, {N} unchecked
REPAIRS: {N} found, {N} checked, {N} unchecked

UNCHECKED: (each unchecked line, verbatim)
- [ ] D3 | gate {N} | ...

VERDICT: PASS | FAIL | NOT RUN -- {reason}
```

`PASS` requires every gate at PASS and no unchecked defect. Any gate at FAIL or NOT RUN, or any unchecked defect, is `FAIL` — an unchecked defect and a `PASS` verdict cannot both be true. A `NOT RUN` gate is a `FAIL` with no line for the worker; the orchestrator stops on it, naming the gate.

An unchecked repair is work scheduled against the citing file and is set aside: an entry whose only unchecked lines are repairs is `PASS` and keeps its README row. A gate whose only findings are repairs is `PASS`.
