# Research Entry Review Rubric

How to review a finished research entry and the analysis files produced from it.

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

Run all three commands. Report their output as **exact counts per severity and the verbatim issue lines** — "mostly clean", "a few warnings", and "passes validation" are not review output.

```bash
uv run --script .claude/skills/research-curator/scripts/fix_research_formatting.py --check ./research/{category}/{name}.md
uv run --script .claude/skills/research-curator/scripts/validate_research.py main --json ./research/{category}/{name}.md
uv run --script .claude/skills/research-curator/scripts/validate_research.py check-backlinks ./research
```

| Command | What a defect looks like | Record |
|---|---|---|
| `fix_research_formatting.py --check` | Non-zero exit — the file needs formatting fixes | Every path the tool named, and the fix it wanted. `--check` does not write; drop `--check` only when this review is also applying fixes |
| `validate_research.py main --json` | Any issue in the JSON `entries[].issues[]` array | `errors: N, warnings: N` from `summary`, then every issue's `check`, `severity`, `message`, and `line`, quoted |
| `validate_research.py check-backlinks ./research` | Any asymmetric cross-reference involving this entry, or any file the scan could not read or parse | Each object in JSON `edges`, and every object in `skips` when `scan_skipped_files` is non-zero. `--fix` retains the original `edges` and adds repair outcome fields |

A non-zero `scan_skipped_files` field fails this command on its own, because a file dropped from
the scan was never compared -- exit 0 would claim coverage the scan did not have. Treat those
paths as Gate 1 defects, not as noise.

**Cross-reference reciprocity** is measured by `check-backlinks`, not by eye. An entry that cites B while B does not cite back is a defect against this entry even though the missing row lives in B. Row format: [Cross-Reference Format](./cross-reference-format.md).

---

## Gate 2 — Fidelity Rules

Each rule in [Entry Quality Standards](./entry-quality-standards.md) is a separate check with its own verdict. Run all five; one rule's pass says nothing about another's.

| Check | Question | Defect |
|---|---|---|
| **Rule 1 — Read Before Writing** | Does every section's content trace to a source listed in References, and was that source actually reachable? | A claim whose only possible basis is the resource's name, URL path, or domain. An inaccessible source whose absence is not stated in References |
| **Rule 2 — Preserve Counts** | Are capability figures written as the exact number the source gives? | A vague quantifier ("many languages", "recent release", "low latency") standing where the source has a figure |
| **Rule 2a — No Popularity Statistics** | Did this run leave every star, download, fork, and contributor count out of the entry? | A figure this run gathered, wherever it landed — a badge, a quoted README passage, a section of its own. Figures the entry already carried stay as written, per Rule 2a's scope |
| **Rule 3 — Absence vs Nonexistence** | Where information was not found, does the entry say it was not found? | "Doesn't support X" / "Not available" / "Not supported" where the honest statement is "Not mentioned in documentation" or "Unable to access {source}". Applies to the entry's repo claims too: `-> nothing in {scope}` reports that these search terms matched nothing in that scope, and an item reading it as "this repo has no X" is a Rule 3 defect |
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
2. **Path is described correctly** — the file's real contents match what the claim says about them. A proposal that names a real path but misdescribes what lives there is a defect of the same severity as an invented path.
3. **Gap is real** — where a proposal says the local system lacks a capability, the file confirms the absence. A capability the file already implements makes the proposal a defect, not a low-confidence proposal.
4. **Measurable signal is runnable** — where a proposal names a command or an observable field as its completion signal, that command runs and that field is reachable.
5. **Quoted line contains the matched term** — each present-anchor Relevance item carries a `Term:` line naming the term that produced its match list ([Entry Template](./entry-template.md)'s Relevance item shape). Check that the quoted line contains that term. A quote that does not is evidence about something else, and is a defect no matter how real the path is: a GUI `widget` anchored to a tmux menu widget, an SDL2 `simulator` anchored to an iOS Simulator. An item with no `Term:` line is itself the defect — record it as one and check the quote against both of the capability's terms; do not mark this rule NOT RUN for a missing field the entry was required to write.
6. **Quote is an assertion and a locator** — reject a quoted line that is a frontmatter field (`description:`, `name:`, `allowed-tools:`), a bullet in a link list or index table, or a sample argument inside a code fence. Each carries the term without asserting anything about this repo's behaviour. Reject one that cannot be re-found either — `true`, `3`, a lone heading word.
7. **Paths are distinct** — no two Relevance items anchor to the same file. Repeated paths multiply one observation into several findings; count them as one and record the rest as defects.

Record each verified claim with the path you read. A gate 4 pass asserts you opened the files; it cannot be reached by reading the proposal alone.

---

## Gate 5 — Did the Analysis Engage This Repo?

Judgment check, applied to the entry's "Relevance to Claude Code Development" section and to both analysis files.

Ask: **was this text produced by running something against this repository?**

Two item shapes pass, and they pass for different reasons.

- A **presence anchor** passes when it names a specific file, skill, agent, or workflow of this repo and says something about it that is true here and would be false elsewhere.
- An **absence anchor** passes when you re-run **both** of its search commands — the narrow term and the broader term — and get zero from each. Its `→ 0 matches` is true of most repositories, so it never satisfies the would-be-false-elsewhere test; re-running the commands is what makes it a finding rather than a claim, and running them is the check. An anchor whose commands you did not re-run is `NOT RUN`, not a pass. An anchor recording only one command is a defect — one term at zero is the manufactured absence Phase 1c exists to prevent, not an anchor. An anchor whose commands now return matches is also a defect: what the entry recorded as searched-and-empty is neither, so the item rests on nothing. Report it as a stale anchor, and do not restate it as "the entry claims this repo has no X" — per Gate 2 Rule 3, the entry claims no such thing.
- **FAILS** when an item carries neither shape — text that would survive a find-and-replace of this repo's name, generic advice ("could improve code quality", "useful for agent workflows", "fits well with this project's architecture") dressed as repo-specific findings.

An entry whose Relevance section is entirely absence anchors passes this gate when every command re-runs to zero. It is a thin entry, not a failing one; record the count so the thinness is visible.

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
not reachable in this checkout; and `harness_compatibility.json` carries no entry for it, so it is
reachable in no other harness either. Whether it is enabled is therefore not a question this gate's
behaviour turns on. Do not re-open it, and do not replace this table with a call to that plugin or
any other out-of-skill route: everything Gate 6 needs lives under
`.claude/skills/research-curator/`.

SOURCE: Triggers 1–4 adapted for research-entry content from the `hallucination-detector` plugin's `commands/hallucination-audit.md` (<https://github.com/bitflight-devops/hallucination-detector>, accessed 2026-09-13) — copied in and re-scoped, not referenced. Plugin availability read from `.claude-plugin/marketplace.json`, `.claude/settings.json` `enabledPlugins`, and `harness_compatibility.json` (2026-09-13); `AGENTS.md` Repository Overview states the plugin is "not enabled by default in every install".

---

## Verdict

Report in this form:

```text
REVIEW: ./research/{category}/{name}.md

GATE 1 mechanical:    PASS | FAIL | NOT RUN ({reason})
  fix_research_formatting --check: exit {N}
  validate_research main --json:   errors {N}, warnings {N}
  check-backlinks:                 {N} asymmetric pairs, {N} scan-skipped files
GATE 2 fidelity:      PASS | FAIL — rules failed: {1|2|2a|3|4}
GATE 3 depth:         PASS | FAIL — sections failed: {names}
GATE 4 repo claims:   PASS | FAIL — {N} claims verified, {N} defective, {N} for repair
GATE 5 engagement:    PASS | FAIL
GATE 6 triggers:      PASS | FAIL — triggers hit: {names}

DEFECTS: {N}
1. {file}:{line} — GATE {N} — "{exact quoted text}" — {required correction}
2. ...

REPAIRS: {N}
1. {file}:{line} — GATE {N} — "{exact quoted text}" — {the change that invalidated it} — {required correction}
2. ...

VERDICT: APPROVE | REQUEST CHANGES
```

`APPROVE` requires every gate at PASS and `DEFECTS: 0`. Any gate at FAIL or NOT RUN, or any defect recorded, is `REQUEST CHANGES` — a defect count above zero and an `APPROVE` verdict cannot both be true.

Repairs are reported and then set aside: they are work scheduled against the citing file, so an entry with repairs and `DEFECTS: 0` is `APPROVE` and keeps its README row. A gate whose only findings are repairs is `PASS`.
