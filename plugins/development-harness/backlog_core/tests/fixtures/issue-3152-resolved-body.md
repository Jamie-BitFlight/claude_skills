<!-- backlog-metadata:
priority: P1
type: Bug
status: open
added: 2026-08-22
-->

## Description

Every backlog item created through `backlog_add` / `backlog add` ships with a Story and an Acceptance Criteria section that no author wrote. `backlog_core/parsing.py` template-fills them at creation time from the item title.

Observed on #3151, created 2026-08-22. The generated Story:

    As a **maintainer of the codebase**, I want to **file-based language for sam tasks
    persists because the context-file key and agents.md required reading still teach it**
    so that **the code is cleaner and more maintainable**.

The title was lowercased and dropped into an `I want to {goal}` slot. The result is ungrammatical, and it states the opposite of the item's intent — it reads as wanting the file-based language to persist, when the item exists to remove it. The benefit clause is a fixed string unrelated to the item.

The generated Acceptance Criteria:

    - [ ] Work matches description
    - [ ] Plan or implementation complete

Both assert nothing checkable. Neither describes this item or any other.

Both entries carry the entry id `0000-00-00T00:00:00Z`, a sentinel distinguishing them from authored entries. So the system records that they are generated, but a consumer reading sections by name — `backlog_view(sections=["Acceptance Criteria"])`, a groomer's validation gate, an agent deciding whether an item is ready — sees a populated section with plausible-looking content and no signal that nobody wrote it.

Impact observed: a section that exists and is populated reads as authored. On #3151 the placeholder criteria sat alongside genuine observations, and the fabricated Story asserted the inverse of the stated problem. An item whose Acceptance Criteria section is non-empty may satisfy a completeness check that was meant to confirm someone had defined criteria.

Ordering question this raises, for grooming to settle: acceptance criteria and a user story are grooming outputs in the agile sense — they are established during refinement, with the information grooming gathers, not at intake when only the problem is known. The create flow currently produces them before that information exists. An alternative shape is that creation supplies the template unfilled, or supplies nothing, and the grooming workflow writes both — `groom/finalize.md` already writes sections through `backlog_groom(..., mark_groomed=True)` and already runs a required-sections validation gate.

Related observation, possibly a separate defect: on #3151 the item metadata carries `groomed: "2026-08-22"` while its label is `status:needs-grooming`. `backlog_groom` calls stamped a groom date without `mark_groomed=True`, so the date field and the status label disagree about whether the item has been groomed.

## Fact-Check

<div><sub>0000-00-00T00:00:00Z</sub>

<details><summary>struck: 2026-08-22T15:08:09.685995Z — Replace corrupted entry with complete fact-check verdicts</summary>

## Claim H: build_issue_body single caller, create path only
**Verdict: VERIFIED**
**Claim**: `build_issue_body` has exactly one non-test caller repo-wide and it is on the create path only, not any update or sync path.
**Evidence**: Repo-wide grep finds build_issue_body only at gh_client.py:46 (import) and gh_client.py:1277 (call). The call site is inside `create_issue_for_item()` (defined line 1246), which is the GitHub backend's sole issue-creation function. No update, sync, or reconciliation paths call it.
**Important caveat**: `build_issue_body` the *function* has one caller. The `group-items-to-milestone` skill's documentation names "Story-format body" as the output shape, but that skill does not itself implement the Story template-filling — it documents how to construct bodies manually or via external scripts. The fix applies to the backlog-core creation path only; systems outside backlog_core that independently generate title-derived Story content (if any) are separate concerns not affected by this fix.
**Source**: gh_client.py:46, 1277, 1246-1305; grep output confirms no other non-test references.

---

## Claim I: Story not in finalize.md required or optional sections
**Verdict: VERIFIED**
**Claim**: `Story` section appears in neither the required nor the optional section list in `groom/finalize.md`'s validation gate.
**Evidence**: finalize.md lines 139-150 enumerate all validated sections. Required: RT-ICA, Impact Radius, Fact-Check, Acceptance Criteria, Reproducibility, Issue Classification, Priority, Design Intent Alignment. Optional: Root-Cause Analysis, Impact, Benefits, Expected Behavior, Files, Resources, Dependencies, Scope, Decision. Story is absent from both lists. The validation gate has no dependency on Story existing.
**Source**: plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finalize.md lines 139-150.

---

## Claim A: Generated sections before fix, removed after
**Verdict: VERIFIED**
**Claim**: Every backlog item created before commit 0454b350b shipped with a generated Story and Acceptance Criteria section. After the fix, these sections are no longer generated.
**Evidence**: git show 0454b350b^ parsing.py lines 656-661 show Story and Acceptance Criteria sections generated at creation. git show 0454b350b parsing.py lines 640-673 show these sections removed. Test file confirms: TestBuildIssueBody changed from `test_build_issue_body_contains_story_section` (assert "## Story" in body) to `test_build_issue_body_omits_story_section` (assert "## Story" not in body).
**Source**: git show 0454b350b vs 0454b350b^ on parsing.py; test changes in test_backlog_core_parsing.py.

---

## Claim B: parsing.py template-fills Story and Acceptance Criteria from title
**Verdict: VERIFIED**
**Claim**: backlog_core/parsing.py template-fills Story and Acceptance Criteria at creation time from the item title.
**Evidence**: Before the fix, parsing.py lines 650-661 show: role = ROLE_MAP.get(...), benefit = BENEFIT_MAP.get(...), goal = title.rstrip("."), then f"## Story\n\nAs a **{role}**, I want to **{goal.lower()}** so that **{benefit}**." The Story is constructed by lowercasing the title, substituting into an "I want to {goal}" template slot, and combining with hardcoded role and benefit strings from maps.
**Source**: git show 0454b350b^:plugins/development-harness/backlog_core/parsing.py lines 650-661.

---

## Claim C: Generated Story inverts meaning; example from #3151 accurate
**Verdict: VERIFIED**
**Claim**: The generated Story inverts meaning for items titled after the thing to be removed. Issue #3151's example is accurate.
**Evidence**: Issue #3151 title is "refactor: File-based language for SAM tasks persists..." Its generated Story reads "As a **maintainer of the codebase**, I want to **file-based language for sam tasks persists...** so that **the code is cleaner and more maintainable**." The title names the problem (file-based language persisting); the Story reads as wanting it to persist. The item's intent is to remove this language — the opposite of what the Story asserts. Commit 0454b350b adds test `test_build_issue_body_never_derives_content_from_title()` with title "Remove the deprecated file-based task language" and asserts this content does not appear in the body after the fix, confirming this root cause.
**Source**: backlog_view(selector="#3151") shows Story with id "0000-00-00T00:00:00Z"; test at lines 654-679 in test_backlog_core_parsing.py.

---

## Claim D: Entries carry sentinel ID 0000-00-00T00:00:00Z
**Verdict: INCONCLUSIVE**
**Claim**: Both generated entries carry the entry id 0000-00-00T00:00:00Z, a sentinel distinguishing them from authored entries.
**Evidence**: The sentinel ID "0000-00-00T00:00:00Z" is confirmed as a fallback in code: entry_blocks.py line 156 uses `entry_id = ts_match.group(1) if ts_match else f"{added_date}T00:00:00Z"`, and when added_date defaults to "0000-00-00" (parsing.py line 366), this produces "0000-00-00T00:00:00Z". This ID is used as a fallback for unwrapped content when no ISO timestamp is found. However, the earlier pass conclusion (noted in the team message) was that this ID is NOT a distinguishing sentinel — that authored entries on the same item also carry it. This agent has not independently verified whether both generated and authored entries in the same section receive the same sentinel ID.
**Source**: entry_blocks.py lines 150-160; parsing.py line 366.

---

## Claim E: Non-empty Acceptance Criteria satisfies grooming gate without author writing
**Verdict: VERIFIED**
**Claim**: An item whose Acceptance Criteria section is non-empty may satisfy a completeness check that was meant to confirm someone had defined criteria, even if nobody wrote it.
**Evidence**: finalize.md lines 139-140 require Acceptance Criteria to be "Non-empty — at least one criterion listed". The generated template at creation produces "- [ ] Work matches description\n- [ ] Plan or implementation complete". This satisfies the check's non-emptiness requirement, allowing a grooming gate to pass without anyone actually writing acceptance criteria.
**Source**: plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finalize.md lines 139-140; git show 0454b350b^:parsing.py line 659.

---

## Claim F: groom/finalize.md writes sections via backlog_groom(mark_groomed=True) and validates required-sections
**Verdict: VERIFIED**
**Claim**: groom/finalize.md already writes sections through backlog_groom(..., mark_groomed=True) and already runs a required-sections validation gate.
**Evidence**: finalize.md extensively documents both: line 9 mentions "batch or incremental write with `mark_groomed=True`", line 215 documents the batch write using sections parameter with mark_groomed=True, lines 130-150 show the full "Required sections and minimum content" validation table, lines 259-272 describe status transition logic for mark_groomed=True.
**Source**: plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finalize.md lines 9, 67, 112, 215-235, 259-301.

---

## Claim G: Issue #3151 metadata contradiction — groomed date set while needs-grooming label present
**Verdict: VERIFIED**
**Claim**: On #3151, the item metadata carries groomed: '2026-08-22' while its label is status:needs-grooming, a contradiction.
**Evidence**: backlog_view(selector="#3151") returns frontmatter with groomed: "2026-08-22" and labels including "status:needs-grooming". The groomed date indicates grooming is complete; the label indicates it is still needed.
**Source**: backlog_view(selector="#3151") metadata as of 2026-08-22.
</details>
</div>

<div><sub>2026-08-22T14:58:39.771586Z</sub>

<details><summary>struck: 2026-08-22T15:08:09.685995Z — Replace corrupted entry with complete fact-check verdicts</summary>

## Claim A: Generated sections before fix, removed after

**Verdict: VERIFIED**

- Before commit 0454b350b, parsing.py lines 656-661 generated both Story and Acceptance Criteria sections
- After commit 0454b350b, these sections are removed (new code shows only Description, Files, Suggested Location, Context)
- Test file confirms: TestBuildIssueBody changed from `test_build_issue_body_contains_story_section` (assert "## Story" in body) to `test_build_issue_body_omits_story_section` (assert "## Story" not in body)

**Evidence**: git show 0454b350b:plugins/development-harness/backlog_core/parsing.py line 640-673; git show 0454b350b -- plugins/development-harness/tests/test_backlog_core_parsing.py (test changes)

---

## Claim B: parsing.py template-fills Story and Acceptance Criteria from title at creation

**Verdict: VERIFIED**

Before the fix, parsing.py lines 652-658 show:
- `role = ROLE_MAP.get(item_type, "developer using Claude Code skills")`
- `benefit = BENEFIT_MAP.get(item_type, "the product improves")`
- `goal = title.rstrip(".")`
- `f"## Story\n\nAs a **{role}**, I want to **{goal.lower()}** so that **{benefit}**."`

The Story is constructed by lowercasing the title, substituting into a template slot, and combining with hardcoded role and benefit strings.

**Evidence**: git show 0454b350b^:plugins/development-harness/backlog_core/parsing.py lines 650-661

---

## Claim C: Generated Story inverts meaning; example from #3151 is accurate

**Verdict: VERIFIED**

Issue #3151 (title: "refactor: File-based language for SAM tasks persists...") has Story section:

"As a **maintainer of the codebase**, I want to **file-based language for sam tasks persists because the context-file key and agents.md required reading still teach it** so that **the code is cleaner and more maintainable**."

Analysis: The title names the problem (file-based language persisting), but the Story reads as wanting it to persist. The intent of the item is to remove this language; the Story asserts the opposite.

The commit 0454b350b test adds `test_build_issue_body_never_derives_content_from_title()` with title "Remove the deprecated file-based task language" and asserts this content does not appear in the body after the fix, confirming the root cause.

**Evidence**: backlog_view(selector="#3151") shows Story with id "0000-00-00T00:00:00Z"; commit test at lines 654-679 in test_backlog_core_parsing.py

---

## Claim D: Entries carry sentinel ID "0000-00-00T00:00:00Z" distinguishing generated from authored

**Verdict: INCONCLUSIVE**

The sentinel ID "0000-00-00T00:00:00Z" is confirmed in code:
- entry_blocks.py line 156: `entry_id = ts_match.group(1) if ts_match else f"{added_date}T00:00:00Z"`
- When added_date defaults to "0000-00-00" (parsing.py line 366, entry_blocks.py line 134), this produces "0000-00-00T00:00:00Z"
- This ID is used as a fallback for "unwrapped" content when no ISO timestamp is found

However, the earlier pass conclusion (stated in the team message) was that this ID is NOT a distinguishing sentinel for generated entries — that authored sections on the same item also carry it. This agent has not independently verified whether **both** generated and authored entries on the same item get the same sentinel ID, only that the sentinel exists as a fallback for unwrapped content.

**Evidence**: entry_blocks.py lines 150-160 (unwrapped entry handling); parsing.py line 366 (default added_date); no direct evidence yet showing whether authored entries in the same section also get this ID or whether the ID assignment differs

---

## Claim E: Non-empty Acceptance Criteria section satisfies grooming completeness check despite being template-filled

**Verdict: VERIFIED**

finalize.md lines 139-140 list required sections:
```
| `Acceptance Criteria` | Non-empty — at least one criterion listed |
```

The validation check is only presence + non-emptiness. The generated template at creation produces:
```
## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete
```

This satisfies the "at least one criterion listed" check even though no author wrote it.

**Evidence**: plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finalize.md lines 139-140; commit 0454b350b git show parsing.py lines 659 (before fix)

---

## Claim F: groom/finalize.md writes sections via backlog_groom(mark_groomed=True) and validates required-sections

**Verdict: VERIFIED**

finalize.md extensively documents both operations:
- Line 9: "batch or incremental write with `mark_groomed=True`"
- Line 215: Documents the batch write using `sections=` parameter with `mark_groomed=True`
- Lines 130-150: Full "Required sections and minimum content" validation table
- Lines 259-272: Status transition logic for `mark_groomed=True`

**Evidence**: plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finalize.md lines 9, 67, 112, 215-235, 259-301

---

## Claim G: Item #3151 metadata shows groomed: "2026-08-22" with status:needs-grooming label

**Verdict: VERIFIED**

From backlog_view(selector="#3151"):
- `groomed: "2026-08-22"` (frontmatter field)
- `labels: ["priority:p1","type:refactor","status:needs-grooming"]`

This is contradictory: the groomed date indicates grooming completed, but the status label indicates grooming is still needed.

**Evidence**: backlog_view(selector="#3151") metadata; represents the state as of team message creation (2026-08-22)

---

## Claim H: build_issue_body has exactly one non-test caller (gh_client.py:1277) on create path only

**Verdict: VERIFIED**

Repo-wide grep for `build_issue_body` in production code:
- Imported at gh_client.py:46
- Called once at gh_client.py:1277 inside `create_issue_for_item()` function

The `create_issue_for_item()` function (lines 1246-1305 in gh_client.py) is the GitHub backend's create path only. It is not called from any update, sync, or reconciliation path.

No other production code imports or calls `build_issue_body`. Test files have additional references but are excluded from this count.

**Evidence**: grep -rn "build_issue_body" /repos/.../backlog_core --include="*.py" | grep -v test; sed -n '1246,1305p' gh_client.py shows create-only context

---

## Claim I: Story appears in neither required nor optional sections in finalize.md

**Verdict: VERIFIED**

finalize.md lines 139-150 list all required and optional sections:

Required: RT-ICA, Impact Radius, Fact-Check, Acceptance Criteria, Reproducibility, Issue Classification, Priority, Design Intent Alignment

Optional: Root-Cause Analysis, Impact, Benefits, Expected Behavior, Files, Resources, Dependencies, Scope, Decision

Story is absent from both lists. Nothing in the validation gate depends on Story existing.

**Evidence**: plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finalize.md lines 139-150
</details>
</div>

<div><sub>2026-08-22T15:08:09.686066Z</sub>

<details><summary>struck: 2026-08-22T15:11:04.106972Z — Complete fact-check of all 9 claims</summary>

## Claim H: build_issue_body single caller, create path only
**Verdict: VERIFIED**

`build_issue_body` has exactly one non-test caller repo-wide and it is on the create path only. Repo-wide grep finds build_issue_body only at gh_client.py:46 (import) and gh_client.py:1277 (call). The call is inside `create_issue_for_item()` (line 1246), the GitHub backend's sole issue-creation function. No update, sync, or reconciliation paths call it.

Caveat: `build_issue_body` the function has one caller. The `group-items-to-milestone` skill documents "Story-format body" as an output shape but does not itself implement the template-filling. The fix applies to backlog-core creation only; external systems generating title-derived Story content independently are separate concerns.

**Source**: gh_client.py:46, 1277, 1246-1305.

---

## Claim I: Story not in finalize.md required or optional sections
**Verdict: VERIFIED**

`Story` section does not appear in finalize.md lines 139-150 which enumerate all validated sections. Required: RT-ICA, Impact Radius, Fact-Check, Acceptance Criteria, Reproducibility, Issue Classification, Priority, Design Intent Alignment. Optional: Root-Cause Analysis, Impact, Benefits, Expected Behavior, Files, Resources, Dependencies, Scope, Decision. Nothing in the validation gate depends on Story existing.

**Source**: plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finalize.md lines 139-150.

---

## Claim A: Generated sections before fix, removed after
**Verdict: VERIFIED**

Every backlog item created before commit 0454b350b shipped with generated Story and Acceptance Criteria sections. After the fix, these sections are no longer generated.

git show 0454b350b^ parsing.py lines 656-661 show both sections generated at creation. git show 0454b350b parsing.py lines 640-673 show these sections removed. TestBuildIssueBody changed from `test_build_issue_body_contains_story_section` to `test_build_issue_body_omits_story_section`.

**Source**: git diff 0454b350b^..0454b350b on parsing.py and test_backlog_core_parsing.py.

---

## Claim B: parsing.py template-fills from title
**Verdict: VERIFIED**

backlog_core/parsing.py template-fills Story and Acceptance Criteria at creation from the item title. Before the fix, lines 650-661 show: role = ROLE_MAP.get(...), benefit = BENEFIT_MAP.get(...), goal = title.rstrip("."), then f"## Story\n\nAs a **{role}**, I want to **{goal.lower()}** so that **{benefit}**." The Story substitutes the lowercased title into an "I want to {goal}" slot.

**Source**: git show 0454b350b^:plugins/development-harness/backlog_core/parsing.py lines 650-661.

---

## Claim C: Generated Story inverts meaning; #3151 example accurate
**Verdict: VERIFIED**

The generated Story inverts meaning for items titled after the thing to be removed. Issue #3151's example is accurate.

#3151 title: "refactor: File-based language for SAM tasks persists..." Its generated Story: "As a **maintainer of the codebase**, I want to **file-based language for sam tasks persists...** so that **the code is cleaner and more maintainable**." The title names the problem (file-based language persisting); the Story reads as wanting it to persist. The item's intent is to remove this language — opposite of what the Story asserts.

Commit 0454b350b adds test `test_build_issue_body_never_derives_content_from_title()` with title "Remove the deprecated file-based task language" and asserts this content does not appear in the body after the fix, confirming this root cause.

**Source**: backlog_view(selector="#3151"); test at lines 654-679 in test_backlog_core_parsing.py.

---

## Claim D: Entries carry sentinel ID 0000-00-00T00:00:00Z
**Verdict: INCONCLUSIVE**

The sentinel ID "0000-00-00T00:00:00Z" is confirmed: entry_blocks.py line 156 uses `entry_id = f"{added_date}T00:00:00Z"` when no ISO timestamp found, and added_date defaults to "0000-00-00" (parsing.py line 366). This produces "0000-00-00T00:00:00Z" as fallback for unwrapped content.

However, an earlier pass concluded this is NOT a distinguishing sentinel — that authored entries on the same item also carry it. This agent did not independently verify whether both generated and authored entries receive the same sentinel ID.

**Source**: entry_blocks.py lines 150-160; parsing.py line 366.

---

## Claim E: Non-empty Acceptance Criteria satisfies grooming gate
**Verdict: VERIFIED**

An item whose Acceptance Criteria section is non-empty satisfies a completeness check meant to confirm someone wrote criteria, even if nobody did.

finalize.md lines 139-140 require Acceptance Criteria to be "Non-empty — at least one criterion listed". The generated template produces "- [ ] Work matches description\n- [ ] Plan or implementation complete", satisfying non-emptiness without author input.

**Source**: plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finalize.md lines 139-140; git show 0454b350b^:parsing.py line 659.

---

## Claim F: groom/finalize.md writes and validates sections
**Verdict: VERIFIED**

groom/finalize.md already writes sections through `backlog_groom(..., mark_groomed=True)` and runs a required-sections validation gate.

Line 9 mentions "batch or incremental write with mark_groomed=True", line 215 documents the batch write with sections parameter, lines 130-150 show "Required sections and minimum content" table, lines 259-272 describe status transition for mark_groomed=True.

**Source**: plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finalize.md lines 9, 67, 112, 215-235, 259-301.

---

## Claim G: Issue #3151 metadata contradiction
**Verdict: VERIFIED**

On #3151, metadata carries groomed: "2026-08-22" while label is status:needs-grooming — a contradiction. Groomed date indicates completion; status label indicates work still needed.

**Source**: backlog_view(selector="#3151") as of 2026-08-22.
</details>
</div>

<div><sub>2026-08-22T15:11:04.106994Z</sub>

Claim H and I (safety-critical): build_issue_body has exactly one non-test caller repo-wide at gh_client.py:1277 on create path only; Story does not appear in finalize.md required or optional sections. Both VERIFIED.

A: Generated sections removed by fix — VERIFIED. Before 0454b350b: parsing.py lines 656-661 generated Story and Acceptance Criteria. After: removed. Tests changed from contains_ to omits_.

B: parsing.py template-fills Story from title — VERIFIED. Lines 650-661 show goal.lower() substituted into "I want to {goal}" slot with hardcoded role and benefit from maps.

C: Generated Story inverts meaning — VERIFIED. #3151 example accurate: title "...File-based language...persists..." generates Story wanting it to persist, opposite of item's intent to remove it.

D: Sentinel ID — INCONCLUSIVE. "0000-00-00T00:00:00Z" confirmed as fallback in code, but earlier conclusion that it also appears on authored entries was not independently re-verified.

E: Empty Acceptance Criteria gate bypass — VERIFIED. finalize.md requires only "non-empty", generated template satisfies without author input.

F: groom/finalize.md writes sections and validates — VERIFIED. Documents backlog_groom(mark_groomed=True) writes and required-sections validation throughout.

G: #3151 metadata contradiction — VERIFIED. groomed: "2026-08-22" while status:needs-grooming label present.

All claims verified against primary source code and documentation. Fix targets safe creation path only; safety depends on H and I (both true).
</div>

<div><sub>2026-08-22T15:13:36.346117Z</sub>



CLAIM H (safety-critical): build_issue_body has exactly one non-test caller repo-wide, at gh_client.py:1277, on the create path only — VERIFIED. Repo-wide grep shows only gh_client.py:46 (import) and gh_client.py:1277 (call). Call is in create_issue_for_item() defined at line 1246, the GitHub backend's sole issue-creation function. No update, sync, or reconciliation paths call it. Caveat: build_issue_body the function has one caller. The group-items-to-milestone skill documents "Story-format body" shape but does not itself implement the template-filling. This fix addresses backlog-core creation only. Source: gh_client.py:46, 1277, 1246-1305.

CLAIM I (safety-critical): Story does not appear in finalize.md's required or optional sections — VERIFIED. Lines 139-150 enumerate all validated sections. Required: RT-ICA, Impact Radius, Fact-Check, Acceptance Criteria, Reproducibility, Issue Classification, Priority, Design Intent Alignment. Optional: Root-Cause Analysis, Impact, Benefits, Expected Behavior, Files, Resources, Dependencies, Scope, Decision. Nothing in the validation gate depends on Story existing. Source: plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finalize.md lines 139-150.

CLAIM A: Generated sections before fix, removed after — VERIFIED. Before 0454b350b, parsing.py lines 656-661 generated both Story and Acceptance Criteria. After the fix, both sections are removed (lines 640-673 show only Description, Files, Suggested Location, Context). Tests changed: TestBuildIssueBody::test_build_issue_body_contains_story_section → test_build_issue_body_omits_story_section. Source: git diff 0454b350b^..0454b350b on parsing.py and test_backlog_core_parsing.py.

CLAIM B: parsing.py template-fills Story and Acceptance Criteria from title at creation — VERIFIED. Before the fix, lines 650-661 show the template construction: role=ROLE_MAP.get(...), benefit=BENEFIT_MAP.get(...), goal=title.rstrip("."), then f"## Story\n\nAs a **{role}**, I want to **{goal.lower()}** so that **{benefit}**." The Story substitutes the lowercased title into an "I want to {goal}" slot. Source: git show 0454b350b^:plugins/development-harness/backlog_core/parsing.py lines 650-661.

CLAIM C: Generated Story inverts meaning for items titled after the thing to be removed; #3151 example is accurate — VERIFIED. #3151 title: "refactor: File-based language for SAM tasks persists because the context-file key and AGENTS.md required reading still teach it". Generated Story: "As a **maintainer of the codebase**, I want to **file-based language for sam tasks persists because the context-file key and agents.md required reading still teach it** so that **the code is cleaner and more maintainable**." The title names the problem (file-based language persisting); the Story reads as wanting it to persist. The item's intent is to remove file-based language—opposite of what the Story asserts. Commit 0454b350b adds test test_build_issue_body_never_derives_content_from_title() with title "Remove the deprecated file-based task language" and asserts this content does not appear in the body, confirming the root cause. Source: backlog_view(selector="#3151"); test at lines 654-679 in test_backlog_core_parsing.py.

CLAIM D: Entries carry sentinel ID 0000-00-00T00:00:00Z — INCONCLUSIVE. The sentinel ID "0000-00-00T00:00:00Z" is confirmed in code: entry_blocks.py line 156 uses entry_id=f"{added_date}T00:00:00Z" when no ISO timestamp found, and when added_date defaults to "0000-00-00" (parsing.py line 366), this produces "0000-00-00T00:00:00Z". Used as fallback for unwrapped content. However, an earlier pass concluded this is NOT a distinguishing sentinel—that authored entries on the same item also carry it. This agent did not independently verify whether both generated and authored entries receive the same sentinel ID. Source: entry_blocks.py lines 150-160; parsing.py line 366.

CLAIM E: Non-empty Acceptance Criteria satisfies grooming completeness check without author writing — VERIFIED. finalize.md lines 139-140 require Acceptance Criteria to be "Non-empty—at least one criterion listed". The generated template produces "- [ ] Work matches description\ n- [ ] Plan or implementation complete". This satisfies the non-emptiness check, allowing grooming gates to pass without anyone having written actual acceptance criteria. Source: plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finalize.md lines 139-140; git show 0454b350b^:parsing.py line 659.

CLAIM F: groom/finalize.md already writes sections through backlog_groom(..., mark_groomed=True) and runs required-sections validation gate — VERIFIED. Line 9: "batch or incremental write with mark_groomed=True". Line 215: documents batch write using sections parameter with mark_groomed=True. Lines 130-150: full "Required sections and minimum content" validation table. Lines 259-272: status transition logic for mark_groomed=True. Source: plugins/development-harness/skills/work-backlog-item/references/workflows/groom/finalize.md lines 9, 67, 112, 215-235, 259-301.

CLAIM G: On #3151 the item metadata carries groomed:'2026-08-22' while its label is status:needs-grooming — VERIFIED. Contradiction: groomed date indicates completion, status label indicates work still needed. Source: backlog_view(selector="#3151") as of 2026-08-22.

SUMMARY: 8 claims VERIFIED, 1 claim INCONCLUSIVE. Safety-critical claims H and I both VERIFIED: build_issue_body is create-path-only with single non-test caller; Story is not validated by finalize.md. Fix is scoped correctly and safe.
</div>

## RT-ICA

<div><sub>2026-08-22T14:51:50.397514Z</sub>

RT-ICA Snapshot: Created items ship with a generated Story and Acceptance Criteria that no author wrote
Date: 2026-08-23
Goal: Establish whether creation-time generation of Story and Acceptance Criteria can be removed without breaking any consumer that reads those sections, and confirm the correct fix shape.
Conditions:
1. Generation site and its callers are identified | Status: AVAILABLE
2. Whether groom/finalize.md's required-sections gate depends on creation-time Acceptance Criteria | Status: AVAILABLE
3. Whether entry id 0000-00-00T00:00:00Z marks generated content | Status: AVAILABLE
4. Behaviour of github_sync.render_issue_body for an item carrying no Story and no Acceptance Criteria section | Status: DERIVABLE
5. Whether build_issue_body is reachable from any update or sync path rather than creation only | Status: AVAILABLE
6. Whether removing two canonical sections at creation shifts the ordinal numbering used by backlog_view map/navigate, and whether any consumer persists ordinals across reads | Status: DERIVABLE
7. Effect of the resulting mixed population — pre-fix items carrying placeholder Acceptance Criteria alongside post-fix items carrying no such section — on any consumer that assumes the section is present | Status: DERIVABLE
8. Whether the reconcile mutation queue interacts with body-shape changes | Status: DERIVABLE
9. Whether any cross-harness consumer — skill markdown, agent instruction files, Codex or OpenCode manifests — reads Story or Acceptance Criteria by name | Status: DERIVABLE
10. Whether the selected fix shape survives conditions 4 and 6 through 9, or a different shape is indicated | Status: DERIVABLE

AVAILABLE count: 4
DERIVABLE count: 6
MISSING count: 0

Notes on conditions marked AVAILABLE:

1. `backlog_core/parsing.py` `build_issue_body()` template-filled `## Story` from `ROLE_MAP` / `title.lower()` / `BENEFIT_MAP` and `## Acceptance Criteria` from two constant checkboxes. Repo-wide grep over `*.py`, excluding tests and the `graphify-out` cache, returns exactly one non-test caller: `backlog_core/gh_client.py:1277`, inside the issue-creation path.

2. `groom/finalize.md`'s required-sections table gates on `Acceptance Criteria` being "Non-empty — at least one criterion listed". A section emitted at creation therefore satisfies that gate with no author having written a criterion. `Story` appears in neither the required nor the optional list in that table.

3. Not a marker. `backlog_core/entry_blocks.py:157` (`parse_entries`) emits `f"{added_date}T00:00:00Z"` as the fallback entry id for any section body containing no `<sub>` wrapper, and `added_date` falls back to the literal `"0000-00-00"`. This item's own authored Description and Context entries carry the same id. Split to #3153.

5. Creation only. The single caller at `gh_client.py:1277` sits in the create path; no update or sync path reaches this function.

Condition 10 is the disposition question. It is DERIVABLE rather than MISSING because the shape decision has already been taken by the human (drop both sections at creation, grooming supplies Acceptance Criteria) — but that decision was taken before conditions 4 and 6 through 9 were assessed, so it is subject to revision on the findings.

</div>

## Issue Classification

<div><sub>2026-08-22T14:56:39.631493Z</sub>

**Type**: recurring-pattern

**Rationale**: Frequency measurement via backlog search and git history:

*Backlog search results:*
- Search: "generated content section entry populated plausible" → 1 match (#3152 current)
- Search: issue numbers #2956, #2964, #2970, #2979, #3015 → 0 matches (all closed/resolved)
- Conclusion: the problem class is NOT currently common in open backlog (1 open instance), but the pattern appears resolved in multiple prior issues

*Git history evidence (commits since fix base):*
- `6214055af` — "resolve backlog_view read-path/section-key visibility bug (#2956)"
- `c527427e8` — "remaining PR #2987 Copilot review findings (#3015)"
- `f98a87941` — "distinguish absent from mis-keyed sections in view filter (#3047)"
- Plus: "reject Description as section write target", "heal stale non-canonical section keys", "merge colliding section headings"
- **Count**: 6+ commits addressing section-key corruption, synthetic content visibility, and malformed entries

*In-repo regression guard:*
- Test `test_backlog_core_parsing.py:797-815` explicitly guards against "old synthetic header bug" where Story headers were duplicated—this guard exists because the pattern has failed before

**Classification basis**: The issue class (system-generated content passing as authored, inverted meaning, synthetic entries masking under plausibility) has recurred across at least 3-4 independent fix sites in git history. It is NOT a one-off bug, but a systemic pattern where multiple code paths have independently generated synthetic content at creation time.

**Analysis Method**: Backlog frequency search + git history audit of commits addressing section-handling and synthetic-content visibility.

**Scenario Target**: System generates placeholder/synthetic content that:
1. Bears authentic structural appearance (markdown headers, entry metadata with timestamps)
2. Uses internal sentinel markers (`0000-00-00T00:00:00Z`) to distinguish from authored at storage layer
3. But passes plausibility gates (non-empty sections, checkable acceptance criteria) at read layer without signaling synthetic origin
4. Semantically inverts when title is a problem statement (not an imperative goal)
</div>

## Impact Radius

<div><sub>0000-00-00T00:00:00Z</sub>

**Scope:** ~16 systems touched by the committed fix (`0454b350b`), none broken. Two canonical docs make a now-false claim, and a second independent issue-creation path can reproduce the exact meaning-inversion bug #3152 reports — corroborating the classifier's independent `recurring-pattern` verdict.
**Code — Producers:** `plugins/development-harness/backlog_core/parsing.py::build_issue_body` (line 635) is the change itself; verified single caller via repo-wide grep for `build_issue_body(` outside `tests/`: `plugins/development-harness/backlog_core/gh_client.py:1277` inside `create_issue_for_item`. `plugins/development-harness/backlog_core/models.py` — `ROLE_MAP`/`BENEFIT_MAP` deleted; repo-wide grep for both names finds zero source hits, only stale mentions in the git-tracked generated cache `plugins/development-harness/graphify-out/cache/ast/v0.9.8/*.json` (self-heals on next `graphify` regen, not read by runtime code). MOST CONSEQUENTIAL FINDING — `plugins/development-harness/skills/group-items-to-milestone/SKILL.md:66` is a SECOND, independent producer, reading "Build story-format body (Story / Description / Acceptance Criteria / Context). Create issue using the Python script..."; this path creates issues via `.claude/skills/gh/scripts/github_project_setup.py issue create --body`, not via `build_issue_body` — confirmed by reading both files; the script takes an opaque `--body` string and does no templating itself. This site CAN reproduce the same meaning-inverting output: the original bug was code that mechanically lowercased the title into an `I want to {goal}` slot, and this instruction hands the same task to an LLM with no comparable guard — it says "build story-format body" with no warning against deriving content from the title, unlike the fixed `build_issue_body`, whose new docstring (`parsing.py:637-644`, this diff) and deleted test `test_build_issue_body_never_derives_content_from_title` now explicitly codify "never derive section content from the title." The committed fix closed one producer of title-derived Story content while this second, unguarded producer remains live.
**Code — Consumers:** `plugins/development-harness/backlog_core/github_sync.py::render_issue_body` (`:113`, skip logic `:154-157`) does `sec = item.sections.get(key); if not isinstance(sec, Section) or not sec.entries: continue` for each `SECTION_HEADING` key — read directly, confirmed an item missing `story`/`acceptance_criteria` produces no heading and no exception. `plugins/development-harness/backlog_core/reconciliation.py::_candidate` (`:147-171`), `_new_local_item` (`:129-131`), `_compose` (`:106-126`) — the create-to-parse-to-render round trip, traced end to end: `parse_issue_body` on a body without Story/AC yields a `sections` dict missing those keys, `render_issue_body(candidate, original_body=provider.body)` (`:163`) renders identically via the same skip logic, so `_normalized_body(rendered) == _normalized_body(provider.body)` (`:164`) holds and no `ProviderPatch` is generated for a newly created item on this account. `plugins/development-harness/backlog_core/operations.py::_check_ac_overlap` (`:1123-1134`, call sites `:1174-1175` and `:1241-1242`) fires only when a caller writes the groomed Acceptance Criteria section via `backlog_groom`, which still happens during grooming regardless of this fix; read the function body directly — it inspects `item.description`, unrelated to creation-time generation. `plugins/development-harness/backlog_core/server.py` `backlog_view(map=True)`/`navigate=` ordinal system (`:2454-2531`) — verified by reading the docstring and code: ordinals are a live dot-path map computed per call from whatever sections actually exist, not a hardcoded table; grepped `server.py` for any hardcoded section-to-ordinal mapping and found none, so a mixed population of old (with Story/AC) and new (without) items is handled correctly because every `navigate=` call is expected to follow a fresh `map=True` discovery call. Fixtures `plugins/development-harness/backlog_core/tests/fixtures/issue-1857-full.json`, `issue-2515-full.json`, `issue-996-full.json`, `issue-2521-full.json`, and `plugins/development-harness/tests/test_md_migration.py:20` already exercise parsing a real body containing `## Story` — parse-side, unaffected since only generation changed. Ran `uv run pytest plugins/development-harness/tests/test_backlog_core_parsing.py -k BuildIssueBody -q`: 19 passed, 5 skipped.
**Code — Other References:** None identified beyond the above.
**Documentation:** `plugins/development-harness/skills/backlog/references/item-schema.md` — header states "All skills that read or write item files MUST conform to this schema," yet line 55 reads `"2. Acceptance Criteria (written by: create-backlog-item — bullet list)"`, repeated at line 80 and in the completeness-states table at line 154 — now false for the path this fix changed; highest-severity doc finding since it's marked canonical. `plugins/development-harness/skills/backlog/README.md:161-163` duplicates the same "Body Sections — Canonical Order" table with `"2. Acceptance Criteria (written by: create-backlog-item)"` — same staleness, independent copy, must be updated together with item-schema.md or the two re-diverge. `plugins/development-harness/docs/backlog-lifecycle.draft.md:85` states "Body sections written: Description, optionally Acceptance Criteria, Research First..." — file is explicitly named `.draft.md`; could not determine authoritative status from content alone. `plugins/development-harness/skills/discovery/SKILL.md:32` and `plugins/development-harness/skills/rt-ica/SKILL.md:75` instruct extracting `sections['Acceptance Criteria']` from a freshly loaded item during S1 Discovery/RT-ICA; for an item created after this fix and not yet groomed, that key is absent — prose read by an LLM, so it degrades gracefully (finds nothing, moves on) rather than crashing, but the instruction still describes a section that will not exist at the point these skills typically run. `plugins/development-harness/backlog_core/ARCHITECTURE.md` was already corrected by this same commit; no further action.
**Configuration / CI:** None identified. No `.github/workflows/*` file, fixture, or config references `## Story` or the removed Acceptance Criteria placeholder text.
**Agent Instructions:** `plugins/development-harness/skills/group-items-to-milestone/SKILL.md:66` (detailed under Code — Producers above) is the standout finding here too — it is a live agent instruction that, absent this fix's new title-derivation guard, can independently reproduce #3152's meaning-inversion failure through a second, unguarded creation path.
**Systems Inventory:** (1) backlog_core/parsing.py::build_issue_body — changed producer. (2) backlog_core/models.py — ROLE_MAP/BENEFIT_MAP removed, no orphan refs. (3) backlog_core/gh_client.py::create_issue_for_item:1277 — sole caller of build_issue_body. (4) backlog_core/github_sync.py::render_issue_body — consumer, verified safe. (5) backlog_core/reconciliation.py — consumer, verified clean round-trip. (6) backlog_core/operations.py::_check_ac_overlap / groomed-AC write path — unaffected. (7) backlog_core/server.py backlog_view ordinal system — verified dynamic, unaffected. (8) backlog_core/tests/fixtures + tests/test_md_migration.py — pre-existing parse-side Story fixtures, unaffected. (9) graphify-out/manifest.json + cache/ast/** — tracked generated cache, stale ROLE_MAP/BENEFIT_MAP mentions, self-heals. (10) skills/backlog/references/item-schema.md — STALE, canonical doc. (11) skills/backlog/README.md — STALE, duplicate table. (12) docs/backlog-lifecycle.draft.md — STALE, authoritative status unclear. (13) skills/discovery/SKILL.md — minor staleness. (14) skills/rt-ica/SKILL.md — minor staleness. (15) backlog_core/ARCHITECTURE.md — already fixed in this commit. (16) skills/group-items-to-milestone/SKILL.md + .claude/skills/gh/scripts/github_project_setup.py — independent creation path that can still reproduce the meaning-inversion bug.
**Ecosystem Completeness Checklist:** [x] Every code producer updated or verified compatible EXCEPT group-items-to-milestone's independent path (see above — NOT updated, still exposed). [x] Every code consumer migrated / verified tolerant of absence. [ ] Every stale document updated — item-schema.md, backlog/README.md, backlog-lifecycle.draft.md, discovery/SKILL.md, rt-ica/SKILL.md still need updates. [ ] Every agent instruction updated — group-items-to-milestone/SKILL.md:66 still instructs building a title-derived Story body. [x] Old interface deprecated/removed — ROLE_MAP/BENEFIT_MAP fully removed from source, only a self-healing generated cache still names them. [x] CI/config files updated and validated — none reference the removed sections; fix's own tests pass (19 passed, 5 skipped).
</div>

<div><sub>2026-08-22T14:59:13.720622Z</sub>

**Scope summary**: ~15 systems touched, none broken. The committed fix (`0454b350b`) removes Story/Acceptance-Criteria generation from `build_issue_body` only — the single caller creating new GitHub issues. Every runtime consumer checked (render/parse round-trip, reconcile diffing, ordinal navigation, the groomed-AC gate) already tolerates an absent section and was verified, not assumed, to do so. The real finding is **documentation**: two files explicitly and falsely claim "written by: create-backlog-item" for Acceptance Criteria post-fix (`item-schema.md`, `backlog/README.md`) — both are marked canonical/must-conform. A third, independent producer (`group-items-to-milestone`) still instructs building a `Story`-format body by the same title-derivation pattern this fix eliminates — a design-intent inconsistency, not a break.

### Code — Producers (write the changed interface)
- `plugins/development-harness/backlog_core/parsing.py::build_issue_body` — the change itself. Sole caller confirmed: `plugins/development-harness/backlog_core/gh_client.py:1277` inside `create_issue_for_item`. No other producer calls `build_issue_body` (verified via repo-wide grep, tests excluded).
- `plugins/development-harness/backlog_core/models.py` — `ROLE_MAP`/`BENEFIT_MAP` deleted. Repo-wide grep for both names outside `graphify-out/` returns zero hits — no orphaned import.
- `plugins/development-harness/.claude/skills/gh/scripts/github_project_setup.py` (generic `issue create --body TEXT` wrapper) — takes body as an opaque string; does not itself construct Story/AC content, so it is not a producer of the affected interface. Listed only because `group-items-to-milestone/SKILL.md:66` (below) tells an agent to pass it a hand-built Story-format body.

### Code — Consumers (read the changed interface)
- `plugins/development-harness/backlog_core/github_sync.py::render_issue_body` (`github_sync.py:113-176`) — iterates `SECTION_HEADING.items()` and skips any key whose `item.sections.get(key)` is missing or has no entries (`github_sync.py:154-157`). Read directly: confirmed this already no-ops cleanly for an item with no Story/AC section — no crash, no empty-heading emission.
- `plugins/development-harness/backlog_core/reconciliation.py::_candidate`/`_new_local_item`/`_compose` (`reconciliation.py:129-171`) — the create→parse→render round trip. `parse_issue_body` on a body with no `## Story`/`## Acceptance Criteria` simply produces a `sections` dict without those keys; `render_issue_body(candidate, original_body=...)` then renders identically (same skip logic above), so `_normalized_body(rendered) == _normalized_body(provider.body)` holds and **no spurious `ProviderPatch` is generated** for newly created items on this account. Traced, not assumed.
- `plugins/development-harness/backlog_core/operations.py::_check_ac_overlap` / `_handle_update_groomed` (`operations.py:1123-1175, 1241-1242`) — fires only when a caller writes the "Acceptance Criteria" *groomed* section (via `backlog_groom`), which still happens during grooming regardless of this fix. Unaffected.
- `plugins/development-harness/backlog_core/server.py` `backlog_view(map=True)` / `navigate="N.M"` ordinal system (`server.py:2454-2531`) — docstring and code confirm ordinals are a **live dot-path map computed per-call from whatever sections actually exist**, not a hardcoded position table. No code anywhere hardcodes "Acceptance Criteria is ordinal 2" or similar. A mixed population (old items with Story/AC at some ordinal, new items without) is handled correctly because every navigation is preceded by a fresh `map=True` discovery call — this is a non-issue, verified by reading the implementation, not inferred.
- `plugins/development-harness/backlog_core/tests/fixtures/issue-1857-full.json`, `issue-2515-full.json`, `issue-996-full.json`, `issue-2521-full.json`, `plugins/development-harness/tests/test_md_migration.py:20` — existing fixtures/tests already exercise **parsing** a real issue body that contains `## Story`. These are parse-side (old-format) fixtures, unrelated to whether new items generate the section; they continue to pass because parsing was never changed, only generation. Confirms mixed-population parsing already has test coverage.
- `plugins/development-harness/graphify-out/manifest.json` and sibling `graphify-out/cache/ast/**/*.json` — tracked-in-git (not gitignored — verified via `git ls-files`/`git check-ignore`) generated code-graph cache. Several `cache/ast/v0.9.8/*.json` files still reference `ROLE_MAP`/`BENEFIT_MAP` by name from before the deletion. Stale but self-healing on next `graphify` regeneration; not read by any runtime code path.

### Code — Other References
None identified beyond the producer/consumer list above.

### Documentation (will become stale)
- **`plugins/development-harness/skills/backlog/references/item-schema.md`** (lines 34-45 field-ownership table is unaffected, but lines 51-92 and 154 are now false) — explicitly states, as the file's own header claims "All skills that read or write item files MUST conform to this schema": `"2. Acceptance Criteria (written by: create-backlog-item — bullet list)"` (line 55) and repeats "written by: create-backlog-item" at line 80 and in the completeness-states table at line 154 ("Newly created ... Description, optionally AC + Research First + Suggested Location"). This is now incorrect for the GitHub-issue-creation path this fix changes. Highest-severity doc finding — it is marked canonical.
- **`plugins/development-harness/skills/backlog/README.md:161-163`** — duplicates the same "Body Sections — Canonical Order" table with `"2. Acceptance Criteria (written by: create-backlog-item)"`. Same staleness as above, independent copy that must be updated in step with `item-schema.md` or the two will re-diverge.
- **`plugins/development-harness/docs/backlog-lifecycle.draft.md:85`** — states "Body sections written: Description, optionally Acceptance Criteria, Research First..." describing creation-time behavior. File is explicitly named `.draft.md`; unclear whether it is treated as authoritative or superseded working notes (could not determine authoritative status from content alone — no supersession banner found, but the `.draft` suffix and its appearance only as a cross-reference target, never a "load this" instruction elsewhere, suggests lower priority than the two files above).
- **`plugins/development-harness/skills/discovery/SKILL.md:32`** and **`plugins/development-harness/skills/rt-ica/SKILL.md:75`** — both instruct an agent to "Extract: ... `sections['Acceptance Criteria']` ..." from a freshly loaded item during S1 Discovery / RT-ICA. For an item created after this fix and not yet groomed, that key will be absent. This is prose read by an LLM (not a literal dict-access crash) so it degrades gracefully — the agent finds nothing and moves on — but the instruction itself is now describing a section that will not exist at the point these skills typically run (pre-grooming). Minor staleness, not a functional break.
- `plugins/development-harness/backlog_core/ARCHITECTURE.md` — already corrected by this same commit (removes `ROLE_MAP`/`BENEFIT_MAP` from the extracted-constants list). No further action needed.

### Configuration / CI
None identified. No `.github/workflows/*` file, fixture, or config references `## Story` or the creation-time Acceptance Criteria text.

### Agent Instructions (instruct AI to use current interface)
- **`plugins/development-harness/skills/group-items-to-milestone/SKILL.md:66`** — "Build story-format body (Story / Description / Acceptance Criteria / Context). Create issue using the Python script..." This is a **second, independent issue-creation path** (via `.claude/skills/gh/scripts/github_project_setup.py issue create --body`) that does not call `build_issue_body` and is therefore not broken by this diff. However, it explicitly instructs generating the same title-derived "Story" pattern that `build_issue_body`'s new docstring (parsing.py, this diff) says is deliberately wrong ("a template-filled section emitted at creation satisfies [the groom] check without anyone having written a criterion", and the removed test `test_build_issue_body_never_derives_content_from_title` codifies exactly this concern). This is a design-intent inconsistency between the two creation paths, not a runtime break — flagged for the maintainer to reconcile, since #3152's stated objection is specifically about ungroomed, title-derived Story/AC content appearing at creation.

### Systems Inventory
1. `backlog_core/parsing.py::build_issue_body` — changed producer
2. `backlog_core/models.py` — ROLE_MAP/BENEFIT_MAP removed, no orphan refs
3. `backlog_core/gh_client.py::create_issue_for_item` (:1277) — sole caller of build_issue_body
4. `backlog_core/github_sync.py::render_issue_body` — consumer, verified safe (skip-if-absent)
5. `backlog_core/reconciliation.py` (`_candidate`, `_new_local_item`, `_compose`) — consumer, verified clean round-trip
6. `backlog_core/operations.py::_check_ac_overlap` / groomed-AC write path — unaffected (fires at grooming time)
7. `backlog_core/server.py` — `backlog_view(map=True/navigate=...)` ordinal system — verified dynamic, unaffected
8. `backlog_core/tests/fixtures/issue-*.json` + `tests/test_md_migration.py` — pre-existing parse-side Story fixtures, unaffected
9. `graphify-out/manifest.json` + `graphify-out/cache/ast/**` — tracked generated cache, stale ROLE_MAP/BENEFIT_MAP mentions, self-heals on regen
10. `skills/backlog/references/item-schema.md` — STALE, canonical doc, needs update
11. `skills/backlog/README.md` — STALE, duplicate table, needs update
12. `docs/backlog-lifecycle.draft.md` — STALE, authoritative status unclear
13. `skills/discovery/SKILL.md` — minor staleness in extraction instruction
14. `skills/rt-ica/SKILL.md` — minor staleness in extraction instruction
15. `backlog_core/ARCHITECTURE.md` — already fixed in this same commit
16. `skills/group-items-to-milestone/SKILL.md` + `.claude/skills/gh/scripts/github_project_setup.py` — independent creation path, design-intent inconsistency (not broken)

### Ecosystem Completeness Checklist
- [x] Every code producer updated or verified compatible — sole producer (`build_issue_body`) is the change itself; all consumers traced and verified tolerant of absence
- [x] Every code consumer migrated to new interface — none required migration; all degrade gracefully by design (skip-if-absent pattern already present in `render_issue_body`)
- [ ] Every stale document updated — `item-schema.md` and `backlog/README.md` still assert "written by: create-backlog-item" for Acceptance Criteria; `backlog-lifecycle.draft.md`, `discovery/SKILL.md`, `rt-ica/SKILL.md` need minor updates
- [ ] Every agent instruction updated — `group-items-to-milestone/SKILL.md:66` still instructs building a title-derived Story-format body via an independent path
- [x] Old interface deprecated or removed (if replacing) — `ROLE_MAP`/`BENEFIT_MAP` fully removed from source; only a self-healing generated cache (`graphify-out/`) still names them
- [x] CI/config files updated and validated — none reference the removed sections; `uv run pytest plugins/development-harness/tests/test_backlog_core_parsing.py -k BuildIssueBody` run and confirmed 19 passed, 5 skipped

**Bottom line**: the code change is safe as committed — every runtime path was traced to source and found to already handle section absence correctly (this was largely because `render_issue_body`'s entry-bearing-sections loop was already written defensively, not because this diff added new defensiveness). The unresolved risk is entirely in prose: two canonical documentation files make a now-false claim about who writes Acceptance Criteria, and one sibling skill (`group-items-to-milestone`) still tells an agent to hand-build the exact anti-pattern this fix removes. None of this blocks merging the code change, but the fix is incomplete as a *documentation and design-intent* matter — the human's original objection ("no impact assessment was done") is addressed by this analysis, and the remaining gaps (4 doc updates + 1 sibling-skill reconciliation) are small, bounded follow-up work.
</div>

<div><sub>2026-08-22T15:11:41.223051Z</sub>

**Code — Producers (write the changed interface)**
- `plugins/development-harness/backlog_core/parsing.py::build_issue_body` (line 635) — the change itself. Verified single caller via repo-wide grep for `build_issue_body(` outside `tests/`: `plugins/development-harness/backlog_core/gh_client.py:1277`, inside `create_issue_for_item`.
- `plugins/development-harness/backlog_core/models.py` — `ROLE_MAP`/`BENEFIT_MAP` deleted. Verified via repo-wide grep for both names: zero hits in source; only stale hits in the generated, git-tracked cache `plugins/development-harness/graphify-out/cache/ast/v0.9.8/*.json` (self-heals on next `graphify` regen, not read by runtime code).
- **`plugins/development-harness/skills/group-items-to-milestone/SKILL.md:66`** — a SECOND, independent producer: "Build story-format body (Story / Description / Acceptance Criteria / Context). Create issue using the Python script..." This path creates GitHub issues via `.claude/skills/gh/scripts/github_project_setup.py issue create --body`, NOT via `build_issue_body` — confirmed by reading the SKILL.md step and the script's signature (it takes an opaque `--body` string; it does not itself template anything from the title). Can this site reproduce the same meaning-inverting output? Yes, plausibly. The original bug was code that mechanically lowercased the title into an `I want to {goal}` slot. This instruction hands the same task to an LLM with no comparable guard: it says "build story-format body" with no warning against deriving Story content from the title, unlike the fixed `build_issue_body`, whose new docstring (this diff, `parsing.py:637-644`) and deleted test `test_build_issue_body_never_derives_content_from_title` now explicitly codify "never derive section content from the title." An LLM following the unguarded instruction at `group-items-to-milestone/SKILL.md:66` has no textual signal steering it away from the same "lowercase title into I-want-to slot" pattern. Most consequential finding: the committed fix closed one producer of title-derived Story content while a second, independent producer with no equivalent guard remains live.
**Code — Consumers (read the changed interface)**
- `plugins/development-harness/backlog_core/github_sync.py::render_issue_body` (`github_sync.py:113`, skip logic at `github_sync.py:154-157`) — iterates `SECTION_HEADING.items()` and does `sec = item.sections.get(key); if not isinstance(sec, Section) or not sec.entries: continue`. Verified by reading this code directly: an item with no `story`/`acceptance_criteria` key in `item.sections` produces no `## Story`/`## Acceptance Criteria` heading and no exception — confirmed by source inspection, not assumption.
- `plugins/development-harness/backlog_core/reconciliation.py::_candidate` (`reconciliation.py:147-171`), `_new_local_item` (`:129-131`), `_compose` (`:106-126`) — the create→parse→render round trip. Verified by tracing the call chain: `parse_issue_body` on a body with no Story/AC heading yields a `sections` dict missing those keys; `render_issue_body(candidate, original_body=provider.body)` (`:163`) then renders identically via the same skip logic above, so `_normalized_body(rendered) == _normalized_body(provider.body)` (`:164`) holds and no `ProviderPatch` is generated on this account for a newly created item. Traced end to end, not assumed.
- `plugins/development-harness/backlog_core/operations.py::_check_ac_overlap` (`:1123-1134`) and its call sites at `:1174-1175` and `:1241-1242` — fires only when a caller writes the groomed "Acceptance Criteria" section via `backlog_groom`, which still happens during grooming regardless of this fix (the groomer teammate in `swarm.md` still produces this subsection). Read the function body directly: it inspects `item.description`, unrelated to whether AC was generated at creation. Unaffected.
- `plugins/development-harness/backlog_core/server.py` — `backlog_view(map=True)` / `navigate="N.M"` ordinal system (`server.py:2454-2531`). Verified by reading the tool docstring and implementation: ordinals are a live dot-path map computed per call from whatever sections actually exist ("Use map=True first to discover valid ordinals" — `server.py:2457,2470`), not a hardcoded position table. Grepped `server.py` for any hardcoded section-to-ordinal mapping: none found. A mixed population (old items with Story/AC at some ordinal, new items without) is handled correctly because every `navigate=` call is expected to be preceded by a fresh `map=True` discovery call. Verified by reading the implementation, not inferred.
- `plugins/development-harness/backlog_core/tests/fixtures/issue-1857-full.json`, `issue-2515-full.json`, `issue-996-full.json`, `issue-2521-full.json`, and `plugins/development-harness/tests/test_md_migration.py:20` — existing fixtures/tests already exercise parsing a real issue body containing `## Story`. Confirmed these are parse-side (old-format) fixtures, unaffected by this change since only generation (not parsing) changed. Ran `uv run pytest plugins/development-harness/tests/test_backlog_core_parsing.py -k BuildIssueBody -q`: 19 passed, 5 skipped.
**Code — Other References**
None identified beyond the producer/consumer list above.
</div>

## Acceptance Criteria

<div><sub>0000-00-00T00:00:00Z</sub>

- [ ] Work matches description
- [ ] Plan or implementation complete
</div>

## Story

<div><sub>0000-00-00T00:00:00Z</sub>

As a **developer relying on this plugin**, I want to **created items ship with a generated story and acceptance criteria that no author wrote and that can invert the item's meaning** so that **the tool works correctly and reliably**.
</div>

## Context

<div><sub>0000-00-00T00:00:00Z</sub>

- **Source**: Session observation — 2026-08-22, observed on #3151 at creation
- **Priority**: P1
- **Added**: 2026-08-22
- **Research questions**: None
</div>

<div><sub>2026-08-22T14:05:04.454399Z</sub>

The sentinel is itself malformed, so it is not a sound marker even for its own purpose.

Generated Story and Acceptance Criteria entries carry the entry id `0000-00-00T00:00:00Z`. That is not a valid ISO 8601 timestamp — there is no year zero, no month zero, and no day zero. Every authored entry uses that same field as a genuine timestamp, so one field now holds two kinds of value: real timestamps and an impossible one used as a flag.

Consequence to check, not asserted: `backlog_view` accepts a `since` parameter documented as "ISO date/datetime. Only entries at or after this timestamp are included." Any comparison or parse over entry ids encounters this value. Whether it raises, silently sorts first, or is coerced has not been tested here — the observation is that a value which cannot be a date is stored where dates are read.

This compounds the main defect rather than mitigating it. The generated sections are indistinguishable from authored ones to a consumer reading by section name, and the one field that could distinguish them holds data that no date parser should accept. A marker for "this was generated, not written" belongs in an explicit field with an explicit meaning, not encoded as an impossible value in a timestamp.

Observed on #3151 and reproduced on this item at creation.
</div>

## Root-Cause Analysis

<div><sub>2026-08-22T14:58:19.705431Z</sub>

**Evidence Chain**

1. **Original defect:** `backlog_core/models.py` lines 433-451 defined `ROLE_MAP` and `BENEFIT_MAP` that template-fill Story and Acceptance Criteria sections at item creation time
2. **Symptom:** `backlog_core/parsing.py:build_issue_body()` called these maps to generate synthetic content in Story and Acceptance Criteria sections without human input
3. **Masking mechanism:** Synthetic entries bore sentinel timestamps (`0000-00-00T00:00:00Z`) distinguishing them from authored content at the storage/parsing level, but consumers (grooming validation gates, agents reading sections by name) treat all non-empty sections as populated and authored
4. **Semantic inversion mechanism:** Item #3151 has title: "refactor: File-based language for SAM tasks persists because the context-file key and AGENTS.md required reading still teach it". This is a PROBLEM STATEMENT naming an undesired current state. The generator lowercases and slots it into "I want to {goal}": result reads as "I want to file-based language for SAM tasks persists because..." — which inverts meaning by making it sound like the person WANTS the problem to persist, when the item exists to end it. The generator assumed all titles name desired goals; refactor and bug titles typically name undesired states.
5. **Precedent defect:** Regression test at `test_backlog_core_parsing.py:797-815` guards the "old synthetic header bug" where Story headers were duplicated from synthetic generation—evidence this pattern has caused failures before

**Pattern recurrence classification — git-verified**

Same problem class appears at minimum across these commits (git history since development-harness plugin creation):
- Commit `6214055af` / Issue #2956: "backlog_view read-path/section-key visibility bug" — synthetic entries visible/invisible depending on read path
- Commit `c527427e8` / Issue #3015: Section-key and collision fixes
- Commit `f98a87941` / Issue #3047: "distinguish absent from mis-keyed sections" — synthetic/malformed entry differentiation
- Regression guard `test_backlog_core_parsing.py:797-815`: "old synthetic header bug"
- Current: Issue #3152 — Story and Acceptance Criteria generated at creation
- Mentioned: Issue #3153 — sentinel values written where dates are read

**Root cause of recurring pattern**

Generation of synthetic/placeholder content occurs at item INTAKE (creation) before refinement. The system records that entries are synthetic (via sentinel timestamps), but:
- Downstream consumers read sections by name, not by entry-timestamp sentinel — they see a section populated and assume it was authored
- A non-empty section satisfies "non-empty Acceptance Criteria" gates regardless of who wrote it
- Template-filled content is plausible enough (proper markdown, checkboxes, prose) to be mistaken for authored content
- No systemic mechanism prevents re-synthesis of placeholder content at other creation or intake points — each code path independently decided to generate Story and AC at creation

**Systemic guardrail gap**

Current fix removes template generation at one call site (`build_issue_body` at creation). Missing guardrail: no validation gate prevents synthetic content generation at OTHER code paths that create or populate acceptance criteria or story sections. The grooming workflow (`groom/finalize.md`) requires non-empty Acceptance Criteria to mark an item groomed, but checks for SECTION EXISTENCE, not for AUTHOR-PRESENCE. A template-filled section satisfies this gate without human input, every time.

**Why committed one-site fix is INSUFFICIENT**

Removing `build_issue_body()` synthetic generation is NECESSARY. But the broader pattern—synthetic content that passes structural/plausibility checks—can re-emerge at OTHER generation sites unless a guardrail prevents it repo-wide. Evidence: the regression guard at line 797 exists BECAUSE this same pattern failed before at a different site (`build_issue_body_from_file`). History shows 6+ independent commits in `backlog_core/` addressing section-handling, malformed entries, and visibility bugs. One-site removal does not establish the guardrail.
</div>

## Resolution

<div><sub>2026-08-22T14:22:10.792088Z</sub>

Fixed on branch `fix/3152-no-generated-story-acceptance-criteria`, commit `0454b350b`.

Root cause: `backlog_core/parsing.py` `build_issue_body()` (single non-test caller: `gh_client.py:1277`, GitHub issue creation) template-filled two sections from the item title:

    role = ROLE_MAP.get(item_type, ...)
    benefit = BENEFIT_MAP.get(item_type, ...)
    goal = title.rstrip(".")
    sections = [
        f"## Story\n\nAs a **{role}**, I want to **{goal.lower()}** so that **{benefit}**.",
        f"## Description\n\n{desc}",
        "## Acceptance Criteria\n\n- [ ] Work matches description\n- [ ] Plan or implementation complete",
    ]

Fix shape chosen: drop both sections at creation. `build_issue_body()` now emits only sections whose content the caller supplied — Description, plus Files / Suggested Location / Context when set. `ROLE_MAP` and `BENEFIT_MAP` had no remaining consumers and were deleted from `models.py`; the stale reference in `backlog_core/ARCHITECTURE.md` was removed.

Why this shape rather than an unfilled template: `groom/finalize.md`'s required-sections table gates on `Acceptance Criteria` being "Non-empty — at least one criterion listed". Any populated section emitted at creation satisfies that gate without anyone having written a criterion. An absent section cannot. Grooming already writes Acceptance Criteria as a required output; `Story` appears in neither the required nor the optional list in that table, so nothing depends on it existing.

Reproduction, using the #3151 title named in the report. Before:

    ## Story

    As a **maintainer of the codebase**, I want to **file-based language for sam tasks
    persists because the context-file key and agents.md required reading still teach it**
    so that **the code is cleaner and more maintainable**.

After: the body contains `## Description` and `## Context` only.

Tests: `tests/test_backlog_core_parsing.py` — `test_build_issue_body_omits_story_section`, `test_build_issue_body_omits_acceptance_criteria_section`, `test_build_issue_body_never_derives_content_from_title` (guards the root cause directly: a title naming the thing to be removed must not appear in generated prose), plus the updated minimal-item case. Full suite: 3375 passed, 39 skipped, 5 xfailed.

Correction to a premise in this item, verified against source: the `0000-00-00T00:00:00Z` entry id is not a sentinel distinguishing generated entries from authored ones. `backlog_core/entry_blocks.py:157` (`parse_entries`) emits `f"{added_date}T00:00:00Z"` as the fallback id for any section body containing no `<sub>` entry wrapper, and `added_date` itself falls back to the literal `"0000-00-00"` when `item.added` is empty. On this very item the authored `Description` and `Context` entries carry the same id. The system was therefore never recording that Story and Acceptance Criteria were generated — the id was a missing-timestamp fallback that happened to apply to every section of a freshly created issue. Filed separately.

</div>
